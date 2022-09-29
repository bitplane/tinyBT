import socket
import time

from utils import decode_id, decode_uint32, encode_ip, encode_uint32
from utils.crc32c import crc32c


def bep42_prefix(ip: str, crc32_salt, first_node_bits):
    """
    BEP #0042 - prefix is based on ip and last byte of the node id - 21 most significant bits must match
    ip = ip address in string format eg. "127.0.0.1"
    """
    # first_node_bits determines the last 3 bits

    ip_asint = decode_uint32(encode_ip(ip))
    value = crc32c(
        bytearray(encode_uint32((ip_asint & 0x030F3FFF) | ((crc32_salt & 0x7) << 29)))
    )
    return (value & 0xFFFFF800) | ((first_node_bits << 8) & 0x00000700)


def valid_id(node_id, connection) -> bool:
    node_id = bytearray(node_id)
    vprefix = bep42_prefix(connection[0], node_id[-1], 0)
    return ((vprefix ^ decode_uint32(node_id[:4])) & 0xFFFFF800) == 0


class DHT_Node:
    """
    Represents a node in the DHT table
    """

    def __init__(self, connection, id, version=None):
        self.connection = (socket.gethostbyname(connection[0]), connection[1])
        self.set_id(id)
        self.version = version
        self.tokens = {}  # tokens to gain write access to self.values
        self.values = {}
        self.attempt = 0
        self.pending = 0
        self.last_ping = 0

    def set_id(self, id):
        self.id = id
        self.id_cmp = decode_id(id)

    def __repr__(self):
        return "id:%s con:%15s:%-5d v:%20s c:%5s last:%.2f" % (
            hex(self.id_cmp),
            self.connection[0],
            self.connection[1],
            repr(self.version),
            valid_id(self.id, self.connection),
            time.time() - self.last_ping,
        )
