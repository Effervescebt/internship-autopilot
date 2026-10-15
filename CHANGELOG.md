# Changelog

## 0.3.0 - 2026-10-15

### Added

- `eligibility.skip_no_sponsorship` (off by default) skips postings that explicitly refuse visa
  sponsorship for the role, including "now or in the future" and "authorized to work for any employer".
- Every kept posting gets a sponsorship note: `[No sponsorship]`, `[Borderline]` (no sponsorship only for
  a later full-time role, or no sponsorship but F-1/CPT students eligible) or `[No sponsorship info]`
  (the job description does not mention sponsorship or work authorization).
- `autopilot/skills.py`: skills the job description mentions move to the front of each skills line, and
  each line is trimmed to exactly one rendered line using widths measured by LaTeX.
- Skills groups accept an `extra` list of skills that are shown only when a posting asks for them.
- The resume notes list JD skills you have that did not fit on the skills lines.

### Changed

- `run_daily.sh` waits up to five minutes for the network after a wake or boot before running.

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
