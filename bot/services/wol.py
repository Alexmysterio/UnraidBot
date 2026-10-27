"""Wake-on-LAN."""

from __future__ import annotations

import asyncio
import re
import socket


def normalize_mac(mac: str) -> str:
    clean = re.sub(r"[^0-9A-Fa-f]", "", mac)
    if len(clean) != 12:
        raise ValueError("MAC inválida")
    return clean.upper()


def _packet(mac: str) -> bytes:
    raw = bytes.fromhex(normalize_mac(mac))
    return b"\xff" * 6 + raw * 16


def send_magic_packet(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    packet = _packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, port))


async def wake(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    await asyncio.to_thread(send_magic_packet, mac, broadcast, port)
