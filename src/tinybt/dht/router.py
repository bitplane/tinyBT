import logging
import random
import threading

from dht.node import DHT_Node, valid_id
from utils.threadmanager import ThreadManager


# Trivial node list implementation
class DHT_Router(object):
    def __init__(self, name, user_setup={}):
        setup = {
            "report_t": 10,
            "limit_t": 30,
            "limit_N": 2000,
            "redeem_t": 300,
            "redeem_frac": 0.05,
        }
        setup.update(user_setup)

        self._log = logging.getLogger(self.__class__.__name__ + ".%s" % name)
        # This is our (trivial) routing table.
        self._nodes = {}
        self._nodes_lock = threading.RLock()
        self._nodes_protected = set()
        self._connections_bad = set()

        # Start maintainance threads
        self._threads = ThreadManager(self._log.getChild("maintainance"))
        self.shutdown = self._threads.shutdown

        # - Report status of routing table
        def _show_status():
            with self._nodes_lock:
                self._log.info(
                    "Routing table contains %d ids with %d nodes (%d bad, %s protected)"
                    % (
                        len(self._nodes),
                        sum(map(len, self._nodes.values())),
                        len(self._connections_bad),
                        len(self._nodes_protected),
                    )
                )
                if self._log.isEnabledFor(logging.DEBUG):
                    for node in self.get_nodes():
                        self._log.debug("\t%r" % node)

        self._threads.start_continuous_thread(
            _show_status, thread_interval=setup["report_t"], thread_waitfirst=True
        )

        # - Limit number of active nodes

        def _limit(maxN):
            self._log.debug("Starting limitation of nodes")
            N = len(self.get_nodes())
            if N > maxN:
                for node in self.get_nodes(
                    N - maxN,
                    expression=lambda n: n.connection not in self._connections_bad,
                    sorter=lambda x: random.random(),
                ):
                    self.remove_node(node, force=True)

        self._threads.start_continuous_thread(
            _limit,
            thread_interval=setup["limit_t"],
            maxN=setup["limit_N"],
            thread_waitfirst=True,
        )

        # - Redeem random nodes from the blacklist

        def _redeem_connections(fraction):
            self._log.debug("Starting redemption of blacklisted nodes")
            remove = int(fraction * len(self._connections_bad))
            with self._nodes_lock:
                while self._connections_bad and (remove > 0):
                    self._connections_bad.pop()
                    remove -= 1

        self._threads.start_continuous_thread(
            _redeem_connections,
            thread_interval=setup["redeem_t"],
            fraction=setup["redeem_frac"],
            thread_waitfirst=True,
        )

    def protect_nodes(self, node_id_list):
        self._log.info("protect %s" % repr(sorted(node_id_list)))
        with self._nodes_lock:
            self._nodes_protected.update(node_id_list)

    def good_node(self, node):
        with self._nodes_lock:
            node.attempt = 0

    def remove_node(self, node, force=False):
        with self._nodes_lock:
            node.attempt += 1
            if node.id in self._nodes:
                max_attempts = 2
                if valid_id(node.id, node.connection):
                    max_attempts = 5

                protected = node.id in self._nodes_protected
                too_many_attempts = node.attempt > max_attempts

                if force or (too_many_attempts and not protected):
                    if not force:
                        self._connections_bad.add(node.connection)

                    def is_not_removed_node(n):
                        return n.connection != node.connection

                    self._nodes[node.id] = list(
                        filter(is_not_removed_node, self._nodes[node.id])
                    )
                    if not self._nodes[node.id]:
                        self._nodes.pop(node.id)

    def register_node(self, node_connection, node_id, node_version=None):
        with self._nodes_lock:
            if node_connection in self._connections_bad:
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(
                        "rejected bad connection %s" % repr(node_connection)
                    )
                return
            for node in self._nodes.get(node_id, []):
                if node.connection == node_connection:
                    if not node.version:
                        node.version = node_version
                    return node
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("added connection %s" % repr(node_connection))
            node = DHT_Node(node_connection, node_id, node_version)
            self._nodes.setdefault(node_id, []).append(node)
            return node

    # Return nodes matching a filter expression
    def get_nodes(self, N=None, expression=lambda _n: True, sorter=lambda n: n.id_cmp):
        if not self._nodes:
            raise RuntimeError("No nodes in routing table!")

        result = []
        with self._nodes_lock:
            for _id, node_list in self._nodes.items():
                result.extend(filter(expression, node_list))

        result.sort(key=sorter)
        if N is None:
            return result
        return result[:N]
