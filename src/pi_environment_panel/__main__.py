from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import load_config
from .app import PanelApp
from .layout import build_plan
from .preview import render_png
from .epaper import WaveshareUART


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
    sub.add_parser("display").set_defaults(func=cmd_display)
    sub.add_parser("daemon").set_defaults(func=cmd_daemon)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
