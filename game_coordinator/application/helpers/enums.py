import enum


class ConnectType(enum.Enum):
    UNKNOWN = "unknown"
    DIRECT = "direct"
    STUN = "STUN"
    TURN = "TURN"


class Family(enum.Enum):
    UNKNOWN = "unknown"
    IPv4 = "IPv4"
    IPv6 = "IPv6"
