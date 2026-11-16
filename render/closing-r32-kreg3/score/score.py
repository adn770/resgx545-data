#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r32-kreg3's scorer (Q024's last clause: CR_PDS_REG_0A78 and the render time of many
small triangles). Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of resgx545 bf0ba5618263, pinned in FROZEN.commits); the frozen
numbers are gen/gen.py's.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when s0 passed c0-tri and picked STAGE's form
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py q024 ROOT                   the frozen retire rule on ROOT's s0 and k stage (exit 0)

A row's reading (run/hooks.sh's twin, E1124's rule): diff, the wrong pixels of its renders
summed (t10 tri); us, the MEDIAN of renders 2 to N (every `tri WxH #i: T us` line in output
order); img, how many renders' `probe NAME: o0 ...` lines differ from the first's (t30 probe),
and the first's line.

s0, the calibration (frozen before the run): a form's reference DRAWS when its job timed as many
renders as the form has, printed no `failed:` line and one image, the image of the form's first
reference. A form QUALIFIES when its eight references all draw and their interquartile range is
at most PICK_PCT percent of their median. PICK: the first qualifying form in FORMS order (the
64x64 forms, then the 1024x768 ones), or none; with none, or c0-tri not exact, every k gate is
shut and no flagged row runs.

k<form>: REF = the form's references' median; BOUND = max(FLOOR, K x their IQR in percent of
REF), cannot tell above CAP. The 0x2c controls c01-c16 must draw (the reference image); their
band is BOUND around REF. The single-control outlier rule (E1124, kept): at most OUTLIERS control
a stage outside its band is allowed, named, and left out of MED and the spread; two or more
outside fail the controls. A control that does not draw, or has no reading, is never an allowed
outlier. MED = the in-band controls' median; their IQR at most BOUND / 2 of MED is the premise
(else every value is cannot tell). A value (aV fit, bV held out) is FAILED when both its
readings lie more than BOUND from MED on the same side, held otherwise; a value outside on its
fit pass only is noise by the frozen rule. A value row that draws another image is cannot tell
(an IMAGE line names it, a finding of its own).

