# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r14-zls's generator is current, and every row carries the flags its premise
needs (E934; plan section 3 "Per-session premise checks"): the zbase-form rows have --depth-store,
their rd:12 poke is armed after depth_arm's (t10's source, pinned) and --depth-pages holds the
store's extent plus the move; the stencil rows' rd:14 is depth_arm's stencil load base and its
move stays in the stencil buffer; --isp2 only with --depth --stencil --stencil-store; the
replicated rows are the kept records' rows byte for byte (but an added poke); every stage's rows
write its scorer's dump; the rivals part on the rows; tool t10 and its recipe are bound."""
import hashlib
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import z14 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
SRC = "resgx545:userspace/libsgxfive/tools/sgxfive-test.c"


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
    assert list(CFG["stages"]) == ["zgran", "zodd", "zbits2", "zflat"]
    assert [len(rows(s)) for s in CFG["stages"]] == [11, 13, 19, 9]
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
            # every row writes its stage's scorer dump (score.py REQUIRED)
            if s == "zgran":
                assert o["--depth-store"] is True
            if s == "zbits2":
                assert o["--stencil-store"] is True
            if "--isp2" in o:
                assert o["--stencil"] is True and o["--stencil-store"] is True


def test_depth_arm_premises():
    src = pins.blob(SRC).decode()
    assert hashlib.sha256(src.encode()).hexdigest() == CFG["tools"]["t10"]["source_sha256"]
    arm = src.index("ret = depth_arm(&z, o->depth_base")
    kpr = src.index("ret = kpr_write(o->kpr[k].reg, o->kpr[k].fill, o->kpr[k].spec);", arm)
    assert arm < kpr < arm + 1200
    assert 'depth_poke("rd:12=0x%llx", (unsigned long long)(z->depth.addr - base));' in src
    assert 'depth_poke("rd:13=0x%llx", (unsigned long long)(ds->addr - base));' in src
    assert 'depth_poke("rd:14=0x%llx", 0x80000000ull | (z->stencil.addr - base));' in src
    assert ".depth_base = 0x3e000000," in src
    assert 'return i >> f->val & 1 ? 0x3f400000 : 0x3e800000;' in src      # bit:K, z14.fill_at
    assert '{ "stencil", o->stencil, &z.stencil, &o->stencil_fill },' in src  # buffer order


def test_zbase_form_rows():
    t = all_rows()
    for name in ("zg-c-m4", "zg-c-m40", *Z.GRAN_MOVES, *Z.INT_ROWS, "zb2-d12"):
        o = opts(t[name][5])
        rd12 = int(o["--kpoke-render"].split("=")[1], 16)
        assert o["--kpoke-render"].startswith("1:rd:12=") and int(o["--depth-pages"]) == Z.ZB_PAGES
        assert o["--poke"] == "blk:1=0x00000200" and o["--tri-z"] == "0.5,0.5,0.5"
        m = rd12 - Z.ZB_OWN
        # the farthest read (the move plus the 4 tiles' 8 KiB) inside the 20-page depth buffer
        assert 0 <= m and m + 4 * Z.ZB_N <= Z.ZB_PAGES * 4096, name
        assert int(o["--depth-store-fill"], 16) == (Z.INT_SFILL if name in Z.INT_ROWS else Z.ZB_SFILL)
    for n, f in Z.INT_ROWS.items():
        assert opts(t[n][5])["--depth-fill"] == "bit:10"
        assert int(opts(t[n][5])["--depth-ctl"], 16) == 0x0017500E | f << 24
    r13 = "render/closing-r13-zls/tables/zbase.txt"
    assert t["zg-c-ctl"][5] == kept_args(r13, "zb-c-ctl")
    assert t["zg-c-m4"][5] == kept_args(r13, "zb-m4") and t["zg-c-m40"][5] == kept_args(r13, "zb-m40")
    assert t["zb2-d12"][5] == kept_args(r13, "zb-c-id").replace("0x0017500e", "0x0017400e")
    assert t["zg-m8"][5] == kept_args(r13, "zb-m4").replace("rd:12=0x1004", "rd:12=0x1008")
    # E1029's kept zb-m4 printed the addresses hook_check and the scorer assume
    txt = pins.blob("data:render/closing-r13-zls/out/20261113-213117/zbase/zb-m4.txt.gz").decode()
    assert "depth: 0x3e001000 20 pages, fill index, base 0x3e000000," in txt
    assert "depth store: 0x3e015000 20 pages" in txt


