#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r34-sa0b's scorer (the corrected rerun of r34-sa0, E1139), frozen before the run. Every verdict rule comes from kit/scorekit.py,
the kept files are read through kit/kitscore.py (byte copies of resgx545 914dd2323f79, pinned in
FROZEN.commits). Standard library only.

  score.py s KEPT_DIR [ROOTS...]   CONTROL, READING, ROW, SUMMARY lines and the Q136 RULE (exit 0)
  score.py q136 ROOT               Q136's retire rule alone over the attempt ROOT (ROOT/s)
  score.py gate STAGE ROOTS...     exit 0 (one stage, not gated)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Readings, from the kept texts only (every expected value is this session's own: a program's
constants, or the output of the job right before the reader in this attempt):
  - a probe row's o0 line, `o0 0xV (2048 of 2048)` or `o0 mixed 0xA xN ... [other xK]`, as a
    multiset; a reader outputs the value it read (E496's form; the keys K2 and K4 are 0, so the
    xor below is the identity), and its dword 0 must be one of its o0 values (the form's premise:
    else cannot tell);
  - the job before a reader (the row before it in the table; a reset or idle is not a job): a
    probe's own o0 multiset, a t10 fill's `fill: ok ... colour 0xV` (2048 pixels, with `diff: 0
    of 2048`), a t10 tri: its two colours (t10's source, gen/constants.txt TRI);
  - controls (W, K): readings.tsv `sa` (scratch dword 0) and `top` (the most frequent o0 value).

Categories of a reader (decoded D, the job before's output Q): M when D's most frequent value is
the group's marker; PREV when every value of D is a value of Q and D's most frequent value is Q's
(after a tri: every value one of its two colours); TRI when every value of D is one of the tri's
colours. A frozen M, PREV or TRI is held when D is in it, FAILED when D is in another of the three
and not in it, cannot tell otherwise (no reading, an `other` count, a marker of another row, any
other value); `!M` and `!PREV` are held when D is read and not M (not PREV), FAILED when it is.
Every reader is gated by the controls of its group (its W and K rows).

Q136 RULE, against the question line's two clauses:
  (a) "how long does a value written to sa0 last across jobs": DECIDED iff every W and K control
      of the R groups passed, all 16 held-out R rows are decided under H-PERSIST, H-ONEJOB and
      H-COLOUR (M or PREV, both replicates) and exactly one of them holds on all 16; the answer
      is that one (with H-RESET and H-IDLE then failed on their rows).
  (b) "is pa0's 0xff00ff00/0xff203040 mixture in the first jobs of a table the colour left by the
      job before it": DECIDED iff the K controls of the P groups passed, both ptr fit rows read
      TRI (E496's mixture re-read after a t10 tri), and H-PREV holds and H-FIXED fails on all
      four held-out rows pk3 and pfl (a colour job and the t10 fill before pa0); pk3r (a debugfs
      reset between) is printed with the answer, whichever way it reads.
RETIRE-CAPABLE iff (a) and (b) are both DECIDED; else NARROW, naming the clause(s) decided."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGE = "s"
REQUIRED = {STAGE: (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}
NPIX = 2048


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
K2, K4 = int(C["K2"], 16), int(C["K4"], 16)
TRI = frozenset(int(v, 16) for v in C["TRI"].split(","))
FULL_A = ("H-PERSIST", "H-ONEJOB", "H-COLOUR")
SIDE_A = ("H-RESET", "H-IDLE")
B_CORE = ("pk3", "pfl")
CLAIMS = {
    "H-PERSIST": "an sa0 write lasts across every job, reset and idle of the stage",
    "H-ONEJOB": "an sa0 write is read by the next job only, across a reset and idle; a job between "
                "replaces it with that job's colour",
    "H-COLOUR": "an sa0 write does not last into the next job: the next job reads the colour the job "
                "before it output",
    "H-RESET": "a debugfs reset replaces sa0",
    "H-IDLE": "sa0 is lost over 10 to 120 s of idle",
    "H-PREV": "pa0 reads the colour the job before it output",
    "H-FIXED": "pa0 reads the 0xff00ff00/0xff203040 mixture whatever ran before it",
    "H-RESETP": "a debugfs reset replaces what pa0 reads",
}
ANSWER_A = {
    "H-PERSIST": "an sa0 value written by iaddu32 in a fill's pixel task lasts across every job of "
                 "the stage that does not write sa0 (a colour fill, the t10 fill and triangle), a debugfs reset and 120 s idle",
    "H-ONEJOB": "an sa0 value written by iaddu32 in a fill's pixel task lasts one job: the next job "
                "reads it, also across a debugfs reset or up to 120 s idle with no job between, "
                "and any job between (a colour fill, the t10 fill or triangle) "
                "replaces it with that job's colour",
    "H-COLOUR": "an sa0 value written by iaddu32 in a fill's pixel task does not reach the next "
                "job: the next job reads the colour the writer output, after a reset and idle "
                "too (E496's job 8 was the colour rule)",
}


def producible(row):
    return {"sa", "top"} if row["args"].split()[:1] == ["probe"] else set()


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


O0 = re.compile(r"^probe \S+: o0 (.*)$", re.M)


def o0_multiset(text):
    """{value: count} of a probe's o0 line and the `other` count, or (None, None)."""
    m = O0.search(text)
    if not m:
        return None, None
    s = m.group(1)
    one = re.fullmatch(r"0x([0-9a-f]{8}) \((\d+) of (\d+)\)", s)
    if one:
        return {int(one.group(1), 16): int(one.group(2))}, 0
    if not s.startswith("mixed "):
        return None, None
    vals = {int(v, 16): int(c) for v, c in re.findall(r"0x([0-9a-f]{8}) x(\d+)", s)}
    oth = re.search(r"other x(\d+)", s)
    return vals, int(oth.group(1)) if oth else 0


def top(ms):
    return max(ms.items(), key=lambda kv: kv[1])[0] if ms else None


def job_output(row, cases, d):
    """The output of an ok row as ('ms', {value: count}) or ('tri', None), or None."""
    c = cases.get(row["name"])
    if c is None or not K.completed(c):
        return None
    t = K.text(d, row["name"] + ".txt")
    a = row["args"].split()
    if a[:1] == ["probe"]:
        ms, oth = o0_multiset(t)
        return ("ms", ms) if ms and not oth and sum(ms.values()) == NPIX else None
    if a == ["fill"]:
        m = re.search(r"^fill: ok, 64x32 .* colour (0x[0-9a-f]{8})$", t, re.M)
        ok = re.search(r"^diff: 0 of 2048 pixels", t, re.M)
        return ("ms", {int(m.group(1), 16): NPIX}) if m and ok else None
    if a == ["tri"]:
        return ("tri", None) if re.search(r"^diff: 0 of 4096 pixels", t, re.M) else None
    return None


def group_of(name):
    return name.split("-")[0][:-1]


def decode(row, cases, d):
    """A reader's decoded multiset (2048 pixels, no `other`), or None."""
    c = cases.get(row["name"])
    if c is None or not K.completed(c):
        return None
    ms, oth = o0_multiset(K.text(d, row["name"] + ".txt"))
    if not ms or oth or sum(ms.values()) != NPIX:
        return None
    key = K2 if "/bins/r.bin" in row["args"] else K4
    dw = re.search(r"^probe \S+: scratch \+0x000 0x([0-9a-f]{8})$", K.text(d, row["name"] + ".txt"),
                   re.M)
    if not dw or int(dw.group(1), 16) ^ key not in {v ^ key for v in ms}:
        return None
    return {v ^ key: n for v, n in ms.items()}


def classify(dm, prev, marker):
    """{'M', 'PREV', 'TRI'} that the decoded multiset is in (an empty set: none of them)."""
    out = set()
    if dm is None:
        return None
    vals = set(dm)
    if marker is not None and top(dm) == marker:
        out.add("M")
    if prev is not None:
        kind, q = prev
        if kind == "tri":
            if vals <= TRI:
                out.add("PREV")
        elif vals <= set(q) and top(dm) == top(q):
            out.add("PREV")
    if vals <= TRI:
        out.add("TRI")
    return out


def state(token, cats):
    if cats is None:
        return None
    if token.startswith("!"):
        base = token[1:]
        return base not in cats
    if token in cats:
        return True if len(cats & {"M", "PREV"}) <= 1 else None
    return False if cats & {"M", "PREV", "TRI"} else None


def controls(d):
    preds = K.predictions(KP, STAGE)
    cases, rds = K.rows(d, "cases.tsv"), K.readings(d)
    out, lines = {}, []
    for r in K.table(KP, STAGE):
        n = r["name"]
        if r["set"] != "control":
            continue
        want = {q: mv["H-REF"] for q, mv in preds[n].items()}
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            lines.append(f"CONTROL {n}: did not complete ({c['class'] if c else 'not run'}): "
                         "cannot tell")
            continue
        got = rds.get(n, {})
        bad = {q: got.get(q) for q, v in want.items() if got.get(q) != v}
        out[n] = not bad
        lines.append(f"CONTROL {n}: " + (", ".join(f"{q} {got.get(q)}" for q in sorted(want))
                                         if not bad else "differs: " + ", ".join(
                                             f"{q} {v} (frozen {want[q]})"
                                             for q, v in sorted(bad.items())))
                     + f": {cword(out[n])}")
    return out, lines


def fmt(dm):
    if dm is None:
        return "no reading"
    return " ".join("0x%08x x%d" % (v, n) for v, n in sorted(dm.items(), key=lambda kv: -kv[1]))


def score(d):
    """(lines, per-model row states {model: {row: state}}, controls, readings {row: cats})."""
    ctl, lines = controls(d)
    cases = K.rows(d, "cases.tsv")
    preds = K.predictions(KP, STAGE)
    tab = K.table(KP, STAGE)
    marker = {}
    for r in tab:
        if r["name"].endswith("-w"):
            marker[r["name"].split("-")[0]] = int(preds[r["name"]]["sa"]["H-REF"], 16)
    per, cats_of = {}, {}
    for i, r in enumerate(tab):
        n = r["name"]
        if r["set"] not in ("heldout", "fit"):
            continue
        t = n.split("-")[0]
        dm = decode(r, cases, d)
        prev = job_output(tab[i - 1], cases, d) if i else None
        cats = classify(dm, prev, marker.get(t))
        cats_of[n] = cats
        lines.append(f"READING {n}: {fmt(dm)}; the job before ({tab[i - 1]['name']}): "
                     + ("its two colours" if prev and prev[0] == "tri" else
                        fmt(prev[1]) if prev else "no output")
                     + f": {'/'.join(sorted(cats)) if cats else 'none of M, PREV, TRI'}")
        grp = {k: v for k, v in ctl.items() if k.split("-")[0] == t}
        g = SK.gate(grp) if grp else SK.Gate(ok=True)
        for m, tok in sorted(preds[n]["cat"].items()):
            st = SK.gated(g, state(tok, cats))
            per.setdefault(m, {})[n] = st
            lines.append(f"ROW {n} ({r['set']}) {m}: frozen {tok}: {word(st)}")
    for m in sorted(per):
        held = {n: v for n, v in per[m].items() if not n.startswith("ptr")}
        if held:
            lines.append(f"SUMMARY: {STAGE}: {m}: " + SK.headline(CLAIMS[m], ctl,
                                                                  list(held.values())))
    return lines, per, ctl, cats_of


def rule(per, ctl, cats_of):
    """Q136 RULE (the docstring)."""
    ra = sorted(n for n in per["H-ONEJOB"])
    ctl_a = {k: v for k, v in ctl.items() if not group_of(k).startswith("p")}
    ctl_b = {k: v for k, v in ctl.items() if group_of(k).startswith("p")}
    decided_a = [n for n in ra if all(per[m][n] is not None for m in FULL_A)]
    holds_a = [m for m in FULL_A if all(per[m][n] is True for n in ra)]
    out = []
    head = (f"Q136 RULE (a): controls {sum(v is True for v in ctl_a.values())} of {len(ctl_a)} "
            f"passed; R rows decided {len(decided_a)} of {len(ra)}; holding on every row: "
            f"{', '.join(holds_a) or 'none'}; "
            + "; ".join(f"{m} {SK.tally(per[m].values())}" for m in FULL_A + SIDE_A))
    a_ok = (all(v is True for v in ctl_a.values()) and len(decided_a) == len(ra) == 16
            and len(holds_a) == 1)
    if a_ok:
        out.append(head + f": DECIDED, {holds_a[0]}")
    else:
        why = ("a control did not pass" if not all(v is True for v in ctl_a.values()) else
               "a held-out R row is not decided" if len(decided_a) != len(ra) else
               "no single pattern holds on every R row")
        out.append(head + f": not decided ({why})")
    core = sorted(n for n in per["H-PREV"] if group_of(n) in B_CORE)
    fits = sorted(n for n in cats_of if group_of(n) == "ptr")
    fit_tri = all(cats_of[n] is not None and "TRI" in cats_of[n] for n in fits) and len(fits) == 2
    b_ok = (all(v is True for v in ctl_b.values()) and fit_tri and len(core) == 4
            and all(per["H-PREV"][n] is True for n in core)
            and all(per["H-FIXED"][n] is False for n in core))
    rs = sorted(n for n in per.get("H-RESETP", {}))
    rsw = ", ".join(f"{n} {'PREV' if per['H-PREV'][n] else 'not PREV' if per['H-PREV'][n] is False else 'cannot tell'}"
                    for n in rs)
    head_b = (f"Q136 RULE (b): controls {sum(v is True for v in ctl_b.values())} of {len(ctl_b)} "
              f"passed; ptr fits read TRI: {'yes' if fit_tri else 'no'}; H-PREV "
              f"{SK.tally(per['H-PREV'][n] for n in core)}, H-FIXED "
              f"{SK.tally(per['H-FIXED'][n] for n in core)} on pk3, pfl; pk3r: {rsw}")
    out.append(head_b + (": DECIDED, H-PREV" if b_ok else ": not decided"))
    if a_ok and b_ok:
        out.append("Q136 RULE: RETIRE-CAPABLE (both clauses decided)")
    elif a_ok or b_ok:
        out.append(f"Q136 RULE: NARROW: clause ({'a' if a_ok else 'b'}) decided, clause "
                   f"({'b' if a_ok else 'a'}) open")
    else:
        out.append("Q136 RULE: NARROW: neither clause decided")
    if a_ok:
        out.append(f"Q136 ANSWER (a) [HW]: {ANSWER_A[holds_a[0]]} (16 of 16 held-out rows, both "
                   "replicates, every control)")
    if b_ok:
        rest = ("; a debugfs reset between keeps it (pk3r)" if all(per["H-PREV"][n] for n in rs)
                else "; pk3r (a debugfs reset between): " + rsw)
        out.append("Q136 ANSWER (b) [HW]: pa0 in a fill's pixel task reads the colour the job "
                   "before it output (a colour fill, the t10 fill), and after the t10 triangle "
                   "its two colours 0xff00ff00 and 0xff203040, the mixture of E496's first jobs, "
                   "whose table ran after a triangle (env.toml `before`) [infer]" + rest)
    out.append("Q136 NOT THE LINE: an o destination, other operands and one job per register of "
               "the banks (body extras), the instance slots (Q129, Q193), the kernel's own jobs "
               "beyond a debugfs reset; the lead confirms")
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (not gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q136":
        _, per, ctl, cats = score(os.path.join(argv[2], STAGE))
        print("\n".join(rule(per, ctl, cats)))
        return 0
    if len(argv) >= 3 and argv[1] == STAGE:
        lines, per, ctl, cats = score(argv[2])
        print("\n".join(lines + rule(per, ctl, cats)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
