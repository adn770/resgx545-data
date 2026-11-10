"""R3 geometry stages (laptop session ~/r3g, decisions R3-G1..R3-G9 in plans/resgx545-question-closing.md), order: g-da, g-db, g-dc,
g-dd (depth at w != 1, Q230), g-c4, g-d36, g-c6, g-c5, g-c7 (the raise limit C by target and the dword 36, Q210, Q273).

Frozen predictions come from r3models (offline FITS to data measured before this file); the runs hold them out.  A prediction row is
(case, quantity, value, model, set): `set` is control (measured value, a failing one voids the group), heldout, repeat, replicate.
Quantities the scorers read as meta, never tallied: cell, frac, word_down, word_up, thr_dir, raise_rule, last_raise_thr0.
Case names starting with "@" are stage-level predictions (no job row).
"""
from __future__ import annotations

import io
import contextlib
from fractions import Fraction as F

import r1_geo as G
import r2models as M2
import r3models as M
from rcommon import BINS, RT_DPM2, TEMPLATES, Row, probe

HX = G.HX
GREEN = G.GREEN
STOP = "stophang"
RT = RT_DPM2
WORD = lambda x: M.word(M.f32(x))
HXF = lambda x: HX(WORD(x))
DEPTH_RULES = ("D1", "D2", "D5", "T26", "T27", "K23")


PROGRAMS = {}          # name -> (template, {input: float32 Fraction}, blk words): what tests/test_templates_r3.py runs in sgx-sim


def order(rows):
    return [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]


# ------------------------------------------------------------------------------------------------ depth rows
def _wz_row(rows, needs, name, Z, W, st, role, blk=None):
    """A vtx_wzclip.s row: w = W constant, x and y scaled by W, clip z = Z (float32 values)."""
    kw = dict(blk=blk) if blk else {}
    p = G._p3(name, "vtx_wzclip.s", "vtxuse", ["S", "A", "B", "Z"], [HXF(W), HX(0), HXF(W), HXF(Z)], src_dir=TEMPLATES, **kw)
    rows.append(Row(name, st, "safe", "-", STOP, "-", G._cmd_of(p, TEMPLATES), role, name))
    needs.append(f"$S/{name}__0.bin")
    PROGRAMS[name] = ("vtx_wzclip.s", dict(S=W, A=F(0), B=W, Z=Z), blk or {})


def _w3(word):
    return ",".join([f"0x{word:08x}"] * 3)


def _dword(Z: F, W: F, rule, sum_mode="rn"):
    return M.depth_word(Z, W, rule, sum_mode)


def _ctl_preds(preds, n, word, why):
    preds += [(n, "object", "present", "in band, no clip", "control"), (n, "depth_words", _w3(word), why, "control")]


# the held-out (Z, W) pairs of g-da: z/w in (-1, -0.5] so the sum is exact and the word is a function of the rounded product alone
WS = [5.0, 9.0, 11.0, 13.0, 1.3, 0.7, 0.01, 6.0, 1.7, 23.0, 0.3, 19.0]
# (kind, lo, hi, n, targets): the first inside bin straddles t = 3/8 (one cell below it, one above)
DA_BINS = [("outside-lo", 0.02, 0.10, 2, None), ("outside-mid", 0.30, 0.36, 3, None), ("inside", 0.37, 0.39, 2, (0.3715, 0.380)),
           ("inside", 0.39, 0.41, 2, None), ("inside", 0.41, 0.43, 2, None), ("inside", 0.44, 0.455, 2, None),
           ("inside", 0.455, 0.4667, 2, None), ("outside-hi", 0.47, 0.498, 4, None), ("above-half", 0.52, 0.60, 2, None)]


def da_pairs():
    """[(kind, Z, W, frac)] in frozen order: for every bin of DA_BINS, n cells whose fractions sit at the centres of n equal slices of
    the bin (or at the bin's explicit targets), at least 0.004 away from t = 3/8 and 7/16 (the two named thresholds), preferring cells where at least two candidate
    words differ; each W is used at most three times."""
    cands = []
    for W in WS:
        w = M.f32(W)
        for i in range(505, 995):
            z = M.f32(-W * i / 1000.0)
            q = z / w
            if not (F(-1) < q <= F(-1, 2)):
                continue
            fr = float(M.frac(z, w))
            if min(abs(fr - 0.375), abs(fr - 0.4375)) < 0.004:
                continue
            nd = len({M.depth_word(z, w, r) for r in DEPTH_RULES})
            cands.append((fr, W, z, w, nd))
    used, out = {}, []
    for kind, lo, hi, n, tg in DA_BINS:
        for j in range(n):
            target = tg[j] if tg else lo + (hi - lo) * (j + 0.5) / n
            best = None
            for fr, W, z, w, nd in cands:
                if not (lo <= fr < hi) or used.get(W, 0) >= 3 or any(z == o[1] for o in out):
                    continue
                sc = ((0 if nd >= 3 else 1 if nd == 2 else 2, round(abs(fr - target) / 0.01), used.get(W, 0), abs(fr - target)) if not tg else
                      (0 if nd >= 2 else 1, round(abs(fr - target) / 0.002), used.get(W, 0), abs(fr - target)))
                if best is None or sc < best[0]:
                    best = (sc, fr, W, z, w)
            assert best, (kind, lo, hi, j)
            out.append((kind, best[3], best[4], best[1]))
            used[best[2]] = used.get(best[2], 0) + 1
    return out


