# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator current, its inputs pinned, and its models replayed on the
kept records they must hold on and fail on:

- chain: gen/chain.py's model reproduces the pinned texmodel.py (E562's sampler model) on every
  tx-shapes and tx-fields spec whose short side is at most 16 (where E561's tile law is plain
  Morton) under A, B and D, and E562's kept images under A (B and D miss the two controls); the
  controls' programs are E562's published ones, rebuilt byte for byte by gen/prog.py; every
  coordinate of every held-out row is exact in float32 and more than 1/128 texel from a texel edge
  at every level (E562's windows came to 1/128 at 128 x 16's level 6); the tested form parts from each rival on every row; every model's farthest read is
  inside the 16 mapped pages (D on 256 x 32 is not: README.md "Deviations" 1).
- ty: E1039's name map (c + U) holds on every pixel of r14-tex's three kept mode 4 rows, before the
  freeze; the controls' programs are r14-tex's; the type rows are E567's programs but for T0's u
  mode (16 x 16) or T1's size and the `map` widths (32 x 32); H-AS-U4 and H-MODE0 part on every
  mode 5 to 7 row, NAME-U and NAME-WRAP on the n16 row; the halving is types_post.py's."""
import gzip
import json
import math
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import chain as C  # noqa: E402
import pins  # noqa: E402
import prog  # noqa: E402
import tex  # noqa: E402
import ty as TY  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
TEXMODEL = "data:texture/p1141/support/texmodel.py"
KEPT562 = ("shapes/shp-128x16-l8-x64", "shapes/shp-8x64-l7-y32", "shapes/shp-64x4-l7",
           "shapes/shp-16x32-l6", "shapes/shp-32x32-l3", "fields/fld-128x16-max8",
           "fields/fld-128x16-bias33", "fields/fld-128x16-mf750", "fields/fld-32x16-max3")
R14 = "data:render/closing-r14-tex/out/20261114-054258/addr5/addr5-ty%d-u4.txt.gz"
TYPES_POST = "data:render/closing-r14-tex/fold/types_post.py"
TEST_PINS = {TEXMODEL, TYPES_POST, R14 % 3} | {"data:texture/p1132/tx-%s.txt.gz" % k
                                               for k in KEPT562}


def specs():
    return json.loads(pins.blob(tex.SPECS))


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_input_is_pinned():
    import make
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))
    assert TEST_PINS <= set(CFG["freeze"]["pins"]), sorted(TEST_PINS - set(CFG["freeze"]["pins"]))


