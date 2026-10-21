"""Server milestones: what everyone reached together ("1.000 diamonds mined together!").

The totals of all players are checked every minute. A milestone is a round number (100, 200, 500,
1.000, 2.000, 5.000, ...) above a starting point per statistic. A new one is shown on the website and,
when a console is configured, announced in the game chat with the advancement sound.

The first run only writes down what was already reached, so an existing server doesn't get a flood
of messages.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import subprocess
import threading

from .config import Config

log = logging.getLogger(__name__)

# statistic -> (first milestone, icon on the website, in the chat)
MILESTONES = {
    "diamond_ore": (100, "block/diamond_ore", "💎"),
    "ancient_debris": (50, "block/ancient_debris_side", "🔥"),
    "blocks_mined": (10_000, "item/diamond_pickaxe", "⛏"),
    "blocks_used": (10_000, "block/bricks", "🏠"),
    "items_crafted": (10_000, "block/crafting_table_front", "🔨"),
    "logs_chopped": (1_000, "block/oak_log", "🪓"),
    "crops_harvested": (1_000, "item/wheat", "🌾"),
    "animals_bred": (100, "item/lead", "🐄"),
    "mob_kills": (1_000, "item/iron_sword", "⚔"),
    "villager_trades": (500, "item/emerald", "💰"),
    "items_enchanted": (50, "item/enchanted_book", "✨"),
    "fish_caught": (50, "item/fishing_rod", "🎣"),
    "times_slept": (100, "block/red_bed_head_up", "🛏"),
    "walked_km": (100, "item/leather_boots", "👣"),
    "deaths": (50, "item/totem_of_undying", "💀"),
    "playtime_h": (100, "item/clock_00", "⏰"),
}


def level(value: float, start: int) -> int:
    """The highest round number (1, 2, 5 times a power of ten) reached, from start on; 0 below start."""
    if value < start:
        return 0
    best, n = start, start
    while n <= value:
        best = n
        n = next_round(n)
    return best


def next_round(n: int) -> int:
    """100 -> 200 -> 500 -> 1000 -> ..."""
    digits = len(str(n)) - 1
    lead = n // 10 ** digits
    return {1: 2, 2: 5}.get(lead, 10) * 10 ** digits


def totals(fun: dict, times: dict) -> dict[str, tuple[float, str | None, float]]:
    """statistic -> (everyone together, the player with the most, their amount)."""
    rows = {r["key"]: r["values"] for r in fun.get("rows", [])}
    rows["playtime_h"] = {p: s / 3600 for p, s in times.items()}
    out = {}
    for key in MILESTONES:
        values = {p: v for p, v in rows.get(key, {}).items() if isinstance(v, (int, float))}
        top = max(values.items(), key=lambda kv: kv[1], default=(None, 0))
        out[key] = (sum(values.values()), *top)
    return out


class Milestones:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.file = cfg.data_dir / "milestones.json"
        self.lock = threading.Lock()
        try:
            self.state = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = None  # first run: write down, don't announce

    def check(self, fun: dict, times: dict, online: set[str]) -> None:
        """Note (and announce) the milestones reached since the last check."""
        now = totals(fun, times)
        with self.lock:
            first = self.state is None
            state = self.state or {"reached": {}, "log": []}
            new = []
            for key, (value, top, top_value) in now.items():
                n = level(value, MILESTONES[key][0])
                if n > state["reached"].get(key, 0):
                    state["reached"][key] = n
                    # only the highest new one per statistic: no flood after a pause.
                    # On the first run without a time: reached before this was installed
                    entry = {"key": key, "n": n, "t": None if first else dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             "top": top, "top_n": round(top_value)}
                    state["log"].append(entry)
                    if not first:
                        new.append(entry)
            state["log"] = state["log"][-50:]
            changed = first or new
            self.state = state
            if changed:
                self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
                self.file.write_text(json.dumps(state, indent=1), encoding="utf-8")
        if new and online:
            threading.Thread(target=self.announce, args=(new,), daemon=True).start()

    def report(self, fun: dict, times: dict) -> dict:
        """For the website: the milestones reached (newest first) and how far everyone is to the next."""
        now = totals(fun, times)
        state = self.state or {"reached": {}, "log": []}
        progress = []
        for key, (value, *_) in now.items():
            start = MILESTONES[key][0]
            n = level(value, start)
            nxt = next_round(n) if n else start
            progress.append({"key": key, "icon": MILESTONES[key][1], "value": round(value, 1), "reached": n, "next": nxt})
        return {"log": sorted(state["log"], key=lambda e: e["t"] or "", reverse=True)[:12], "progress": progress}

    # ---------- the game chat ----------
    def announce(self, entries: list[dict]) -> None:
        if not self.cfg.console_tmux:
            return
        texts = chat_texts(self.cfg)
        for e in entries:
            self.console(f"tellraw @a {message(e, texts, self.cfg.default_language)}")
            self.console("execute as @a at @s run playsound minecraft:ui.toast.challenge_complete master @s ~ ~ ~ 0.6")

    def console(self, command: str) -> None:
        """Type a command into the server console (the tmux session it runs in)."""
        session = self.cfg.console_tmux
        try:
            subprocess.run(["tmux", "send-keys", "-t", session, "-l", command], check=True, timeout=5)
            subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], check=True, timeout=5)
        except (OSError, subprocess.SubprocessError) as e:
            log.warning("could not send a milestone to the console: %s", e)


def chat_texts(cfg: Config) -> dict:
    """The milestone texts of the website, in its default language (English for what's missing)."""
    texts = {}
    for lang in ("en", cfg.default_language):
        try:
            texts.update(json.loads((cfg.web_dir / "i18n" / f"{lang}.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return texts


def fmt(n: float, lang: str) -> str:
    return f"{int(n):,}".replace(",", "." if lang in ("nl", "es", "de") else ",")


def message(e: dict, texts: dict, lang: str) -> str:
    """A tellraw text: ⭐ Together! You all mined 1.000 diamonds 💎  (hover: who did the most)."""
    what = texts.get(f"together.{e['key']}", e["key"]).replace("{n}", fmt(e["n"], lang))
    parts = [{"text": "⭐ " + texts.get("together.chat", "Together!") + " ", "color": "gold", "bold": True},
             {"text": texts.get("together.line", "{what}").replace("{what}", what) + " " + MILESTONES[e["key"]][2], "color": "yellow"}]
    if e.get("top"):
        top = texts.get("together.top", "Most: {p} ({n})").replace("{p}", e["top"]).replace("{n}", fmt(e["top_n"], lang))
        parts.append({"text": " " + top, "color": "gray"})
    return json.dumps(parts, ensure_ascii=False)