def _down_up(z, w):
    p = z * M.rz_recip(w)
    dn, up = M.rnd(p, "rz"), M.rnd(p, "ra")
    assert dn != up, "an exact product separates nothing"
    return M.word(M.H + M.H * dn), M.word(M.H + M.H * up)


def g_da():
    rows, preds, needs = [], [], []
    ctl = [("da-ctl-z0-w3", 0.0, 3.0, 0x3F000000, "E754's e3i-w3: Z = 0, W = 3: depth 0.5"),
           ("da-ctl-zm05-w1", -0.5, 1.0, 0x3E800000, "S1/S1b cut-p's vertex A: Z = -0.5, W = 1: depth 0.25"),
           ("da-rep-m2p6-3", -2.6, 3.0, 0x3D88888C, "repeat of E783's t4-m2p6-3, the ONE word the threshold fit rests on (D1 gives another)"),
           ("da-rep-m6p1-7", -6.1, 7.0, 0x3D83A840, "repeat of E783's t4-m6p1-7 (D1 and D5 agree)")]
    for n, Z, W, w, role in ctl:
        _wz_row(rows, needs, n, M.f32(Z), M.f32(W), "control", f"control: Z = {Z:g}, W = {W:g}, {role}")
        _ctl_preds(preds, n, w, "measured (E754, S1b, E783)")
    p2 = [("da-p2-w2", M.rprec(M.f32(-1.3), 20, "rz"), M.f32(2.0)), ("da-p2-w05", M.rprec(M.f32(-0.35), 20, "rz"), M.f32(0.5))]
    for n, z, w in p2:
        _wz_row(rows, needs, n, z, w, "control", f"control: w = {float(w):g} (a power of two): the product is exact, every candidate gives one word")
        ws = {M.depth_word(z, w, r) for r in DEPTH_RULES}
        assert len(ws) == 1, (n, ws)
        _ctl_preds(preds, n, ws.pop(), "every candidate (z RZ(1/w) is exact at a power of two)")
    pairs = da_pairs()
    counter = {}
    for kind, z, w, fr in pairs:
        c = counter[kind] = counter.get(kind, 0) + 1
        n = f"da-{ {'outside-lo': 'lo', 'outside-mid': 'mid', 'inside': 'in', 'outside-hi': 'hi', 'above-half': 'up'}[kind] }{c}"
        _wz_row(rows, needs, n, z, w, "heldout",
                f"Z = {float(z):.9g}, W = {float(w):g}: z/w = {float(z / w):.4f}, fraction of |z RZ(1/w)| {fr:.4f} ({kind})")
        dn, up = _down_up(z, w)
        words = {r: M.depth_word(z, w, r) for r in DEPTH_RULES}
        preds += [(n, "object", "present", "in band (x, y scaled by w): no clip", "heldout"),
                  (n, "cell", kind, "geometry of the cell", "heldout"), (n, "frac", f"{fr:.6f}", "geometry of the cell", "heldout"),
                  (n, "word_down", f"0x{dn:08x}", "frame: RZ of the product", "heldout"),
                  (n, "word_up", f"0x{up:08x}", "frame: one ulp above it, away from zero", "heldout")]
        exp = {"outside-lo": "down", "outside-mid": "down", "outside-hi": "up", "above-half": "up", "inside": "flip"}[kind]
        preds.append((n, "thr_dir", exp, "H-thr (up iff the fraction exceeds one t in (0.3655, 0.4667))", "heldout"))
        for r in DEPTH_RULES:
            preds.append((n, "depth_words", _w3(words[r]), f"{r} ({M.RULE_TEXT[r]})", "heldout"))
    head = """g-da (Q230, depth at w != 1): the threshold ladder.  Offline FIT (post hoc, closing3/geometry/exp-geometry-r3.md): E783's six words
and E782's four kept vertices are all matched by ONE family, "round |z RZ(1/w)| away from zero iff its fraction exceeds t", t between
0.3655 and 0.4667 (T26: t = 3/8, T27: t = 7/16; K23, z cut to 23 bits, also fits), round to nearest (D1) and the others miss one word
or more.  The fit rests on ONE word (t4-m2p6-3); 257 models were tried.  z/w in (-1, -0.5] keeps the sum 0.5 + 0.5 q exact, so the
stored word is a function of the rounded product alone.  Controls (6, each can fail): the two R2 controls, repeats of t4-m2p6-3 and
t4-m6p1-7 (the first one is the fit's own word: another word stops the reading), w = 2 and 0.5 (exact products).  Held out (21):
five cells below t (fraction 0.02-0.10, 0.30-0.36: down), four above (0.47-0.498: up, D1 down), two above one half (up), ten inside
the interval in five bins of two (T26 up from 0.375, T27 from 0.4375).  H-thr holds iff the 11 outside cells read as frozen and the
10 inside cells are monotone in the fraction; T26 or T27 is named only if one is right 10 of 10 inside.  A non-monotone inside row
refutes the threshold family; the simulator then keeps refusing z != 0.  Each W is used at most three times."""
    return order(rows), preds, needs, head


