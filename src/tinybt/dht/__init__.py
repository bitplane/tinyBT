import logging

from dht.dht import DHT

if __name__ == "__main__":
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logging.getLogger("DHT").setLevel(logging.INFO)
    logging.getLogger("DHT_Router").setLevel(logging.ERROR)
    logging.getLogger("KRPCPeer").setLevel(logging.ERROR)
    logging.getLogger("KRPCPeer.local").setLevel(logging.ERROR)
    logging.getLogger("KRPCPeer.remote").setLevel(logging.ERROR)

    # Create a DHT swarm
    setup = {}
    bootstrap_connection = ("localhost", 10001)
    # 	bootstrap_connection = ('router.bittorrent.com', 6881)
    dht1 = DHT(("0.0.0.0", 10001), bootstrap_connection, setup)
    dht2 = DHT(("0.0.0.0", 10002), bootstrap_connection, setup)
    dht3 = DHT(("0.0.0.0", 10003), bootstrap_connection, setup)
    dht4 = DHT(("0.0.0.0", 10004), ("localhost", 10003), setup)
    dht5 = DHT(("0.0.0.0", 10005), ("localhost", 10003), setup)
    dht6 = DHT(("0.0.0.0", 10006), ("localhost", 10005), setup)

    log.critical('starting "ping" test')
    log.critical("ping: dht1 -> bootstrap = %r" % dht1.dht_ping(bootstrap_connection))
    log.critical("ping: dht6 -> bootstrap = %r" % dht6.dht_ping(bootstrap_connection))

    log.critical('starting "find_node" test')
    for idx, node in enumerate(dht3.dht_find_node(dht1._node.id)):
        log.critical(
            "find_node: dht3 -> id(dht1) result #%d: %s:%d" % (idx, node[0], node[1])
        )
        if idx > 10:
            break

    import binascii

    info_hash = binascii.unhexlify(
        "ae3fa25614b753118931373f8feae64f3c75f5cd"
    )  # Ubuntu 15.10 info hash

    log.critical('starting "get_peers" test')
    for idx, peer in enumerate(dht5.dht_get_peers(info_hash)):
        log.critical("get_peers: dht5 -> info_hash result #%d: %r" % (idx, peer))

    log.critical('starting "announce_peer" test')
    for idx, async_result in enumerate(dht5.dht_announce_peer(info_hash)):
        log.critical(
            "announce_peer: dht2 -> close_nodes(info_hash) #%d: %r"
            % (idx, async_result.get_result(1))
        )

    log.critical('starting "get_peers" test')
    for idx, peer in enumerate(dht1.dht_get_peers(info_hash)):
        log.critical("get_peers: dht1 -> info_hash result #%d: %r" % (idx, peer))

    for dht in [dht1, dht2, dht3, dht4, dht5, dht6]:
        dht.shutdown()
