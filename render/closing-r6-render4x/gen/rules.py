#!/usr/bin/env python3
"""rules.py: the candidate rules of Q292's 4x fault, computed from a row's argv (target W x H and the context's maximum MW x MH),
standard library only.  Copied from r5-render4x (closing5/r5-render4x/gen/rules.py: the eleven rules, unchanged and dead after E868,
kept to print their predictions as the comparison) with round 6's H-TPM added (closing6/render4x/exp-render4x-r6.md 1.1 to 1.3,
morton.py and cells.py, E870):

  H-TPM [post hoc, E870]: the tail pointers of a 4x job are one dword a tile of the DOUBLED grid (16 x 8 pixel tiles) at TA-data offset
  4 x Z(x, y), Z the bit interleave with y on the even bits and x on the odd bits; a four-array 4x job faults iff the end of the
  target's entries, 4 x (Z(2tx - 1, 2ty - 1) + 1), is greater than the td.rgn of the context's maximum.  When it faults, the region
  headers of in-target tiles whose word-1 dword is an in-target tile's entry lose their stream offset (lost()).
  Its eight variants (TPM-<interleave>-<limit>: y or x on the even bits; the limit at the end of the tail room, the OTPM page, the
  state page or td.rgn) are kept for the verdict, which names the variants no decided row contradicts; H-TPM = TPM-y-rgn.

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
RULES = HTPC + KFIX + KTHR                 # round 5's eleven (dead after E868): their predictions are printed, never a verdict
TPM = tuple("TPM-%s-%s" % (i, l) for i in ("y", "x") for l in ("tail", "otpm", "state", "rgn"))
HTPM = "TPM-y-rgn"
ALL = (HTPM,) + tuple(v for v in TPM if v != HTPM) + RULES


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


def spread(v):
    r = 0
    for b in range(12):
        r |= ((v >> b) & 1) << (2 * b)
    return r


def z(x, y, yeven=True):
    """The Z-order index of tile (x, y): y on the even bits (H-TPM) or x on the even bits."""
    return (spread(y) | spread(x) << 1) if yeven else (spread(x) | spread(y) << 1)


def entries_end(w, h, yeven=True):
    """The end in bytes of the target's tail-pointer entries on the doubled grid: 4 x (Z(2tx - 1, 2ty - 1) + 1) (Z is monotone in each
    coordinate, so the far corner is the largest index)."""
    t = lay(w, h)
    return 4 * (z(2 * t["tx"] - 1, 2 * t["ty"] - 1, yeven) + 1)


def limit(mw, mh, which):
    m = lay(mw, mh)
    return {"tail": m["ctl"], "otpm": m["ctl"] + 0x1000, "state": m["state"], "rgn": m["rgn"]}[which]


def tpm_fault(v, w, h, mw, mh):
    _, i, l = v.split("-")
    return entries_end(w, h, i == "y") > limit(mw, mh, l)


def lost(w, h, mw=None, mh=None, rgn=None, yeven=True):
    """H-TPM's lost stream offsets of a faulting job: the byte offsets of the region headers (word 0's address) of in-target tiles of
    the doubled grid whose word-1 dword is the entry 4 x Z(x, y) of an in-target tile (cells.py lost(), E870 part 1).  Headers in the
    doubled-grid order of rlib.headers (column-major macrotiles, 4 x 4 blocks), from the td.rgn of the maximum."""
    mw, mh = mw or w, mh or h
    t = lay(w, h)
    base = rgn if rgn is not None else lay(mw, mh)["rgn"]
    X, Y = 2 * t["tx"], 2 * t["ty"]
    ent = {4 * z(x, y, yeven) for x in range(X) for y in range(Y)}
    n, i, out = t["n"], 0, []
    for col in range(n):
        for row in range(n):
            for by in range(2 * t["my"] // 4):
                for bx in range(2 * t["mx"] // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * t["mx"] + bx * 4 + xx, row * 2 * t["my"] + by * 4 + yy
                            if x < X and y < Y and (base + 12 * i + 4) in ent:
                                out.append(base + 12 * i)
                            i += 1
    return out


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
    if rule.startswith("TPM-"):
        return tpm_fault(rule, w, h, mw, mh)
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


def survivors(observed, rules=ALL):
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


# the 26 four-array 4x outcomes on record (closing6/render4x/morton.py CELLS, E870's check table): (w, h, mw, mh, fault, record).
# Every one was known when H-TPM was written: an offline check, not a held-out one (E870).
RECORDED = [
    (64, 64, 64, 64, 0, "E824 c2"), (288, 144, 288, 144, 0, "E824 h1, E828 j1r"), (256, 288, 256, 288, 0, "E824 h2"),
    (384, 384, 384, 384, 0, "E824 h3"), (320, 160, 320, 160, 0, "E824 h4"), (512, 384, 512, 384, 0, "E824 h5"),
    (640, 480, 640, 480, 0, "E824 h6"), (320, 400, 320, 400, 0, "E824 h7"), (1024, 768, 1024, 768, 0, "E824 h8"),
    (1280, 1024, 1280, 1024, 1, "E845, E869 d"), (2048, 1536, 2048, 1536, 1, "E845"),
    (1024, 768, 2048, 2048, 0, "E867 m0"), (1280, 1024, 1280, 1040, 0, "E867 m1"), (1280, 1024, 2048, 2048, 0, "E867 m2"),
    (1280, 1024, 2048, 1024, 1, "E867 m3"), (2048, 1536, 4096, 4096, 0, "E867 m4"), (2048, 240, 2048, 240, 1, "E868 l1"),
    (256, 1536, 256, 1536, 0, "E868 l2"), (768, 2048, 768, 2048, 1, "E868 l3"), (1280, 768, 1280, 768, 1, "E868 l4"),
    (1024, 1024, 1024, 1024, 1, "E868 l5"), (1024, 512, 1024, 512, 0, "E868 x1"), (1184, 768, 1184, 768, 1, "E868 x2"),
    (1024, 800, 1024, 800, 1, "E868 x3"),
    (4096, 1152, 4096, 1152, 1, "E846 o7 (also overflows)"), (4096, 4096, 4096, 4096, 1, "E828 j4 (also overflows)")]


def recorded_misses(rule):
    """The recorded cells a rule gets wrong (threshold rules: the cells their fit interval leaves open count as misses)."""
    return [rec for w, h, mw, mh, f, rec in RECORDED if fault(rule, w, h, mw, mh) != bool(f)]
