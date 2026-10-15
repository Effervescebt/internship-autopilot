"""Skills section: JD-matched skills first, and every group kept to exactly one rendered line.

Widths are measured by LaTeX itself with the resume template's fonts and margins (one extra compile per
resume), so a skills line never wraps a word or two onto a second line. Items the job description asks
for go first; a group's `extra` items are skills you have that are only shown when a posting asks for them.
"""
import re
import subprocess
import tempfile
from pathlib import Path

from .config import ROOT

MARGIN_PT = 2.0  # safety margin against rounding


def esc(s):
    from .tailor import esc as _esc
    return _esc(s)


def mentions(item, text):
    """True if the JD text mentions this skill (or any alternative written as "A/B" or "Name (ABBR)")."""
    names = {item}
    m = re.match(r"(.+?)\s*\((.+)\)$", item)
    if m:
        names |= {m.group(1), m.group(2)}
    names |= {part for n in list(names) for part in n.split("/") if len(part) > 1}
    for n in names:
        k = re.escape(n.lower().strip())
        if re.search(rf"(?<![a-z0-9]){k}(?![a-z0-9+#])", text):
            return True
    return False


def ordered_items(group, text):
    """JD-mentioned items first (profile order kept), then the rest; extras only when mentioned."""
    base = list(group.get("items", []))
    extra = [i for i in group.get("extra", []) if mentions(i, text)]
    wanted = [i for i in base if mentions(i, text)] + extra
    return wanted, wanted + [i for i in base if i not in wanted]


def line_tex(label, items):
    return rf"{{\bfseries {esc(label)}:}} {esc(', '.join(items))}"


def measure(strings):
    """Natural widths (pt) of LaTeX snippets typeset with the resume template; also the line width."""
    tpl = (ROOT / "templates" / "resume.tex").read_text()
    pre = tpl[: tpl.index(r"\begin{document}")]
    body = [r"\newlength{\w}", r"\typeout{WIDTH linewidth \the\linewidth}"]
    for i, s in enumerate(strings):
        body.append(rf"\settowidth{{\w}}{{{s}}}\typeout{{WIDTH {i} \the\w}}")
    doc = pre + "\\begin{document}\n" + "\n".join(body) + "\n\\mbox{}\n\\end{document}\n"
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "m.tex").write_text(doc)
        out = subprocess.run(["pdflatex", "-interaction=nonstopmode", "m.tex"], cwd=d,
                             capture_output=True, text=True).stdout
    widths = {k: float(v) for k, v in re.findall(r"WIDTH (\S+) ([\d.]+)pt", out)}
    if "linewidth" not in widths:
        return None, None
    return widths["linewidth"], [widths.get(str(i), 0.0) for i in range(len(strings))]


def fit_groups(groups, text):
    """Return (lines as LaTeX, every skill shown on the page, JD-asked skills that did not fit)."""
    plans = []
    for g in groups:
        wanted, items = ordered_items(g, text)
        plans.append((g["label"], wanted, items))
    # Measure every prefix of every line in one compile; prefixes are what we may end up showing.
    snippets, index = [], []
    for gi, (label, _, items) in enumerate(plans):
        for n in range(1, len(items) + 1):
            index.append((gi, n))
            snippets.append(line_tex(label, items[:n]))
    linewidth, widths = measure(snippets) if snippets else (None, None)
    best = {gi: len(items) for gi, (_, _, items) in enumerate(plans)}  # unmeasured: show everything
    if linewidth:
        limit = linewidth - MARGIN_PT
        best = {gi: 1 for gi in range(len(plans))}
        for (gi, n), w in zip(index, widths):
            if w <= limit:
                best[gi] = max(best[gi], n)
    lines, shown, missing = [], [], []
    for gi, (label, wanted, items) in enumerate(plans):
        keep = items[: best[gi]]
        lines.append(line_tex(label, keep))
        shown += keep
        missing += [i for i in wanted if i not in keep]
    return lines, shown, missing
