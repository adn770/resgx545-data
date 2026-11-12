#!/usr/bin/env python3
"""score_q291.py: r7-rp stages q291g (the gate row) and q291 (Q291, the attribute band), plan
closing7/a/exp-pixel-r7.md sections 1.2 and 3.3.  Standard library and the session's scorekit only.
The pure model lives here too (the generator, the fake world and the tests import it).

Program: probes/pds/templates/pix_posstore.s (E898, sha256 8a136e52...): every instance stores pa0
at scratch dword 4 s (no .skipinv), and the valid ones pa0, pa1 and 0x7E570000 | g25 at dwords
4 s + 1, + 2, + 3, s = (y mod 16) << 5 | (x mod 32) (E808).  `probe --tri` prints every changed
scratch dword (`probe NAME: scratch +0xOFF 0xVALUE`, no cap) against the fill 0xD0000000 | i.

Readings of an attribute row: valid set = the pixels (tile origin + slot) whose dword 1 changed.
Frozen sets (exact equality): H-BAND (predicted: covered, in the tile area, x + 0.5 < 1.25 W and
y + 0.5 < 1.25 H), H-TARGET (covered, inside W x H), H-TILE (covered, in the tile area).  Coverage
is E606's rule (centre inside the triangle on the 1/256 grid, left and top edges own the tie).
Values: set P (E437's position pair) dword 1 = f32(x + 0.5), dword 2 = f32(y + 0.5) (H-LIN);
set V (E606's vertex pair, no --tri-z: clip z 0) dword 1 within 4 units of 2^-23 of 0, dword 2
within 23 units (E661) of the clip x (x + 0.5) / (W / 2) - 1; dword 3 = 0x7E570000 | (x & 1) |
(y & 1) << 1 everywhere.  Secondary (E111, not gating): dword 0's set = the valid set grown to
2 x 2 quads.  Depth twins (`tri --depth`): rule A's stored set (E831's reader, r3_geo.py).

CLI: score_q291.py STAGE KEPT | gate STAGE KEPT | verdict ATT_DIR.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import hashlib  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shlex  # noqa: E402
import struct  # noqa: E402
from fractions import Fraction  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import scorekit  # noqa: E402

STAGES = ("q291g", "q291")
TILE_W, TILE_H = 32, 16
LANE_TAG = 0x7E570000
BG_COLOUR = 0xFF203040              # the triangle probe's background (sgxfive_tri_default)
SCRATCH_DWORDS = 16384              # 64 KiB (sgxfive-test.c scratch_pages 16)
SLOT_DWORDS = 2048                  # the program's 9-bit mask: 512 slots of 4 dwords
TOL_Z, TOL_X = 4, 23                # E606 clip z, E661 clip x, units of 2^-23 absolute
PROGS = {"q291_pos": "P", "q291_vtx": "V"}
MODELS = ("H-BAND", "H-TARGET", "H-TILE")

# Files read, per stage: the row's stdout; cases.tsv once; the depth twins' dumps by name.
TWINS = ("q291-pz-20x12", "q291-pz-18x12", "q291-pz-24x8", "q291-pz-12x12", "q291-pz-10x6")
REQUIRED = {
    "q291g": (".txt", "cases.tsv"),
    "q291": (".txt", "cases.tsv") + tuple(n + ".depth.1.bin" for n in TWINS),
}


# ---- numbers -------------------------------------------------------------------------------------
def f32(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


def fl(w):
    return struct.unpack("<f", struct.pack("<I", w))[0]


def units(w, want):
    """|value - want| in units of 2^-23 (absolute); a missing, NaN or infinite word is far."""
    if w is None or not math.isfinite(fl(w)):
        return math.inf
    return abs(Fraction(fl(w)) - Fraction(want)) * (1 << 23)


# ---- the row's command ---------------------------------------------------------------------------
def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def parse_row(args):
    """The row's argv (a table's args field) as the model needs it."""
    a = shlex.split(args)
    r = {"cmd": a[0], "W": opt(a, "--width", int), "H": opt(a, "--height", int)}
    r["full"] = "--tri-full" in a
    r["v256"] = [int(v) for v in opt(a, "--tri-v").split(",")] if "--tri-v" in a else None
    if a[0] == "probe":
        slots = dict(s.split("=", 1) for s in (a[i + 1] for i, t in enumerate(a) if t == "--slot"))
        r["pixel"] = os.path.basename(slots.get("pixel", "")).replace(".bin", "")
        r["vtxuse"] = os.path.basename(slots.get("vtxuse", "")).replace(".bin", "") or None
        r["pds"] = os.path.basename(a[-1]).replace(".bin", "")
        r["set"] = PROGS.get(r["pds"])
        r["coords"] = opt(a, "--vtx-coords", int, 0)
        r["kind"] = "store" if r["pixel"] == "pix_posstore" else "image"
    else:
        r["kind"] = "depth" if "--depth" in a else "other"
        r["pages"] = opt(a, "--depth-pages", int)
        r["ctl"] = opt(a, "--depth-ctl")
        r["z"] = opt(a, "--tri-z")
    return r


def vertices256(r):
    if r["v256"]:
        v = r["v256"]
        return [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]
    if r["full"]:      # sgxfive-test.c: (0,0) (3W,0) (0,3H) in 1/16 pixel
        return [(0, 0), (3 * r["W"] * 256, 0), (0, 3 * r["H"] * 256)]
    # sgxfive_tri_default: v64 * 16 * size / 64 in 1/16 pixel (integer division), to 1/256
    v64 = ((8, 8), (56, 20), (20, 56))
    return [(16 * (x * 16 * r["W"] // 64), 16 * (y * 16 * r["H"] // 64)) for x, y in v64]


def covered(v, x, y):
    """E606: the centre (x + 0.5, y + 0.5) inside the triangle (1/256 grid, exact), a sample on an
    edge owned iff the edge of the winding-normalised triangle has dy < 0, or dy = 0 and dx > 0."""
    px, py = 256 * x + 128, 256 * y + 128
    (x0, y0), (x1, y1), (x2, y2) = v
    area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    if area == 0:
        return False
    pts = [v[0], v[1], v[2]] if area > 0 else [v[0], v[2], v[1]]
    for i in range(3):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 3]
        e = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if e < 0:
            return False
        if e == 0:
            dx, dy = bx - ax, by - ay
            if not (dy < 0 or (dy == 0 and dx > 0)):
                return False
    return True


def area_wh(W, H):
    return -(-W // TILE_W) * TILE_W, -(-H // TILE_H) * TILE_H


def in_band(x, y, W, H):
    return 4 * x + 2 < 5 * W and 4 * y + 2 < 5 * H       # x + 0.5 < 1.25 W, likewise y


def model_sets(r):
    """{model: set of (x, y)} for the row's triangle and size."""
    W, H = r["W"], r["H"]
    aw, ah = area_wh(W, H)
    v = vertices256(r)
    cov = {(x, y) for y in range(ah) for x in range(aw) if covered(v, x, y)}
    return {"H-BAND": {p for p in cov if in_band(p[0], p[1], W, H)},
            "H-TARGET": {p for p in cov if p[0] < W and p[1] < H},
            "H-TILE": cov}


