"""Job sources. Ships with the SimplifyJobs community internship list.

To add another source, write a function that returns a list of candidate dicts with the keys
id, source, company, title, location, url, posted (YYYY-MM-DD) and sponsorship, then call it from
fetch_candidates(). Respect each site's terms of use; many job boards forbid automated scraping.
"""
import datetime as dt
import html
import json
import re
import time
import urllib.request

UA = "internship-autopilot (+https://github.com/Effervescebt/internship-autopilot)"


def get(url, retries=3, timeout=25):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - network errors of every kind are retried
            if getattr(e, "code", None) == 404:
                return ""
            time.sleep(2 * (i + 1))
    return ""


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n- ", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def fetch_simplify(cfg):
    s = cfg["search"]
    raw = get(s["simplify_listings_url"])
    if not raw:
        print("warning: could not download the SimplifyJobs list")
        return []
    cutoff = time.time() - s.get("max_age_days", 14) * 86400
    term = s["term"].lower()
    cats = set(s.get("categories", []))
    out = []
    for x in json.loads(raw):
        if not (x.get("active") and x.get("is_visible", True)):
            continue
        if not any(term in t.lower() for t in x.get("terms", [])):
            continue
        if cats and x.get("category") not in cats:
            continue
        if max(x.get("date_posted", 0), x.get("date_updated", 0)) < cutoff:
            continue
        out.append({
            "id": "sj-" + x["id"], "source": "SimplifyJobs",
            "company": x.get("company_name", ""), "title": x.get("title", ""),
            "location": "; ".join(x.get("locations", [])),
            "url": x.get("url", "").replace("?embed=true", ""),
            "posted": dt.date.fromtimestamp(x.get("date_posted", 0)).isoformat(),
            "sponsorship": x.get("sponsorship", ""),
        })
    return out


def fetch_candidates(cfg):
    return fetch_simplify(cfg)


def job_description(c):
    """Best-effort plain-text JD. Uses public ATS APIs where possible; returns '' if unavailable."""
    url = c["url"]
    gh = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)", url)
    if gh:
        j = get(f"https://boards-api.greenhouse.io/v1/boards/{gh.group(1)}/jobs/{gh.group(2)}")
        if j:
            return strip_html(html.unescape(json.loads(j).get("content", "")))
    ghj = re.search(r"gh_jid=(\d+)", url)
    if ghj:
        slug = re.sub(r"[^a-z0-9]", "", c["company"].lower())
        j = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{ghj.group(1)}")
        if j:
            return strip_html(html.unescape(json.loads(j).get("content", "")))
    lever = re.search(r"jobs\.lever\.co/([\w-]+)/([\w-]+)", url)
    if lever:
        j = get(f"https://api.lever.co/v0/postings/{lever.group(1)}/{lever.group(2)}")
        if j:
            d = json.loads(j)
            parts = [d.get("descriptionPlain", "")]
            parts += [l.get("text", "") + "\n" + strip_html(l.get("content", "")) for l in d.get("lists", [])]
            return "\n\n".join(parts + [d.get("additionalPlain", "")])
    ashby = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url)
    if ashby:
        j = get(f"https://api.ashbyhq.com/posting-api/job-board/{ashby.group(1)}")
        if j:
            for p in json.loads(j).get("jobs", []):
                if p.get("id") == ashby.group(2):
                    return p.get("descriptionPlain") or strip_html(p.get("descriptionHtml", ""))
    text = strip_html(get(url))
    return text if len(text) > 800 else ""  # JS-rendered career sites return almost nothing