# ------------------------------------------------------------------------------------------------ g-db
DB_RULES = ("D1", "D5", "T26", "T27", "T26d", "T27d", "K23")
SUMS = ("rn", "rz", "rh")
SUM_TEXT = {"rn": "the sum 0.5 + 0.5 q' to nearest even", "rz": "the sum toward zero", "rh": "the sum half up"}


def _greedy(pool, labels_of, k, prefer=None):
    """Pick k items from pool [(key, item)] maximizing the number of label pairs told apart; deterministic.  labels_of(item)
    -> {label: word}."""
    chosen, sep = [], set()
    for _ in range(k):
        best = None
        for key, item in pool:
            if any(key == c[0] for c in chosen):
                continue
            lab = labels_of(item)
            labs = sorted(lab)
            new = {(a, b) for i, a in enumerate(labs) for b in labs[i + 1:] if lab[a] != lab[b]} - sep
            sc = (len(new), -len(chosen))
            if best is None or sc > best[0]:
                best = (sc, key, item, new)
        chosen.append((best[1], best[2]))
        sep |= best[3]
    return [c[1] for c in chosen], sep


def db_labels_a(z, w):
    return {f"{r}+{s}": M.depth_word(z, w, r, s) for r in DB_RULES for s in SUMS}


def db_labels_b(z, w):
    out = {f"{r}+{s} (own)": M.depth_word(z, w, r, s) for r in ("D1", "D5", "T26", "T27", "K23") for s in SUMS}
    out.update({f"{r}+grid": M.q_candidates(z, w, r, True) for r in ("D1", "D5", "T26", "T27")})
    return out


def db_pairs():
    wsel = [5.0, 9.0, 13.0, 1.3, 0.7, 6.0, 1.7, 23.0, 11.0, 0.3]
    pool_a, pool_b = [], []
    for W in wsel:
        w = M.f32(W)
        for i in range(505, 995, 3):
            z = M.f32(W * i / 1000.0)                              # z > 0, z/w in [0.5, 1)
            pool_a.append(((W, i), (z, w)))
        for i in range(255, 500, 3):
            for sg in (1, -1):
                z = M.f32(sg * W * i / 1000.0)                     # |z/w| in (0.25, 0.5), both signs
                pool_b.append(((W, i, sg), (z, w)))
    a, _ = _greedy(pool_a, lambda it: db_labels_a(*it), 6)
    # the six q-precision cells: three of each sign
    b_pos, _ = _greedy([p for p in pool_b if p[0][2] == 1], lambda it: db_labels_b(*it), 3)
    pool_b2 = [p for p in pool_b if p[0][2] == -1]
    b_neg, _ = _greedy(pool_b2, lambda it: db_labels_b(*it), 3)
    return a, b_pos + b_neg


def db_near1():
    """E783's "near w = 1" w values; z is -0.75 or, where all eight rules agree there, the nearest z below it (steps of 2^-22)
    that tells at least three words apart."""
    ws = [(M.wordval(0x3F800001), "1+2^-23"), (M.wordval(0x3F7FFFFE), "1-2^-23"), (M.f32(1.5), "1.5"), (M.f32(1.0000004), "1.0000004")]
    out = []
    for w, lab in ws:
        for k in range(0, 4000):
            z = M.f32(-0.75) - F(k, 2 ** 22)
            if len({M.depth_word(z, w, r) for r in ("D1", "D2", "D5", "T26", "T27", "K23", "T26d", "T27d")}) >= 3:
                break
        out.append((w, lab, z))
    return out


