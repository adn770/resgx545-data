#!/usr/bin/env python3
"""rules.py: the candidate rules of Q292's 4x fault (closing5/render4x/exp-render4x-r5.md 1.4, onset_fit.py), computed from a row's
argv (target W x H and the context's maximum MW x MH), standard library only.

  H-TPC [infer]: at 4x the TA keeps 4 bytes a tile of the doubled grid from the tail-pointer base on and clears them when the TA ends;
  where that extent passes a limit of the CONTEXT'S layout (the maximum's), the first region headers are zeroed and the 3D faults at
  the request base.  Four variants are frozen (decision R5-6 a): the extent dense (d) or row-strided by the macrotile span (rs) or
  rounded both ways (rb); the limit the region headers (`rgn`) or the state page (`state`).
  K rules: size rules with no mechanism.  K-W, K-H, K-OR, K-AND are fixed; K-TPM (tiles a macrotile), K-P (scene pages U4) and K-AREA
  (pixels) have a threshold the kept cells place only inside an interval: a rule of that kind is a FAMILY of thresholds, and a cell
  inside its open interval is predicted "either" (no threshold) and constrains the family when it is measured.

Every rule is a function of the argv only: fault(rule, w, h, mw, mh) -> True (fault) | False (complete) | None (no threshold there).
"""
import math

HTPC = ("TPC-d-rgn", "TPC-d-state", "TPC-rs-rgn", "TPC-rb-rgn")
KFIX = ("K-W", "K-H", "K-OR", "K-AND")
KTHR = ("K-TPM", "K-P", "K-AREA")
RULES = HTPC + KFIX + KTHR


def rup(a, m):
    return (a + m - 1) // m * m


def lay(w, h):
    """The single-sampled layout of sgx_render.c (fork a2788bd8) for a W x H context: tiles, macrotiles, tail side and offsets."""
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span = max(n * mx, n * my)
    side = 1
    while side < span:
        side <<= 1
    tail = rup(4 * side * side, 4096)
    return dict(tx=tx, ty=ty, n=n, mx=mx, my=my, side=side, ctl=tail, state=tail + 0x2000, rgn=tail + 0x3000,
                rgn_size=0xc0 * (mx // 4) * (my // 4) * n * n)


def u4(w, h):
    return 1 + math.ceil(2 * math.ceil(w / 16) * math.ceil(h / 16) / 32)


def extent(t, v):
    """The 4x tail extent in bytes of the TARGET's doubled grid, by variant."""
    if v == "d":
        return 4 * (2 * t["tx"]) * (2 * t["ty"])
    if v == "rs":
        return 4 * (2 * t["n"] * t["mx"]) * (2 * t["ty"])
    if v == "rb":
        return 4 * (2 * t["n"] * t["mx"]) * (2 * t["n"] * t["my"])
    raise KeyError(v)


def metric(rule, w, h):
    t = lay(w, h)
    return {"K-TPM": t["mx"] * t["my"], "K-P": u4(w, h), "K-AREA": w * h}[rule]


# the kept four-array 4x cells (E824, E828, E845, E846): the fit, POST HOC.  1 = fault.  The two 4096-wide faults also overflow and have
# a right block (exp 1.1): kept for the fixed rules as onset_fit.py did (all 11 rules fit 13 of 13), left out of the threshold intervals
FIT = [((64, 64), 0, "E824 c2"), ((288, 144), 0, "E824 h1, E828 j1r, E845 s0"), ((256, 288), 0, "E824 h2"),
       ((384, 384), 0, "E824 h3"), ((320, 160), 0, "E824 h4"), ((512, 384), 0, "E824 h5"),
       ((640, 480), 0, "E824 h6"), ((320, 400), 0, "E824 h7"), ((1024, 768), 0, "E824 h8, E845 s0, E846 o3"),
       ((1280, 1024), 1, "E845"), ((2048, 1536), 1, "E845"),
       ((4096, 1152), 1, "E846 o7 (also overflows: U4 1153)"), ((4096, 4096), 1, "E828 j4 (also overflows)")]
FIT_CLEAN = [c for c in FIT if c[0][0] < 4096]


def interval(rule, cells=FIT_CLEAN):
    """(lo, hi): the family's thresholds thr with lo <= thr < hi, fault iff metric > thr, from completing and faulting cells."""
    lo = max(metric(rule, w, h) for (w, h), f, _ in cells if not f)
    hi = min(metric(rule, w, h) for (w, h), f, _ in cells if f)
    return lo, hi


def fault(rule, w, h, mw=None, mh=None):
    mw, mh = mw or w, mh or h
    t, m = lay(w, h), lay(mw, mh)
    if rule.startswith("TPC-"):
        _, v, lim = rule.split("-")
        return extent(t, v) > m[lim]
    if rule == "K-W":
        return w > 1024
    if rule == "K-H":
        return h > 768
    if rule == "K-OR":
        return w > 1024 or h > 768
    if rule == "K-AND":
        return w > 1024 and h > 768
    lo, hi = interval(rule)
    x = metric(rule, w, h)
    if x <= lo:
        return False
    if x >= hi:
        return True
    return None


def pred_word(rule, w, h, mw=None, mh=None):
    f = fault(rule, w, h, mw, mh)
    if f is None:
        lo, hi = interval(rule)
        return "either (no threshold: %s %d inside (%d, %d))" % (rule, metric(rule, w, h), lo, hi)
    return "fault" if f else "complete"


def survivors(observed, rules=RULES):
    """observed: [(w, h, mw, mh, 'complete' | 'fault')] of the rows that decided.  The rules no row contradicts; a threshold family
    survives while some threshold fits the fit cells and every observed row (lo < hi)."""
    out = []
    for r in rules:
        if r in KTHR:
            lo, hi = interval(r)
            for w, h, mw, mh, oc in observed:
                x = metric(r, w, h)
                if oc == "complete":
                    lo = max(lo, x)
                else:
                    hi = min(hi, x)
            if lo < hi:
                out.append(r)
            continue
        if all(fault(r, w, h, mw, mh) == (oc == "fault") for w, h, mw, mh, oc in observed):
            out.append(r)
    return out


def fit_table():
    """The fit as onset_fit.py printed it: per cell and rule, agree or not (threshold rules agree by construction)."""
    rows = []
    for (w, h), f, rec in FIT:
        rows.append((w, h, f, rec, {r: (fault(r, w, h) is None or fault(r, w, h) == bool(f)) for r in RULES}))
    return rows
