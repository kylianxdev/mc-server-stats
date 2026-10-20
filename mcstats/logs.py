"""Parse the server logs (logs/*.log.gz + latest.log) into sessions, commands, events, ...

Privacy: private messages (/msg, /tell, ...) are skipped completely, IP addresses are never
kept, and coordinates in commands/feedback are hidden (configurable).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import re
from pathlib import Path

from .config import Config

PRIVATE_COMMANDS = {"tell", "msg", "w", "whisper", "teammsg", "tm", "me"}

ADMIN_COMMANDS = {
    "op", "deop", "gamemode", "give", "tp", "teleport", "gamerule", "setworldspawn", "spawnpoint",
    "time", "weather", "kill", "effect", "enchant", "xp", "experience", "summon", "fill", "setblock",
    "clone", "execute", "whitelist", "ban", "ban-ip", "pardon", "pardon-ip", "kick", "difficulty",
    "item", "attribute", "data", "worldborder", "reload", "stop", "clear", "loot", "place",
    "forceload", "fillbiome", "tick", "locate",
}

LINE = re.compile(r"^\[(\d\d:\d\d:\d\d)\] \[([^\]]+)\]: (.*)$")
CMD = re.compile(r"^(\S+) issued server command: (/.*)$")
OP_ON = re.compile(r"^System chat: (?:\[(\S+): )?Made (\S+) a server operator\]?$")
OP_OFF = re.compile(r"^System chat: (?:\[(\S+): )?Made (\S+) no longer a server operator\]?$")
FEEDBACK = re.compile(r"^System chat: \[(\S+): (.*)\]$")
LOGIN = re.compile(r"^(\S+)\[/[^\]]+\] logged in")  # the IP inside [...] is deliberately not captured
WARN = re.compile(r"^(\S+) moved (too quickly|wrongly)!|^Can't keep up!")
WL_ADD = re.compile(r"^System chat: (?:\[(\S+): )?Added (\S+) to the whitelist\]?$")
WL_DEL = re.compile(r"^System chat: (?:\[(\S+): )?Removed (\S+) from the whitelist\]?$")
BAN = re.compile(r"^System chat: (?:\[(\S+): )?Banned (\S+): (.*?)\]?$")
JOIN = re.compile(r"^System chat: (\S+) joined the game$")
LEAVE = re.compile(r"^System chat: (\S+) left the game$")
ADV = re.compile(r"^System chat: (\S+) has (made the advancement|completed the challenge|reached the goal) \[(.+)\]$")
SYSMSG = re.compile(r"^System chat: (\S+) (.+)$")
# how vanilla death messages start (after the player name); other "System chat" lines are not deaths
DEATH = re.compile(r"^(was |died|drowned|blew up|hit the ground|fell |burned|went (up in flames|off with a bang)|tried to swim|"
                   r"walked into|experienced kinetic|suffocated|starved|froze|withered|discovered the floor|didn't want|left the confines)")
# three coordinates in a row, e.g. "-277 ~ -229" or "-299, 185, -91"
COORDS = re.compile(r"[~^]?-?\d+(?:\.\d+)?,?\s+[~^]?-?\d*(?:\.\d+)?,?\s+[~^]?-?\d+(?:\.\d+)?")
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def read_lines(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        yield from fh


def log_files(logs_dir: Path) -> list[tuple[str, int, Path]]:
    """(date, index, path) in chronological order; latest.log last."""
    files = []
    for f in logs_dir.glob("*.log.gz"):
        if m := re.match(r"(\d{4}-\d\d-\d\d)-(\d+)", f.name):
            files.append((m.group(1), int(m.group(2)), f))
    latest = logs_dir / "latest.log"
    if latest.exists():
        files.append((dt.date.fromtimestamp(latest.stat().st_mtime).isoformat(), 10**6, latest))
    return sorted(files)


def known_players(cfg: Config) -> set[str]:
    try:
        return {u["name"] for u in json.loads((cfg.minecraft_dir / "usercache.json").read_text())}
    except (OSError, ValueError):
        return set()


class LogParser:
    """Parses all logs; the result is cached until a log file changes."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.admin_commands = ADMIN_COMMANDS | set(cfg.extra_admin_commands)
        self._key = None
        self._data = None

    def hide(self, text: str) -> str:
        return COORDS.sub("[x y z]", text) if self.cfg.hide_coordinates else text

    def parse(self) -> dict:
        files = log_files(self.cfg.logs_dir)
        key = tuple((str(f), f.stat().st_mtime, f.stat().st_size) for _, _, f in files)
        if key == self._key:
            return self._data

        known = known_players(self.cfg)
        commands, ops, logins, warnings, feedback, moderation = [], [], [], [], [], []
        sessions, advancements, deaths = [], [], []
        is_op: dict[str, bool] = {}

        for day, _, path in files:
            open_sessions, last_ts = {}, None
            for raw in read_lines(path):
                m = LINE.match(raw.rstrip("\n"))
                if not m:
                    continue
                time, _thread, msg = m.groups()
                when = f"{day} {time}"
                last_ts = when

                if j := JOIN.match(msg):
                    open_sessions[j.group(1)] = when
                elif j := LEAVE.match(msg):
                    if start := open_sessions.pop(j.group(1), None):
                        sessions.append((j.group(1), start, when))
                elif a := ADV.match(msg):
                    kind = "challenge" if "challenge" in a.group(2) else "goal" if "goal" in a.group(2) else "task"
                    advancements.append({"t": when, "p": a.group(1), "a": a.group(3), "kind": kind})
                elif (s := SYSMSG.match(msg)) and s.group(1) in known and DEATH.match(s.group(2)):
                    deaths.append({"t": when, "p": s.group(1), "m": self.hide(s.group(2))})
                elif c := CMD.match(msg):
                    player, command = c.groups()
                    name = command[1:].split(" ", 1)[0].lower().removeprefix("minecraft:")
                    if name in PRIVATE_COMMANDS:
                        continue
                    admin, op_now = name in self.admin_commands, is_op.get(player, False)
                    # without operator rights an admin command does nothing: then it was only an attempt
                    commands.append({"t": when, "p": player, "c": self.hide(command),
                                     "admin": admin and op_now, "tried": admin and not op_now})
                elif o := OP_ON.match(msg):
                    is_op[o.group(2)] = True
                    ops.append({"t": when, "p": o.group(2), "by": o.group(1) or "console", "op": True})
                elif o := OP_OFF.match(msg):
                    is_op[o.group(2)] = False
                    ops.append({"t": when, "p": o.group(2), "by": o.group(1) or "console", "op": False})
                elif w := WL_ADD.match(msg):
                    moderation.append({"t": when, "p": w.group(2), "by": w.group(1) or "console", "a": "whitelist_add"})
                elif w := WL_DEL.match(msg):
                    moderation.append({"t": when, "p": w.group(2), "by": w.group(1) or "console", "a": "whitelist_remove"})
                elif b := BAN.match(msg):
                    moderation.append({"t": when, "p": b.group(2), "by": b.group(1) or "console", "a": "ban", "reason": b.group(3)})
                elif f := FEEDBACK.match(msg):
                    feedback.append({"t": when, "p": f.group(1), "m": self.hide(f.group(2))})
                elif l := LOGIN.match(msg):
                    logins.append({"t": when, "p": l.group(1)})
                elif WARN.match(msg):
                    warnings.append({"t": when, "m": msg})
            # end of a log file = server stopped: close the open sessions (latest.log: still online)
            for p, start in open_sessions.items():
                sessions.append((p, start, None if path.name == "latest.log" else last_ts))

        ops_json = _names(self.cfg.minecraft_dir / "ops.json")
        data = {
            "generated": dt.datetime.now().strftime(TIME_FMT),
            "first_log": files[0][0] if files else None,
            "current_ops": ops_json,
            "ever_ops": sorted({o["p"] for o in ops if o["op"]} | set(ops_json)),
            "whitelist": _names(self.cfg.minecraft_dir / "whitelist.json"),
            "commands": commands[::-1],
            "ops": ops[::-1],
            "logins": logins[::-1],
            "warnings": warnings[::-1],
            "feedback": feedback[::-1],
            "moderation": moderation[::-1],
            "profiles": build_profiles(sessions, advancements, deaths),
            "_sessions": sessions,  # internal, used for "who plays together"; not published
        }
        self._key, self._data = key, data
        return data


