#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r33-tim2's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 7dba6bd12e84, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py file NAME.txt               the readings of one job's text (a kept record's, offline)

r33-tim's scorer (E1131) with two corrections the run showed: a running count reaches 400000
itself (the reload word read once, E1131), and the window is read against the count's own line
fitted before the change, not against the change sample (a sample read late after its
timestamp, as E1131's t1-08 was, would move the whole model).

A row's readings (analyse(); run/hooks.sh's rd_words is the twin of the control keys):
  diff          the `diff:` lines summed
  ivl           ns a sample: regtimeline's TOTAL / samples, or the stored rows' mean step when
                TOTAL is 0
  lead, job     the median spacing (ns) of the stored rows before the tool starts and after
  ten           1 when every stored 0x0acc sample is a running count (bits 31:25 0, bit 24 set,
                bits 23:0 at most 400000), else 0
  ten0, ten9    the same for 0x0acc in the kit's snap0 and snap9
  tnoen, tover  the samples without bit 24 alone set in 31:24; those with bits 23:0 > 400000
  tmax          the largest bits 23:0
  rate, period  the timer's countdown: the timeline split at each reload (bits 23:0 rising by
                more than 200000; a late read is a dip, not a reload), each piece of 20 samples
                or more fitted by least squares (counts against us); rate = minus the median
                slope (counts/us), period = the median spacing (us) of the pieces' zero
                crossings, neighbours only
and with 0x0804 and 0x012c (t1):
  ccn, ccword, ccstart   CR_CACHE_CTRL's changes, its word after the first, ms from the tool's
                         start to it (the change sample: the first that differs from the first)
  tcc           bits 23:0 of 0x0acc in the change sample
  nline, dropped        the line: the samples of the 1 ms before the change, unwrapped across a
                reload, fitted by least squares, then fitted again without the samples more than
                1000 counts off the first fit (dropped); nline the samples kept
  lcc, rcc      the line's count at the change sample, and that sample's residual
  d26, w26, l26 the first CR_EVENT_STATUS bit 26 sample within 200 us after the change: us from
                the change, the episode's width (to the first sample with it clear), the line's
                count there
  wn, wmed, wmax        the window (the change sample to bit 26's fall, or to the change + 120
                us): its samples, the median and largest |residual| from the line
  as20, as120   |median residual| of the samples 20 to 60 us and 120 to 300 us after the change
Residuals are folded into +-200000. The window's readings (wmed, as20, as120) count only where
the row's premises hold: one change (ccn 1) and a line of 50 samples or more; else cannot tell.
The stage case t1-all: tccspread, the smallest arc of the 400000-count circle that holds every
decided row's lcc (5 rows at least).

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("t1", "t1d")
REQUIRED = {s: (".txt", ".snap0.regs", ".snap9.regs", "cases.tsv", "void.tsv", "readings.tsv")
            for s in STAGES}
GATES = {}
RELOAD = 400000         # the boot's timer word 0x61a80 (E008, E532)
MINSEG = 20             # samples a fitted piece needs
WIN_NO26_NS = 120000    # the window without a bit 26 episode
SEEK26_NS = 200000      # bit 26 counts only this soon after the change (E1120: up to 106.6 us)
PREMISED = ("wmed", "as20", "as120")
LINE_NS = 1_000_000      # the line is fitted on the samples of this span before the change
OFFLINE = 1000          # counts: a sample this far off the first fit is a late read
STAGE_CASE = "t1-all"


def producible(row):
    keys = {"diff", "ten0", "ten9"}
    if row["tool"] == "rt":
        keys |= {"ivl", "ten"}
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


def diff_sum(text):
    s = [int(ln.split()[1]) for ln in text.splitlines() if ln.startswith("diff: ") and
         ln.split()[1].isdigit()]
    return sum(s) if s else None


def reg(regs_text, off):
    for ln in regs_text.splitlines():
        p = ln.split()
        if len(p) >= 3 and p[0] == "reg" and p[1] == off:
            return int(p[2], 16)
    return None


