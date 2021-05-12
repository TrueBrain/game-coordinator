import ipaddress

from .enums import Family


def ip_to_str(ip):
    if isinstance(ip, ipaddress.IPv4Address):
        return f"{ip}"
    elif isinstance(ip, ipaddress.IPv6Address):
        return f"[{ip}]"
    raise NotImplementedError


def get_family(ip):
    if isinstance(ip, ipaddress.IPv4Address):
        return Family.IPv4
    else:
        return Family.IPv6
