"""Player skins and capes from the official Mojang API, refreshed in the background.

A background thread checks every few minutes whether someone picked a new skin. The version
("v", taken from the texture hash) is part of /api/data, so the website shows a new skin right away.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
import urllib.request
from pathlib import Path

from .config import Config

log = logging.getLogger(__name__)
PROFILE_URL = "https://sessionserver.mojang.com/session/minecraft/profile/{}"
TEXTURES = "https://textures.minecraft.net/texture/"


class Skins:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.dir = cfg.data_dir / "skins"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.default = cfg.assets_dir / "entity" / "player" / "wide" / "steve.png"

    def start(self):
        threading.Thread(target=self._loop, name="skins", daemon=True).start()

    def info(self) -> dict[str, dict]:
        out = {}
        for f in self.dir.glob("*.json"):
            try:
                out[f.stem] = json.loads(f.read_text())
            except ValueError:
                pass
        return out

    def png(self, name: str) -> bytes:
        f = self.dir / f"{name}.png"
        return (f if f.exists() else self.default).read_bytes()

    def cape(self, name: str) -> bytes | None:
        f = self.dir / f"{name}.cape.png"
        return f.read_bytes() if f.exists() else None

    def _download(self, url: str, target: Path) -> str:
        """Download a texture from textures.minecraft.net; returns its short version hash."""
        url = url.replace("http://", "https://")
        if not url.startswith(TEXTURES):
            raise ValueError(f"unexpected texture url {url}")
        with urllib.request.urlopen(url, timeout=5) as r:
            target.write_bytes(r.read())
        return url.rsplit("/", 1)[1][:16]

    def refresh(self, name: str, uuid: str):
        with urllib.request.urlopen(PROFILE_URL.format(uuid.replace("-", "")), timeout=5) as r:
            profile = json.load(r)
        textures = json.loads(base64.b64decode(next(p["value"] for p in profile["properties"] if p["name"] == "textures")))
        skin, cape = textures["textures"].get("SKIN"), textures["textures"].get("CAPE")
        meta_file = self.dir / f"{name}.json"
        old = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        meta = {"model": "wide", "v": "steve"}
        png = self.dir / f"{name}.png"
        if skin:
            meta["model"] = "slim" if skin.get("metadata", {}).get("model") == "slim" else "wide"
            meta["v"] = skin["url"].rsplit("/", 1)[1][:16]
            if meta["v"] != old.get("v") or not png.exists():
                self._download(skin["url"], png)
                log.info("new skin for %s", name)
        elif old.get("v") != "steve" or not png.exists():  # no custom skin: Steve
            png.write_bytes(self.default.read_bytes())
        cape_png = self.dir / f"{name}.cape.png"
        if cape:  # the cape the player has selected (also used for elytra, like in the game)
            meta["cape"] = cape["url"].rsplit("/", 1)[1][:16]
            if meta["cape"] != old.get("cape") or not cape_png.exists():
                self._download(cape["url"], cape_png)
                log.info("new cape for %s", name)
        elif cape_png.exists():
            cape_png.unlink()
        if meta != old:
            meta_file.write_text(json.dumps(meta))

    def _loop(self):
        while True:
            try:
                users = json.loads((self.cfg.minecraft_dir / "usercache.json").read_text())
            except (OSError, ValueError):
                users = []
            for u in users:
                try:
                    self.refresh(u["name"], u["uuid"])
                except Exception as e:  # network hiccup or rate limit: try again next round
                    log.warning("could not fetch skin of %s: %s", u.get("name"), e)
                time.sleep(1)  # go easy on the Mojang API
            time.sleep(self.cfg.skin_check_interval)
