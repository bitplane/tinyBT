import random
import socket
import urllib.parse
import urllib.request

from utils import (
    decode_connections,
    decode_uint32,
    decode_uint64,
    encode_int32,
    encode_ip,
    encode_uint16,
    encode_uint32,
    encode_uint64,
)
from utils.client import UDPSocket
from utils.exception import TrackerResponseError


# Implementation of BEP #0015 (UDP tracker protocol)
def get_peers(
    tracker_url,
    info_hash,
    peer_id,
    ip="0.0.0.0",
    port=0,
    uploaded=0,
    downloaded=0,
    left=0,
    event="started",
    num_want=-1,
    key=0,
):
    event = {"empty": 0, "completed": 1, "started": 2, "stopped": 3}[event]
    url = urllib.parse.urlparse(tracker_url)
    conn = (socket.gethostbyname(url.hostname), url.port)
    sock = UDPSocket(("0.0.0.0", 0))

    def recv():
        timeout = 5
        while True:
            try:
                data, _src = sock.recvfrom(timeout)
            except socket.error:
                data = None
            if not data:
                timeout *= 2
                if timeout > 60:
                    break
                continue

            assert len(data) >= 16
            action = decode_uint32(data[0:4])
            remote_tid = decode_uint32(data[4:8])
            return (action, remote_tid, data[8:])

        return (None, None, None)

    def perform_announce():
        cid = 0x41727101980

        action_connect = 0
        tid = random.randint(0, 2**32 - 1)
        remote_tid = None
        while remote_tid != tid:
            req = (
                encode_uint64(cid) + encode_uint32(action_connect) + encode_uint32(tid)
            )
            sock.sendto(req, conn)
            (action, remote_tid, data) = recv()
            if not data:
                raise TrackerResponseError(
                    "Tracker %s:%d did not answer to handshake" % conn
                )
            remote_cid = decode_uint64(data[0:8])
            if action != action_connect:
                remote_tid = None

        action_announce = 1
        tid = random.randint(0, 2**32 - 1)
        remote_tid = None
        while remote_tid != tid:
            assert len(info_hash) == 20
            assert len(peer_id) == 20
            req = (
                encode_uint64(remote_cid)
                + encode_uint32(action_announce)
                + encode_uint32(tid)
                + info_hash
                + peer_id
                + encode_uint64(downloaded)
                + encode_uint64(left)
                + encode_uint64(uploaded)
                + encode_uint32(event)
                + encode_ip(ip)
                + encode_uint32(key)
                + encode_int32(num_want)
                + encode_uint16(port)
            )
            sock.sendto(req, conn)
            (action, remote_tid, data) = recv()
            if not data:
                raise TrackerResponseError("Tracker %s:%d did not answer query" % conn)
            if action != action_announce:
                remote_tid = None

        # interval = decode_uint32(data[0:4])
        # num_leech = decode_uint32(data[4:8])
        # num_seed = decode_uint32(data[8:12])

        return list(decode_connections(data[12:]))

    try:
        return perform_announce()
    finally:
        sock.close()