def g_db():
    rows, preds, needs = [], [], []
    a, b = db_pairs()
    n1 = db_near1()

    def emit(n, z, w, labels, role, text):
        _wz_row(rows, needs, n, z, w, "heldout", role)
        assert len(set(labels.values())) >= 2, (n, labels)
        preds.append((n, "object", "present", "in band (x, y scaled by w): no clip", "heldout"))
        for lab, word in labels.items():
            preds.append((n, "depth_words", _w3(word), text(lab), "heldout"))

    for i, (z, w) in enumerate(a, 1):
        emit(f"db-pos{i}", z, w, db_labels_a(z, w), f"Z = {float(z):.9g}, W = {float(w):g}: z > 0, z/w = {float(z / w):.4f} in [0.5, 1)",
             lambda lab: f"{lab} (product rule {M.RULE_TEXT[lab.split('+')[0]]}; {SUM_TEXT[lab.split('+')[1]]}; z > 0 group)")
    for i, (z, w) in enumerate(b, 1):
        emit(f"db-q{i}", z, w, db_labels_b(z, w), f"Z = {float(z):.9g}, W = {float(w):g}: |z/w| = {float(abs(z / w)):.4f} in (0.25, 0.5), "
             f"{'+' if z > 0 else '-'}",
             lambda lab: f"{lab} ({'the product kept on the 2^-23 grid of the sum' if lab.endswith('grid') else 'the product at float32 precision, then the sum'}; q group)")
    for i, (w, lab, z1) in enumerate(n1, 1):
        labels = {r: M.depth_word(z1, w, r) for r in ("D1", "D2", "D5", "T26", "T27", "K23", "T26d", "T27d")}
        emit(f"db-near{i}", z1, w, labels, f"Z = {float(z1):.9g} (-0.75 or the nearest z that tells the rules apart), W = {lab}: w next to 1",
             lambda lab_: f"{lab_} ({M.RULE_TEXT[lab_]}; near-1 group)")
    head = """g-db (Q230): sign, magnitude and the sum.  The threshold family of g-da is asked, on the cells it can still be wrong, whether
"up" means away from zero (T26 / T27: the fraction of |p|) or toward +infinity (T26d / T27d: the floor fraction; the same on
every negative product, so g-da cannot tell), and how the sum 0.5 + 0.5 q' is rounded where it is not exact: nearest even (rn),
toward zero (rz), half up (rh).  Six pairs with z > 0 and z/w in [0.5, 1) (the sum ties when q' is odd): 7 rules x 3 sums = 21
labels, the generator keeps the six pairs that tell the most label pairs apart (greedy).  Six pairs with |z/w| in (0.25, 0.5),
three of each sign: the product at its own float32 precision against the product kept on the 2^-23 grid of the sum (D1, D5, T26,
T27), K23 and the sums.  Four pairs with w next to 1 (E783's "near w = 1"): z = -0.75 (or the nearest z that separates), w = 1 + 2^-23, 1 - 2^-23 (E783 named 1 - 2^-24, whose RZ reciprocal is exactly 1: no rule can differ), 1.5, 1.0000004,
eight rules.  No control job: the stage reads only cells that g-da's controls guard (the scorer needs every pair to carry at least two
distinct frozen words); a held-out label is `consistent` only if it fits all 16 cells it is frozen on."""
    return order(rows), preds, needs, head


# ------------------------------------------------------------------------------------------------ g-dc
def _vp_pool(off, scale, ws, step=7):
    pool = []
    for W in ws:
        w = M.f32(W)
        for i in range(-995, 995, step):
            if abs(i) < 60:
                continue
            z = M.f32(W * i / 1000.0)
            q = z / w
            if abs(q) >= 1:
                continue
            pool.append(((W, i), (z, w)))
    return pool


def g_dc():
    rows, preds, needs = [], [], []
    ob = lambda off, sc: {10: WORD(off), 11: WORD(sc)}
    one = M.f32(1.0)

    def emit(n, st, z, w, off, sc, role):
        _wz_row(rows, needs, n, z, w, st, role, blk=ob(off, sc))
        labs = M.vp_cands(z, w, off, sc)
        preds.append((n, "object", "present", "in band (x, y scaled by w): no clip", st))
        return labs

    # control: the default viewport words written explicitly (0.5 and 0.5) reproduce t4-ctl-zm05-w1
    n = "dc-ctl-default"
    labs = emit(n, "control", M.f32(-0.5), one, M.f32(0.5), M.f32(0.5), "control: blk 10 = blk 11 = 0.5 (the defaults, written explicitly), Z = -0.5, W = 1")
    assert len(set(labs.values())) == 1 and next(iter(labs.values())) == 0x3E800000, labs
    preds.append((n, "depth_words", _w3(0x3E800000), "measured (t4-ctl-zm05-w1, S1/S1b: the defaults 0.5, 0.5)", "control"))
    # w = 1: offset 0.25 scale 0.5, and the swap (offset 0.5 scale 0.25); scale 0.3 offset 0.6 with z where one and two roundings differ
    z0 = M.f32(-0.3125)
    for n, off, sc, role in (("dc-w1-o25s5", M.f32(0.25), M.f32(0.5), "blk 10 = 0.25, blk 11 = 0.5, z = -0.3125: offset 0.25 + 0.5 z = 0.09375 if blk 10 is the offset"),
                             ("dc-w1-o5s25", M.f32(0.5), M.f32(0.25), "the swap: blk 10 = 0.5, blk 11 = 0.25: 0.5 + 0.25 z = 0.421875 if blk 10 is the offset")):
        labs = emit(n, "heldout", z0, one, off, sc, f"{role} (w = 1)")
        assert len(set(labs.values())) >= 2, (n, labs)
        for k, w_ in labs.items():
            preds.append((n, "depth_words", _w3(w_), f"{k} ({M.VP_KINDS[k][1]})", "heldout"))
    s3, o6 = M.f32(0.3), M.f32(0.6)
    pool = [((i,), (M.f32(i / 997.0), one)) for i in range(-990, 990, 3) if i]
    sel, _ = _greedy(pool, lambda it: M.vp_cands(it[0], it[1], o6, s3), 1)
    z, w = sel[0]
    labs = emit("dc-w1-s3o6", "heldout", z, w, o6, s3, f"blk 10 = 0.6, blk 11 = 0.3, z = {float(z):.9g}, w = 1: one against two roundings of the sum")
    assert labs["VF"] != labs["VT"], labs
    for k, w_ in labs.items():
        preds.append(("dc-w1-s3o6", "depth_words", _w3(w_), f"{k} ({M.VP_KINDS[k][1]})", "heldout"))
    # w != 1, scale 0.3: (z rhw) scale against (z scale) rhw
    pool = _vp_pool(o6, s3, (3.0, 7.0, 1.1, 0.7, 5.0, 13.0))
    sel, _ = _greedy(pool, lambda it: M.vp_cands(it[0], it[1], o6, s3), 6)
    for i, (z, w) in enumerate(sel, 1):
        n = f"dc-wn{i}"
        labs = emit(n, "heldout", z, w, o6, s3, f"blk 10 = 0.6, blk 11 = 0.3, Z = {float(z):.9g}, W = {float(w):g}: z/w = {float(z / w):.4f}")
        for k, w_ in labs.items():
            preds.append((n, "depth_words", _w3(w_), f"{k} ({M.VP_KINDS[k][1]})", "heldout"))
    head = """g-dc (Q230): the viewport z words, `--blk 10=V --blk 11=V` (vp4, vp5).  E193 reads vp4 as the z offset and vp5 as the z scale (both
0.5 by default); one slope never separated which is which, nor how the sum is rounded.  Candidates: VF (offset + scale x the
product to nearest, one rounding of the sum), VT (the scale product rounded first), VZ ((z scale) rounded, times RZ(1/w)
rounded, then the sum), VS (the order swapped).  Four jobs at w = 1: the default words written explicitly (control: 0x3e800000),
offset 0.25 with scale 0.5, the swap, and scale 0.3 with offset 0.6 and a z where one and two roundings of the sum differ; then
six at w != 1 with scale 0.3 chosen by the generator (greedy) to tell (z rhw) scale from (z scale) rhw.  Depth stays inside [0, 1].
The product at w != 1 is rounded to nearest in every candidate (D1): g-da decides that rule first, so a miss at w != 1 is read
together with its result."""
    return order(rows), preds, needs, head


