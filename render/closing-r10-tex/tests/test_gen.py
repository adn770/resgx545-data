# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r10-tex's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the programs that rerun a kept job rebuild its
published program byte for byte; every coordinate the programs compute is exact in float32; the
frozen models reproduce the kept jobs they rest on (E957's offsets, E932's mode 5, E975's R-4096,
E956's edges under H-SEAM-FLOAT, E976's rows under R10-BF11); the rivals part where the plan needs
them to; every rival's reads fit the probe's scratch (the plan's per-row premise checks)."""
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tomllib

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import pins  # noqa: E402
import q282 as Q  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402
import tex  # noqa: E402
import texprog as T  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
SEEDS = "/Users/jtorra/src/scratch/resgx545/closing10/seeds"
R9G = "data:render/closing-r9-geo/out/20261113-081038/%s.txt.gz"
R9X = "data:render/closing-r9-x/out/20261113-081821/%s.txt.gz"


def kept_xy(pin):
    return T.pixels(gzip.decompress(pins.blob(pin)).decode(errors="replace"))


def tokens(stage, name, model):
    return open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")).read().split()


def binfile(name):
    return open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    A.jobs()
    C.jobs3()
    T3.jobs()
    SRGB.jobs()
    test_programs_rebuild_the_published_ones()
    test_models_reproduce_the_kept_jobs()
    test_edge_float_reproduces_e956()
    test_r10bf11_reproduces_e976_and_e723()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_programs_rebuild_the_published_ones():
    for mine, pub in (("addr3-ctl-u0", "render/closing-r9-geo/bins/addr-ctl-u0.bin"),
                      ("addr3-u4-rep", "render/closing-r9-geo/bins/addr-u4-rep.bin"),
                      ("cube3-ctl-xn", "render/closing-r4-render4x/bins/p1141-cube__4.bin"),
                      ("cube3-a2-replay", "render/closing-r8-geo/bins/cube-off-a2.bin"),
                      ("t3b-ctl", "texture/p1132-recomp/raw/tx-t3bits/bins/tx-t3bits__0.bin"),
                      ("t3b-b14ref", "texture/p1132-recomp/raw/tx-t3bits/bins/tx-t3bits__14.bin"),
                      ("t3b-u01", "render/closing-r9-x/bins/b14-u01.bin"),
                      ("srgb2-ctl", "texture/p1141/stage-bins/p1141-t0b27__4.bin")):
        assert binfile(mine) == pins.blob("data:" + pub), mine


def test_programs_fit_the_probe():
    for f in os.listdir(os.path.join(KP, "bins")):
        if f.endswith(".bin"):
            n = os.path.getsize(os.path.join(KP, "bins", f))
            assert n % 8 == 0 and n <= 256 * 8, (f, n)       # PROBE_MAX_WORDS, sgxfive-test.c


def test_every_coordinate_is_exact():
    specs = [A.coords(w, h) for _, _, w, h, _, _, _ in A.jobs()]
    specs += [s for _, _, s, _, _, _ in C.jobs3()]
    for spec in specs:
        for y in range(T.H):
            for x in range(T.W):
                for s in spec:
                    assert T.exact_f32(T.coord(s, x, y)), (spec, x, y)
    for j in T3.jobs()[2:] + SRGB.jobs()[1:]:
        sp = j[3]
        for y in range(32):
            for x in range(64):
                for ax in ("u", "v"):
                    assert tex.exact_f32(tex.coord(sp[ax], x, y)), (j[0], ax, x, y)


# ---- the models on the kept jobs they rest on ----------------------------------------------------
def addr_kept(name):
    px = kept_xy(R9G % ("addr2/" + name))
    return [(px[(x, y)] & 0x0FFFFFFF) - A.BASE for y in range(32) for x in range(64)]


def test_models_reproduce_the_kept_jobs():
    # E957's control and replicate (16 x 16), its 8 x 8 and 32 x 32 offsets (116, 308: H-W) and
    # E932's mode 5 read (H-B5 at 16 x 16), through E561's index
    assert A.image(16, 16, 0, 0, "REPEAT") == addr_kept("addr-ctl-u0")
    assert A.image(16, 16, 4, 0, "H-W") == addr_kept("addr-u4-rep")
    assert A.image(8, 8, 4, 0, "H-W") == addr_kept("addr-u4-n8")
    assert A.image(32, 32, 4, 0, "H-W") == addr_kept("addr-u4-n32")
    assert A.image(16, 16, 5, 0, "H-B5") == addr_kept("addr-u5-rep")
    # E975: R-4096 on b14-u01 (the replicate) and on b14-w32s32 (S * S = 1024: H-U01 fails there)
    u01 = pins.kept_pixels(T3.E975_U01)
    assert [int(t, 16) for t in tokens("t3b", "t3b-u01", "R-4096")] == u01
    sp = T3.spec(32, 32, 32, T3.U64, T3.V32, 0, 12, T3.T3W | T3.B14)
    m = T3.models(sp, dict(sp, t3=T3.T3W))
    hw = pins.kept_pixels(R9X % "t3/b14-w32s32")
    assert m["R-4096"] == hw and m["H-U01"] != hw
    # the controls' frozen images are the kept ones
    assert [int(t, 16) for t in tokens("t3b", "t3b-ctl", "H-E566")] == pins.kept_pixels(
        T3.E566 % "s64x32-ctl")
    e726 = kept_xy("data:" + "texture/p1141/out-hw/p1141tex-dumps/tex-h-cube/cu-xn.txt.gz")
    assert [int(t, 16) for t in tokens("cube3", "cube3-ctl-xn", "E726")] == [
        e726[(x, y)] for y in range(32) for x in range(64)]


def test_edge_float_reproduces_e956():
    """Seeds finding 3, post hoc on E956's kept edges: H-SEAM-FLOAT 96 of 96 out pixels within 1
    on both, H-SEAM-ADJ 64 of 96 at +z/+x."""
    R = C.rule()
    got = {}
    for k in ("zx", "yx"):
        px = kept_xy(R9G % ("cube2/cube-edge-" + k))
        spec = C.EDGE[k]
        for rv in C.EDGE3_RIVALS:
            ok = n = 0
            for p, (f, kind) in C.edge_cells(R, spec, 16).items():
                if kind != "out":
                    continue
                c = tuple(T.coord(s, *p) for s in spec)
                tl = C.blend_float(R, c, 16) if rv == "H-SEAM-FLOAT" else C.blend(R, c, 16, rv)
                b = C.blend_bytes(tl)
                n += 1
                ok += all(abs(float(b[i]) - (px[p] >> 8 * i & 255)) <= 1 for i in range(4))
            got[(k, rv)] = (ok, n)
    assert got == {("zx", "H-SEAM-FLOAT"): (96, 96), ("zx", "H-SEAM-ADJ"): (64, 96),
                   ("yx", "H-SEAM-FLOAT"): (96, 96), ("yx", "H-SEAM-ADJ"): (96, 96)}


def test_r10bf11_reproduces_e976_and_e723():
    """R10-BF11 (x then y) on r9-x's six kept srgb rows (its fit set a, b and the held-out c) and
    E723's g-bl-st-a and g-bl-st-b: 2048 of 2048 pixels each (seeds q282_r10_heldout.out)."""
    r9 = pins.module("data:render/closing-r9-x/gen/srgb.py", "r9x_srgb")
    ra, rb = r9.pair_rows(9051), r9.pair_rows(9052)
    specs = {"srgb-a1": r9.spec_a(ra), "srgb-a2": r9.spec_a(rb),
             "srgb-b1": r9.spec_b(r9.pair_rows(9053)), "srgb-b2": r9.spec_b(r9.pair_rows(9054)),
             "srgb-c1": r9.spec_a(ra, 21), "srgb-c2": r9.spec_a(rb, 43)}
    for n, sp in specs.items():
        assert SRGB.predict(sp, "R10-BF11") == pins.kept_pixels(R9X % ("srgb/" + n)), n
    cases = {c["name"]: c for c in json.loads(pins.blob(SRGB.E723_CASES))}
    for n in ("g-bl-st-a", "g-bl-st-b"):
        hw = pins.kept_pixels(f"data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/{n}.txt.gz")
        assert SRGB.predict(cases[n]["spec"], "R10-BF11") == hw, n


def test_q282_matches_the_seeds_rule_file():
    f = os.path.join(SEEDS, "q282/q282_r10_rule.json")
    if not os.path.exists(f):
        pytest.skip("the seeds directory is not here (a published copy)")
    assert hashlib.sha256(open(f, "rb").read()).hexdigest().startswith("e9623e35")
    rule = json.load(open(f))
    assert rule["name"] == "R10-BF11-FLOOR-RHU-W0" and "XY" in rule["two_stage_combinations_declared_before_scoring"]
    assert Q.half_rhu(Q.F(1) + Q.F(1, 2048)) == 0x3c01          # a tie between halves goes up
    assert Q.half_rne(1.0 + 2.0 ** -11) == 0x3c00                # where nearest-even goes down


def test_cube3_ties_are_the_seeds_rows():
    f = os.path.join(SEEDS, "q284/rows_a.json")
    if not os.path.exists(f):
        pytest.skip("the seeds directory is not here (a published copy)")
    seeds = json.load(open(f))
    for k, v in list(C.CC3.items()) + list(C.RR3.items()) + [("a2-replay", C.A2)]:
        assert [list(s) for s in v] == seeds[k]["spec"], k
        two = sum(1 for c in C.tie_cells(v).values() if len(C.tied_axes(c)) == 2)
        assert two == seeds[k]["two_axis_ties"], k


# ---- the rivals part, the reads fit --------------------------------------------------------------
def differ(stage, name, a, b):
    return sum(x != y for x, y in zip(tokens(stage, name, a), tokens(stage, name, b)))


def test_rivals_part():
    for n in A.NONSQUARE + ("addr3-ns32x8-u4",):
        ms = A.MODE4
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                assert differ("addr3", n, ms[i], ms[j]) == 2048, (n, ms[i], ms[j])
    for n in ("addr3-16x32-u5", "addr3-32x16-u5"):
        assert differ("addr3", n, "H-B5", "H-B5H") == 2048
    assert differ("t3b", "t3b-s256", "R-4096", "H-U01") == 2048
    assert differ("t3b", "t3b-s16h64", "R-4096", "H-U01") == 2048
    assert differ("t3b", "t3b-offgrid", "R-4096", "R-ROUND") == 2048
    assert differ("t3b", "t3b-clamp", "R-4096", "H-URAW") == 1024
    assert differ("t3b", "t3b-vramp", "R-4096", "H-UV") == 2048
    assert differ("t3b", "t3b-f16", "R-4096", "R-4096TX") == 1024
    assert differ("srgb2", "srgb2-offgrid", "R10-BF11", "R10-BF11-ROUND") >= 2000
    assert differ("srgb2", "srgb2-k0b", "R10-BF11", "H-K0FLOOR") >= 600
    sub = [int(t, 16) for t in tokens("srgb2", "srgb2-sub", "R10-BF11")]
    assert sum(1 for v in sub for c in (0, 1) if not v >> 16 * c & 0x7C00 and v >> 16 * c & 0x3FF) >= 400
    for k in ("zx", "yx"):
        a = tokens("cube3", "cube3-edge-" + k, "H-SEAM-FLOAT")
        b = tokens("cube3", "cube3-edge-" + k, "H-SEAM-ADJ")
        outs = [i for i, t in enumerate(a) if t.startswith("o:")]
        ins = [i for i, t in enumerate(a) if t.startswith("i:")]
        assert len(outs) == 512 and len(ins) == 1024
        far = [i for i in outs if max(abs(float(p) - float(q)) for p, q in
                                      zip(a[i][2:].split(","), b[i][2:].split(","))) > 2]
        assert len(far) == 512, k                      # 2 x TOL apart: one rival must fail
    for name, st, spec, n, t0, kind in C.jobs3():
        if kind == "tie":
            assert sum(1 for c in C.tie_cells(spec).values() if len(C.tied_axes(c)) == 2) == 2048


def test_the_plans_along_725_would_not_part():
    """The deviation: at +z/+x the plan's along texel 7.25 parts the edge rivals on no out pixel."""
    R = C.rule()
    spec = (C._RAMPE, C.const(0.0703125), C.const(0.75))
    c = tuple(T.coord(s, 0, 0) for s in spec)
    assert C.st(R, c, 16)[2] == T.F(29, 4) or C.st(R, c, 16)[1] == T.F(29, 4)
    a, b = C.edge_tokens(R, spec, "H-SEAM-FLOAT"), C.edge_tokens(R, spec, "H-SEAM-ADJ")
    assert not [i for i, t in enumerate(a) if t.startswith("o:") and max(
        abs(float(p) - float(q)) for p, q in zip(t[2:].split(","), b[i][2:].split(","))) > 2]


def rows(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            out.append(ln.rstrip("\n").split("|", 5))
    return out


def test_addr3_reads_fit_the_mapping():
    for name, st, risk, knobs, tool, args in rows("addr3"):
        a = args.split()
        assert a[a.index("--scratch-pages") + 1] == "32"
        assert "mov r22, #0x5cafc000" in open(os.path.join(KP, "bins", name + ".s")).read()
        for f in os.listdir(os.path.join(KP, "predictions/addr3")):
            if f.startswith(name + "."):
                idx = [int(t, 16) & 0x0FFFFFFF for t in tokens("addr3", name, f.split(".")[1])]
                assert min(idx) >= A.BASE - 1024 and max(idx) < 32 * 1024 - 1024, (name, f)


def test_t3b_reads_fit_the_mapping():
    for name, st, risk, knobs, tool, args in rows("t3b"):
        a = args.split()
        pages = int(a[a.index("--scratch-pages") + 1]) if "--scratch-pages" in a else 16
        for f in os.listdir(os.path.join(KP, "predictions/t3b")):
            if f.startswith(name + ".") and f.count(".") == 2:
                tk = tokens("t3b", name, f.split(".")[1])
                if tk[0].startswith("h:"):
                    continue                     # the 16-bit pair: T3.f16_extent, asserted in gen
                idx = [int(t, 16) & 0x0FFFFFFF for t in tk]
                assert min(idx) >= 0 and max(idx) < (pages - 1) * 1024, (name, f)
