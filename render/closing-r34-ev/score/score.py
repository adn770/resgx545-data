#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r34-ev's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 fd916fedc118, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when GATES[STAGE]'s calibration opens it
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py file NAME.txt [SNAP0]       the readings of one job's text (a kept record's, offline)

A row's readings (analyse(); run/hooks.sh's rd_words is the twin of the control keys):
  ivl           ns a sample: regtimeline's end / samples (TOTAL 0: sampling lasts as long as the
                command, after a 5 ms lead), or seconds / samples when end is 0 (the kit's fake)
  r012c, r0118, r0660, r0748   the first sample of each sampled register (hex)
  img           the green count of the probe's `o0 mixed 0xff203040 xA 0xff00ff00 xG` line
  ovl           1 with the probe's "scene overflowed the parameter buffer" line, else 0
  diff, cok     the copy's `diff:` lines summed; 1 with its `copy: ok` line
with 0x012c (CR_EVENT_STATUS): an episode of bit B is a run of samples with B set (its width: the
first sample with it set to the first with it clear; one still set at the last sample has no
width); bits (every bit seen but 29), oom (episodes of bit 1 or 2), mt, gbl (of bit 1, of bit 2),
thr (of bit 3), e0, e14, e18 (of bits 0, 14, 18), w0max, w1max, w13max, w18max (ns, the widest);
with 0x0118 (CR_EVENT_STATUS2): s2 (episodes of bit 12 or bit 0), s2words (distinct words);
with 0x0748: bKn, bKmax, bKmin for K = 0..4 (episodes with bit K CLEAR, their widest and
narrowest in ns), b4ms (the widest bit 4 clear in ms); with 0x0660 (CR_DPM_3D_PAGE_COUNTS): pcn
(changes after the first sample), pcfin (the last word), pchi, pclo (its halves).

Controls: `reg:0xOFF` against `@snap0` (scorekit.reg_control on the row's own snap0, kept as
NAME.snap0.regs) or a constant (0x0748, not snapshotted); `ivl` against `@cal:STAGE`, the
calibration of that stage's rows OF THE SAME FORM (kitscore.calibration with their names: the
overflow probe, the copy and the large copy each load the CPU differently); img and diff exact.
A gate (GATES) opens when its calibration stage ran, no control there FAILED, every form a later
control cites has a window, and for d1 that window's median is at most D1_MAX_NS.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("e0", "e1", "e2c", "e2", "d0", "d1")
REQUIRED = {s: (".txt", ".snap0.regs", "cases.tsv", "void.tsv", "readings.tsv") for s in STAGES}
GATES = {"e1": "e0", "e2": "e2c", "d1": "d0"}
D1_MAX_NS = 3500        # E1057's bit 2 clear is 3.9 to 4.1 us: a coarser sampler can miss one
STAGE_CASE = {"d1": "d1-all"}
OVL = "scene overflowed the parameter buffer"
O0 = re.compile(r"o0 mixed 0xff203040 x(\d+) 0xff00ff00 x(\d+)")


def form(args):
    """The job form of a row's args: ovf, copy or lcopy."""
    if " probe " in f" {args} ":
        return "ovf"
    return "lcopy" if "--width 256" in args else "copy"


def producible(row):
    keys = {"ivl"}
    a = row["args"]
    regs = a.split()[2].split(",") if a.count(" -- ") else []
    keys |= {"r" + r[2:] for r in regs}
    keys |= {"img", "ovl"} if form(a) == "ovf" else {"diff", "cok"}
    if "0x0748" in regs:
        keys |= {f"b{k}n" for k in range(5)}
    return keys


# ---- one job ----------------------------------------------------------------------------------
def timeline(text):
    """regtimeline's block: dict(regs, samples, seconds, start, end, rc, rows=[(t, [v])], cut)
    or None when the text has none."""
    tl = None
    for ln in text.splitlines():
        if ln.startswith("timeline: regs"):
            if tl is not None:
                break
            p = ln.split()
            i = p.index("samples")
            tl = dict(regs=[int(x, 16) for x in p[2:i]], samples=int(p[i + 1]),
                      seconds=float(p[i + 3]), start=int(p[i + 5]), end=int(p[i + 7]),
                      rc=int(p[i + 9]), rows=[], cut=False)
        elif ln.startswith("tl ") and tl is not None:
            p = ln.split()
            if len(p) != len(tl["regs"]) + 2:
                tl["cut"] = True
                break
            tl["rows"].append((int(p[1]), [int(x, 16) for x in p[2:]]))
    return tl