# ------------------------------------------------------------------------------------------------ g-dd
def _tpl_row(rows, needs, name, template, inputs, case, st, role, **kw):
    p = G._p3(name, template, "vtxuse", inputs, [HX(v) for v in case], src_dir=TEMPLATES, **kw)
    probe.build_helpers([p], BINS, TEMPLATES)
    needs += [f"$S/{name}__0.bin", "$S/pix_green.bin"]
    rows.append(Row(name, st, "safe", "-", STOP, "-", G._cmd_of(p, TEMPLATES), role, name))
    PROGRAMS[name] = (template, dict(zip(inputs, [M.wordval(v) for v in case])), {})


def _fmt_xy_words(xy, words, sel=None):
    return ";".join(f"{x:.4f},{y:.4f}=0x{w:08x}" for (x, y), w, s in zip(xy, words, sel or [True] * len(xy)) if s)


DD_CUTS = [("dd-p1", 2.0, 1.0, 0.25, 1.5, "+w", "z = 2x + 1, w = 0.25x + 1.5: cut at x = 2/7, made w = 11/7"),
           ("dd-p2", 2.0, 1.0, -0.25, 1.5, "+w", "z = 2x + 1, w = -0.25x + 1.5: cut at x = 2/9, made w = 13/9"),
           ("dd-m1", 2.0, -0.25, 0.5, 1.25, "-w", "z = 2x - 0.25, w = 0.5x + 1.25: cut at x = -0.4, made w = 1.05 (z = -w)"),
           ("dd-m2", 2.0, -0.25, -0.25, 1.5, "-w", "z = 2x - 0.25, w = -0.25x + 1.5: cut at x = -5/7, made w = 47/28 (z = -w)")]


def g_dd():
    rows, preds, needs = [], [], []
    for n, A, B, C, D, plane, role in DD_CUTS:
        _tpl_row(rows, needs, n, "vtx_zw.s", ["A", "B", "C", "D"], [WORD(A), WORD(B), WORD(C), WORD(D)], "heldout", role,
                 temps=8, vtx_coords=2, slots={"pixel": "pix_green.s"})
        pr = M2.predict_zwclip(A, B, C, D)
        made = pr["made"]
        assert any(made), n
        P = lambda q, v, m: preds.append((n, q, v, m, "heldout"))
        fmt = lambda xy: ";".join(f"{x:.6f},{y:.6f}" for x, y in xy)
        P("object", "present", "clip")
        P("nvert", str(pr["nv"]), "HSH (Sutherland-Hodgman in (x, y, z, w), planes z <= w and z >= -w)")
        P("xy_set", fmt(sorted(pr["xy"])), "HSH (window = 32 + 32 x/w, made vertices at the cut)")
        P("xy_ordered", fmt(pr["xy"]), "HZZ (strip zigzag of the SH polygon)")
        P("prims", ";".join(",".join(str(e) for e in t) for t in pr["prims"]), "HPR (index | 16 for a boundary edge)")
        for lab, key, desc in (("HI-w", "rhw_w", "made 1/w = RZ of 1/w_made"),):
            v = _fmt_xy_words(pr["xy"], pr[key])
            P("rhw_by_xy", v, f"{lab} ({desc}), exact word")
            P("rhw_by_xy", v, f"{lab} ({desc}), within 1 ulp")
        P("depth_made_by_xy", _fmt_xy_words(pr["xy"], [d or 0 for d in pr["depth_made"]], made),
          "HDP-made (z = +w / -w gives depth 1.0 / 0.0 exactly at a made vertex, whatever w)")
    head = """g-dd (Q230): the made vertices at w != 1, measurement (vtx_zw.s: z = A x + B, w = C x + D).  Two cuts on the +w plane and two on the
-w plane, new constants (E782 had 4/3 and 6/5 on +w only).  Frozen: the polygon (set, order, prim words, window positions: E782's rules
held out again), the made vertices' 1/w by HI-w (RZ of 1/w_made, exact and within one ulp), and "depth exactly 1.0 (+w) / 0.0 (-w)"
at a made vertex (HDP-made), the rule E782 refuted at one of four vertices and which can be refuted again.  The depth words are
recorded either way.  The structure (nvert, set, order, prims) is the control that can fail: a job whose structure fails is flagged and its
made-vertex words are not tallied.  Whether the made z is the made w bit for bit [infer] stays open unless a pattern shows."""
    return order(rows), preds, needs + [GREEN], head


