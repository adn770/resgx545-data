#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r18-flag's scorer, frozen before the run. Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
2c0fe18e46d0, pinned in FROZEN.commits). Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py dumps f2 KEPT_DIR           f2's load rows that completed: their store against E1046's
  score.py gate STAGE ROOTS...         exit 0 when the stage's gate is open (below)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Readings of a row (every stage): end (the runner's class: ok, fault or hang; a failure reads
nothing), fstat and fpage (the row's FIRST kernel `BIF fault S at A` line: S, and A & ~0xfff),
image (an ok probe's 2048 `row Y:` tokens, "%08x", raster order, one space, sha256), o0 (an ok
probe --tri's `o0 ...` line after "o0 "). A model's row is held when every quantity it predicts
equals the reading, FAILED when one differs, cannot tell when one is missing; a row whose stage's
controls did not all pass is cannot tell (scorekit.gated).

s0 (the references): a control passes iff every key of its frozen H-REF row equals its reading
(readings.tsv, the runner's hook_reading; f1-ref-a's image from its text). GATES names the s0
controls of each flagged stage; h2's control is its own h2-c-b (o0 present, end ok).

gate STAGE: open iff every s0 control GATES[STAGE] names passed (the newest attempt that kept s0)
and no kept file of an earlier stage of the newest attempt (ROOTS[0]) holds `SGX recovery failed`
(a failed recovery anywhere closes every later stage; hook_fault also ends the session on it).

f4's H-FAULT-ANY also needs both rows' fstat equal (one requestor). f1's fault page and f3's page
are scored with the models that predict them; README.md says which clause each decides."""
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

ORDER = ("s0", "f1", "f2", "f3", "f4", "h1", "h2")
FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {st: (".txt", ".dmesg") + FIXED for st in ORDER}
GATES = {"f1": ("zv-c-g3", "zv-g5-24"), "f2": ("rf-c-depth", "f1-ref-a"), "f3": ("f2-ctl-256",),
         "f4": ("x-ctl",), "h1": ("ix32-n",), "h2": ()}
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
CLAIMS = {
    "H-PAST-FAULT": "a ZLS store faults at its first unmapped page and lands on a mapped one (G 3 ok, G 5 at +0x15000)",
    "H-PAST-ANY": "any ZLS store past its buffer faults (G 3 at +0x10000, G 5 at +0x12000)",
    "H-DROP": "ZLS stores past the mapping are dropped (both complete)",
    "H-PAST-FAULT-PAGE": "G 5 faults 0x90200 at depth + 0x15000, its first unmapped page",
    "H-PAST-ANY-PAGE": "the stores fault 0x90200 at their first page past the buffer",
    "H-PAGE-END": "f3's faults at the TA data's first unmapped page (0x20006) and the parameter heap's (0x10000)",
    "H-WO-ALL": "WRITEONLY faults a read: the ZLS load (0x80200) and the texture read (0x80002)",
    "H-WO-LOAD-OK": "WRITEONLY does not stop the ZLS load",
    "H-EDM-READ": "EDMPROTECT lets the ZLS load and the texture read through",
    "H-EDM-ZLS": "EDMPROTECT stops the ZLS load (0xa0200)",
    "H-EDM-TEX": "EDMPROTECT stops the texture read (0xa0002)",
    "H-KIND": "O18-1's kind: an empty axis faults 0x90004 (the TA), other words 0x90100 (the 3D)",
    "H-ONE-KIND": "every faulting word faults 0x90100",
    "H-FAULT-ANY": "ISP word 0 bit 18 faults both jobs, through one requestor",
    "H-NEEDS-BUF": "bit 18 needs a buffer E065's job lacked: the ramp draws, the library row faults",
    "H-B24-HANG": "bit 24 alone hangs the job over a 32-bit list",
    "H-B24-W32": "bit 24 selects 32-bit indices (E414's object)",
    "M1-SHAPE": "E700's counter M1 on two new shapes (each third row at c = 8 + 4 hangs)",
    "H-ALT": "E413's alternation (each second row hangs)",
    "H-SCALE": "the threshold scales with the stream (no row hangs)",
}


def producible(row):
    a = row["args"].split()
    if a[:1] == ["tri"]:
        keys = {"job", "hash", "fb"}
        if "--depth" in a:
            keys.add("depthat")
        if "--depth-dump" in a:
            keys.add("zdump")
            if "--depth-store" in a:
                keys.add("zstore")
        if "--dump-render" in a:
            keys.add("tadata")
        return keys
    if a[:1] == ["probe"]:
        keys = {"pixels", "scratchat"}
        if "--tri" in a:
            keys |= {"bg", "o0"}
            if "--dump-render" in a:
                keys.add("tadata")
            if "--index-width" in a:
                keys.add("w32")
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
        o0 = [ln.split(": o0 ", 1)[1].strip() for ln in text.splitlines() if ": o0 " in ln]
        if o0:
            out["o0"] = o0[0]
        fb = re.search(r"^layout: fb (0x[0-9a-f]+)", text, re.M)
        if fb:
            out["fb"] = fb.group(1)
        dl = re.search(r"^diff: (\d+) of", text, re.M)
        if dl:
            out["diff"] = dl.group(1)
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


def stage_controls(stage, roots, d=None):
    """The controls that gate STAGE's rows: s0's GATES[STAGE] (found among ROOTS), or h2's own."""
    if stage == "h2":
        cases = K.rows(d, "cases.tsv") if d else {}
        rd = reading(cases, d, "h2-c-b") if d else {}
        ok = None if not rd else (rd.get("end") == "ok" and "o0" in rd)
        return {"h2-c-b": ok}, [f"CONTROL h2-c-b: {rd or 'no reading'} (frozen end ok, o0 present): {cword(ok)}"]
    s0 = find_stage(roots, "s0")
    if s0 is None:
        return {n: None for n in GATES[stage]}, [f"CONTROL {n}: s0 not kept: cannot tell" for n in GATES[stage]]
    allc, lines = s0_controls(s0)
    return {n: allc.get(n) for n in GATES[stage]}, [ln for ln in lines if ln.split()[1].rstrip(":") in GATES[stage]]


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


# ---- the flagged stages -----------------------------------------------------------------------
def score_stage(stage, d, roots):
    preds, cases, tab = K.predictions(KP, stage), K.rows(d, "cases.tsv"), K.table(KP, stage)
    ctl, lines = stage_controls(stage, roots or [os.path.dirname(d)], d)
    g = SK.gate(ctl)
    models = {}
    for n, qs in preds.items():
        for q, mv in qs.items():
            for m, v in mv.items():
                if m != "H-REF":
                    models.setdefault(m, {}).setdefault(n, {})[q] = v
    per = {m: [] for m in models}
    reads = {r["name"]: reading(cases, d, r["name"]) for r in tab}
    for r in tab:
        n = r["name"]
        if r["set"] in ("control", "prime") and stage != "h2":
            continue
        rd = reads[n]
        lines.append(f"READING {n}: {rd or 'no reading (did not run, or failed)'}")
        for m in sorted(models):
            if n not in models[m] or (stage == "h2" and r["set"] != "heldout"):
                continue
            st = model_state(models[m][n], rd)
            if stage == "f4" and m == "H-FAULT-ANY" and st is True:
                stats = {reads[x].get("fstat") for x in ("b18-lib", "b18-ramp")}
                st = len(stats) == 1 and None not in stats
            st = SK.gated(g, st)
            per[m].append(st)
            lines.append(f"ROW {n} {m}: (frozen {models[m][n]}): {word(st)}")
    for m in sorted(per):
        lines.append(f"SUMMARY: {stage}: {m}: " + SK.headline(CLAIMS[m], ctl, per[m]))
    return lines


def score_s0(d, roots):
    ctl, lines = s0_controls(d)
    for st, names in GATES.items():
        if names:
            g = SK.gate({n: ctl.get(n) for n in names})
            lines.append(f"GATE {st}: {'open' if g.ok else 'closed: ' + '; '.join(g.problems)}")
    lines.append("SUMMARY: s0: " + (f"{sum(1 for v in ctl.values() if v)} of {len(ctl)} references passed"
                                    if ctl else "no reference read"))
    return lines


def dumps_f2(d):
    preds = K.predictions(KP, "s0")
    want = preds["rf-c-depth"]["zstore"]["H-REF"]
    cases, lines = K.rows(d, "cases.tsv"), []
    for n in ("q108-edm-load", "q108-wo-load"):
        r = cases.get(n)
        if r is None or r["class"] != "ok":
            lines.append(f"DUMP {n}: ended {r['class'] if r else 'not run'}: no store to read")
            continue
        p = os.path.join(d, n + ".depth-store.1.bin")
        b = gzip.open(p + ".gz").read() if os.path.exists(p + ".gz") else open(p, "rb").read() if os.path.exists(p) else None
        got = hashlib.sha256(b).hexdigest() if b is not None else None
        lines.append(f"DUMP {n}: store {got or 'not kept'}: "
                     + ("E1046's store byte for byte (the load read the buffer)" if got == want else
                        "not E1046's store" if got else "cannot tell"))
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
            ctl, _ = stage_controls(st, roots)
            g = SK.gate(ctl)
            if not g.ok:
                problems += g.problems
        print(f"gate {st}: " + ("open" if not problems else "closed: " + "; ".join(problems)))
        return 1 if problems else 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 4 and argv[1:3] == ["dumps", "f2"]:
        print("\n".join(dumps_f2(argv[3])))
        return 0
    if len(argv) >= 3 and argv[1] in ORDER:
        st, d, roots = argv[1], argv[2], argv[3:]
        print("\n".join(score_s0(d, roots) if st == "s0" else score_stage(st, d, roots)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
