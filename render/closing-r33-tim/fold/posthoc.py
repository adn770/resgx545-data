#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r33-tim's post-hoc readings (not frozen; the frozen controls failed on ivl).

  posthoc.py OUT_ATTEMPT_DIR     one line a row of t1 and t1d, then a summary

Per row: the median sample spacing (ns) in the lead (before the tool starts) and in the job (from
its start to the end of sampling), the largest spacing in the job (gmax, ns); the timer's rate and period (score.py's countdown over the
whole timeline). t1 rows also: the CR_CACHE_CTRL change (ms after the tool's start, the bracket:
ns from the sample before to the change sample), the count at the change sample (tcc), bit 26's
first episode within 200 us (d26, w26 us), and the timer against a line fitted on the samples of
the 1 ms before the change (unwrapped across a reload; fitted twice, the second time without
the samples more than 1000 counts off the first fit, `dropped`): the change sample's residual, the
median and largest |residual| of the window's samples (the change sample to bit 26's fall, or
+120 us), the count the line gives at the change (lcc) and at bit 26's rise and fall, and the
median signed residual 20 to 60 us (s20) and 120 to 300 us (s120) after the change."""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402

R = SC.RELOAD


def med(xs):
    return SC.median(xs)


def linefit(pts):
    """least squares count = a + b (t - t0) (t in ns, b counts/ns) over pts [(t, c)]."""
    n = len(pts)
    t0 = pts[0][0]
    xs = [t - t0 for t, _ in pts]
    ys = [c for _, c in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return t0, my - b * mx, b


def row(path):
    text = gzip.open(path, "rt").read()
    tl = SC.timeline(text)
    rows, regs, st = tl["rows"], tl["regs"], tl["start"]
    k = regs.index(0x0acc)
    t = [r[0] for r in rows]
    lead = med([b - a for a, b in zip(t, t[1:]) if a < st])
    job = med([b - a for a, b in zip(t, t[1:]) if a >= st])
    rate, period, _ = SC.countdown([(x, v[k] & 0xffffff) for x, v in rows])
    gmax = max(b - a for a, b in zip(t, t[1:]) if a >= st)
    out = dict(lead=lead, job=job, gmax=gmax, rate=rate, period=period)
    if 0x0804 not in regs:
        return out
    c, s = regs.index(0x0804), regs.index(0x012c)
    i = next(j for j, (_, v) in enumerate(rows) if v[c] != rows[0][1][c])
    tcc = rows[i][0]
    out.update(ccstart=round((tcc - st) / 1e6, 3), bracket=tcc - rows[i - 1][0],
               tcc=rows[i][1][k] & 0xffffff)
    # the line: the samples of the 1 ms before the change, unwrapped across a reload
    pre = [(x, v[k] & 0xffffff) for x, v in rows[:i] if x >= tcc - 1_000_000]
    unw, off = [], 0
    for j, (x, cnt) in enumerate(pre):
        if j and cnt > pre[j - 1][1] + R // 2:
            off -= R
        unw.append((x, cnt + off))
    t0, a, b = linefit(unw)
    # a read late after its timestamp (a preempted sample) sits far below the line: drop the
    # samples more than 1000 counts off the first fit and fit again
    keep = [(x, cnt) for x, cnt in unw if abs(cnt - (a + b * (x - t0))) <= 1000]
    out["dropped"] = len(unw) - len(keep)
    t0, a, b = linefit(keep)

    def line(x):
        return (a + b * (x - t0) - off) % R

    def res(x, cnt):
        return SC.fold(cnt - line(x))
    out["lcc"] = round(line(tcc))
    out["rcc"] = round(res(tcc, out["tcc"]))
    end = tcc + SC.WIN_NO26_NS
    for j in range(i, len(rows)):
        x, v = rows[j]
        if x > tcc + SC.SEEK26_NS:
            break
        if v[s] & (1 << 26):
            out["d26"] = round((x - tcc) / 1000, 3)
            out["l26"] = round(line(x))
            f = next((m for m in range(j + 1, len(rows)) if not rows[m][1][s] & (1 << 26)), None)
            if f is not None:
                out["w26"] = round((rows[f][0] - x) / 1000, 3)
                out["lfall"] = round(line(rows[f][0]))
                end = rows[f][0]
            break
    win = [(x, v[k] & 0xffffff) for x, v in rows[i:] if x <= end]
    r = [abs(res(x, cnt)) for x, cnt in win]
    out.update(wn=len(win), wmed=round(med(r)), wmax=round(max(r)),
               wspan=round((win[-1][0] - win[0][0]) / 1000, 3))
    for key, lo, hi in (("s20", 20_000, 60_000), ("s120", 120_000, 300_000)):
        sr = [res(x, v[k] & 0xffffff) for x, v in rows if lo <= x - tcc <= hi]
        out[key] = round(med(sr)) if sr else None
    return out


def main(argv):
    att = argv[1]
    for st in ("t1", "t1d"):
        d = os.path.join(att, st)
        for name in sorted(f for f in os.listdir(d) if f.startswith(st + "-") and
                           f.endswith(".txt.gz")):
            r = row(os.path.join(d, name))
            print(name[:-7], " ".join(f"{k}={v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