# ---- chain ------------------------------------------------------------------------------------
def test_chain_model_is_texmodel_where_the_tile_law_is_morton():
    TM = pins.module(TEXMODEL)
    n = 0
    for name, d in specs().items():
        if d["group"] not in ("shapes", "fields"):
            continue
        sp = d["spec"]
        j = C.spec_job(name, sp)
        if min(j["w"], j["h"]) > 16:
            continue
        for rule in "ABD":
            tm = TM.render(sp, {"chain": rule})
            mine = C.image(j, rule)
            for p, (a, b) in enumerate(zip(mine, tm)):   # texmodel's OOB: past its 16 pages
                assert a == b or (b == TM.OOB and C.pixel(j, rule, p % 64, p // 64)[1] >= 16384), (
                    name, rule, p)
        n += 1
    assert n == 101


def test_chain_model_on_e562_kept():
    for case in [c for _, c in C.CONTROLS] + [k.split("/")[1] for k in KEPT562]:
        group = "fields" if case.startswith("fld") else "shapes"
        j = C.spec_job(case, specs()[case]["spec"])
        kept = pins.kept_pixels(f"data:texture/p1132/tx-{group}/{case}.txt.gz")
        assert C.image(j, "A") == kept, case
    for _, case in C.CONTROLS:
        j = C.spec_job(case, specs()[case]["spec"])
        kept = pins.kept_pixels(C.SHAPES_KEPT % case)
        assert C.image(j, "B") != kept and C.image(j, "D") != kept, case


def test_control_programs_are_e562s():
    for name, case in C.CONTROLS:
        sp = specs()[case]["spec"]
        b = open(os.path.join(KP, "bins", name + ".bin"), "rb").read()
        assert b == pins.blob(C.SHAPES_BIN % specs()[case]["bin"])
        assert tex.assemble(prog.text(C.spec_job(case, sp))) == b
        assert prog.text(C.spec_job(case, sp)) == tex.text(sp)


def exact(q):
    return C.F(C.fbits(C.bits(float(q)))) == q


def test_coordinates_exact_and_off_the_edges():
    for j in C.HELDOUT:
        for y in range(32):
            for x in range(64):
                u, v, lod = (C.coord(j[k], x, y) for k in ("u", "v", "lod"))
                assert exact(u) and exact(v) and exact(lod), (j["name"], x, y)
                assert 0 < u < 1 and 0 < v < 1
                for lw, lh, _ in C.levels(j["w"], j["h"], "A"):
                    for c, n in ((u, lw), (v, lh)):
                        f = c * n - math.floor(c * n)
                        assert n == 1 or C.F(1, 128) < f < C.F(127, 128), (j["name"], x, y)


def test_lod_rows():
    want = {"lw": 0, "lh": C.F(1, 2), "lb": C.F(3, 2)}
    for j in C.HELDOUT:
        tail = j["name"].rsplit("-", 1)[1]
        c = want.get(tail, 0 if tail in ("b33", "max3") else C.F(1, 2))
        assert [C.coord(j["lod"], 0, y) for y in range(0, 32, 4)] == [k + c for k in range(8)]
    text = open(os.path.join(KP, "bins", "chain-1x32-lh.s")).read()
    assert "shr.skipinv r1, pa0, #18" in text and "fmad.skipinv r26, r1, r2, r3" in text


def t_word(name, reg):
    text = open(os.path.join(KP, "bins", name + ".s")).read()
    return int(re.search(rf"mov {reg}, #0x([0-9a-f]+)", text).group(1), 16)


def test_chain_words():
    for j in C.HELDOUT:
        n = j["name"]
        text = open(os.path.join(KP, "bins", n + ".s")).read()
        assert ("smp1dreplace" in text) == n.startswith("chain-1d"), n
        assert t_word(n, "r22") == 0x5CAF0000 and t_word(n, "r23") == C.T3
        t1 = t_word(n, "r21")
        assert (t1 >> 24 & 31) == (9 if n.startswith("chain-h") else 12), n
        assert ((t1 >> 12 & 0xFFF) + 1, (t1 & 0xFFF) + 1) == (j["w"], j["h"])
        assert t1 >> 29 == 0                                  # twiddled
        t0 = t_word(n, "r20")
        assert t0 & 0x1F8 == 0                                 # repeat, point
        if n.endswith("-max3"):
            assert t0 >> 17 & 15 == 3 and t0 >> 21 & 63 == 63
        elif n.endswith("-b33"):
            assert t0 >> 21 & 63 == 0x33 and t0 >> 17 & 15 == 14
        elif n.endswith("-mf"):
            assert t0 == C.T0_MIP | 1 << 9
        else:
            assert t0 == C.T0_MIP
    assert [j["name"] for j in C.HELDOUT][-3:] == ["chain-1d-lw", "chain-1d-lh", "chain-1d-max3"]


def test_rows_part_their_models():
    for j in C.HELDOUT:
        tested = j["models"][0]
        for m in j["models"][1:]:
            if j["name"] == "chain-h32x16-mf" and m in ("A-DW-BL8", "D-TX-BL8"):
                assert C.parts(j, "A-DW-BL8", "D-TX-BL8") == 0   # 32 x 16: one layout
            assert C.parts(j, tested, m) >= 256, (j["name"], m)


def test_reads_inside_the_scratch():
    for j in C.HELDOUT:
        for m in j["models"]:
            assert C.farthest(j, m) < C.PAGES * 1024, (j["name"], m)
    j = [x for x in C.HELDOUT if x["name"] == "chain-256x32-lw"][0]
    assert C.levels(256, 32, "D")[1][2] == 65536 >= 64 * 1024


def test_u16_odd_halves():
    """E1003's kept u16 row reads 0xd000 on odd texels (the high half of a name)."""
    j = [x for x in C.HELDOUT if x["name"] == "chain-h32x16-lw"][0]
    vals = set(C.image(j, "A-TX"))
    assert 0xD000 in vals and all(v < 0x10000 for v in vals)


# ---- ty ---------------------------------------------------------------------------------------
def test_e1039_map_fitted_before_the_freeze():
    for ty in (1, 3, 4):
        px = pins.kept_pixels(R14 % ty)
        for c in (TY.NAME_C[ty], TY.NAME_C[ty] - 256):
            want = [TY.half(0xD0000000 | (c + 16 + (p % 64) % 16)) for p in range(2048)]
            assert px == want, (ty, c)
        assert px != [TY.half(0xD0000000 | (TY.NAME_C[ty] + 1 + 16 + (p % 64) % 16))
                      for p in range(2048)]


def test_halving_is_types_posts():
    src = pins.blob(TYPES_POST).decode()
    assert "return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))" in src


def test_ty_programs():
    b = lambda n: open(os.path.join(KP, "bins", n + ".bin"), "rb").read()  # noqa: E731
    assert b("ty-ty1u4r") == tex.assemble(tex.text(TY.spec(1, 4)))
    assert b("ty-ctl") == pins.blob("data:render/closing-r14-tex/bins/addr5-ctl.bin")
    for ty in (1, 4):
        a = tex.text(TY.spec(ty, 0)).splitlines()
        for m in (5, 6, 7):
            s = open(os.path.join(KP, "bins", f"ty-16-ty{ty}-u{m}.s")).read().splitlines()
            d = [(x, y) for x, y in zip(a, s) if x != y]
            assert len(a) == len(s) and len(d) == 1 and d[0][0].startswith("mov r20, ")
            assert int(d[0][1].split("#")[1], 16) == int(d[0][0].split("#")[1], 16) | m << 6
    for ty in (1, 3, 4):
        t1 = t_word(f"ty-32-ty{ty}-u0", "r21")
        assert t1 >> 29 == ty and (t1 & 0xFFFFFF) == 31 << 12 | 31
        assert t_word(f"ty-32-ty{ty}-u4", "r20") == t_word(f"ty-32-ty{ty}-u0", "r20") | 4 << 6
    n16 = tex.text(TY.spec(1, 4, u=TY.n16_u()))
    assert open(os.path.join(KP, "bins", "ty-16-ty1-n16.s")).read() == n16


def test_n16_coordinates():
    TM = pins.module(TEXMODEL)
    u = TY.n16_u()
    for x in range(64):
        U = TM.ev(u, x, 0) * 16
        assert U == x - 24 + 0.5, x


def test_ty_rows_part():
    jobs = {j[0]: j for j in TY.jobs()}
    for ty in (1, 4):
        for m in (5, 6, 7):
            pix = jobs[f"ty-16-ty{ty}-u{m}"][4]
            assert sum(a != b for a, b in zip(pix["H-AS-U4"], pix["H-MODE0"])) == 2048
    pix = jobs["ty-16-ty1-n16"][4]
    assert sum(a != b for a, b in zip(pix["NAME-U"], pix["NAME-WRAP"])) >= 1024
    for ty in (1, 3, 4):
        pix = jobs[f"ty-32-ty{ty}-u0"][4]
        a, b = list(pix.values())
        assert sum(x != y for x, y in zip(a, b)) >= 1024
        assert max(int(t, 16) & 0x0FFFFFFF for t in a + b) < TY.LIMIT


def test_kept_gz_names():
    for p in TEST_PINS:
        if p.endswith(".gz"):
            assert gzip.decompress(pins.blob(p))
