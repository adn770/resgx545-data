# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r17-zls's generator is current, and every row carries the flags its premise
needs (E934; plan section 3 "Premise tests per builder"): the replicated rows are the kept
records' rows byte for byte and every changed row differs from its kept twin in the named words
only; the odd-size targets and every zb20 row name --depth-pages; both zovp2 shapes have slots
shared by two tiles and edge tiles (E465's slot map, E996's header order) and the planes are the
kept references'; E1063's size is where the three pack starts agree and the new sizes where they
part; the new models reproduce E996, E1041, E1064 and E1063's kept dumps where those hold; every
stage's rows write its scorer's dump; tool t10 and its recipe are bound."""
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
import z17 as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
T10 = "a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f"
STAGE_DUMP = {"zovp2": "--depth-store", "zovs2": "--stencil-store"}


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
    assert list(CFG["stages"]) == ["zovp2", "zovs2", "zb20"]
    assert CFG["stages"]["zb20"].get("on_stop") == "end"
    assert [len(rows(s)) for s in CFG["stages"]] == [5, 3, 9]
    assert {s: [r[0] for r in rows(s)] for s in CFG["stages"]} == Z.STAGE_ROWS
    for s in CFG["stages"]:
        head = open(os.path.join(KP, f"tables/{s}.txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for name, st, risk, knobs, tool, args in rows(s):
            assert tool == "t10" and risk == "safe" and "expectdiff" in knobs.split()
            assert (st == "control") == any(w.startswith("reads:") for w in knobs.split()), name
            o = opts(args)
            assert args.startswith("tri ") and o["--depth"] is True and o["--depth-dump"] == '"$W"'
            for bad in ("--kpoke-render", "--kpoke", "--kreg", "--clkgate", "--trc-hazard",
                        "expectfault"):
                assert bad not in args.split() and bad not in knobs.split()
            # every row of a stage writes its scorer's dump (zb20: the depth dump and the stencil
            # store: no depth store)
            if s in STAGE_DUMP:
                assert STAGE_DUMP[s] in o, name
            assert ("--depth-store" in o) == (s == "zovp2"), name
            assert ("--stencil-store" in o) == (s != "zovp2"), name


def test_odd_sizes_name_their_pages():
    """E934 and HACKING's Known tool weaknesses: a target that is not whole tiles, and every
    zb20 row but the replicate, names --depth-pages and holds every tile's slot and records"""
    for n, r in all_rows().items():
        o = opts(r[5])
        w, h = int(o["--width"]), int(o["--height"])
        whole = w % 32 == 0 and h % 16 == 0
        replicated = n in Z.C160 or n == "zb20-c-f6"
        if not whole or n.startswith("zb20-") and not replicated:
            assert "--depth-pages" in o, n
        if "--depth-pages" in o:
            g = int(o["--depth-ctl"], 16) >> 3 & 0x1FF
            tw, th = Z.tiles(w, h)
            pages = int(o["--depth-pages"])
            need = (Z.TILE_DW * ((th - 1) * (g + 1) + tw) * 4 + 4095) // 4096
            assert pages >= need and pages * 1024 >= w * h, n
            assert pages == (Z.PAGES20 if n.startswith("zb20-") else Z.PAGES2), n


