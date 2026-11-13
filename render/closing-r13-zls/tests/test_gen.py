# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r13-zls's generator is current, and every row carries the flags its premise
needs (E934; plan section 3 "Per-session premise checks"): zbase rows have --depth-store, their
rd:12 poke is armed after depth_arm's (t10's source, pinned) and --depth-pages holds the store's
extent plus the move; zbits rows have --isp2 only with --depth --stencil --stencil-store; the
replicated rows are the kept records' rows byte for byte (but the tool and an added poke); the
rivals part on the rows; tool t10 and its recipe are bound."""
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
import z13 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def rows(stage):
    return [ln.rstrip("\n").split("|", 5) for ln in open(os.path.join(KP, f"tables/{stage}.txt"))
            if ln.strip() and not ln.startswith("#")]


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
    return [ln.split("|", 5) for ln in t.splitlines() if ln.startswith(name + "|")][0]


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["zbase", "zbits", "zfmt"]
    assert [len(rows(s)) for s in CFG["stages"]] == [11, 16, 6]
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


def test_zbase_premises():
    src = pins.blob("resgx545:userspace/libsgxfive/tools/sgxfive-test.c").decode()
    assert hashlib.sha256(src.encode()).hexdigest() == CFG["tools"]["t10"]["source_sha256"]
    # depth_arm pokes rd:12 (the depth buffer - base) and rd:13 before the row's --kpoke-render
    arm = src.index("ret = depth_arm(&z, o->depth_base")
    # (the render loop's own: an earlier kpr_write is the second context.s, line 2989)
    kpr = src.index("ret = kpr_write(o->kpr[k].reg, o->kpr[k].fill, o->kpr[k].spec);", arm)
    assert arm < kpr < arm + 1200 and "zbuf_fill(&z.depth, &o->depth_fill);" in src[arm:kpr]
    assert 'depth_poke("rd:12=0x%llx", (unsigned long long)(z->depth.addr - base));' in src
    assert ".depth_base = 0x3e000000," in src
    for name, st, risk, knobs, tool, args in rows("zbase"):
        o = opts(args)
        assert o["--depth-store"] is True and o["--pixels"] is True
        assert o["--tri-full"] is True and o["--tri-z"] == "0.5,0.5,0.5"
        assert int(o["--width"]) == 64 and int(o["--height"]) == 32
        if name in ("zb-c-ctl", "zb-c-eq0"):
            continue
        assert o["--kpoke-render"].startswith("1:rd:12=")
        rd12 = int(o["--kpoke-render"].split("=")[1], 16)
        pages = int(o["--depth-pages"])
        assert pages == Z.ZB_PAGES and o["--poke"] == "blk:1=0x00000200"
        m = rd12 - Z.ZB_OWN
        buf = pages * 4096
        if name == "zb-mst":
            assert rd12 == Z.ZB_ST_OFF and o["--depth-store-fill"] == "index"
            continue
        # the farthest read of the load (the move plus the 4 tiles' 8 KiB) inside the depth buffer
        assert 0 <= m and m + 4 * Z.ZB_N <= buf, name
        assert o["--depth-fill"] == "index" and int(o["--depth-store-fill"], 16) == Z.ZB_SFILL
        assert int(o["--depth-ctl"], 16) == (Z.ZB_CTL_OFF if name == "zb-c-off" else Z.ZB_CTL)
    assert Z.ZB_STORE - Z.ZB_BASE == Z.ZB_ST_OFF == 0x15000


def test_zbase_replicates_kept_rows():
    t = {r[0]: r[5] for r in rows("zbase")}
    z243 = kept_args("render/closing-r9-x/tables/zls.txt", "z243-ctl")
    assert t["zb-c-ctl"] == z243[5] + " --kpoke-render 1:rd:12=0x1000"
    eq = kept_args("render/closing-r10-x/tables/dcmp.txt", "eq-m0")
    assert t["zb-c-eq0"] == eq[5]
    # E977's kept z243-ctl: depth_arm's own rd:12 at 18 pages is 0x1000 (depth 0x3e001000)
    txt = pins.blob("data:render/closing-r9-x/out/20261113-081821/zls/z243-ctl.txt.gz").decode()
    assert "depth: 0x3e001000 18 pages, fill 0x3f400000, base 0x3e000000," in txt


def test_zbase_rivals_part():
    moved = [n for n in Z.ZB_MOVES]
    for i, a in enumerate(Z.ZB_MODELS):
        for b in Z.ZB_MODELS[i + 1:]:
            assert any(Z.zb_predict(n, a) != Z.zb_predict(n, b) for n in moved), (a, b)


def test_zbits_premises():
    base = kept_args("render/closing-r10-st1/tables/st1.txt", "st1-b0")[5]
    q071 = kept_args("render/closing-r10-st1/tables/st1.txt", "q071-b0")[5]
    ramp = kept_args("render/closing-r10-x/tables/zbits.txt", "zb-ctl-f0")[5]
    t = {r[0]: r for r in rows("zbits")}
    assert t["zbs-base"][5] == base and t["zbs-q071"][5] == q071 and t["zbr-ctl"][5] == ramp
    for name, st, risk, knobs, tool, args in t.values():
        o = opts(args)
        if "--isp2" in o:
            assert o["--depth"] is True and o["--stencil"] is True and o["--stencil-store"] is True
            assert name.startswith("zbs-")
        else:
            assert name.startswith("zbr-") and "--stencil" not in o
        ctl = int(o["--depth-ctl"], 16)
        if name in Z.ZBITS_BITS:
            bits = Z.ZBITS_BITS[name]
            ref = base if name.startswith("zbs-") else ramp
            refctl = Z.ST_CTL if name.startswith("zbs-") else Z.RAMP_CTL
            want = refctl | Z.SET_BITS if bits == "set" else Z.cleared(refctl, bits)
            assert ctl == want
            assert args == ref.replace(f"--depth-ctl {refctl:#010x}", f"--depth-ctl {ctl:#010x}")
            if bits != "set":
                assert ctl ^ refctl == sum(1 << b for b in bits)


def test_zbits_rivals_part():
    for c, pre in (("Z", "zbs-"), ("L", "zbr-")):
        ms = Z.clause_models(c)
        names = [n for n in Z.ZBITS_BITS if n.startswith(pre)]
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                assert any(Z.zbits_predict(n, a) != Z.zbits_predict(n, b) for n in names), (a, b)


def test_zfmt_rows():
    zst2 = "render/closing-r10-zls/tables/zst2.txt"
    t = {r[0]: r[5] for r in rows("zfmt")}
    assert t["zf-y6-ctl"] == kept_args(zst2, "z2y-f6")[5]
    sa5 = kept_args(zst2, "z2x-f7-sa5")[5]
    for n, f in (("zf-7k-3f", "0x3f3f3f3f"), ("zf-7k-1f", "0x1f1f1f1f")):
        assert t[n] == sa5.replace("--stencil-fill 0xa5a5a5a5", f"--stencil-fill {f}")
    y6 = kept_args(zst2, "z2y-f6")[5]
    assert t["zf-flat-f6"] == y6.replace("--tri-z 0.25,0.25,0.75", "--tri-z 0.5,0.5,0.5")
    y48 = y6.replace("64", "48").replace("--tri-z 0.25,0.25,0.75", "--tri-z 0.375,0.375,0.875")
    assert t["zf-y48-f6"] == y48
    assert t["zf-y48-f0"] == y48.replace("0x0617300e", "0x0017300e")
    # 48 x 32: the store's 4 tiles (2 pages) inside the default 2 + 16 pages (HACKING weakness)
    assert (48 * 32 * 4 + 4095) // 4096 + 16 >= 2 * 2 * 512 * 4 // 4096


def test_c7_rule_is_e1015s():
    b = pins.blob("data:cited/closing11/plan/c7-q120/c7_rule.py")
    assert hashlib.sha256(b).hexdigest().startswith("4d87c5ad")
    assert 'TEMPLATE = "ASBASBASBASBASBABASBASBASBASBASBSBASBASBASBASBAS"' in b.decode()


def test_in_tile_order_is_zls_rs():
    rs = pins.blob("resgx545:crates/sgx-pipe/src/zls.rs").decode()
    assert "fn in_tile_order_is_y0_x0_y1_x1_y2_x2_y3_x3_x4" in rs
    assert sorted(Z.in_tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))


def test_recipe_is_bound():
    t = CFG["tools"]["t10"]
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert "data:render/closing-r10-st1/lead/build_tool10.sh" in CFG["freeze"]["pins"]
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
    for p in list(sc.KEPT.values()) + [sc.C7_RULE]:
        assert p in want, p
