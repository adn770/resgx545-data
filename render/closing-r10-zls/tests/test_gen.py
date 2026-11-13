# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r10-zls's generator is current; every row carries the flags its premise
needs (E934) and nothing it must not; the rivals of each stage part on its rows; the layouts are
E465/E490's (sgx-pipe zls.rs, pinned); E985's frozen rules file is the one zst2.py codes; every
repository file the session reads is pinned; t9's recipe is the bound one."""
import gzip
import hashlib
import os
import re
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import zbg as B  # noqa: E402
import zst2 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
X978 = "data:render/closing-r9-x/out/20261113-081821/zst/"


def rows(st):
    return [ln.rstrip("\n").split("|", 5) for ln in open(os.path.join(KP, f"tables/{st}.txt"))
            if ln.strip() and not ln.startswith("#")]


def opts(args):
    a = args.split()
    o = {}
    for i, x in enumerate(a):
        if x.startswith("--"):
            o.setdefault(x, []).append(a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith("--")
                                       else True)
    return o


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["zst2", "zbgc", "zbg", "zw"]
    assert CFG["stages"]["zbg"].get("gate") and not CFG["stages"]["zst2"].get("gate")
    assert [len(rows(s)) for s in CFG["stages"]] == [26, 2, 7, 4]
    for s in CFG["stages"]:
        head = open(os.path.join(KP, f"tables/{s}.txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]          # safe class: no expected fault
        for name, st, risk, knobs, tool, args in rows(s):
            assert risk == "safe" and "expectdiff" in knobs.split()
            assert not any(w.startswith(("dbg:", "expectfault", "expect:")) for w in knobs.split())
            assert (st == "control") == ("reads:depth_changed" in knobs)
            assert tool == ("t4" if s == "zst2" else "t9")


def test_zst2_rows_premises():
    planes = {}
    for name, st, risk, knobs, tool, args in rows("zst2"):
        o = opts(args)
        p, fmt = Z.plane_of(name), Z.fmt_of(name)
        w, h = Z.PLANES[p][:2]
        tx, ty = Z.tiles(w, h)
        ctl = int(o["--depth-ctl"][0], 16)
        assert ctl & 0x00171004 == 0x00171004 and (ctl >> 3 & 0x1FF) == tx - 1   # E466's store, G
        assert ctl >> 24 & 7 == fmt and not ctl & 1 << 19
        assert ctl & 0x6002 == 0x2002                                            # stencil load only
        assert o["--depth"] == [True] and o["--stencil"] == [True] and o["--stencil-store"] == [True]
        assert o["--depth-dump"] == ['"$W"'] and o["--poke"] == ["blk:1=0x00400200"]
        assert int(o["--width"][0]) == w and int(o["--height"][0]) == h
        assert "--kpoke-render" not in o and "--isp2" not in o
        fill = o["--stencil-fill"][0]
        assert fill == "index" or fill in Z.FILLS.values()
        assert (fill != "index") == (len(name.split("-")) == 3)
        planes.setdefault(p, set()).add(fmt)
        if p == "e":
            pages = int(o["--depth-pages"][0])
            # the whole-tile extent of every buffer: f3's last block, f0's tiles, the stencil
            ext = max((max(Z.block(x, y, tx) for x in range(tx) for y in range(ty)) + 1) * 2560,
                      512 * 4 * tx * ty, 128 * 4 * tx * ty)
            assert pages * 4096 >= ext and pages >= -(-w * h * 4 // 4096)
        else:
            assert "--depth-pages" not in o
        if "--tri-v" in o:
            assert o["--tri-v"] == ["0,0,%d,0,0,%d" % (512 * w, 512 * h)] and "--tri-full" not in o
            assert o["--tri-z"] == ["0,1,1"]
    assert planes == {"x": {0, 3, 4, 7}, "y": {0, 3, 4, 5, 6, 7}, "d": {0, 3, 4, 5, 6, 7},
                      "e": {0, 3, 6}}
    # the x plane is E978's own rows: z120-ctl-s and z120-f4-s replicated
    r = {n: a for n, _, _, _, _, a in rows("zst2")}
    e978 = {ln.split("|")[0]: ln.split("|")[5] for ln in pins.blob(
        "data:render/closing-r9-x/tables/zst.txt").decode().splitlines()
        if ln.strip() and not ln.startswith("#")}
    assert r["z2x-f0"] == e978["z120-ctl-s"] and r["z2x-f4"] == e978["z120-f4-s"]


def test_d_plane_spans_0_to_1():
    zs = [(x + 0.5) / 128 + (y + 0.5) / 64 for y in range(32) for x in range(64)]
    assert min(zs) < 0.02 and 0.98 < max(zs) < 1


def test_bg_rows_premises():
    for s in ("zbgc", "zbg"):
        for name, st, risk, knobs, tool, args in rows(s):
            o = opts(args)
            ctl = int(o["--depth-ctl"][0], 16)
            assert ctl & 0x00171004 == 0x00171004 and (ctl >> 3 & 0x1FF) == 7
            assert not ctl & 0x6002                                              # no load
            assert bool(ctl & 1 << 19) == name.endswith("-b19")
            assert ctl >> 24 & 7 == (0 if s == "zbgc" else int(name.split("-f")[1][0]))
            assert len(o["--kpoke-render"]) == 1 and o["--kpoke-render"][0].startswith("1:rd:16=0x")
            assert o["--poke"] == ["blk:1=0x00400200"] and "--stencil" not in o
            v = int(o["--kpoke-render"][0].split("=")[1], 16)
            assert v == (B.CONTROLS[name] if s == "zbgc" else B.NEGZ if "-z-" in name else B.NEG)
    for name, st, risk, knobs, tool, args in rows("zw"):
        o = opts(args)
        assert "--kpoke-render" not in o and o["--tri-z"] == ["0,1,0"]
        assert o["--poke"][0] == "blk:1=0x00400200" and o["--poke"][1].startswith("blk:10=")
        assert int(o["--depth-ctl"][0], 16) == 0x0017103c
    # zw-c50 is E977's z242-a-f0 with word 10 made explicit
    e977 = {ln.split("|")[0]: ln.split("|")[5] for ln in pins.blob(
        "data:render/closing-r9-x/tables/zls.txt").decode().splitlines()
        if ln.strip() and not ln.startswith("#")}
    c50 = [a for n, _, _, _, _, a in rows("zw") if n == "zw-c50"][0]
    assert c50 == e977["z242-a-f0"] + " --poke blk:10=0x3f000000"


def test_bg_rivals_part():
    """every pair of -0.25 models differs on some zbg row"""
    ms = B.BG_MODELS
    for i, a in enumerate(ms):
        for b in ms[i + 1:]:
            assert any(B.bg_value(a, f, x, B.NEG) != B.bg_value(b, f, x, B.NEG)
                       for f in (0, 1, 2) for x in (False, True)), (a, b)
    assert len(B.bg_dwords(0)) > 0.7 * B.W * B.H and len(B.bg_dwords(2)) > 0.35 * B.W * B.H
    assert not any(B.is_tri(x, y) for d in B.bg_dwords(2).values() for x, y in d)


def test_w10_rivals_part():
    for w in (0.75, 1.0, 0.125):
        for i, a in enumerate(B.W10_MODELS):
            for b in B.W10_MODELS[i + 1:]:
                assert sum(not B.w10_at(B.w10_z(a, w, x), B.w10_z(b, w, x))
                           for x, y in B.w10_pixels()) > 1000, (w, a, b)


def ld(pin):
    return pins.blob(pin)


def test_w10_models_on_the_two_kept_points():
    """the tolerance and mask on E977 (w 0.5) and E981's ramp a (w 0.25): H-LIN and H-HYP hold
    (both go through them), H-OFF fails at 0.25 (E981)"""
    for pin, w, want in (("data:render/closing-r9-x/out/20261113-081821/zls/z242-a-f0.depth.1.bin.gz",
                          0.5, {"H-LIN": True, "H-HYP": True, "H-OFF": True}),
                         ("data:render/closing-r9-z2/out/20261113-082522/z2/z2-a-f0.depth.1.bin.gz",
                          0.25, {"H-LIN": True, "H-HYP": True, "H-OFF": False})):
        b = ld(pin)
        z = struct.unpack("<%dI" % (len(b) // 4), b)
        for m, held in want.items():
            ok = all(B.w10_at(B.fbits(z[B.f0_index(x, y)]), B.w10_z(m, w, x)) for x, y in B.w10_pixels())
            assert ok == held, (pin, m)


def test_zst2_rivals_part_on_e978():
    ref = struct.unpack("<18432I", ld(X978 + "z120-ctl-s.depth.1.bin.gz"))
    sten = ld(X978 + "z120-f3-s.stencil.1.bin.gz")
    for fmt in (3, 4):
        p = {m: Z.predict(fmt, m, ref, sten, 64, 32) for m in Z.models(fmt, "index")}
        assert p["H-E985"] != p["H-E985/H-RASTER"] and p["H-E985"] != p["H-E985/H-F2ORD"]
    assert Z.predict(6, "H-E985", ref, sten, 64, 32) != Z.predict(6, "H-F6ITI", ref, sten, 64, 32)


def test_e985_rules_frozen():
    """zst2.py codes closing10/seeds/q120/frozen_rules.md (E985's hash), and its code is the
    offline scorer's (q120_score.py) where that file is present"""
    p = os.path.join(KP, "..", "seeds", "q120", "frozen_rules.md")
    if os.path.exists(p):
        assert hashlib.sha256(open(p, "rb").read()).hexdigest() == Z.FROZEN_RULES_SHA


def test_layouts():
    assert sorted(Z.in_tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))
    assert sorted(B.in_tile_index16(x, y) for y in range(0, 16, 2) for x in range(32)) == list(range(256))
    assert sorted(Z.block(x, y, 3) for y in range(3) for x in range(3)) == [0, 1, 2, 3, 4, 5, 6, 8, 10]
    rs = pins.blob("resgx545:crates/sgx-pipe/src/zls.rs").decode()
    assert "fn in_tile_order_is_y0_x0_y1_x1_y2_x2_y3_x3_x4" in rs and "pub fn in_tile_index16" in rs


def test_every_read_is_pinned():
    src = "".join(open(os.path.join(KP, f)).read() for f in
                  ("score/score.py", "gen/zbg.py", "gen/zst2.py", "tests/test_score.py",
                   "tests/test_gen.py"))
    pinned = set(CFG["freeze"]["pins"])
    for m in re.findall(r'"(render/closing-r9-[^"]+)"', src):
        assert "data:" + m in pinned, m
    for m in re.findall(r'"data:(render/closing-r9-[^"]+)"', src):
        assert "data:" + m in pinned or m.endswith("/"), m


def test_recipe_is_bound():
    t = CFG["tools"]["t9"]
    assert t["recipe"] == "data:render/closing-r9-k1/lead/build_tool9.sh"
    src = open(os.path.join(KP, "lead/build_tool9.sh"), "rb").read()
    assert src == pins.blob(t["recipe"])
    assert f"SRCSHA={t['built_sha256']}".encode() in src
    assert b"COMMIT=97447b04b38cadac7733f0cd12503e2ef207a3bf" in src
    assert CFG["tools"]["t4"]["source"].startswith("4623753f2cc5b9a34b357736801a4c6e66138bf9:")
