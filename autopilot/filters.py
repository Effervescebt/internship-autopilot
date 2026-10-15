"""Title, location and eligibility rules. All patterns can be extended from config.toml."""
import re

US_STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
             "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
US_LOC = re.compile(r"\b(USA?|United States|Remote)\b|,\s*(" + "|".join(US_STATES) + r")\b|\b(SF|NYC|LA)\b")
CITIZENSHIP = re.compile(
    r"u\.?s\.? citizen(ship)? (is )?required|must be a u\.?s\.? citizen|us citizens? only|"
    r"citizenship is required|security clearance|secret clearance|\bts/sci\b|clearance (is )?required|"
    r"\bitar\b|export control|green card holders? only|permanent residents? only", re.I)
F1_EXCLUDED = re.compile(
    r"not (be )?eligible for (any )?(international students|f-?1|j-?1|cpt|opt|visa)|"
    r"(f-?1|j-?1|cpt|opt)[^.]{0,40}(are|is) not eligible|"
    r"cannot (accept|consider) (students on |candidates on )?(f-?1|cpt|opt)", re.I)
NO_SPONSOR = re.compile(r"(not|unable to|will not|cannot|won't) (to )?(provide |offer )?(visa )?sponsor|"
                        r"(not|un)able to (provide |offer )?(visa |immigration )?sponsorship|"
                        r"(not|without) (requiring|require|need|needing) (current or future |now or in the future )?"
                        r"(visa |employment |immigration )?sponsorship|"
                        r"sponsorship (is )?not (available|offered|provided)", re.I)
# Explicit refusals that also cover the internship itself.
NOW_OR_FUTURE = re.compile(r"(now or in the future|current or future|currently or in the future|"
                           r"now or at any (point|time) in the future)[^.]{0,60}sponsor|"
                           r"sponsor[^.]{0,60}(now or in the future|current or future|currently or in the future)",
                           re.I)
ANY_EMPLOYER = re.compile(r"authori[sz]ed to work (in the u\.?s\.? )?for any employer", re.I)
# Statements that only rule out sponsorship for a later full-time role.
FUTURE_ONLY = re.compile(r"(future|full[- ]time|conversion|return offer|post[- ]graduation|after graduation)"
                         r"[^.]{0,60}sponsor|sponsor[^.]{0,60}(future (full[- ]time )?employment|full[- ]time|"
                         r"conversion|return offer|after graduation|upon graduation)", re.I)
AUTH_MENTION = re.compile(r"sponsor|work authori[sz]ation|authori[sz]ed to work|\bvisa\b|\bcpt\b|\bopt\b|f-?1\b",
                          re.I)
CPT_WELCOME = re.compile(r"(f-?1|cpt)[^.]{0,60}(eligible|welcome|accepted)", re.I)
PHD_ONLY = re.compile(r"(must be|currently) (currently )?(pursuing|enrolled in) a ph\.?d|"
                      r"(obtaining|pursuing) a ph\.?d\.? degree|\(phd\)|phd intern", re.I)
MASTERS_OK = re.compile(r"master.?s|\bm\.?s\.?\b|\bms/phd|bs/ms", re.I)


def title_ok(title, cfg):
    s = cfg["search"]
    t = title.lower()
    if not any(re.search(p, t, re.I) for p in s.get("title_must_match", [r"\bintern"])):
        return False
    return not any(re.search(p, t, re.I) for p in s.get("title_exclude", []))


def location_ok(location, cfg):
    return not cfg["eligibility"].get("us_only", True) or not location or bool(US_LOC.search(location))


def role_type(title):
    t = title.lower()
    if re.search(r"data (scien|analy|engineer)|analytics|analyst", t):
        return "Data"
    if re.search(r"research|scientist", t):
        return "Research"
    if re.search(r"machine learning|\bml\b|\bai\b|deep learning|llm|nlp|vision|perception", t):
        return "MLE"
    return "SWE"


def sponsorship_status(c, jd):
    """Classify what a posting says about visa sponsorship.

    Returns "refuses" (explicitly no sponsorship for this role), "future_only" (only rules out sponsoring a
    later full-time role), "refuses_but_cpt" (no sponsorship, but F-1/CPT students are eligible),
    "cpt_welcome", "unstated" (nothing about sponsorship or work authorization), "unknown" (no job
    description), or "other" (mentions work authorization without a clear refusal).
    """
    text = f"{c['title']}\n{jd}"
    tagged = c.get("sponsorship") == "Does Not Offer Sponsorship"
    refusal = tagged or bool(NO_SPONSOR.search(text) or ANY_EMPLOYER.search(text) or NOW_OR_FUTURE.search(text))
    if CPT_WELCOME.search(text):
        return "refuses_but_cpt" if refusal else "cpt_welcome"
    if ANY_EMPLOYER.search(text) or NOW_OR_FUTURE.search(text):
        return "refuses"
    if FUTURE_ONLY.search(text):
        return "future_only"
    if refusal:
        return "refuses"
    if not jd:
        return "unknown"
    return "other" if AUTH_MENTION.search(text) else "unstated"


VISA_NOTES = {
    "refuses": "[No sponsorship] States no visa sponsorship; confirm CPT/OPT is fine with the recruiter",
    "future_only": "[Borderline] Only rules out sponsorship for a later full-time role",
    "refuses_but_cpt": "[Borderline] States no sponsorship, but says F-1/CPT students are eligible",
    "cpt_welcome": "JD says F-1/CPT students are eligible",
    "unstated": "[No sponsorship info] JD does not mention sponsorship or work authorization",
    "unknown": "[No sponsorship info] No job description available",
    "other": "",
}


def eligibility(c, jd, cfg):
    """Return (skip_reason or None, visa_note)."""
    e = cfg["eligibility"]
    text = f"{c['title']}\n{jd}"
    if e.get("skip_citizenship_required", True) and (
            c.get("sponsorship") == "U.S. Citizenship is Required" or CITIZENSHIP.search(text)):
        return "citizenship / clearance required", ""
    if e.get("skip_if_f1_excluded", True) and F1_EXCLUDED.search(text):
        return "excludes F-1 / CPT / OPT students", ""
    if e.get("skip_phd_only", True) and PHD_ONLY.search(text) and not MASTERS_OK.search(text):
        return "PhD only", ""
    for pattern in e.get("extra_skip_patterns", []):
        if re.search(pattern, text, re.I):
            return f"matches skip pattern: {pattern}", ""
    status = sponsorship_status(c, jd)
    if status == "refuses" and e.get("skip_no_sponsorship", False):
        return "no visa sponsorship", ""
    if status == "refuses" and not e.get("note_no_sponsorship", True):
        return None, ""
    return None, VISA_NOTES[status]
