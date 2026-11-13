#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r13-isp's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(headline, tally), the kept files are read through kit/kitscore.py (byte copies of resgx545
05b7039ee021, pinned in FROZEN.commits); the frozen predictions are predictions/ (gen/make.py),
the readers gen/clip.py (family files) and gen/pivot.py (r10-geo's, a byte copy: pixel intervals).
Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage is gated by another's controls)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Row states: held (True), FAILED (False), cannot tell (None). A job whose kept class is not ok, or
an output without its whole image, is cannot tell, never a pass. Every stage's controls gate
every row of the stage (scorekit.headline).

q201 (Q201): the 64 x 64 probe image (`row N:` lines). Drawn: a value other than the target's
fill 0xff203040. Coverage: the drawn set against E1018's (the frozen bitmap). Value: for every
drawn pixel the offset s of its component, value = pixel + s (src0) or (pixel + s) / 32 - 1
(cset, the clip coordinate on 64 x 64), exact from the float32; a model holds on a row when every
drawn pixel's s lies within 1/64 pixel of the model's frozen offset (the 1/16 grid's points are
4 tolerances apart). A control passes when its coverage and its offset (H-SAMPLE0's) hold.
q261, far (Q261, Q199): the target image (`row N:`, the triangle 0xff00ff00). A pixel model holds
when every determined pixel ('0' or '1', not '?') agrees. The clip family (H-CLIP): per row the
set of parameter values whose image agrees; the row holds when that set is not empty; per family
(G the high x guard, a the low x guard, g the y guard, h an absolute guard) the values that every
row of the stage agrees with (READING lines). H-CLIP-ONE: one value of each family fits every row
that tests it (FAILED when a row fits none or a family's set is empty). On 128 x 128 rows,
H-REL (x <= 128 + G, the G of the 64 x 64 rows) against H-ABS (x <= h, h = 64 + G). H-PIVOT
(q261, 64 x 64 rows along x): the set of D (the far vertex's y displacement) whose exact
coverage is the image, from the frozen pixel intervals (r10-geo's d_set). Controls: the kept
image of the record they replicate, pixel for pixel."""
import os
import re
import struct
import sys
from fractions import Fraction

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"q201": (".txt",) + FIXED, "q261": (".txt",) + FIXED, "far": (".txt",) + FIXED}
GATES = {}
GREEN, BG = 0xFF00FF00, 0xFF203040
TOL = Fraction(1, 64)
ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
Q201_MODELS = ("H-SAMPLE0", "H-CENTRE", "H-SWAP", "H-SPLIT")


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"]:
        return {"pixels"} if "--pixels" in a else set()
    if a[:1] != ["tri"]:
        return set()
    keys = {"job", "hash", "diff"}
    if "--pixels" in a:
        keys.add("pixels")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def done(cases, n):
    return n in cases and K.completed(cases[n])


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def frozen(stage, name, want):
    body = open(os.path.join(KP, "predictions", stage, name)).read()
    import hashlib
    if "sha256:" + hashlib.sha256(body.encode()).hexdigest() != want:
        raise SystemExit("score.py: %s/%s is not the frozen file" % (stage, name))
    return body


def pixels(text, n):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == n else None


def opt(args, name, default=None):
    a = args.split()
    return a[a.index(name) + 1] if name in a else default


def bits(body):
    return [None if c == "?" else c == "1" for c in "".join(body.split())]


# ================================================================================ q201
def as_float(v):
    f = struct.unpack("<f", struct.pack("<I", v))[0]
    return None if f != f or f in (float("inf"), float("-inf")) else Fraction(f)


def offsets(px, w, prog, comp):
    """{pixel index: s} for every drawn pixel (None where the value is not a finite float)"""
    out = {}
    for i, v in enumerate(px):
        if v == BG:
            continue
        f = as_float(v)
        c = i % w if comp == "x" else i // w
        if f is None:
            out[i] = None
        elif prog == "cset":
            out[i] = (f + 1) * w / 2 - c
        else:
            out[i] = f - c
    return out


def held_at(offs, o):
    if not offs:
        return None
    return all(s is not None and abs(s - o) <= TOL for s in offs.values())


def reading(offs):
    vals = sorted(s for s in offs.values() if s is not None)
    if not vals:
        return "no drawn pixel"
    med = vals[len(vals) // 2]
    near = Fraction(round(med * 16), 16)
    spread = max(abs(s - med) for s in vals)
    return "s = %s (nearest 1/16: %d/16), spread %.2e px over %d pixels%s" % (
        "%.6f" % float(med), near * 16, float(spread), len(vals),
        "" if len(vals) == len(offs) else ", %d not finite" % (len(offs) - len(vals)))


def row_kind(args):
    prog = "cset" if "cset.bin" in args else "src0"
    comp = "x" if "pix_pa0.bin" in args else "y"
    return prog, comp


def score_q201(d):
    P, cases, lines = K.predictions(KP, "q201"), K.rows(d, "cases.tsv"), []
    ctl, per, cov_rows = {}, {m: [] for m in Q201_MODELS}, []
    for r in K.table(KP, "q201"):
        n = r["name"]
        prog, comp = row_kind(r["args"])
        px = pixels(K.text(d, n + ".txt"), 4096) if done(cases, n) else None
        cov = bits(frozen("q201", n + ".coverage.txt", P[n]["coverage"]["E1018"]))
        want = {m: Fraction(v) for m, v in P[n]["offset"].items()}
        if px is None:
            cst, offs = None, {}
        else:
            cst = [v != BG for v in px] == cov
            offs = offsets(px, 64, prog, comp)
        res = {m: (None if px is None else held_at(offs, o)) for m, o in want.items()}
        rd = "no image" if px is None else reading(offs)
        if r["set"] == "control":
            st = None if px is None or res["H-SAMPLE0"] is None else (cst and res["H-SAMPLE0"])
            ctl[n] = st
            lines.append("CONTROL %s (%s %s): coverage %s, offset frozen %s, read %s: %s" % (
                n, prog, comp, word(cst), want["H-SAMPLE0"], rd, cword(st)))
            continue
        cov_rows.append(cst)
        for m in Q201_MODELS:
            per[m].append(res[m])
        lines.append("ROW %s (%s %s %s): coverage %s; %s; read %s" % (
            n, r["set"], prog, comp, word(cst),
            "; ".join("%s %s %s" % (m, want[m], word(res[m])) for m in Q201_MODELS), rd))
    claims = {"H-SAMPLE0": "an iterated coordinate set and the position source both read at byte 0's point "
                           "(x + lo/16, y + hi/16)",
              "H-CENTRE": "both read at the pixel centre whatever byte 0",
              "H-SWAP": "both read at (x + hi/16, y + lo/16)",
              "H-SPLIT": "the position source moves with byte 0, the coordinate set stays at the centre"}
    for m in Q201_MODELS:
        lines.append("SUMMARY: q201: %s: %s" % (m, SK.headline(claims[m], ctl, per[m])))
    lines.append("SUMMARY: q201: E1018: %s" % SK.headline(
        "the drawn set is E1018's coverage at byte 0's point", ctl, cov_rows))
    return lines


# ================================================================================ q261, far
def d_set(drawn, exact, iv, w=64):
    """r10-geo score.py's d_set: the open intervals of D for which the image is the coverage at
    s = D ([(lo, hi)], [] when none)"""
    for i in range(w * w):
        if (i % w, i // w) not in iv and drawn[i] != exact[i]:
            return []
    pts = sorted({v for lo, hi in iv.values() for v in (lo, hi) if v is not None})
    cands = []
    if not pts:
        cands = [(None, None, Fraction(0))]
    else:
        cands.append((None, pts[0], pts[0] - 1))
        for a, b in zip(pts, pts[1:]):
            cands.append((a, b, (a + b) / 2))
        cands.append((pts[-1], None, pts[-1] + 1))
    ok = []
    for lo, hi, mid in cands:
        if all(drawn[y * w + x] == ((a is None or a < mid) and (b is None or mid < b))
               for (x, y), (a, b) in iv.items()):
            if ok and ok[-1][1] == lo and lo is not None:
                ok[-1] = (ok[-1][0], hi)
            else:
                ok.append((lo, hi))
    return ok


def ival_text(s):
    if not s:
        return "none"
    f = lambda v, e: e if v is None else "%.3f" % float(v)  # noqa: E731
    return " u ".join("(%s, %s)" % (f(lo, "-inf"), f(hi, "+inf")) for lo, hi in s)


def agree(got, want):
    if got is None:
        return None
    return all(w is None or g == w for g, w in zip(got, want))


def fam_key(label):
    return label.split("=")[0]


def score_clip(stage, d, roots=()):
    import clip as C
    import pivot as PIV
    P, cases, lines = K.predictions(KP, stage), K.rows(d, "cases.tsv"), []
    ctl, per = {}, {}
    fams = {}          # family -> list of sets of values (one per held-out row testing it)
    clip_rows, fit_none = [], []
    rel_abs = {"H-REL": [], "H-ABS": []}
    g64 = []
    for r in K.table(KP, stage):
        n = r["name"]
        w = int(opt(r["args"], "--width"))
        px = pixels(K.text(d, n + ".txt"), w * w) if done(cases, n) else None
        got = None if px is None else [v == GREEN for v in px]
        pr = P.get(n, {})
        exact = bits(frozen(stage, n + ".H-EXACT.txt", pr["pixels"]["H-EXACT"]))
        res = {}
        for m, sha in pr.get("pixels", {}).items():
            res[m] = agree(got, bits(frozen(stage, "%s.%s.txt" % (n, m), sha)))
        fam = C.family_parse(frozen(stage, n + ".clip.txt", pr["family"]["H-CLIP"]), exact, w)
        fits = None if got is None else sorted((lab for lab, img in fam.items() if agree(got, img)),
                                               key=lambda s: (fam_key(s), int(s.split("=")[1])))
        desc = "; ".join("%s %s" % (m, word(s)) for m, s in res.items())
        ftxt = "cannot tell" if fits is None else (", ".join(fits) or "none")
        if r["set"] == "control":
            st = res.get("KEPT")
            ctl[n] = st
            lines.append("CONTROL %s: kept image %s; H-CLIP fits %s: %s" % (n, word(st), ftxt, cword(st)))
            continue
        for m, s in res.items():
            if m != "KEPT":
                per.setdefault(m, []).append(s)
        clip_rows.append(None if fits is None else bool(fits))
        if fits is not None:
            by = {}
            for lab in fam:
                by.setdefault(fam_key(lab), set())
            for lab in fits:
                by[fam_key(lab)].add(int(lab.split("=")[1]))
            if w == 128:
                rel = by.get("G", set())
                ab = {h - 64 for h in by.get("h", set())}
                fams.setdefault("G128", []).append(rel)
                fams.setdefault("h128", []).append(ab)
            else:
                for k, v in by.items():
                    fams.setdefault(k, []).append(v)
                if "G" in by:
                    g64.append(by["G"])
            if not fits:
                fit_none.append(n)
        extra = ""
        if "ivals" in pr:
            ivt = frozen(stage, n + ".ivals.txt", pr["ivals"]["H-PIVOT"])
            if got is None:
                per.setdefault("H-PIVOT", []).append(None)
                extra = "; H-PIVOT cannot tell"
            else:
                ds = d_set(got, [bool(v) for v in exact], PIV.ivals_parse(ivt))
                per.setdefault("H-PIVOT", []).append(bool(ds))
                extra = "; H-PIVOT D in %s" % ival_text(ds)
        lines.append("ROW %s (%s, %dx%d): %s; H-CLIP fits %s%s" % (n, r["set"], w, w, desc, ftxt, extra))
    for m, rows in per.items():
        lines.append("SUMMARY: %s: %s: %s" % (stage, m, SK.headline(m + " draws every determined pixel", ctl, rows)))
    lines.append("SUMMARY: %s: H-CLIP: %s" % (stage, SK.headline(
        "every held-out row is the image of E1012's clip at some value of its family", ctl, clip_rows)))
    inter = {}
    for k, sets in sorted(fams.items()):
        s = set.intersection(*sets) if sets else set()
        inter[k] = s
        lines.append("READING %s family %s: %s over %d rows" % (stage, k, sorted(s) if s else "none", len(sets)))
    g_all = set.intersection(*(g64 + fams.get("G128", []))) if g64 or fams.get("G128") else None
    if "G128" in fams:
        rel = g_all if g_all is not None else set()
        ab = set.intersection(*(g64 + fams["h128"])) if g64 or fams["h128"] else set()
        lines.append("READING %s H-REL (x <= W + G): G in %s; H-ABS (x <= 64 + G whatever W): G in %s" % (
            stage, sorted(rel) or "none", sorted(ab) or "none"))
        rel_abs["H-REL"].append(bool(rel))
        rel_abs["H-ABS"].append(bool(ab))
        for m in ("H-REL", "H-ABS"):
            lines.append("SUMMARY: %s: %s: %s" % (stage, m, SK.headline(
                m + ": one G fits every +x row of both targets", ctl, rel_abs[m])))
    one = None if any(s is None for s in clip_rows) or not clip_rows else \
        (not fit_none and all(inter[k] for k in inter if k != "h128"))
    lines.append("SUMMARY: %s: H-CLIP-ONE: %s" % (stage, SK.headline(
        "one value of each guard (G, a, g) fits every held-out row", ctl, [one])))
    for root in roots:
        q = os.path.join(root, "q261")
        if stage == "far" and os.path.isdir(q):
            other = [ln for ln in score_clip("q261", q) if ln.startswith("READING q261 family ")]
            lines.append("READING far with q261: " + " | ".join(other))
            break
    return lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        if argv[1] == "q201":
            out = score_q201(argv[2])
        else:
            out = score_clip(argv[1], argv[2], argv[3:])
        print("\n".join(out))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
