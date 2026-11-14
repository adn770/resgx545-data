# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r16-zls's generator is current, and every row carries the flags its premise
needs (E934; plan section 3 "Premise tests per builder"): the replicated rows are the kept
records' rows byte for byte and every changed row differs from its kept twin in the named words
only; each zpass2 twin is the row right after its pass; every NaN fill is a value fill; E465's
slot map shares slots at G 0 and G 2; t10's block holds the reference in ISP word 0's bits 7:0,
the z offset and scale in words 10 and 11 and the background word 0x300; every stage's rows write
its scorer's dump; the rivals part on the rows; OQ069's frozen output is current and its Python
cut is sgx-pipe's; tool t10 and its recipe are bound."""
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
import z16 as Z  # noqa: E402

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


def ctl_swap(args, old, new):
    assert args.count(f"--depth-ctl {old:#010x}") == 1
    return args.replace(f"--depth-ctl {old:#010x}", f"--depth-ctl {new:#010x}")


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["zpass2", "zbits4", "zovp", "zoff"]
    assert CFG["stages"]["zoff"].get("on_stop") == "end"
    assert [len(rows(s)) for s in CFG["stages"]] == [15, 14, 10, 10]
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
            # every row of a stage writes its scorer's dump, and no other store
            assert ("--depth-store" in o) == (s in ("zpass2", "zovp")), name
            assert ("--stencil-store" in o) == (s == "zbits4"), name
            if "--isp2" in o:
                assert o["--stencil"] is True and o["--stencil-store"] is True
            # Known tool weaknesses: every target is whole tiles (no --depth-pages needed)
            w, h = int(o["--width"]), int(o["--height"])
            assert w % 32 == 0 and h % 16 == 0, name
            if "--depth-pages" in o:
                g = int(o["--depth-ctl"], 16) >> 3 & 0x1FF
                tw, th = Z.tiles(w, h)
                need = (Z.TILE_DW * ((th - 1) * (g + 1) + tw) * 4 + 4095) // 4096
                assert int(o["--depth-pages"]) >= need, name


def test_replicated_rows_are_kept_rows():
    t = all_rows()
    zp = "render/closing-r15-zls/tables/zpass.txt"
    assert t["zp2-c-467"][5] == kept_args(zp, "zp-c-467")
    assert t["zp2-c-z125"][5] == kept_args(zp, "zp-z125")
    assert t["zo-c-f1"][5] == kept_args(zp, "zp-f1")
    zb2 = "render/closing-r14-zls/tables/zbits2.txt"
    assert t["zb4-c-base"][5] == kept_args(zb2, "zb2-c-base")
    assert t["zb4-c-b23"][5] == kept_args(zb2, "zb2-b23")
    zf = "render/closing-r13-zls/tables/zfmt.txt"
    assert t["zb4-c-f6"][5] == kept_args(zf, "zf-flat-f6")
    assert t["zw2-c-0125"][5] == kept_args("render/closing-r10-zls/tables/zw.txt", "zw-0125")
    # bit 0 and bit 20: the kept twin's argv with its control word changed, nothing else
    twins = {"zb4-b0-st": (zb2, "zb2-c-base", 0x0017300E), "zb4-b0-f6": (zf, "zf-flat-f6", 0x0617300E),
             "zb4-b0-f7": (zf, "zf-7k-3f", 0x0717300E),
             "zb4-b0-c16": ("render/closing-r13-zls/tables/zbits.txt", "zbs-c16", 0x0016300E),
             "zb4-20-f6": (zf, "zf-flat-f6", 0x0617300E), "zb4-20-f7": (zf, "zf-7k-3f", 0x0717300E),
             "zb4-20-d12": ("render/closing-r14-zls/tables/zgran.txt", "zb2-d12", 0x0017400E),
             "zb4-20-640": ("render/closing-r14-zls/tables/zodd.txt", "zo-640-f0", 0x0017109C)}
    for n, (tab, twin, ctl) in twins.items():
        new = ctl | 1 if "-b0-" in n else ctl & ~(1 << 20)
        assert t[n][5] == ctl_swap(kept_args(tab, twin), ctl, new), n
        assert Z.ZB4_TWIN[n] == twin
    # bit 23: E1042's zb2-b23 plus the one moved value
    b23 = kept_args(zb2, "zb2-b23")
    assert t["zb4-23-ref"][5] == b23 + " --poke blk:1^=0x80"
    assert t["zb4-23-msk"][5] == b23.replace("--isp2 0x040501ff", "--isp2 0x0405ffff")
    assert t["zb4-23-bg"][5] == b23 + " --kpoke-render 1:rd:17=0x35a"
    # zpass2: each twin is its pass row without the load bits; the depths as frozen
    for k, z in Z.DEPTHS.items():
        p = t[Z.pass_name(k)][5]
        assert p == t["zp2-c-z125"][5].replace("0.125,0.125,0.125", f"{z},{z},{z}")
        assert t[f"zp2-t-{k}"][5] == ctl_swap(p, 0x0017500E, 0x0017100C)
    # zovp: the plane of E996's references, the load and store at the overlapping pitch
    zov = "render/closing-r10-x/tables/zov.txt"
    for n, (w, h, g, ref, gref) in Z.OVP_ROWS.items():
        r_args = kept_args(zov, ref[:-4])
        for k in ("--width", "--height", "--tri-v", "--tri-z"):
            assert opts(t[n][5])[k] == opts(r_args)[k], (n, k)
        assert opts(t[n][5])["--depth-ctl"] == f"{Z.with_g(0x0017500E, g):#010x}"
        assert g + 1 < Z.tiles(w, h)[0] <= gref + 1
    assert t["zo-c-64"][5] == ctl_swap(t["zo-p-64"][5], 0x00175006, 0x00171004)
    for n, (w, h, g) in Z.OVS_ROWS.items():
        assert t[n][5] == ctl_swap(kept_args(zb2, "zb2-c-base"), 0x0017300E,
                                   Z.with_g(0x0017300E, g)).replace(
            "--width 64 --height 32 --max-width 64 --max-height 32", Z.size(w, h))
    # the NaN rows: zp-f1's form under never, a value fill
    for n, (fmt, v) in Z.NAN_ROWS.items():
        o = opts(t[n][5])
        assert o["--depth-fill"] == f"{v:#010x}" and int(o["--depth-fill"], 16) == v
        assert o["--depth-ctl"] == f"{0x0017500E | fmt << 24:#010x}" and o["--poke"] == "blk:1=0x00000200"
    # zoff: zw-0125's argv with word 10 (and word 11) moved
    for n, (w, s) in Z.ZOFF_ROWS.items():
        want = t["zw2-c-0125"][5].replace("blk:10=0x3e000000", f"blk:10={Z.f32_bits(w):#010x}")
        if s != 0.5:
            want += f" --poke blk:11={Z.f32_bits(s):#010x}"
        assert t[n][5] == want


