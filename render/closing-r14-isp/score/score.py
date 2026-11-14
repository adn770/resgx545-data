#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r14-isp's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(headline), the kept files are read through kit/kitscore.py (byte copies of resgx545 dddadbd,
pinned in FROZEN.commits); the frozen predictions are predictions/ (gen/make.py), read through
gen/guard.py (bitmaps and diff files) and gen/wind.py (the depth models). Standard library only.

  score.py STAGE KEPT_DIR        CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...   exit 0 (no stage is gated by another's controls)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Row states: held (True), FAILED (False), cannot tell (None). A job whose kept class is not ok, or
an output without its whole image or dump, is cannot tell, never a pass.

wind (Q241): a cull row holds a model when its drawn count, target hash and depth dump (sha256)
are the model's (H-CULL: E977's ramp; H-KILL: E998's no-pixel); a z row holds a model when every
target pixel's drawn state (the `row N:` image, the triangle 0xff00ff00) and every tile dword of
the dump are the model's (wind.zcheck: the exact word, or a float within 2^-20 of the plane). The
controls: their frozen drawn, hash and dump. H-CULL's headline is gated by wind-ctl-rev and
wind-ctl-b15, the z models' by wind-ctl-always and wind-ctl-rev.
g14, clipr (Q261, Q199): the target image (`row N:`, the triangle 0xff00ff00); a model holds on a
row when every pixel it determines ('0' or '1', not '?') agrees. Per row the side's bound family
(the values whose image agrees: READING lines, intersected per target shape and side). Controls:
the kept image of the record they replicate, pixel for pixel. Every stage's controls gate every
row of the stage. The tie and inside-guard rows also print the decisive reading: per rule, the
pixels where the rules' images part, agreed or not."""
import hashlib
import os
import re
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
DUMP = ".depth.1.bin"
REQUIRED = {"wind": (".txt", DUMP) + FIXED, "g14": (".txt",) + FIXED, "clipr": (".txt",) + FIXED}
GATES = {}
GREEN = 0xFF00FF00
ROW = re.compile(r"(?:^|: )row (\d+): ([0-9a-fA-Fx ]+)$", re.M)


def producible(row):
    a = row["args"].split()
    if a[:1] != ["tri"]:
        return set()
    keys = {"job", "hash", "diff", "drawn"}
    if "--pixels" in a:
        keys.add("pixels")
    if "--depth" in a:
        keys.add("depth_changed")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def done(cases, n):
    return n in cases and K.completed(cases[n]) is True


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        if DUMP in REQUIRED[stage]:
            K._read(os.path.join(d, n + DUMP))


def frozen(stage, name, want):
    body = open(os.path.join(KP, "predictions", stage, name)).read()
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


def first(text, pattern):
    m = re.search(pattern, text or "", re.M)
    return m.group(1) if m else None


def opt(args, name, default=None):
    a = args.split()
    return a[a.index(name) + 1] if name in a else default


# ================================================================================ wind
def score_wind(d):
    import wind as WD
    P, cases, lines = K.predictions(KP, "wind"), K.rows(d, "cases.tsv"), []
    ctl, per = {}, {}
    for r in K.table(KP, "wind"):
        n = r["name"]
        ok = done(cases, n)
        text = K.text(d, n + ".txt") if ok else None
        dump = K._read(os.path.join(d, n + DUMP)) if ok else None
        if dump is not None and len(dump) % 4:
            dump = None
        drawn = first(text, r"^tri \d+x\d+ #1: (\d+) triangle")
        hsh = first(text, r"^target: \d+x\d+ hash (0x[0-9a-f]+)")
        sha = None if dump is None else "sha256:" + hashlib.sha256(dump).hexdigest()
        px = pixels(text, WD.W * WD.H) if ok else None
        img = None if px is None else [v == GREEN for v in px]
        words = None if dump is None else list(struct.unpack("<%dI" % (len(dump) // 4), dump))
        pr = P.get(n, {})
        res = {}
        for m in pr.get("drawn", {}):
            want = (str(pr["drawn"][m]), pr["hash"][m], pr["depth.1.bin"][m])
            res[m] = None if drawn is None or hsh is None or sha is None else (drawn, hsh, sha) == want
        for m, h in pr.get("zmodel", {}).items():
            zm = WD.zparse(frozen("wind", "%s.%s.txt" % (n, m), h))
            res[m] = None if not ok or len(words or ()) <= max(zm["dwords"]) else WD.zcheck(zm, words, img)
        rd = "drawn %s, hash %s, dump %s" % (drawn, hsh, "-" if sha is None else sha[7:19])
        if words is not None:
            vals = {}
            for x in range(WD.TW):
                for y in range(WD.TH):
                    if WD.inside(x, y):
                        z = WD.plane(WD.fwd_depths(next(t for t in WD.ROWS if t[0] == n)), x, y)
                        if not 0 <= z <= 1:
                            w = words[WD.store_dword(x, y)]
                            vals[w] = vals.get(w, 0) + 1
            if vals:
                top = sorted(vals.items(), key=lambda kv: -kv[1])[:4]
                rd += "; out-of-range dwords: %d, %d distinct, %s" % (
                    sum(vals.values()), len(vals), ", ".join("0x%08x x %d" % kv for kv in top))
        if r["set"] == "control":
            st = None if any(v is None for v in res.values()) else all(res.values())
            ctl[n] = st
            lines.append("CONTROL %s: %s; %s: %s" % (n, rd, "; ".join("%s %s" % (m, word(s)) for m, s in res.items()),
                                                    cword(st)))
            continue
        for m, s in res.items():
            per.setdefault(m, []).append(s)
        lines.append("ROW %s: %s; %s" % (n, rd, "; ".join("%s %s" % (m, word(s)) for m, s in res.items())))
    cull_ctl = {k: v for k, v in ctl.items() if k in ("wind-ctl-rev", "wind-ctl-b15")}
    z_ctl = {k: v for k, v in ctl.items() if k in ("wind-ctl-always", "wind-ctl-rev")}
    claims = {"H-CULL": "ISP word 0 bits 15, 16, 17 each remove one winding: the reversed triangle draws E977's ramp",
              "H-KILL": "each bit removes any triangle (no pixel, the background depth)",
              "H-CLAMP": "a depth outside [0, 1] is stored clamped to it and drawn",
              "H-ZCLIP": "pixels past [0, 1] are removed",
              "H-RAW": "the plane's depth is stored as it is and drawn",
              "H-ABS": "the plane's depth is stored with its sign cleared and drawn"}
    for m, rows in per.items():
        c = cull_ctl if m in ("H-CULL", "H-KILL") else z_ctl
        lines.append("SUMMARY: wind: %s: %s" % (m, SK.headline(claims[m], c, rows)))
    return lines


# ================================================================================ g14, clipr
def shape(r):
    return "%sx%s" % (opt(r["args"], "--width"), opt(r["args"], "--height")) + (
        " vp" if "--poke" in r["args"] else "")


def score_clip(stage, d):
    import guard as G
    P, cases, lines = K.predictions(KP, stage), K.rows(d, "cases.tsv"), []
    ctl, per, fams = {}, {}, {}
    for r in K.table(KP, stage):
        n = r["name"]
        W, H = int(opt(r["args"], "--width")), int(opt(r["args"], "--height"))
        px = pixels(K.text(d, n + ".txt"), W * H) if done(cases, n) else None
        got = None if px is None else [v == GREEN for v in px]
        pr = P[n]
        (lab0, h0), = pr["ref"].items()
        ref = G.bits(frozen(stage, n + ".ref.txt", h0))
        (labs, hm), = pr["models"].items()
        models = G.diff_parse(frozen(stage, n + ".models.txt", hm), ref, W)
        res = {m: G.agree(got, img) for m, img in models.items()}
        desc = "; ".join("%s %s" % (m, word(s)) for m, s in res.items())
        ftxt = ""
        if "family" in pr:
            (side, hf), = pr["family"].items()
            fam = G.diff_parse(frozen(stage, n + ".family.txt", hf), ref, W)
            fits = None if got is None else sorted((int(v) for v, img in fam.items() if G.agree(got, img)))
            ftxt = "; %s fits %s" % (side, "cannot tell" if fits is None else
                                     (ranges(fits) if fits else "none"))
            if fits is not None and r["set"] != "control":
                fams.setdefault((shape(r), side), []).append(set(fits))
        if r["set"] == "control":
            kb = G.bits(frozen(stage, n + ".KEPT.txt", pr["pixels"]["KEPT"]))
            st = G.agree(got, kb)
            ctl[n] = st
            lines.append("CONTROL %s (%dx%d): kept image %s; %s%s: %s" % (n, W, H, word(st), desc, ftxt, cword(st)))
            continue
        for m, s in res.items():
            per.setdefault(m, []).append(s)
        dec = ""
        if any(m.startswith(("CLIP-", "IN-")) for m in models) and got is not None:
            rules = [m for m in models if m.startswith(("CLIP-", "IN-"))]
            idx = [i for i in range(W * H) if len({models[m][i] for m in rules}) > 1]
            dec = "; decisive pixels %d: %s" % (len(idx), ", ".join(
                "%s %d" % (m, sum(models[m][i] == got[i] for i in idx)) for m in rules))
        lines.append("ROW %s (%s, %dx%d%s): %s%s%s" % (n, r["set"], W, H, ", vp" if "--poke" in r["args"] else "",
                                                      desc, ftxt, dec))
    claims = {"H-VP": "the guard is a quarter of the viewport past each edge (clip x, y within 1.5 w)",
              "H-TGT": "the guard is a quarter of the target past each edge",
              "H-MAX4": "the guard is a quarter of max(W, H) past each edge",
              "H-MIN4": "the guard is a quarter of min(W, H) past each edge",
              "H-ABS": "the guard is fixed in pixels (x >= -16, y in [-16, 80])",
              "H-EXACT": "no clip: the exact triangle",
              "H-SAT": "the far vertex saturates a 24.8 word", "H-WRAP": "the far vertex wraps a 24.8 word",
              "H-CULL": "the triangle is removed",
              "CLIP-HU": "H-HALFUP-CLIP: a clip-made vertex is rounded half up (floor(256 x + 1/2))",
              "CLIP-HA": "H-HAZ-CLIP: half away from zero", "CLIP-RNE": "H-RNE-CLIP: half to even",
              "CLIP-TR": "H-TRUNC-CLIP: toward zero",
              "IN-E607": "a vertex inside the guard rounds as E607 (half up) and E943 (below 0 away from zero)",
              "IN-HU": "a vertex inside the guard rounds half up at both signs",
              "IN-RNE": "a vertex inside the guard rounds half to even",
              "IN-TR": "a vertex inside the guard rounds toward zero"}
    for m, rows in per.items():
        lines.append("SUMMARY: %s: %s: %s" % (stage, m, SK.headline("%s: %s" % (m, claims.get(m, m)), ctl, rows)))
    for (sh, side), sets in sorted(fams.items()):
        s = set.intersection(*sets)
        lines.append("READING %s family %s %s: %s over %d rows" % (stage, sh, side, ranges(sorted(s)) if s else "none",
                                                                   len(sets)))
    return lines


def ranges(vals):
    out, i = [], 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[j] + 1:
            j += 1
        out.append(str(vals[i]) if i == j else "%d..%d" % (vals[i], vals[j]))
        i = j + 1
    return "[%s]" % ", ".join(out)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        out = score_wind(argv[2]) if argv[1] == "wind" else score_clip(argv[1], argv[2])
        print("\n".join(out))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
