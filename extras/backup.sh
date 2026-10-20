#!/bin/bash
# Optional: back up the world while the server keeps running (cron, e.g. every 6 hours).
# Turns auto-save off during the backup so the world doesn't change halfway, and tells players in chat.
#
#   MC_DIR=/srv/minecraft BACKUP_DIR=/srv/backups TMUX_SESSION=minecraft ./backup.sh
#
# Expects the server console in a tmux session (tmux new -s minecraft ./start.sh).
set -u

MC_DIR=${MC_DIR:-/srv/minecraft}
WORLD=${WORLD:-world}
BACKUP_DIR=${BACKUP_DIR:-$HOME/backups/minecraft}
KEEP_DAYS=${KEEP_DAYS:-7}
SESSION=${TMUX_SESSION:-minecraft}
LOG="$MC_DIR/logs/latest.log"
OUT="$BACKUP_DIR/${WORLD}_$(date +%Y-%m-%d_%H-%M).tar.zst"

mkdir -p "$BACKUP_DIR"
mc() { tmux send-keys -t "$SESSION" "$1" Enter; }

RUNNING=0
if tmux has-session -t "$SESSION" 2>/dev/null; then
  RUNNING=1
  lines=$(wc -l < "$LOG")
  mc 'tellraw @a [{"text":"💾 ","color":"gold"},{"text":"Making a backup of the world, keep playing!","color":"yellow"}]'
  mc "save-off"
  mc "save-all"  # without "flush": that would freeze the server for a moment
  for _ in $(seq 120); do
    # at midnight latest.log is replaced by a new (shorter) file
    [ "$(wc -l < "$LOG")" -lt "$lines" ] && lines=0
    tail -n +"$((lines + 1))" "$LOG" | grep -q "Saved the game" && break
    sleep 1
  done
  sleep 10  # give the IO threads time to write everything
fi

tar -C "$MC_DIR" --exclude="$WORLD/session.lock" -cf - "$WORLD" server.properties whitelist.json ops.json \
  | zstd -q -T2 -3 -o "$OUT"
status=$?

if [ "$RUNNING" = 1 ]; then
  mc "save-on"
  if [ $status -eq 0 ]; then
    mc 'tellraw @a [{"text":"✔ ","color":"green"},{"text":"Backup done!","color":"green"}]'
  fi
fi

if [ $status -eq 0 ]; then
  echo "$(date) backup done: $OUT ($(du -h "$OUT" | cut -f1))"
  find "$BACKUP_DIR" -name "${WORLD}_*.tar.zst" -mtime +"$KEEP_DAYS" -delete
else
  echo "$(date) BACKUP FAILED (status $status)"
  rm -f "$OUT"
  exit 1
fi
