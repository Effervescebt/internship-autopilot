"""Keyword-based resume tailoring. No AI service needed.

Every bullet in profile.toml carries a list of keywords. A bullet scores one point per keyword
found in the job title + description (title hits count double). Entries marked `core = true` always
appear; other entries and extra bullets are added in score order while the page still fits.
"""
import re
import shutil
import subprocess
from pathlib import Path
from string import Template

from .config import ROOT

# Common JD technologies, used only to report "gaps" (asked for but not in your profile).
TECH_TERMS = [
    "python", "java", "c++", "golang", "rust", "javascript", "typescript", "react", "node.js",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis", "kafka", "spark", "hadoop", "flink",
    "airflow", "dbt", "snowflake", "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "linux",
    "git", "pytorch", "tensorflow", "jax", "hugging face", "langchain", "llm", "nlp", "computer vision",
    "reinforcement learning", "recommendation", "ranking", "distributed systems", "microservices",
    "graphql", "ci/cd", "tableau", "pandas", "numpy", "scikit-learn", "cuda",
]

LATEX_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                 "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s):
    return "".join(LATEX_SPECIAL.get(ch, ch) for ch in str(s))


def hits(keyword, text):
    k = re.escape(keyword.lower())
    return re.search(rf"(?<![a-z0-9]){k}(?![a-z0-9])", text) is not None


def score_bullet(b, title, text):
    return sum((2 if hits(k, title) else 1) for k in b.get("keywords", []) if hits(k, text))


def header_tex(p, cfg):
    person = p["person"]
    contact = [esc(x) for x in (person.get("email"), person.get("phone")) if x]
    contact += [rf"\href{{{l['url']}}}{{{esc(l.get('text', l['url']))}}}" for l in person.get("links", [])]
    avail = cfg.get("resume", {}).get("availability", "")
    if avail:
        contact.append(esc(avail))
    sep = r" \textbar{} "
    return (rf"\begin{{center}}{{\LARGE\bfseries {esc(person['name'])}}}\par\vspace{{0.2em}}"
            rf"\small {sep.join(contact)}\end{{center}}\vspace{{-0.6em}}")


def education_tex(p, drop_details=False):
    out = [r"\rsection{Education}"]
    for e in p.get("education", []):
        out.append(rf"\entry{{{esc(e['school'])}}}{{{esc(e.get('location', ''))}}}"
                   rf"{{{esc(e['degree'])}}}{{{esc(e.get('dates', ''))}}}")
        if not drop_details:
            out += [esc(d) + r"\par" for d in e.get("details", [])]
    return "\n".join(out)


def entry_tex(entry, bullets):
    if entry.get("role"):
        head = (rf"\entry{{{esc(entry['heading'])}}}{{{esc(entry.get('location', ''))}}}"
                rf"{{{esc(entry['role'])}}}{{{esc(entry.get('dates', ''))}}}")
    else:
        head = rf"\project{{{esc(entry['heading'])}}}{{{esc(entry.get('dates', ''))}}}"
    items = "".join(rf"\item {esc(b['text'])}" + "\n" for b in bullets)
    return head + "\n\\begin{itemize}\n" + items + "\\end{itemize}"


def skills_tex(p, title, text):
    lines = []
    for g in p.get("skills", {}).get("groups", []):
        items = sorted(g["items"], key=lambda i: not hits(i, text))  # JD matches first
        lines.append(rf"{{\bfseries {esc(g['label'])}:}} {esc(', '.join(items))}")
    return r"\rsection{Skills}" + "\n" + "\\\\\n".join(lines) if lines else ""


