"""Daily snapshots of every player's numbers, for "player of the week" and progress over time.

One JSON file per day in <data_dir>/history/. Today's file is rewritten every few minutes, so it
always holds the last numbers of the day. scripts/backfill_history.py can fill it from old backups.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

from .config import Config

TRACKED = ("blocks_mined", "mob_kills", "diamond_ore", "deaths", "walked_km")
WRITE_EVERY = 300  # seconds


def snapshot(fun: dict, progress: dict, playtime: dict) -> dict:
    rows = {r["key"]: r["values"] for r in fun["rows"]}
    return {p: {"xp": progress[p]["xp"], "playtime": playtime.get(p, 0), "advancements": progress[p].get("advancements", 0),
                **{k: rows.get(k, {}).get(p, 0) for k in TRACKED}}
            for p in fun["players"]}


class History:
    def __init__(self, cfg: Config):
        self.dir = cfg.data_dir / "history"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._written = 0.0

    def record(self, snap: dict, day: dt.date | None = None):
        if time.time() - self._written < WRITE_EVERY and day is None:
            return
        day = day or dt.date.today()
        (self.dir / f"{day.isoformat()}.json").write_text(json.dumps(snap))
        self._written = time.time()

    def load(self, days: int = 30) -> dict[str, dict]:
        files = sorted(self.dir.glob("????-??-??.json"))[-days:]
        out = {}
        for f in files:
            try:
                out[f.stem] = json.loads(f.read_text())
            except ValueError:
                pass
        return out

    def report(self, current: dict, days: int = 30) -> dict:
        """Daily series per player plus the change over the last 7 days ("this week")."""
        snaps = self.load(days)
        snaps[dt.date.today().isoformat()] = current
        dates = sorted(snaps)
        series = {p: {"xp": [snaps[d].get(p, {}).get("xp") for d in dates],
                      "playtime": [snaps[d].get(p, {}).get("playtime") for d in dates]} for p in current}
        week_ago = (dt.date.today() - dt.timedelta(days=7)).isoformat()
        base_date = max((d for d in dates if d <= week_ago), default=dates[0])
        base = snaps[base_date]
        week = {p: {k: round(v - base.get(p, {}).get(k, 0), 1) for k, v in nums.items()} for p, nums in current.items()}
        return {"dates": dates, "series": series, "week": {"since": base_date, "players": week}}
