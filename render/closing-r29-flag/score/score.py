#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r29-flag's scorer, frozen before the run. Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
c0571816c4ff, pinned in FROZEN.commits). Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py q010 ROOT                   Q010's retire rule (R29-3 a) over the attempt ROOT
  score.py gate STAGE ROOTS...         exit 0 when the stage's gate is open (below)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Readings of a row (every stage): end (the runner's class: ok, fault or hang; a failure reads
nothing), fstat and fpage (the row's FIRST kernel `BIF fault S at A` line: S, and A & ~0xfff),
image (an ok probe's 2048 `row Y:` tokens, "%08x", raster order, one space, sha256), hash (an ok
tri's or copy's `target: WxH hash H`), o0 (present: an ok probe --tri's `o0` line). A model's row
is held when every quantity it predicts equals the reading, FAILED when one differs, cannot tell
when one is missing; a row whose controls did not all pass is cannot tell (scorekit.gated).

s0 (the references): a control passes iff every key of its frozen H-REF row equals its reading
(readings.tsv, the runner's hook_reading; f1-ref-a's image from its text). GATES names the s0
controls of each flagged stage.

Controls by question: Q108 (f1) rf-c-depth, f1-ref-a; Q139 (f2) f2-ctl-256, c-512; Q010 (h1's
copies q010-af and q010-p1, h2's q010-p2) s0's four c10- copies and h1's q010-ld2, q010-pre; Q163
(h2's h2-a3, h2-b3, h2-c3) h2's own h2-c-b (end ok, o0 present). A Q010 copy is scored only after
its recovery (premise): q010-af after at least one fault in f1 or f2 of the attempt, q010-p1 after
q010-h1 hung, q010-p2 after q010-h2 hung; else cannot tell.

gate STAGE: open iff every s0 control GATES[STAGE] names passed (the newest attempt that kept s0)
and no kept file of an earlier stage of the newest attempt (ROOTS[0]) holds `SGX recovery failed`
(a failed recovery anywhere closes every later stage; hook_fault also ends the session on it)."""
import glob
import gzip
import hashlib
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

ORDER = ("s0", "f1", "f2", "h1", "h2")
FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {st: (".txt", ".dmesg") + FIXED for st in ORDER}
GATES = {"f1": ("rf-c-depth", "f1-ref-a"), "f2": ("f2-ctl-256", "c-512"),
         "h1": ("c10-zc", "c10-zn", "c10-bc", "c10-bn"), "h2": ()}
Q010_S0 = GATES["h1"]
Q010_H1 = ("q010-ld2", "q010-pre")
Q010_ROWS = {"q010-af": None, "q010-p1": "q010-h1", "q010-p2": "q010-h2"}
Q163_ROWS = ("h2-a3", "h2-b3", "h2-c3")
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
CLAIMS = {
    "H-WO-READ": "WRITEONLY with EDMPROTECT faults a read as WRITEONLY alone (0x80200 load, 0x80002 texture)",
    "H-EDM-TYPE": "with both flags a read faults with EDMPROTECT's type (0xa0200, 0xa0002), as a write",
    "H-PASS": "with both flags the ZLS load and the texture read complete",
    "H-KIND": "E1073's kind: an empty-axis macrotile word faults 0x90004 (the TA's header write)",
    "H-AXIS": "the TA's empty-axis write faults at a page fixed by the axis (x 0x20008, y 0x20010)",
    "H-SIZE": "the TA's empty-axis write moves with the TA data's end (x end + 2 pages, y end + 10)",
    "H-KEEP": "no recovered fault or hang clears colour-space set 0 (a copy without the load reads the last set)",
    "H-RECOV-CLR": "a recovered fault or hang clears colour-space set 0 to zeros",
    "H-B24-HANG": "VDM index list header bit 24 alone hangs E414's job (E737)",
    "H-PREV16": "a block-2 v = 1 job completes iff the job before it completed with a block at v 1 or 6",
    "D-PREVADD": "a block-2 v = 1 job completes iff the job before it completed with a non-zero add",
    "D-C": "a block-2 v = 1 job hangs iff E700's c is 0 or 5 (fitted lookup)",
    "H-ALWAYS": "every block-2 v = 1 job hangs on this module family",
}


def producible(row):
    a = row["args"].split()
    if a[:1] == ["tri"]:
        keys = {"job", "hash"}
        if "--depth" in a:
            keys.add("depthat")
            if "--depth-store" in a and "--depth-dump" in a:
                keys.add("zstore")
        if "--dump-render" in a:
            keys.add("tadata")
        return keys
    if a[:1] == ["copy"]:
        return {"job", "hash"}
    if a[:1] == ["probe"]:
        keys = {"pixels", "scratchat"}
        if "--tri" in a:
            keys.add("o0")
        return keys
    return set()


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        K.text(d, n + ".dmesg")


def image_sha(text):
    toks = []
    for ln in (text or "").splitlines():
        if ": row " in ln or ln.startswith("row "):
            toks += [t.lower().zfill(8) for t in ln.split(": ", 2)[-1].split()]
    return hashlib.sha256(" ".join(toks).encode()).hexdigest() if len(toks) == 2048 else None


def reading(cases, d, n):
    """{quantity: value} of a kept row ({} when it did not run or failed)."""
    r = cases.get(n)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return {}
    out = {"end": r["class"]}
    text = K.text(d, n + ".txt")
    if r["class"] == "fault":
        f = FAULT.findall(K.text(d, n + ".dmesg"))
        if f:
            out["fstat"], out["fpage"] = f[0][0], f"{int(f[0][1], 16) & ~0xfff:#x}"
    if r["class"] == "ok":
        img = image_sha(text)
        if img:
            out["image"] = img
        if any(": o0 " in ln for ln in text.splitlines()):
            out["o0"] = "present"
        h = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", text, re.M)
        if h:
            out["hash"] = h.group(1)
        j = re.search(r"^job: (\w+)", text, re.M)
        if j:
            out["job"] = j.group(1)
    return out


def model_state(pred, rd):
    if not rd:
        return None
    if rd.get("end") != pred.get("end"):
        return False
    states = [None if rd.get(q) is None else rd[q] == v for q, v in pred.items() if q != "end"]
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


# ---- s0 -----------------------------------------------------------------------------------
def s0_controls(d):
    """{control: PASS True / FAILED False / cannot tell None}, and the CONTROL lines."""
    preds = K.predictions(KP, "s0")
    cases, rd = K.rows(d, "cases.tsv"), K.readings(d)
    out, lines = {}, []
    for r in K.table(KP, "s0"):
        n = r["name"]
        want = {q: mv["H-REF"] for q, mv in preds.get(n, {}).items()}
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            lines.append(f"CONTROL {n}: did not complete ({c['class'] if c else 'not run'}): cannot tell")
            continue
        got = dict(rd.get(n, {}))
        if "image" in want:
            got["image"] = image_sha(K.text(d, n + ".txt"))
        bad = {q: got.get(q) for q, v in want.items() if got.get(q) != v}
        out[n] = not bad
        lines.append(f"CONTROL {n}: " + (f"every frozen key read ({', '.join(sorted(want))})" if not bad else
                                         "differs: " + ", ".join(f"{q} {v} (frozen {want[q]})" for q, v in sorted(bad.items())))
                     + f": {cword(out[n])}")
    return out, lines


def find_stage(roots, st):
    for root in roots:
        d = os.path.join(root, st)
        if os.path.isdir(d) and (os.path.exists(os.path.join(d, "cases.tsv")) or
                                 os.path.exists(os.path.join(d, "cases.tsv.gz"))):
            return d
    return None


def s0_named(roots, names):
    s0 = find_stage(roots, "s0")
    if s0 is None:
        return {n: None for n in names}, [f"CONTROL {n}: s0 not kept: cannot tell" for n in names]
    allc, lines = s0_controls(s0)
    return {n: allc.get(n) for n in names}, [ln for ln in lines if ln.split()[1].rstrip(":") in names]


def h1_controls(roots):
    """h1's own Q010 controls (q010-ld2, q010-pre): their frozen job and hash."""
    d = find_stage(roots, "h1")
    preds = K.predictions(KP, "h1")
    out, lines = {}, []
    cases = K.rows(d, "cases.tsv") if d else {}
    rds = K.readings(d) if d else {}
    for n in Q010_H1:
        want = {q: mv["H-REF"] for q, mv in preds[n].items()}
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
        else:
            got = rds.get(n, {})
            out[n] = all(got.get(q) == v for q, v in want.items())
        lines.append(f"CONTROL {n}: {dict(rds.get(n, {})) or 'no reading'} (frozen {want}): {cword(out[n])}")
    return out, lines


def q010_controls(roots):
    a, la = s0_named(roots, Q010_S0)
    b, lb = h1_controls(roots)
    return {**a, **b}, la + lb


def h2_control(d):
    cases = K.rows(d, "cases.tsv") if d else {}
    rd = reading(cases, d, "h2-c-b") if d else {}
    ok = None if not rd else (rd.get("end") == "ok" and "o0" in rd)
    return {"h2-c-b": ok}, [f"CONTROL h2-c-b: {rd or 'no reading'} (frozen end ok, o0 present): {cword(ok)}"]


def stage_controls(stage, roots, d=None):
    if stage == "h2":
        return h2_control(d)
    return s0_named(roots, GATES[stage])


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


def q010_premise(name, roots):
    """True when the copy follows its recovery in the kept attempt, False when it does not, None
    when the stage it needs is not kept."""
    if name == "q010-af":
        seen = None
        for st in ("f1", "f2"):
            d = find_stage(roots, st)
            if d:
                seen = bool(seen) or any(r["class"] == "fault" for r in K.rows(d, "cases.tsv").values())
        return seen
    d = find_stage(roots, "h1")
    if d is None:
        return None
    r = K.rows(d, "cases.tsv").get(Q010_ROWS[name])
    return None if r is None else r["class"] == "hang"


# ---- the flagged stages -----------------------------------------------------------------------
def score_stage(stage, d, roots):
    roots = roots or [os.path.dirname(d)]
    preds, cases, tab = K.predictions(KP, stage), K.rows(d, "cases.tsv"), K.table(KP, stage)
    ctl, lines = stage_controls(stage, roots, d)
    g = SK.gate(ctl)
    qctl, ql = q010_controls(roots) if any(r["name"] in Q010_ROWS for r in tab) else ({}, [])
    lines += ql
    qg = SK.gate(qctl) if qctl else g
    models = {}
    for n, qs in preds.items():
        for q, mv in qs.items():
            for m, v in mv.items():
                if m != "H-REF":
                    models.setdefault(m, {}).setdefault(n, {})[q] = v
    per = {m: [] for m in models}
    for r in tab:
        n = r["name"]
        if r["set"] in ("control", "prime"):
            continue
        rd = reading(cases, d, n)
        lines.append(f"READING {n}: {rd or 'no reading (did not run, or failed)'}")
        prem = q010_premise(n, roots) if n in Q010_ROWS else True
        if n in Q010_ROWS:
            lines.append(f"PREMISE {n}: " + {True: "after its recovery", False: "no recovery before it",
                                              None: "its recovery's stage not kept"}[prem])
        for m in sorted(models):
            if n not in models[m]:
                continue
            st = model_state(models[m][n], rd)
            if prem is not True:
                st = None
            st = SK.gated(qg if n in Q010_ROWS else g, st)
            per[m].append(st)
            lines.append(f"ROW {n} {m}: (frozen {models[m][n]}): {word(st)}")
    for m in sorted(per):
        c = qctl if m in ("H-KEEP", "H-RECOV-CLR") else ctl
        lines.append(f"SUMMARY: {stage}: {m}: " + SK.headline(CLAIMS[m], c, per[m]))
    if stage == "h2":
        lines += q010_rule([os.path.dirname(d)] + list(roots))
    return lines


def q010_rule(roots):
    """R29-3 a: retire when every Q010 control passed and the three held-out copies (after the
    faults and after both hangs) read one hypothesis."""
    ctl, _ = q010_controls(roots)
    got = {}
    for n in Q010_ROWS:
        st = "h2" if n == "q010-p2" else "h1"
        d = find_stage(roots, st)
        preds = K.predictions(KP, st)[n]
        rd = reading(K.rows(d, "cases.tsv"), d, n) if d else {}
        prem = q010_premise(n, roots)
        verdicts = {m: model_state({q: mv[m] for q, mv in preds.items()}, rd) for m in ("H-KEEP", "H-RECOV-CLR")}
        got[n] = [m for m, v in verdicts.items() if v is True and prem is True]
    one = {tuple(v) for v in got.values()}
    ok = all(v is True for v in ctl.values()) and len(one) == 1 and len(next(iter(one))) == 1
    return [f"Q010 RULE: controls {sum(1 for v in ctl.values() if v)} of {len(ctl)} passed; copies "
            + ", ".join(f"{n} {'/'.join(v) or 'none'}" for n, v in got.items()) + ": "
            + (f"one hypothesis, {next(iter(one))[0]}: RETIRE (R29-3 a)" if ok else "not one hypothesis: narrow only")]


def score_s0(d, roots):
    ctl, lines = s0_controls(d)
    for st, names in GATES.items():
        if names:
            g = SK.gate({n: ctl.get(n) for n in names})
            lines.append(f"GATE {st}: {'open' if g.ok else 'closed: ' + '; '.join(g.problems)}")
    lines.append("SUMMARY: s0: " + (f"{sum(1 for v in ctl.values() if v)} of {len(ctl)} references passed"
                                    if ctl else "no reference read"))
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
        if GATES[st]:
            ctl, _ = s0_named(roots, GATES[st])
            g = SK.gate(ctl)
            if not g.ok:
                problems += g.problems
        print(f"gate {st}: " + ("open" if not problems else "closed: " + "; ".join(problems)))
        return 1 if problems else 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q010":
        print("\n".join(q010_rule([argv[2]])))
        return 0
    if len(argv) >= 3 and argv[1] in ORDER:
        st, d, roots = argv[1], argv[2], argv[3:]
        print("\n".join(score_s0(d, roots) if st == "s0" else score_stage(st, d, roots)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
