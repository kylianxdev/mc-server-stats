"""Configuration, loaded from a TOML file (see config.example.toml)."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    # Minecraft server
    minecraft_dir: Path = Path("/srv/minecraft")
    world: str = "world"
    # web server
    host: str = "0.0.0.0"
    port: int = 8200
    # site
    title: str = "Server Stats"
    tagline: str = ""
    default_language: str = "en"
    languages: list[str] = field(default_factory=lambda: ["en", "nl", "es", "de", "fr"])
    # privacy
    hide_coordinates: bool = True
    show_log: bool = True
    # features
    afk_threshold: int = 300
    afk_since: str = ""
    skin_check_interval: int = 180
    extra_admin_commands: list[str] = field(default_factory=list)
    # storage
    data_dir: Path = ROOT / "data"
    assets_dir: Path = ROOT / "assets"
    web_dir: Path = ROOT / "web"

    @property
    def world_dir(self) -> Path:
        return self.minecraft_dir / self.world

    @property
    def logs_dir(self) -> Path:
        return self.minecraft_dir / "logs"


def _path(value: str, base: Path) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def load(path: str | Path | None) -> Config:
    cfg = Config()
    if not path:
        return cfg
    path = Path(path)
    base = path.resolve().parent
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    mc, web, site = raw.get("minecraft", {}), raw.get("web", {}), raw.get("site", {})
    privacy, feat, storage = raw.get("privacy", {}), raw.get("features", {}), raw.get("storage", {})

    if "dir" in mc:
        cfg.minecraft_dir = _path(mc["dir"], base)
    cfg.world = mc.get("world", cfg.world)
    cfg.host = web.get("host", cfg.host)
    cfg.port = int(web.get("port", cfg.port))
    cfg.title = site.get("title", cfg.title)
    cfg.tagline = site.get("tagline", cfg.tagline)
    cfg.default_language = site.get("default_language", cfg.default_language)
    cfg.languages = list(site.get("languages", cfg.languages))
    cfg.hide_coordinates = bool(privacy.get("hide_coordinates", cfg.hide_coordinates))
    cfg.show_log = bool(privacy.get("show_log", cfg.show_log))
    cfg.afk_threshold = int(feat.get("afk_threshold_seconds", cfg.afk_threshold))
    cfg.afk_since = str(feat.get("afk_since", cfg.afk_since))
    cfg.skin_check_interval = int(feat.get("skin_check_interval_seconds", cfg.skin_check_interval))
    cfg.extra_admin_commands = list(feat.get("extra_admin_commands", cfg.extra_admin_commands))
    if "data_dir" in storage:
        cfg.data_dir = _path(storage["data_dir"], base)
    if "assets_dir" in storage:
        cfg.assets_dir = _path(storage["assets_dir"], base)
    return cfg
