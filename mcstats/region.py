"""Read the blocks around the world spawn from the region files, for the 3D header.

Minecraft stores the world in region files (.mca): 32×32 chunks, each a compressed NBT tree with
sections of 16×16×16 blocks. Every section has a palette of block states and a packed array of
palette indexes. Only blocks you can actually see are sent to the website.
"""
from __future__ import annotations

import gzip
import json
import struct
from collections import OrderedDict
import threading
import time
import zlib
from pathlib import Path

from .config import Config
from .nbt import read_nbt, read_nbt_file

AIR = {"air", "cave_air", "void_air", "light", "structure_void", "barrier"}
# blocks you can see through: the blocks behind them must still be drawn
SEE_THROUGH_WORDS = ("glass", "leaves", "water", "lava", "ice", "slab", "stairs", "fence", "wall", "pane", "door", "trapdoor",
                     "grass", "fern", "flower", "sapling", "torch", "rail", "carpet", "snow", "vine", "bush", "lily", "kelp",
                     "seagrass", "sugar_cane", "bamboo", "mushroom", "dandelion", "poppy", "orchid", "allium", "tulip",
                     "daisy", "cornflower", "lantern", "chain", "ladder", "sign", "banner", "bed", "button", "lever",
                     "plate", "berry", "roots", "sprouts", "dripleaf", "azalea", "petals", "moss_carpet", "cobweb")


def see_through(name: str) -> bool:
    return name in AIR or any(w in name for w in SEE_THROUGH_WORDS)


class Region:
    """One .mca file; chunks are read lazily."""

    def __init__(self, path: Path):
        self.data = path.read_bytes() if path.exists() else b""

    def chunk(self, cx: int, cz: int) -> dict | None:
        if len(self.data) < 8192:
            return None
        i = 4 * ((cx & 31) + (cz & 31) * 32)
        loc = int.from_bytes(self.data[i:i + 3], "big")
        if not loc:
            return None
        off = loc * 4096
        length, kind = struct.unpack_from(">IB", self.data, off)
        raw = self.data[off + 5:off + 4 + length]
        if kind == 2:
            raw = zlib.decompress(raw)
        elif kind == 1:
            raw = gzip.decompress(raw)
        elif kind != 3:
            return None  # lz4 or an external file: skip
        return read_nbt(raw)


