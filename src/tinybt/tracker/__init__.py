import binascii
import logging
import os

from tracker import http, udp
from utils import decode_connection


class TrackerException(Exception):
    pass


def decode_connections(data):
    while len(data) >= 6:
        c = decode_connection(data[0:6])
        if c[1] >= 1024:
            yield c
        data = data[6:]


if __name__ == "__main__":
    peer_id = os.urandom(20)
    ubuntu_1510_info_hash = binascii.unhexlify(
        "ae3fa25614b753118931373f8feae64f3c75f5cd"
    )
    http_tracker = "http://torrent.ubuntu.com:6969/announce"
    udp_tracker = "udp://tracker.coppersurfer.tk:6969"
    try:
        peers = http.get_peers(http_tracker, ubuntu_1510_info_hash, peer_id)
        print(peers)
    except Exception:
        logging.exception("Exception during http query")
    try:
        udp.get_peers(udp_tracker, ubuntu_1510_info_hash, peer_id)
        print(peers)
    except Exception:
        logging.exception("Exception during udp query")
