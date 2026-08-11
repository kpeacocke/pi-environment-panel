from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import load_config
from .app import PanelApp
from .layout import build_plan
from .preview import render_png
from .epaper import WaveshareUART, frame


def _epaper(cfg):
    return WaveshareUART(
        device=cfg.panel.serial_device,
        baud=cfg.panel.baud,
        wake_gpio=cfg.panel.wake_gpio,
        reset_gpio=cfg.panel.reset_gpio,
        english_font_command=cfg.panel.english_font_command,
    )


def cmd_snapshot(args):
    cfg = load_config(args.config)
    app = PanelApp(cfg)
    state = app.snapshot(force_health=True)
    app.write_snapshot(state)
    print(json.dumps(state.to_dict(), indent=2))


def cmd_preview(args):
    cfg = load_config(args.config)
    app = PanelApp(cfg)
    state = app.snapshot(force_health=True)
    app.write_snapshot(state)
    plan = build_plan(state, cfg)
    render_png(plan, args.output)
    print(args.output)


def cmd_probe(args):
    cfg = load_config(args.config)
    with _epaper(cfg) as panel:
        ok = panel.handshake()
    if not ok:
        raise SystemExit("e-paper handshake failed: no OK response")
    print("e-paper handshake OK")



def cmd_diagnose_epaper(args):
    import grp
    import os
    import stat

    cfg = load_config(args.config)
    device = Path(cfg.panel.serial_device)

    print("=== DEVICE ===")
    print(f"configured: {device}")
    try:
        print(f"resolved:   {device.resolve(strict=True)}")
    except Exception as exc:
        print(f"resolved:   ERROR: {exc}")
    try:
        st = device.stat()
        print(f"mode:       {stat.filemode(st.st_mode)}")
        print(f"owner:      uid={st.st_uid} gid={st.st_gid}")
    except Exception as exc:
        print(f"stat:       ERROR: {exc}")

    groups = []
    for gid in os.getgroups():
        try:
            groups.append(grp.getgrgid(gid).gr_name)
        except KeyError:
            groups.append(str(gid))
    print(f"groups:     {', '.join(groups)}")

    print()
    print("=== UART OWNERSHIP ===")
    cmdline = Path("/proc/cmdline").read_text(errors="ignore").strip()
    serial_console = [x for x in cmdline.split() if x.startswith("console=serial") or "ttyAMA" in x or "ttyS" in x]
    print("serial console:", " ".join(serial_console) if serial_console else "none in /proc/cmdline")

    print()
    print("=== WAVESHARE HANDSHAKE ===")
    expected = frame(0x00)
    print("TX expected:", expected.hex(" ").upper())
    print('Expected response contains ASCII: 4F 4B ("OK")')

    # First try the documented power-on default without touching WAKE. If the
    # panel is already awake this isolates UART from GPIO.
    attempts = [
        (115200, False, "115200 / no WAKE"),
        (115200, True,  "115200 / WAKE edge"),
        # These do not change the module baud; they only listen/send the same
        # handshake at alternate host speeds to find a panel whose baud was
        # changed earlier in the current power cycle.
        (9600,   True,  "9600 / WAKE edge"),
        (57600,  True,  "57600 / WAKE edge"),
        (38400,  True,  "38400 / WAKE edge"),
        (19200,  True,  "19200 / WAKE edge"),
    ]

    found = False
    for baud, use_wake, label in attempts:
        panel = WaveshareUART(
            device=cfg.panel.serial_device,
            baud=baud,
            wake_gpio=cfg.panel.wake_gpio,
            reset_gpio=cfg.panel.reset_gpio,
            english_font_command=cfg.panel.english_font_command,
        )
        print()
        print(f"--- {label} ---")
        try:
            with panel:
                tx, rx, wake_result = panel.raw_handshake(
                    wake=use_wake,
                    strict_wake=use_wake,
                )
            print("WAKE:", wake_result[1])
            print("TX:  ", tx.hex(" ").upper())
            print("RX:  ", rx.hex(" ").upper() if rx else "<no bytes>")
            if rx:
                print("ASCII:", repr(rx.decode("ascii", errors="replace")))
            if b"OK" in rx:
                print("RESULT: PASS")
                found = True
                break
            print("RESULT: no OK")
        except Exception as exc:
            print(f"RESULT: ERROR: {type(exc).__name__}: {exc}")

    print()
    print("=== RESULT ===")
    if found:
        print("Transport is working.")
        return

    print("No UART response was received.")
    print("The command bytes are correct, so check the physical transport next:")
    print("  panel serial -> Raspberry Pi 5 dedicated UART/debug connector")
    print("  configured UART device -> /dev/ttyAMA10 for this build")
    print("  common GND")
    print("  panel power")
    print("  panel WAKE_UP -> configured GPIO")
    print("Observe whether the module state LED lights when the WAKE attempt runs.")
    raise SystemExit(2)


def cmd_display(args):
    cfg = load_config(args.config)
    app = PanelApp(cfg)
    state = app.snapshot(force_health=True)
    app.write_snapshot(state)
    plan = build_plan(state, cfg)
    with _epaper(cfg) as panel:
        if not panel.handshake():
            raise SystemExit("e-paper handshake failed: no OK response")
        panel.execute(plan)
    print("e-paper updated")


def cmd_daemon(args):
    cfg = load_config(args.config)
    app = PanelApp(cfg)
    last_refresh = 0.0
    last_overall = None

    while True:
        started = time.monotonic()
        try:
            state = app.snapshot()
            app.write_snapshot(state)
            changed = state.overall != last_overall
            due = started - last_refresh >= cfg.panel.refresh_seconds

            if changed or due:
                plan = build_plan(state, cfg)
                with _epaper(cfg) as panel:
                    if panel.handshake():
                        panel.execute(plan)
                        last_refresh = time.monotonic()
                        last_overall = state.overall
                    else:
                        print("WARN: e-paper handshake failed", flush=True)
        except Exception as exc:
            print(f"ERROR: {exc}", flush=True)

        elapsed = time.monotonic() - started
        time.sleep(max(1.0, cfg.panel.sample_seconds - elapsed))


def build_parser():
    p = argparse.ArgumentParser(description="Pi Environment Panel")
    p.add_argument("--config", help="Config TOML path")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("snapshot").set_defaults(func=cmd_snapshot)

    preview = sub.add_parser("preview")
    preview.add_argument("--output", default="dashboard.png")
    preview.set_defaults(func=cmd_preview)

    sub.add_parser("probe-epaper").set_defaults(func=cmd_probe)
    sub.add_parser("diagnose-epaper").set_defaults(func=cmd_diagnose_epaper)
    sub.add_parser("display").set_defaults(func=cmd_display)
    sub.add_parser("daemon").set_defaults(func=cmd_daemon)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
