"""Command line: python3 -m autopilot <command>

  scheduled  run if a scheduled slot is due (used by scripts/run_daily.sh); otherwise exit quietly
  due        print the name of the slot that is due and not yet complete (exit status 1 if none)
  run [N]    run now: add N postings (default: one slot's quota)
  build      regenerate Dashboard.html / applications.xlsx and import saved statuses
  tailor     tailor one resume by hand:  python3 -m autopilot tailor "Job title" jd.txt [out_folder]
  status     show how many postings were added today
"""
import datetime as dt
import re
import sys
import time
from pathlib import Path

from . import filters, schedule, sources, tailor
from .config import load_config, load_profile
from .tracker import Store


def slug(s, n=24):
    return re.sub(r"[^A-Za-z0-9]+", "", s.title())[:n] or "Job"


def ranked_candidates(cfg, store):
    s = cfg["search"]
    today = dt.date.today()
    priority = [c.lower() for c in s.get("priority_companies", [])]
    fresh = s.get("fresh_days", 2)
    skip_citizenship = cfg["eligibility"].get("skip_citizenship_required", True)
    out = []
    for c in sources.fetch_candidates(cfg):
        if not filters.title_ok(c["title"], cfg) or not filters.location_ok(c["location"], cfg):
            continue
        if store.is_seen(c):
            continue
        if skip_citizenship and c.get("sponsorship") == "U.S. Citizenship is Required":
            continue
        try:
            c["age"] = (today - dt.date.fromisoformat(c["posted"])).days
        except ValueError:
            c["age"] = 999
        c["priority"] = any(p in c["company"].lower() for p in priority)
        out.append(c)
    # newest first (fresh window, then within a week, then older); priority companies first in each
    bucket = lambda c: 0 if c["age"] <= fresh else 1 if c["age"] <= 7 else 2
    out.sort(key=lambda c: (bucket(c), not c["priority"], c["age"]))
    seen, uniq = set(), []
    for c in out:  # one posting per (company, title)
        k = (c["company"].lower(), c["title"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def schedule_settings(cfg):
    hours = cfg.get("schedule", {}).get("run_hours", [10, 21])
    return hours, cfg["search"].get("per_day", 20)


def log_path(cfg, day, slot):
    return cfg["paths"]["output_dir"] / "logs" / f"{day}-{slot}.md"


def slot_complete(cfg, day, slot):
    try:
        return f"RUN_COMPLETE {day} {slot}" in log_path(cfg, day, slot).read_text()
    except FileNotFoundError:
        return False


def due_slot(cfg):
    """(slot name, slot hour) if a scheduled run is due and not complete, else None."""
    hours, _ = schedule_settings(cfg)
    hour = schedule.current_slot(dt.datetime.now().hour, hours)
    if hour is None:
        return None
    name = schedule.slot_name(hour)
    return None if slot_complete(cfg, dt.date.today().isoformat(), name) else (name, hour)


def run(target, slot):
    cfg, profile = load_config(), load_profile()
    store = Store(cfg)
    store.import_statuses()
    today = dt.date.today().isoformat()
    day_dir = cfg["paths"]["output_dir"] / "applications" / today
    per_company = cfg["search"].get("max_per_company", 3)
    per_co = {}
    for j in store.jobs:
        if j["date"] == today:
            per_co[j["company"]] = per_co.get(j["company"], 0) + 1
    index = len([p for p in day_dir.iterdir() if p.is_dir()]) if day_dir.exists() else 0
    added, skipped = 0, []

    cands = ranked_candidates(cfg, store)
    print(f"{slot}: {len(cands)} new candidates, target {target}")
    for c in cands:
        if added >= target:
            break
        if per_co.get(c["company"], 0) >= per_company:
            continue
        jd = sources.job_description(c)
        time.sleep(0.5)
        reason, visa = filters.eligibility(c, jd, cfg)
        if reason:
            store.mark(c, "skipped", reason)
            skipped.append((c, reason))
            continue
        added += 1
        index += 1
        folder = day_dir / f"{index:02d}_{slug(c['company'])}_{slug(c['title'], 30)}"
        print(f"[{added}/{target}] {c['company']} - {c['title']}")
        fit, notes = tailor.tailor(profile, cfg, c["title"], jd, folder)
        (folder / "jd.txt").write_text(f"{c['company']} - {c['title']}\n{c['location']}\n{c['url']}\n\n{jd}")
        rel = folder.relative_to(cfg["paths"]["output_dir"])
        store.add({"id": c["id"], "date": today, "slot": slot, "company": c["company"], "title": c["title"],
                   "location": c["location"], "url": c["url"], "posted": c["posted"],
                   "role_type": filters.role_type(c["title"]), "priority": c["priority"], "fit": fit,
                   "visa_note": visa, "notes": notes, "status": "To apply",
                   "pdf": str(rel / cfg.get("resume", {}).get("pdf_name", "Resume.pdf")),
                   "jd": str(rel / "jd.txt")})
        per_co[c["company"]] = per_co.get(c["company"], 0) + 1
    store.build()
    write_log(cfg, today, slot, store, skipped, added)


def write_log(cfg, today, slot, store, skipped, added):
    log = log_path(cfg, today, slot)
    log.parent.mkdir(parents=True, exist_ok=True)
    rows = [j for j in store.jobs if j["date"] == today and j.get("slot") == slot]
    lines = [f"# {today} ({slot})\n", "| Company | Title | Type | Fit | Visa note |", "|---|---|---|---|---|"]
    lines += [f"| {j['company']} | {j['title']} | {j['role_type']} | {j['fit']} | {j['visa_note']} |" for j in rows]
    reasons = {}
    for _, r in skipped:
        reasons[r] = reasons.get(r, 0) + 1
    lines += ["", f"Skipped {len(skipped)}: " + ", ".join(f"{r} ({n})" for r, n in reasons.items()), "",
              f"RUN_COMPLETE {today} {slot} {added}"]
    log.write_text("\n".join(lines) + "\n")
    print(f"done: {added} postings in this run; log at {log}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd in ("scheduled", "due"):
        cfg = load_config()
        slot = due_slot(cfg)
        if cmd == "due":
            print(slot[0] if slot else "")
            sys.exit(0 if slot else 1)
        if not slot:
            print("no scheduled run is due")
            return
        hours, per_day = schedule_settings(cfg)
        today = dt.date.today().isoformat()
        done = sum(j["date"] == today for j in Store(cfg).jobs)
        run(schedule.target(slot[1], hours, per_day, done), slot[0])
    elif cmd == "run":
        cfg = load_config()
        hours, per_day = schedule_settings(cfg)
        n = int(argv[1]) if len(argv) > 1 else max(schedule.quotas(hours, per_day).values())
        run(n, "manual-" + dt.datetime.now().strftime("%H%M"))
    elif cmd == "build":
        Store(load_config()).build()
    elif cmd == "tailor":
        if len(argv) < 3:
            sys.exit('usage: python3 -m autopilot tailor "Job title" jd.txt [out_folder]')
        out = Path(argv[3] if len(argv) > 3 else "tailored")
        fit, notes = tailor.tailor(load_profile(), load_config(), argv[1], Path(argv[2]).read_text(), out)
        print(f"fit {fit}/5 -> {out}\n{notes}")
    elif cmd == "status":
        store, today = Store(load_config()), dt.date.today().isoformat()
        print(f"today: {sum(j['date'] == today for j in store.jobs)} postings; total: {len(store.jobs)}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
