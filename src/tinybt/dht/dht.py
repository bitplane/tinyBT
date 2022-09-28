import hashlib
import hmac
import inspect
import logging
import os
import socket
import threading
import time

from dht.node import DHT_Node, bep42_prefix, valid_id
from dht.router import DHT_Router
from krpc import KRPCError, KRPCPeer
from utils import (
    AsyncTimeout,
    ThreadManager,
    decode_connection,
    decode_id,
    decode_nodes,
    encode_connection,
    encode_ip,
    encode_nodes,
    encode_uint32,
)


class DHT(object):
    def __init__(
        self,
        listen_connection,
        bootstrap_connection=("router.bittorrent.com", 6881),
        user_setup={},
        user_router=None,
    ):
        """Start DHT peer on given (host, port) and bootstrap connection to the DHT"""
        setup = {"discover_t": 180, "check_t": 30, "check_N": 10}
        setup.update(user_setup)
        self._log = logging.getLogger(
            self.__class__.__name__ + ".%s.%d" % listen_connection
        )
        self._log.info(
            "Starting DHT node with bootstrap connection %s:%d" % bootstrap_connection
        )
        listen_connection = (
            socket.gethostbyname(listen_connection[0]),
            listen_connection[1],
        )
        # Generate key for token generation
        self._token_key = os.urandom(20)
        # Start KRPC server process and Routing table
        self._krpc = KRPCPeer(listen_connection, self._handle_query)
        if not user_router:
            user_router = DHT_Router("%s.%d" % listen_connection, setup)
        self._nodes = user_router
        self._node = DHT_Node(listen_connection, os.urandom(20))
        self._node_lock = threading.RLock()
        # Start bootstrap process
        tmp = self.ping(bootstrap_connection, sender_id=self._node.id).get_result(
            timeout=1
        )
        self._node.connection = decode_connection(tmp[b"ip"])
        self._bootstrap_node = self._nodes.register_node(
            bootstrap_connection, tmp[b"r"][b"id"]
        )
        # BEP #0042 Enable security extension
        local_id = bytearray(self._node.id)
        bep42_value = encode_uint32(
            bep42_prefix(self._node.connection[0], local_id[-1], local_id[0])
        )
        self._node.set_id(bep42_value[:3] + self._node.id[3:])
        assert valid_id(self._node.id, self._node.connection)
        self._nodes.protect_nodes([self._node.id])

        # Start maintainance threads
        self._threads = ThreadManager(self._log.getChild("maintainance"))

        # Periodically ping nodes in the routing table
        def _check_nodes(N, last_ping=15 * 60, timeout=5):
            def get_unpinged(n):
                return time.time() - n.last_ping > last_ping

            check_nodes = list(self._nodes.get_nodes(N, expression=get_unpinged))
            if not check_nodes:
                return
            self._log.debug("Starting cleanup of known nodes")
            node_result_list = []
            for node in check_nodes:
                node.last_ping = time.time()
                node_result_list.append(
                    (node, node.id, self.ping(node.connection, self._node.id))
                )
            t_end = time.time() + timeout
            for (node, node_id, async_result) in node_result_list:
                result = self._eval_dht_response(
                    node, async_result, timeout=max(0, t_end - time.time())
                )
                if result and (
                    node.id != result.get(b"id")
                ):  # remove nodes with changing identities
                    self._nodes.remove_node(node, force=True)

        self._threads.start_continuous_thread(
            _check_nodes, thread_interval=setup["check_t"], N=setup["check_N"]
        )

        # Try to discover a random node to populate routing table
        def _discover_nodes():
            self._log.debug("Starting discovery of random node")
            for idx, entry in enumerate(self.dht_find_node(os.urandom(20), timeout=1)):
                if idx > 10:
                    break

        self._threads.start_continuous_thread(
            _discover_nodes, thread_interval=setup["discover_t"]
        )

    def get_external_connection(self):
        return self._node.connection

    def shutdown(self):
        """This function allows to cleanly shutdown the DHT."""
        self._log.info("shutting down DHT")
        self._threads.shutdown()  # Trigger shutdown of maintainance threads
        self._krpc.shutdown()  # Stop listening for incoming connections
        self._nodes.shutdown()
        self._threads.join()  # Trigger shutdown of maintainance threads

    # Handle remote queries
    _reply_handler = {}

    def _handle_query(self, send_krpc_reply, rec, source_connection):
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug("handling query from %r: %r" % (source_connection, rec))
        try:
            remote_args_dict = rec[b"a"]
            if b"id" in remote_args_dict:
                self._nodes.register_node(
                    source_connection, remote_args_dict[b"id"], rec.get(b"v")
                )
            query = rec[b"q"]
            callback = self._reply_handler[query]
            callback_kwargs = {}
            for arg in inspect.getargspec(callback).args[2:]:
                arg_bytes = arg.encode("ascii")
                if arg_bytes in remote_args_dict:
                    callback_kwargs[arg] = remote_args_dict[arg_bytes]

            def send_dht_reply(**kwargs):
                # BEP #0042 - require ip field in answer
                return send_krpc_reply(
                    kwargs, {b"ip": encode_connection(source_connection)}
                )

            send_dht_reply.connection = source_connection
            callback(self, send_dht_reply, **callback_kwargs)
        except Exception:
            self._log.exception("Error while processing request %r" % rec)

    # Evaluate async KRPC result and notify the routing table about failures
    def _eval_dht_response(self, node, async_result, timeout):
        try:
            result = async_result.get_result(timeout)
            node.version = result.get(b"v", node.version)
            self._nodes.good_node(node)
            return result[b"r"]
        except AsyncTimeout:  # The node did not reply
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("KRPC timeout %r" % node)
        except KRPCError:  # Some other error occured
            if self._log.isEnabledFor(logging.INFO):
                self._log.exception("KRPC Error %r" % node)
        self._nodes.remove_node(node)
        async_result.discard_result()
        return {}

    # Iterate KRPC function on closest nodes - query_fun(connection, id, search_value)
    def _iter_krpc_search(self, query_fun, process_fun, search_value, timeout, retries):
        id_cmp = decode_id(search_value)
        (returned, used_connections, discovered_nodes) = (set(), {}, set())
        while not self._threads.shutdown_in_progress():

            def above_retries(c):
                return used_connections[c] > retries

            blacklist_connections = set(filter(above_retries, used_connections))

            def valid_node(n):
                return n and (n.connection not in blacklist_connections)

            discovered_nodes = set(filter(valid_node, discovered_nodes))

            def not_blacklisted(n):
                return n.connection not in blacklist_connections

            def sort_by_id(n):
                return n.id_cmp ^ id_cmp

            close_nodes = set(
                self._nodes.get_nodes(
                    N=20, expression=not_blacklisted, sorter=sort_by_id
                )
            )

            if not close_nodes.union(discovered_nodes):
                break

            node_result_list = []
            for node in close_nodes.union(
                discovered_nodes
            ):  # submit all queries at the same time
                if node.pending > 3:
                    continue
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("asking %s" % repr(node))
                async_result = query_fun(node.connection, self._node.id, search_value)
                with self._node_lock:
                    node.pending += 1
                node_result_list.append((node, async_result))
                used_connections[node.connection] = (
                    used_connections.get(node.connection, 0) + 1
                )

            t_end = time.time() + timeout
            for (
                node,
                async_result,
            ) in node_result_list:  # sequentially retrieve results
                if self._threads.shutdown_in_progress():
                    break
                result = self._eval_dht_response(
                    node, async_result, timeout=max(0, t_end - time.time())
                )
                with self._node_lock:
                    node.pending -= 1
                for node_id, node_connection in decode_nodes(result.get(b"nodes", b"")):
                    discovered_nodes.add(
                        self._nodes.register_node(node_connection, node_id)
                    )
                for tmp in process_fun(node, result):
                    if tmp not in returned:
                        returned.add(tmp)
                        yield tmp

    # syncronous query / async reply implementation of BEP #0005 (DHT Protocol) #
    #############################################################################
    # Each KRPC method XYZ is implemented using 3 functions:
    #   dht_XYZ(...) - wrapper to process the result of the KRPC function
    #       XYZ(...) - direct call of the KRPC method - returns AsyncResult
    #      _XYZ(...) - handler to process incoming KRPC calls

    # ping methods
    #   (sync method)
    def dht_ping(self, connection, timeout=5):
        try:
            result = self.ping(connection, self._node.id).get_result(timeout)
            if result.get(b"r", {}).get(b"id"):
                self._nodes.register_node(
                    connection, result[b"r"][b"id"], result.get(b"v")
                )
            return result.get(b"r", {})
        except (AsyncTimeout, KRPCError):
            pass

    #   (verbatim, async KRPC method)
    def ping(self, target_connection, sender_id):
        return self._krpc.send_krpc_query(target_connection, b"ping", id=sender_id)

    #   (reply method)
    def _ping(self, send_krpc_reply, id):
        send_krpc_reply(id=self._node.id)

    _reply_handler[b"ping"] = _ping

    # find_node methods
    #   (sync method, iterating on close nodes)
    def dht_find_node(self, search_id, timeout=5, retries=2):
        def process_find_node(node, result):
            for node_id, node_connection in decode_nodes(result.get(b"nodes", b"")):
                if node_id == search_id:
                    yield node_connection

        return self._iter_krpc_search(
            self.find_node, process_find_node, search_id, timeout, retries
        )

    #   (verbatim, async KRPC method)
    def find_node(self, target_connection, sender_id, search_id):
        return self._krpc.send_krpc_query(
            target_connection, b"find_node", id=sender_id, target=search_id
        )

    #   (reply method)
    def _find_node(self, send_krpc_reply, id, target):
        id_cmp = decode_id(id)

        def select_valid(n):
            return valid_id(n.id, n.connection)

        def sort_by_id(n):
            return n.id_cmp ^ id_cmp

        send_krpc_reply(
            id=self._node.id,
            nodes=encode_nodes(
                self._nodes.get_nodes(N=20, expression=select_valid, sorter=sort_by_id)
            ),
        )

    _reply_handler[b"find_node"] = _find_node

    # get_peers methods
    #   (sync method, iterating on close nodes)
    def dht_get_peers(self, info_hash, timeout=5, retries=2):
        def process_get_peers(node, result):
            if result.get(b"token"):
                node.tokens[info_hash] = result[
                    b"token"
                ]  # store token for subsequent announce_peer
            for node_connection in map(decode_connection, result.get(b"values", b"")):
                yield node_connection

        return self._iter_krpc_search(
            self.get_peers, process_get_peers, info_hash, timeout, retries
        )

    #   (verbatim, async KRPC method)
    def get_peers(self, target_connection, sender_id, info_hash):
        return self._krpc.send_krpc_query(
            target_connection, b"get_peers", id=sender_id, info_hash=info_hash
        )

    #   (reply method)
    def _get_peers(self, send_krpc_reply, id, info_hash):
        token = hmac.new(
            self._token_key, encode_ip(send_krpc_reply.connection[0]), hashlib.sha1
        ).digest()
        id_cmp = decode_id(id)

        def select_valid(n):
            return valid_id(n.id, n.connection)

        def sort_by_id(n):
            return n.id_cmp ^ id_cmp

        reply_args = {
            "nodes": encode_nodes(
                self._nodes.get_nodes(N=8, expression=select_valid, sorter=sort_by_id)
            )
        }
        if self._node.values.get(info_hash):
            reply_args["values"] = list(
                map(encode_connection, self._node.values[info_hash])
            )
        send_krpc_reply(id=self._node.id, token=token, **reply_args)

    _reply_handler[b"get_peers"] = _get_peers

    # announce_peer methods
    #   (sync method, announcing to all nodes giving tokens)
    def dht_announce_peer(self, info_hash, implied_port=1):
        def has_info_hash_token(node):
            return info_hash in node.tokens

        for node in self._nodes.get_nodes(expression=has_info_hash_token):
            yield self.announce_peer(
                node.connection,
                self._node.id,
                info_hash,
                self._node.connection[1],
                node.tokens[info_hash],
                implied_port=implied_port,
            )

    #   (verbatim, async KRPC method)
    def announce_peer(
        self, target_connection, sender_id, info_hash, port, token, implied_port=None
    ):
        req = {"id": sender_id, "info_hash": info_hash, "port": port, "token": token}
        if (
            implied_port is not None
        ):  # (optional) "1": port not reliable - remote should use source port
            req["implied_port"] = implied_port
        return self._krpc.send_krpc_query(target_connection, b"announce_peer", **req)

    #   (reply method)
    def _announce_peer(
        self, send_krpc_reply, id, info_hash, port, token, implied_port=None
    ):
        local_token = hmac.new(
            self._token_key, encode_ip(send_krpc_reply.connection[0]), hashlib.sha1
        ).digest()
        if (local_token == token) and valid_id(
            id, send_krpc_reply.connection
        ):  # Validate token and ID
            if implied_port:
                port = send_krpc_reply.connection[1]
            self._node.values.setdefault(info_hash, []).append(
                (send_krpc_reply.connection[0], port)
            )
            send_krpc_reply(id=self._node.id)

    _reply_handler[b"announce_peer"] = _announce_peer