def section_blocks(section: dict):
    """(palette names, function local index -> palette index) for one 16³ section."""
    states = section.get("block_states") or {}
    entries = states.get("palette", [])
    # since 1.21.5 a list may mix types: a plain block is stored as {"": "minecraft:stone"}
    unwrap = lambda p: p if isinstance(p, str) else p.get("", p.get("Name", "minecraft:air")) if isinstance(p, dict) else "minecraft:air"
    palette = [str(unwrap(p)).removeprefix("minecraft:") for p in entries]
    props = [p.get("Properties", {}) if isinstance(p, dict) else {} for p in entries]
    data = states.get("data")
    if not palette:
        return ["air"], [{}], lambda i: 0
    if not data or len(palette) == 1:
        return palette, props, lambda i: 0
    bits = max(4, (len(palette) - 1).bit_length())
    per_long = 64 // bits
    mask = (1 << bits) - 1
    longs = [v & 0xFFFFFFFFFFFFFFFF for v in data]

    def at(i: int) -> int:
        return (longs[i // per_long] >> ((i % per_long) * bits)) & mask
    return palette, props, at


def spawn_point(cfg: Config) -> tuple[int, int, int]:
    for path in (cfg.world_dir / "level.dat",
                 cfg.world_dir / "dimensions" / "minecraft" / "overworld" / "data" / "paper" / "level_overrides.dat"):
        try:
            d = read_nbt_file(path)
            d = d.get("Data", d.get("data", d))
            if "spawn" in d:
                x, y, z = d["spawn"]["pos"]
                return int(x), int(y), int(z)
            if "SpawnX" in d:
                return int(d["SpawnX"]), int(d["SpawnY"]), int(d["SpawnZ"])
        except Exception:
            continue
    return 0, 64, 0


def region_dir(cfg: Config) -> Path:
    new = cfg.world_dir / "dimensions" / "minecraft" / "overworld" / "region"  # since 26.1
    return new if new.exists() else cfg.world_dir / "region"


def surroundings(cfg: Config, radius: int = 32, below: int = 3) -> dict:
    """The visible blocks in a square around spawn, from a bit under the surface up to the sky."""
    sx, sy, sz = spawn_point(cfg)
    x0, x1, z0, z1 = sx - radius, sx + radius, sz - radius, sz + radius
    regions: dict[tuple[int, int], Region] = {}
    columns: dict[tuple[int, int], dict[int, str]] = {}  # (x, z) -> {y: name}
    props_of: dict[tuple[int, int, int], dict] = {}

    for cx in range(x0 >> 4, (x1 >> 4) + 1):
        for cz in range(z0 >> 4, (z1 >> 4) + 1):
            key = (cx >> 5, cz >> 5)
            if key not in regions:
                regions[key] = Region(region_dir(cfg) / f"r.{key[0]}.{key[1]}.mca")
            chunk = regions[key].chunk(cx, cz)
            if not chunk:
                continue
            for section in chunk.get("sections", chunk.get("Level", {}).get("Sections", [])):
                palette, props, at = section_blocks(section)
                if palette == ["air"] or all(p in AIR for p in palette):
                    continue
                base_y = section.get("Y", 0) * 16
                for ly in range(16):
                    for lz in range(16):
                        z = cz * 16 + lz
                        if not z0 <= z <= z1:
                            continue
                        for lx in range(16):
                            x = cx * 16 + lx
                            if not x0 <= x <= x1:
                                continue
                            idx = at(ly * 256 + lz * 16 + lx)
                            name = palette[idx]
                            if name not in AIR:
                                y = base_y + ly
                                columns.setdefault((x, z), {})[y] = name
                                if props[idx]:
                                    props_of[(x, y, z)] = props[idx]

    return visible(columns, props_of, (sx, sy, sz), below)


def visible(columns: dict, props_of: dict, spawn: tuple[int, int, int], below: int = 3, closed: bool = True) -> dict:
    """Only the blocks you can see, relative to spawn, with a palette (website format)."""
    sx, sy, sz = spawn
    tops = {xz: max(ys) for xz, ys in columns.items() if ys}
    if not tops:
        return {"spawn": [sx, sy, sz], "palette": [], "blocks": []}
    # per column: from a bit below the lowest neighbour up, so cliff faces are complete but no hidden underground
    def floor_of(x, z):
        return min(tops.get(n, tops[(x, z)]) for n in ((x, z), (x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1))) - below
    floors = {xz: floor_of(*xz) for xz in tops}
    # the outer ring goes all the way down, so the edges look like solid ground instead of thin floating slices
    xs, zs = [x for x, _ in tops], [z for _, z in tops]
    lowest = min(tops.values()) - below
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    for (x, z) in tops:
        if min(x - min(xs), max(xs) - x, z - min(zs), max(zs) - z) < 2:
            floors[(x, z)] = lowest
    solid = {(x, y, z) for (x, z), ys in columns.items() for y, n in ys.items() if y >= lowest - 1 and not see_through(n)}

    palette, index, blocks = [], {}, []
    for (x, z), ys in columns.items():
        for y, name in ys.items():
            if y < floors[(x, z)]:
                continue
            # hidden when all six neighbours are solid blocks (outside the area counts as solid: nobody looks from there)
            if all(n in solid or (closed and not (x0 <= n[0] <= x1 and z0 <= n[2] <= z1)) for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1))):
                continue
            p = props_of.get((x, y, z), {})
            state = name + (":top" if p.get("type") == "top" else ":bottom" if p.get("type") == "bottom" else "")
            if state not in index:
                index[state] = len(palette)
                palette.append(state)
            blocks += (x - sx, y - sy, z - sz, index[state])  # flat: x, y, z, palette index, x, y, …
    return {"spawn": [sx, sy, sz], "palette": palette, "blocks": blocks,
            "surface": {f"{x - sx},{z - sz}": y - sy for (x, z), y in tops.items()}}


# plants and small things: from the air you look past them at the ground (like the game's MOTION_BLOCKING heightmap)
PLANT_WORDS = ("grass", "fern", "flower", "sapling", "torch", "rail", "carpet", "vine", "bush", "lily", "kelp", "seagrass",
               "sugar_cane", "mushroom", "dandelion", "poppy", "orchid", "allium", "tulip", "daisy", "cornflower", "button",
               "lever", "plate", "berry", "roots", "sprouts", "petals", "sign", "banner", "snow", "cobweb", "bluet", "rose",
               "lilac", "peony", "sunflower", "wheat", "carrots", "potatoes", "beetroots", "stem", "litter", "wildflowers")


def is_surface(name: str) -> bool:
    """Does this block count as the ground (or roof, or treetop) seen from the air?"""
    return name not in AIR and (name == "grass_block" or not any(w in name for w in PLANT_WORDS))


