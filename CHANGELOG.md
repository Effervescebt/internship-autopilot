# Changelog

## 0.2.0 - 2026-09-30

### Changed

- Runs twice a day instead of once. The daily quota (`search.per_day`) is split across
  `schedule.run_hours`, which defaults to 10:00 and 21:00, so postings published during the day are
  picked up the same evening instead of the next morning.
- A run that follows missed runs makes up their share of the daily quota.
- `run_daily.sh` now asks `python3 -m autopilot due` whether a run is due; each run writes its own log
  (`output/logs/<date>-<slot>.md`) and continues the folder numbering of earlier runs that day.
- `python3 -m autopilot run` runs one quota by default and accepts an explicit count.
- The launchd example triggers at both run hours.

### Added

- `autopilot/schedule.py` with run slot and quota logic.
- Unit tests for scheduling and eligibility filtering, run by GitHub Actions on Python 3.11 to 3.13.

## 0.1.0 - 2026-09-29

- Initial release: SimplifyJobs collection, eligibility filtering, keyword-based resume tailoring with
  LaTeX page fitting, static dashboard with status tracking, spreadsheet export, launchd/cron scheduling.
