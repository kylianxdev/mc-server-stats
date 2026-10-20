#!/usr/bin/env python3
"""Download the textures and translations the website needs, straight from Mojang.

Minecraft's textures and language files belong to Mojang and are not part of this repository.
This script downloads the official client for your server's version (checksum verified),
extracts only what the website uses into assets/, and also fetches the 3D skin viewer.

    python3 scripts/fetch_assets.py --config config.toml
    python3 scripts/fetch_assets.py --version 1.21.10 --out assets
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mcstats import config  # noqa: E402

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES = "https://resources.download.minecraft.net/{}/{}"
SKINVIEW3D = "https://cdn.jsdelivr.net/npm/skinview3d@3.4.2/bundles/skinview3d.bundle.js"
LANG_CODES = {"en": "en_us", "nl": "nl_nl", "es": "es_es", "de": "de_de", "fr": "fr_fr", "pt": "pt_br",
              "it": "it_it", "pl": "pl_pl", "sv": "sv_se", "da": "da_dk", "tr": "tr_tr", "cs": "cs_cz"}
LANG_KEYS = ("entity.minecraft.", "item.minecraft.", "block.minecraft.", "enchantment.minecraft.",
             "trim_pattern.minecraft.", "trim_material.minecraft.", "advancements.", "death.")

TEX = "assets/minecraft/textures/"
SPRITES = {  # sprite in the client -> path on the website
    "gui/sprites/widget/button.png": "gui/widget/button.png",
    "gui/sprites/widget/button_highlighted.png": "gui/widget/button_highlighted.png",
    "gui/sprites/hud/heart/full.png": "gui/hud/heart/full.png",
    "gui/sprites/hud/experience_bar_background.png": "gui/hud/experience_bar_background.png",
    "gui/sprites/hud/experience_bar_progress.png": "gui/hud/experience_bar_progress.png",
    "gui/sprites/advancements/task_frame_obtained.png": "gui/advancements/task_frame_obtained.png",
    "gui/sprites/advancements/goal_frame_obtained.png": "gui/advancements/goal_frame_obtained.png",
    "gui/sprites/advancements/challenge_frame_obtained.png": "gui/advancements/challenge_frame_obtained.png",
    "gui/sprites/advancements/task_frame_unobtained.png": "gui/advancements/task_frame_unobtained.png",
    "gui/sprites/advancements/goal_frame_unobtained.png": "gui/advancements/goal_frame_unobtained.png",
    "gui/sprites/advancements/challenge_frame_unobtained.png": "gui/advancements/challenge_frame_unobtained.png",
}
FOLDERS = ("entity/equipment/humanoid/", "entity/equipment/humanoid_leggings/", "entity/equipment/wings/",
           "trims/entity/humanoid/", "trims/entity/humanoid_leggings/", "palettes/", "entity/player/", "environment/")


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def get_json(url: str):
    return json.loads(get(url))


def detect_version(mc_dir: Path) -> str | None:
    """The version of the server in mc_dir (versions/<id>/ or the startup line in the log)."""
    versions = sorted((p.name for p in (mc_dir / "versions").glob("*") if p.is_dir()), reverse=True)
    if versions:
        return versions[0]
    latest = mc_dir / "logs" / "latest.log"
    if latest.exists() and (m := re.search(r"Starting minecraft server version (\S+)", latest.read_text(errors="replace"))):
        return m.group(1)
    return None


def wanted(rel: str) -> str | None:
    """Destination path below assets/ for a texture in the client jar, or None."""
    if not rel.endswith(".png"):  # also skips the folder entries in the jar
        return None
    if rel in SPRITES:
        return SPRITES[rel]
    # before 26.1 the armor trim palettes were in trims/color_palettes/
    if rel.startswith("trims/color_palettes/"):
        name = rel.rsplit("/", 1)[1]
        return "palettes/trim_base.png" if name == "trim_palette.png" else f"palettes/trim/{name}"
    if re.fullmatch(r"(block|item)/[^/]+\.png", rel) or rel.startswith(FOLDERS):
        return rel
    return None


def read_advancements(z: zipfile.ZipFile) -> dict:
    """All advancements (not recipes) with their tab, parent, icon, frame and title/description keys."""
    out = {}
    prefix = re.compile(r"^data/minecraft/advancements?/")
    for name in z.namelist():
        if not prefix.match(name) or not name.endswith(".json") or "/recipes/" in name:
            continue
        adv_id = prefix.sub("", name)[:-5]
        d = json.loads(z.read(name))
        display = d.get("display")
        if not display:
            continue
        icon = display.get("icon", {})
        text = lambda v: v.get("translate", "") if isinstance(v, dict) else str(v)
        out[adv_id] = {"tab": adv_id.split("/")[0], "parent": str(d.get("parent", "")).removeprefix("minecraft:") or None,
                       "icon": str(icon.get("id", icon.get("item", ""))).removeprefix("minecraft:"),
                       "frame": display.get("frame", "task"), "title": text(display.get("title", "")),
                       "desc": text(display.get("description", "")), "hidden": bool(display.get("hidden", False))}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", help="config.toml (for the Minecraft folder, languages and assets folder)")
    ap.add_argument("--version", help="Minecraft version, e.g. 1.21.10 (default: detected from the server)")
    ap.add_argument("--out", help="output folder (default: assets/ or storage.assets_dir from the config)")
    ap.add_argument("--languages", help="comma separated, e.g. en,nl,es (default: from the config)")
    args = ap.parse_args()

    cfg = config.load(args.config)
    out = Path(args.out) if args.out else cfg.assets_dir
    languages = args.languages.split(",") if args.languages else cfg.languages
    version = args.version or detect_version(cfg.minecraft_dir)
    if not version:
        sys.exit("Could not detect the Minecraft version, use --version")

    manifest = get_json(MANIFEST)
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if not entry:
        sys.exit(f"Version {version} not found in Mojang's version manifest")
    meta = get_json(entry["url"])
    client = meta["downloads"]["client"]
    print(f"Minecraft {version}: downloading client ({client['size'] // 1_000_000} MB)…")
    jar = get(client["url"])
    if hashlib.sha1(jar).hexdigest() != client["sha1"]:
        sys.exit("Checksum of the client jar does not match, aborting")

    count = 0
    with zipfile.ZipFile(io.BytesIO(jar)) as z:
        for name in z.namelist():
            if name.startswith(TEX) and (dest := wanted(name[len(TEX):])):
                target = out / dest
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
                count += 1
        en_us = json.loads(z.read("assets/minecraft/lang/en_us.json"))
        advancements = read_advancements(z)
    print(f"  {count} textures")
    (out / "advancements.json").write_text(json.dumps(advancements, separators=(",", ":")))
    print(f"  {len(advancements)} advancements")

    # translations: en_us is in the jar, the others come from the asset index
    lang_dir = out / "lang"
    lang_dir.mkdir(parents=True, exist_ok=True)
    index = get_json(meta["assetIndex"]["url"])["objects"]
    for lang in dict.fromkeys(["en", *languages]):
        code = LANG_CODES.get(lang, lang)
        if code == "en_us":
            strings = en_us
        elif (obj := index.get(f"minecraft/lang/{code}.json")):
            strings = json.loads(get(RESOURCES.format(obj["hash"][:2], obj["hash"])))
        else:
            print(f"  no Minecraft translation for {lang} ({code}), skipped")
            continue
        strings = {k: v for k, v in strings.items() if k.startswith(LANG_KEYS)}
        (lang_dir / f"{lang}.json").write_text(json.dumps(strings, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  translations: {lang} ({len(strings)} names)")

    (out / "js").mkdir(parents=True, exist_ok=True)
    (out / "js" / "skinview3d.bundle.js").write_bytes(get(SKINVIEW3D))
    print("  skinview3d (3D skin viewer, MIT license)")
    # list of item/block textures, so the website picks the right icon without trying (and missing) first
    names = sorted(str(p.relative_to(out))[:-4] for d in ("item", "block") for p in (out / d).glob("*.png"))
    (out / "textures.json").write_text(json.dumps(names, separators=(",", ":")))
    (out / "VERSION").write_text(version + "\n")
    print(f"Done: {out}")


if __name__ == "__main__":
    main()
