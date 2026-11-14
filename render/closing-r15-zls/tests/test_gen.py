# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r15-zls's generator is current, and every row carries the flags its premise
needs (E934; plan section 3 "Per-session premise checks"): the replicated rows are the kept
records' rows byte for byte; every row at a size that is not whole tiles passes --depth-pages
(HACKING "Known tool weaknesses"); the blk:10 pokes are the floats 1.25 and -0.25 and the
reference flip lands on ISP word 0's bits 7:0 (t10's library, render.c at a581c06); E411's sized
rows' buffers cover every rival's extent and E465's pages are E991's; every stage's rows write
its scorer's dump; the rivals part on the rows; tool t10 and its recipe are bound."""
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
import z15 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
T10 = "a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f"


def at_t10(path):
    """a file of resgx545 at t10's source commit (commit-addressed; the tool's own tree)"""
    r = subprocess.run(["git", "-C", pins.MAIN, "show", f"{T10}:{path}"], capture_output=True,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.decode()


def rows(stage):
    return [ln.rstrip("\n").split("|", 5) for ln in open(os.path.join(KP, f"tables/{stage}.txt"))
            if ln.strip() and not ln.startswith("#")]


def all_rows():
    return {r[0]: r for s in CFG["stages"] for r in rows(s)}


def opts(args):
    a = args.split()
    o = {}
    for i, x in enumerate(a):
        if x.startswith("--"):
            o.setdefault(x, []).append(a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith("--")
                                       else True)
    return {k: v[0] if len(v) == 1 else v for k, v in o.items()}


def kept_args(table, name):
    t = pins.blob("data:" + table).decode()
    return [ln.split("|", 5) for ln in t.splitlines() if ln.startswith(name + "|")][0][5]


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["zpass", "zbits3", "zflat2", "zovl"]
    assert CFG["stages"]["zovl"].get("on_stop") == "end"
    assert [len(rows(s)) for s in CFG["stages"]] == [12, 11, 13, 16]
    assert {s: [r[0] for r in rows(s)] for s in CFG["stages"]} == Z.STAGE_ROWS
    for s in CFG["stages"]:
        head = open(os.path.join(KP, f"tables/{s}.txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for name, st, risk, knobs, tool, args in rows(s):
            assert tool == "t10" and risk == "safe" and "expectdiff" in knobs.split()
            assert (st == "control") == any(w.startswith("reads:") for w in knobs.split())
            o = opts(args)
            assert args.startswith("tri ") and o["--depth"] is True and o["--depth-dump"] == '"$W"'
            for bad in ("--kpoke", "--kreg", "--clkgate", "--trc-hazard", "expectfault"):
                assert bad not in args.split() and bad not in knobs.split()
            if s == "zpass":
                assert o["--depth-store"] is True
            if s == "zbits3":
                assert o["--stencil-store"] is True
            if "--isp2" in o:
                assert o["--stencil"] is True and o["--stencil-store"] is True
            # Known tool weaknesses: a size that is not whole tiles passes --depth-pages
            w, h = int(o["--width"]), int(o["--height"])
            if w % 32 or h % 16:
                assert "--depth-pages" in o, name
                tw, th = Z.tiles(w, h)
                g = int(o["--depth-ctl"], 16) >> 3 & 0x1FF
                need = (Z.TILE_DW * ((th - 1) * (g + 1) + tw) * 4 + 4095) // 4096
                assert int(o["--depth-pages"]) >= need, name


def test_replicated_rows_are_kept_rows():
    t = all_rows()
    assert t["zp-c-id"][5] == kept_args("render/closing-r13-zls/tables/zbase.txt", "zb-c-id")
    zb2 = "render/closing-r14-zls/tables/zbits2.txt"
    assert t["zb3-c-base"][5] == kept_args(zb2, "zb2-c-base")
    assert t["zb3-c-base"][5] == kept_args("render/closing-r10-st1/tables/st1.txt", "st1-b0")
    assert t["zb3-c-set"][5] == kept_args(zb2, "zb2-c-set")
    assert t["zb3-c-b23"][5] == kept_args(zb2, "zb2-b23")
    assert t["zb3-c-ref1"][5] == t["zb3-c-base"][5] + " --poke blk:1^=0x1"
    assert t["zb3-b15-r1"][5] == kept_args(zb2, "zb2-b15") + " --poke blk:1^=0x1"
    assert t["zb3-b23-idx"][5] == kept_args(zb2, "zb2-b23").replace("--stencil-fill bytes",
                                                                    "--stencil-fill index")
    e = kept_args("render/closing-r10-st1/tables/st1.txt", "st1-e-b0")
    assert t["zp-e-st"][5] == e.replace("--width 40 --height 20 --max-width 40 --max-height 20",
                                        "--width 34 --height 18 --max-width 34 --max-height 18")
    zf = "render/closing-r14-zls/tables/zflat.txt"
    assert t["zl2-c-flat"][5] == kept_args("render/closing-r13-zls/tables/zfmt.txt", "zf-flat-f6")
    assert t["zl2-c-flat"][5] == kept_args(zf, "zl-c-flat")
    assert t["zl2-c-y6"][5] == kept_args("render/closing-r10-zls/tables/zst2.txt", "z2y-f6")
    assert t["zl2-c-f5"][5] == kept_args(zf, "zl-f5-flat")
    for n, z in Z.REC0_DEPTHS.items():
        assert t[n][5] == t["zl2-c-flat"][5].replace("0.5,0.5,0.5", f"{z},{z},{z}")
    for k, z in Z.TWIN_DEPTHS.items():
        f6 = t["zl2-c-flat"][5].replace("0.5,0.5,0.5", f"{z},{z},{z}")
        assert t[f"zl2-f6-{k}"][5] == f6
        assert t[f"zl2-f0-{k}"][5] == f6.replace("0x0617300e", "0x0017300e")
    zo = "render/closing-r14-zls/tables/zodd.txt"
    assert t["zv-c-ov"][5] == kept_args(zo, "zo-c-ov")
    assert t["zv-c-ov"][5] == kept_args("render/closing-r10-x/tables/zov.txt", "zov-64x32-g0")
    assert t["zv-c-g3"][5] == kept_args(zo, "zo-g3")
    for n in ("zv-b25", "zv-g5", "zv-g9", "zv-g17"):
        c, p = Z.G_CTLS[n]
        assert t[n][5] == t["zv-c-g3"][5].replace("0x0017101c", f"{c:#010x}").replace(
            "--depth-pages 20", f"--depth-pages {p}")
    # the overlap rows: E996's form; their references are kept full-pitch rows of the same form
    zov = "render/closing-r10-x/tables/zov.txt"
    for n, (w, h, g, f, ref, gref) in Z.OV_ROWS.items():
        r_args = kept_args(zov if ref.startswith("zov") else zo, ref)
        assert r_args == Z.zov_args(w, h, gref, 0)
        assert t[n][5] == r_args.replace(f"{Z.zctl(gref):#010x}", f"{Z.zctl(g, f):#010x}") + (
            " --depth-pages 20" if w % 32 or h % 16 else "")
        assert g + 1 < Z.tiles(w, h)[0] and gref + 1 >= Z.tiles(w, h)[0]
    assert Z.macro(640, 480)[0] == 4 and Z.macro(65, 33)[0] == 2


def test_t10_library_premises():
    src = at_t10("userspace/libsgxfive/tools/sgxfive-test.c")
    assert hashlib.sha256(src.encode()).hexdigest() == CFG["tools"]["t10"]["source_sha256"]
    assert 'return i >> f->val & 1 ? 0x3f400000 : 0x3e800000;' in src      # bit:K, z15.fill_at
    assert 'depth_poke("rd:13=0x%llx", (unsigned long long)(ds->addr - base));' in src
    rc = at_t10("userspace/libsgxfive/src/render.c")
    # ISP word 0 (blk:1) holds the stencil reference in bits 7:0 (E284) and is 0x01d00300 with
    # --isp2: the flip blk:1^=0x1 sets the reference to 1; words 10 and 11 the viewport's z (0.5,
    # 0.5) and they move only with --isp2 (no blk:10 row has it)
    assert "blk[i++] = 0x01d00200;\t\t/* isp0 */" in rc and "blk[1] |= 1u << 8;" in rc
    assert rc.count("blk[i++] = sgxfive_f32(0.5f);") == 2
    poke = at_t10("userspace/libsgxfive/src/poke.c")
    assert "p.flip = true;" in poke
    t = all_rows()
    for n in ("zb3-c-ref1", "zb3-b15-r1"):
        assert "--isp2" in t[n][5] and "--poke blk:1^=0x1" in t[n][5]
    for n in ("zv-c-075", "zv-r-hi", *Z.INT_OUT):
        o = opts(t[n][5])
        assert "--isp2" not in o and o["--tri-z"] == "0.5,0.5,0.5" and "--tri-full" in o
        pk = dict(p.split("=") for p in o["--poke"])
        assert pk["blk:1"] == "0x01c00200"                                     # always (E995)
        z = struct.unpack("<f", struct.pack("<I", int(pk["blk:10"], 16)))[0]
        assert z in (1.25, -0.25, 0.75) and -0.5 <= z <= 1.5                    # E287's range


def test_sized_rows_cover_every_extent():
    """E411's arrangement: the store base page 12 (rd:13 0xd000, the depth buffer at base +
    0x1000); E465 puts tile row ty at dword 512 (G + 1) ty from it; each row's buffer holds
    every rival's farthest page, ascending in extent, last in the session"""
    t = all_rows()
    ext = []
    for n in ("zv-c-g3", "zv-b25", "zv-g5", "zv-g9", "zv-g17"):
        o = opts(t[n][5])
        assert o["--kpoke-render"] == "1:rd:13=0xd000" and o["--width"] == o["--height"] == "64"
        pages = int(o["--depth-pages"])
        ctl = int(o["--depth-ctl"], 16)
        g, fmt = ctl >> 3 & 0x1FF, ctl >> 24 & 7
        unit = 256 if fmt == 2 else 512
        last = 12 * 1024 + unit * (3 * (g + 1) + 2)              # past the last tile's dwords
        assert last <= pages * 1024, n
        ext.append(last)
        if n != "zv-c-g3":
            ms = Z.B25_MODELS if n == "zv-b25" else Z.G_MODELS
            assert all(max(Z.g_pages(n, m)) < pages for m in ms)
    assert ext[1:] == sorted(ext[1:]) and Z.STAGE_ROWS["zovl"][-4:] == ["zv-b25", "zv-g5", "zv-g9", "zv-g17"]
    # E991's lists: G 5 depth pages 12 and 15 then 18; G 9 and 17 page 12 then 17 and 21
    assert sorted(Z.g_pages("zv-g5", "H-E465-EXT")) == [12, 15, 18, 21]
    assert sorted(Z.g_pages("zv-g9", "H-E465-EXT"))[:2] == [12, 17]
    assert sorted(Z.g_pages("zv-g17", "H-E465-EXT"))[:2] == [12, 21]


def test_zpass_rows():
    t = all_rows()
    for n, (w, h, ctl, fill, z, test, pages, s, ms) in Z.ZPASS.items():
        o = opts(t[n][5])
        assert int(o["--depth-ctl"], 16) == ctl and o["--depth-fill"] == fill
        assert o["--tri-z"] == f"{z},{z},{z}" and int(o["--depth-pages"]) == pages
        # the load and store over the tiles inside both buffers
        tw, th = Z.tiles(w, h)
        assert Z.TILE_DW * tw * th <= pages * 1024
        # dyadic flat depths (deviation: 0.125, 0.375): the float is exact
        assert float(z) * 1024 == int(float(z) * 1024)
    assert Z.ZPASS["zp-e-dp"][:2] == (34, 18) and Z.ZPASS["zp-c-band"][2] & 0x4002 == 0


def part(models, row_names, pred):
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            assert any(pred(n, a) != pred(n, b) for n in row_names), (a, b)


def test_rivals_part():
    part(Z.EDGE_MODELS, ["zp-e-dp"], Z.pass_predict)
    part(Z.EDGE_MODELS, ["zp-e-st"], lambda n, m: Z.stencil_predict(n, m)[:2])
    part(Z.B19_MODELS, ["zp-19-nv", "zp-19-ls"], Z.pass_predict)
    for n in ("zp-f1", "zp-f2"):
        part(Z.INT_MODELS, [n], Z.pass_predict)
    part(Z.Z_MODELS, ["zp-z75"], Z.pass_predict)
    part(Z.B15_MODELS, ["zb3-b15-r1"], lambda n, m: Z.stencil_predict(n, m)[:2])
    g23 = {b: (b * 7 + 3) & 0xFF for b in range(256)}       # any map that reads the loaded byte
    part(Z.B23_MODELS, ["zb3-b23-idx"], lambda n, m: Z.stencil_predict(n, m, g23)[:2])
    part(Z.PAIR_MODELS, ["zb3-p21-23"], lambda n, m: Z.stencil_predict(n, m)[:2])
    for n in Z.INT_OUT:
        if "125" in n:
            assert Z.int_out_predict(n, "H-INT-SAT") != Z.int_out_predict(n, "H-INT-WRAP")
        else:
            part(Z.INT_OUT_MODELS, [n], Z.int_out_predict)
    part(Z.G_MODELS, ["zv-g5", "zv-g9", "zv-g17"], Z.g_pages)
    part(Z.B25_MODELS, ["zv-b25"], Z.g_pages)
    part(list(Z.OV_MODELS), [(640, 480, 2)], lambda n, m: Z.owners(*n, m))
    assert Z.owners(65, 33, 1, "H-LATE/HDR") != Z.owners(65, 33, 1, "H-EARLY/HDR")
    assert Z.owners(160, 48, 2, "H-LATE/HDR") != Z.owners(160, 48, 2, "H-LATE/RASTER")
    # zflat2: 0.5 + 2^-20 has low bits set and is dyadic; FL-REC0's depths have none
    assert Z.f32_bits(Z.TWIN_DEPTHS["0p5e20"]) == 0x3F000010
    assert all(Z.f32_bits(z) & 0xFFFF == 0 for z in Z.REC0_DEPTHS.values())
    assert all(Z.f32_bits(z) & 0xFFFF for z in Z.TWIN_DEPTHS.values())


def test_col23_is_e1042s_read():
    import importlib
    sys.path.insert(0, os.path.join(KP, "score"))
    sc = importlib.import_module("score")
    st = sc.kept("zb3-c-b23")
    dr = sc.drawn_set(sc.kept("zb2-b23-txt").decode())
    for y in range(32):
        for x in range(64):
            assert st[Z.st_pos(x, y)] ^ (0xFF if (x, y) in dr else 0) == Z.COL23[x % 16]
    assert sc.g23_map() is not None


def test_recipe_is_bound():
    t = CFG["tools"]["t10"]
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert t["recipe"] in CFG["freeze"]["pins"]
    assert t["sha256"] == "9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb"
    src = open(os.path.join(KP, "lead/build_tool10.sh"), "rb").read()
    assert src == pins.blob("data:render/closing-r10-st1/lead/build_tool10.sh")
    assert f"SRCSHA={t['built_sha256']}" in src.decode()
    assert re.search(r"COMMIT=a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f", src.decode())


def test_every_pin_read_is_declared():
    import importlib
    sys.path.insert(0, os.path.join(KP, "score"))
    sc = importlib.import_module("score")
    want = set(CFG["freeze"]["pins"])
    for p in sc.KEPT.values():
        assert p in want, p