# ------------------------------------------------------------------------------------------------ DPM rows
LT_LAST_2048 = M.lt_last_thr0(2048, 2048)           # 0xd4
H_LAST = "H-last (dword 36 = max(count before the LAST abort - 2, 0); fit: 49 of 49 kept jobs with an abort, only two separating the readings)"


def dpm_cmd(w, h, extra="", ctx=None):
    cx = f" --max-width {ctx[0]} --max-height {ctx[1]}" if ctx else ""
    return f'probe --tri pixel --width {w} --height {h}{cx} --vertices 1500{extra} --dump-render "$W/dump" "{GREEN}"'


def _dpm(rows, preds, name, st, P, knobs, cmd, role):
    rows.append(Row(name, st, "safe", P, " ".join([STOP] + knobs), RT, cmd, role, name))
    if P.startswith("0x"):
        preds.append((name, "knob0624_first", hex(int(P, 16) - 0x22), "knob", st))
    preds.append((name, "dw36", "max(count before the last abort - 2, 0)", H_LAST, "heldout" if st != "control" else "heldout"))


def _lt_preds(preds, name, w, h, st):
    lt = M.lt_last_thr0(w, h)
    preds.append((name, "raise_rule", f"thr0 <= {lt:#x}", f"LT (raise iff thr0 <= floor(0x351 R / 32768), R = regions: {lt:#x} here)", st))


def g_c4():
    rows, preds = [], []
    ctl = [("c3-4096-0x372", 4096, 0x372, "R", "raise"), ("c3-4096-0x374", 4096, 0x374, "N", "none"),
           ("c3-2048-0xe2", 2048, 0xE2, "R", "raise"), ("c3-2048-0x122", 2048, 0x122, "N", "none")]
    for n, s, P, c, word in ctl:
        knobs = [f"ctl:{c}"] + ([f"obs:c4"] if s == 2048 else [])
        _dpm(rows, preds, n, "control", hex(P), knobs, dpm_cmd(s, s), f"control: R2's {n} ({word}; E785 / R1)")
        preds.append((n, "raise", "yes" if c == "R" else "no", "measured (R1 at 4096, R2 at 2048)", "control"))
    for i in range(1, 7):
        n = f"c4-b{i}"
        _dpm(rows, preds, n, "heldout", "B:c4", ["obs:c4"], dpm_cmd(2048, 2048),
             f"bisect cell {i} of 6: the midpoint of the kept observations of g-c4 (thr0 0xc0 raise, 0x100 none at the start)")
        _lt_preds(preds, n, 2048, 2048, "heldout")
    preds.append(("@g-c4", "last_raise_thr0", f"{LT_LAST_2048:#x}", "LT (one parameter from 4096x4096 only: last raise thr0 0xd4, C = 0xf4)", "heldout"))
    head = f"""g-c4 (Q210): the exact limit C at 2048x2048, 1500 vertices, plain 2048x2048 context.  E785 bracketed the last raising thr0 in (0xc0,
0x100): raise at P 0xe2, none at 0x122.  LT (a fit to 4096x4096 alone): the last raise is at thr0 <= floor(0x351 R / 32768) with R =
regions = ceil(W/32) ceil(H/16), i.e. thr0 0xd4 (C 0xf4) at 2048x2048, inside the bracket, a 1 in 64 hit on the exact cell.  Four
controls (R1's two at 4096, R2's two at 2048; knob ctl:R / ctl:N: a control that reads otherwise stops the session), then six
bisect cells whose thr0 the RUNNER picks from the kept observations of the group (state file, midpoint lo + (hi - lo) / 2, lo = the
highest raise, hi = the lowest silent above it; under LT the cells are 0xe0, 0xd0, 0xd8, 0xd4, 0xd6, 0xd5).  A void cell (no abort,
or the second run does not reach thr0) ends the bisect.  The scorer re-derives every pick and flags one off the rule.  Verdict: the
exact flip at 0xd4/0xd5 = LT holds; any other exact flip refutes LT and is the measurement; two flips refute the monotone form.
Side table in every job: H-last."""
    return order(rows), preds, [GREEN], head