def episodes(rows, k, test):
    """[(start ns, width ns or None)] of the runs of samples whose register k passes test."""
    out, st = [], None
    for t, v in rows:
        on = test(v[k])
        if on and st is None:
            st = t
        elif not on and st is not None:
            out.append((st, t - st))
            st = None
    if st is not None:
        out.append((st, None))
    return out


def widest(eps):
    w = [x for _, x in eps if x is not None]
    return max(w) if w else None


def analyse(text, snap0=""):
    a = {}
    s = [int(ln.split()[1]) for ln in text.splitlines()
         if ln.startswith("diff: ") and ln.split()[1].isdigit()]
    if s:
        a["diff"] = sum(s)
    if "copy: ok," in text:
        a["cok"] = 1
    m = O0.search(text)
    if m:
        a["img"] = int(m.group(2))
    if any(ln.startswith("probe p1139-green: ") for ln in text.splitlines()):
        a["ovl"] = 1 if OVL in text else 0
    tl = timeline(text)
    if tl is None or not tl["rows"]:
        return a
    a["tl"] = len(tl["rows"])
    a["cut"] = int(tl["cut"])
    a["tlrc"] = tl["rc"]
    if tl["end"] > 0 and tl["samples"] > 0:
        a["ivl"] = int(tl["end"] / tl["samples"])
    elif tl["seconds"] > 0 and tl["samples"] > 0:
        a["ivl"] = int(tl["seconds"] * 1e9 / tl["samples"])
    rows = tl["rows"]
    for i, r in enumerate(tl["regs"]):
        a[f"r{r:04x}"] = f"0x{rows[0][1][i]:08x}"
    if 0x012C in tl["regs"]:
        k = tl["regs"].index(0x012C)
        seen = set()
        for _, v in rows:
            seen |= {b for b in range(32) if v[k] >> b & 1}
        a["bits"] = ",".join(str(b) for b in sorted(seen - {29}))
        ep = {b: episodes(rows, k, lambda x, b=b: x >> b & 1) for b in (0, 1, 2, 3, 13, 14, 18)}
        a["oom"] = len(episodes(rows, k, lambda x: x & 0x6))
        a["mt"], a["gbl"], a["thr"] = len(ep[1]), len(ep[2]), len(ep[3])
        a["e0"], a["e14"], a["e18"] = len(ep[0]), len(ep[14]), len(ep[18])
        for b in (0, 1, 13, 18):
            w = widest(ep[b])
            if w is not None:
                a[f"w{b}max"] = w
            elif not ep[b]:
                a[f"w{b}max"] = 0
    if 0x0118 in tl["regs"]:
        k = tl["regs"].index(0x0118)
        a["s2"] = len(episodes(rows, k, lambda x: x & 0x1001))
        a["s2words"] = len({v[k] for _, v in rows})
    if 0x0748 in tl["regs"]:
        k = tl["regs"].index(0x0748)
        for b in range(5):
            ep = episodes(rows, k, lambda x, b=b: not x >> b & 1)
            a[f"b{b}n"] = len(ep)
            w = [x for _, x in ep if x is not None]
            if w:
                a[f"b{b}max"], a[f"b{b}min"] = max(w), min(w)
            elif not ep:
                a[f"b{b}max"] = 0
            if b == 4 and w:
                a["b4ms"] = round(max(w) / 1e6, 1)
    if 0x0660 in tl["regs"]:
        k = tl["regs"].index(0x0660)
        a["pcn"] = sum(1 for (_, v), (_, w) in zip(rows, rows[1:]) if v[k] != w[k])
        fin = rows[-1][1][k]
        a["pcfin"], a["pchi"], a["pclo"] = f"0x{fin:x}", fin >> 16, f"0x{fin & 0xffff:x}"
    return a


# ---- frozen values ----------------------------------------------------------------------------
def inside(value, want):
    """value against a frozen value: A..B, a hex or decimal constant, or a word."""
    if value is None:
        return None
    if ".." in want:
        lo, hi = want.split("..")
        try:
            return float(lo) <= float(value) <= float(hi)
        except ValueError:
            return False
    if want.startswith("0x"):
        try:
            return int(str(value), 16) == int(want, 16)
        except ValueError:
            return False
    try:
        return float(value) == float(want)
    except ValueError:
        return str(value) == want


def frozen(stage):
    """[(case, quantity, value, model, set)] of predictions/STAGE.tsv."""
    out = []
    lines = open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 5:
            out.append(tuple(f[:5]))
    return out


class Kept:
    def __init__(self, stage, d):
        self.stage, self.d = stage, d
        self.cases = K.rows(d, "cases.tsv")
        self.void = K.rows(d, "void.tsv")
        self.readings = K.readings(d)
        self.read = {}

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def get(self, n):
        if n not in self.read:
            self.read[n] = None if not self.done(n) else analyse(
                K.text(self.d, n + ".txt"), K.text(self.d, n + ".snap0.regs"))
        return self.read[n]

    def snaps(self):
        return {n: K.snap_regs(self.d, n) for n in self.cases if self.done(n)}


