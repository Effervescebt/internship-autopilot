#!/bin/sh
# Scheduler wrapper for launchd / cron. Trigger it often (at login and every 30 minutes); it runs the
# pipeline only when a slot from schedule.run_hours in config.toml has started and is not yet complete.
# Default slots are 10:00 and 21:00, so postings published during the day are picked up the same evening.
cd "$(dirname "$0")/.." || exit 1
mkdir -p output/logs
TODAY=$(date +%F)

SLOT=$(python3 -m autopilot due) || exit 0

# One run at a time; clear a stale lock older than 3 hours.
LOCK=.run.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180)" ]; then rm -rf "$LOCK"; mkdir "$LOCK"; else exit 0; fi
fi
trap 'rm -rf "$LOCK"' EXIT

# Give up on a slot after 3 failed attempts.
ATTEMPTS="output/logs/.attempts-$TODAY-$SLOT"
n=$(( $(cat "$ATTEMPTS" 2>/dev/null || echo 0) + 1 ))
[ "$n" -gt 3 ] && exit 0
echo "$n" > "$ATTEMPTS"

# After a wake or boot the network can take a while to come back; wait up to 5 minutes for it.
for i in $(seq 1 20); do curl -s -m 5 -o /dev/null https://raw.githubusercontent.com && break; sleep 15; done

# Keep a Mac awake while running (the display may still turn off).
KEEPAWAKE=""
command -v caffeinate >/dev/null && KEEPAWAKE="caffeinate -i"

$KEEPAWAKE python3 -m autopilot scheduled >> "output/logs/run-$TODAY-$SLOT.out" 2>&1

LOG="output/logs/$TODAY-$SLOT.md"
if command -v osascript >/dev/null; then
  if grep -q "^RUN_COMPLETE $TODAY $SLOT" "$LOG" 2>/dev/null; then
    N=$(grep "^RUN_COMPLETE $TODAY $SLOT" "$LOG" | awk '{print $4}')
    osascript -e "display notification \"$N new postings. Open output/Dashboard.html\" with title \"Internship Autopilot\""
  else
    osascript -e 'display notification "Run did not finish; it will be retried" with title "Internship Autopilot"'
  fi
fi
