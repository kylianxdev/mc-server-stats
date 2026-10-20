"""Read the blocks around the world spawn from the region files, for the 3D header.

Minecraft stores the world in region files (.mca): 32×32 chunks, each a compressed NBT tree with
sections of 16×16×16 blocks. Every section has a palette of block states and a packed array of
palette indexes. Only blocks you can actually see are sent to the website.
"""
from __future__ import annotations

import gzip
import json
import struct
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


def visible(columns: dict, props_of: dict, spawn: tuple[int, int, int], below: int = 3) -> dict:
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
            if all(n in solid or not (x0 <= n[0] <= x1 and z0 <= n[2] <= z1) for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1))):
                continue
            p = props_of.get((x, y, z), {})
            state = name + (":top" if p.get("type") == "top" else ":bottom" if p.get("type") == "bottom" else "")
            if state not in index:
                index[state] = len(palette)
                palette.append(state)
            blocks += (x - sx, y - sy, z - sz, index[state])  # flat: x, y, z, palette index, x, y, …
    return {"spawn": [sx, sy, sz], "palette": palette, "blocks": blocks,
            "surface": {f"{x - sx},{z - sz}": y - sy for (x, z), y in tops.items()}}


class World3D:
    """The 3D surroundings, read in the background every 10 minutes so a visitor never waits for it."""

    def __init__(self, cfg: Config, every: int = 600):
        self.cfg, self.every = cfg, every
        self._body = None
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True, name="world3d").start()

    def _read(self) -> bytes:
        try:
            body = json.dumps(surroundings(self.cfg), separators=(",", ":")).encode()
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
