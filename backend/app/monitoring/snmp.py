from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SnmpResult:
    success: bool
    values: dict[str, float | str] = field(default_factory=dict)
    detail: str = ""


async def collect_snmp_v3(*, target: str, username: str, auth_key: str, priv_key: str, timeout: float = 3.0) -> SnmpResult:
    """Read conservative standard OIDs with SNMPv3 authPriv.

    Import is local so ICMP-only installations remain usable if the optional driver
    cannot initialize on a platform. Device-specific CPU/RAM OIDs are intentionally
    not guessed.
    """
    try:
        from pysnmp.hlapi.v3arch.asyncio import (
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            UsmUserData,
            get_cmd,
            usmAesCfb128Protocol,
            usmHMACSHAAuthProtocol,
        )
    except (ImportError, AttributeError) as exc:
        return SnmpResult(False, detail=f"SNMP-драйвер недоступен: {type(exc).__name__}")

    engine = SnmpEngine()
    try:
        transport = await UdpTransportTarget.create((target, 161), timeout=timeout, retries=0)
        error_indication, error_status, _, var_binds = await get_cmd(
            engine,
            UsmUserData(
                username,
                authKey=auth_key,
                privKey=priv_key,
                authProtocol=usmHMACSHAAuthProtocol,
                privProtocol=usmAesCfb128Protocol,
            ),
            transport,
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")),  # sysName
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.3.0")),  # sysUpTime
        )
        if error_indication:
            return SnmpResult(False, detail=f"SNMP недоступен: {error_indication}")
        if error_status:
            return SnmpResult(False, detail=f"SNMP ошибка: {error_status.prettyPrint()}")
        values = {
            "sys_name": var_binds[0][1].prettyPrint(),
            "uptime_ticks": float(var_binds[1][1]),
        }
        return SnmpResult(True, values=values, detail="SNMPv3 authPriv: стандартные OID получены")
    except Exception as exc:
        return SnmpResult(False, detail=f"SNMP запрос завершился ошибкой: {type(exc).__name__}")
    finally:
        engine.close_dispatcher()


def counter_rate(previous: int, current: int, seconds: float, bits: int = 64) -> float | None:
    if seconds <= 0:
        return None
    if current >= previous:
        delta = current - previous
    else:
        maximum = 2**bits
        delta = maximum - previous + current
        if delta > maximum // 2:
            return None
    return delta / seconds

