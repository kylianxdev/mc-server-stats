"""The HTTP server: the website, the textures, the skins and one JSON endpoint with all data."""
from __future__ import annotations

import email.utils
import gzip
import hashlib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, demo, playerdata, scoreboard, social
from .hall import hall_of_fame
from .history import History, snapshot
from .world import world_state
from .config import Config
from .logs import LogParser
from .progress import progress
from .region import World3D, live_positions
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
        self.world3d = None if demo_mode else World3D(cfg)

    def data(self) -> dict:
        cfg = self.cfg
        if self.demo:
            return {**self.demo, "live3d": demo.live3d()}
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
            "colors": scoreboard.name_colors(board, armor := playerdata.public_equipment(equipment)),
            "armor": armor,
            "progress": prog,
            "world": world_state(cfg),
            "advancements": adv_times,
            "hall": hall_of_fame(adv_times, base["profiles"]),
            "buddies": social.buddies(sessions),
            "pvp": social.pvp(base["profiles"]),
            "ores": ores(stats),
            "history": self.history.report(snap),
            "skins": self.skins.info(),
            # online players inside the 3D header: where they are now, relative to its middle
            "live3d": live_positions(cfg, self.world3d.frame, online),
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


def site_version(web_dir: Path) -> str:
    """Changes whenever a file of the website changes (it goes into every URL, so browsers never mix versions)."""
    h = hashlib.sha1()
    for f in sorted(p for d in ("css", "js", "i18n") for p in (web_dir / d).rglob("*") if p.is_file()):
        st = f.stat()
        h.update(f"{f.relative_to(web_dir)}:{st.st_mtime_ns}:{st.st_size};".encode())
    return h.hexdigest()[:10]


def index_html(web_dir: Path) -> bytes:
    """index.html with ?v=<version> on every script and stylesheet, plus an import map for the modules they import."""
    v = site_version(web_dir)
    html = (web_dir / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'((?:href|src)=")(/(?:css|js)/[^"?]+)"', rf'\1\2?v={v}"', html)
    modules = {f"/{p.relative_to(web_dir).as_posix()}": f"/{p.relative_to(web_dir).as_posix()}?v={v}"
               for p in sorted((web_dir / "js").rglob("*.js"))}
    head = (f'<script type="importmap">{json.dumps({"imports": modules}, separators=(",", ":"))}</script>\n'
            f'<script>window.siteVersion = "{v}";</script>\n')
    return html.replace("<link ", head + "<link ", 1).encode()


def make_handler(app: App):
    cfg = app.cfg

    class Handler(BaseHTTPRequestHandler):
        server_version = f"mc-server-stats/{__version__}"
        protocol_version = "HTTP/1.1"  # keep the connection open: the 3D header asks for hundreds of map tiles
        timeout = 60

        def send(self, body: bytes, ctype: str, cache: str = "no-store", status: int = 200):
            self.send_response(status)
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

        def proxy_bluemap(self, rest: str):
            """Pass a request on to BlueMap, so the 3D header can show its map from this same website."""
            if rest.rstrip("/").endswith("/live/sse"):  # a never ending stream: BlueMap then just asks every second
                return self.send(b"", "text/plain", "no-store", status=404)
            req = urllib.request.Request(cfg.bluemap_url + rest, headers={
                k: v for k in ("Accept-Encoding", "If-None-Match", "If-Modified-Since") if (v := self.headers.get(k))})
            try:
                r = urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                r = e
            except OSError:
                return self.send(b"", "text/plain", "no-store", status=502)
            with r:
                body = r.read()
                self.send_response(r.status)
                for k in ("Content-Type", "Content-Encoding", "Cache-Control", "ETag", "Last-Modified"):
                    if v := r.headers.get(k):
                        self.send_header(k, v)
                # BlueMap's app itself (1.2 MB of JavaScript) is sent compressed
                ctype = r.headers.get("Content-Type", "")
                if (r.status == 200 and len(body) > 1024 and not r.headers.get("Content-Encoding")
                        and ("javascript" in ctype or "json" in ctype or "css" in ctype or "html" in ctype)
                        and "gzip" in self.headers.get("Accept-Encoding", "")):
                    body = gzip.compress(body, 6)
                    self.send_header("Content-Encoding", "gzip")
                    self.send_header("Vary", "Accept-Encoding")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def bluemap_tile(self, rest: str) -> bool:
            """Send one of BlueMap's map tiles straight from its files (much faster than through BlueMap)."""
            m = re.fullmatch(r"/maps/(\w+)/tiles/(\d)/(x-?\d+(?:/-?\d+)*/z-?\d+(?:/-?\d+)*)\.(prbm|png)", rest.split("?", 1)[0])
            if not m:
                return False
            mapid, lod, tile, kind = m.groups()
            f = cfg.bluemap_maps_dir / mapid / "tiles" / lod / f"{tile}.{kind}{'.gz' if kind == 'prbm' else ''}"
            try:
                st = f.stat()
            except OSError:
                return False  # BlueMap knows (also: a tile that doesn't exist yet)
            modified = email.utils.formatdate(st.st_mtime, usegmt=True)
            fresh = self.headers.get("If-Modified-Since") == modified
            self.send_response(304 if fresh else 200)
            self.send_header("Content-Type", "image/png" if kind == "png" else "application/octet-stream")
            if kind == "prbm":
                self.send_header("Content-Encoding", "gzip")  # stored compressed: sent as it is
            self.send_header("Cache-Control", "public, max-age=86400, stale-if-error=604800")
            self.send_header("Last-Modified", modified)
            body = b"" if fresh else f.read_bytes()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True

        def do_GET(self):
            path = urllib.parse.unquote(self.path.split("?", 1)[0])
            try:
                if path.startswith("/bluemap/") and cfg.bluemap_url and not app.demo:
                    rest = self.path[len("/bluemap"):]
                    return self.bluemap_tile(rest) or self.proxy_bluemap(rest)
                if path == "/api/world3d":
                    body = demo.world3d() if app.demo else app.world3d.json()
                    return self.send(body, MIME[".json"], "max-age=300")
                if path == "/api/data":
                    return self.send(json.dumps(app.data()).encode(), MIME[".json"])
                if path in ("/", "/index.html"):
                    return self.send(index_html(cfg.web_dir), MIME[".html"], "no-cache")
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
                    # with ?v= (as index.html asks for them) the file never changes, so it can be kept for good
                    versioned = "v=" in self.path.partition("?")[2]
                    return self.send(f.read_bytes(), MIME[f.suffix], "public, max-age=31536000, immutable" if versioned else "no-cache")
            except Exception:
                log.exception("error while handling %s", path)
                self.send_response(500)
                self.send_header("Content-Length", "0")
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
