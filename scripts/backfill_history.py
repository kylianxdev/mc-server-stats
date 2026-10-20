#!/usr/bin/env python3
"""Fill the history (for "player of the week" and progress charts) from old world backups.

Works with backups made by extras/backup.sh (.tar.zst) and with plain .tar.gz/.tgz files that
contain the world folder. The date is taken from the file name (YYYY-MM-DD); per day the last
backup is used. Days that already have history are skipped unless you pass --force.

    python3 scripts/backfill_history.py --config config.toml --backups ~/backups/minecraft
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mcstats import config, playerdata  # noqa: E402
from mcstats.history import History, snapshot  # noqa: E402
from mcstats.progress import progress  # noqa: E402
from mcstats.stats import fun_stats, playtime  # noqa: E402


def extract_players(archive: Path, world: str, target: Path):
    """Extract only <world>/players/ from a backup into target."""
    members = f"{world}/players"
    if archive.name.endswith(".zst"):
        if not shutil.which("zstd"):
            sys.exit("zstd is needed for .tar.zst backups (sudo apt install zstd)")
        zstd = subprocess.Popen(["zstd", "-dc", str(archive)], stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(target), members], stdin=zstd.stdout, check=False, stderr=subprocess.DEVNULL)
        zstd.wait()
    else:
        with tarfile.open(archive) as t:
            t.extractall(target, members=[m for m in t.getmembers() if m.name.startswith(members)], filter="data")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("--backups", required=True, help="folder with the backup files")
    ap.add_argument("--force", action="store_true", help="also overwrite days that already have history")
    args = ap.parse_args()

    cfg = config.load(args.config)
    history = History(cfg)
    existing = set(history.load(10_000))
    per_day: dict[str, Path] = {}
    for f in sorted(Path(args.backups).expanduser().iterdir()):
        if f.name.endswith((".tar.zst", ".tar.gz", ".tgz")) and (m := re.search(r"(\d{4}-\d\d-\d\d)", f.name)):
            per_day[m.group(1)] = f  # sorted by name, so the last backup of the day wins

    for day, archive in sorted(per_day.items()):
        if day in existing and not args.force:
            print(f"{day}: already in the history, skipped")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            extract_players(archive, cfg.world, tmp)
            if not (tmp / cfg.world / "players").exists():
                print(f"{day}: no player data in {archive.name}, skipped")
                continue
            shutil.copy(cfg.minecraft_dir / "usercache.json", tmp / "usercache.json")
            old = config.Config(minecraft_dir=tmp, world=cfg.world, data_dir=cfg.data_dir)
            stats = playerdata.load_stats(old)
            fun = fun_stats(stats)
            done = playerdata.advancements_done(playerdata.advancement_times(old))
            prog = progress(fun, stats, playerdata.equipment(old), done, {})
            history.record(snapshot(fun, prog, playtime(stats)), day=dt.date.fromisoformat(day))
            print(f"{day}: {len(stats)} players from {archive.name}")


if __name__ == "__main__":
    main()
