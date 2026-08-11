from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from .models import DashboardState, Trends


class HistoryStore:
    def __init__(self, state_dir: str, retention_days: int = 90):
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "history.sqlite3"
        self.retention_days = retention_days
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    ts REAL PRIMARY KEY,
                    temperature_c REAL,
                    humidity_pct REAL,
                    pressure_hpa REAL,
                    ups_pct REAL,
                    battery_voltage_v REAL,
                    cpu_temp_c REAL,
                    cpu_pct REAL,
                    ram_pct REAL,
                    disk_free_pct REAL,
                    hailo_ok INTEGER,
                    camera_ok INTEGER
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS samples_ts_idx ON samples(ts)")

    def add(self, state: DashboardState):
        ts = datetime.fromisoformat(state.timestamp).timestamp()
        with self._connect() as db:
            db.execute("""
                INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                state.sense.temperature_c,
                state.sense.humidity_pct,
                state.sense.pressure_hpa,
                state.ups.battery_pct,
                state.ups.battery_voltage_v,
                state.system.cpu_temp_c,
                state.system.cpu_pct,
                state.system.ram_pct,
                state.system.disk_free_pct,
                _boolint(state.health.hailo),
                _boolint(state.health.camera),
            ))
            cutoff = datetime.now(timezone.utc).timestamp() - self.retention_days * 86400
            db.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))

    def _delta(self, column: str, hours: float, current: float | None) -> float | None:
        if current is None:
            return None
        target = datetime.now(timezone.utc).timestamp() - hours * 3600
        with self._connect() as db:
            row = db.execute(
                f"""SELECT {column} FROM samples
                    WHERE ts <= ? AND {column} IS NOT NULL
                    ORDER BY ts DESC LIMIT 1""",
                (target,),
            ).fetchone()
        if not row or row[0] is None:
            return None
        return current - float(row[0])

    def trends(self, state: DashboardState) -> Trends:
        return Trends(
            pressure_1h=self._delta("pressure_hpa", 1, state.sense.pressure_hpa),
            pressure_6h=self._delta("pressure_hpa", 6, state.sense.pressure_hpa),
            pressure_24h=self._delta("pressure_hpa", 24, state.sense.pressure_hpa),
            temperature_6h=self._delta("temperature_c", 6, state.sense.temperature_c),
            temperature_24h=self._delta("temperature_c", 24, state.sense.temperature_c),
        )


def _boolint(value):
    if value is None:
        return None
    return 1 if value else 0