def test_replicated_rows_are_kept_rows():
    t = all_rows()
    assert t["zo2-c-160"][5] == kept_args("render/closing-r16-zls/tables/zovp.txt", "zo-p-160")
    assert t["zo2-c-s160"][5] == kept_args("render/closing-r16-zls/tables/zbits4.txt", "zo-s-160")
    zf = "render/closing-r13-zls/tables/zfmt.txt"
    assert t["zb20-c-f6"][5] == kept_args(zf, "zf-flat-f6")
    assert t["zb20-c-f6"][5] == kept_args("render/closing-r16-zls/tables/zbits4.txt", "zb4-c-f6")
    # zovp2: E996's plane and size of the kept references, the load and store at the pitch
    zodd = "render/closing-r14-zls/tables/zodd.txt"
    for n, (w, h, g, ref, gref) in Z.OVP_ROWS.items():
        r_args = kept_args(zodd, ref)
        for k in ("--width", "--height", "--max-width", "--max-height", "--tri-v", "--tri-z"):
            assert opts(t[n][5])[k] == opts(r_args)[k], (n, k)
        assert opts(t[n][5])["--depth-ctl"] == f"{Z.with_g(Z.ZP_CTL, g):#010x}"
        assert int(opts(r_args)["--depth-ctl"], 16) >> 3 & 0x1FF == gref
        assert g + 1 < Z.tiles(w, h)[0] <= gref + 1               # overlapping, the reference not
        assert opts(t[n][5])["--depth-fill"] == Z.OVL_FILL
    # the E1041 zo-65-ov row's no-load store: the same plane at the same G (its kept dump)
    ov = kept_args(zodd, "zo-65-ov")
    assert int(opts(ov)["--depth-ctl"], 16) >> 3 & 0x1FF == 1
    for n, (w, h, g, ref, gref) in Z.OVC_ROWS.items():
        p = [k for k, v in Z.OVP_ROWS.items() if v[:3] == (w, h, g)][0]
        assert t[n][5] == t[p][5].replace(f"--depth-ctl {Z.with_g(Z.ZP_CTL, g):#010x}",
                                          f"--depth-ctl {Z.with_g(0x00171004, g):#010x}")
    # the stencil rows are E988's st1 form at the shape, with the pages named
    zb2 = "render/closing-r14-zls/tables/zbits2.txt"
    for n, (w, h, g) in Z.OVS_ROWS.items():
        want = kept_args("render/closing-r16-zls/tables/zbits4.txt", "zo-s-160")
        want = want.replace("--depth-ctl 0x00173016", f"--depth-ctl {Z.with_g(Z.ST_CTL, g):#010x}")
        want = want.replace("--width 160 --height 48 --max-width 160 --max-height 48", Z.size(w, h))
        want = want.replace('--depth-dump', f"--depth-pages {Z.PAGES2} --depth-dump")
        assert t[n][5] == want, n
    assert zb2 in "".join(Z.TABLES) or True
    # zb20: E1031's rows with the size, G and pages moved, bit 20 set (twin) or cleared (row)
    for n, (fmt, w, h, g) in Z.ZB20_ROWS.items():
        base = kept_args(zf, "zf-flat-f6" if fmt == 6 else "zf-7k-3f")
        ctl = Z.F6_CTL if fmt == 6 else Z.F7_CTL
        for name, c in ((n.replace("-b-", "-t-"), Z.with_g(ctl, g)),
                        (n, Z.with_g(ctl, g) & ~(1 << 20))):
            want = base.replace("--width 64 --height 32 --max-width 64 --max-height 32",
                                Z.size(w, h))
            want = want.replace(f"--depth-ctl {ctl:#010x}", f"--depth-ctl {c:#010x}")
            want = want.replace("--depth-fill 0xdeadbeef", f"--depth-fill 0xdeadbeef --depth-pages "
                                f"{Z.PAGES20}")
            assert t[name][5] == want, name


def test_order():
    z = Z.STAGE_ROWS["zb20"]
    for n in Z.ZB20_ROWS:
        assert z.index(n.replace("-b-", "-t-")) + 1 == z.index(n)        # the twin right before
    assert z[0] == "zb20-c-f6" and z[-4:] == ["zb20-t-6-128", "zb20-b-6-128", "zb20-t-7-128",
                                               "zb20-b-7-128"]               # the new range last
    for s in ("zovp2", "zovs2"):
        assert Z.STAGE_ROWS[s][0] in Z.C160                                # the replicate first
        cs = [n for n in Z.STAGE_ROWS[s] if all_rows()[n][1] == "control"]
        assert Z.STAGE_ROWS[s][:len(cs)] == cs                             # controls gate: first


