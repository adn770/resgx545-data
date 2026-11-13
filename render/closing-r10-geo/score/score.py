#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-geo's scorer, frozen before the run. Every verdict rule comes from
kit/scorekit.py (headline, tally), the kept files are read through kit/kitscore.py (byte copies
of resgx545 9849dab7540c, pinned in FROZEN.commits); the frozen predictions are predictions/
(gen/make.py), the readers gen/pivot.py, gen/bgw.py with gen/bgl_model.py (r9-k1's, a byte copy),
gen/q139even.py (r9-lgeo's) and score/lib_dump.py (r9-lgeo's, with its byte copies). Standard
library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage is gated by another's controls)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Row states: held (True), FAILED (False), cannot tell (None). A job whose kept class is not ok
(rc 0, or rc 1 with `job: ok` and its diff line: expectdiff), an output without its whole image
or dump, is cannot tell, never a pass. Every stage's controls gate every row of the stage.

pivot (Q261): the 64 x 64 image (`row N:` lines, the triangle 0xff00ff00). The control passes iff
every pixel outside E684's band is exact. Per row: H-EXACT (all 4096 pixels), H-EXACT-BAND (the
pixels outside the band), and the set of D (the far vertex's y displacement, pixels) for which
the image is the coverage at s = D (the row's frozen pixel intervals; every other pixel its
H-EXACT state), a union of open intervals. Per triangle H-PIVOT holds iff the intersection over
its 12 rows is not empty (FAILED when it is; cannot tell when a row is missing and what was read
is not empty); READING lines give the interval. H-CONSTD (one D for the three triangles) and
H-ANGLE (D = theta |F|, one theta) are single claims on the three intervals.
bgw (Q066): the 3034 background pixels' texels (bgl_model.score_tex: right at <= 1 % of the
predicted pixels wrong, wrong above 10 %, between cannot tell), each model's prediction
recomputed from gen/bgw.py and checked against its frozen id; a poke that does not read back in
the kept render_param dump makes the row cannot tell. Controls: H-INERT (identity) right.
q139c (Q139): as r9-lgeo's q139b: the controls pass iff the image is exact and every target
tile has one header with a stream (lib_dump.baseline_layout, the header base of their size);
each poked row's wrong tiles (lib_dump.image_tiles) and every header slot (observed_slots from
that base) against each model's frozen set and slots; H-LAST on the row's own dump: exactly one
header with flag bit 7, and a target tile drawn iff a header with a stream naming it lies at or
before that slot (every tile); H-FLAGSLOT: that slot is the frozen one."""
import math
import os
import re
import sys
from fractions import Fraction

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"pivot": (".txt",) + FIXED, "bgw": (".txt", ".tri.param.bin") + FIXED,
            "q139c": (".txt", ".tri.param.bin", ".tri.tadata.bin") + FIXED}
GATES = {}
TRI_COLOUR = 0xFF00FF00
ROW = re.compile(r"^row (\d+): ([0-9a-fA-Fx ]+)$", re.M)


def producible(row):
    a = row["args"].split()
    if a[:1] != ["tri"]:
        return set()
    keys = {"job", "hash", "diff"}
    if "--pixels" in a:
        keys.add("pixels")
    if "--dump-render" in a:
        keys.add("dump")
    if "--bg-layer" in a:
        keys |= {"inplace", "layer"}
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
        if stage in ("bgw", "q139c"):
            K._read(os.path.join(d, n + ".tri.param.bin"))
        if stage == "q139c":
            K._read(os.path.join(d, n + ".tri.tadata.bin"))


def frozen_file(stage, name):
    return open(os.path.join(KP, "predictions", stage, name)).read()


def sha(text):
    import hashlib
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


# ================================================================================ pivot
def pixels(text, n=4096):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == n else None


def d_set(drawn, exact, iv):
    """The union of open intervals of D (Fractions, None = unbounded) for which the image is
    the coverage at s = D: [(lo, hi)], [] when none."""
    for i in range(4096):
        if (i % 64, i // 64) not in iv and drawn[i] != exact[i]:
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
        if all(drawn[y * 64 + x] == ((a is None or a < mid) and (b is None or mid < b))
               for (x, y), (a, b) in iv.items()):
            if ok and ok[-1][1] == lo and lo is not None:
                ok[-1] = (ok[-1][0], hi)           # joined across a breakpoint (a tie point)
            else:
                ok.append((lo, hi))
    return ok


def intersect(a, b):
    out = []
    for lo1, hi1 in a:
        for lo2, hi2 in b:
            lo = lo1 if lo2 is None else lo2 if lo1 is None else max(lo1, lo2)
            hi = hi1 if hi2 is None else hi2 if hi1 is None else min(hi1, hi2)
            if lo is None or hi is None or lo < hi:
                out.append((lo, hi))
    return out


def ival_text(s):
    if not s:
        return "none"
    f = lambda v, e: e if v is None else "%.3f" % float(v)  # noqa: E731
    return " u ".join("(%s, %s)" % (f(lo, "-inf"), f(hi, "+inf")) for lo, hi in s)


def score_pivot(d):
    import pivot as PIV
    P, cases, lines = K.predictions(KP, "pivot"), K.rows(d, "cases.tsv"), []
    ctl, per = {}, {"H-EXACT": [], "H-EXACT-BAND": []}
    tri_sets = {t: [] for t in PIV.TRIS}
    tri_missing = {t: 0 for t in PIV.TRIS}
    for r in K.table(KP, "pivot"):
        n = r["name"]
        px = pixels(K.text(d, n + ".txt")) if done(cases, n) else None
        got = None if px is None else [v == TRI_COLOUR for v in px]
        res = {}
        for m, frozen in P.get(n, {}).get("pixels", {}).items():
            body = frozen_file("pivot", "%s.%s.txt" % (n, m))
            if sha(body) != frozen:
                raise SystemExit("score.py: %s %s: the prediction file is not the frozen one" % (n, m))
            want = "".join(body.split())
            if got is None:
                res[m] = (None, "no image")
                continue
            det = [i for i, c in enumerate(want) if c != "?"]
            bad = sum(("1" if got[i] else "0") != want[i] for i in det)
            res[m] = (bad == 0, "%d/%d determined pixels" % (len(det) - bad, len(det)))
        desc = "; ".join("%s %s" % (m, t) for m, (_, t) in res.items())
        if r["set"] == "control":
            st = None if any(s is None for s, _ in res.values()) else all(s for s, _ in res.values())
            ctl[n] = st
            lines.append("CONTROL %s: %s: %s" % (n, desc, cword(st)))
            continue
        for m, (s, _) in res.items():
            per[m].append(s)
        tri = "far-" + n.split("-")[1]
        iv_frozen = P[n]["ivals"]["H-PIVOT"]
        ivt = frozen_file("pivot", n + ".ivals.txt")
        if sha(ivt) != iv_frozen:
            raise SystemExit("score.py: %s: the pixel intervals are not the frozen ones" % n)
        if got is None:
            tri_missing[tri] += 1
            lines.append("ROW %s (%s): %s; D: cannot tell" % (n, r["set"], desc))
            continue
        exact = ["1" == c for c in "".join(frozen_file("pivot", n + ".H-EXACT.txt").split())]
        ds = d_set(got, exact, PIV.ivals_parse(ivt))
        tri_sets[tri].append(ds)
        flips = sum(1 for (x, y) in PIV.ivals_parse(ivt) if got[y * 64 + x] != exact[y * 64 + x])
        lines.append("ROW %s (%s): %s; %d drawn, %d interval pixels off H-EXACT; D in %s" % (
            n, r["set"], desc, sum(got), flips, ival_text(ds)))
    piv_states, inter = [], {}
    for tri in PIV.TRIS:
        sets = tri_sets[tri]
        s = [(None, None)]
        for x in sets:
            s = intersect(s, x)
        inter[tri] = s if sets else None
        if sets and not s:
            st = False
        elif tri_missing[tri] or not sets:
            st = None
        else:
            st = True
        piv_states.append(st)
        lines.append("READING %s: %d of %d rows read; D (the far vertex's y displacement, px) in %s"
                     % (tri, len(sets), len(sets) + tri_missing[tri], ival_text(s if sets else [])))
    # one D for all three, and one angle theta = D / |F|
    const = angle = None
    if all(piv_states):
        s = [(None, None)]
        for tri in PIV.TRIS:
            s = intersect(s, inter[tri])
        const = bool(s)
        lines.append("READING H-CONSTD: D in %s" % ival_text(s))
        th = [(None, None)]
        for tri in PIV.TRIS:
            vp = PIV.verts_px(tri)
            fv = vp[PIV.far_index(vp)]
            R = math.hypot(float(fv[0]), float(fv[1]))
            th = intersect(th, [(None if lo is None else Fraction(float(lo) / R),
                                 None if hi is None else Fraction(float(hi) / R))
                                for lo, hi in inter[tri]])
        angle = bool(th)
        lines.append("READING H-ANGLE: theta = D / |F| in %s" % (
            "none" if not th else " u ".join("(%s, %s)" % (
                "-inf" if lo is None else "%.3e" % float(lo), "+inf" if hi is None else "%.3e" % float(hi))
                for lo, hi in th)))
    out = lines
    out.append("SUMMARY: Q261 H-EXACT: every row is the exact coverage at its own vertices, band "
               "included: " + SK.headline("H-EXACT holds", ctl, per["H-EXACT"]))
    out.append("SUMMARY: Q261 H-EXACT-BAND (E979): every pixel outside E684's 1e-3 band exact: "
               + SK.headline("H-EXACT-BAND holds", ctl, per["H-EXACT-BAND"]))
    out.append("SUMMARY: Q261 H-PIVOT: per triangle one y displacement D of the far vertex gives "
               "all 12 rows pixel for pixel: " + SK.headline("H-PIVOT holds", ctl, piv_states))
    out.append("SUMMARY: Q261 H-CONSTD: one D gives the three triangles: "
               + SK.headline("H-CONSTD holds", ctl, [const]))
    out.append("SUMMARY: Q261 H-ANGLE: D proportional to the far vertex's distance: "
               + SK.headline("H-ANGLE holds", ctl, [angle]))
    return out


# ================================================================================ bgw
def score_bgw(d):
    import bgl_model as M
    import bgw as BGW
    P, cases, lines = K.predictions(KP, "bgw"), K.rows(d, "cases.tsv"), []
    mask = M.load_mask()
    jobs = {j[0]: j for j in BGW.jobs()}
    ctl, per, tallies = {}, {m: [] for m in BGW.MODELS}, {}
    for r in K.table(KP, "bgw"):
        n = r["name"]
        _, sset, _, _, w, v, models = jobs[n]
        for m, p in models.items():
            if M.map_id(p) != P[n]["texmap"][m]:
                raise SystemExit("score.py: %s %s: the model gives %s, the frozen prediction %s"
                                 % (n, m, M.map_id(p), P[n]["texmap"][m]))
        ok = done(cases, n)
        o = M.object_words(M.gz(os.path.join(d, n + ".tri.param.bin"))) if ok else None
        rb = None if o is None else (True if w is None else o[w] == BGW.bits(v))
        img = M.tri_rows(K.text(d, n + ".txt")) if ok else {}
        res = {}
        for m, p in models.items():
            s = M.score_tex(p, img, mask) if ok else (None, 0, 0)
            if rb is not True:
                s = (None,) + tuple(s[1:])
            res[m] = s
        desc = "; ".join("%s %s (%d of %d)" % (m, word(s), mm, sc) for m, (s, sc, mm) in res.items())
        if sset == "control":
            ctl[n] = res["H-INERT"][0]
            lines.append("CONTROL %s: object read %s; %s: %s" % (
                n, "yes" if o is not None else "NO", desc, cword(ctl[n])))
            continue
        for m, (s, _, _) in res.items():
            per[m].append(s)
            tallies.setdefault((w, m), []).append(s)
        lines.append("ROW %s: word %d = %g read back %s; %s" % (
            n, w, v, {True: "yes", False: "NO", None: "-"}[rb], desc))
    for (w, m), sts in sorted(tallies.items()):
        lines.append("TALLY word %d %s: %s" % (w, m, SK.tally(sts)))
    lines.append("SUMMARY: Q066 H-INERT: finite values in words 9 and 11 to 14 change no texel: "
                 + SK.headline("H-INERT holds", ctl, per["H-INERT"]))
    lines.append("SUMMARY: Q066 H-SCALE0: words 11, 12, 14 scale u, v, u (0 read as 1), clamped "
                 "outside [0, 1): " + SK.headline("H-SCALE0 holds", ctl, per["H-SCALE0"]))
    return lines


# ================================================================================ q139c
def q139_job(d, cases, n):
    import lib_dump as L
    if not done(cases, n):
        return None, "not a completed job" if n in cases else "did not run"
    j = dict(text=K.text(d, n + ".txt"), param=L.read_bytes(os.path.join(d, n + ".tri.param.bin")),
             tadata=L.read_bytes(os.path.join(d, n + ".tri.tadata.bin")))
    if not j["tadata"] or not j["param"]:
        return None, "no dump"
    return j, "read"


def slot_agree(pred, obs):
    return sum(1 for t, v in pred.items()
               if (v is None and not obs.get(t)) or (v is not None and v in obs.get(t, [])))


def last_flag(tadata, base, w, h, bad):
    """(flagged slots, tiles H-LAST gets right, target tiles)."""
    import lib_dump as L
    hs = L.headers(tadata, base, stop_zero=1 << 30)
    last = sorted(i for i, c, r, fl, st in hs if fl & 0x80)
    want = L.target_tiles(w, h)
    pred = {L.tile_of(c, r) for i, c, r, fl, st in hs if st and last and i <= last[-1]} & want
    got = want - bad
    return last, len(pred & got) + len((want - pred) & bad), len(want)


def score_q139c(d):
    import lib_dump as L
    import q139even as E
    P, cases, lines = K.predictions(KP, "q139c"), K.rows(d, "cases.tsv"), []
    tab = K.table(KP, "q139c")
    one = lambda n, q, m: P.get(n, {}).get(q, {}).get(m)  # noqa: E731
    size = {t["name"]: tuple(int(x) for x in one(t["name"], "size", "all").split("x")) for t in tab}

    def slots_of(n, m):
        body = frozen_file("q139c", "%s.%s.slots" % (n, m))
        if sha(body) != one(n, "slots", m):
            raise SystemExit("score.py: %s %s: the slots file is not the frozen one" % (n, m))
        return E.slots_parse(body.strip())
    ctl, lay = {}, {}
    for t in tab:
        n = t["name"]
        if t["set"] != "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        if j is None:
            ctl[n] = None
            lines.append("CONTROL %s: cannot tell (%s)" % (n, why))
            continue
        complete, bad = L.image_tiles(j["text"], w, h)
        ok, txt, ly = L.baseline_layout(j["tadata"], j["param"], w, h)
        ctl[n] = complete and not bad and ok
        if ctl[n]:
            lay[(w, h)] = ly
            fl = last_flag(j["tadata"], ly["base"], w, h, bad)
            agree = sum(1 for tl, v in slots_of(n, "H-EVEN").items() if ly["slot"].get(tl) == v)
            lines.append("READING %s: H-EVEN slots %d of %d; flag bit 7 at slots %s, H-LAST right on "
                         "%d of %d tiles" % (n, agree, w // 32 * -(-h // 16), fl[0][:4], fl[1], fl[2]))
        lines.append("CONTROL %s: image %s, %d wrong tiles; %s: %s" % (
            n, "complete" if complete else "INCOMPLETE", len(bad), txt, cword(ctl[n])))
    st = {"slots-heldout": [], "slots-replicate": [], "H-LAST": [], "H-FLAGSLOT": []}
    for t in tab:
        n, sset = t["name"], t["set"]
        if sset == "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        comp = None
        if j is not None:
            comp, bad = L.image_tiles(j["text"], w, h)
        if j is None or not comp or (w, h) not in lay:
            for k in ("slots-" + sset, "H-LAST", "H-FLAGSLOT"):
                st[k].append(None)
            lines.append("ROW %s (%s): cannot tell (%s)" % (
                n, sset, why if j is None else "image not whole" if not comp
                else "no baseline layout of %dx%d" % (w, h)))
            continue
        base = lay[(w, h)]["base"]
        obs = L.observed_slots(j["tadata"], base, w, h)
        parts, ms = [], {}
        for m in E.MODELS:
            same = L.tiles_text(bad) == one(n, "wrong", m)
            pred = slots_of(n, m)
            ag = slot_agree(pred, obs)
            ms[m] = same and ag == len(pred)
            parts.append("%s %s (wrong %s, slots %d of %d)" % (m, "yes" if ms[m] else "no",
                                                               "=" if same else "differs", ag, len(pred)))
        st["slots-" + sset].append(ms["blkrow"] and ms["H-EVEN"])
        last, right, ntiles = last_flag(j["tadata"], base, w, h, bad)
        hl = len(last) == 1 and right == ntiles
        st["H-LAST"].append(hl)
        fs = len(last) == 1 and str(last[0]) == one(n, "flagslot", "H-FLAGSLOT") and \
            L.tiles_text(bad) == one(n, "wrong", "H-FLAGSLOT")
        st["H-FLAGSLOT"].append(fs)
        rep = "replicated" if L.tiles_text(bad) == one(n, "wrong", "kept") else \
            "NOT replicated (%d kept)" % len(L.tiles_parse(one(n, "wrong", "kept")))
        lines.append("ROW %s (%s): %d wrong tiles; the dataset's image %s; %s" % (
            n, sset, len(bad), rep, "; ".join(parts)))
        lines.append("ROW %s H-LAST: flag bit 7 at slots %s; a tile drawn iff its header is at or "
                     "before it: %d of %d tiles: %s; H-FLAGSLOT (frozen slot %s): %s" % (
                         n, last[:4], right, ntiles, word(hl), one(n, "flagslot", "H-FLAGSLOT"), word(fs)))
    lines.append("SUMMARY: Q139 held out (fy 11 and 23): R7-BLK (= H-EVEN at fx 4 and 8) gives the "
                 "wrong-tile set and every header slot: " + SK.headline(
                     "R7-BLK holds", ctl, st["slots-heldout"]))
    lines.append("SUMMARY: Q139 replicates of E907's fy-10 dumps: R7-BLK gives the wrong-tile set "
                 "and every header slot: " + SK.headline("R7-BLK holds", ctl, st["slots-replicate"]))
    lines.append("SUMMARY: Q139 H-LAST (E959, held out): one header with flag bit 7, a target tile "
                 "drawn iff its header lies at or before it: " + SK.headline(
                     "H-LAST holds", ctl, st["H-LAST"]))
    lines.append("SUMMARY: Q139 H-FLAGSLOT: the flagged header is the last target tile's in block "
                 "order (H-EVEN's slot): " + SK.headline("H-FLAGSLOT holds", ctl, st["H-FLAGSLOT"]))
    return lines


SCORERS = {"pivot": score_pivot, "bgw": score_bgw, "q139c": score_q139c}


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        print("\n".join(SCORERS[argv[1]](argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
