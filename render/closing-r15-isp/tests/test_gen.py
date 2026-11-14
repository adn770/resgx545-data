# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current, its byte copies are the pinned files, every input it
reads is pinned, and the premises the stage rests on hold on the pinned data:

  engine   zcut.cover_exact is guard.cover on integer polygons; the three forms reproduce E1045's
           two kept depth rows (every target pixel, the count of background dwords, and every
           dword of the band: the model's 4608 dwords of each kept dump, the planes within 2^-20)
  rows     (the plan's engine check) every cut row: every vertex inside H-VP's guard on 80 x 40 and
           an int32 in 1/256 px, a single window variant (the float32 clip coordinates round back to
           the integers), 6 to 20 pixel centres within 1/512 px of the exact cut line, at least 6
           pixels (all determined) where H-POLYCLIP parts from H-POLYCLIP-NR and from H-PIXCUT,
           H-PIXCUT and H-POLYCLIP-NR one image, no pixel undetermined, the depth margin of every
           pixel at least twice H-PIXCUT's 2^-18, the background-dword counts of H-POLYCLIP and
           H-POLYCLIP-NR different; the construction (header of gen/zcut.py): the crossings
           on the pixel-centre lattice within 1/2 unit
  e065     the pinned timeline holds the three jobs the rows replicate (48, 0, 0 triangle pixels,
           their hashes) and the baseline"""
import gzip
import hashlib
import os
import random
import re
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import guard as G  # noqa: E402
import pins  # noqa: E402
import q261_rule2 as R2  # noqa: E402
import zcut as Z  # noqa: E402

F = Z.F
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


# ---------------------------------------------------------------- the generator and its inputs
def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    import make
    for rel, pin in make.COPIES.items():
        assert pin in CFG["freeze"]["pins"]
        assert open(os.path.join(KP, rel), "rb").read() == pins.blob(pin), rel
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_c6_engine_is_the_frozen_one():
    c6 = "data:cited/closing11/plan/c6-q261/"
    want = pins.blob(c6 + "q261_rule2.sha256").decode().split()[0]
    assert hashlib.sha256(pins.blob(c6 + "q261_rule2.py")).hexdigest() == want


# ---------------------------------------------------------------- the engine
def test_cover_exact_is_guard_cover():
    rnd = random.Random(15)
    for k in range(200):
        W, H = rnd.choice([(12, 10), (20, 6), (7, 15)])
        V = [(128 + 128 * rnd.randint(-6, 30), 128 + 128 * rnd.randint(-6, 26)) if k % 2
             else (rnd.randint(-2000, 8000), rnd.randint(-2000, 8000)) for _ in range(3)]
        P = G.oriented(V)
        if P is None:
            continue
        assert Z.cover_exact([(F(x), F(y)) for x, y in P], W, H) == G.cover(P, W, H)


def kept_job(k):
    t = gzip.decompress(pins.blob(Z.E1045 + k + ".txt.gz")).decode()
    dump = gzip.decompress(pins.blob(Z.E1045 + k + ".depth.1.bin.gz"))
    return t, struct.unpack("<%dI" % (len(dump) // 4), dump)


def test_the_forms_reproduce_e1045s_two_kept_rows():
    for name, k, vt, zt in Z.CTL_Z:
        t, words = kept_job(k)
        img = [v == 0xFF00FF00 for v in pins.pixels(t, Z.W * Z.H)]
        flat, d = [int(x) for x in vt.split(",")], [float(x) for x in zt.split(",")]
        for m in Z.MODELS:
            mod = Z.model_of(flat, d, m)
            assert mod["drawn"] == img, (name, m)
            lo, hi = Z.ones_range(mod)
            assert lo == hi == Z.parse_ones(t), (name, m)
            assert Z.parse_ones(t) == sum(1 for i in range(Z.TW * Z.TH) if words[Z.store_dword(i % Z.TW, i // Z.TW)] == Z.ONE)
            assert len(mod["dwords"]) == Z.TW * Z.TH
            for i, (kind, v) in mod["dwords"].items():
                if kind == "eq":
                    assert words[i] == v
                else:
                    f = struct.unpack("<f", struct.pack("<I", words[i]))[0]
                    assert abs(f - v) <= 2.0 ** -20, (name, i)


# ---------------------------------------------------------------- the rows
def row_stats(r):
    flat = Z.row_flat(r)
    d = Z.row_depths(r)
    V = Z.window_variants(flat)
    assert len(V) == 1, "a float32 variant parts: %s" % r[0]
    v = V[0]
    Zs = [Z.f32(z) for z in d]
    O, OZ = Z.oriented_z(v, Zs)
    pl = Z.plane_fn(v, Zs)
    tri = G.cover(O, Z.TW, Z.TH)
    lvl = 1 if r[1] == "hi" else 0
    (x0, y0), (x1, y1), (x2, y2) = v
    det = F((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    gx = ((Zs[1] - Zs[0]) * (y2 - y0) - (Zs[2] - Zs[0]) * (y1 - y0)) / det
    gy = ((Zs[2] - Zs[0]) * (x1 - x0) - (Zs[1] - Zs[0]) * (x2 - x0)) / det
    gn = (float(gx) ** 2 + float(gy) ** 2) ** 0.5
    near, margin = 0, 1.0
    for y in range(Z.H):
        for x in range(Z.W):
            if tri[y * Z.TW + x]:
                z = float(pl(*Z.centre(x, y))) - lvl
                margin = min(margin, abs(z))
                near += abs(z) / gn / 256 <= 1 / 512
    return near, margin, v


def test_every_cut_row_meets_the_plan_s_engine_check():
    ones = {}
    for r in Z.ROWS:
        near, margin, v = row_stats(r)
        assert 6 <= near <= 20, (r[0], near)
        assert margin >= 2 * float(Z.EPS_PIX), (r[0], margin)
        for x, y in v:                                    # inside H-VP's guard, so no guard clip
            assert Z.GUARD[0] * 256 < x < Z.GUARD[1] * 256 and Z.GUARD[2] * 256 < y < Z.GUARD[3] * 256
            assert abs(x) < 2 ** 31 and abs(y) < 2 ** 31
        ims = Z.images(Z.row_flat(r), Z.row_depths(r))
        tgt = [(x, y) for y in range(Z.H) for x in range(Z.W)]

        def part(a, b):
            return [p for p in tgt if ims[a][p[1] * Z.TW + p[0]] != ims[b][p[1] * Z.TW + p[0]]]
        assert not any(ims[m][p[1] * Z.TW + p[0]] is None for m in Z.MODELS for p in tgt), r[0]
        assert len(part("H-POLYCLIP", "H-POLYCLIP-NR")) >= 6, r[0]
        assert len(part("H-POLYCLIP", "H-PIXCUT")) >= 6, r[0]
        assert ims["H-PIXCUT"] == ims["H-POLYCLIP-NR"], r[0]       # one image: the pair no row parts
        ms = {m: Z.model_of(Z.row_flat(r), Z.row_depths(r), m) for m in Z.MODELS}
        ones[r[0]] = {m: Z.ones_range(ms[m]) for m in Z.MODELS}
        assert ones[r[0]]["H-POLYCLIP"] != ones[r[0]]["H-POLYCLIP-NR"], r[0]
        assert sum(1 for v in ms["H-POLYCLIP-NR"]["drawn"] if v) >= 500                   # a real image
    assert len({r[3] for r in Z.ROWS}) == 6


def test_the_cut_line_is_built_on_the_centre_lattice():
    """each row's crossings: on the edge from the apex v0 to v_i at 1/m_i of the way, m_i an integer 2 to 5
    (the depth a_i = 1.25 - m_i/4 at the cut 1, (m_i - 1)/4 at the cut 0 for the apex -0.25), and
    within 1/2 unit of a pixel centre on the lattice line"""
    for r in Z.ROWS:
        name, apex, order, V, d = r
        for i in (1, 2):
            a = F(d[i]).limit_denominator(64)
            m = (F(5, 4) - a) * 4 if apex == "hi" else a * 4 + 1
            assert m.denominator == 1 and 2 <= m <= 5, (name, i, m)
            c = [F(V[0][k]) + (F(V[i][k]) - V[0][k]) / m for k in (0, 1)]
            # the crossing within 1/2 unit of a centre (256 X + 128, 256 Y + 128) in each coordinate
            for k in (0, 1):
                off = (c[k] - 128) % 256
                assert min(off, 256 - off) <= F(1, 2), (name, i, k, float(off))


# ---------------------------------------------------------------- E065
def e065_cases():
    t = pins.blob(Z.E065).decode()
    out, case = {}, None
    for ln in t.splitlines():
        m = re.match(r"=== case (\S+)$", ln)
        if m:
            case = m.group(1)
        m = re.match(r"target: 64x64 hash (0x[0-9a-f]+)", ln)
        if m and case:
            out.setdefault(case, {})["hash"] = m.group(1)
        m = re.match(r"tri 64x64 #1: (\d+) triangle", ln)
        if m and case:
            out.setdefault(case, {})["drawn"] = int(m.group(1))
    return out


def test_e065_kept_jobs_are_the_rows_predictions():
    c = e065_cases()
    for bit, (n, h) in Z.E065_KEPT.items():
        k = c["blk:1^=0x%x" % bit]
        assert (k["drawn"], k["hash"]) == (n, h)
    assert c["baseline"] == {"hash": "0x99385a04ee01c585", "drawn": 1062}
    assert Z.E065_KEPT[0x8000][0] == 48 and Z.E065_KEPT[0x10000] == Z.E065_KEPT[0x20000]


def test_the_mock_constants_are_the_frozen_kept_readings():
    import importlib.util
    spec = importlib.util.spec_from_file_location("r15i_world", os.path.join(KP, "mock/world.py"))
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    pr = open(os.path.join(KP, "predictions/zcut.tsv")).read().splitlines()
    got = {}
    for ln in pr[1:]:
        f = ln.split("\t")
        got.setdefault(f[0], {})[f[1]] = f[2]
    for name, k, vt, zt in Z.CTL_Z:
        assert W.KEPT[(vt, zt)] == (got[name]["hash"], got[name]["depthline"])
    assert W.E065 == {48: Z.E065_KEPT[0x8000][1], 0: Z.E065_KEPT[0x10000][1], 1062: "0x99385a04ee01c585"}
