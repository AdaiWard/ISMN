from __future__ import annotations

import ipaddress
import re
import socket

from app.core.config import get_settings


HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$")


def normalize_target(value: str) -> str:
    target = value.strip().rstrip(".").lower()
    try:
        return str(ipaddress.ip_address(target))
    except ValueError:
        if not HOSTNAME_RE.fullmatch(target):
            raise ValueError("Некорректный IP-адрес или hostname")
        return target


def resolve_addresses(target: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return {ipaddress.ip_address(target)}
    except ValueError:
        try:
            infos = socket.getaddrinfo(target, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError("Hostname не разрешается") from exc
        return {ipaddress.ip_address(info[4][0]) for info in infos}


def ensure_target_allowed(target: str) -> str:
    normalized = normalize_target(target)
    networks = [ipaddress.ip_network(item, strict=False) for item in get_settings().allowed_networks]
    addresses = resolve_addresses(normalized)
    if not addresses or any(not any(address in network for network in networks) for address in addresses):
        raise ValueError("Адрес находится вне разрешённых сетей")
    return normalized