def _names(path: Path) -> list[str]:
    try:
        return [e["name"] for e in json.loads(path.read_text())]
    except (OSError, ValueError, KeyError):
        return []


def build_profiles(sessions, advancements, deaths, now: dt.datetime | None = None) -> dict:
    """Per player: sessions, playtime per day and per hour of day, advancements and deaths."""
    now = now or dt.datetime.now()
    out: dict[str, dict] = {}
    for p, start, end in sessions:
        a = dt.datetime.strptime(start, TIME_FMT)
        b = dt.datetime.strptime(end, TIME_FMT) if end else now
        if b < a:
            continue
        pr = out.setdefault(p, {"sessions": 0, "longest": 0, "first": start, "last": start,
                                "per_day": {}, "per_hour": [0] * 24, "online": False})
        pr["sessions"] += 1
        pr["longest"] = max(pr["longest"], int((b - a).total_seconds()))
        pr["first"] = min(pr["first"], start)
        pr["last"] = max(pr["last"], end or now.strftime(TIME_FMT))
        pr["online"] = pr["online"] or end is None
        t = a
        while t < b:  # spread per minute over days and hours
            step = min(b, t.replace(second=0, microsecond=0) + dt.timedelta(minutes=1))
            sec = (step - t).total_seconds()
            day = t.strftime("%Y-%m-%d")
            pr["per_day"][day] = pr["per_day"].get(day, 0) + sec
            pr["per_hour"][t.hour] += sec
            t = step
    for p, pr in out.items():
        pr["per_day"] = {d: int(v) for d, v in sorted(pr["per_day"].items())}
        pr["per_hour"] = [int(v) for v in pr["per_hour"]]
        pr["advancements"] = [x for x in advancements if x["p"] == p][::-1]
        pr["deaths"] = [x for x in deaths if x["p"] == p][::-1]
    return out
