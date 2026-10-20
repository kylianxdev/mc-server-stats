"""Who plays together, and who defeated whom."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from itertools import combinations

from .logs import TIME_FMT

BY = re.compile(r" by (\S+?)(?: using .*)?$")


def buddies(sessions: list[tuple[str, str, str | None]], now: dt.datetime | None = None) -> list[dict]:
    """Seconds every pair of players was online at the same time, most first."""
    now = now or dt.datetime.now()
    per_player: dict[str, list[tuple[dt.datetime, dt.datetime]]] = {}
    for p, start, end in sessions:
        a = dt.datetime.strptime(start, TIME_FMT)
        b = dt.datetime.strptime(end, TIME_FMT) if end else now
        if b > a:
            per_player.setdefault(p, []).append((a, b))
    out = []
    for p, q in combinations(sorted(per_player), 2):
        together = sum(max(0, (min(b1, b2) - max(a1, a2)).total_seconds())
                       for a1, b1 in per_player[p] for a2, b2 in per_player[q])
        if together >= 60:
            out.append({"a": p, "b": q, "s": int(together)})
    return sorted(out, key=lambda x: -x["s"])


def pvp(profiles: dict[str, dict]) -> list[dict]:
    """How often one player killed another, from the death messages ("... was slain by Steve")."""
    count = Counter()
    for victim, pr in profiles.items():
        for d in pr.get("deaths", []):
            if (m := BY.search(d["m"])) and m.group(1) in profiles and m.group(1) != victim:
                count[(m.group(1), victim)] += 1
    return [{"killer": k, "victim": v, "n": n} for (k, v), n in count.most_common()]