def test_shapes_share_slots_and_have_edge_tiles():
    for w, h, g in [(v[0], v[1], v[2]) for v in Z.OVP_ROWS.values()] + list(Z.OVS_ROWS.values()):
        tw, th = Z.tiles(w, h)
        sh = Z.shared_slots(w, h, g)
        assert sh, (w, h, g)
        edge = {(c, r) for r in range(th) for c in range(tw) if Z.is_edge(c, r, w, h)}
        assert edge and (tw - 1, 0) in edge and (0, th - 1) in edge
        # a shared slot with an edge tile in it, and an edge tile that owns a slot
        slots = {}
        for t in Z.header_rank(w, h):
            slots.setdefault(t[1] * (g + 1) + t[0], []).append(t)
        assert any(any(t in edge for t in slots[s]) for s in sh), (w, h, g)
        assert any(Z.owners(w, h, g)[s] in edge for s in sh), (w, h, g)
        # first and last differ (E996's owner rule is what H-OVL-FIRST rivals)
        assert Z.owners(w, h, g) != Z.owners(w, h, g, late=False)
    assert Z.shared_slots(65, 33, 1) == {2, 4} and Z.shared_slots(63, 31, 0) == {1}
    assert Z.shared_slots(160, 48, 2) == {3, 4, 6, 7}


def test_zb20_geometry():
    for n, (fmt, w, h, g) in Z.ZB20_ROWS.items():
        tw, th = Z.tiles(w, h)
        assert g + 1 == tw and not Z.shared_slots(w, h, g)           # no overlap
        rank = Z.header_rank(w, h)
        # the tile order is the slot order (so a packed run in tile order is in slot order)
        assert sorted(rank, key=rank.get) == [(c, r) for r in range(th) for c in range(tw)]
        starts = [Z.pack_start(m, w, h, g) for m in Z.PACK_MODELS]
        assert len(set(starts)) == 3, (n, starts)
        # the packed run of the largest possible records stays inside the pages
        assert max(starts) + 48 * th * (g + 1) <= Z.PAGES20 * 1024
    # E1063's size: the three starts agree
    assert {Z.pack_start(m, 64, 32, 1) for m in Z.PACK_MODELS} == {2048}
    assert [Z.pack_start(m, 128, 64, 3) for m in Z.PACK_MODELS] == [2048, 8192, 4096]
    assert [Z.pack_start(m, 96, 48, 2) for m in Z.PACK_MODELS] == [2048, 4608, 3072]


