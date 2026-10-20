#!/usr/bin/env bash
# mc-server-stats installer
#
#   curl -fsSL https://raw.githubusercontent.com/kylianxdev/mc-server-stats/main/install.sh | bash
#   ./install.sh [options]
#
# Options:
#   --minecraft-dir DIR   your server folder (default: detected)
#   --port PORT           website port (default: 8200)
#   --lang CODE           default language: en, nl, es, de, fr (default: from your system)
#   --install-dir DIR     where to put mc-server-stats (default: ~/mc-server-stats)
#   --yes                 don't ask, use the defaults
#   --no-service          don't install the systemd service
#   --no-datapacks        don't copy the datapacks into the world
#   --update              update an existing installation (git pull, textures, restart)
set -euo pipefail

REPO_URL="${MCSTATS_REPO:-https://github.com/kylianxdev/mc-server-stats.git}"
INSTALL_DIR="${HOME}/mc-server-stats"
MC_DIR="" PORT="8200" LANG_CODE="" YES=0 SERVICE=1 DATAPACKS=1 UPDATE=0

c_g=$'\e[32m' c_y=$'\e[33m' c_r=$'\e[31m' c_b=$'\e[1m' c_0=$'\e[0m'
say()  { echo "${c_g}==>${c_0} ${c_b}$*${c_0}"; }
warn() { echo "${c_y}!${c_0} $*"; }
die()  { echo "${c_r}✗ $*${c_0}" >&2; exit 1; }
ask() {  # ask "question" default -> answer (reads from the terminal, also when piped from curl)
  local q=$1 def=$2 ans
  if [ "$YES" = 1 ] || [ ! -r /dev/tty ]; then echo "$def"; return; fi
  read -r -p "$q [$def] " ans </dev/tty || true
  echo "${ans:-$def}"
}
yes_no() { [[ "$(ask "$1 (y/n)" "${2:-y}")" =~ ^[YyJj] ]]; }
usage() {
  cat <<'USAGE'
mc-server-stats installer

  ./install.sh [options]

  --minecraft-dir DIR   your server folder (default: detected)
  --port PORT           website port (default: 8200)
  --lang CODE           default language: en, nl, es, de, fr (default: from your system)
  --install-dir DIR     where to put mc-server-stats (default: ~/mc-server-stats)
  --yes                 don't ask, use the defaults
  --no-service          don't install the systemd service
  --no-datapacks        don't copy the datapacks into the world
  --update              update an existing installation (git pull, textures, restart)
USAGE
}
need() { [ $# -ge 2 ] || die "$1 needs a value (see --help)"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --minecraft-dir) need "$@"; MC_DIR=$2; shift ;;
    --port) need "$@"; PORT=$2; shift ;;
    --lang) need "$@"; LANG_CODE=$2; shift ;;
    --install-dir) need "$@"; INSTALL_DIR=$2; shift ;;
    --yes|-y) YES=1 ;;
    --no-service) SERVICE=0 ;;
    --no-datapacks) DATAPACKS=0 ;;
    --update) UPDATE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac
  shift
done

# ---------------------------------------------------------------- requirements
command -v python3 >/dev/null || die "Python 3.11+ is needed (sudo apt install python3)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || die "Python 3.11+ is needed, found $(python3 --version)"
command -v git >/dev/null || die "git is needed (sudo apt install git)"

# ---------------------------------------------------------------- get the code
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -n "$HERE" ] && [ -f "$HERE/mcstats/__init__.py" ]; then
  INSTALL_DIR=$HERE  # running from a clone
elif [ -d "$INSTALL_DIR/.git" ]; then
  :
else
  say "Downloading mc-server-stats to $INSTALL_DIR"
  git clone -q --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

restart_service() {  # only the service that belongs to this installation
  if systemctl cat mc-server-stats 2>/dev/null | grep -qx "WorkingDirectory=$INSTALL_DIR"; then
    sudo systemctl restart mc-server-stats && say "Restarted the mc-server-stats service"
  fi
}

if [ "$UPDATE" = 1 ]; then
  say "Updating"
  git pull --ff-only
  python3 scripts/fetch_assets.py --config config.toml
  restart_service
  say "Up to date: $(python3 -c 'import mcstats; print(mcstats.__version__)')"
  exit 0
fi

