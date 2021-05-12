HUMAN_ENCODE_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNQRSTUVWXYZ23456789"
HUMAN_ENCODE_BASE = len(HUMAN_ENCODE_CHARS)


def human_encode(b):
    value = int.from_bytes(b, "big")

    result = ""
    while value:
        result += HUMAN_ENCODE_CHARS[value % HUMAN_ENCODE_BASE]
        value //= HUMAN_ENCODE_BASE

    return result
