# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r15-tw's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the copied files are r14-flag's published ones;
tw-zero reruns E1047's f1-zero program byte for byte and each bit-14 row differs from its
reference in T3 only; the coordinates are exact and step at most one texel a pixel; the SAFE
CLASS premise (R15-2 a): every texture is W x 32 and every row's farthest read under every frozen
model lies inside t14's 1 MiB scratch, with the rows in reach order; the frozen rivals agree with
E1047's three kept images where the plan says they do (H-CLAMP1 is already refuted there); and on
every held-out row the frozen models part."""
import gzip
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import law  # noqa: E402
import pins  # noqa: E402
import tex  # noqa: E402
import tw  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R14 = "data:render/closing-r14-flag/"
SCRATCH_DW = 256 * 1024


def binfile(name):
    return open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def r14f1():
    """r14-flag's published f1 generator (E1047's rows and coordinates), on this session's law,
    pins and tex (the same functions: test_copied_files_are_r14_flags)."""
    return pins.module(R14 + "gen/f1.py", "r14f1")


def kept(name):
    return pins.pixels(gzip.decompress(pins.blob(tw.KEPT + name + ".txt.gz")).decode(errors="replace"),
                       2048)


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    tw.jobs()
    r14f1().jobs()
    for n in ("f1-tw32", "f1-small", "f1-zero"):
        kept(n)
    for p in (R14 + "gen/pins.py", R14 + "gen/tex.py", R14 + "gen/law.py",
              R14 + "lead/build_tool14.sh", tw.KEPT + "cases.tsv",
              "data:render/closing-r10-tex/gen/addr.py"):
        pins.blob(p)
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))


def test_copied_files_are_r14_flags():
    """gen/law.py is r14-flag's byte for byte (r10-tex addr.py's tile law); gen/pins.py and
    gen/tex.py are r14-flag's but for the lines naming the session; lead/build_tool14.sh is the
    published recipe t14 was built with (closing14/k14/TOOL14.built)."""
    assert open(os.path.join(KP, "gen/law.py"), "rb").read() == pins.blob(R14 + "gen/law.py")
    strip = lambda t: [ln for ln in t.splitlines() if "r14" not in ln and "r15" not in ln]  # noqa: E731
    for f in ("pins.py", "tex.py"):
        assert strip(pins.blob(R14 + "gen/" + f).decode()) == \
            strip(open(os.path.join(KP, "gen", f)).read()), f
    assert open(os.path.join(KP, "lead/build_tool14.sh"), "rb").read() == \
        pins.blob(R14 + "lead/build_tool14.sh")


def test_tw_zero_is_e1047s_f1_zero_and_bit14_rows_differ_in_t3_only():
    assert binfile("tw-zero") == pins.blob(tw.ZERO_BIN)
    for ref, b14 in (("tw-ref16", "tw16-u0"), ("tw-ref64", "tw64-u0"), ("tw-ref128", "tw128-u0"),
                     ("tw-refu16", "tw-u16")):
        a, b = binfile(ref), binfile(b14)
        assert len(a) == len(b)
        assert len([i for i in range(0, len(a), 8) if a[i:i + 8] != b[i:i + 8]]) == 1, (ref, b14)
        assert tw.spec(b14) == dict(tw.spec(ref), t3=tw.spec(ref)["t3"] | tw.B14)
    for n, *_ in tw.ROWS:
        sp = tw.spec(n)
        assert sp["t1"] & 0xFFF == 31 and sp["base"] == 0, n          # H = 32, at dword 0
        assert sp["t1"] >> 29 == 0, n                                  # twiddled (type 0)
        assert sp["t3"] & ~tw.B14 == tw.T3 and sp["t0"] in (tw.T0_PT, tw.T0_BL), n


def test_coordinates_exact_ranges_and_lod():
    """Every pixel's u and v are exact float32 values and equal texmodel's ev() of the spec (the
    program's arithmetic); u lies where the plan puts it; u steps at most one texel a pixel and v
    one texel a row (LOD 0 or below, as E1047's rows)."""
    tm = pins.module(tex.TEXMODEL)
    rng = {"u0": (0, 1), "u1": (1, 2), "u2": (2, 3)}
    for n, _, w, _, kind, _, _ in tw.ROWS:
        sp = tw.spec(n)
        us = []
        for y in range(32):
            for x in range(64):
                u, v = tw.uv(n, x, y)
                assert tex.exact_f32(u) and tex.exact_f32(v), (n, x, y)
                assert tw.F(tm.ev(sp["u"], x, y)) == u and tw.F(tm.ev(sp["v"], x, y)) == v
                us.append(u)
        lo, hi = min(us), max(us)
        key = n.rsplit("-", 1)[-1]
        if key in rng:
            assert rng[key][0] < lo and hi < rng[key][1], (n, lo, hi)
        assert (us[1] - us[0]) * w <= 1, n
        assert all(tw.uv(n, 0, y + 1)[1] - tw.uv(n, 0, y)[1] == tw.F(1, 32) for y in range(31))
    # the bilinear rows straddle the wrap at the texture's edge (every footprint's second column
    # wraps): bl32 around u = 1, bl16 around u = 2
    for n, edge in (("tw-bl32", 1), ("tw-bl16", 2)):
        us = [tw.uv(n, x, 0)[0] for x in range(64)]
        assert min(us) < edge <= max(us), n
        w = tw.row(n)[2]
        assert all(tw.fl(u * w - tw.F(1, 2)) % w == w - 1 for u in us), n


def test_safe_class_reach_inside_the_scratch_and_in_order():
    """R15-2 a: H = 32 on every row (above, the T1 height field) and every frozen model's farthest
    read inside the 1 MiB scratch (dwords below 262144, here below 140000: a margin of 120000
    dwords); the rows run in ascending reach, each control before the rows it gates."""
    order = [r[0] for r in tw.jobs()]
    reach = {n: tw.reach(n) for n in order}
    assert max(reach.values()) == 134143 < 140000 < SCRATCH_DW, reach
    assert [reach[n] for n in order] == sorted(reach[n] for n in order)
    for n, models in ((r[0], tw.models(r[0])) for r in tw.ROWS):
        for m in models:
            for rd in tw.reads(n, m):
                assert all(0 <= i < SCRATCH_DW for i in rd), (n, m)
    for n, ref in tw.GATE.items():
        assert order.index(tw.ZERO) < order.index(n)
        if ref:
            assert order.index(ref) < order.index(n)
            assert tw.row(ref)[2:4] == tw.row(n)[2:4], (n, ref)        # the same W and format
    assert reach[tw.ZERO] == 66133                                     # E1047's f1-zero


def test_rivals_on_e1047s_kept_images():
    """At W = 32 H-TWP, H-TWP4128 and H-WRAPW are E1047's form and give its three kept images
    2048 of 2048; H-CLAMP1 gives f1-small and f1-zero (u in [0, 1)) but fails f1-tw32 (u in (1,
    2)): it is carried as the plan's rival though E1047 already refutes it at this width;
    H-TWP4096 gives 1024 of each (E1047's verdict)."""
    f1 = r14f1()
    for row in ("f1-tw32", "f1-small", "f1-zero"):
        want = kept(row)
        for m in tw.POINT:
            got = [tw.name_of(tw.point_index(m, *f1.coords(row, x, y), 32))
                   for y in range(32) for x in range(64)]
            hit = sum(a == b for a, b in zip(got, want))
            if m in ("H-TWP", "H-TWP4128", "H-WRAPW") or (m == "H-CLAMP1" and row != "f1-tw32"):
                assert hit == 2048, (row, m, hit)
            elif m == "H-CLAMP1":
                assert hit < 1024, (row, m, hit)
            else:
                assert hit == 1024, (row, m, hit)
    assert ["%08x" % v for v in kept("f1-zero")] == tw.kept_zero()


def parted(a, b):
    n = 0
    for x, y in zip(a, b):
        if x.startswith("t:"):
            xa, ya = ([int(v) for v in t[2:].split(",")] for t in (x, y))
            n += max(abs(p - q) for p, q in zip(xa, ya)) >= 3          # past both tolerances
        else:
            n += x != y
    return n


def test_frozen_models_part_on_every_held_out_row():
    for n, sset, w, fmt, kind, _, _ in tw.ROWS:
        if sset == "control":
            continue
        ms = tw.models(n)
        im = {m: tw.tokens(n, m) for m in ms}
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                p = parted(im[a], im[b])
                if {a, b} == {"H-TWP", "H-CLAMP1"} and n.endswith("u0"):
                    assert p == 0, n                     # u below 1: one image
                elif {a, b} == {"H-FOOT-TW", "H-FOOT-SHIFT"}:
                    assert p >= 128, (n, a, b, p)
                else:
                    assert p >= 1024, (n, a, b, p)
    # the u past 1 rows part the clamp; the pitch forms part on the tile row from t = 16
    for n in ("tw16-u1", "tw64-u2", "tw128-u2"):
        assert parted(tw.tokens(n, "H-TWP"), tw.tokens(n, "H-CLAMP1")) == 2048
    for n in ("tw16-u0", "tw64-u0", "tw128-u0"):
        a, b = tw.tokens(n, "H-TWP"), tw.tokens(n, "H-TWP4128")
        assert a[:1024] == b[:1024] and parted(a[1024:], b[1024:]) == 1024


def test_controls_and_point_images():
    """The references are E561's law (law.index; u16: the half of the texel's dword); H-POINT is
    H-TWP's point image; a model's image names only scratch dwords."""
    for n in ("tw-ref16", "tw-ref64", "tw-ref128"):
        w = tw.row(n)[2]
        want = ["%08x" % tw.name_of(law.index(tw.fl(u * w) % w, tw.fl(v * 32) % 32, w, 32))
                for u, v in (tw.uv(n, x, y) for y in range(32) for x in range(64))]
        assert tw.tokens(n, "REF") == want
    toks = tw.tokens("tw-refu16", "REF")
    # 512 even texels name their dword's low half; the 512 odd ones read the high half 0xd000
    assert all(t.startswith("h:") for t in toks) and len(set(toks)) == 513
    assert sum(t == "h:d000" for t in toks) == 1024
    for n in ("tw-bl32", "tw-bl16"):
        pt = tw.tokens(n, "H-POINT")
        assert all(t.startswith("t:") and t.endswith(",208") for t in pt), n