q024 (the frozen retire rule, against the question "does CR_PDS_REG_0A78 change timing, when two
of its values were slower in one timing run?"; E1124 closed the 256x256 clause): RETIRE only when
the k stage of s0's pick prints its claim with 64 of 64 values decided and none FAILED (its
controls, the outlier rule, the spread premise, BOUND at most CAP, c-end exact). A value FAILED
on both passes: FINDING (Q024 stays open, narrowed to it). Otherwise NOTHING: no form qualified
(STOPPED before any flagged row), the k stage did not run, or it did not decide 64 of 64."""
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
KSTAGES = {G.stage_of(f[0]): f[0] for f in G.FORMS}
REQUIRED = {"s0": FILES, **{st: FILES for st in KSTAGES}}
GATES = {st: "s0" for st in KSTAGES}
CLAIM = ("CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the render time of {load} within "
         "{b:.2f} percent of 0x2c's on two shuffled passes")
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


def iqr_pct(xs):
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return (q[2] - q[0]) / statistics.median(xs) * 100.0


def _exact(r):
    """t10 tri: every render drew exactly and the tool said so."""
    return None if r is None or "diff" not in r else r["diff"] == 0 and r.get("ok", False)


def draws(r, form, image):
    """t30 probe: the form's N timed renders, no failure, one image within the job and equal to
    image (when given)."""
    if r is None or "img" not in r or "us" not in r:
        return None
    return (not r["failed"] and r["n"] == G.FORM[form][3] and r["img"] == 0
            and (image is None or r["image"] == image))


STATE = {True: "PASS", False: "FAILED", None: "cannot tell"}


def pick(forms):
    """The frozen pick rule. forms: {form: dict(drawn=[bool or None] * REFS, us=[...])}; the first
    form in FORMS order whose REFS references all drew and spread at most PICK_PCT, or None."""
    for f, *_ in G.FORMS:
        x = forms.get(f)
        if x and len(x["drawn"]) == G.REFS and all(x["drawn"]) and len(x["us"]) == G.REFS \
                and iqr_pct(x["us"]) <= G.PICK_PCT:
            return f
    return None


def s0_info(d):
    """(controls, lines, info): info = dict(c0, pick, forms={form: dict(ref, iqr, bound, image,
    drawn, us)})."""
    got = readings_of(d)
    controls, lines, forms = {}, [], {}
    names = [r["name"] for r in K.table(KP, "s0")]
    for f, *_ in G.FORMS:
        mine = [n for n in names if n.startswith(f"v{f}-")]
        image = got.get(mine[0], {}).get("image")
        drawn = [draws(got.get(n), f, image) for n in mine]
        us = [got[n]["us"] for n, ok in zip(mine, drawn) if ok]
        iqr = iqr_pct(us) if len(us) >= 4 else None
        forms[f] = dict(ref=statistics.median(us) if us else None, iqr=iqr, image=image,
                        bound=None if iqr is None else max(G.FLOOR_PCT, G.K * iqr),
                        drawn=drawn, us=us)
    for n in names:
        g = got.get(n)
        if n == "c0-tri":
            controls[n] = _exact(g)
        else:
            f = n[1:].split("-")[0]
            controls[n] = draws(g, f, forms[f]["image"])
        txt = "no reading" if g is None else ", ".join(
            f"{k} {g[k]}" for k in ("diff", "us", "img", "n") if k in g)
        lines.append(f"CONTROL {n}: {txt}: {STATE[controls[n]]}")
    p = pick(forms)
    for f, *_ in G.FORMS:
        x = forms[f]
        ok = len(x["us"]) == G.REFS and x["iqr"] is not None and x["iqr"] <= G.PICK_PCT
        iqr = "unread" if x["iqr"] is None else f"{x['iqr']:.3f} %"
        lines.append(f"FORM {f} ({G.load(f)}): {len(x['us'])} of {G.REFS} drew; median "
                     f"{x['ref']} us; IQR {iqr} (at most {G.PICK_PCT}): "
                     f"{'qualifies' if ok else 'does not qualify'}")
    c0 = _exact(got.get("c0-tri"))
    lines.append(f"PICK: {p if p else 'none'}" + (
        f" ({G.load(p)}; stage {G.stage_of(p)}; BOUND {forms[p]['bound']:.3f} %)" if p else
        " (no form qualified: no flagged row runs; Q024 STOPPED before any flagged row)"))
    return controls, lines, dict(c0=c0, pick=p, forms=forms)


def info_of(roots):
    for root in roots:
        d = os.path.join(root, "s0")
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "cases.tsv")):
            return s0_info(d)[2]
    return None


def k_verdicts(stage, d, info):
    """(controls, rows, lines, bound) of a k stage."""
    form = KSTAGES[stage]
    got = readings_of(d)
    table = K.table(KP, stage)
    fi = (info or {}).get("forms", {}).get(form) or {}
    ref, b = fi.get("ref"), fi.get("bound")
    image = fi.get("image")
    picked = info is not None and info.get("pick") == form
    spread_max = None if b is None else b / 2
    controls, lines = {}, []
    controls["pick"] = True if picked else None
    lines.append(f"CONTROL pick: s0 picked {info.get('pick') if info else 'unread'} "
                 f"(this stage's form {form}): {'PASS' if picked else 'cannot tell'}")
    okb = b is not None and b <= G.CAP_PCT
    controls["bound"] = True if okb else None
    lines.append(f"CONTROL bound: BOUND {'unread' if b is None else f'{b:.3f} %'} "
                 f"(at most {G.CAP_PCT} %): {'PASS' if okb else 'cannot tell'}")
    ctl = [r["name"] for r in table if r["set"] == "control" and _value(r)]
    dev, drawn = {}, {}
    for n in ctl:
        g = got.get(n)
        drawn[n] = draws(g, form, image)
        if drawn[n] and ref and b is not None:
            dev[n] = _pct(g["us"], ref)
    out = [n for n in dev if abs(dev[n]) > b]
    allowed = out if len(out) <= G.OUTLIERS else []
    for r in table:
        if r["set"] != "control":
            continue
        n = r["name"]
        g = got.get(n)
        if n not in ctl:            # c-end: an exact triangle, no write
            s, note = _exact(g), ""
        elif not drawn[n]:
            s, note = drawn[n], ""
        elif n not in dev:
            s, note = None, " (no s0 reference or bound)"
        elif n in allowed:
            s, note = True, (f", {dev[n]:+.2f} % of s0's {ref:.0f} us: outside the band, the one "
                             f"allowed outlier (left out of MED)")
        else:
            s = abs(dev[n]) <= b
            note = f", {dev[n]:+.2f} % of s0's {ref:.0f} us (band {b:.2f} %)"
        controls[n] = s
        txt = "no reading" if g is None else ", ".join(
            f"{k} {g[k]}" for k in ("diff", "us", "img", "n") if k in g)
        lines.append(f"CONTROL {n}: {txt}{note}: {STATE[s]}")
    inband = [got[n]["us"] for n in dev if n not in out]
    med = statistics.median(inband) if inband else None
    spread = iqr_pct(inband) if len(inband) >= 4 else None
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
    gate_ok = SK.gate(controls).ok
    for v in sorted(vals):
        devs, other = {}, []
        for sset, n in vals[v].items():
            g = got.get(n)
            if g and draws(g, form, None) and g["image"] != image:
                other.append(n)
            if g and draws(g, form, image) and med:
                devs[sset] = _pct(g["us"], med)
        if len(devs) < 2 or not gate_ok:
            state = None
        else:
            a, bb = devs["fit"], devs["held"]
            state = not (abs(a) > b and abs(bb) > b and (a > 0) == (bb > 0))
            far.append((max(abs(a), abs(bb)), v))
        rows.append(state)
        txt = ", ".join(f"{k} {x:+.2f} %" for k, x in sorted(devs.items())) or "no reading"
        note = " (fit pass outside, held-out inside: noise by the frozen rule)" if state and \
            abs(devs["fit"]) > b else ""
        lines.append(f"ROW {v}: {txt} of {med} us: "
                     f"{ {True: 'held', False: 'FAILED', None: 'cannot tell'}[state] }{note}")
        if other:
            lines.append(f"IMAGE {v}: {', '.join(other)} drew another image than the "
                         "references' (a finding)")
    far.sort(reverse=True)
    lines.append("FARTHEST: " + ", ".join(f"{v} {x:.2f} %" for x, v in far[:4]))
    return controls, rows, lines, b


def score_stage(stage, d, roots):
    """(lines, summary)"""
    if stage == "s0":
        controls, lines, info = s0_info(d)
        claim = (f"s0's references draw; picked form {info['pick']}" if info["pick"] else
                 "s0's references: no form qualified")
        # the headline counts c0-tri and the references; a reference that did not draw is a
        # FAILED control (the form does not qualify) but never a stop of its own
        return lines, SK.headline(claim, {"c0-tri": controls["c0-tri"]},
                                  [v for n, v in controls.items() if n != "c0-tri"])
    controls, rows, lines, b = k_verdicts(stage, d, info_of(roots))
    claim = CLAIM.format(load=G.load(KSTAGES[stage]), b=b if b is not None else float("nan"))
    return lines, SK.headline(claim, controls, rows)


def q024(root):
    s0 = os.path.join(root, "s0")
    if not os.path.exists(os.path.join(s0, "cases.tsv")):
        print("s0: not run")
        print("Q024: NOTHING (s0 did not run)")
        return 0
    info = s0_info(s0)[2]
    p = info["pick"]
    print(f"s0: c0-tri {STATE[info['c0']]}; pick {p or 'none'}")
    if not p:
        print("Q024: NOTHING (STOPPED before any flagged row: no form's references spread at most "
              f"{G.PICK_PCT} percent)")
        return 0
    st = G.stage_of(p)
    d = os.path.join(root, st)
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        print(f"{st}: not run")
        print(f"Q024: NOTHING ({st} did not run)")
        return 0
    h = score_stage(st, d, [root])[1]
    print(f"{st}: {h}")
    if "is not supported" in h:
        print(f"Q024: FINDING (a value outside on both passes on {st}): stays open, narrowed to "
              "those values")
    elif h.startswith("CR_PDS") and h.endswith("(64 of 64 rows decided)"):
        print("Q024: RETIRE (no value of 0x00-0x3f changes the render time of many small "
              f"triangles ({G.load(p)}) beyond {st}'s bound, both passes, controls held; the "
              "256x256 clause closed in E1124)")
    else:
        print(f"Q024: NOTHING ({st} did not decide 64 of 64)")
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d) and os.path.exists(os.path.join(d, "cases.tsv")):
                info = s0_info(d)[2]
                g = SK.gate({"c0-tri": info["c0"],
                             "pick": True if info["pick"] == KSTAGES[argv[2]] else None})
                print(f"gate {argv[2]} on {dep}: pick {info['pick'] or 'none'}: "
                      f"{'open' if g.ok else '; '.join(g.problems)}")
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
