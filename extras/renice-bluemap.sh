#!/bin/bash
# Optional, for servers running the BlueMap plugin: give BlueMap's render threads the lowest CPU
# priority (nice 19), so map rendering never competes with the game itself.
# Java ignores thread priorities on Linux, so this is done per thread from the outside.
# Run from cron every few minutes (BlueMap creates new threads after a reload).
PID=$(pgrep -f "java.*\.jar" | head -1) || exit 0
for t in /proc/"$PID"/task/*; do
  case "$(cat "$t/comm" 2>/dev/null)" in
    BlueMap*) renice -n 19 -p "${t##*/}" >/dev/null 2>&1 ;;
  esac
done
