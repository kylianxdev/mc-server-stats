"""The HTTP server: the website, the textures, the skins and one JSON endpoint with all data."""
from __future__ import annotations

import gzip
import json
import logging
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, demo, playerdata, scoreboard, social
from .hall import hall_of_fame
from .history import History, snapshot
from .world import world_state
from .config import Config
from .logs import LogParser
from .progress import progress
from .skins import Skins
from .stats import fun_stats, ores, playtime

log = logging.getLogger(__name__)
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2"}
LOG_KEYS = ("commands", "ops", "logins", "warnings", "feedback", "moderation", "current_ops", "ever_ops", "whitelist")


class App:
    def __init__(self, cfg: Config, demo_mode: bool = False):
        self.cfg = cfg
        self.demo = demo.data(cfg) if demo_mode else None  # made once: the demo doesn't change
        self.logs = LogParser(cfg)
        self.skins = Skins(cfg)
        self.history = History(cfg)

    def data(self) -> dict:
        cfg = self.cfg
        if self.demo:
            return self.demo
        base = dict(self.logs.parse())
        sessions = base.pop("_sessions")
        stats = playerdata.load_stats(cfg)
        fun = fun_stats(stats)
        equipment = playerdata.equipment(cfg)
        adv_times = playerdata.advancement_times(cfg)
        board = scoreboard.read(cfg)
        online = {p for p, pr in base["profiles"].items() if pr["online"]}
        prog = progress(fun, stats, equipment, playerdata.advancements_done(adv_times), base["profiles"])
        times = playtime(stats)
        snap = snapshot(fun, prog, times)
        self.history.record(snap)
        out = {
            **base,
            "site": {"title": cfg.title, "tagline": cfg.tagline, "default_language": cfg.default_language,
                     "languages": cfg.languages, "show_log": cfg.show_log, "version": __version__},
            "playtime": times,
            "fun": fun,
            "afk": scoreboard.afk(cfg, board, online),
            "colors": scoreboard.team_colors(board),
            "armor": playerdata.public_equipment(equipment),
            "progress": prog,
            "world": world_state(cfg),
            "advancements": adv_times,
            "hall": hall_of_fame(adv_times, base["profiles"]),
            "buddies": social.buddies(sessions),
            "pvp": social.pvp(base["profiles"]),
            "ores": ores(stats),
            "history": self.history.report(snap),
            "skins": self.skins.info(),
        }
        if not cfg.show_log:
            for key in LOG_KEYS:
                out.pop(key, None)
        return out


def _static(root: Path, rel: str) -> Path | None:
    """A file below root, or None (also for '..' tricks)."""
    root = root.resolve()
    f = (root / rel).resolve()
    return f if f.is_file() and root in f.parents and f.suffix in MIME else None


def make_handler(app: App):
    cfg = app.cfg

    class Handler(BaseHTTPRequestHandler):
        server_version = f"mc-server-stats/{__version__}"

        def send(self, body: bytes, ctype: str, cache: str = "no-store"):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", cache)
            # text compresses ~5x: much faster on a slow connection
            if len(body) > 1024 and not ctype.startswith("image/") and "gzip" in self.headers.get("Accept-Encoding", ""):
                body = gzip.compress(body, 6)
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Vary", "Accept-Encoding")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urllib.parse.unquote(self.path.split("?", 1)[0])
            try:
                if path == "/api/data":
                    return self.send(json.dumps(app.data()).encode(), MIME[".json"])
                if path in ("/", "/index.html"):
                    return self.send((cfg.web_dir / "index.html").read_bytes(), MIME[".html"])
                if m := re.fullmatch(r"/skin/(\w{1,16})\.png", path):
                    # may be cached long: the website asks for a new ?v= when the skin changes
                    if app.demo:
                        return self.send(demo.skin_path(cfg, m.group(1)).read_bytes(), MIME[".png"], "public, max-age=604800")
                    return self.send(app.skins.png(m.group(1)), MIME[".png"], "public, max-age=604800")
                if (m := re.fullmatch(r"/cape/(\w{1,16})\.png", path)) and (cape := app.skins.cape(m.group(1))):
                    return self.send(cape, MIME[".png"], "public, max-age=604800")
                if path.startswith("/assets/") and (f := _static(cfg.assets_dir, path[len("/assets/"):])):
                    return self.send(f.read_bytes(), MIME[f.suffix], "public, max-age=604800")
                if path.startswith("/fonts/") and (f := _static(cfg.web_dir, path.lstrip("/"))):
                    return self.send(f.read_bytes(), MIME[f.suffix], "public, max-age=31536000")
                if path.startswith(("/css/", "/js/", "/i18n/")) and (f := _static(cfg.web_dir, path.lstrip("/"))):
                    # kept 5 minutes, then refreshed in the background: fast for visitors, updates show up soon
                    return self.send(f.read_bytes(), MIME[f.suffix], "max-age=300, stale-while-revalidate=86400")
            except Exception:
                log.exception("error while handling %s", path)
                self.send_response(500)
                self.end_headers()
                return
            self.send_response(404)
            self.send_header("Cache-Control", "max-age=3600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    return Handler


def serve(cfg: Config, demo_mode: bool = False):
    if not (cfg.assets_dir / "block" / "dirt.png").exists():
        log.warning("textures not found in %s, run scripts/fetch_assets.py first", cfg.assets_dir)
    app = App(cfg, demo_mode)
    if demo_mode:
        log.info("demo mode: showing a made-up server")
    else:
        app.skins.start()
    httpd = ThreadingHTTPServer((cfg.host, cfg.port), make_handler(app))
    log.info("mc-server-stats %s on http://%s:%d (Minecraft: %s)", __version__, cfg.host, cfg.port, cfg.minecraft_dir)
    httpd.serve_forever()
