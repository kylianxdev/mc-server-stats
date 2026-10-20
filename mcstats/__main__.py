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
    parser.add_argument("--demo", action="store_true", help="show a made-up server (no Minecraft server needed)")
    parser.add_argument("-p", "--port", type=int, help="port of the website (overrides the config)")
    parser.add_argument("--recap", action="store_true", help="print the weekly recap for the game chat and exit")
    parser.add_argument("--url", default="", help="with --recap: link to the website in the message")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    path = args.config if os.path.exists(args.config) else None
    if not path and not args.demo:
        logging.warning("config file %s not found, using defaults", args.config)
    cfg = config.load(path)
    if args.port:
        cfg.port = args.port
    if args.recap:
        from .recap import recap
        from .server import App
        message = recap(App(cfg, args.demo).data(), cfg.default_language, args.url)
        if message:
            print(message)
        return
    serve(cfg, demo_mode=args.demo)


if __name__ == "__main__":
    main()