D36_THR0 = ((2048, 0x60), (2048, 0x70), (2048, 0x90), (2048, 0xB0), (4096, 0x2C0), (4096, 0x300))


def g_d36():
    rows, preds = [], []
    for s, t in D36_THR0:
        n = f"d36-{s}-{t:#x}"
        _dpm(rows, preds, n, "heldout", hex(t + 0x22), [], dpm_cmd(s, s), f"{s}x{s}, thr0 {t:#x} (P {t + 0x22:#x}): partial renders with three or more aborts expected")
    preds.append(("@g-d36", "separating_jobs", ">= 3 jobs where the last abort's count differs from the peak or the second abort's", H_LAST, "heldout"))
    head = """g-d36 (Q273): dword 36 of the control block against the 0x072c page count at the LAST abort.  H-last (fit post hoc on 49 kept jobs, 49
of 49, only two of them separating it from the peak and second-abort readings): the firmware writes dword 36 = max(global page count
- 2, 0) at every abort and the last write stays; no abort reads 0.  E790 refuted "peak less 2" (13 of 15) and "first abort less 2" (8
of 15).  Six jobs, 1500 vertices, the knob only: 2048x2048 at thr0 0x60, 0x70, 0x90, 0xb0 (E785 had three aborts at 0x80 and 0xc0), 4096x4096
at 0x2c0 and 0x300 (E786's k-1500-0x300 had three).  The scorer prints per job the counts before each abort, marks a job SEP when H-last's value differs
from the peak reading's or the second-abort reading's.  H-last holds iff every separating job fits and at least 3
jobs separate; one miss in a separating job refutes it; fewer than 3 separating jobs: cannot tell.  The controls are g-c4's (the
session's): the scorer needs g-c4's four controls to pass.  Partial renders are expected 3 to 8 a job; the stage stops on `job hung`."""
    return order(rows), preds, [GREEN], head


def g_c6():
    rows, preds = [], []
    ctx = (4096, 4096)
    cmd = dpm_cmd(2048, 2048, ctx=ctx)
    _dpm(rows, preds, "c6-cal", "heldout", "0x422", ["cal:c6"], cmd, "calibration: 2048x2048 target in a 4096x4096 context at P 0x422 (page need; 0x213 on the plain context)")
    preds.append(("c6-cal", "page_need", "0x213", "H-target / H-context (the scene and target fix the need: the same as the plain context)", "heldout"))
    for n, P, role in (("c6-L", "L:c4", "the last raising cell of g-c4 (picked by the runner from g-c4's kept observations)"),
                       ("c6-F", "F:c4", "the first silent cell of g-c4"),
                       ("c6-0x100", "0x122", "thr0 0x100 (none on the plain context)"),
                       ("c6-0x120", "0x142", "thr0 0x120")):
        _dpm(rows, preds, n, "heldout", P, ["fit:c6"], cmd, f"2048x2048 in a 4096x4096 context: {role}")
        if n in ("c6-L", "c6-F"):
            want = "yes" if n == "c6-L" else "no"
            preds.append((n, "raise", want, "H-target (the limit follows the target: the flip of g-c4)", "heldout"))
            preds.append((n, "raise", "yes", "H-context (the limit follows the context: raise at every valid cell, as 4096x4096's 0x371)", "heldout"))
        else:
            preds.append((n, "raise", "no", "H-target (the limit follows the target: none above g-c4's flip)", "heldout"))
            preds.append((n, "raise", "yes", "H-context (the limit follows the context: raise at every valid cell, as 4096x4096's 0x371)", "heldout"))
    head = """g-c6 (Q210): context against target.  The render context is created for up to --max-width x --max-height; R2's 2048x2048 jobs ran in a
2048x2048 context.  Here the same 2048x2048 target in a 4096x4096 context: a calibration at P 0x422, the two cells at g-c4's flip
(the runner reads g-c4's kept observations: the last raise L and the first silent F; a stage run without g-c4's state skips them) and
thr0 0x100, 0x120.  H-target: the flip of g-c4 (L raises, F none, 0x100 and 0x120 none).  H-context: raise at every valid cell (the
4096 limit).  A page need other than 0x213 is reported and makes the cells a measurement.  Cells with 2 thr0 above the need are skipped
by the runner (fit:c6) as void by construction."""
    return order(rows), preds, [GREEN], head


C5_T = (("c5a", 4096, 2048), ("c5b", 2048, 4096), ("c5c", 3072, 3072))


