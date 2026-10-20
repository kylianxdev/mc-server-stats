"""The weekly recap for the game chat: "Player of the week: ...".

    python3 -m mcstats --config config.toml --recap      # prints the message (a tellraw JSON text)

extras/weekly-recap.sh sends it to the chat, e.g. every Sunday evening.
"""
from __future__ import annotations

import json

TEXT = {
    "en": ("🏆 Player of the week: ", "+{xp} site XP, {mined} blocks mined and {kills} mobs defeated!", "[See the stats]"),
    "nl": ("🏆 Speler van de week: ", "+{xp} site-XP, {mined} blokken gemijnd en {kills} mobs verslagen!", "[Bekijk de stats]"),
    "es": ("🏆 Jugador de la semana: ", "+{xp} XP web, {mined} bloques minados y {kills} criaturas derrotadas", "[Ver estadísticas]"),
    "de": ("🏆 Spieler der Woche: ", "+{xp} Seiten-XP, {mined} Blöcke abgebaut und {kills} Kreaturen besiegt!", "[Statistiken ansehen]"),
    "fr": ("🏆 Joueur de la semaine : ", "+{xp} XP site, {mined} blocs minés et {kills} créatures vaincues !", "[Voir les stats]"),
}


def recap(data: dict, lang: str, url: str = "") -> str | None:
    """A tellraw text for the player with the most site XP gained this week, or None without history."""
    week = data["history"]["week"]
    if not week["players"] or week["since"] == data["history"]["dates"][-1]:
        return None
    best, nums = max(week["players"].items(), key=lambda kv: kv[1].get("xp", 0))
    if nums.get("xp", 0) <= 0:
        return None
    head, body, link = TEXT.get(lang, TEXT["en"])
    fmt = lambda v: f"{int(v):,}".replace(",", "." if lang in ("nl", "es", "de") else ",")
    parts = [{"text": head, "color": "gold"}, {"text": best + " ", "color": "yellow", "bold": True},
             {"text": body.format(xp=fmt(nums["xp"]), mined=fmt(nums.get("blocks_mined", 0)), kills=fmt(nums.get("mob_kills", 0))) + " ",
              "color": "white"}]
    if url:
        parts.append({"text": link, "color": "green", "underlined": True,
                      "click_event": {"action": "open_url", "url": url}, "hover_event": {"action": "show_text", "value": url}})
    return json.dumps(parts, ensure_ascii=False)
