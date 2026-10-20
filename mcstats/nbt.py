"""A small, dependency-free reader for Minecraft's NBT format (player data, scoreboard)."""
from __future__ import annotations

import gzip
import struct
from pathlib import Path


def read_nbt(data: bytes):
    """Parse uncompressed NBT bytes and return the root tag as Python dicts/lists/values."""
    pos = 0

    def take(fmt: str):
        nonlocal pos
        value = struct.unpack_from(">" + fmt, data, pos)[0]
        pos += struct.calcsize(">" + fmt)
        return value

    def string() -> str:
        nonlocal pos
        n = take("H")
        value = data[pos:pos + n].decode("utf-8", "replace")
        pos += n
        return value

    def payload(tag: int):
        nonlocal pos
        if tag == 1: return take("b")
        if tag == 2: return take("h")
        if tag == 3: return take("i")
        if tag == 4: return take("q")
        if tag == 5: return take("f")
        if tag == 6: return take("d")
        if tag == 7:
            n = take("i")
            value = data[pos:pos + n]
            pos += n
            return value
        if tag == 8: return string()
        if tag == 9:
            elem, n = take("b"), take("i")
            return [payload(elem) for _ in range(n)]
        if tag == 10:
            out = {}
            while (child := take("b")) != 0:
                key = string()  # the name comes before the value
                out[key] = payload(child)
            return out
        if tag == 11:
            return [take("i") for _ in range(take("i"))]
        if tag == 12:
            return [take("q") for _ in range(take("i"))]
        raise ValueError(f"unknown NBT tag type {tag}")

    root = take("b")
    string()  # root name, always empty in practice
    return payload(root)


def read_nbt_file(path: Path):
    """Read a (usually gzip-compressed) .dat file."""
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return read_nbt(raw)
