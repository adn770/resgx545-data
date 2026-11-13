# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator current, its inputs pinned, and its models replayed on the
kept records they must hold on (fit rows and controls) and fail on:

- srgb3: c2's rule_b.py at its frozen hash; FTZ-OUT reproduces E723's g-bl-st-a and r10-tex's
  srgb2-sub (E1004's fit row) 2048 of 2048, R10-BF11 misses srgb2-sub (E1004's reading); the
  control programs equal the published ones that ran (r10-tex srgb2-ctl, r9-x an-t3b11).
- addr4: H-MAX reproduces E1000's kept 8 x 32, 16 x 64 and 64 x 16 (the fit), the uv5 region
  models reproduce E565's bd-uv5 (16 x 16 in the uv5 form at base 0, E1017's post hoc fit), H-W
  misses E1000's 16 x 64; every model's farthest read is inside the 32 mapped pages.
- t3c: the level sampler (E561's tile law, texmodel's blend) gives E564's an-t3b11 at level 0
  exactly (c8's decode) and E564's an-ctl at levels 3 and 4 within 1 a byte;
  every bit-14 model's reads are inside the row's pages.
- sb12: E383's runs of each mode lie in that mode's word set (4094 to 4096 of 4096), colour 0's
  mode 8 image does not (so inset parts H-FIXED from a changed image)."""
import gzip
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import addr as A  # noqa: E402
import pins  # noqa: E402
import sb as SB  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R10 = "data:render/closing-r10-tex/out/20261113-102730/%s.txt.gz"
TEST_PINS = {
    "data:render/closing-r10-tex/out/20261113-102730/srgb2/srgb2-sub.txt.gz",
    "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-8x32-u4.txt.gz",
    "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-64x16-u4.txt.gz",
    "data:render/closing-r10-tex/bins/srgb2-ctl.bin",
    "data:render/closing-r9-x/bins/an-t3b11.bin",
    "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/g-bl-st-b.txt.gz",
    "data:texture/p1132/tx-lod/an-ctl.txt.gz",
}


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_input_is_pinned():
    import make
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))
    assert TEST_PINS <= set(CFG["freeze"]["pins"])


def test_rule_b_frozen_hash():
    assert pins.sha(pins.blob(SRGB.RULE_B)) == SRGB.RULE_B_SHA


def test_ftz_out_on_kept_rows():
    import json
    R = SRGB.rule()
    cases = {c["name"]: c for c in json.loads(pins.blob(SRGB.E723_CASES))}
    a = SRGB.predict(R, cases["g-bl-st-a"]["spec"], "FTZ-OUT")
    assert a == pins.kept_pixels(SRGB.E723_A)
    # r10-tex's srgb2-sub: spec_a(sub_rows(10053), 5/64), its pairs from its own seed
    sub = SRGB.spec_a(SRGB.sub_rows(10053), SRGB.F(5, 64))
    kept = pins.kept_pixels(R10 % "srgb2/srgb2-sub")
    assert SRGB.predict(R, sub, "FTZ-OUT") == kept
    assert SRGB.predict(R, sub, "R10-BF11") != kept


def test_control_programs_are_the_published_ones():
    b = lambda n: open(os.path.join(KP, "bins", n + ".bin"), "rb").read()  # noqa: E731
    assert b("srgb3-ctl") == pins.blob("data:render/closing-r10-tex/bins/srgb2-ctl.bin")
    assert b("t3c-ctl") == pins.blob("data:render/closing-r9-x/bins/an-t3b11.bin")


def test_addr_max_on_e1000():
    for name, w, h in (("addr3-8x32-u4", 8, 32), ("addr3-16x64-u4", 16, 64),
                       ("addr3-64x16-u4", 64, 16)):
        job = (name, "fit", w, h, 4, 0, "sweep", A.FMT32)
        kept = pins.kept_pixels(R10 % f"addr3/{name}")
        assert A.image(job, "H-MAX") == kept, name
    job = ("x", "fit", 16, 64, 4, 0, "sweep", A.FMT32)
    assert A.image(job, "H-W") != pins.kept_pixels(R10 % "addr3/addr3-16x64-u4")


def test_uv5_regions_on_bd_uv5():
    """bd-uv5 (16 x 16, base 0): u = x / 16 - 1.46875, v = y / 8 - 1.4375 (its program), so
    s = x - 24 and t = 2 y - 23; the uv5 form at the texel centres gives the same (s, t)."""
    A.UV5_FORM[(16, 16)] = ((1, -24), (2, -23))
    try:
        job = ("bd-uv5", "fit", 16, 16, 5, 5, "uv5", A.FMT32)
        kept = [v + A.BASE for v in pins.kept_pixels(A_BDUV5)]
        for group in (("IN-M", "LR-M", "AB-M", "CO-WH2"), ("IN-W", "LR-H", "AB-W", "CO-12M4")):
            got = [None] * 2048
            for m in group:
                for p, v in enumerate(A.image(job, m)):
                    if v is not None:
                        got[p] = v
            assert None not in got
            assert got == kept, group
    finally:
        del A.UV5_FORM[(16, 16)]


A_BDUV5 = "data:texture/p1132/tx-border/bd-uv5.txt.gz"


def test_addr_reads_inside_the_mapping():
    for job in A.JOBS:
        top = A.farthest(job)
        dwords = top // 2 + 1 if job[7] == A.FMT16 else top + 1
        assert A.BASE + dwords < A.PAGES * 1024, job[0]
        if job[6] == "uv5":
            assert set(A.regions(job)) == {"II", "IO", "OI", "OO"}


def test_t3_level_images_on_e564():
    """Level 0 is E564's an-t3b11 exactly; levels 3 and 4 (round(log2 of E564's gradient LOD),
    x <= 26 level 3) are E564's an-ctl within 1 a byte, every pixel."""
    import math
    sp = T3.rspec(T3.T1_64, T3.T3_B11, 0)
    assert T3.level_image(sp, 0) == pins.kept_pixels(T3.E564 % "an-t3b11")
    ctl = pins.kept_pixels(T3.E564 % "an-ctl")
    lv = {3: T3.level_image(sp, 3), 4: T3.level_image(sp, 4)}
    for p, v in enumerate(ctl):
        m = lv[math.floor(math.log2(8 * (1 + (p % 64) / 64)) + 0.5)][p]
        assert all(abs((m >> 8 * c & 255) - (v >> 8 * c & 255)) <= 1 for c in range(4)), p


def test_t3_b14_reads_inside_pages():
    for name, st, knobs, sp, models, pages in T3.jobs():
        if name.startswith("t3c-b14bl"):
            # the largest dword any tap of any model names: the last row's last texel + 4096
            top = (T3.B14_H - 1) * T3.B14_S + T3.B14_W - 1 + 4096
            assert top < (pages or 16) * 1024


def test_sb_word_sets():
    for mode in range(7):
        w = set(SB.words(pins.blob, mode))
        for im in SB.kept(pins.blob, 0x1200 | mode):
            assert sum(v in w for v in im) == 4096
    m8 = SB.kept(pins.blob, 0x208)[0]
    assert sum(v in set(SB.words(pins.blob, 0)) for v in m8) == 0


def test_kept_gz_names():
    for p in TEST_PINS:
        if p.endswith(".gz"):
            assert gzip.decompress(pins.blob(p))
