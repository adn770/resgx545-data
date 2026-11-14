# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current, its byte copies are the pinned files, every input
it reads is pinned, and the premises each stage rests on hold on the pinned data:

  engine  guard.cover is R2.decide row by row; guard's clip with a box is r13-isp's clip4 (c6's
          engine) on E1023's 24 rows at every value of their families, and H-VP (a quarter of the
          target past each edge on those rows) draws all 24 kept images (r13-isp's post hoc QUARTER)
  shapes  every target's library macrotile words take whole 4-tile blocks (fx and fy 0 mod 4,
          where H-EVEN is R7-BLK: Q139), and each shape has a kept job that ran ok
  g14     every rival (H-TGT, H-MAX4, H-MIN4, H-ABS, H-EXACT) parts from H-VP on some held-out
          row; every designed row parts H-VP's bound from its listed values (in some row of its
          name) and its image depends on its own bound only; the vp rows' window vertices
  clipr   the tie rows: the clip vertex on x = 80 at (n + 1/2)/256, the float32 clip-space
          intersection exact, the four rules parting as the parity and sign say, decisive pixels
          outside E943's band; the 4096 x 16 rows: V inside H-VP's guard and outside H-MIN4's, on a
          1/512 tie, as submitted exactly, decisive pixels outside E943's band; w4-f parts 5120
  wind    E977's kept dump is the ramp's plane within 2^-23 (the tolerance's premise), E998's
          bit 15 dump the background in every tile dword, no z row's centre within 0.003 of 0 or 1,
          and the z models part on both z rows"""
import gzip
import hashlib
import os
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
import rows as RW  # noqa: E402
import wind as WD  # noqa: E402

F = G.F
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R13 = "data:render/closing-r13-isp/"


def table(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, _, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, args=args, a=args.split()))
    return out


def opt(r, o):
    return r["a"][r["a"].index(o) + 1]


_ROWS = {}


def rowlist(stage):
    if stage not in _ROWS:
        _ROWS[stage] = RW.g14_rows() if stage == "g14" else RW.clipr_rows()
    return _ROWS[stage]


def preds(stage, name, W):
    ref = G.bits(open(os.path.join(KP, "predictions", stage, name + ".ref.txt")).read())
    ms = G.diff_parse(open(os.path.join(KP, "predictions", stage, name + ".models.txt")).read(), ref, W)
    p = os.path.join(KP, "predictions", stage, name + ".family.txt")
    fam = G.diff_parse(open(p).read(), ref, W) if os.path.exists(p) else {}
    return ref, ms, fam


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
def test_cover_is_decide():
    import random
    rnd = random.Random(14)
    for k in range(400):
        W, H = rnd.choice([(12, 10), (20, 6), (7, 15)])
        if k % 2:
            V = [(128 + 128 * rnd.randint(-6, 30), 128 + 128 * rnd.randint(-6, 26)) for _ in range(3)]
        else:
            V = [(rnd.randint(-2000, 8000), rnd.randint(-2000, 8000)) for _ in range(3)]
        P = G.oriented(V)
        if P is None:
            continue
        for Q in (P, G.clip(V, (F(1), F(9), F(-1), F(5)), "HU")):
            if len(Q) < 3:                      # clipped away: cover draws nothing (decide's [] is vacuous)
                assert not any(G.cover(Q, W, H))
                continue
            assert G.cover(Q, W, H) == [R2.decide(None, Q, 256 * x + 128, 256 * y + 128)
                                        for y in range(H) for x in range(W)]


def r13_rows():
    for st in ("q261", "far"):
        for ln in pins.blob(R13 + "tables/%s.txt" % st).decode().splitlines():
            if ln and not ln.startswith("#"):
                name, s, _, _, _, args = ln.split("|", 5)
                a = args.split()
                w = int(a[a.index("--width") + 1])
                yield st, name, s, w, int(a[a.index("--tri-unit") + 1]), [int(t) for t in a[a.index("--tri-v") + 1].split(",")]


def test_engine_is_r13s_clip_on_e1023s_rows():
    import clip as C
    n = 0
    for st, name, s, w, unit, vt in r13_rows():
        V3 = [(vt[0], vt[1]), (vt[2], vt[3]), (vt[4], vt[5])]
        side = C.side_of([(F(x, 256), F(y, 256)) for x, y in C.variants(V3, unit, w)[0]])
        exact, fams = C.predict(V3, unit, w, side, w == 128)
        vp = G.default_vp(w, w)
        assert G.predict(vt, unit, w, w, vp, None, rin="HU") == exact, name
        for lab, img in fams[::3]:
            k, v = lab.split("=")
            b = C.bounds("abs" if k == "h" else side, int(v), w)
            assert G.predict(vt, unit, w, w, vp, tuple(F(x) for x in b), rin="HU") == img, (name, lab)
        n += 1
    assert n == 24


def test_vp_draws_e1023s_24_kept_rows():
    assert "QUARTER: 24 of 24 rows" in pins.blob(R13 + "fold/posthoc_bounds.out").decode()
    n = 0
    for st, name, s, w, unit, vt in r13_rows():
        txt = gzip.decompress(pins.blob(R13 + "out/20261113-215416/%s/%s.txt.gz" % (st, name))).decode()
        got = [v == 0xFF00FF00 for v in pins.pixels(txt, w * w)]
        vp = G.default_vp(w, w)
        assert G.agree(got, G.predict(vt, unit, w, w, vp, G.boxes(w, w, vp)["H-VP"])), name
        n += 1
    assert n == 24


# ---------------------------------------------------------------- shapes
def tiling(width, height):
    """libsgxfive render.c sgxfive_tiling (a581c06): n, mx, my"""
    tx, ty = (width + 31) // 32, (height + 15) // 16
    n = 4 if width * height >= 640 * 480 else 2
    return n, ((tx + n - 1) // n + 3) & ~3, ((ty + n - 1) // n + 3) & ~3


def kept_ok_shapes():
    out = set()
    for pin in ("data:render/closing-r7-geo/out/20261112-211113/zf/cases.tsv",
                "data:render/closing-r10-geo/out/20261113-103256/q139c/cases.tsv"):
        for ln in pins.blob(pin).decode().splitlines()[1:]:
            f = ln.split("\t")
            a = f[6].split()
            if f[8] == "ok" and "--width" in a and not any(t.startswith("--kpoke") for t in a):
                out.add((int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])))
    for st, name, s, w, unit, vt in r13_rows():
        out.add((w, w))
    txt = gzip.decompress(pins.blob(WD.E977 + ".txt.gz")).decode()
    if "\njob: ok\n" in txt:
        out.add((80, 40))
    return out


def test_every_shape_takes_whole_blocks_and_ran_ok():
    ok = kept_ok_shapes()
    for s in ("wind", "g14", "clipr"):
        for r in table(s):
            w, h = int(opt(r, "--width")), int(opt(r, "--height"))
            n, mx, my = tiling(w, h)
            assert mx % 4 == 0 and my % 4 == 0 and n == 2, (w, h)
            assert (w, h) in ok, (w, h)


# ---------------------------------------------------------------- g14
def test_g14_every_rival_parts_from_vp_somewhere():
    parted = set()
    for r in table("g14"):
        if r["set"] == "control":
            continue
        W = int(opt(r, "--width"))
        ref, ms, fam = preds("g14", r["name"], W)
        for m, img in ms.items():
            if any(a is not None and b is not None and a != b for a, b in zip(img, ms["H-VP"])):
                parted.add(m)
    assert parted == {"H-TGT", "H-MAX4", "H-MIN4", "H-ABS", "H-EXACT"}


def test_g14_rows_part_their_values_and_depend_on_their_bound_only():
    covered = {}
    for r in rowlist("g14"):
        if r["set"] == "control" or not r["parts"]:
            continue
        W, H, vp, side = r["W"], r["H"], r["vp"], r["side"]
        base = G.boxes(W, H, vp)["H-VP"]
        vpval = base[G.SIDES[side]]
        V = G.variants(r["vt"], r["unit"], W, H, vp)
        assert len(V) == 1, r["name"]
        V = V[0]
        img = {p: G.image(V, G.with_bound(base, side, F(p)), W, H) for p in set(r["parts"]) | {vpval}}
        key = r["name"].rsplit("-", 1)[0] if r["name"][-2] == "-" and r["name"][-1].isdigit() else r["name"]
        covered.setdefault(key, set())
        covered[key] |= {p for p in r["parts"] if img[p] != img[vpval]}
        for s, vals in RW.others(W, H, vp, side).items():
            for v in vals:
                assert G.image(V, G.with_bound(G.with_bound(base, side, vpval), s, v), W, H) == img[vpval], (r["name"], s, v)
    for name, W, H, side, n, parts, seed in RW.G14:
        vpval = G.boxes(W, H, G.default_vp(W, H))["H-VP"][G.SIDES[side]]
        assert covered[name] == {F(p) for p in parts} - {vpval}, name
    vp = [r for r in rowlist("g14") if r["pokes"]]
    assert covered["g14-vp128-px"] == {F(80)}
    for r in vp[:2]:          # the 64 x 64 viewport at the origin: window = the tool's pixel / 2
        win = G.windows(r["vt"], r["unit"], 128, 128, r["vp"])
        assert win[:2] == [tuple(p) for p in RW.NEAR[r["side"]]]


def test_vp_rows_part_vp_from_tgt_by_thousands_of_pixels():
    for name in ("g14-vp64-px", "g14-vp64-py"):
        ref, ms, fam = preds("g14", name, 128)
        d = sum(1 for a, b in zip(ms["H-VP"], ms["H-TGT"]) if a != b)
        assert d > 2000, (name, d)
        col = [i % 128 for i, v in enumerate(ms["H-VP"]) if v] if name.endswith("px") else \
            [i // 128 for i, v in enumerate(ms["H-VP"]) if v]
        assert max(col) == 79                       # H-VP: nothing past window 80


# ---------------------------------------------------------------- clipr
def test_tie_rows():
    sig = {}
    for r in rowlist("clipr"):
        if r["kind"] != "tie":
            continue
        V = G.variants(r["vt"], r["unit"], 64, 64, r["vp"])
        assert len(V) == 1
        V = V[0]
        n = r["tie"]
        P1, Vf = V[0], V[2]
        t = F(80 * 256 - P1[0], Vf[0] - P1[0])
        assert P1[1] + t * (Vf[1] - P1[1]) == F(2 * n + 1, 2)          # the tie, exactly
        p = (F(P1[0], 256), F(P1[1], 256))
        q = (F(Vf[0], 256), F(Vf[1], 256))
        assert G.clip_f32(p, q, 0, 1.5, (32, 32), (32, 32)) == (F(80), F(2 * n + 1, 512))
        y2 = V[1][1] + t * (Vf[1] - V[1][1])
        assert y2.denominator == 1                                     # the other clip on the grid
        assert -16 * 256 < min(v[1] for v in V) and max(v[1] for v in V) < 80 * 256   # inside the y guard
        polys = RW.tie_polys(V)
        imgs = {k: G.cover(P, 64, 64) for k, P in polys.items()}
        want = RW.tie_classes(n, 1 if n >= 0 else -1)
        for a in RW.RULES:
            for b in RW.RULES:
                assert (imgs[a] == imgs[b]) == (want[a] == want[b])
        dec = 0
        for k in RW.RULES[1:]:
            for j in range(4096):
                if imgs[k][j] != imgs["HU"][j]:
                    d = min(G.dist(polys["HU"], j % 64, j // 64), G.dist(polys[k], j % 64, j // 64))
                    assert d >= 2.5e-4
                    dec += d >= 6.4e-4
        assert dec >= 2
        for k in RW.RULES:
            sig.setdefault(k, []).append(imgs[k] == imgs["HU"])
    assert len({tuple(v) for v in sig.values()}) == 4                     # the four rules apart


def test_w4_rows():
    rs = {r["name"]: r for r in rowlist("clipr")}
    sig = {}
    for name in ("clipr-w4-d", "clipr-w4-e"):
        r = rs[name]
        W, H, vp = 4096, 16, r["vp"]
        win = G.windows(r["vt"], r["unit"], W, H, vp)
        assert len(G.variants(r["vt"], r["unit"], W, H, vp)) == 1
        x, y = win[2]
        assert -1024 < x < 5120 and not -4 <= x <= 4100                   # inside H-VP, outside H-MIN4
        assert (y * 512).denominator == 1 and (y * 512) % 2 == 1          # on a 1/512 tie
        assert -4 < y < 20
        for p in win[:2]:
            assert (p[0] * 256).denominator == (p[1] * 256).denominator == 1
        box = G.boxes(W, H, vp)["H-VP"]
        polys = {k: G.clip(G.variants(r["vt"], r["unit"], W, H, vp, k)[0], box) for k in ("E607", "HU", "RNE", "TR")}
        imgs = {k: G.cover(P, W, H) for k, P in polys.items()}
        good = 0
        for k in ("HU", "RNE", "TR"):
            for j in range(W * H):
                if imgs[k][j] != imgs["E607"][j]:
                    good += min(G.dist(polys["E607"], j % W, j // W), G.dist(polys[k], j % W, j // W)) >= 6.4e-4
        assert good >= 10, (name, good)
        for k in imgs:
            sig.setdefault(k, []).append(imgs[k] == imgs["E607"])
    assert len({tuple(v) for v in sig.values()}) == 4
    ref, ms, fam = preds("clipr", "clipr-w4-f", 4096)
    assert fam["5120"] != fam["4100"] and fam["5120"] != fam["4115"]


# ---------------------------------------------------------------- wind
def test_e977_dump_is_the_plane_and_e998s_the_background():
    b = gzip.decompress(pins.blob(WD.E977 + ".depth.1.bin.gz"))
    w = struct.unpack("<%dI" % (len(b) // 4), b)
    m = WD.zmodel([1.0, 0.0, 1.0], "H-CLAMP")
    assert WD.zcheck(m, list(w), m["drawn"])
    assert all(m["drawn"])
    for i, (k, v) in m["dwords"].items():
        if k == "near":
            f = struct.unpack("<f", struct.pack("<I", w[i]))[0]
            assert abs(f - v) <= 2.0 ** -23
    b = gzip.decompress(pins.blob(WD.E998 + ".depth.1.bin.gz"))
    w = struct.unpack("<%dI" % (len(b) // 4), b)
    assert all(w[WD.store_dword(x, y)] == WD.ONE for x in range(96) for y in range(48))
    assert WD.HASH_RAMP in gzip.decompress(pins.blob(WD.E977 + ".txt.gz")).decode()
    assert WD.HASH_BG in gzip.decompress(pins.blob(WD.E998 + ".txt.gz")).decode()
    assert WD.HASH_RAMP in gzip.decompress(pins.blob("data:render/closing-r10-x/out/20261113-101116/isp0x/x-ctl.txt.gz")).decode()


def test_z_rows_part_the_models_away_from_0_and_1():
    for r in WD.ROWS:
        if r[5] != "z":
            continue
        d = WD.fwd_depths(r)
        for y in range(48):
            for x in range(96):
                if WD.inside(x, y):
                    z = WD.plane(d, x, y)
                    assert abs(z) > 0.003 and abs(z - 1) > 0.003
        ms = {m: WD.zmodel(d, m) for m in WD.ZMODELS}
        texts = {m: WD.ztext(v) for m, v in ms.items()}
        assert len({texts["H-CLAMP"], texts["H-ZCLIP"], texts["H-RAW"]}) == 3
        assert sum(ms["H-ZCLIP"]["drawn"]) < 3200 == sum(ms["H-CLAMP"]["drawn"])