def _heightmap(longs: list[int], n: int = 256) -> list[int]:
    per = -(-n // len(longs))  # entries per long; they never span two longs
    bits, longs = 64 // per, [v & 0xFFFFFFFFFFFFFFFF for v in longs]
    mask = (1 << bits) - 1
    return [(longs[i // per] >> ((i % per) * bits)) & mask for i in range(n)]


class ChunkReader:
    """The chunks of an area; blocks are looked up by world position.

    Only the most recently used chunks and region files are kept, so reading a big area stays light on memory
    (go through it chunk by chunk).
    """

    def __init__(self, cfg: Config, keep_chunks: int = 96, keep_regions: int = 6):
        self.dir, self.regions, self.chunks = region_dir(cfg), OrderedDict(), OrderedDict()
        self.keep_chunks, self.keep_regions = keep_chunks, keep_regions

    def _chunk(self, cx: int, cz: int) -> dict | None:
        if (cx, cz) in self.chunks:
            self.chunks.move_to_end((cx, cz))
        else:
            rk = (cx >> 5, cz >> 5)
            if rk in self.regions:
                self.regions.move_to_end(rk)
            else:
                self.regions[rk] = Region(self.dir / f"r.{rk[0]}.{rk[1]}.mca")
                if len(self.regions) > self.keep_regions:
                    self.regions.popitem(last=False)
            c = self.regions[rk].chunk(cx, cz)
            hm = (c or {}).get("Heightmaps", {}).get("MOTION_BLOCKING")
            self.chunks[(cx, cz)] = c and {"sections": {s.get("Y", 0): s for s in c.get("sections", [])}, "decoded": {},
                                           "min_y": c.get("yPos", -4) * 16, "heights": _heightmap(hm) if hm else None}
            if len(self.chunks) > self.keep_chunks:
                self.chunks.popitem(last=False)
        return self.chunks[(cx, cz)]

    def block(self, x: int, y: int, z: int) -> tuple[str, dict]:
        ch = self._chunk(x >> 4, z >> 4)
        if not ch:
            return "air", {}
        sy = y >> 4
        if sy not in ch["decoded"]:
            sec = ch["sections"].get(sy)
            ch["decoded"][sy] = section_blocks(sec) if sec else (["air"], [{}], lambda i: 0)
        palette, props, at = ch["decoded"][sy]
        i = at((y & 15) * 256 + (z & 15) * 16 + (x & 15))
        return palette[i], props[i]

    def top(self, x: int, z: int) -> int | None:
        """The highest block from the air: the game's own MOTION_BLOCKING heightmap (ignores grass and flowers)."""
        ch = self._chunk(x >> 4, z >> 4)
        if not ch or not ch["heights"]:
            return None
        v = ch["heights"][(z & 15) * 16 + (x & 15)]
        if not v:
            return None
        # the saved heightmap can lag behind (a tree chopped down): go down to the real top
        y = ch["min_y"] + v - 1
        for _ in range(64):
            if is_surface(self.block(x, y, z)[0]):
                return y
            y -= 1
        return None


def standing_spot(top, bed: tuple[int, int, int], reach: int = 8) -> tuple[int, int, int]:
    """Where a player stands outside their house: the nearest open ground at about the height of their bed."""
    bx, by, bz = bed
    best = None
    for dx in range(-reach, reach + 1):
        for dz in range(-reach, reach + 1):
            y = top(bx + dx, bz + dz)
            if y is not None and by - 4 <= y <= by and (best is None or dx * dx + dz * dz < best[0]):
                best = (dx * dx + dz * dz, (bx + dx, y + 1, bz + dz))
    return best[1] if best else bed


def valley(top, block, center: tuple[int, int], homes: dict[str, tuple[int, int, int]],
           margin: int = 28, max_half: int = 128, patch: int = 9, far: int = 0, step: int = 4) -> dict:
    """An area seen from the air (website format): the ground from the heightmap, every block around the homes.

    Everything is relative to the center, so no real coordinates end up on the website.
    """
    cx, cz = center
    near = {p: h for p, h in homes.items() if abs(h[0] - cx) <= max_half and abs(h[2] - cz) <= max_half}
    half = min(max_half, max([abs(h[0] - cx) for h in near.values()] + [abs(h[2] - cz) for h in near.values()] + [0]) + margin)
    if far:
        half = -(-half // step) * step  # the coarse land then fits exactly around the detailed middle
    x0, x1, z0, z1 = cx - half, cx + half, cz - half, cz + half
    base = top(cx, cz)
    base = 64 if base is None else base

    palette, index = [], {}

    def pi(state: str) -> int:
        if state not in index:
            index[state] = len(palette)
            palette.append(state)
        return index[state]

    heights, tops, unders = [], [], []
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            y = top(x, z)
            if y is None:
                heights.append(None); tops.append(0); unders.append(0)
                continue
            under = block(x, y - 1, z)[0]
            heights.append(y - base)
            tops.append(pi(block(x, y, z)[0]))
            unders.append(pi(under if under not in AIR else block(x, y, z)[0]))

    # every block around the homes: walls, windows, roofs
    detail, patches = [], []
    for bx, by, bz in near.values():
        px0, px1, pz0, pz1 = max(x0, bx - patch), min(x1, bx + patch), max(z0, bz - patch), min(z1, bz + patch)
        ys = [t for x in range(px0, px1 + 1) for z in range(pz0, pz1 + 1) if (t := top(x, z)) is not None]
        if not ys:
            continue
        columns, props_of = {}, {}
        for x in range(px0, px1 + 1):
            for z in range(pz0, pz1 + 1):
                for y in range(min(ys) - 3, max(ys) + 1):
                    name, props = block(x, y, z)
                    if name not in AIR:
                        columns.setdefault((x, z), {})[y] = name
                        if props:
                            props_of[(x, y, z)] = props
        part = visible(columns, props_of, (cx, base, cz), below=2, closed=False)
        b = part["blocks"]
        for i in range(0, len(b), 4):
            detail += (b[i], b[i + 1], b[i + 2], pi(part["palette"][b[i + 3]]))
        patches.append([px0 - cx, pz0 - cz, px1 - cx, pz1 - cz])

    # the land around it up to the horizon, coarser: one column for every step×step blocks
    lod = None
    if far > half:
        fh, ft, n = [], [], 2 * far // step
        fx0, fz0 = cx - far, cz - far
        # chunk by chunk, so every chunk is read once
        cells = sorted(((i, j) for j in range(n) for i in range(n)),
                       key=lambda c: (((fz0 + c[1] * step) >> 4), ((fx0 + c[0] * step) >> 4)))
        grid = {}
        for i, j in cells:
            cell_x, cell_z = fx0 + i * step, fz0 + j * step
            inside = cell_x + step > x0 and cell_x <= x1 and cell_z + step > z0 and cell_z <= z1
            x, z = cell_x + step // 2, cell_z + step // 2
            y = None if inside else top(x, z)  # the detailed part covers the middle
            grid[(i, j)] = (None, 0) if y is None else (y - base, pi(block(x, y, z)[0]))
        for j in range(n):
            for i in range(n):
                fh.append(grid[(i, j)][0]); ft.append(grid[(i, j)][1])
        lod = {"step": step, "origin": [fx0 - cx, fz0 - cz], "size": [n, n], "h": fh, "t": ft}

    spots = {p: standing_spot(top, h) for p, h in near.items()}
    return {"kind": "valley", "far": lod, "origin": [x0 - cx, z0 - cz], "size": [x1 - x0 + 1, z1 - z0 + 1], "palette": palette,
            "h": heights, "t": tops, "u": unders, "detail": detail, "patches": patches,
            "homes": {p: [x - cx, y - base, z - cz] for p, (x, y, z) in spots.items()}}


def homes_of(cfg: Config, center: tuple[int, int] | None = None, reach: int = 400) -> dict[str, tuple[int, int, int]]:
    """Every player's home: from the config, otherwise their bed (respawn point) in the overworld."""
    from .playerdata import uuid_names
    names, homes = uuid_names(cfg), {}
    for f in sorted((cfg.world_dir / "players" / "data").glob("*.dat")):
        try:
            r = read_nbt_file(f).get("respawn") or {}
        except Exception:
            continue
        if r.get("dimension", "minecraft:overworld") == "minecraft:overworld" and "pos" in r:
            homes[names.get(f.stem, f.stem)] = tuple(int(v) for v in r["pos"])
    homes.update({p: tuple(int(v) for v in pos) for p, pos in cfg.world3d_homes.items()})
    if center:
        homes = {p: h for p, h in homes.items() if abs(h[0] - center[0]) <= reach and abs(h[2] - center[1]) <= reach}
    return homes


def bluemap_running(cfg: Config) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{cfg.bluemap_url}/maps/{cfg.world}/settings.json", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def world_center(cfg: Config) -> tuple[tuple[int, int], dict]:
    """The middle of the 3D header (the config, else the middle of everyone's home, else spawn) and the homes."""
    sx, _, sz = spawn_point(cfg)
    homes = homes_of(cfg, tuple(cfg.world3d_center) if cfg.world3d_center else (sx, sz))
    if cfg.world3d_center:
        return tuple(cfg.world3d_center), homes
    if homes:
        xs, zs = [h[0] for h in homes.values()], [h[-1] for h in homes.values()]
        return ((min(xs) + max(xs)) // 2, (min(zs) + max(zs)) // 2), homes
    return (sx, sz), homes


def world_header(cfg: Config) -> dict:
    """What the 3D header shows: BlueMap's own 3D map when it runs (every block, perfectly rendered),
    otherwise the valley drawn by this website."""
    if not bluemap_running(cfg):
        return world_valley(cfg)
    (cx, cz), homes = world_center(cfg)
    reader = ChunkReader(cfg, keep_chunks=4)
    xs, zs = [h[0] for h in homes.values()] + [cx], [h[-1] for h in homes.values()] + [cz]
    spread = max(max(xs) - min(xs), max(zs) - min(zs), 60)
    y = reader.top(cx, cz) or 64
    return {"kind": "bluemap", "bluemap": {"map": cfg.world, "x": cx, "y": y, "z": cz, "distance": round(spread * 1.25)},
            "frame": [cx, y, cz]}


def world_valley(cfg: Config) -> dict:
    """The valley for the website; "frame" (center and base height, never sent) is kept to place live players."""
    reader = ChunkReader(cfg)
    center, homes = world_center(cfg)
    # homes given by hand without a height: put them on the ground
    homes = {p: (h[0], reader.top(h[0], h[-1]) + 1 if len(h) == 2 else h[1], h[-1]) for p, h in homes.items()}
    out = valley(reader.top, reader.block, center, homes, far=cfg.world3d_far)
    out["frame"] = [center[0], (reader.top(*center) or 64), center[1]]
    return out


class World3D:
    """The 3D surroundings, read in the background every 10 minutes so a visitor never waits for it."""

    def __init__(self, cfg: Config, every: int = 600):
        self.cfg, self.every = cfg, every
        self._body, self.frame = None, None
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True, name="world3d").start()

    def _read(self) -> bytes:
        try:
            out = world_header(self.cfg)
            self.frame = out.pop("frame")  # real coordinates: kept here, never sent
            body = json.dumps(out, separators=(",", ":")).encode()
        except Exception as e:  # unknown chunk format: the website just shows the flat header
            body = json.dumps({"error": str(e), "palette": [], "blocks": []}).encode()
        with self._lock:
            self._body = body
        return body

    def _loop(self):
        while True:
            self._read()
            time.sleep(self.every)

    def json(self) -> bytes:
        with self._lock:
            body = self._body
        return body if body is not None else self._read()


def live_positions(cfg: Config, frame: list[int] | None, online: set[str]) -> dict[str, list[float]]:
    """Where online players are right now, relative to the 3D header (only those inside it).

    From BlueMap's live player list when it runs (updated every second), otherwise from the player files.
    """
    if not frame:
        return {}
    import urllib.request
    fx, fy, fz = frame
    found: dict[str, tuple[float, float, float, float]] = {}
    try:
        with urllib.request.urlopen(f"{cfg.bluemap_url}/maps/{cfg.world}/live/players.json", timeout=0.4) as r:
            for p in json.load(r).get("players", []):
                if not p.get("foreign"):
                    pos, rot = p["position"], p.get("rotation", {})
                    found[p["name"]] = (pos["x"], pos["y"], pos["z"], rot.get("yaw", 0.0))
    except Exception:
        from .playerdata import uuid_names
        names = {n: u for u, n in uuid_names(cfg).items()}
        for p in online:
            try:
                d = read_nbt_file(cfg.world_dir / "players" / "data" / f"{names[p]}.dat")
                if d.get("Dimension", "minecraft:overworld") == "minecraft:overworld":
                    found[p] = (*d["Pos"][:3], d.get("Rotation", [0.0])[0])
            except Exception:
                continue
    out = {}
    for p, (x, y, z, yaw) in found.items():
        if p in online and abs(x - fx) <= cfg.world3d_far and abs(z - fz) <= cfg.world3d_far:
            out[p] = [round(x - fx, 1), round(y - fy, 1), round(z - fz, 1), round(yaw)]
    return out
