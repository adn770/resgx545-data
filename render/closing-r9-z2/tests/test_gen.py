# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r9-z2's generator is current; its rows carry every flag their premise needs
(E934); its rivals separate on each ramp; the layouts are E465/E490's (sgx-pipe zls.rs, pinned);
the recipe in lead/ is the one session.toml names and checks the bound source's hash."""
import os
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import z2 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def rows():
    return [ln.rstrip("\n").split("|", 5) for ln in open(os.path.join(KP, "tables/z2.txt"))
            if ln.strip() and not ln.startswith("#")]


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_rows_premises():
    rs = rows()
    assert len(rs) == 10 and list(CFG["stages"]) == ["z2"]
    for name, st, risk, knobs, tool, args in rs:
        a = args.split()
        o = lambda k: a[a.index(k) + 1]
        assert tool == "t9" and risk == "safe" and "expectdiff" in knobs.split()
        assert (st == "control") == ("reads:depth_changed" in knobs)
        ctl = int(o("--depth-ctl"), 16)
        assert ctl & 0x00171004 == 0x00171004 and (ctl >> 3 & 0x1FF) == 7     # E466's store, G 7
        assert ctl >> 24 & 7 == int(name.split("-f")[1][0])
        assert bool(ctl & 1 << 19) == name.endswith("-b19")
        assert not ctl & 0x6002                                                 # no load
        assert o("--tri-z") == "0,1,0" and o("--depth-dump") == '"$W"'
        pokes = [a[i + 1] for i, x in enumerate(a) if x == "--poke"]
        assert pokes[0] == "blk:1=0x00400200"                                   # less, depth written
        off = struct.unpack("<f", struct.pack("<I", int(pokes[1].split("=")[1], 16)))[0]
        assert pokes[1].startswith("blk:10=") and off == (0.25 if "-a-" in name else -0.25)


def test_depth_range_of_each_ramp():
    """depth = offset + 0.5 (2t - 1), t = (x + 0.5) / 512 at y = 0: ramp a crosses 0, b stays below"""
    for r, lo, hi in (("a", -0.25, 0.25), ("b", -0.75, -0.25)):
        off = 0.25 if r == "a" else -0.25
        d = [off + 0.5 * (2 * (x + 0.5) / 512 - 1) for x in range(256)]
        assert lo < min(d) and max(d) < hi and (min(d) < 0 < max(d)) == (r == "a")


def ramp(off):
    z0 = [0xDEADBEEF] * (512 * 8 * 8)
    for y in range(128):
        for x in range(256):
            z = struct.unpack("<f", struct.pack("<f", off + 0.5 * (2 * (x + 0.5) / 512 - 1)))[0]
            z0[512 * ((y >> 4) * 8 + (x >> 5)) + Z.in_tile_index(x, y)] = \
                struct.unpack("<I", struct.pack("<f", z))[0]
    return z0


def test_rivals_separate():
    """on the geometric ramps every pair of models differs on some dword of the rows that can
    separate them (H-B19 = H-CLAMP without bit 19, = H-ABS with it, by its definition)"""
    for off in (0.25, -0.25):
        z0 = ramp(off)
        for fmt in (1, 2):
            for b19 in (False, True):
                p = {m: Z.predict(z0, fmt, b19, m) for m in Z.MODELS}
                for a in ("H-ABS", "H-CLAMP", "H-WRAP"):
                    for b in ("H-ABS", "H-CLAMP", "H-WRAP"):
                        if a < b:
                            assert p[a] != p[b], (off, fmt, b19, a, b)
                assert p["H-B19"] == (p["H-ABS"] if b19 else p["H-CLAMP"])


def test_positive_half_is_e466s():
    """over z >= 0 all four models store round(z * 0xffffff) (E466/E490, bit 19 or not)"""
    for m in Z.MODELS:
        for b in (False, True):
            for z in (0.0, 0.125, 0.25, 0.3, 0.4166):
                assert Z.rival(m, z, b) == int(z * 16777215 + 0.5)


def test_layouts():
    assert sorted(Z.in_tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))
    assert all(Z.in_tile_pixel(Z.in_tile_index(x, y)) == (x, y) for y in range(16) for x in range(32))
    assert sorted(Z.in_tile_index16(x, y) for y in range(0, 16, 2) for x in range(32)) == list(range(256))
    main = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
    rs = subprocess.run(["git", "-C", main, "show", f"{CFG['freeze']['resgx545']}:crates/sgx-pipe/src/zls.rs"],
                        capture_output=True, text=True, check=True).stdout
    assert "fn in_tile_order_is_y0_x0_y1_x1_y2_x2_y3_x3_x4" in rs and "pub fn in_tile_index16" in rs


def test_recipe_is_bound():
    t = CFG["tools"]["t9"]
    assert t["recipe"] == "data:render/closing-r9-z2/lead/build_tool9.sh"
    src = open(os.path.join(KP, "lead/build_tool9.sh")).read()
    assert t["built_from"] == "97447b04b38cadac7733f0cd12503e2ef207a3bf:userspace/libsgxfive/tools/sgxfive-test.c"
    assert f"SRCSHA={t['built_sha256']}" in src and "COMMIT=97447b04b38cadac7733f0cd12503e2ef207a3bf" in src