def tile_of(r):
    """The one tile the row's covered pixels lie in (the plan's one-tile rule), as its origin."""
    t = {(x // TILE_W, y // TILE_H) for x, y in model_sets(r)["H-TILE"]}
    if len(t) != 1:
        raise ValueError(f"row {r} touches tiles {sorted(t)}: slots would be shared")
    tx, ty = t.pop()
    return tx * TILE_W, ty * TILE_H


def slot(x, y):
    return (y % TILE_H) << 5 | (x % TILE_W)


def lane(x, y):
    return (x & 1) | (y & 1) << 1


def quads(s):
    return {((x & ~1) + i, (y & ~1) + j) for x, y in s for i in (0, 1) for j in (0, 1)}


def set_sha(pts):
    return hashlib.sha256(repr(sorted(pts)).encode()).hexdigest()


def want_values(r, x, y):
    """(dword 1, dword 2) the frozen value rule gives at pixel (x, y): P exact words; V the
    reference values (clip z, clip x) as Fractions."""
    if r["set"] == "P":
        return f32(x + 0.5), f32(y + 0.5)
    return Fraction(0), Fraction(2 * x + 1, r["W"]) - 1


def value_ok(r, x, y, d1, d2):
    w1, w2 = want_values(r, x, y)
    if r["set"] == "P":
        return d1 == w1 and d2 == w2
    return units(d1, w1) <= TOL_Z and units(d2, w2) <= TOL_X


# ---- depth twins (E831's reader: gen/r3_geo.py of closing-r3-geo-c, as r6-misc copied it) --------
DEPTH_BG, DEPTH_FILL = 0x3F800000, 0xDEADBEEF
RULES = {
    "A": lambda v: math.ceil(Fraction(5, 4) * v - Fraction(1, 2)),
    "FLOOR": lambda v: math.floor(Fraction(5, 4) * v),
    "ROUND": lambda v: math.floor(Fraction(5, 4) * v + Fraction(1, 2)),
    "CEIL": lambda v: math.ceil(Fraction(5, 4) * v),
    "RSTRICT": lambda v: math.ceil(Fraction(5, 4) * v - 1),
}


def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def pitch_g(w):
    return max(1, -(-w // TILE_W) - 1)


def depth_ctl(w):
    return 0x171004 | pitch_g(w) << 3


def depth_pages(w, h):
    g = pitch_g(w)
    tw, th = -(-w // TILE_W), -(-h // TILE_H)
    n = (th - 1) * (g + 1) + tw
    return max((w * h * 4 + 4095) // 4096, n // 2) + 16


def dword_index(x, y, w):
    return 512 * ((y // TILE_H) * (pitch_g(w) + 1) + x // TILE_W) + mort(x % TILE_W, y % TILE_H)


def band_set(rule, w, h):
    aw, ah = area_wh(w, h)
    xm, ym = RULES[rule](w), RULES[rule](h)
    return {(x, y) for y in range(ah) for x in range(aw) if x < xm and y < ym}


def stored_set(words, w, h):
    aw, ah = area_wh(w, h)
    st, dead = set(), 0
    for y in range(ah):
        for x in range(aw):
            v = words[dword_index(x, y, w)]
            if v == DEPTH_FILL:
                dead += 1
            elif v != DEPTH_BG:
                st.add((x, y))
    return st, dead


def extent(s):
    return (max(x for x, _ in s) + 1, max(y for _, y in s) + 1) if s else (0, 0)


def depth_reading(words, w, h):
    """{stored, dead, rules: [rule names whose set equals the stored one], A: held}."""
    st, dead = stored_set(words, w, h)
    rules = [k for k in RULES if band_set(k, w, h) == st]
    return {"stored": len(st), "sha": set_sha(st), "extent": extent(st), "dead": dead,
            "rules": rules, "A": st == band_set("A", w, h) and dead == 0}


# ---- kept files ----------------------------------------------------------------------------------
def _open(path):
    if os.path.exists(path):
        return open(path, "rb")
    if os.path.exists(path + ".gz"):
        return gzip.open(path + ".gz", "rb")
    return None


def read_text(kept, name):
    f = _open(os.path.join(kept, name))
    if f is None:
        return None
    with f:
        return f.read().decode(errors="replace")


def read_words(kept, name):
    f = _open(os.path.join(kept, name))
    if f is None:
        return None
    with f:
        b = f.read()
    return list(struct.unpack("<%dI" % (len(b) // 4), b[: len(b) // 4 * 4]))


def cases(kept):
    """Rows of cases.tsv: {name: {set, args, rc, class, tool}} in order."""
    t = read_text(kept, "cases.tsv")
    if t is None:
        return None
    lines = [ln for ln in t.splitlines() if ln.strip() and not ln.startswith("#")]
    head = lines[0].split("\t")
    out = {}
    for ln in lines[1:]:
        d = dict(zip(head, ln.split("\t")))
        out[d["name"]] = d
    return out


def predictions(stage, kp=KP):
    out = {}
    with open(os.path.join(kp, "predictions", stage + ".tsv")) as f:
        next(f)
        for ln in f:
            case, q, v, model, sset = ln.rstrip("\n").split("\t")[:5]
            out.setdefault(case, {})[(q, model)] = v
    return out


SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-f]+) 0x([0-9a-f]{8})$")
ROW = re.compile(r"^probe \S+: row (\d+):((?: [0-9a-f]{8})*)$")


def parse_probe(text):
    """{ok, failed, scratch {dword index: value}, rows {y: [words]}} of a probe's stdout."""
    sc, rows, ok, failed = {}, {}, False, False
    for ln in text.splitlines():
        m = SCR.match(ln)
        if m:
            sc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
            continue
        m = ROW.match(ln)
        if m:
            rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
            continue
        if re.match(r"^probe \S+: failed:", ln):
            failed = True
        if re.match(r"^probe \S+: o0 ", ln):
            ok = True
    return {"ok": ok and not failed, "failed": failed, "scratch": sc, "rows": rows}


def store_reading(r, text):
    """The reading of a pix_posstore row: None when the job gave none (failed, no o0 line)."""
    p = parse_probe(text)
    if not p["ok"]:
        return None
    ox, oy = tile_of(r)
    sc = p["scratch"]
    pix = lambda s: (ox + s % TILE_W, oy + s // TILE_W)  # noqa: E731
    valid = {pix(i // 4) for i in sc if i < SLOT_DWORDS and i % 4 == 1}
    dw0 = {pix(i // 4) for i in sc if i < SLOT_DWORDS and i % 4 == 0}
    outside = sorted(i for i in sc if i >= SLOT_DWORDS)
    bad_val, bad_lane, clamp = [], [], 0
    W, H = r["W"], r["H"]
    for (x, y) in sorted(valid):
        s = slot(x, y)
        d1, d2, d3 = sc.get(4 * s + 1), sc.get(4 * s + 2, 0xD0000000 | (4 * s + 2)), \
            sc.get(4 * s + 3, 0xD0000000 | (4 * s + 3))
        if not value_ok(r, x, y, d1, d2):
            bad_val.append((x, y))
            if r["set"] == "P" and (d1, d2) == (f32(min(x, W - 1) + 0.5), f32(min(y, H - 1) + 0.5)):
                clamp += 1
        if d3 != LANE_TAG | lane(x, y):
            bad_lane.append((x, y))
    ms = model_sets(r)
    target = ms["H-TARGET"]
    miss_target = sorted(target - valid)
    return {"valid": valid, "sha": set_sha(valid), "n": len(valid), "dw0": dw0,
            "outside": outside, "bad_val": bad_val, "bad_lane": bad_lane, "clamp": clamp,
            "intarget_ok": not miss_target and not any(p in target for p in bad_val),
            "miss_target": miss_target,
            "models": [m for m in MODELS if set_sha(ms[m]) == set_sha(valid)]}


def image_reading(r, text):
    """pix_pa0's image: every covered target pixel f32(x + 0.5), the rest the background."""
    p = parse_probe(text)
    if not p["ok"] or len(p["rows"]) != r["H"]:
        return None
    v = vertices256(r)
    wrong = 0
    for y in range(r["H"]):
        row = p["rows"].get(y, [])
        if len(row) != r["W"]:
            return None
        for x in range(r["W"]):
            want = f32(x + 0.5) if covered(v, x, y) else BG_COLOUR
            wrong += row[x] != want
    return {"wrong": wrong, "pixels": r["W"] * r["H"]}


# ---- per-row scoring -----------------------------------------------------------------------------
def row_result(name, row, kept, pred):
    """(state, text, reading): state True / False / None of the row's own test (H-BAND for an
    attribute row, the image for pix_pa0, rule A for a twin)."""
    r = parse_row(row["args"])
    if r["cmd"] == "tri" and r["kind"] == "depth":
        words = read_words(kept, name + ".depth.1.bin")
        if words is None:
            return None, f"{name}: no depth dump: cannot tell", None
        d = depth_reading(words, r["W"], r["H"])
        want = pred.get(("stored_set_sha", "A"))
        held = d["A"] and d["sha"] == want
        return held, (f"{name}: twin {r['W']}x{r['H']} stored {d['stored']} extent {d['extent']} "
                      f"dead {d['dead']} rules {d['rules'] or ['none']}: rule A "
                      f"{'held' if held else 'FAILED'}"), d
    text = read_text(kept, name + ".txt")
    if text is None:
        return None, f"{name}: no output kept: cannot tell", None
    if r["kind"] == "image":
        g = image_reading(r, text)
        if g is None:
            return None, f"{name}: no image (job failed or rows missing): cannot tell", None
        return g["wrong"] == 0, f"{name}: image {g['pixels'] - g['wrong']} of {g['pixels']} " \
            "pixels f32(x + 0.5)", g
    g = store_reading(r, text)
    if g is None:
        return None, f"{name}: the job gave no reading (failed or no o0 line): cannot tell", None
    held = g["sha"] == pred.get(("valid_sha", "H-BAND"))
    rivals = [m for m in MODELS if g["sha"] == pred.get(("valid_sha", m))]
    rule = "H-LIN" if r["set"] == "P" else "E661"
    txt = (f"{name}: valid {g['n']} slots, sets {rivals or ['none']}; values {rule} "
           f"{g['n'] - len(g['bad_val'])} of {g['n']}" +
           (f" ({g['clamp']} clamped to the target)" if g["clamp"] else "") +
           f"; lanes {g['n'] - len(g['bad_lane'])} of {g['n']}; in-target "
           f"{'ok' if g['intarget_ok'] else 'MISS %d' % len(g['miss_target'])}; dword 0 "
           f"{'quads' if g['dw0'] == quads(g['valid']) else 'not the quads (%d)' % len(g['dw0'])}"
           + (f"; {len(g['outside'])} dwords past 8 KiB" if g["outside"] else ""))
    return held, txt, g


def control_state(r, held, g):
    """A control: its set (H-BAND, the frozen 512 or the image), values and lanes."""
    if held is None:
        return None
    if r["kind"] == "image":
        return held
    return bool(held and not g["bad_val"] and not g["bad_lane"] and not g["outside"]
                and g["intarget_ok"])


# ---- stage scores --------------------------------------------------------------------------------
def _premise(stage, kept):
    cs = cases(kept)
    if cs is None:
        return None, ["STOP: premise: cases.tsv not kept"]
    miss = scorekit.missing_files(REQUIRED[stage], kept, list(cs))
    return cs, [f"missing: {m}" for m in miss]


def score(stage, kept):
    if stage not in STAGES:
        raise ValueError(f"score_q291 has no stage {stage}")
    pr = predictions(stage)
    cs, miss = _premise(stage, kept)
    if cs is None:
        return "cannot tell: cases.tsv not kept", miss
    det, controls, ctl_reads = list(miss), {}, {}
    rows = {"P": {}, "V": {}, "fit": {}, "twin": {}}
    models, vals = {}, {"P": {}, "V": {}}
    clamped = 0
    for name, row in cs.items():
        if name not in pr:
            raise ValueError(f"row {name} has no frozen prediction")
        r = parse_row(row["args"])
        held, txt, g = row_result(name, row, kept, pr[name])
        det.append(f"[{row['set']}] {txt}")
        if row["set"] in ("gate", "control"):
            controls[name] = control_state(r, held, g)
            ctl_reads[name] = {"reading": "-" if g is None else "yes"}
        elif row["set"] == "twin":
            rows["twin"][name] = held
        elif row["set"] == "fit":
            rows["fit"][name] = held
        elif row["set"] == "heldout":
            rows[r["set"]][name] = held
            vals[r["set"]][name] = None if g is None else not (g["bad_val"] or g["bad_lane"])
            if g is not None:
                models[name] = [m for m in MODELS if g["sha"] == pr[name].get(("valid_sha", m))]
                clamped += g["clamp"]
    bad_twin = {parse_row(cs[n]["args"])["W"] * 1000 + parse_row(cs[n]["args"])["H"]
                for n, h in rows["twin"].items() if h is False}
    for name, row in cs.items():
        r = parse_row(row["args"])
        if r["cmd"] == "probe" and r["W"] * 1000 + r["H"] in bad_twin:
            det.append(f"{name}: no depth reference (its size's twin is not rule A's set)")
    stops = scorekit.premise_stops({n: ("reading",) for n in controls}, ctl_reads)
    det += stops
    if stage == "q291g":
        st = controls.get("q291-ps-gate-32x16")
        word = {True: "PASS", False: "FAILED", None: "cannot tell"}[st]
        return (f"q291g gate {word}: 512 slots of 32 x 16, each its slot's position and lane "
                f"(E808, E437) -> stage q291 {'runs' if st else 'skipped'}"), det
    claim = "Q291 H-BAND (the attribute band is the depth band, x + 0.5 < 1.25 W, y + 0.5 < 1.25 H)"
    head = scorekit.headline(claim, controls, list(rows["P"].values()))
    tp = scorekit.tally(rows["P"].values())
    tv = scorekit.tally(rows["V"].values())
    tz = scorekit.tally(rows["twin"].values())
    other = {m: sum(1 for n in rows["P"] if models.get(n) and m in models[n]
                    and "H-BAND" not in models[n]) for m in ("H-TARGET", "H-TILE")}
    if stops or any(s is None for s in controls.values()):
        verdict = "cannot tell"
    elif any(s is False for s in controls.values()):
        verdict = "controls FAILED"
    elif tp.decided and tp.failed == 0 and tp.cannot_tell == 0:
        verdict = "H-BAND held"
    elif tp.decided == len(rows["P"]) and any(other[m] == len(rows["P"]) for m in other):
        verdict = [m for m in other if other[m] == len(rows["P"])][0] + " held (the other way)"
    elif tp.decided:
        verdict = "mixed: narrowed"
    else:
        verdict = "cannot tell"
    fit = scorekit.combine(rows["fit"].values())
    lin, e661 = scorekit.tally(vals["P"].values()), scorekit.tally(vals["V"].values())
    word = lambda t: {True: "held", False: "refuted", None: "cannot tell"}[t.verdict()]  # noqa
    summ = (f"Q291 {verdict}: held-out P {tp}; rivals H-TARGET {other['H-TARGET']}, H-TILE "
            f"{other['H-TILE']}; values H-LIN {word(lin)} ({lin}"
            + (f"; {clamped} slots clamped to the target" if clamped else "") +
            f"); fit pair {fit}; vertex pair H-BAND {tv}, values E661 {word(e661)} ({e661}); "
            f"depth twins rule A {tz}; headline: {head}")
    return summ, det


def gate(stage, kept):
    """0 pass, 1 failed, 2 cannot tell (q291g); 0 for q291 (no driver gate)."""
    if stage != "q291g":
        return 0
    cs, miss = _premise(stage, kept)
    if cs is None or miss or "q291-ps-gate-32x16" not in cs:
        return 2
    pr = predictions(stage)
    name = "q291-ps-gate-32x16"
    r = parse_row(cs[name]["args"])
    held, _, g = row_result(name, cs[name], kept, pr[name])
    st = control_state(r, held, g)
    return 2 if st is None else (0 if st else 1)


def verdict(att_dir):
    out = []
    for st in STAGES:
        d = os.path.join(att_dir, st)
        if not os.path.isdir(d):
            out.append(f"SUMMARY: {st}: not run (no kept directory): cannot tell")
            continue
        s, _ = score(st, d)
        out.append(f"SUMMARY: {s}")
    return out


def main(argv):
    if len(argv) == 3 and argv[0] == "gate":
        return gate(argv[1], argv[2])
    if len(argv) == 2 and argv[0] == "verdict":
        for ln in verdict(argv[1]):
            print(ln)
        return 0
    if len(argv) == 2:
        s, det = score(argv[0], argv[1])
        for ln in det:
            print(ln)
        print("SUMMARY: " + s)
        return 0
    print("usage: score_q291.py STAGE KEPT | gate STAGE KEPT | verdict ATT_DIR", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
