from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from .models import DashboardState, Trends
from .collectors import sense as sense_collector
from .collectors import ups as ups_collector
from .collectors import system as system_collector
from .collectors import health as health_collector
from .collectors import weather as weather_collector
from .derive import comfort_label, overall_status
from .store import HistoryStore


class PanelApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.store = HistoryStore(cfg.panel.state_dir, cfg.panel.history_days)
        self._health = None
        self._health_at = 0.0

    def snapshot(self, force_health=False) -> DashboardState:
        sense = sense_collector.collect(self.cfg.sense)
        ups = ups_collector.collect(self.cfg.ups)
        system = system_collector.collect(self.cfg.panel.nvme_path)
        weather = weather_collector.collect(self.cfg.weather, self.cfg.panel.state_dir)

        now = time.monotonic()
        if force_health or self._health is None or now - self._health_at >= self.cfg.panel.health_seconds:
            self._health = health_collector.collect(sense.ok, ups.ok)
            self._health_at = now
        else:
            # Fast health reflects the collectors that run each sample.
            self._health.sense = sense.ok
            self._health.ups = ups.ok
        health = self._health

        state = DashboardState(
            timestamp=datetime.now().astimezone().isoformat(),
            sense=sense,
            ups=ups,
            system=system,
            health=health,
            weather=weather,
            trends=Trends(),
        )
        state.comfort = comfort_label(
            sense.temperature_c,
            sense.humidity_pct,
            self.cfg.thresholds,
        )

        self.store.add(state)
        state.trends = self.store.trends(state)
        state.overall = overall_status(state, self.cfg.thresholds)
        return state

    def write_snapshot(self, state):
        path = Path(self.cfg.panel.state_dir) / "latest.json"
        path.write_text(json.dumps(state.to_dict(), indent=2))
        return path