def test_stencil_rows():
    t = all_rows()
    st1 = kept_args("render/closing-r10-st1/tables/st1.txt", "st1-b0")
    assert t["zb2-c-base"][5] == st1
    assert t["zb2-c-set"][5] == kept_args("render/closing-r13-zls/tables/zbits.txt", "zbs-set")
    for n in ("zg-c-sid", "zg-s14"):
        o = opts(t[n][5])
        rd14 = int(o["--kpoke-render"].split("=")[1], 16)
        assert t[n][5] == st1.replace("--stencil-fill bytes", "--stencil-fill index") + \
            f" --kpoke-render 1:rd:14={rd14:#x}"
        assert rd14 >> 31 and (rd14 & 0x7FFFFFFF) == Z.ST_STENCIL - Z.ZB_BASE + (Z.S_MOVE if n == "zg-s14" else 0)
        # the moved load's 2048 bytes inside the stencil's 18 pages
        assert Z.S_MOVE + 2048 <= 18 * 4096
    for n in [x for x in Z.STAGE_ROWS["zbits2"] if x.startswith("zb2-")]:
        o = opts(t[n][5])
        ctl = int(o["--depth-ctl"], 16)
        if n in Z.PITCH_ROWS:
            w, bit = Z.PITCH_ROWS[n]
            assert ctl == 0x00173016 & ~(1 << bit) and int(o["--width"]) == w
            assert t[n][5] == st1.replace("0x0017300e", f"{ctl:#010x}").replace(
                "--width 64", f"--width {w}").replace("--max-width 64", f"--max-width {w}")
        elif n not in ("zb2-c-base", "zb2-c-set"):
            bits = Z.z_bits(n)
            assert ctl == Z.ST_CTL | sum(1 << b for b in bits)
            assert t[n][5] == st1.replace("0x0017300e", f"{ctl:#010x}")
    # E988's buffer addresses (st1-b0 as kept)
    txt = pins.blob("data:render/closing-r13-zls/out/20261113-213117/zbits/zbs-base.txt.gz").decode()
    assert "stencil: 0x3e013000 18 pages" in txt and "stencil store: 0x3e025000 18 pages" in txt


