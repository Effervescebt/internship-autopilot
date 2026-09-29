"""Command line: python3 -m autopilot <command>

  run      find today's new postings, tailor a resume for each, update Dashboard.html (the daily job)
  build    only regenerate Dashboard.html / applications.xlsx (and import saved statuses)
  tailor   tailor one resume by hand:  python3 -m autopilot tailor "Job title" jd.txt [out_folder]
  status   show how many postings were added today
"""
import datetime as dt
import re
import sys
import time
from pathlib import Path

from . import filters, sources, tailor
from .config import load_config, load_profile
from .tracker import Store


def slug(s, n=24):
    return re.sub(r"[^A-Za-z0-9]+", "", s.title())[:n] or "Job"


def ranked_candidates(cfg, store):
    s = cfg["search"]
    today = dt.date.today()
    priority = [c.lower() for c in s.get("priority_companies", [])]
    fresh = s.get("fresh_days", 2)
    out = []
    for c in sources.fetch_candidates(cfg):
        if not filters.title_ok(c["title"], cfg) or not filters.location_ok(c["location"], cfg):
            continue
        if store.is_seen(c) or c.get("sponsorship") == "U.S. Citizenship is Required" and \
                cfg["eligibility"].get("skip_citizenship_required", True):
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
    # one posting per (company, title)
    seen, uniq = set(), []
    for c in out:
        k = (c["company"].lower(), c["title"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def run():
    cfg, profile = load_config(), load_profile()
    store = Store(cfg)
    store.import_statuses()
    today = dt.date.today().isoformat()
    day_dir = cfg["paths"]["output_dir"] / "applications" / today
    s = cfg["search"]
    per_day, per_company = s.get("per_day", 20), s.get("max_per_company", 3)
    done_today = [j for j in store.jobs if j["date"] == today]
    added, skipped, per_co = len(done_today), [], {}
    for j in done_today:
        per_co[j["company"]] = per_co.get(j["company"], 0) + 1

    cands = ranked_candidates(cfg, store)
    print(f"{len(cands)} new candidates")
    for c in cands:
        if added >= per_day:
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
        folder = day_dir / f"{added:02d}_{slug(c['company'])}_{slug(c['title'], 30)}"
        print(f"[{added}/{per_day}] {c['company']} - {c['title']}")
        fit, notes = tailor.tailor(profile, cfg, c["title"], jd, folder)
        (folder / "jd.txt").write_text(f"{c['company']} - {c['title']}\n{c['location']}\n{c['url']}\n\n{jd}")
        rel = folder.relative_to(cfg["paths"]["output_dir"])
        store.add({"id": c["id"], "date": today, "company": c["company"], "title": c["title"],
                   "location": c["location"], "url": c["url"], "posted": c["posted"],
                   "role_type": filters.role_type(c["title"]), "priority": c["priority"], "fit": fit,
                   "visa_note": visa, "notes": notes, "status": "To apply",
                   "pdf": str(rel / cfg.get("resume", {}).get("pdf_name", "Resume.pdf")),
                   "jd": str(rel / "jd.txt")})
        per_co[c["company"]] = per_co.get(c["company"], 0) + 1
    store.build()
    write_log(cfg, today, store, skipped, added)


def write_log(cfg, today, store, skipped, added):
    log = cfg["paths"]["output_dir"] / "logs" / f"{today}.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    rows = [j for j in store.jobs if j["date"] == today]
    lines = [f"# {today}\n", "| Company | Title | Type | Fit | Visa note |", "|---|---|---|---|---|"]
    lines += [f"| {j['company']} | {j['title']} | {j['role_type']} | {j['fit']} | {j['visa_note']} |" for j in rows]
    reasons = {}
    for _, r in skipped:
        reasons[r] = reasons.get(r, 0) + 1
    lines += ["", f"Skipped {len(skipped)}: " + ", ".join(f"{r} ({n})" for r, n in reasons.items()), "",
              f"RUN_COMPLETE {today} {added}"]
    log.write_text("\n".join(lines) + "\n")
    print(f"done: {added} postings today; log at {log}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd == "run":
        run()
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