def calibrations(cal_stage, roots):
    """{form: scorekit.Calibration} of a calibration stage's kept rows, per job form; {} when
    the stage did not run under any root."""
    for root in roots:
        d = os.path.join(root, cal_stage)
        if not os.path.isdir(d):
            continue
        tab = K.table(KP, cal_stage)
        cases = K.rows(d, "cases.tsv")
        forms = {}
        for r in tab:
            forms.setdefault(form(r["args"]), []).append(r["name"])
        out = {}
        for f, names in forms.items():
            done = [n for n in names if n in cases and K.completed(cases[n])]
            out[f] = K.calibration(d, done)
        return out
    return {}


def control_state(stage, a, ctl, n, snaps, cals, form_):
    res = {}
    for _, q, v, _, _ in ctl:
        if q.startswith("reg:"):
            got = a.get("r" + q[6:]) if a else None
            res[q] = SK.reg_control(None if got is None else int(got, 16), v, q[4:], n, snaps)
        elif q == "ivl":
            c = cals.get(form_)
            res[q] = SK.ivl_control(a.get("ivl") if a else None, v,
                                    {v[5:]: c} if c is not None else {})
        else:
            res[q] = inside(None if a is None else a.get(q), v)
    state = None if a is None or any(x is None for x in res.values()) else all(res.values())
    if a is not None and any(x is False for x in res.values()):
        state = False
    return res, state


READ_KEYS = ("ivl", "r012c", "r0118", "r0660", "r0748", "img", "ovl", "diff", "cok", "bits",
             "oom", "mt", "gbl", "thr", "e0", "e14", "e18", "w0max", "w1max", "w13max", "w18max",
             "s2", "s2words", "b0n", "b0max", "b1n", "b1max", "b2n", "b2max", "b3n", "b3max",
             "b4n", "b4ms", "pcn", "pcfin", "pchi", "pclo")


def verdicts(stage, d, roots=()):
    kp = Kept(stage, d)
    snaps = kp.snaps()
    cal_stage = GATES.get(stage)
    cals = calibrations(cal_stage, roots or (os.path.dirname(d),)) if cal_stage else {}
    controls, per_model, lines = {}, {}, []
    preds = frozen(stage)
    b2tot, b2rows = 0, 0
    for r in K.table(KP, stage):
        n = r["name"]
        a = kp.get(n)
        mine = [p for p in preds if p[0] == n]
        ctl = [p for p in mine if p[4] == "control"]
        if r["set"] == "control":
            res, state = control_state(stage, a, ctl, n, snaps, cals, form(r["args"]))
            controls[n] = state
            lines.append(f"CONTROL {n}: " + " ".join(
                f"{q}={(a or {}).get('r' + q[6:] if q.startswith('reg:') else q)}"
                f"({'ok' if x else 'FAIL' if x is False else '?'})" for q, x in res.items())
                + ": " + ("PASS" if state else "FAILED" if state is False else "cannot tell"))
        for _, q, v, m, s in mine:
            if s == "control":
                continue
            got = None if a is None else a.get(q)
            st = inside(got, v)
            per_model.setdefault(m, []).append(st)
            lines.append(f"ROW {n} [{s}] {m} {q}={got} (frozen {v}): "
                         + ("held" if st else "FAILED" if st is False else "cannot tell"))
        if a is not None:
            if stage == "d1" and r["set"] != "control" and "b2n" in a:
                b2tot += a["b2n"]
                b2rows += 1
            lines.append(f"READ {n}: " + " ".join(f"{k}={a.get(k)}" for k in READ_KEYS
                                                    if a.get(k) is not None))
    case = STAGE_CASE.get(stage)
    for _, q, v, m, s in [p for p in preds if p[0] == case]:
        got = b2tot if b2rows >= 3 else None
        st = inside(got, v)
        per_model.setdefault(m, []).append(st)
        lines.append(f"ROW {case} [{s}] {m} {q}={got} over {b2rows} rows (frozen {v}): "
                     + ("held" if st else "FAILED" if st is False else "cannot tell"))
    for f, c in sorted(cals.items()):
        lines.append(f"CAL {cal_stage} {f}: median {c.ns} ns over {c.rows} rows, window "
                     f"{c.window}" + (f" ({'; '.join(c.problems)})" if c.problems else ""))
    return controls, per_model, lines


