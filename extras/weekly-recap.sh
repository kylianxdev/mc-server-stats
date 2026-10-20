#!/bin/bash
# Optional: post "Player of the week" in the game chat (cron, e.g. Sundays at 20:00:
#   0 20 * * 0  STATS_URL=http://your-server:8200 /path/to/mc-server-stats/extras/weekly-recap.sh
# Uses the language and history of the website. Skipped when nobody is online.
set -u
SESSION=${TMUX_SESSION:-minecraft}
DIR="$(cd "$(dirname "$0")/.." && pwd)"

tmux has-session -t "$SESSION" 2>/dev/null || exit 0
grep -q "There are 0 of" <(tmux send-keys -t "$SESSION" "list" Enter; sleep 1; tmux capture-pane -p -t "$SESSION" -S -3) && exit 0

MSG=$(cd "$DIR" && python3 -m mcstats --config "$DIR/config.toml" --recap --url "${STATS_URL:-}" 2>/dev/null) || exit 0
[ -n "$MSG" ] && tmux send-keys -t "$SESSION" "tellraw @a $MSG" Enter
