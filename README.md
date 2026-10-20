<div align="center">

# ⛏ mc-server-stats

**A live statistics website for your Minecraft server, styled like Minecraft itself.**

3D players in the armor they actually wear, leaderboards, playtime charts, AFK tracking and a level for what you achieved.
Made for a fun survival server with your friends. No plugins, no mods: one command to install.

<img src="docs/images/hero.gif" alt="Players online walk over the grass under the night sky" width="800">

[Features](#features) · [Screenshots](#screenshots) · [Install](#installation) · [Try the demo](#try-the-demo) · [Configuration](#configuration)

![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![Minecraft 1.21.5+](https://img.shields.io/badge/minecraft-1.21.5%2B-62B47A) ![No plugins](https://img.shields.io/badge/plugins-none-orange)

</div>

## Features

**The world**
- **A sky that follows the game**, drawn with the game's own textures: `clouds.png` drifting by, the sun, the moon in the
  right phase for the day, and when it rains in your world, `rain.png` falling in columns just like in Minecraft. Plus
  the day number, the weather and whether the Ender Dragon has been defeated.

**Players**
- **3D players** ([skinview3d](https://github.com/bs-community/skinview3d)) with their skin, active **cape** and the
  **armor they're wearing**: dyed leather, **armor trims** with the real color palettes, elytras. Drag to rotate, pick an animation.
- **A play style title** for everyone: Miner, Lumberjack, Farmer, Builder, Explorer, Warrior, Trader, Fisher or Enchanter.
- **The advancement screen** of every player, like in the game: five tabs, real frames and icons, done or not yet.
- **Equipment** with enchantments and trims, **ores mined**, favourite block, most used and most crafted item,
  ~30 statistics with ranks, playtime per day and per hour, which dimension they're in, and a timeline of advancements and deaths.
- **Versus**: put two players side by side and see who wins, statistic by statistic.

**The group**
- **Site level**: XP for what you achieved (advancements, diamonds, building, mob variety, gear, …), not for time online.
  Weighted and capped so farming one thing doesn't decide everything, using Minecraft's own XP formula. Also ranks *XP per hour*.
- **Player of the week** and everyone's progress this week, from daily snapshots (`scripts/backfill_history.py` can fill
  them from old backups). Optional weekly recap in the game chat.
- **Hall of Fame**: who was the first on the server, with diamonds, in the Nether, in the End, to defeat the dragon, …
- **Best buddies** (who plays together most), **player vs player** results and the **latest events** of everyone.
- **Leaderboards** for every statistic, with spinning 3D heads.

**And also**
- **Live**: the page updates itself every 5 seconds.
- **AFK meter**, **armor colored names** and **nicer chat** as optional datapacks.
- **Log**: commands, operator history (who was ever op, admin commands with and without rights), whitelist/bans, warnings.
- **Multilingual**: English, Nederlands, Español, Deutsch, Français. Item, mob, enchantment, trim and advancement names
  and even death messages come from Minecraft's official translations.

### Privacy by design
Private messages (`/msg`, `/tell`, …) are never shown, IP addresses are never read, coordinates in commands are hidden
(`/tp [x y z]`) and inventories are only used to calculate the level, never published. The log tab can be turned off.
The website loads nothing from other sites: fonts, textures and the 3D viewer are all served by your own server.

## Screenshots

<div align="center">

**Every player in 3D, wearing their real armor, trims and capes.** Drag to rotate, pick an animation.

<img src="docs/images/player.gif" alt="A player in netherite armor with gold trims, rotating and switching animations" width="760">

**The home page:** totals, playtime per day, when people play and everyone who plays.

<img src="docs/images/overview.png" alt="Home page with totals, charts and player cards" width="800">

**A site level for what you achieved,** not for how long you were online.

<img src="docs/images/player.png" alt="Player page with site level and badges" width="800">

<img src="docs/images/site-level.png" alt="Where the site level comes from" width="800">

**Equipment** with enchantments and armor trims, in the names of your language.

<img src="docs/images/equipment.png" alt="Equipment with enchantments and trims" width="800">

**When it rains in your world, it rains on the website,** with the game's own rain, clouds and moon.

<img src="docs/images/rain.gif" alt="Rain at night, drawn with the game's rain texture" width="800">

**Hall of Fame,** player of the week and best buddies.

<img src="docs/images/hall.png" alt="Hall of Fame" width="800">

<img src="docs/images/week.png" alt="Player of the week and best buddies" width="800">

**The advancement screen** of every player, and **versus** to compare two players.

<img src="docs/images/advancements.png" alt="Advancement screen with tabs" width="800">

<img src="docs/images/versus.png" alt="Two players compared side by side" width="800">

**Leaderboards** for everything, with spinning 3D heads.

<img src="docs/images/leaderboards.gif" alt="Leaderboards with spinning 3D heads" width="760">

**In your language, and on your phone.**

<img src="docs/images/player-es.png" alt="Player page in Spanish, with an elytra" width="560"> <img src="docs/images/mobile.png" alt="The website on a phone" width="220">

</div>

## Try the demo

Want to see it first? The demo shows a made-up server, no Minecraft server needed:

```bash
git clone https://github.com/kylianxdev/mc-server-stats.git && cd mc-server-stats
python3 scripts/fetch_assets.py --version 1.21.10
python3 -m mcstats --demo     # open http://localhost:8200
```

## Requirements

- A Minecraft Java server, 1.21.5 or newer (tested with 26.3, Paper)
- Python 3.11+ (no extra packages needed)
- Read access to the server folder

## Installation

On the machine that runs your Minecraft server:

```bash
curl -fsSL https://raw.githubusercontent.com/kylianxdev/mc-server-stats/main/install.sh | bash
```

The installer finds your server, writes `config.toml`, downloads the textures, installs the datapacks, offers live
equipment updates on Paper and sets up a service that starts automatically. It asks before changing anything;
add `--yes` to accept all defaults. Afterwards open `http://your-server:8200`.

Update later with `~/mc-server-stats/install.sh --update`. All options: `install.sh --help`.

<details>
<summary>Manual installation</summary>

```bash
git clone https://github.com/kylianxdev/mc-server-stats.git
cd mc-server-stats
cp config.example.toml config.toml        # set minecraft.dir to your server folder
python3 scripts/fetch_assets.py --config config.toml
python3 -m mcstats --config config.toml   # http://your-server:8200
```

`fetch_assets.py` downloads the official Minecraft client for your server's version (checksum verified) and extracts the
textures and translations the website needs. Minecraft's assets belong to Mojang, so they're not part of this repository.
Run it again after updating Minecraft (`install.sh --update` does this for you).
</details>

### Datapacks (recommended)

Copy the folders from `datapacks/` into `<server>/world/datapacks/` and run `/reload` (pretty-chat needs a restart):

| Datapack | What it does |
|---|---|
| `afk-meter` | Measures AFK time every second (needed for the AFK numbers) |
| `armor-colors` | Players' name color follows their armor trim, otherwise their chestplate (in chat, tab list and above their head) |
| `pretty-chat` | `<Steve> hi` becomes **Steve** » hi |

The `pack.mcmeta` files are made for pack format 121 (Minecraft 26.x). For other versions, change `min_format`/`max_format`.

### Real-time equipment (Paper)

Player files are normally saved every 5 minutes. To see armor changes within seconds, set in `config/paper-global.yml`:

```yaml
player-auto-save:
  max-per-tick: 2
  rate: 200   # every 10 seconds; only player files, cheap
```

### Run as a service

See `deploy/mc-server-stats.service` (systemd). To serve it on port 80/443, put it behind a reverse proxy such as Caddy or nginx.

## Configuration

Everything is in `config.toml`. See [`config.example.toml`](config.example.toml): the server folder, port, site title,
languages, privacy options and the AFK threshold.

## Extras

`extras/` contains optional scripts that work well with the website: a world **backup** that warns players in chat
(`backup.sh`), a **chat announcement** with a clickable link to the website (`announce.sh`), a **weekly recap** with the
player of the week in the chat (`weekly-recap.sh`), and a helper that gives the BlueMap plugin a lower CPU priority
(`renice-bluemap.sh`).

To fill "player of the week" and the progress charts right away instead of waiting a week, read your old backups:
`python3 scripts/backfill_history.py --config config.toml --backups /path/to/backups`

## Translations

Website texts live in `web/i18n/<language>.json`. To add a language: copy `en.json`, translate it, add the code to
`languages` in your config, and (if it's a new Minecraft language) to `LANG_CODES` in `scripts/fetch_assets.py`.

## Development

```bash
python3 -m unittest discover -s tests -t .
```

```
mcstats/      Python backend: logs, statistics, site level, scoreboard, skins, HTTP server
web/          the website: index.html, css/, js/ (ES modules), i18n/
datapacks/    afk-meter, armor-colors, pretty-chat
scripts/      fetch_assets.py
extras/       optional helper scripts
deploy/       systemd service
tests/        unit tests
```

## License

MIT, see [LICENSE](LICENSE). Not an official Minecraft product; not approved by or associated with Mojang or Microsoft.
