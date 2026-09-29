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
NO_SPONSOR = re.compile(r"(not|unable to|will not|cannot|won't) (to )?(provide |offer )?(visa )?sponsor", re.I)
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
    note = ""
    if CPT_WELCOME.search(text):
        note = "JD says F-1/CPT students are eligible"
    elif e.get("note_no_sponsorship", True) and (
            c.get("sponsorship") == "Does Not Offer Sponsorship" or NO_SPONSOR.search(text)):
        note = "States no sponsorship; interns on CPT usually fine, confirm with recruiter"
    return None, note
