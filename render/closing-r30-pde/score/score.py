#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r30-pde's scorer (Q109), frozen before the run. Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
42c4de7855d6, pinned in FROZEN.commits). Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, READING, ROW lines, then SUMMARY lines (exit 0)
  score.py q109 ROOT                   Q109's clause rule over the attempt ROOT (below)
  score.py gate STAGE ROOTS...         exit 0 when the stage's gate is open (below)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Readings of a row (reading()): end (the runner's class: ok, fault or hang; a failure, a voided
soft row or a row not run reads nothing); for an ok row job, diff (the tool's), tags (a copy's
`tags:` lines: S:P a 4 KiB whose dwords are the tags of slab S page P, else x), and from the
row's vm_large.txt large (none, or cCODE.lLAYOUT.oORDER), table (intact, CHANGED) and changed
(the region's changed 4 KiB, S:P sorted, or none); for a fault fstat and fpage (the kernel's
first `BIF fault S at A` line: S, and A & ~0xfff); for every row bif (CR_BIF_INT_STAT 0x0c04 and
CR_BIF_FAULT 0x0c08 in the runner's register snapshot after the job, `snap9`), a reading only.
run/hooks.sh's hook_reading is the twin (tests/test_score.py).

A model's row is held when every quantity it predicts equals the reading, FAILED when one
differs, cannot tell when one is missing; a row whose controls did not all pass is cannot tell
(scorekit.gated). Controls: s0's eight (s0-pcopy-K, s0-kcopy-K, s0-pfill-K, s0-kfill-K, K = 1, 2):
a control passes iff every key of its frozen H-REF row equals its reading.

gate STAGE: f1 and f2 open iff the eight s0 controls passed; f45 and f67 also need s0-warm's
H-WARM (the slot mapped over a 4 MiB region, order 10, nothing changed); and no kept file of an
earlier stage of the newest attempt (ROOTS[0]) holds `SGX recovery failed`.

q109 ROOT, the clause rule (README.md "What retires"):
  clause 1, per code 1-5: `translates` when H-DENSE held on every dense row of the code (copy a,
    copy b, the fill) with none FAILED, `faults` when H-FAULT held on every one, `as 4 KiB` or
    `as a section` likewise, else `open`;
  clause 2, over the codes that translate: the table index (clause 1's H-DENSE against H-4K), the
    mask (misalign: H-MASK-S or H-MASK4K) and the offset (ptoff: H-PTOFF-IGN or H-PTOFF-USE), each
    decided when one hypothesis held on every such row of every translating code and none other;
    moot when no code translates and every code has its clause 1 reading (faults, as 4 KiB, as a
    section);
  clause 3, per code 6 and 7: `faults` when H-FAULT held on both rows (fault or recovered hang)
    and the two faults read the same fstat; `taken as a size` when H-ALIAS (or H-ALIAS16) held on
    both; else `open`.
  RETIRE iff the controls passed, every code 1-5 has a clause 1 verdict, clause 2 is decided (or
  moot), and codes 6 and 7 each have a clause 3 verdict; else NARROW, naming what stays open."""
import glob
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

ORDER = ("s0", "f1", "f2", "f45", "f67")
FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {st: ("any:.txt", "any:.dmesg", "any:.snap9.regs", ".vm_large.txt") + FIXED
            for st in ORDER}
CONTROLS = tuple(f"s0-{k}-{i}" for i in (1, 2) for k in ("pcopy", "kcopy", "pfill", "kfill"))
GATES = {"f1": CONTROLS, "f2": CONTROLS, "f45": CONTROLS, "f67": CONTROLS}
WARM_GATED = ("f45", "f67")
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+|0) at (0x[0-9a-f]+|0)")
TAGS = re.compile(r"^tags: va \+0x[0-9a-f]+: first (0x[0-9a-f]+) \(slab (\d+) page (\d+) dword (\d+)\), "
                  r"(\d+)/(\d+) follow it", re.M)
CLAIMS = {
    "H-DENSE": "a PDE of size S translates: entry va / S of its table, the entry's address masked to S",
    "H-4K": "the size field is ignored: 4 KiB entries, entry va / 4 KiB",
    "H-SECTION": "the PDE names the data itself (no table)",
    "H-FAULT": "the BIF does not take the entry: the job faults (or hangs, recovered)",
    "H-MASK-S": "a large entry's address is masked to S (its low bits below S are ignored)",
    "H-MASK4K": "a large entry's address is used to 4 KiB (the offset in the page added to it)",
    "H-PTOFF-IGN": "the PDE's bits 11:4 are ignored: the table starts at the PDE's page",
    "H-PTOFF-USE": "the PDE's bits 11:4 offset the table in its page",
    "H-4K-PTOFF": "4 KiB entries from a table offset by the PDE's bits 11:4",
    "H-ALIAS": "the unnamed code is taken as a size (any but 16 KiB, or 4 KiB entries)",
    "H-ALIAS16": "the unnamed code is taken as 16 KiB",
    "H-WARM": "the 4 MiB region was had right after the boot, the GPU never touched it",
}


def producible(row):
    a = row["args"].split()
    keys = {"job", "diff", "large", "table", "changed"} if a[:1] in (["copy"], ["fill"]) else set()
    if a[:1] == ["copy"] and "--src-addr" in a:
        keys.add("tags")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n, r in cases.items():
        K.text(d, n + ".txt")
        K.text(d, n + ".dmesg")
        K.text(d, n + ".snap9.regs")
        if r["class"] == "ok":
            K.text(d, n + ".vm_large.txt")


# ---- readings (run/hooks.sh's hook_reading is the twin) ---------------------------------------
def tags_of(text):
    out = []
    for first, s, p, dw, fo, n in TAGS.findall(text or ""):
        out.append(f"{s}:{p}" if first.startswith("0xa") and dw == "0" and fo == n else "x")
    return ",".join(out) if out else None


def large_of(text):
    """{large, table, changed} of a vm_large.txt."""
    if text is None or not text.strip():
        return {}
    lines = text.splitlines()
    if lines[0].strip() == "none":
        return {"large": "none"}
    out = {}
    m = re.match(r"addr 0x[0-9a-f]+ code (\d+) layout (\d+) ", lines[0])
    o = re.search(r"^region 0x[0-9a-f]+ \+0x[0-9a-f]+ order (\d+)$", text, re.M)
    if m and o:
        out["large"] = f"c{m.group(1)}.l{m.group(2)}.o{o.group(1)}"
    t = re.search(r"^table (\S+) ", text, re.M)
    if t:
        out["table"] = t.group(1)
    ch = sorted({(int(s), int(p)) for s, p in
                 re.findall(r"^slab (\d+) page (\d+): \d+ changed", text, re.M)})
    out["changed"] = ",".join(f"{s}:{p}" for s, p in ch) or "none"
    return out


def tool_of(text):
    out = {}
    j = re.search(r"^job: (\w+)", text or "", re.M)
    if j:
        out["job"] = j.group(1)
    d = re.search(r"^diff: (\d+) of ", text or "", re.M)
    if d:
        out["diff"] = d.group(1)
    t = tags_of(text)
    if t:
        out["tags"] = t
    return out


def regval(text, reg):
    m = re.search(rf"^reg {reg} (\S+)", text or "", re.M)
    return m.group(1) if m else None


def reading(cases, d, n):
    """{quantity: value} of a kept row ({} when it did not run, failed or was voided)."""
    r = cases.get(n)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return {}
    out = {"end": r["class"]}
    snap = K.text(d, n + ".snap9.regs")
    if snap:
        out["bif"] = f"{regval(snap, '0x0c04')}/{regval(snap, '0x0c08')}"
    if r["class"] == "fault":
        f = FAULT.findall(K.text(d, n + ".dmesg") or "")
        if f:
            out["fstat"], out["fpage"] = f[0][0], f"{int(f[0][1], 16) & ~0xfff:#x}"
    if r["class"] == "ok":
        out.update(tool_of(K.text(d, n + ".txt")))
        out.update(large_of(K.text(d, n + ".vm_large.txt")))
    return out


def model_state(pred, rd, hang_is_fault=False):
    """hang_is_fault (f67 only): a hang the kernel recovered reads as H-FAULT's end (the BIF did
    not take the code); in f1, f2 and f45 a hang is no model's end (hook_fault ends the session)."""
    if not rd:
        return None
    if rd.get("end") != pred.get("end"):
        if not (hang_is_fault and pred.get("end") == "fault" and rd.get("end") == "hang"):
            return False
    states = [None if rd.get(q) is None else rd[q] == v for q, v in pred.items() if q != "end"]
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


# ---- the attempt ------------------------------------------------------------------------------
def find_stage(roots, st):
    for root in roots:
        d = os.path.join(root, st)
        if os.path.isdir(d) and (os.path.exists(os.path.join(d, "cases.tsv")) or
                                 os.path.exists(os.path.join(d, "cases.tsv.gz"))):
            return d
    return None


def s0_controls(d):
    """{control: PASS True / FAILED False / cannot tell None}, the CONTROL lines, and s0-warm's
    H-WARM state."""
    preds = K.predictions(KP, "s0")
    cases = K.rows(d, "cases.tsv")
    out, lines = {}, []
    for n in CONTROLS:
        want = {q: mv["H-REF"] for q, mv in preds.get(n, {}).items()}
        rd = reading(cases, d, n)
        if not rd or rd.get("end") != "ok":
            out[n] = None
            c = cases.get(n)
            lines.append(f"CONTROL {n}: did not complete ({c['class'] if c else 'not run'}): cannot tell")
            continue
        bad = {q: rd.get(q) for q, v in want.items() if rd.get(q) != v}
        out[n] = not bad
        lines.append(f"CONTROL {n}: " + ("every frozen key read (" + ", ".join(sorted(want)) + ")" if not bad else
                                         "differs: " + ", ".join(f"{q} {v} (frozen {want[q]})" for q, v in sorted(bad.items())))
                     + f": {cword(out[n])}")
    wp = {q: mv["H-WARM"] for q, mv in preds.get("s0-warm", {}).items()}
    wrd = reading(cases, d, "s0-warm")
    warm = model_state(wp, wrd)
    lines.append(f"WARM s0-warm: {wrd or 'no reading (voided, failed or not run)'}: {word(warm)}")
    return out, lines, warm


def s0_named(roots):
    s0 = find_stage(roots, "s0")
    if s0 is None:
        return {n: None for n in CONTROLS}, [f"CONTROL {n}: s0 not kept: cannot tell" for n in CONTROLS], None
    return s0_controls(s0)


def recovery_failed(root, stage):
    """The kept files of the stages before STAGE in ROOT that hold `SGX recovery failed`."""
    hits = []
    for st in ORDER[:ORDER.index(stage)]:
        for p in sorted(glob.glob(os.path.join(root, st, "*"))):
            if os.path.isdir(p):
                continue
            try:
                b = gzip.open(p).read() if p.endswith(".gz") else open(p, "rb").read()
            except (OSError, EOFError):
                continue
            if b"SGX recovery failed" in b:
                hits.append(os.path.relpath(p, root))
    return hits


def stage_models(stage):
    preds = K.predictions(KP, stage)
    models = {}
    for n, qs in preds.items():
        for q, mv in qs.items():
            for m, v in mv.items():
                models.setdefault(m, {}).setdefault(n, {})[q] = v
    return models


def row_states(stage, d, roots):
    """{model: {row: state}}, the controls, and the READING and ROW lines of a flagged stage."""
    cases, tab = K.rows(d, "cases.tsv"), K.table(KP, stage)
    ctl, lines, _ = s0_named(roots)
    g = SK.gate(ctl)
    models = stage_models(stage)
    st = {m: {} for m in models}
    for r in tab:
        n = r["name"]
        rd = reading(cases, d, n)
        lines.append(f"READING {n}: {rd or 'no reading (did not run, failed or voided)'}")
        for m in sorted(models):
            if n in models[m]:
                s = SK.gated(g, model_state(models[m][n], rd, hang_is_fault=stage == "f67"))
                st[m][n] = s
                lines.append(f"ROW {n} {m}: (frozen {models[m][n]}): {word(s)}")
    return st, ctl, lines


def score_stage(stage, d, roots):
    roots = roots or [os.path.dirname(d)]
    st, ctl, lines = row_states(stage, d, roots)
    for m in sorted(st):
        lines.append(f"SUMMARY: {stage}: {m}: " + SK.headline(CLAIMS[m], ctl, list(st[m].values())))
    return lines


def score_s0(d, roots):
    ctl, lines, warm = s0_controls(d)
    g = SK.gate(ctl)
    for st in GATES:
        probs = list(g.problems) + (["s0-warm: no 4 MiB region"] if st in WARM_GATED and warm is not True else [])
        lines.append(f"GATE {st}: {'open' if not probs else 'closed: ' + '; '.join(probs)}")
    lines.append(f"SUMMARY: s0: {sum(1 for v in ctl.values() if v)} of {len(ctl)} references passed; "
                 f"s0-warm {word(warm)}")
    return lines


# ---- Q109's clause rule -------------------------------------------------------------------------
def code_rows(stage, code, suffixes):
    return [f"c{code}-{s}" for s in suffixes if f"c{code}-{s}" in K.predictions(KP, stage)]


def all_held(states, names, model):
    v = [states.get(model, {}).get(n) for n in names]
    return bool(names) and all(s is True for s in v)


def q109_rule(root):
    roots = [root]
    ctl, _, _ = s0_named(roots)
    states = {}
    for stage in ("f1", "f2", "f45", "f67"):
        d = find_stage(roots, stage)
        if d is None:
            continue
        st, _, _ = row_states(stage, d, roots)
        for m, rows in st.items():
            states.setdefault(m, {}).update(rows)
    lines = []
    c1 = {}
    for code in (1, 2, 3, 4, 5):
        stage = "f1" if code <= 3 else "f45"
        names = code_rows(stage, code, ("a", "b", "f"))
        v = "open"
        for m, label in (("H-DENSE", "translates"), ("H-FAULT", "faults"), ("H-4K", "as 4 KiB"),
                         ("H-SECTION", "as a section")):
            if all_held(states, names, m):
                v = label
                break
        c1[code] = v
        lines.append(f"Q109 CLAUSE 1 code {code}: {v}")
    tr = [c for c, v in c1.items() if v == "translates"]
    c2 = {}
    for part, models, suffix in (("mask", ("H-MASK-S", "H-MASK4K"), "m"),
                                 ("offset", ("H-PTOFF-IGN", "H-PTOFF-USE"), "o")):
        names = [n for c in tr if c <= 4 for n in code_rows("f2" if c <= 3 else "f45", c, (suffix,))]
        held = [m for m in models if all_held(states, names, m)]
        c2[part] = held[0] if len(held) == 1 else "open"
    c2["index"] = "H-DENSE" if tr else "open"
    # moot: no named code translates and each has its reading (it faults, or the size field is
    # not taken): a larger page has no layout or mask of its own to measure
    moot = not tr and all(v != "open" for v in c1.values())
    c2ok = moot or all(v != "open" for v in c2.values())
    lines.append("Q109 CLAUSE 2: " + ("moot: no named code translates (" + ", ".join(sorted(set(c1.values())))
                                      + ")" if moot else
                                      ", ".join(f"{k} {v}" for k, v in sorted(c2.items()))
                                      + f" (over codes {tr or 'none'})"))
    c3 = {}
    for code in (6, 7):
        names = [f"c{code}-u1", f"c{code}-u2"]
        v = "open"
        if all_held(states, names, "H-FAULT"):
            d = find_stage(roots, "f67")
            rds = [reading(K.rows(d, "cases.tsv"), d, n) for n in names] if d else []
            ends = {r.get("end") for r in rds}
            fs = {r.get("fstat") for r in rds}
            if ends == {"fault"} and len(fs) == 1 and None not in fs:
                v = f"faults, BIF status {fs.pop()} both times"
            elif ends == {"hang"}:
                v = "stalls: no BIF fault, a hang the kernel recovered, both times"
            else:
                v = "open: the two rows read " + ", ".join(f"{r.get('end')} {r.get('fstat') or ''}".strip() for r in rds)
        elif all_held(states, names, "H-ALIAS"):
            v = "taken as a size (not 16 KiB)"
        elif all_held(states, names, "H-ALIAS16"):
            v = "taken as 16 KiB"
        c3[code] = v
        lines.append(f"Q109 CLAUSE 3 code {code}: {v}")
    cok = all(v is True for v in ctl.values())
    open_parts = ([f"clause 1 code {c}" for c, v in c1.items() if v == "open"] +
                  ([] if c2ok else [f"clause 2 {k}" for k, v in sorted(c2.items()) if v == "open"]) +
                  [f"clause 3 code {c}" for c, v in c3.items() if v.startswith("open")])
    if not cok:
        open_parts.insert(0, "the s0 controls did not all pass")
    lines.append("Q109 RULE: " + ("RETIRE (every clause has its reading)" if not open_parts else
                                  "NARROW: open " + "; ".join(open_parts)))
    return lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        st, roots = argv[2], argv[3:]
        if st not in GATES:
            print(f"gate {st}: open (not gated)")
            return 0
        problems = []
        if roots:
            hits = recovery_failed(roots[0], st)
            if hits:
                problems.append("SGX recovery failed in " + ", ".join(hits[:3]))
        ctl, _, warm = s0_named(roots)
        g = SK.gate({n: ctl.get(n) for n in GATES[st]})
        if not g.ok:
            problems += g.problems
        if st in WARM_GATED and warm is not True:
            problems.append("s0-warm did not read its 4 MiB region (H-WARM " + word(warm) + ")")
        print(f"gate {st}: " + ("open" if not problems else "closed: " + "; ".join(problems)))
        return 1 if problems else 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q109":
        print("\n".join(q109_rule(argv[2])))
        return 0
    if len(argv) >= 3 and argv[1] in ORDER:
        st, d, roots = argv[1], argv[2], argv[3:]
        print("\n".join(score_s0(d, roots) if st == "s0" else score_stage(st, d, roots)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
