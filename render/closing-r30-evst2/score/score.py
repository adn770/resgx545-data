#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r30-evst2's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 24e4a365f48b, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READ lines, then SUMMARY lines (exit 0);
                                       e3's density reads e1 from KEPT_DIR's attempt or a ROOT
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed (none)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py file NAME.txt               the readings of one job's text (a kept record's, offline)

Every row's text is t10's output then regtimeline's block (`timeline: regs ... samples N seconds
T start NS end NS rc R`, then `tl T_NS V...` a change). analyse() reads it; run/hooks.sh's
rd_words is its twin for the control readings (tests/test_session.py holds them equal).

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what score()
reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("e1", "e5", "e2", "e3", "e4")
REQUIRED = {s: (".txt", "cases.tsv", "void.tsv", "readings.tsv") for s in STAGES}
GATES = {}          # no stage gates another: a FAILED control voids its own stage's headlines
IDLE = 0x20000000   # CR_EVENT_STATUS when idle (E547)
POST_NS = 5_000_000  # after the job's end, 5 ms for the kernel's own end of the job
PIPE = {0x0118, 0x012c, 0x0804, 0x0b14}   # not pipeline registers (e3's kick anchor)


def regs_of(args):
    """The REGS of a row's regtimeline args (`TOTAL LEAD REGS -- ...`)."""
    out = []
    for part in args.split()[2].split(","):
        lo, _, hi = part.partition("-")
        out += range(int(lo, 0), int(hi or lo, 0) + 4, 4)
    return out


def producible(row):
    regs = regs_of(row["args"]) if row["tool"] == "rt" else []
    keys = {"diff", "idle", "ivl"} if 0x012c in regs else set()
    if {0x0118, 0x0804, 0x0b14} <= set(regs):
        keys |= {"idle2", "cache", "se16"}
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


def count16(v):
    return v & 0xffff


def advance(a, b):
    return (count16(b) - count16(a)) % 0x10000


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


def analyse(text):
    """Every reading of one job (None where the job cannot give it)."""
    r = dict(diff=diff_sum(text))
    tl = timeline(text)
    if tl is None or not tl["rows"] or 0x012c not in tl["regs"]:
        r["timeline"] = None
        return r
    rows, regs = tl["rows"], tl["regs"]
    c = regs.index(0x012c)
    st, en = tl["start"], tl["end"]
    dur = max(tl["seconds"] * 1e9, en)
    r.update(timeline=tl, cut=tl["cut"], rc=tl["rc"])
    r["ivl"] = int(dur / tl["samples"]) if tl["samples"] else None
    r["idle"] = "0x%08x" % rows[0][1][c]
    win = [(t, v) for t, v in rows if st <= t <= en + POST_NS]
    out = [t for t, v in rows if (t < st or t > en + POST_NS) and v[c] != IDLE]
    held = value_at(rows, c, en + POST_NS)       # a word still set when the window closes
    r["outside"] = len(out) + (1 if rows[-1][0] > en + POST_NS and held != IDLE else 0)
    e26 = episodes(rows, c, 26)
    r["b26n"] = len(e26)
    r["b26seen"] = 1 if e26 else 0
    r["b26word"] = ",".join("0x%08x" % w for w in sorted(set().union(*[e[2] for e in e26]))) \
        if e26 else None
    widths = [(f - s) / 1000 for s, f, _ in e26 if f is not None]
    r["b26width"] = widths or None
    r["b26first"] = (e26[0][1] - e26[0][0]) / 1000 if e26 and e26[0][1] is not None else None
    ends = [e[0] for b in (18, 0) for e in episodes(rows, c, b)]
    first_end = min(ends) if ends else None
    r["endclusters"] = clusters(sorted(ends))
    if e26 and first_end is not None:
        r["b26lead"] = (first_end - e26[0][0]) / 1000
        r["b26clear"] = 1 if e26[0][1] is not None and e26[0][1] <= first_end else 0
    else:
        r["b26lead"] = r["b26clear"] = None
    e14, e31 = episodes(rows, c, 14), episodes(rows, c, 31)
    if e14 or e31:
        r["swmaster"] = 1 if [e[:2] for e in e14] == [e[:2] for e in e31] else 0
    else:
        r["swmaster"] = None
    r["sub"] = sum(len(episodes(rows, c, b)) for b in (6, 9, 20))
    r["bits"] = sorted({b for _, v in win for b in range(32) if (v[c] ^ IDLE) >> b & 1})
    if 0x0118 in regs:
        c2 = regs.index(0x0118)
        r["idle2"] = "0x%08x" % rows[0][1][c2]
        r["st2"] = sum(1 for _, v in rows if v[c2] != 0x400)
        r["latch"] = 1 if any(v[c2] & 0xc0 for _, v in rows) else 0
    if 0x0804 in regs:
        c3 = regs.index(0x0804)
        v0 = rows[0][1][c3]
        r["cache"] = "0x%08x" % v0
        r["ccchg"] = sum(1 for _, v in rows if v[c3] != v0)
        ch = [i for i, (_, v) in enumerate(rows) if v[c3] != v0]
        r["ccword"] = "0x%08x" % rows[ch[0]][1][c3] if ch else None
        r["ccback"] = (1 if any(v[c3] == v0 for _, v in rows[ch[0]:]) else 0) if ch else None
        # the change's lead to bit 26, only where bit 26 precedes the render end (E1116: two
        # jobs whose bit 26 came late, after the render end, gave 16 and 21 ms)
        r["cc26"] = (e26[0][0] - rows[ch[0]][0]) / 1000 \
            if ch and e26 and r.get("b26lead") is not None and r["b26lead"] > 0 else None
    if 0x0b14 in regs:
        r.update(serv(rows, regs.index(0x0b14), st, en))
    pipe = [i for i, a in enumerate(regs) if a not in PIPE]
    if pipe and e26:
        first = None
        for (t0, v0), (t1, v1) in zip(rows, rows[1:]):
            if t1 >= st and any(v0[i] != v1[i] for i in pipe):
                first = t1
                break
        r["kick26"] = (e26[0][0] - first) / 1000 if first is not None else None
    return r


def clusters(ts, gap=500_000):
    """Render-end clusters: rises of bit 18 or 0 more than 500 us apart start a new one."""
    n, last = 0, None
    for t in ts:
        if last is None or t - last > gap:
            n += 1
        last = t
    return n


def serv(rows, col, st, en):
    """CR_USE0_SERV_EVENT: bit 16 of the first sample, the tick rate before the job (counts a
    ms), the counts over the job beyond the ticks that rate gives, bit 16 clear in the job."""
    out = dict(se16=str(rows[0][1][col] >> 16 & 1))
    pre = [(t, v[col]) for t, v in rows if t < st]
    if len(pre) >= 2 and pre[-1][0] > pre[0][0]:
        n = sum(advance(a[1], b[1]) for a, b in zip(pre, pre[1:]))
        rate = n / ((pre[-1][0] - pre[0][0]) / 1e6)
        out["tickrate"] = round(rate, 4)
        a, b = value_at(rows, col, st), value_at(rows, col, en)
        if a is not None and b is not None:
            out["seextra"] = round(advance(a, b) - rate * (en - st) / 1e6)
        else:
            out["seextra"] = None
    else:
        out["tickrate"] = out["seextra"] = None
    out["se16clr"] = sum(1 for t, v in rows if st <= t <= en and not v[col] >> 16 & 1)
    out["selast16"] = rows[-1][1][col] >> 16 & 1
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


def other_stage(d, stage, roots):
    for root in [os.path.dirname(os.path.abspath(d))] + list(roots or []):
        p = os.path.join(root, stage)
        if os.path.isdir(p):
            return p
    return None


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
            res = {q: inside(None if a is None else _ctl(a, q), v)
                   for q, m in want.items() for v in m.values()}
            state = None if a is None or any(v is None for v in res.values()) else \
                all(res.values())
            controls[n] = state
            lines.append(f"CONTROL {n}: " + " ".join(
                f"{q}={_ctl(a, q) if a else None}" for q in want) + ": " +
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
                f"{k}={_fmt(a.get(k))}" for k in ("ivl", "b26n", "b26word", "b26width", "b26first",
                                                  "b26lead", "endclusters", "bits", "st2", "ccchg",
                                                  "ccword", "ccback", "cc26",
                                                  "tickrate", "seextra", "se16clr", "kick26")
                if k in a))
    for m, v in _stage_quantities(stage, kp, rows, d, roots).items():
        q, got = v
        for want_m, want in preds.get(stage, {}).get(q, {}).items():
            st = inside(got, want)
            per_model.setdefault(want_m, {"fit": [], "held": []})["held"].append(st)
            lines.append(f"STAGE {stage} {want_m} {q}={_fmt(got)} (frozen {want}): "
                         + ("held" if st else "FAILED" if st is False else "cannot tell"))
    return controls, per_model, lines


def _ctl(a, q):
    return a.get(q)


def _fmt(v):
    if isinstance(v, float):
        return "%.1f" % v
    if isinstance(v, list):
        return "[" + ",".join(_fmt(x) for x in v) + "]"
    return str(v)


def _stage_quantities(stage, kp, rows, d, roots):
    data = [kp.get(r["name"]) for r in rows if r["set"] != "control"]
    ok = [a for a in data if a is not None and a.get("timeline")]
    out = {}
    if stage == "e1":
        out["seen"] = ("seen", sum(a["b26seen"] for a in ok) if len(ok) == len(data) else None)
    if stage == "e5":
        full = len(ok) == len(data)
        out["multi"] = ("multi", sum(1 for a in ok if a["b26n"] >= 2) if full else None)
        out["each"] = ("each", sum(1 for a in ok if a["b26n"] >= 3) if full else None)
    if stage == "e3":
        e1 = other_stage(d, "e1", roots)
        f3 = frac(ok)
        f1 = None
        if e1:
            k1 = Kept("e1", e1)
            d1 = [k1.get(r["name"]) for r in K.table(KP, "e1") if r["set"] != "control"]
            f1 = frac([a for a in d1 if a is not None and a.get("timeline")])
        out["density"] = ("density", None if f1 is None or f3 is None else round(f1 - f3, 3))
    if stage == "e4":
        rates = [a.get("tickrate") for a in ok + [kp.get(r["name"]) for r in rows
                                                   if r["set"] == "control" and kp.get(r["name"])]]
        rates = [x for x in rates if x is not None]
        out["tickrate"] = ("tickrate", round(sum(rates) / len(rates), 4) if rates else None)
    return out


def frac(ok):
    return sum(a["b26seen"] for a in ok) / len(ok) if ok else None


CLAIMS = {
    "H-ALONE": "bit 26 shows as the word 0x24000000 alone",
    "H-WIDE": "bit 26 stays 40 to 140 us",
    "H-BEFORE": "bit 26 rises 60 to 200 us before the render end and falls before it",
    "H-SW": "SW_EVENT and MASTER_INTERRUPT rise and fall together",
    "H-SUB": "bits 6, 9 and 20 stay under a sample",
    "H-IDLE": "CR_EVENT_STATUS reads 0x20000000 outside the job",
    "H-ST2": "CR_EVENT_STATUS2 stays 0x400",
    "H-WIDE1": "bit 26's first episode is 40 to 140 us with CR_EVENT_STATUS sampled alone",
    "H-NARROW4": "bit 26's first episode is 3 to 12 us with four registers sampled",
    "H-NARROW27": "bit 26's first episode is 8 to 20 us with 27 registers sampled",
    "H-CC-KICK": "CR_CACHE_CTRL goes from 0x0000ffff to 0x1000ffff 15 to 60 us before bit 26 and stays",
    "H-CC-FLAT": "CR_CACHE_CTRL reads its idle value throughout",
    "H-SE-EVENTS": "CR_USE0_SERV_EVENT counts the served events beyond the ticks",
    "H-SE-TICKS": "CR_USE0_SERV_EVENT counts ticks only",
    "H-EVERY": "bit 26 is seen in every plain triangle at the densest sampling",
    "H-PART": "bit 26 is missed in some plain triangles at the densest sampling",
    "H-ONCE": "at most 2 of 5 -n 3 jobs show bit 26 twice or more",
    "H-EACH": "3 or more -n 3 jobs show bit 26 once a render",
    "H-DENSITY": "bit 26 is seen more often at denser sampling",
    "H-INDEP": "bit 26 is seen as often at any sampling",
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
