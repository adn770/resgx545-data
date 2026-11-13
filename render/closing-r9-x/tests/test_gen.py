# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r9-x's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the texture programs rebuild E566's and E723's
published programs byte for byte; the frozen models reproduce what they were formed on (Q078's
three E566 jobs, Q282's fit scores on E723's g-bl-st-a, E684's far21d0 image); every coordinate the
programs compute is exact in float32; every rival's reads fit in the probe's scratch pages (the
plan's check 3); every far vertex is a coordinate t4 takes and its clip word is exact (check 2)."""
import gzip
import json
import os
import re
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import far as FAR  # noqa: E402
import pins  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402
import tex  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    T3.jobs()
    SRGB.jobs()
    FAR.jobs()
    for p in ("data:texture/p1141/stage-bins/p1141-t0b27__4.bin",
              "data:texture/p1132-recomp/raw/tx-t3bits/bins/tx-t3bits__0.bin",
              "data:texture/p1132-recomp/raw/tx-t3bits/bins/tx-t3bits__14.bin",
              "data:texture/p1132/tx-t3/s32x32-t3b14.txt.gz",
              "data:isp/coverage-envelope/far/raw/1401720.txt.gz"):
        pins.blob(p)
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_programs_rebuild_the_published_ones():
    S = T3.specs()
    for name, binname in (("s64x32-ctl", "tx-t3bits__0"), ("s64x32-t3b14", "tx-t3bits__14")):
        pub = pins.blob(f"data:texture/p1132-recomp/raw/tx-t3bits/bins/{binname}.bin")
        assert tex.assemble(tex.text(S[name]["spec"])) == pub, name
    cases = {c["name"]: c for c in json.loads(pins.blob(SRGB.E723_CASES))}
    pub = pins.blob("data:texture/p1141/stage-bins/p1141-t0b27__4.bin")
    assert tex.assemble(tex.text(cases["g-bl-st-a"]["spec"])) == pub
    for n, b in (("t3-ctl", "tx-t3bits__0"), ("t3-b14ref", "tx-t3bits__14")):
        assert open(os.path.join(KP, "bins", n + ".bin"), "rb").read() == pins.blob(
            f"data:texture/p1132-recomp/raw/tx-t3bits/bins/{b}.bin")
    assert open(os.path.join(KP, "bins/srgb-ctl.bin"), "rb").read() == pub


def test_programs_fit_the_probe():
    for f in os.listdir(os.path.join(KP, "bins")):
        if f.endswith(".bin"):
            n = os.path.getsize(os.path.join(KP, "bins", f))
            assert n % 8 == 0 and n <= 256 * 8, (f, n)       # PROBE_MAX_WORDS, sgxfive-test.c


def test_t3_rivals_on_e566():
    """The three rivals on E566's kept bit-14 jobs: all exact at W = S with u on texel centres;
    at s32x32 (u past the texture) H-U01 alone (q078_ru.out: R-U01 2048, R-U and R-URAW 1024)."""
    S = T3.specs()
    for name, want in (("s64x32-t3b14", {"H-UCOL": 2048, "H-U01": 2048, "H-URAW": 2048}),
                       ("s32x32-t3b14", {"H-UCOL": 1024, "H-U01": 2048, "H-URAW": 1024})):
        hw = pins.kept_pixels(T3.E566 % name)
        m, _, _ = T3.models(S[name]["spec"])
        got = {k: sum(a == b for a, b in zip(v, hw)) for k, v in m.items()}
        assert got == want, (name, got)


def test_t3_scratch_holds_every_read():
    for name, st, knobs, sp, models, extra, npages in T3.jobs():
        if npages is None:
            continue
        top = max(v & 0x0FFFFFFF for im in models.values() for v in im)
        assert top < npages * 1024 and 16 <= npages <= 64, (name, top, npages)
        row = [r for r in open(os.path.join(KP, "tables/t3.txt")) if r.startswith(name + "|")][0]
        m = re.search(r"--scratch-pages (\d+)", row)
        assert (int(m.group(1)) if m else 16) == npages


def test_t3_bit14_rows_set_bit14():
    for name, *_ in T3.B14ROWS:
        s = open(os.path.join(KP, "bins", name + ".s")).read()
        t3 = int(re.search(r"mov r23, #(0x[0-9a-f]+)", s).group(1), 16)
        assert t3 & 1 << 14, name


def test_texture_coordinates_exact():
    for jobs in (T3.jobs(), SRGB.jobs()):
        for j in jobs:
            sp = j[3]
            for ax in ("u", "v"):
                if sp[ax][0] != "lin":
                    continue
                for p in range(2048):
                    assert tex.exact_f32(tex.coord(sp[ax], p % 64, p // 64)), (j[0], ax, p)


def test_srgb_rivals_reproduce_their_fit():
    """q282_rule.json fit 1506 pixels and q282_rule3.json 1493 on E723's g-bl-st-a."""
    cases = {c["name"]: c for c in json.loads(pins.blob(SRGB.E723_CASES))}
    sp = cases["g-bl-st-a"]["spec"]
    hw = pins.kept_pixels(SRGB.E723_A)
    for m, want in (("H-HALF2", 1506), ("H-BF11", 1493)):
        got = sum(a == b for a, b in zip(SRGB.predict(sp, SRGB.RIVALS[m]), hw))
        assert got == want, (m, got)


def test_srgb_eq_is_every_rivals():
    sp = SRGB.spec_a(SRGB.eq_rows(9050))
    eq = SRGB.eq_value(sp)
    for m in SRGB.MODELS:
        assert SRGB.predict(sp, SRGB.RIVALS[m]) == eq, m


def e684_image(case):
    txt = gzip.decompress(pins.blob(f"data:isp/coverage-envelope/far/raw/{case}.txt.gz")).decode()
    rows = {}
    for m in re.finditer(r"^rle (\d+): (.*)$", txt, re.M):
        px = []
        for t in m.group(2).split():
            v, _, n = t.partition("x")
            v, n = (t[:10], t[11:]) if t.startswith("0x") else (v, n)
            px += [int(v, 16)] * int(n)
        rows[int(m.group(1))] = px
    return [v for y in range(64) for v in rows[y]]


def test_far_control_is_e684s_image():
    img = e684_image(1401720)
    pred = [r for r in FAR.jobs() if r[0] == "far-ctl"][0][4]["H-EXACT"]
    got = [v == FAR.TRI_COLOUR for v in img]
    assert sum(got) == 208
    assert all(p is None or p == g for p, g in zip(pred, got))


def test_far_vertices_take_and_exact():
    for name, verts in FAR.FAR:
        for p in verts:
            for c in p:
                v = FAR.u(c)
                assert -(1 << 30) <= v < 1 << 30, (name, c)
                ndc = tex.F(v, (1 << (FAR.UNIT - 1)) * 64) - 1
                assert tex.exact_f32(ndc), (name, c)


def test_far_rows_separate_rivals():
    """every row past 2^23 pixels separates H-EXACT from H-WRAP and from H-CULL"""
    for name, st, knobs, args, models in FAR.jobs():
        if st != "heldout":
            continue
        e = models["H-EXACT"]
        assert any(x is not None and x != y for x, y in zip(e, models["H-CULL"])), name
        if any(abs(c) > 2 ** 23 for p in dict(FAR.FAR)[name] for c in p) or name.endswith("23p"):
            assert any(x is not None and y is not None and x != y
                       for x, y in zip(e, models["H-WRAP"])), name
