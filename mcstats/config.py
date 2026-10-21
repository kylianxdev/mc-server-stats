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
    # 3D header: the middle of the area and the homes (otherwise: everyone's bed)
    world3d_center: list[int] = field(default_factory=list)
    world3d_homes: dict[str, list[int]] = field(default_factory=dict)
    world3d_far: int = 320  # how far the land goes around it (coarser), in blocks
    bluemap_url: str = "http://localhost:8100"  # for live player positions, if BlueMap runs
    bluemap_maps: Path | None = None  # BlueMap's map files (file storage), to send its tiles straight from disk
    # milestones in the game chat: the tmux session of the server console ("" = only on the website)
    console_tmux: str = ""
    # storage
    data_dir: Path = ROOT / "data"
    assets_dir: Path = ROOT / "assets"
    web_dir: Path = ROOT / "web"

    @property
    def world_dir(self) -> Path:
        return self.minecraft_dir / self.world

    @property
    def bluemap_maps_dir(self) -> Path:
        return self.bluemap_maps or self.minecraft_dir / "bluemap" / "web" / "maps"

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
    w3d = raw.get("world3d", {})
    cfg.console_tmux = str(raw.get("milestones", {}).get("tmux", cfg.console_tmux))

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
    cfg.world3d_center = [int(v) for v in w3d.get("center", [])]
    cfg.world3d_far = int(w3d.get("far", cfg.world3d_far))
    cfg.bluemap_url = str(w3d.get("bluemap", cfg.bluemap_url))
    if "bluemap_maps" in w3d:
        cfg.bluemap_maps = _path(w3d["bluemap_maps"], base)
    cfg.world3d_homes = {str(p): [int(v) for v in pos] for p, pos in w3d.get("homes", {}).items()}
    if "data_dir" in storage:
        cfg.data_dir = _path(storage["data_dir"], base)
    if "assets_dir" in storage:
        cfg.assets_dir = _path(storage["assets_dir"], base)
    return cfg