def running(v):
    """A running count: bits 31:25 0, bit 24 set, bits 23:0 at most 400000."""
    return (v >> 24) == 1 and (v & 0xffffff) <= RELOAD


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def pieces(pts):
    """pts [(t_ns, count)] -> [(slope counts/us, zero crossing us, n)] of every piece between
    reloads with MINSEG samples or more, in order, None for a shorter one."""
    segs, cur = [], []
    for p in pts:
        if cur and p[1] > cur[-1][1] + RELOAD // 2:
            segs.append(cur)
            cur = []
        cur.append(p)
    if cur:
        segs.append(cur)
    out = []
    for s in segs:
        if len(s) < MINSEG:
            out.append(None)
            continue
        n = len(s)
        t0 = s[0][0]
        xs = [(t - t0) / 1000.0 for t, _ in s]
        ys = [c for _, c in s]
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx == 0:
            out.append(None)
            continue
        a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        b = my - a * mx
        out.append((a, t0 / 1000.0 - b / a if a else None, n))
    return out


def countdown(pts):
    """rate (counts/us) and period (us) of the pieces, None where they cannot give them."""
    ps = pieces(pts)
    fit = [p for p in ps if p]
    if not fit:
        return None, None, 0
    rate = round(-median([p[0] for p in fit]), 2)
    gaps = [b[1] - a[1] for a, b in zip(ps, ps[1:]) if a and b and a[1] is not None and
            b[1] is not None]
    period = round(median(gaps), 3) if gaps else None
    return rate, period, len(fit)


def fold(r):
    r %= RELOAD
    return r - RELOAD if r > RELOAD // 2 else r


