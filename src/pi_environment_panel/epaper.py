from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable


TRAILER = bytes([0xCC, 0x33, 0xC3, 0x3C])


def xor_parity(data: bytes) -> int:
    value = 0
    for b in data:
        value ^= b
    return value


def frame(command: int, payload: bytes = b"") -> bytes:
    # header + len(2) + cmd + payload + trailer(4) + parity
    length = 9 + len(payload)
    core = bytes([0xA5]) + length.to_bytes(2, "big") + bytes([command]) + payload + TRAILER
    return core + bytes([xor_parity(core)])


def u16(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(value)
    return value.to_bytes(2, "big")


class WaveshareUART:
    def __init__(
        self,
        device="/dev/ttyAMA10",
        baud=115200,
        wake_gpio=22,
        reset_gpio=17,
        english_font_command=0x1E,
    ):
        self.device = device
        self.baud = baud
        self.wake_gpio = wake_gpio
        self.reset_gpio = reset_gpio
        self.english_font_command = english_font_command
        self._serial = None

    def open(self):
        import serial
        self._serial = serial.Serial(self.device, self.baud, timeout=0.15, write_timeout=2.0, exclusive=True)
        return self

    def close(self):
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *_):
        self.close()

    def wake(self, strict: bool = False):
        """Generate the documented rising edge on WAKE_UP.

        Returns (ok, detail).  In normal display operation a wake GPIO failure
        does not prevent trying the UART because an already-awake panel may
        still respond.  Diagnostic mode sets strict=True so the actual error is
        surfaced instead of being hidden.
        """
        pin = None
        try:
            from gpiozero import OutputDevice
            pin = OutputDevice(
                self.wake_gpio,
                active_high=True,
                initial_value=False,
            )
            pin.off()
            time.sleep(0.10)
            pin.on()  # Waveshare documents a rising edge as the wake event.
            time.sleep(0.50)
            return True, f"GPIO{self.wake_gpio} low->high"
        except Exception as exc:
            if strict:
                raise
            return False, f"{type(exc).__name__}: {exc}"
        finally:
            if pin is not None:
                pin.close()

    def reset(self):
        from gpiozero import OutputDevice
        pin = OutputDevice(self.reset_gpio, active_high=True, initial_value=True)
        pin.off()
        time.sleep(0.1)
        pin.on()
        time.sleep(0.5)
        pin.close()

    def send(self, command: int, payload: bytes = b"", settle=0.03):
        if self._serial is None:
            raise RuntimeError("serial device is not open")
        self._serial.write(frame(command, payload))
        self._serial.flush()
        time.sleep(settle)

    def handshake(self) -> bool:
        """Handshake with an already-awake panel first.

        The physical panel on this Pi normally remains awake (state LED on).
        Toggling WAKE before every command is unnecessary and can interfere
        with a working UART session if the auxiliary GPIO wiring differs from
        our assumed WAKE mapping.

        Try the UART exactly as-is first. Only if that receives no OK response
        do we generate the configured WAKE edge and retry once.
        """
        if self._serial is None:
            raise RuntimeError("serial device is not open")

        def attempt() -> bool:
            self._serial.reset_input_buffer()
            self.send(0x00, settle=0.15)
            deadline = time.monotonic() + 1.5
            data = bytearray()
            while time.monotonic() < deadline:
                waiting = self._serial.in_waiting
                if waiting:
                    data.extend(self._serial.read(waiting))
                    if b"OK" in data:
                        return True
                else:
                    time.sleep(0.02)
            return False

        # Primary path: the panel is already awake.
        if attempt():
            return True

        # Fallback only: try the configured WAKE line, then re-handshake.
        self.wake()
        return attempt()

    def read_response(self, seconds: float = 1.5) -> bytes:
        if self._serial is None:
            raise RuntimeError("serial device is not open")
        deadline = time.monotonic() + seconds
        data = bytearray()
        while time.monotonic() < deadline:
            waiting = self._serial.in_waiting
            if waiting:
                data.extend(self._serial.read(waiting))
                # A valid handshake response is ASCII OK. Keep a little margin
                # to capture any surrounding bytes rather than stopping at O.
                if b"OK" in data:
                    time.sleep(0.05)
                    waiting = self._serial.in_waiting
                    if waiting:
                        data.extend(self._serial.read(waiting))
                    break
            else:
                time.sleep(0.02)
        return bytes(data)

    def raw_handshake(self, wake: bool = True, strict_wake: bool = False):
        if self._serial is None:
            raise RuntimeError("serial device is not open")
        wake_result = (None, "not requested")
        if wake:
            wake_result = self.wake(strict=strict_wake)
        self._serial.reset_input_buffer()
        tx = frame(0x00)
        self._serial.write(tx)
        self._serial.flush()
        rx = self.read_response(2.0)
        return tx, rx, wake_result

    def clear(self):
        self.send(0x2E, settle=0.08)

    def refresh(self):
        self.send(0x0A, settle=2.0)

    def set_english_font(self, size: int):
        mapping = {32: 1, 48: 2, 64: 3}
        if size not in mapping:
            raise ValueError("Waveshare native English font supports 32, 48 or 64")
        self.send(self.english_font_command, bytes([mapping[size]]))

    def line(self, x1, y1, x2, y2):
        payload = u16(x1) + u16(y1) + u16(x2) + u16(y2)
        self.send(0x22, payload)

    def fill_rect(self, x1, y1, x2, y2):
        payload = u16(x1) + u16(y1) + u16(x2) + u16(y2)
        self.send(0x24, payload)

    def text(self, x: int, y: int, text: str, size=32):
        self.set_english_font(size)
        clean = text.encode("ascii", errors="replace") + b"\x00"
        payload = u16(x) + u16(y) + clean
        self.send(0x30, payload)

    def execute(self, plan):
        self.clear()
        current_font = None
        for op in plan.operations:
            if op.kind == "text":
                if op.size != current_font:
                    self.set_english_font(op.size)
                    current_font = op.size
                clean = op.text.encode("ascii", errors="replace") + b"\x00"
                self.send(0x30, u16(op.x1) + u16(op.y1) + clean)
            elif op.kind == "line":
                self.line(op.x1, op.y1, op.x2, op.y2)
            elif op.kind == "fill_rect":
                self.fill_rect(op.x1, op.y1, op.x2, op.y2)
        self.refresh()
