#!/usr/bin/env python3
"""Writes the draft records under p1131/draft/: evidence E541-E548, questions Q159-Q166 and the five narrowed ones,
the removal of Q117, the probe wrappers. python3 -B gen/gen_records.py from p1131/. Reads ~/src/resgx545 (landed, read only)."""
import json, pathlib, re, shutil, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from records_ev import EV
from records_q import NEW, NARROW
LANDED = pathlib.Path.home() / "src/resgx545"
D = ROOT / "draft"
for sub in ("evidence", "questions", "probes"):
    if (D / sub).exists():
        shutil.rmtree(D / sub)
def slug(t, n=150):
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return s[:n].strip("-")
def q(s): return json.dumps(s, ensure_ascii=True)
def lst(xs): return "[" + ", ".join(q(x) for x in xs) + "]"
import textwrap
def wrap(text, width=100):
    """Re-wraps each paragraph (blank-line separated) to 100 columns; tables and the front-matter-like lines are kept."""
    out = []
    for para in re.split(r"\n\s*\n", text.strip("\n")):
        lines = para.split("\n")
        if lines[0].startswith("|"):
            out.append(para)
        else:
            out.append(textwrap.fill(" ".join(x.strip() for x in lines), width, break_long_words=False, break_on_hyphens=False))
    return "\n\n".join(out)
for e in EV:
    d = D / "evidence" / e["unit"]; d.mkdir(parents=True, exist_ok=True)
    head = "+++\nid = %s\nclaim = %s\nunit = %s\nmethod = %s\ntiers = %s\ndate = %s\ndata = %s\nterms = %s\n+++\n\n" % (
        q(e["id"]), q(e["claim"]), q(e["unit"]), q(e["method"]), lst(e["tiers"]), q(e["date"]), lst(e["data"]), lst(e["terms"]))
    (d / ("%s-%s.md" % (e["id"], slug(e["claim"])))).write_text(head + wrap(e["body"]) + "\n")
for n in NEW:
    d = D / "questions" / n["unit"]; d.mkdir(parents=True, exist_ok=True)
    lines = ["+++", "id = %s" % q(n["id"]), "question = %s" % q(n["question"]), "unit = %s" % q(n["unit"]), "kind = %s" % q(n["kind"])]
    if n.get("value"):
        lines.append("value = %s" % q(n["value"]))
    lines += ["phase = %d" % n["phase"], "evidence = %s" % lst(n["evidence"]), "terms = %s" % lst(n["terms"]), "+++", ""]
    (d / ("%s-%s.md" % (n["id"], slug(n["question"])))).write_text("\n".join(lines) + "\n" + wrap(n["body"]) + "\n")
for qid, spec in NARROW.items():
    src = next(LANDED.glob("questions/*/%s-*.md" % qid))
    text = src.read_text()
    m = re.search(r"^evidence = \[(.*?)\]$", text, re.M)
    ev = [x.strip().strip('"') for x in m[1].split(",") if x.strip()]
    ev += [x for x in spec["add"] if x not in ev]
    text = text[:m.start()] + "evidence = " + lst(ev) + text[m.end():]
    d = D / "questions" / src.parent.name; d.mkdir(parents=True, exist_ok=True)
    (d / src.name).write_text(text.rstrip("\n") + "\n\n" + wrap(spec["text"]) + "\n")
(D / "removed.txt").write_text("questions/ta/Q117-points-and-point-sizes.md\t# retired: answered by E544 (tools/records/questions.py RETIRED gets \"Q117\": \"answered by E544\")\n")
print(len(EV), "evidence,", len(NEW), "new questions,", len(NARROW), "narrowed")