def test_twins_adjacent_and_order():
    order = Z.STAGE_ROWS["zpass2"]
    for k in Z.DEPTHS:
        i = order.index(Z.pass_name(k))
        assert order[i + 1] == f"zp2-t-{k}"
    # never-run ranges last: the background poke, then the vertex depth -0.5
    assert Z.STAGE_ROWS["zbits4"][-1] == "zb4-23-bg"
    assert Z.STAGE_ROWS["zoff"][-2:] == ["zw2-s75", "zw2-w0"]
    for n, (w, s) in Z.ZOFF_ROWS.items():
        assert w - s >= -0.5                                   # no vertex below -0.5
    # zoff's held-out offsets are none of the kept ones (0.125, 0.25 at s 0.5)
    assert not {(w, s) for w, s in Z.ZOFF_ROWS.values()} & {(0.125, 0.5), (0.25, 0.5)}


def test_value_fills_and_slot_map():
    for n in Z.NAN_ROWS:
        f = opts(all_rows()[n][5])["--depth-fill"]
        assert re.fullmatch(r"0x[0-9a-f]{8}", f) and Z.fill_at(f, 7) == int(f, 16)
    assert Z.fill_at(Z.OVL_FILL, 5) == 0x3E4CCCCD
    # E465: tile (tx, ty) at dword 512 (ty (G + 1) + tx); slots shared at G 0 and G 2
    for g in (0, 2):
        for x, y in ((0, 0), (37, 5), (100, 40)):
            assert Z.store_dword(x, y, g) == 512 * ((y // 16) * (g + 1) + x // 32) + Z.in_tile_index(x, y)
    assert Z.shared_slots(64, 32, 0) == {1}
    assert Z.shared_slots(160, 48, 2) == {3, 4, 6, 7}
    assert Z.owners(64, 32, 0) != Z.owners(64, 32, 0, late=False)


def test_t10_library_premises():
    src = at_t10("userspace/libsgxfive/tools/sgxfive-test.c")
    assert hashlib.sha256(src.encode()).hexdigest() == CFG["tools"]["t10"]["source_sha256"]
    rc = at_t10("userspace/libsgxfive/src/render.c")
    # ISP word 0 (blk:1) holds the reference in bits 7:0 (E284), 0 in t10's block, so ^0x80 sets
    # it to 0x80; words 10 and 11 the viewport's z offset and scale (3d.md 9.1), both 0.5, and no
    # zoff row has --isp2 (which moves them); the background word 0x300 (bit 8 set, STENCIL 0)
    assert "blk[i++] = 0x01d00200;\t\t/* isp0 */" in rc and "blk[1] |= 1u << 8;" in rc
    lines = [ln.strip() for ln in rc.splitlines() if ln.strip().startswith("blk[i++]")]
    assert lines[10] == lines[11] == "blk[i++] = sgxfive_f32(0.5f);"
    assert "c->isp_bgobj = 0x300;" in rc and (Z.BG_RD17 & ~0xFF) == 0x300
    for n in Z.ZOFF_ROWS:
        assert "--isp2" not in all_rows()[n][5]
    assert 'return i >> f->val & 1 ? 0x3f400000 : 0x3e800000;' in src      # bit:K, z16.fill_at


def part(models, names, pred):
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            assert any(pred(n, a) != pred(n, b) for n in names), (a, b)


def test_rivals_part():
    import struct
    # zpass2: OWN parts from TWIN on any twin that is not the depth's float (zp-z125's kept store)
    st = Z.dwords(Z.kept("zp-z125.dst"))
    assert Z.pass_predict("z125", "H-PASS-TWIN", st) != Z.pass_predict("z125", "H-PASS-OWN")
    assert [Z.f32_bits(Z.DEPTHS[k]) for k in Z.ONE_FLOAT] == [0x3EC00000, 0x3F200000, 0x3F000010]
    assert [Z.pass_drawn(k) for k in Z.DEPTHS] == [2048] * 3 + [1024] * 4
    # zbits4
    part(Z.B23_MODELS, list(Z.B23_ROWS), Z.b23_predict)
    for n in Z.OVS_ROWS:
        part(Z.OVS_MODELS, [n], lambda n, m: Z.ovs_predict(*Z.OVS_ROWS[n], m))
    # zovp: each pair of forms parts on both rows
    for n, (w, h, g, ref, gref) in Z.OVP_ROWS.items():
        full = Z.dwords(Z.kept(ref))
        part(Z.OVL_MODELS, [n], lambda _, m: Z.ovp_predict(full, w, h, g, gref, m))
    for n in Z.NAN_ROWS:
        part(Z.NAN_MODELS, [n], Z.nan_predict)
    # zoff: each pair parts on drawn or depth on every row that scores it
    for n, (w, s) in Z.ZOFF_ROWS.items():
        ms = Z.OFF_MODELS if s == 0.5 else Z.SCALE_MODELS
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                same = all(Z.zoff_pixel(a, w, s, x) == Z.zoff_pixel(b, w, s, x) for x in range(256))
                assert not same or {a, b} == {"H-LIN-S", "H-POLYCLIP"} and s == 0.25, (n, a, b)
    assert struct.pack("<f", 0.2) == struct.pack("<I", 0x3E4CCCCD)


def test_oq069_gate_and_cut():
    out = open(os.path.join(KP, "gen/oq069.out")).read()
    assert "the off sets of the two rows are the same (912 pixels)" in out
    assert out.rstrip().endswith("H-LIN reproduces every kept dword outside BEND")
    assert len(Z.BEND()) == 912
    assert Z.bend(Z.dwords(Z.kept("z2-a-f0.dep")), 0.25) == Z.BEND()
    # z16's Python cut is sgx-pipe's isp::depth_cut_image (gen/oq069rs.out)
    rs = open(os.path.join(KP, "gen/oq069rs.out")).read()
    for w in (0.125, 0.25, 0.0, 0.0625, 0.1875, 0.3125, 0.375, 0.4375):
        m = re.search(r"^w %s: covered (\d+) of 32768" % re.escape(f"{w:g}" if w else "0"), rs, re.M)
        assert int(m.group(1)) == Z.zoff_drawn("H-POLYCLIP", w, 0.5), w
    m = re.search(r"^w 0.25 s 0.75: covered (\d+) of 32768", rs, re.M)
    assert int(m.group(1)) == Z.zoff_drawn("H-POLYCLIP", 0.25, 0.75)


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
    want = set(CFG["freeze"]["pins"])
    for p in Z.KEPT.values():
        assert "data:" + p in want, p
    for p in Z.TABLES:
        assert "data:" + p in want, p
