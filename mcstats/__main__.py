"""Run the website:  python -m mcstats --config config.toml"""
import argparse
import logging
import os

from . import config
from .server import serve


def main():
    parser = argparse.ArgumentParser(prog="mcstats", description="Live statistics website for a Minecraft server")
    parser.add_argument("-c", "--config", default=os.environ.get("MCSTATS_CONFIG", "config.toml"),
                        help="path to config.toml (default: ./config.toml or $MCSTATS_CONFIG)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    path = args.config if os.path.exists(args.config) else None
    if not path:
        logging.warning("config file %s not found, using defaults", args.config)
    serve(config.load(path))


if __name__ == "__main__":
    main()