def g_c5():
    rows, preds = [], []
    for g, w, h in C5_T:
        cmd = dpm_cmd(w, h)
        tag = f"{w}x{h}"
        _dpm(rows, preds, f"{g}-cal", "heldout", "0x422", [f"cal:{g}"], cmd, f"{tag}: calibration at P 0x422 (the page need)")
        for i, t in enumerate(M.c5_fixed_cells(w, h), 1):
            n = f"{g}-f{i}"
            _dpm(rows, preds, n, "heldout", hex(t + 0x22), [f"obs:{g}", f"fit:{g}"], cmd, f"{tag}: fixed cell thr0 {t:#x} (P {t + 0x22:#x}): an end of a law's bracket or LT's flip pair")
            _law_preds(preds, n, w, h)
        for i in range(1, 7):
            n = f"{g}-b{i}"
            _dpm(rows, preds, n, "heldout", f"B:{g}", [f"obs:{g}", f"fit:{g}"], cmd, f"{tag}: bisect cell {i} of 6 (midpoint of the kept observations of {g})")
            _law_preds(preds, n, w, h)
        lt = M.lt_last_thr0(w, h)
        br = M.affine_brackets(w, h)
        preds.append((f"@{g}", "last_raise_thr0", f"{lt:#x}", f"LT at {tag}", "heldout"))
        preds.append((f"@{g}", "last_raise_thr0", f"{br['R'][0]:#x}..{br['R'][1]:#x}", f"affine in regions, C(2048x2048) anywhere in [0xe0, 0x120)", "heldout"))
    head = """g-c5 (Q210): three more targets, 1500 vertices, a plain context of the target's size, 12 jobs each: a calibration at P 0x422, five
fixed cells (the ends of the affine-in-regions bracket and LT's flip pair; the runner skips a cell whose 2 thr0 is above the page
need: void by construction), then up to six bisect cells whose thr0 the runner picks from the kept observations of the target's group
(none run if the bracket is closed, absent or non-monotone).  Laws, frozen as formulas over the MEASURED C(2048x2048) of g-c4: LT (one
point, from 4096x4096), and affine through the two exact points in regions, in the tail-pointer side squared, in the macrotile area.
4096x2048 and 2048x4096 have equal regions (16384) and tail-pointer sides 128 and 256: different limits there refute every law in
regions alone.  The scorer evaluates a law's predicted interval against the measured last-raise interval.  The controls are
g-c4's.  Void cells (second run short of thr0) are expected above about half the page need; a law whose flip lies there is
"not reached", not refuted."""
    return order(rows), preds, [GREEN], head


def _law_preds(preds, n, w, h):
    lt = M.lt_last_thr0(w, h)
    br = M.affine_brackets(w, h)
    preds.append((n, "raise_rule", f"thr0 <= {lt:#x}", "LT (last raise thr0 = floor(0x351 R / 32768))", "heldout"))
    for k, key, txt in (("AR", "R", "affine in regions"), ("AS", "side2", "affine in the tail-pointer side squared"), ("AM", "mt", "affine in the macrotile area")):
        preds.append((n, "raise_rule", f"thr0 <= affine({key}; C2048) - 0x20, between {br[key][0]:#x} and {br[key][1]:#x}",
                      f"{k} ({txt} through the measured C(2048x2048) and 0x371)", "heldout"))


def g_c7():
    rows, preds = [], []
    cmd = dpm_cmd(2048, 2048, extra=" --tri-full")
    _dpm(rows, preds, "c7-cal", "heldout", "0x422", ["cal:c7", "gate:3"], cmd, "calibration: --tri-full 1500 vertices at 2048x2048, P 0x422; the gate: at most 3 partial renders")
    preds.append(("c7-cal", "page_need", "> 0x213", "H-scene (a different scene: the page need is larger; unknown)", "heldout"))
    cells = [("c7-L", "L:c4", "the last raising cell of g-c4"), ("c7-F", "F:c4", "the first silent cell of g-c4"),
             ("c7-L-16", "L:c4:-16", "g-c4's last raise less 16"), ("c7-L-4", "L:c4:-4", "g-c4's last raise less 4"),
             ("c7-F+4", "F:c4:+4", "g-c4's first silent plus 4"), ("c7-F+16", "F:c4:+16", "g-c4's first silent plus 16")]
    for n, P, role in cells:
        _dpm(rows, preds, n, "heldout", P, ["obs:c7", "fit:c7"], cmd, f"--tri-full at 2048x2048: {role} (runner-picked from g-c4)")
        preds.append((n, "raise_rule", "raise iff thr0 <= g-c4's last raise", "H-target (the limit follows the target: g-c4's flip)", "heldout"))
        preds.append((n, "raise_rule", "any other flip", "H-scene (the limit follows the scene)", "heldout"))
    for i in range(1, 5):
        n = f"c7-b{i}"
        _dpm(rows, preds, n, "heldout", "B:c7", ["obs:c7", "fit:c7"], cmd, f"bisect cell {i} of 4 (midpoint of the kept observations of c7)")
        preds.append((n, "raise_rule", "raise iff thr0 <= g-c4's last raise", "H-target (the limit follows the target: g-c4's flip)", "heldout"))
    head = """g-c7 (Q210): another scene, LAST, hang-recovery class.  `--tri-full --vertices 1500` at 2048x2048: the triangle covers the target.  The only
stage that tells scene from target (the 1350-vertex scene is a prefix of the 1500 one, so E774's HP1 does not).  The calibration at P
0x422 is the gate: more than 3 partial renders and the stage ends after one job (E630 and E706 saw `job hung` in long partial-render
sequences).  Otherwise: cells at g-c4's flip pair (last raise L, first silent F) and four around it (L - 16, L - 4, F + 4, F + 16),
then up to four bisect cells picked by the runner.  H-target: the flip of g-c4; H-scene: another.  Cells with 2 thr0 above the
scene's own page need are skipped as void by construction.  The controls are g-c4's."""
    return order(rows), preds, [GREEN], head
