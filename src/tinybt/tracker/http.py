import urllib

from utils import decode_connections
from utils.bencode import bdecode
from utils.exception import TrackerResponseError


def open_url(tracker_url, query):
    url = tracker_url + "?" + urllib.parse.urlencode(list(query.items()))
    return urllib.request.urlopen(url)


# Implementation of BEP #0003 (Bittorrent - section: HTTP Tracker protocol)
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
):
    query = {
        b"info_hash": info_hash,
        b"peer_id": peer_id,
        b"ip": ip,
        b"port": port,
        b"uploaded": uploaded,
        b"downloaded": downloaded,
        b"left": left,
        b"compact": 1,
    }
    if event:
        query["event"] = event
    handle = open_url(tracker_url, query)
    if handle.getcode() == 200:
        decoded = bdecode(handle.read())
        if b"peers" not in decoded:
            raise TrackerResponseError(
                decoded.get(b"failure reason", "Unknown failure")
            )
        return list(decode_connections(decoded.get(b"peers", "")))
