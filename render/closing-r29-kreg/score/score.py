#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r29-kreg's scorer (Q024, CR_PDS_REG_0A78 timing). Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
adca9929556b, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row's reading (the hooks' twin): diff, the wrong pixels of its renders summed; us, the mean of
renders 2 to N (E141, E396). s0: c0-tri and r1-r8 draw exactly; their median is REF. k1: a 0x2c
control passes when it draws exactly and its us lies within REF_PCT of REF (the write path does
not move the time); the controls' median is MED, and their interquartile range at most
SPREAD_PCT of MED is the premise (else every value is "cannot tell"). A value (rows aV, fit, and
bV, held out) is FAILED (a dependence) when both its readings lie more than BOUND_PCT from MED on
the same side, held otherwise; a value outside on its fit pass only is noise by the frozen rule.
BOUND_PCT and REF_PCT are the predictions' (dev_pct_le, ref_pct_le); SPREAD_PCT is gen.py's."""
import os
import re
import statistics
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FILES = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"s0": FILES, "k1": FILES}
GATES = {"k1": "s0"}            # k1 runs only when s0's controls passed
SPREAD_PCT = 0.5
CLAIM = ("CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the 256x256 triangle's render time "
         "within 1 percent of 0x2c's on two shuffled passes")
TIME = re.compile(r"^tri \d+x\d+ #\d+: (\d+) us$")


def producible(row):
    a = row["args"].split()
    if a[:1] != ["tri"]:
        return set()
    n = int(a[a.index("-n") + 1]) if "-n" in a else 1
    return {"diff", "us"} if n >= 2 else {"diff"}


def reading(text):
    diffs = [int(ln.split()[1]) for ln in text.splitlines() if re.match(r"^diff: \d+ of ", ln)]
    times = [int(m[1]) for m in map(TIME.match, text.splitlines()) if m]
    out = {}
    if diffs:
        out["diff"] = sum(diffs)
    if len(times) >= 2:
        out["us"] = sum(times[1:]) // len(times[1:])
    if any(ln.startswith("tri: ") and ln.endswith(" renders ok") for ln in text.splitlines()):
        out["ok"] = True
    return out


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    for n in cases:
        K.text(d, n + ".txt")


def readings_of(stage, d):
    """{row name: reading} of the rows that ended ok."""
    cases = K.rows(d, "cases.tsv")
    return {n: reading(K.text(d, n + ".txt")) for n, c in cases.items() if c["class"] == "ok"}


def _value(row):
    """The value a row's kreg word writes to 0x0a78, or None."""
    return next((w.split("=", 1)[1] for w in row["knobs"] if w.startswith("kreg:")), None)


def _pct(x, ref):
    return (x / ref - 1.0) * 100.0


def _iqr_pct(xs):
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return (q[2] - q[0]) / statistics.median(xs) * 100.0


def _exact(r):
    return None if r is None or "diff" not in r else r["diff"] == 0 and r.get("ok", False)


def s0_verdicts(d):
    got = readings_of("s0", d)
    controls, lines = {}, []
    for r in K.table(KP, "s0"):
        n = r["name"]
        controls[n] = _exact(got.get(n))
        lines.append(f"CONTROL {n}: {got.get(n, 'no reading')}: "
                     f"{ {True: 'PASS', False: 'FAILED', None: 'cannot tell'}[controls[n]] }")
    refs = [got[n]["us"] for n in got if n.startswith("r") and "us" in got[n]]
    return controls, [], lines, (statistics.median(refs) if refs else None)


def ref_of(roots):
    for root in roots:
        d = os.path.join(root, "s0")
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "cases.tsv")):
            return s0_verdicts(d)[3]
    return None


def k1_verdicts(d, ref):
    preds = K.predictions(KP, "k1")
    bound = float(next(v["H0"] for p in preds.values() for q, v in p.items()
                       if q == "dev_pct_le"))
    ref_pct = float(next(v["H-CTL"] for p in preds.values() for q, v in p.items()
                         if q == "ref_pct_le"))
    got = readings_of("k1", d)
    table = K.table(KP, "k1")
    ctl = [r["name"] for r in table if r["set"] == "control" and _value(r)]
    times = [got[n]["us"] for n in ctl if n in got and "us" in got[n] and _exact(got[n])]
    med = statistics.median(times) if times else None
    controls, lines = {}, []
    for r in table:
        if r["set"] != "control":
            continue
        n = r["name"]
        s = _exact(got.get(n))
        if s and n in ctl:
            s = None if ref is None else abs(_pct(got[n]["us"], ref)) <= ref_pct
        controls[n] = s
        dev = f", {_pct(got[n]['us'], ref):+.2f} % of s0's {ref:.0f} us" \
            if s is not None and n in ctl and ref else ""
        lines.append(f"CONTROL {n}: {got.get(n, 'no reading')}{dev}: "
                     f"{ {True: 'PASS', False: 'FAILED', None: 'cannot tell'}[s] }")
    spread = _iqr_pct(times) if len(times) >= 4 else None
    controls["spread"] = None if spread is None or spread > SPREAD_PCT else True
    lines.append(f"CONTROL spread: the 0x2c controls' interquartile range "
                 f"{'unread' if spread is None else f'{spread:.2f} %'} of their median "
                 f"{med} us (at most {SPREAD_PCT} %): "
                 f"{'PASS' if controls['spread'] else 'cannot tell'}")
    vals = {}
    for r in table:
        if r["set"] in ("fit", "held"):
            vals.setdefault(_value(r), {})[r["set"]] = r["name"]
    rows, far = [], []
    for v in sorted(vals):
        devs = {}
        for sset, n in vals[v].items():
            g = got.get(n)
            if g and _exact(g) and "us" in g and med:
                devs[sset] = _pct(g["us"], med)
        if len(devs) < 2 or not controls["spread"]:
            state = None
        else:
            a, b = devs["fit"], devs["held"]
            state = not (abs(a) > bound and abs(b) > bound and (a > 0) == (b > 0))
            far.append((max(abs(a), abs(b)), v))
        rows.append(state)
        txt = ", ".join(f"{k} {x:+.2f} %" for k, x in sorted(devs.items())) or "no reading"
        note = " (fit pass outside, held-out inside: noise by the frozen rule)" if state and \
            abs(devs["fit"]) > bound else ""
        lines.append(f"ROW {v}: {txt} of {med} us: "
                     f"{ {True: 'held', False: 'FAILED', None: 'cannot tell'}[state] }{note}")
    far.sort(reverse=True)
    lines.append("FARTHEST: " + ", ".join(f"{v} {x:.2f} %" for x, v in far[:4]))
    return controls, rows, lines


def verdicts(stage, d, roots=()):
    if stage == "s0":
        return s0_verdicts(d)[:3]
    return k1_verdicts(d, ref_of(roots))


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                g = SK.gate(verdicts(dep, d)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, rows, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        claim = CLAIM if argv[1] == "k1" else "s0's references draw exactly"
        print("SUMMARY: " + argv[1] + ": " + SK.headline(claim, controls, rows if rows else
                                                          [c for c in controls.values()]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
