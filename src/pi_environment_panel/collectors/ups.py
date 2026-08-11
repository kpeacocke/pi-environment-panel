from __future__ import annotations

from ..models import UPSReading


# Waveshare UPS HAT (E) register map.
REG_VBUS_MV = 0x10
REG_BATTERY_MV = 0x20
REG_BATTERY_CURRENT_MA = 0x22
REG_BATTERY_PERCENT = 0x24
REG_REMAINING_MIN = 0x28


def _u16(bus, address: int, reg: int) -> int:
    lo = bus.read_byte_data(address, reg)
    hi = bus.read_byte_data(address, reg + 1)
    return lo | (hi << 8)


def _s16(bus, address: int, reg: int) -> int:
    value = _u16(bus, address, reg)
    return value - 0x10000 if value & 0x8000 else value


def collect(cfg) -> UPSReading:
    if not cfg.enabled:
        return UPSReading(error="disabled")

    try:
        from smbus import SMBus
        with SMBus(cfg.bus) as bus:
            vbus_mv = _u16(bus, cfg.address, REG_VBUS_MV)
            battery_mv = _u16(bus, cfg.address, REG_BATTERY_MV)
            current_ma = _s16(bus, cfg.address, REG_BATTERY_CURRENT_MA)
            percent = _u16(bus, cfg.address, REG_BATTERY_PERCENT)
            remaining = _u16(bus, cfg.address, REG_REMAINING_MIN)

        # Treat 4.0 V as a conservative "external VBUS is present" threshold.
        mains = vbus_mv >= 4000

        # The module returns integer percent/minutes; clamp obviously corrupt values.
        pct = float(percent) if 0 <= percent <= 100 else None
        mins = int(remaining) if 0 <= remaining <= 65534 else None

        return UPSReading(
            ok=True,
            mains=mains,
            vbus_voltage_v=vbus_mv / 1000.0,
            battery_voltage_v=battery_mv / 1000.0,
            battery_current_ma=current_ma,
            battery_pct=pct,
            remaining_minutes=mins,
        )
    except Exception as exc:
        return UPSReading(ok=False, error=str(exc))