# ---------------------------------------------------------------- find the Minecraft server
if [ -z "$MC_DIR" ]; then
  say "Looking for your Minecraft server…"
  mapfile -t found < <(find "$HOME" /srv /opt /home /var/lib -maxdepth 4 -name server.properties -printf '%h\n' 2>/dev/null | sort -u | head -10)
  if [ ${#found[@]} -eq 0 ]; then
    MC_DIR=$(ask "Where is your Minecraft server (the folder with server.properties)?" "/srv/minecraft")
  elif [ ${#found[@]} -eq 1 ]; then
    MC_DIR=$(ask "Minecraft server found. Use this folder?" "${found[0]}")
  else
    echo "Found several servers:"; printf '  %s\n' "${found[@]}"
    MC_DIR=$(ask "Which one?" "${found[0]}")
  fi
fi
MC_DIR=$(cd "$MC_DIR" && pwd) || die "Folder $MC_DIR does not exist"
[ -f "$MC_DIR/server.properties" ] || die "No server.properties in $MC_DIR. Is this a Minecraft server folder?"
WORLD=$(sed -n 's/^level-name=//p' "$MC_DIR/server.properties" | tr -d '\r')
WORLD=${WORLD:-world}
say "Server: $MC_DIR (world: $WORLD)"

# ---------------------------------------------------------------- config.toml
if [ -z "$LANG_CODE" ]; then
  sys_lang=$(echo "${LANG:-en}" | cut -c1-2)
  case "$sys_lang" in en|nl|es|de|fr) LANG_CODE=$sys_lang ;; *) LANG_CODE=en ;; esac
fi
if [ -f config.toml ]; then
  warn "config.toml already exists, keeping it"
else
  PORT=$(ask "Port for the website?" "$PORT")
  TITLE=$(ask "Title of the website?" "Server Stats")
  python3 - "$MC_DIR" "$WORLD" "$PORT" "$LANG_CODE" "$TITLE" <<'EOF'
import json, re, sys
mc, world, port, lang, title = sys.argv[1:]
text = open("config.example.toml", encoding="utf-8").read()
for key, value in (("dir", mc), ("world", world), ("title", title), ("default_language", lang)):
    text = re.sub(rf'^{key} = ".*"$', f"{key} = {json.dumps(value)}", text, count=1, flags=re.M)
text = re.sub(r"^port = \d+$", f"port = {int(port)}", text, count=1, flags=re.M)
open("config.toml", "w", encoding="utf-8").write(text)
EOF
  say "Wrote config.toml (edit it any time, then restart)"
fi
PORT=$(sed -n 's/^port = \([0-9]*\)$/\1/p' config.toml | head -1)

# ---------------------------------------------------------------- textures & translations
say "Downloading textures and translations from Mojang…"
python3 scripts/fetch_assets.py --config config.toml

# ---------------------------------------------------------------- datapacks
if [ "$DATAPACKS" = 1 ] && [ -d "$MC_DIR/$WORLD" ]; then
  if yes_no "Install the datapacks (AFK meter, armor colors, nicer chat) into your world?" y; then
    mkdir -p "$MC_DIR/$WORLD/datapacks"
    for pack in afk-meter armor-colors pretty-chat; do
      rm -rf "${MC_DIR:?}/$WORLD/datapacks/$pack"
      cp -r "datapacks/$pack" "$MC_DIR/$WORLD/datapacks/"
    done
    say "Datapacks installed. Type /reload in the server console (the nicer chat needs a restart)"
  fi
fi

# ---------------------------------------------------------------- Paper: save player data more often
PAPER="$MC_DIR/config/paper-global.yml"
if [ -f "$PAPER" ] && grep -q "^  rate: -1$" "$PAPER" && grep -q "^player-auto-save:" "$PAPER"; then
  if yes_no "Paper detected. Save player files every 10 s, so armor changes show up live on the website?" y; then
    cp "$PAPER" "$PAPER.bak"
    python3 - "$PAPER" <<'EOF'
import sys
path = sys.argv[1]
text = open(path).read()
text = text.replace("player-auto-save:\n  max-per-tick: -1\n  rate: -1\n", "player-auto-save:\n  max-per-tick: 2\n  rate: 200\n", 1)
open(path, "w").write(text)
EOF
    say "Done (backup: paper-global.yml.bak), takes effect after the next server restart"
  fi
fi

# ---------------------------------------------------------------- service
if [ "$SERVICE" = 1 ] && command -v systemctl >/dev/null && [ -d /run/systemd/system ] && command -v sudo >/dev/null; then
  if yes_no "Run the website as a service (starts automatically, also after a reboot)?" y; then
    sudo tee /etc/systemd/system/mc-server-stats.service >/dev/null <<EOF
[Unit]
Description=mc-server-stats (Minecraft statistics website)
After=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$INSTALL_DIR
ExecStart=$(command -v python3) -m mcstats --config $INSTALL_DIR/config.toml
Restart=on-failure
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now mc-server-stats >/dev/null 2>&1
    sudo systemctl restart mc-server-stats
    SERVICE=2
  fi
fi

# ---------------------------------------------------------------- done
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
say "Done! 🎉"
if [ "$SERVICE" = 2 ]; then
  sleep 2
  systemctl is-active --quiet mc-server-stats && echo "  The website runs at:  ${c_b}http://${IP:-localhost}:$PORT${c_0}" \
    || warn "The service didn't start, see: journalctl -u mc-server-stats -n 30"
  echo "  Logs:    journalctl -u mc-server-stats -f"
else
  echo "  Start the website with:  cd $INSTALL_DIR && python3 -m mcstats --config config.toml"
  echo "  Then open:  http://${IP:-localhost}:$PORT"
fi
echo "  Update later with:  $INSTALL_DIR/install.sh --update"
echo "  Settings:           $INSTALL_DIR/config.toml"
