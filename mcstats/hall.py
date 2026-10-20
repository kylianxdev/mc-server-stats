"""Hall of Fame: who was the first to reach the big milestones."""
from __future__ import annotations

# (key, advancement id) in the order they usually happen
MILESTONES = [
    ("first_iron", "story/smelt_iron"),
    ("first_diamond", "story/mine_diamond"),
    ("first_nether", "story/enter_the_nether"),
    ("first_enchant", "story/enchant_item"),
    ("first_fortress", "nether/find_fortress"),
    ("first_debris", "nether/obtain_ancient_debris"),
    ("first_netherite_armor", "nether/netherite_armor"),
    ("first_end", "story/enter_the_end"),
    ("first_dragon", "end/kill_dragon"),
    ("first_elytra", "end/elytra"),
    ("first_totem", "adventure/totem_of_undying"),
    ("first_raid", "adventure/hero_of_the_village"),
    ("first_wither", "nether/summon_wither"),
]


def hall_of_fame(adv_times: dict[str, dict[str, str]], profiles: dict[str, dict]) -> list[dict]:
    """For every milestone: who did it first, and when."""
    out = []
    joins = [(pr["first"], p) for p, pr in profiles.items() if pr.get("first")]
    if joins:
        t, p = min(joins)
        out.append({"key": "first_join", "p": p, "t": t})
    for key, adv in MILESTONES:
        done = [(times[adv], p) for p, times in adv_times.items() if times.get(adv)]
        if done:
            t, p = min(done)
            out.append({"key": key, "p": p, "t": t, "adv": adv, "n": len(done)})
    deaths = [(d["t"], p) for p, pr in profiles.items() for d in pr.get("deaths", [])]
    if deaths:
        t, p = min(deaths)
        out.append({"key": "first_death", "p": p, "t": t})
    return sorted(out, key=lambda x: x["t"])