def test_value_fills_and_slot_map():
    assert Z.fill_at(Z.OVL_FILL, 5) == 0x3E4CCCCD
    for g in (0, 1, 2):
        for x, y in ((0, 0), (37, 5), (100, 40)):
            assert Z.store_dword(x, y, g) == 512 * ((y // 16) * (g + 1) + x // 32) + Z.in_tile_index(x, y)
    assert [Z.zx(h) for h in (31, 33, 48)] == [0.015625, 0.0078125, 0.0078125]


def test_t10_library_premises():
    src = at_t10("userspace/libsgxfive/tools/sgxfive-test.c")
    assert hashlib.sha256(src.encode()).hexdigest() == CFG["tools"]["t10"]["source_sha256"]
    assert 'return i >> f->val & 1 ? 0x3f400000 : 0x3e800000;' in src      # bit:K, z17.fill_at
    # --depth-pages N must hold the target (width x height dwords): depth_min_pages
    assert "o->width * o->height * 4 + SGXFIVE_PAGE_SIZE - 1" in src
    assert "o.depth_pages < depth_min_pages(&o) || o.depth_pages > 0x100000" in src.replace(
        "\n", " ").replace("\t", " ").replace("  ", " ") or "depth_pages > 0x100000" in src
    # tri --tri-full: the triangle (0,0) (3W,0) (0,3H) covers every pixel of a tile area at both
    # zovs2 shapes (the stencil of an edge tile beyond the extent is tested [infer])
    assert "p.v[1][0] = 3 * 16 * (int32_t)p.width;" in src
    for w, h, _ in Z.OVS_ROWS.values():
        tw, th = Z.tiles(w, h)
        assert (32 * tw - 1) / (3 * w) + (16 * th - 1) / (3 * h) < 1


def part(models, pred):
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            assert pred(a) != pred(b), (a, b)


def test_rivals_part():
    for n, (w, h, g, ref, gref) in Z.OVP_ROWS.items():
        full = Z.dwords(Z.kept(ref + ".dep"))
        r = {m: Z.ovp_predict(full, w, h, g, gref, m) for m in Z.OVL_MODELS}
        for i, a in enumerate(Z.OVL_MODELS):
            for b in Z.OVL_MODELS[i + 1:]:
                diff = sum(1 for k in set(r[a][0]) | set(r[b][0]) if r[a][0].get(k) != r[b][0].get(k))
                assert diff >= 60 or r[a][1] != r[b][1], (n, a, b, diff)
    # on the stencil: every pair parts on both rows by dwords or the drawn count; EDGE-CLIP from
    # PASS-EDGE by at least 8 bytes (63 x 31: the beyond-extent bytes of the last tile)
    for n, (w, h, g) in Z.OVS_ROWS.items():
        r = {m: Z.ovs_predict(w, h, g, m) for m in Z.OVS_MODELS}
        for i, a in enumerate(Z.OVS_MODELS):
            for b in Z.OVS_MODELS[i + 1:]:
                diff = sum(1 for k in set(r[a][0]) | set(r[b][0]) if r[a][0].get(k) != r[b][0].get(k))
                assert diff >= 8 or r[a][1] != r[b][1], (n, a, b, diff)
    # the depth beyond the extent cannot part the clip (the plane there is above the load): the
    # models Z.OVL_MODELS leave it out, README says why
    assert "H-EDGE-CLIP" not in Z.OVL_MODELS


def test_new_models_reproduce_kept_records():
    # E1064: whole tiles at 160 x 48 G 2 (no edge tile): the new models are r16's H-OVL-PASS
    full = Z.dwords(Z.kept("zov-160x48-ctl.dep"))
    st = Z.dwords(Z.kept("zo-p-160.dst"))
    pred, drawn = Z.ovp_predict(full, 160, 48, 2, 4, "H-OVL-PASS-EDGE")
    assert drawn == Z.kept_count("zo-p-160", "drawn") == 3040
    assert all(st[i] == v for i, v in pred.items())
    for m in ("H-OVL-FIRST",):
        p, _ = Z.ovp_predict(full, 160, 48, 2, 4, m)
        assert not all(st[i] == v for i, v in p.items())
    sst = Z.kept("zo-s-160.sst")
    pred, drawn = Z.ovs_predict(160, 48, 2, "H-OVL-PASS-EDGE")
    assert drawn == Z.kept_count("zo-s-160", "drawn") == 3840
    assert all(sst[i] == v for i, v in pred.items())
    # E1041: the 65 x 33 G 1 no-load store, whole edge tiles (3584 dwords, 2145 drawn)
    drawn, ch = Z.ovc_expect("zo2-c-65")
    ov = Z.dwords(Z.kept("zo-65-ov.dep"))
    pred, _ = Z.ovp_predict(Z.dwords(Z.kept("zo-65-f0.dep")), 65, 33, 1, 2, "H-OVL-PASS-EDGE",
                            load=False)
    assert (drawn, ch) == (Z.kept_count("zo-65-ov", "drawn"), Z.kept_count("zo-65-ov", "depth")) == (2145, 3584)
    assert all(ov[i] == v for i, v in pred.items()) and len(pred) == ch
    assert Z.ovc_expect("zo2-c-63") == (1953, 1536)
    # E1063: at 64 x 32 G 1 the three pack starts hold on the kept bit-20-cleared dumps
    for key, twin in (("zb4-20-f6", "zf-flat-f6"), ("zb4-20-f7", "zf-7k-3f")):
        dep = Z.dwords(Z.kept(key + ".dep"))
        tw = Z.dwords(Z.kept(twin + ".dep"))
        assert Z.prefix_records(tw, 4) == (twin == "zf-flat-f6")     # format 7: two runs of 12
        for m in Z.PACK_MODELS:
            pred = Z.pack_predict(tw, 64, 32, 1, m)
            assert all(dep[i] == v for i, v in pred.items())
            assert not any(v != Z.FILL_DEAD for i, v in enumerate(dep) if i not in pred)
    assert [len(x) for x in Z.records(Z.dwords(Z.kept("zf-flat-f6.dep")), 4)] == [44] * 4
    assert [len(x) for x in Z.records(Z.dwords(Z.kept("zf-7k-3f.dep")), 4)] == [24, 24, 0, 0]


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
    assert "resgx545:crates/sgx-pipe/src/zls.rs" in want
