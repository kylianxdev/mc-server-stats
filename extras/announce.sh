#!/bin/bash
# Optional: post a clickable link to the stats website in the game chat (cron, e.g. every 2 hours).
# Skipped when nobody is online.
#
#   STATS_URL=http://your-server:8200 MESSAGE="Want to see live statistics?" ./announce.sh
set -u

SESSION=${TMUX_SESSION:-minecraft}
URL=${STATS_URL:?set STATS_URL, e.g. http://your-server:8200}
MESSAGE=${MESSAGE:-"Want to see live statistics, or who secretly cheats? 👀"}
LABEL=${LABEL:-"[View the stats]"}

tmux has-session -t "$SESSION" 2>/dev/null || exit 0
grep -q "There are 0 of" <(tmux send-keys -t "$SESSION" "list" Enter; sleep 1; tmux capture-pane -p -t "$SESSION" -S -3) && exit 0

json() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }
tmux send-keys -t "$SESSION" "tellraw @a [{\"text\":\"📊 \",\"color\":\"gold\"},{\"text\":$(json "$MESSAGE "),\"color\":\"yellow\"},{\"text\":$(json "$LABEL"),\"color\":\"green\",\"underlined\":true,\"click_event\":{\"action\":\"open_url\",\"url\":$(json "$URL")},\"hover_event\":{\"action\":\"show_text\",\"value\":$(json "$URL")}}]" Enter