def test_depth_rows():
    t = all_rows()
    zov = "render/closing-r10-x/tables/zov.txt"
    assert t["zo-c-ov"][5] == kept_args(zov, "zov-64x32-g0")
    assert Z.zov_args(128, 32, 1) == kept_args(zov, "zov-128x32-g1")
    assert Z.zov_args(256, 64, 3) == kept_args(zov, "zov-256x64-g3")
    assert t["zb2-c-r16"][5] == kept_args("render/closing-r13-zls/tables/zbits.txt", "zbr-c16")
    f2 = kept_args("render/closing-r9-x/tables/zls.txt", "z242-c-f2")
    assert t["zb2-f2-16"][5] == f2.replace("0x02171014", "0x02161014")
    for k, (w, h, g) in Z.ODD.items():
        assert g + 1 == Z.tiles(w, h)[0] and (w % 32 and h % 16)            # edge tiles, full pitch
    assert Z.macro(640, 480)[0] == 4 and Z.macro(65, 33)[0] == 2
    o = opts(t["zo-g3"][5])
    assert int(o["--depth-ctl"], 16) >> 3 & 0x1FF == 3 and o["--kpoke-render"] == "1:rd:13=0xd000"
    assert Z.g3_pages("H-NEXTTILE") == [12, 14, 16, 18] and Z.g3_pages("H-STRAY") == [12, 14]
    assert max(Z.g3_pages("H-NEXTTILE")) < int(o["--depth-pages"])
    # the 640 x 480 overlap: every slot inside the default buffer (the target's pages + 16)
    slots = max(Z.owners(640, 480, 2, "H-LATE/HDR")) + 1
    assert 512 * slots * 4 <= (640 * 480 * 4 // 4096 + 16) * 4096


def test_flat_rows():
    t = all_rows()
    assert t["zl-c-flat"][5] == kept_args("render/closing-r13-zls/tables/zfmt.txt", "zf-flat-f6")
    y6 = kept_args("render/closing-r10-zls/tables/zst2.txt", "z2y-f6")
    assert t["zl-c-y6"][5] == y6
    for n, z in Z.FLAT_DEPTHS.items():
        assert t[n][5] == y6.replace("0.25,0.25,0.75", f"{z},{z},{z}")
    assert t["zl-f7-idx"][5] == t["zl-c-flat"][5].replace("0x0617300e", "0x0717300e")
    assert t["zl-f5-flat"][5] == t["zl-c-flat"][5].replace("0x0617300e", "0x0517300e")
    assert Z.f32_bits("0.1234") == 0x3DFCB924 and len(set(struct_bytes(0x3DFCB924))) == 4


def struct_bytes(v):
    return [v >> (8 * i) & 0xFF for i in range(4)]


def test_f6c_head_is_c7_rule():
    import types
    m = types.ModuleType("c7_rule")
    exec(compile(pins.blob("data:cited/closing11/plan/c7-q120/c7_rule.py"), "c7_rule.py", "exec"),
         m.__dict__)
    for v in (0x3F000000, 0x3E800000, 0x3DFCB924, 0):
        assert Z.f6c_head(v) == m.f6c_group([v] * 4)[:4]
    flat = pins.blob("data:render/closing-r13-zls/out/20261113-213117/zfmt/zf-flat-f6.depth.1.bin.gz")
    assert Z.dwords(flat)[:4] == Z.f6c_head(0x3F000000)


def part(models, rows_, pred):
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            assert any(pred(n, a) != pred(n, b) for n in rows_), (a, b)


def test_rivals_part():
    part([m for m in Z.GRAN_MODELS if m != "H-BYTE"], Z.GRAN_MOVES,
         lambda n, m: Z.gran_offset(m, Z.GRAN_MOVES[n]))
    # H-BYTE parts from G8 only at +4 (E1029's zb-m4, replicated by zg-c-m4)
    assert Z.gran_offset("H-BYTE", 4) != Z.gran_offset("G8", 4)
    assert all(Z.gran_offset("H-BYTE", m) == Z.gran_offset("G8", m) for m in Z.GRAN_MOVES.values())
    for f in (1, 2):
        part(list(Z.INT_MODELS[f]), [f], lambda n, m: Z.int_predict(n, m))
    part(list(Z.S_MODELS), [0], lambda n, m: [Z.s_loaded(m, x, y) for y in range(32) for x in range(64)])
    zrows = [n for n in Z.STAGE_ROWS["zbits2"] if n.startswith("zb2-b") or n.startswith("zb2-g")]
    part(Z.z_models(), zrows, Z.z_predict)
    part(list(Z.P_MODELS), Z.PITCH_ROWS, lambda n, m: Z.pitch(m, Z.PITCH_ROWS[n][0]))
    part(list(Z.D12_MODELS), [0], lambda n, m: Z.d12_predict(m))
    f2 = Z.dwords(pins.blob("data:render/closing-r9-x/out/20261113-081821/zls/z242-c-f2.depth.1.bin.gz"))
    part(list(Z.L16_MODELS), [0], lambda n, m: Z.l16_predict(m, f2))
    # the 640 x 480 row parts all four orders; 65 x 33's edge row late from early (its header
    # order is raster: one macrotile)
    part(list(Z.OV_MODELS), [(640, 480, 2)], lambda n, m: Z.owners(*n, m))
    assert Z.owners(65, 33, 1, "H-LATE/HDR") != Z.owners(65, 33, 1, "H-EARLY/HDR")
    assert Z.owners(65, 33, 1, "H-LATE/HDR") == Z.owners(65, 33, 1, "H-LATE/RASTER")
    ref = [0x3E000000 + 0x1000 * i for i in range(9 * 512)]
    for k, (w, h, g) in Z.ODD.items():
        part(list(Z.INT_PAST_MODELS), [1, 2], lambda n, m: Z.int_past_predict(ref, w, h, g, n, m))


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
