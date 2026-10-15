from __future__ import annotations

import asyncio
import math
import platform
import re
from dataclasses import dataclass


@dataclass(slots=True)
class PingResult:
    success: bool
    latency_ms: float | None
    packet_loss: float
    detail: str


LATENCY_PATTERNS = (
    re.compile(r"(?:time|время)[=<]\s*(\d+(?:[.,]\d+)?)\s*(?:ms|мс)", re.IGNORECASE),
    re.compile(r"=\s*[\d.]+/([\d.]+)/[\d.]+/[\d.]+\s*ms", re.IGNORECASE),
)


def build_ping_command(target: str, timeout_seconds: float, count: int = 2) -> list[str]:
    if platform.system().lower() == "windows":
        return ["ping", "-n", str(count), "-w", str(int(timeout_seconds * 1000)), target]
    return ["ping", "-c", str(count), "-W", str(max(1, math.ceil(timeout_seconds))), target]


def parse_ping_output(returncode: int, output: str, count: int = 2) -> PingResult:
    matches: list[float] = []
    for pattern in LATENCY_PATTERNS:
        found = pattern.findall(output)
        if found:
            matches = [float(value.replace(",", ".")) for value in found]
            break
    received = len(matches)
    if returncode == 0 and received == 0:
        received = count
    loss = max(0.0, min(100.0, (count - received) * 100.0 / count))
    success = returncode == 0
    latency = sum(matches) / len(matches) if matches else None
    detail = "ICMP-ответ получен" if success else "ICMP-ответ не получен; блокировка ICMP не доказывает отключение устройства"
    return PingResult(success, latency, loss, detail)


async def ping(target: str, timeout_seconds: float = 2.0, count: int = 2) -> PingResult:
    command = build_ping_command(target, timeout_seconds, count)
    kwargs = {}
    if platform.system().lower() == "windows":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            **kwargs,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds * count + 2)
        output = stdout.decode("oem" if platform.system().lower() == "windows" else "utf-8", errors="replace")
        return parse_ping_output(process.returncode or 0, output, count)
    except asyncio.TimeoutError:
        if "process" in locals():
            process.kill()
            await process.wait()
        return PingResult(False, None, 100.0, "Тайм-аут ICMP; блокировка ICMP не доказывает отключение устройства")
    except FileNotFoundError:
        return PingResult(False, None, 100.0, "Системная утилита ping не найдена")