CLAIMS = {
    "H-CTL": "the controls",
    "H-IMG": "the probe draws the kept image of its PB size",
    "H-OOM-SET": "an overflowing job shows CR_EVENT_STATUS bit 1 or 2 (DPM out of memory)",
    "H-OOM-NONE": "an overflowing job shows neither bit 1 nor bit 2",
    "H-OOM-MT": "the out-of-memory bit is never bit 2 (GBL)",
    "H-OOM-GBL": "bit 2 (GBL) shows in an overflowing job",
    "H-THR-NEVER": "bit 3 (REACHED_MEM_THRESH) never shows",
    "H-SHORT": "bits 0 and 13 pulse at most 8 us in an overflowing job",
    "H-PR0-QUIET": "a job that does not overflow shows no out-of-memory bit",
    "H-COPY": "a copy shows no bit 18 and no bit 0",
    "H-COPY-END": "a copy shows bit 18 (PIXELBE_END_RENDER) as a fill does",
    "H-S2-SET": "an overflowing job shows CR_EVENT_STATUS2 bit 12 or bit 0",
    "H-S2-NONE": "CR_EVENT_STATUS2 keeps its word through an overflowing job",
    "H-S2-COPYIDLE": "CR_EVENT_STATUS2 keeps one word through a copy",
    "H-B2PR": "0x0748 bit 2 clears in pulses of at most 7 us, none at PR 0, some at PR 1-7",
    "H-B2-NONE": "0x0748 bit 2 never clears in an overflowing job",
    "H-B4-ONE": "0x0748 bit 4 clears once a job",
    "H-B4-PR": "0x0748 bit 4 clears once a render (two or more in an overflowing job)",
    "H-B4-LEN": "the bit 4 clear lasts as r15-dpm's of the same PB size",
    "H-B1-PR": "0x0748 bit 1 clears in about 4 us pulses, more with more partial renders",
    "H-B3-LONG": "0x0748 bit 3 has a clear of 20 us or more at PR 4 and 7, none over 10 us at PR 0",
    "H-B3-SHORT": "0x0748 bit 3's clears stay under 10 us at PR 4 and 7",
    "H-B0-N": "0x0748 bit 0 clears 30 to 90 times a job",
    "H-PC-ONCE": "CR_DPM_3D_PAGE_COUNTS changes at most once a job",
    "H-PC-RENDER": "CR_DPM_3D_PAGE_COUNTS changes at each render (two or more)",
    "H-PC-FIN": "CR_DPM_3D_PAGE_COUNTS' final word is the kept word of its PB size",
}


def read_files(stage, d):
    kp = Kept(stage, d)
    for r in K.table(KP, stage):
        kp.get(r["name"])
    kp.snaps()


def gate(stage, roots):
    """(open, why) of a stage's gate: its calibration stage ran, no control there FAILED, every
    form a control of the stage cites has a window, d1's median is at most D1_MAX_NS."""
    dep = GATES.get(stage)
    if dep is None:
        return True, "no gate"
    d = next((os.path.join(r, dep) for r in roots if os.path.isdir(os.path.join(r, dep))), None)
    if d is None:
        return False, f"{dep} has not run"
    controls, _, _ = verdicts(dep, d, roots)
    bad = [n for n, s in controls.items() if s is False]
    if bad:
        return False, f"{dep}: control(s) FAILED: {', '.join(bad)}"
    cals = calibrations(dep, roots)
    want = {form(r["args"]) for r in K.table(KP, stage) if r["set"] == "control"}
    for f in sorted(want):
        c = cals.get(f)
        if c is None or c.window is None:
            return False, f"{dep}: no calibration window for {f}" + (
                f" ({'; '.join(c.problems)})" if c is not None and c.problems else "")
        if stage == "d1" and c.ns > D1_MAX_NS:
            return False, f"{dep}: the {f} interval {c.ns} ns is above {D1_MAX_NS} ns"
    return True, "open: " + ", ".join(f"{f} {cals[f].window}" for f in sorted(want))


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        ok, why = gate(argv[2], argv[3:])
        print(f"gate {argv[2]}: {why}")
        return 0 if ok else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) in (3, 4) and argv[1] == "file":
        snap = open(argv[3]).read() if len(argv) == 4 else ""
        a = analyse(open(argv[2], errors="replace").read(), snap)
        print(" ".join(f"{k}={v}" for k, v in a.items()))
        return 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], tuple(argv[3:]))
        print("\n".join(lines))
        for m, rows in sorted(per_model.items()):
            print(f"SUMMARY: {argv[1]} {m} [held]: " +
                  SK.headline(CLAIMS.get(m, m), controls, rows))
        if not per_model:
            print(f"SUMMARY: {argv[1]} calibration: " +
                  SK.headline("the calibration's controls", controls, []))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