def linefit(pts):
    """least squares count = a + b (t - t0) over pts [(t ns, count)]: (t0, a, b)."""
    n = len(pts)
    t0 = pts[0][0]
    xs = [t - t0 for t, _ in pts]
    ys = [c for _, c in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return t0, my - b * mx, b


def window(rows, regs, start):
    """The 0x0804 change, bit 26 after it, and the timer against its pre-change line."""
    out = {}
    c, s, k = regs.index(0x0804), regs.index(0x012c), regs.index(0x0acc)
    v0 = rows[0][1][c]
    ch = [i for i, (_, v) in enumerate(rows) if v[c] != v0]
    out["ccn"] = sum(1 for a, b in zip(rows, rows[1:]) if a[1][c] != b[1][c])
    if not ch:
        return out
    i = ch[0]
    tcc = rows[i][0]
    out["ccword"] = "0x%08x" % rows[i][1][c]
    out["ccstart"] = round((tcc - start) / 1e6, 2)
    out["tcc"] = rows[i][1][k] & 0xffffff
    pre = [(t, v[k] & 0xffffff) for t, v in rows[:i] if t >= tcc - LINE_NS]
    unw, off = [], 0
    for j, (t, cnt) in enumerate(pre):
        if j and cnt > pre[j - 1][1] + RELOAD // 2:
            off -= RELOAD
        unw.append((t, cnt + off))
    if len(unw) < 2:
        out["nline"] = len(unw)
        return out
    t0, a, b = linefit(unw)
    keep = [(t, cnt) for t, cnt in unw if abs(cnt - (a + b * (t - t0))) <= OFFLINE]
    out["dropped"], out["nline"] = len(unw) - len(keep), len(keep)
    if len(keep) < 2:
        return out
    t0, a, b = linefit(keep)

    def line(t):
        return (a + b * (t - t0) - off) % RELOAD

    def res(t, cnt):
        return fold(cnt - line(t))
    out["lcc"] = round(line(tcc))
    out["rcc"] = round(res(tcc, out["tcc"]))
    end = tcc + WIN_NO26_NS
    for j in range(i, len(rows)):
        t, v = rows[j]
        if t > tcc + SEEK26_NS:
            break
        if v[s] & (1 << 26):
            out["d26"] = round((t - tcc) / 1000.0, 3)
            out["l26"] = round(line(t))
            for f in range(j + 1, len(rows)):
                if not rows[f][1][s] & (1 << 26):
                    out["w26"] = round((rows[f][0] - t) / 1000.0, 3)
                    end = rows[f][0]
                    break
            break
    win = [abs(res(t, v[k] & 0xffffff)) for t, v in rows[i:] if t <= end]
    out["wn"] = len(win)
    if win:
        out["wmed"] = round(median(win), 1)
        out["wmax"] = round(max(win), 1)
    for key, lo, hi in (("as20", 20_000, 60_000), ("as120", 120_000, 300_000)):
        sr = [res(t, v[k] & 0xffffff) for t, v in rows if lo <= t - tcc <= hi]
        if sr:
            out[key] = round(abs(median(sr)), 1)
    return out


def analyse(text, snap0="", snap9=""):
    """Every reading of one job (absent where the job cannot give it)."""
    r = dict(diff=diff_sum(text))
    for key, sn in (("ten0", snap0), ("ten9", snap9)):
        v = reg(sn, "0x0acc")
        if v is not None:
            r[key] = 1 if running(v) else 0
    tl = timeline(text)
    if tl is None or not tl["rows"]:
        return r
    rows, regs = tl["rows"], tl["regs"]
    r.update(cut=tl["cut"], rc=tl["rc"])
    st = tl["start"]
    gl = [b[0] - a[0] for a, b in zip(rows, rows[1:]) if a[0] < st]
    gj = [b[0] - a[0] for a, b in zip(rows, rows[1:]) if a[0] >= st]
    if gl:
        r["lead"] = median(gl)
    if gj:
        r["job"] = median(gj)
    if tl["seconds"] > 0 and tl["samples"]:
        r["ivl"] = int(tl["seconds"] * 1e9 / tl["samples"])
    elif len(rows) > 1:
        r["ivl"] = int((rows[-1][0] - rows[0][0]) / (len(rows) - 1))
    if 0x0acc in regs:
        k = regs.index(0x0acc)
        vs = [v[k] for _, v in rows]
        r["ten"] = 1 if all(running(v) for v in vs) else 0
        r["tnoen"] = sum(1 for v in vs if (v >> 24) != 1)
        r["tover"] = sum(1 for v in vs if (v & 0xffffff) > RELOAD)
        r["tmax"] = max(v & 0xffffff for v in vs)
        r["rate"], r["period"], _ = countdown([(t, v[k] & 0xffffff) for t, v in rows])
        if 0x0804 in regs and 0x012c in regs:
            r.update(window(rows, regs, tl["start"]))
    return {k: v for k, v in r.items() if v is not None}


# ---- verdicts -----------------------------------------------------------------------------
def inside(value, want):
    """A frozen value: exact (hex or decimal text) or a closed window lo..hi."""
    if value is None:
        return None
    if ".." in want:
        lo, hi = (float(x) for x in want.split(".."))
        return lo <= float(value) <= hi
    if want.startswith("0x") or str(value).startswith("0x"):
        try:
            return int(str(value), 16) == int(want, 16)
        except ValueError:
            return False
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
                K.text(self.d, n + ".txt"), K.text(self.d, n + ".snap0.regs"),
                K.text(self.d, n + ".snap9.regs"))
        return self.read[n]


def window_ok(a):
    if a is None:
        return None
    return a.get("ccn") == 1 and a.get("nline", 0) >= 50


def spread(vals):
    """The smallest arc of the RELOAD circle holding every value."""
    s = sorted(v % RELOAD for v in vals)
    gaps = [b - a for a, b in zip(s, s[1:])] + [s[0] + RELOAD - s[-1]]
    return RELOAD - max(gaps)


READ_KEYS = ("ivl", "lead", "job", "ten", "ten0", "ten9", "tnoen", "tover", "tmax", "rate",
             "period", "ccn", "ccword", "ccstart", "tcc", "nline", "dropped", "lcc", "rcc",
             "d26", "w26", "l26", "wn", "wmed", "wmax", "as20", "as120")


