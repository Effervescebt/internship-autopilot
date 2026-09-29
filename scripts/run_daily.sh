#!/bin/sh
# Daily wrapper for schedulers (launchd / cron). Runs `python3 -m autopilot run` at most once per day,
# and only after RUN_HOUR, so it can be triggered repeatedly (at login, every 30 minutes) to catch up
# after the computer was asleep or off.
RUN_HOUR=${RUN_HOUR:-10}
cd "$(dirname "$0")/.." || exit 1
mkdir -p output/logs
TODAY=$(date +%F)

[ "$(date +%H)" -lt "$RUN_HOUR" ] && exit 0
grep -q "^RUN_COMPLETE $TODAY" "output/logs/$TODAY.md" 2>/dev/null && exit 0

# One run at a time; clear a stale lock older than 3 hours.
LOCK=.run.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180)" ]; then rm -rf "$LOCK"; mkdir "$LOCK"; else exit 0; fi
fi
trap 'rm -rf "$LOCK"' EXIT

# Give up after 3 failed attempts in one day.
ATTEMPTS="output/logs/.attempts-$TODAY"
n=$(( $(cat "$ATTEMPTS" 2>/dev/null || echo 0) + 1 ))
[ "$n" -gt 3 ] && exit 0
echo "$n" > "$ATTEMPTS"

# Keep a Mac awake while running (the display may still turn off).
KEEPAWAKE=""
command -v caffeinate >/dev/null && KEEPAWAKE="caffeinate -i"

$KEEPAWAKE python3 -m autopilot run >> "output/logs/run-$TODAY.out" 2>&1

if command -v osascript >/dev/null; then
  if grep -q "^RUN_COMPLETE $TODAY" "output/logs/$TODAY.md" 2>/dev/null; then
    N=$(grep "^RUN_COMPLETE $TODAY" "output/logs/$TODAY.md" | awk '{print $3}')
    osascript -e "display notification \"$N new postings. Open output/Dashboard.html\" with title \"Internship Autopilot\""
  else
    osascript -e 'display notification "Run did not finish; will retry later" with title "Internship Autopilot"'
  fi
fi