class Plan:
    """Which entries/bullets are on the page. Entries keep profile order inside each section."""

    def __init__(self, profile, title, text):
        self.p, self.title, self.text = profile, title.lower(), text
        self.chosen = {}  # (section index, entry index) -> list of bullet indexes
        self.queue = []   # optional additions, best first
        for si, sec in enumerate(profile.get("section", [])):
            for ei, entry in enumerate(sec.get("entries", [])):
                scored = sorted(((score_bullet(b, self.title, text), bi)
                                 for bi, b in enumerate(entry.get("bullets", []))), reverse=True)
                if entry.get("core"):
                    keep = entry.get("min_bullets", len(scored))
                    self.chosen[(si, ei)] = [bi for _, bi in scored[:keep]]
                    extra = scored[keep:]
                else:
                    extra = scored
                for rank, (s, bi) in enumerate(extra):
                    # an entry's first bullet carries the heading's cost, so rank it slightly lower
                    self.queue.append((s - (0.5 if rank == 0 and not entry.get("core") else 0), si, ei, bi))
        self.queue.sort(key=lambda x: -x[0])

    def render(self, cfg, drop_edu_details=False):
        body = [education_tex(self.p, drop_edu_details)]
        for si, sec in enumerate(self.p.get("section", [])):
            parts = []
            for ei, entry in enumerate(sec.get("entries", [])):
                bis = sorted(self.chosen.get((si, ei), []))
                if bis:
                    parts.append(entry_tex(entry, [entry["bullets"][b] for b in bis]))
            if parts:
                body.append(rf"\rsection{{{esc(sec['title'])}}}" + "\n" + "\n".join(parts))
        body.append(skills_tex(self.p, self.title, self.text))
        tpl = Template((ROOT / "templates" / "resume.tex").read_text())
        return tpl.substitute(header=header_tex(self.p, cfg), body="\n".join(body))

    def included_keywords(self):
        kws = set()
        for (si, ei), bis in self.chosen.items():
            for bi in bis:
                kws |= {k.lower() for k in self.p["section"][si]["entries"][ei]["bullets"][bi].get("keywords", [])}
        for g in self.p.get("skills", {}).get("groups", []):
            kws |= {i.lower() for i in g["items"]}
        return kws

    def summary(self):
        names = []
        for si, sec in enumerate(self.p.get("section", [])):
            for ei, entry in enumerate(sec.get("entries", [])):
                if self.chosen.get((si, ei)):
                    names.append(entry["heading"])
        return names


def compile_pdf(tex, folder):
    """Compile resume.tex in folder; return page count (0 on failure)."""
    (folder / "resume.tex").write_text(tex)
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-quiet", "resume.tex"],
                       cwd=folder, capture_output=True, text=True)
    pdf = folder / "resume.pdf"
    if not pdf.exists():
        return 0
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        return int(m.group(1)) if m else 0
    log = (folder / "resume.log").read_text(errors="replace")
    m = re.search(r"Output written on .*?\((\d+) page", log)
    return int(m.group(1)) if m else 0


def clean(folder, pdf_name):
    subprocess.run(["latexmk", "-c", "resume.tex"], cwd=folder, capture_output=True)
    for ext in ("out", "fdb_latexmk", "fls", "aux", "log", "synctex.gz"):
        (folder / f"resume.{ext}").unlink(missing_ok=True)
    (folder / "resume.pdf").replace(folder / pdf_name)


def tailor(profile, cfg, title, jd, folder):
    """Build the best one-page resume for this posting. Returns (fit 1-5, notes)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    text = f"{title}\n{jd}".lower()
    plan = Plan(profile, title, text)
    pages = cfg.get("resume", {}).get("page_limit", 1)
    drop_edu = False
    if compile_pdf(plan.render(cfg), folder) > pages:
        drop_edu = True  # core alone overflows: shorten education, then give up gracefully
        if compile_pdf(plan.render(cfg, True), folder) > pages:
            print(f"  warning: core entries alone exceed {pages} page(s); shorten them in profile.toml")
    misses = 0
    for s, si, ei, bi in plan.queue:
        if misses >= 3:
            break
        plan.chosen.setdefault((si, ei), []).append(bi)
        if compile_pdf(plan.render(cfg, drop_edu), folder) > pages:
            plan.chosen[(si, ei)].remove(bi)
            misses += 1
    compile_pdf(plan.render(cfg, drop_edu), folder)
    clean(folder, cfg.get("resume", {}).get("pdf_name", "Resume.pdf"))

    wanted = {t for t in TECH_TERMS if hits(t, text)}
    have = plan.included_keywords()
    matched = sorted(t for t in wanted if t in have or any(hits(t, k) for k in have))
    gaps = sorted(wanted - set(matched))
    fit = 3 if len(wanted) < 3 else max(1, min(5, round(1 + 4 * len(matched) / len(wanted))))
    notes = (f"Included: {', '.join(plan.summary())}. Matched: {', '.join(matched) or '-'}. "
             f"Gaps: {', '.join(gaps) or '-'}.")
    if not jd:
        notes = "No job description could be downloaded; tailored on the title only. " + notes
    return fit, notes