def verdicts(stage, d):
    kp = Kept(stage, d)
    controls, per_model, lines = {}, {}, []
    preds = frozen(stage)
    tccs = []
    for r in K.table(KP, stage):
        n = r["name"]
        a = kp.get(n)
        mine = [p for p in preds if p[0] == n]
        ctl = [p for p in mine if p[4] == "control"]
        if r["set"] == "control":
            res = {q: inside(None if a is None else a.get(q), v) for _, q, v, _, _ in ctl}
            state = None if a is None or any(v is None for v in res.values()) else \
                all(res.values())
            controls[n] = state
            lines.append(f"CONTROL {n}: " + " ".join(
                f"{q}={a.get(q) if a else None}" for _, q, _, _, _ in ctl) + ": " +
                ("PASS" if state else "FAILED" if state is False else "cannot tell"))
        for _, q, v, m, s in mine:
            if s == "control":
                continue
            got = None if a is None else a.get(q)
            st = inside(got, v)
            why = ""
            if q in PREMISED and window_ok(a) is not True:
                st, why = None, " (premise: one change, a line of 50 samples)"
            per_model.setdefault(m, []).append(st)
            lines.append(f"ROW {n} [{s}] {m} {q}={got} (frozen {v}): "
                         + ("held" if st else "FAILED" if st is False else "cannot tell") + why)
        if a is not None:
            if window_ok(a) and "lcc" in a:
                tccs.append(a["lcc"])
            lines.append(f"READ {n}: " + " ".join(f"{k}={a.get(k)}" for k in READ_KEYS
                                                    if a.get(k) is not None))
    for _, q, v, m, s in [p for p in preds if p[0] == STAGE_CASE]:
        got = spread(tccs) if len(tccs) >= 5 else None
        st = inside(got, v)
        per_model.setdefault(m, []).append(st)
        lines.append(f"ROW {STAGE_CASE} [{s}] {m} {q}={got} over {len(tccs)} rows (frozen {v}): "
                     + ("held" if st else "FAILED" if st is False else "cannot tell"))
    return controls, per_model, lines


CLAIMS = {
    "H-DRAW": "every triangle draws exactly",
    "H-SPACING": "the sampler's median spacing before the tool (t1 1100 to 1500, t1d 550 to 900 "
                 "ns) and in the job (3500 to 7500 ns), as E1131 measured",
    "H-TIM-EN": "EVENT_TIMER keeps bit 24 (alone in 31:24) through the job",
    "H-TIM-RANGE": "EVENT_TIMER bits 23:0 never exceed 400000",
    "H-TIM-24": "EVENT_TIMER bits 23:0 run through 24 bits (some sample above 400000)",
    "H-TIM-RELOAD": "the count reloads to 400000 (largest sample 399500 to 400000)",
    "H-TIM-399": "the count drops 398.9 to 399.1 a us, a 1002.40 to 1002.65 us period (E1131, "
                 "E009)",
    "H-TIM-400": "the count drops 399.5 to 400.5 a us, a 998.8 to 1001.2 us period (400 MHz)",
    "H-CC-ONE": "CR_CACHE_CTRL changes once, to 0x1000ffff",
    "H-CC-LAT": "the change comes 18 to 27 ms after the tool starts",
    "H-TIM-LINE": "against the line fitted on the 1 ms before the change, the window's median "
                  "|residual| is at most 800 and the 120 to 300 us median at most 400 counts",
    "H-TIM-WRITE": "120 to 300 us after the change the count sits 2000 counts or more off its "
                   "pre-change line: a write, reload or stop by the kick pass",
    "H-TIM-ASYNC": "the line's count at the change spreads over 100000 counts or more across rows",
    "H-TIM-SYNC": "the line's count at the change sits within 20000 counts across rows",
}


def read_files(stage, d):
    kp = Kept(stage, d)
    for r in K.table(KP, stage):
        kp.get(r["name"])


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0 if GATES.get(argv[2]) is None else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "file":
        a = analyse(open(argv[2], errors="replace").read())
        print(" ".join(f"{k}={v}" for k, v in a.items()))
        return 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for m, rows in sorted(per_model.items()):
            print(f"SUMMARY: {argv[1]} {m} [held]: " +
                  SK.headline(CLAIMS.get(m, m), controls, rows))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
