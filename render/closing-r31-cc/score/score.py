#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r31-cc's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 2ffa9a93727d, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py file NAME.txt               the readings of one job's text (a kept record's, offline)

Every row's text is t10's output then regtimeline's block (`timeline: regs ... samples N seconds
T start NS end NS rc R`, then `tl T_NS V...` a change). analyse() reads it; run/hooks.sh's
rd_words is its twin for the control readings (tests/test_session.py holds them equal).

The anchor of every timing reading is CR_CACHE_CTRL's (0x0804) change: `cct`, the first sample
whose 0x0804 differs from the first sample's. Times are microseconds from it, read at the
sample interval (a reading is the first sample that shows a change, so it is late by up to one
interval; two changes in one sample have no order: "same").

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what score()
reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("c1", "c2", "c3", "c4", "c5")
REQUIRED = {s: (".txt", "cases.tsv", "void.tsv", "readings.tsv") for s in STAGES}
GATES = {}          # no stage gates another: a FAILED control voids its own stage's headlines
IDLE = 0x20000000   # CR_EVENT_STATUS when idle (E547, E1115, E1121)
POST_NS = 5_000_000  # after the job's end, 5 ms for the kernel's own end of the job
PRE_US = 30.0       # the window before the change a BIF word or a served count is looked for
POST_US = 15.0      # the window after it for a BIF word (the TA path's writes come 31 us on, E1120)
CNT_US = 30.0       # the window after it for the next served count
TICK_US = 15.0      # a count within this of a tick the lead's cadence predicts may be a tick


def regs_of(args):
    """The REGS of a row's regtimeline args (`TOTAL LEAD REGS -- ...`)."""
    out = []
    for part in args.split()[2].split(","):
        lo, _, hi = part.partition("-")
        out += range(int(lo, 0), int(hi or lo, 0) + 4, 4)
    return out


def producible(row):
    regs = set(regs_of(row["args"])) if row["tool"] == "rt" else set()
    keys = {"diff", "ivl"} if regs else set()
    for reg, k in ((0x012c, "idle"), (0x0804, "cache"), (0x0b14, "se16"), (0x0c00, "bif0"),
                   (0x0a74, "dms0")):
        if reg in regs:
            keys.add(k)
    return keys


# ---- one job's text ------------------------------------------------------------------------
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


def episodes(rows, col, bit):
    """[(rise_ns, fall_ns or None, {words while set})] of one bit of one register."""
    out, cur = [], None
    for t, v in rows:
        on = v[col] >> bit & 1
        if on and cur is None:
            cur = [t, None, set()]
            out.append(cur)
        if cur is not None:
            if on:
                cur[2].add(v[col])
            else:
                cur[1] = t
                cur = None
    return [tuple(e) for e in out]


def advance(a, b):
    return ((b & 0xffff) - (a & 0xffff)) % 0x10000


def value_at(rows, col, t):
    """The value a register held at t (the last change at or before t)."""
    cur = None
    for tt, v in rows:
        if tt > t:
            break
        cur = v[col]
    return cur


def diff_sum(text):
    s = [int(ln.split()[1]) for ln in text.splitlines() if ln.startswith("diff: ") and
         ln.split()[1].isdigit()]
    return sum(s) if s else None


def us(a, b):
    return round((b - a) / 1000, 1)


def analyse(text):
    """Every reading of one job (None where the job cannot give it)."""
    r = dict(diff=diff_sum(text))
    tl = timeline(text)
    if tl is None or not tl["rows"]:
        r["timeline"] = None
        return r
    rows, regs = tl["rows"], tl["regs"]
    st, en = tl["start"], tl["end"]
    dur = max(tl["seconds"] * 1e9, en)
    r.update(timeline=tl, cut=tl["cut"], rc=tl["rc"])
    r["ivl"] = int(dur / tl["samples"]) if tl["samples"] else None
    cct = None
    if 0x0804 in regs:
        c = regs.index(0x0804)
        v0 = rows[0][1][c]
        r["cache"] = "0x%08x" % v0
        ch = [i for i, (_, v) in enumerate(rows) if v[c] != v0]
        r["ccn"] = sum(1 for a, b in zip(rows, rows[1:]) if a[1][c] != b[1][c])
        r["ccword"] = "0x%08x" % rows[ch[0]][1][c] if ch else None
        r["ccback"] = (1 if any(v[c] == v0 for _, v in rows[ch[0]:]) else 0) if ch else None
        if ch:
            cct = rows[ch[0]][0]
            r["ccstart"] = round((cct - st) / 1e6, 2)      # ms from the command's start
    e26 = []
    if 0x012c in regs:
        c = regs.index(0x012c)
        r["idle"] = "0x%08x" % rows[0][1][c]
        out = [t for t, v in rows if (t < st or t > en + POST_NS) and v[c] != IDLE]
        held = value_at(rows, c, en + POST_NS)
        r["outside"] = len(out) + (1 if rows[-1][0] > en + POST_NS and held != IDLE else 0)
        e26 = episodes(rows, c, 26)
        r["b26n"] = len(e26)
        ends = [e[0] for b in (18, 0) for e in episodes(rows, c, b)]
        first_end = min(ends) if ends else None
        r["b26lead"] = us(e26[0][0], first_end) if e26 and first_end is not None else None
        # the change's lead to bit 26, only where bit 26 precedes the render end (E1120: the
        # rows whose bit 26 came after it gave 5 and 18 ms)
        r["cc26"] = us(cct, e26[0][0]) if cct is not None and e26 and \
            r["b26lead"] is not None and r["b26lead"] > 0 else None
        r["ccfirst"] = (1 if not [t for t, v in rows if st <= t < cct and v[c] != IDLE] else 0) \
            if cct is not None else None
    if 0x0b14 in regs:
        r.update(serv(rows, regs.index(0x0b14), st, en, cct))
    if 0x0c00 in regs:
        r.update(bif(rows, regs.index(0x0c00), st, en, cct))
    if 0x0a74 in regs:
        c = regs.index(0x0a74)
        d0 = rows[0][1][c]
        r["dms0"] = "0x%08x" % d0
        after = [t for t, v in rows if cct is not None and t >= cct and v[c] != d0]
        r["dmslag"] = us(cct, after[0]) if after else None
        # 1: bit 26 rose before the write, 0: after it, None: one sample (no order) or no bit 26
        r["dms26"] = (1 if e26[0][0] < after[0] else 0 if e26[0][0] > after[0] else None) \
            if after and e26 and e26[0][0] >= cct else None
    return r


def ticks_near(lead, t0, t1):
    """True when a tick the lead's cadence predicts may fall in [t0, t1] (ns), or the lead gives
    no cadence: a count there is not read as the job's."""
    if len(lead) < 3:
        return True
    gaps = sorted(b - a for a, b in zip(lead, lead[1:]))
    per = gaps[len(gaps) // 2]
    if not 900_000 <= per <= 1_100_000:
        return True
    tol = TICK_US * 1000
    k = (t0 - tol - lead[-1]) // per
    while lead[-1] + k * per <= t1 + tol:
        p = lead[-1] + k * per
        if t0 - tol <= p <= t1 + tol:
            return True
        k += 1
    return False


def serv(rows, col, st, en, cct):
    """CR_USE0_SERV_EVENT (bit 16 EMPTY, bits 15:0 COUNT, E009): bit 16 of the first sample, the
    tick rate before the job, the counts over the job beyond the ticks, and around the change:
    cntlag (us from the change to the first count at or after it, 0 in the change's sample) and
    cntpre (1: a count in the 30 us before it), each None where a tick may fall in its window."""
    out = dict(se16=str(rows[0][1][col] >> 16 & 1))
    pre = [(t, v[col]) for t, v in rows if t < st]
    lead = [b[0] for a, b in zip(pre, pre[1:]) if advance(a[1], b[1])]
    if len(pre) >= 2 and pre[-1][0] > pre[0][0]:
        n = sum(advance(a[1], b[1]) for a, b in zip(pre, pre[1:]))
        rate = n / ((pre[-1][0] - pre[0][0]) / 1e6)
        out["tickrate"] = round(rate, 4)
        a, b = value_at(rows, col, st), value_at(rows, col, en)
        out["seextra"] = round(advance(a, b) - rate * (en - st) / 1e6) \
            if a is not None and b is not None else None
    else:
        out["tickrate"] = out["seextra"] = None
    out["selast16"] = rows[-1][1][col] >> 16 & 1
    out["cntlag"] = out["cntpre"] = None
    if cct is not None:
        counts = [b[0] for a, b in zip(rows, rows[1:]) if advance(a[1][col], b[1][col])]
        w = PRE_US * 1000
        if not ticks_near(lead, cct, cct + CNT_US * 1000):
            nxt = [t for t in counts if cct <= t <= cct + CNT_US * 1000]
            out["cntlag"] = us(cct, nxt[0]) if nxt else None
        if not ticks_near(lead, cct - w, cct):
            out["cntpre"] = 1 if [t for t in counts if cct - w <= t < cct] else 0
        out["clrpre"] = 1 if [t for t, v in rows if cct - w <= t <= cct
                              and not v[col] >> 16 & 1] else 0
    return out


def bif(rows, col, st, en, cct):
    """CR_BIF_CTRL (0x0c00): its first word, the words other than it in the job, and biford:
    "pre" when one shows in the 30 us before the change, else "post" when one shows in the 15 us
    after it (not in its sample), else None (none near it, or only in the change's own sample)."""
    b0 = rows[0][1][col]
    out = dict(bif0="0x%08x" % b0)
    job = [(t, v[col]) for t, v in rows if st <= t <= en and v[col] != b0]
    out["bifn"] = len(job)
    out["bifwords"] = ",".join(sorted({"0x%08x" % w for _, w in job})) or None
    out["biford"] = None
    if cct is not None:
        pre = [t for t, w in job if cct - PRE_US * 1000 <= t < cct]
        post = [t for t, w in job if cct < t <= cct + POST_US * 1000]
        out["biford"] = "pre" if pre else "post" if post else None
        out["bifsame"] = 1 if value_at(rows, col, cct) != b0 else 0
    return out


# ---- verdicts -----------------------------------------------------------------------------
def inside(value, want):
    """A frozen value: exact (hex or decimal text) or a closed window lo..hi."""
    if value is None:
        return None
    vals = value if isinstance(value, list) else [value]
    if ".." in want:
        lo, hi = (float(x) for x in want.split(".."))
        return all(lo <= float(v) <= hi for v in vals)
    if isinstance(value, list):
        return None
    if want.startswith("0x") or str(value).startswith("0x"):
        try:
            return int(str(value), 16) == int(want, 16)
        except ValueError:
            return False
    return str(value) == want


class Kept:
    def __init__(self, stage, d):
        self.stage, self.d = stage, d
        self.cases = K.rows(d, "cases.tsv")
        self.void = K.rows(d, "void.tsv")
        self.read = {}

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def get(self, n):
        if n not in self.read:
            self.read[n] = analyse(K.text(self.d, n + ".txt")) if self.done(n) else None
        return self.read[n]


READ_KEYS = ("ivl", "ccn", "ccword", "ccstart", "ccfirst", "cc26", "b26n", "b26lead",
             "tickrate", "seextra", "cntlag", "cntpre", "clrpre", "bifn", "bifwords", "biford",
             "bifsame", "dmslag", "dms26")


def verdicts(stage, d, roots=None):
    kp = Kept(stage, d)
    preds = K.predictions(KP, stage)
    controls, per_model, lines = {}, {}, []
    rows = K.table(KP, stage)
    for r in rows:
        n = r["name"]
        a = kp.get(n)
        want = preds.get(n, {})
        if r["set"] == "control":
            res = {q: inside(None if a is None else a.get(q), v)
                   for q, m in want.items() for v in m.values()}
            state = None if a is None or any(v is None for v in res.values()) else \
                all(res.values())
            controls[n] = state
            lines.append(f"CONTROL {n}: " + " ".join(
                f"{q}={a.get(q) if a else None}" for q in want) + ": " +
                ("PASS" if state else "FAILED" if state is False else "cannot tell"))
            continue
        for q, models in want.items():
            for m, v in models.items():
                got = None if a is None else a.get(q)
                st = inside(got, v)
                per_model.setdefault(m, {"fit": [], "held": []})[r["set"]].append(st)
                lines.append(f"ROW {n} [{r['set']}] {m} {q}={_fmt(got)} (frozen {v}): "
                             + ("held" if st else "FAILED" if st is False else "cannot tell"))
        if a is not None:
            lines.append(f"READ {n}: " + " ".join(
                f"{k}={_fmt(a.get(k))}" for k in READ_KEYS if k in a))
    for q, got in _stage_quantities(stage, kp, rows).items():
        for want_m, want in preds.get(stage, {}).get(q, {}).items():
            st = inside(got, want)
            per_model.setdefault(want_m, {"fit": [], "held": []})["held"].append(st)
            lines.append(f"STAGE {stage} {want_m} {q}={_fmt(got)} (frozen {want}): "
                         + ("held" if st else "FAILED" if st is False else "cannot tell"))
    return controls, per_model, lines


def _fmt(v):
    if isinstance(v, float):
        return "%.1f" % v
    return str(v)


def _stage_quantities(stage, kp, rows):
    data = [kp.get(r["name"]) for r in rows if r["set"] != "control"]
    ok = [a for a in data if a is not None and a.get("timeline")]
    out = {}
    if stage in ("c3", "c4", "c5"):
        # the rows whose BIF order is read: every held row ran, else cannot tell
        out["bifdecided"] = sum(1 for a in ok if a.get("biford")) if len(ok) == len(data) \
            else None
    return out


CLAIMS = {
    "H-CC-ONE": "CR_CACHE_CTRL changes once, 0x0000ffff to 0x1000ffff, and stays",
    "H-CC-LAT": "the change comes 1 to 40 ms after the tool starts",
    "H-CC-XFER": "a fill's kick changes CR_CACHE_CTRL as a triangle's does",
    "H-CC-TA": "only a TA kick changes CR_CACHE_CTRL",
    "H-CNT-LAG": "no served count in the 30 us before the change, the next 0 to 12 us after it",
    "H-CNT-LEAD": "a served count comes in the 30 us before the change",
    "H-BIF-FIRST": "a CR_BIF_CTRL word shows in the 30 us before the change (a firmware response "
                   "first: H-CC-FW)",
    "H-BIF-LATER": "CR_BIF_CTRL words show only after the change (H-CC-HW)",
    "H-BIF-VISIBLE": "CR_BIF_CTRL's words near the change are seen in at least one row",
    "H-BIF-HIDDEN": "CR_BIF_CTRL's words near the change are never seen",
    "H-CC-26": "bit 26 rises 15 to 120 us after the change",
    "H-DMS": "CR_DMS_CTRL is written 20 to 70 us after the change",
    "H-WAIT": "CR_DMS_CTRL is written after bit 26's first rise",
    "H-NOWAIT": "CR_DMS_CTRL is written before bit 26's first rise",
    "H-CCFIRST": "the change comes before every CR_EVENT_STATUS event of the job",
    "H-IDLE": "CR_EVENT_STATUS reads 0x20000000 outside the job",
}


def read_files(stage, d):
    kp = Kept(stage, d)
    for r in K.table(KP, stage):
        if kp.done(r["name"]):
            K.text(d, r["name"] + ".txt")
    K.rows(d, "readings.tsv")


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0 if GATES.get(argv[2]) is None else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "file":
        a = analyse(open(argv[2], errors="replace").read())
        a.pop("timeline", None)
        print(" ".join(f"{k}={_fmt(v)}" for k, v in a.items()))
        return 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        for m, sets in sorted(per_model.items()):
            for s in ("fit", "held"):
                if sets[s]:
                    print(f"SUMMARY: {argv[1]} {m} [{s}]: " +
                          SK.headline(CLAIMS.get(m, m), controls, sets[s]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
