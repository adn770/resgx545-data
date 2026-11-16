#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r31-kreg2's scorer (Q024, CR_PDS_REG_0A78 timing, two loads). Every verdict rule
comes from kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of
resgx545 2ffa9a93727d, pinned in FROZEN.commits); the frozen numbers are gen/gen.py's.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when the s0 controls STAGE needs passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py q024 ROOT                   the frozen retire rule on ROOT's k1 and k2 (exit 0)

A row's reading (run/hooks.sh's twin): diff, the wrong pixels of its renders summed (t10 tri);
us, the MEDIAN of renders 2 to N (every `tri WxH #i: T us` line in output order); img, how many
renders' `probe NAME: o0 ...` lines differ from the first's (t30 probe), and the first's line.

s0: c0-tri and r1-r8 draw exactly (REF1 = r1-r8's median); v1-v8 draw one image, each job's six
renders and every job alike (REF2 = their median); BOUND2 = max(FLOOR2, K2 x v1-v8's
interquartile range in percent of REF2), and k2 cannot tell when BOUND2 > CAP2.

k1 (L1) and k2 (L2): the 0x2c controls c01-c16 must draw (k1 exactly, k2 v1's image); their
timing band is REF1_PCT around REF1 (k1) or BOUND2 around REF2 (k2). The single-control outlier
rule (frozen before the run): at most OUTLIERS control a stage outside its band is allowed,
named, and left out of MED and the spread; two or more outside fail the controls. A control that
does not draw, or has no reading, is never an allowed outlier. MED = the in-band controls'
median; their interquartile range at most SPREAD1_PCT (k1) or BOUND2 / 2 (k2) of MED is the
premise (else every value is cannot tell). A value (aV fit, bV held out) is FAILED when both its
readings lie more than the bound (BOUND1_PCT, or BOUND2) from MED on the same side, held
otherwise; a value outside on its fit pass only is noise by the frozen rule. A k2 value row that
draws another image than v1's is cannot tell (and an IMAGE line names it, a finding of its own).

q024 (the frozen retire rule, against the question "does CR_PDS_REG_0A78 change timing, when two
of its values were slower in one timing run?"): RETIRE when k1 and k2 both print their claim with
64 of 64 values decided and none FAILED (every control premise held, c-end exact on both): the
answer is no, no value changes either load's render time by more than the stage's bound. A value
FAILED on both passes: a FINDING (Q024 stays open, narrowed to it). Anything else: NARROW (the
decided load's clause only) or NOTHING."""
import os
import re
import statistics
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import gen as G  # noqa: E402

FILES = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"s0": FILES, "k1": FILES, "k2": FILES}
GATES = {"k1": "s0", "k2": "s0"}
# the s0 controls each stage's gate needs: the exact triangle and its own load's references
GATE_ROWS = {"k1": re.compile(r"^(c0-tri|r\d)$"), "k2": re.compile(r"^(c0-tri|v\d)$")}
CLAIM = {"k1": "CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the 256x256 triangle's render "
               "time within {b:.2f} percent of 0x2c's on two shuffled passes",
         "k2": "CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the render time of 500 small "
               "triangles within {b:.2f} percent of 0x2c's on two shuffled passes"}
TIME = re.compile(r"^tri \d+x\d+ #\d+: (\d+) us$")
O0 = re.compile(r"^probe \S+: (o0 .*)$")


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"] and "--vertices" in a:
        return {"img", "us"}
    if a[:1] != ["tri"]:
        return set()
    n = int(a[a.index("-n") + 1]) if "-n" in a else 1
    return {"diff", "us"} if n >= 2 else {"diff"}


def median_low(xs):
    """The hooks' median: the middle one, or the mean of the middle two rounded down."""
    s, n = sorted(xs), len(xs)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


def reading(text):
    lines = text.splitlines()
    diffs = [int(ln.split()[1]) for ln in lines if re.match(r"^diff: \d+ of ", ln)]
    times = [int(m[1]) for m in map(TIME.match, lines) if m]
    imgs = [m[1] for m in map(O0.match, lines) if m]
    out = {}
    if diffs:
        out["diff"] = sum(diffs)
    if len(times) >= 2:
        out["us"] = median_low(times[1:])
    out["n"] = len(times)
    if imgs:
        out["img"] = sum(1 for i in imgs[1:] if i != imgs[0])
        out["image"] = imgs[0]
    if any(ln.startswith("tri: ") and ln.endswith(" renders ok") for ln in lines):
        out["ok"] = True
    out["failed"] = any("failed:" in ln for ln in lines)
    return out


def read_files(stage, d):
    """Every file the scorer reads of a kept stage (the kit's kept check)."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.text(d, "readings.tsv")
    for n in cases:
        K.text(d, n + ".txt")


def readings_of(d):
    """{row name: reading} of the rows that ended ok."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    return {n: reading(K.text(d, n + ".txt")) for n, c in cases.items() if c["class"] == "ok"}


def _value(row):
    return next((w.split("=", 1)[1] for w in row["knobs"] if w.startswith("kreg:")), None)


def _pct(x, ref):
    return (x / ref - 1.0) * 100.0


def _iqr_pct(xs):
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return (q[2] - q[0]) / statistics.median(xs) * 100.0


def _exact(r):
    """t10 tri: every render drew exactly and the tool said so."""
    return None if r is None or "diff" not in r else r["diff"] == 0 and r.get("ok", False)


def _same(r, image):
    """t30 probe: six timed renders, no failure, one image within the job and equal to image."""
    if r is None or "img" not in r or "us" not in r:
        return None
    return (not r["failed"] and r["n"] == G.RENDERS and r["img"] == 0
            and (image is None or r["image"] == image))


STATE = {True: "PASS", False: "FAILED", None: "cannot tell"}


def s0_info(d):
    """(controls, lines, info) with info = dict(ref1, ref2, bound2, image)."""
    got = readings_of(d)
    v1 = got.get("v1", {}).get("image")
    controls, lines = {}, []
    for r in K.table(KP, "s0"):
        n = r["name"]
        controls[n] = _same(got.get(n), v1) if n.startswith("v") else _exact(got.get(n))
        g = got.get(n)
        txt = "no reading" if g is None else ", ".join(
            f"{k} {g[k]}" for k in ("diff", "us", "img", "n") if k in g)
        lines.append(f"CONTROL {n}: {txt}: {STATE[controls[n]]}")
    r_us = [got[n]["us"] for n in got if re.fullmatch(r"r\d", n) and "us" in got[n]]
    v_us = [got[n]["us"] for n in got if re.fullmatch(r"v\d", n) and "us" in got[n]]
    ref1 = statistics.median(r_us) if r_us else None
    ref2 = statistics.median(v_us) if v_us else None
    iqr2 = _iqr_pct(v_us) if len(v_us) >= 4 else None
    bound2 = None if iqr2 is None else max(G.FLOOR2_PCT, G.K2 * iqr2)
    lines.append(f"REF1 {ref1} us (r1-r8); REF2 {ref2} us (v1-v8), their IQR "
                 f"{'unread' if iqr2 is None else f'{iqr2:.3f} %'}: BOUND2 "
                 f"{'unread' if bound2 is None else f'{bound2:.3f} %'} (cap {G.CAP2_PCT} %)")
    lines.append(f"IMAGE v1: {v1}")
    return controls, lines, dict(ref1=ref1, ref2=ref2, bound2=bound2, image=v1)


def info_of(roots):
    for root in roots:
        d = os.path.join(root, "s0")
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "cases.tsv")):
            return s0_info(d)[2]
    return dict(ref1=None, ref2=None, bound2=None, image=None)


def k_verdicts(stage, d, info):
    """(controls, rows, lines, bound) of k1 or k2."""
    got = readings_of(d)
    table = K.table(KP, stage)
    if stage == "k1":
        ref, band, bound, spread_max = info["ref1"], G.REF1_PCT, G.BOUND1_PCT, G.SPREAD1_PCT
        draws = _exact
    else:
        ref, b2 = info["ref2"], info["bound2"]
        band = bound = b2
        spread_max = None if b2 is None else b2 / 2
        draws = lambda r: _same(r, info["image"])  # noqa: E731
    controls, lines = {}, []
    if stage == "k2":
        ok2 = b2 is not None and b2 <= G.CAP2_PCT
        controls["bound2"] = True if ok2 else None
        lines.append(f"CONTROL bound2: BOUND2 {'unread' if b2 is None else f'{b2:.3f} %'} "
                     f"(at most {G.CAP2_PCT} %): {'PASS' if ok2 else 'cannot tell'}")
    ctl = [r["name"] for r in table if r["set"] == "control" and _value(r)]
    dev, drawn = {}, {}
    for n in ctl:
        g = got.get(n)
        drawn[n] = draws(g)
        if drawn[n] and ref and band is not None:
            dev[n] = _pct(g["us"], ref)
    out = [n for n in dev if abs(dev[n]) > band]
    allowed = out if len(out) <= G.OUTLIERS else []
    for r in table:
        if r["set"] != "control":
            continue
        n = r["name"]
        g = got.get(n)
        if n not in ctl:            # c-end: an exact triangle, no write
            s = _exact(g)
            note = ""
        elif not drawn[n]:
            s, note = drawn[n], ""
        elif n not in dev:
            s, note = None, " (no s0 reference or band)"
        elif n in allowed:
            s, note = True, (f", {dev[n]:+.2f} % of s0's {ref:.0f} us: outside the band, the one "
                             f"allowed outlier (left out of MED)")
        else:
            s = abs(dev[n]) <= band
            note = f", {dev[n]:+.2f} % of s0's {ref:.0f} us (band {band:.2f} %)"
        controls[n] = s
        txt = "no reading" if g is None else ", ".join(
            f"{k} {g[k]}" for k in ("diff", "us", "img", "n") if k in g)
        lines.append(f"CONTROL {n}: {txt}{note}: {STATE[s]}")
    inband = [got[n]["us"] for n in dev if n not in out]
    med = statistics.median(inband) if inband else None
    spread = _iqr_pct(inband) if len(inband) >= 4 else None
    controls["spread"] = None if spread is None or spread_max is None or spread > spread_max \
        else True
    lines.append(f"CONTROL spread: the in-band 0x2c controls' interquartile range "
                 f"{'unread' if spread is None else f'{spread:.3f} %'} of their median {med} us "
                 f"(at most {'unread' if spread_max is None else f'{spread_max:.3f}'} %): "
                 f"{'PASS' if controls['spread'] else 'cannot tell'}")
    lines.append(f"OUTLIERS: {', '.join(out) or 'none'} ({len(out)} outside the band; at most "
                 f"{G.OUTLIERS} allowed)")
    vals = {}
    for r in table:
        if r["set"] in ("fit", "held"):
            vals.setdefault(_value(r), {})[r["set"]] = r["name"]
    rows, far = [], []
    for v in sorted(vals):
        devs, other = {}, []
        for sset, n in vals[v].items():
            g = got.get(n)
            if stage == "k2" and g and _same(g, None) and g["image"] != info["image"]:
                other.append(n)
            if g and draws(g) and med:
                devs[sset] = _pct(g["us"], med)
        if len(devs) < 2 or not SK.gate(controls).ok:
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
        if other:
            lines.append(f"IMAGE {v}: {', '.join(other)} drew another image than v1's (a finding)")
    far.sort(reverse=True)
    lines.append("FARTHEST: " + ", ".join(f"{v} {x:.2f} %" for x, v in far[:4]))
    return controls, rows, lines, bound


def score_stage(stage, d, roots):
    """(lines, summary)"""
    if stage == "s0":
        controls, lines, _ = s0_info(d)
        return lines, SK.headline("s0's references draw and time", controls,
                                  list(controls.values()))
    controls, rows, lines, bound = k_verdicts(stage, d, info_of(roots))
    claim = CLAIM[stage].format(b=bound if bound is not None else float("nan"))
    return lines, SK.headline(claim, controls, rows)


def q024(root):
    heads = {}
    for st in ("k1", "k2"):
        d = os.path.join(root, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            heads[st] = None
            continue
        heads[st] = score_stage(st, d, [root])[1]
    done = {st: h is not None and h.endswith("(64 of 64 rows decided)") and
            "not supported" not in h and h.startswith("CR_PDS") for st, h in heads.items()}
    found = [st for st, h in heads.items() if h and "is not supported" in h]
    for st, h in heads.items():
        print(f"{st}: {h if h is not None else 'not run'}")
    if found:
        print("Q024: FINDING (a value outside on both passes on " + ", ".join(found) +
              "): stays open, narrowed to those values")
    elif all(done.values()):
        print("Q024: RETIRE (no value of 0x00-0x3f changes either load's render time beyond "
              "its bound, both passes, controls held)")
    elif any(done.values()):
        print("Q024: NARROW (decided on " + ", ".join(st for st in done if done[st]) +
              " only)")
    else:
        print("Q024: NOTHING (no load decided)")
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                controls = {n: s for n, s in s0_info(d)[0].items()
                            if GATE_ROWS[argv[2]].match(n)}
                g = SK.gate(controls)
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q024":
        return q024(argv[2])
    if len(argv) >= 3 and argv[1] in REQUIRED:
        lines, head = score_stage(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        print("SUMMARY: " + argv[1] + ": " + head)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
