# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator current, its inputs pinned, and its models replayed on the
kept records they must hold on (fit rows and controls) and fail on:

- srgb4: c2's rule_b.py at its frozen hash; on r13-tex's kept srgb3-tri TRI-G15 holds 2048 of
  2048, TRI-RNTU 4091 of 4096 halves (E1025's post hoc count) and TRI-OUT 1137 pixels (E1025's
  frozen verdict); the controls' programs are the published ones (r10-tex srgb2-ctl, r13-tex
  srgb3-tri; srgb4-b2x1 is srgb3-x1's program but for byte 2 and the r11 template); the r11 point
  decode (low half sRGB of byte 2, high half byte 3 / 255) holds on E723's two kept r11 jobs and
  fails with byte 3 sRGB; the r11 template differs from tx_map.s in its last move only.
- every tri row parts the tested form from each rival on at least one pixel, the dark row parts
  the third flush and the LOD 1.2 row Q-FLOOR from Q-NEAR; the alpha rows part A-LIN from both.
- addr5: C-LOG4 and the M regions reproduce r13-tex's kept 64 x 16 and 16 x 64 uv5 rows (E1026's
  post hoc fit, every pixel), CO-WH2 misses them; every shape's regions all hold pixels and every
  model's farthest read is inside the 32 mapped pages; the type references are E567's programs
  byte for byte and the mode 4 rows differ from them in T0's u mode only."""
import gzip
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import addr as A  # noqa: E402
import addr5 as A5  # noqa: E402
import pins  # noqa: E402
import srgb as S  # noqa: E402
import srgb4 as S4  # noqa: E402
import tex  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R13 = "data:render/closing-r13-tex/out/20261113-214825/%s.txt.gz"
E723 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/%s.txt.gz"
TEST_PINS = {
    R13 % "addr4/addr4-64x16-uv5", R13 % "addr4/addr4-16x64-uv5",
    "data:render/closing-r13-tex/bins/srgb3-x1.bin",
    "data:render/closing-r13-tex/bins/addr4-64x16-uv5.bin",
    E723 % "g-st8x4-r11", E723 % "g-tw8x8-r11", E723 % "g-bl-st-b",
    "data:texture/p1141/support/texmodel.py",
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
    assert pins.sha(pins.blob(S.RULE_B)) == S.RULE_B_SHA


def test_tri_forms_on_srgb3_tri():
    R = S.rule()
    kept = pins.kept_pixels(R13 % "srgb3/srgb3-tri")
    sp = S4.tri_spec(S.TRI_LOD)
    halves = lambda im: sum((a >> 16 * c & 0xFFFF) == (b >> 16 * c & 0xFFFF)  # noqa: E731
                            for a, b in zip(im, kept) for c in (0, 1))
    assert S4.tri_image(R, sp, "TRI-G15") == kept
    assert halves(S4.tri_image(R, sp, "TRI-RNTU")) == 4091
    assert halves(S4.tri_image(R, sp, "TRI-RNE")) == 3957
    out = S4.tri_image(R, sp, "TRI-OUT")
    assert sum(a == b for a, b in zip(out, kept)) == 1137


def test_control_programs_are_the_published_ones():
    b = lambda n: open(os.path.join(KP, "bins", n + ".bin"), "rb").read()  # noqa: E731
    import json
    cases = {c["name"]: c for c in json.loads(pins.blob(S.E723_CASES))}
    assert tex.assemble(tex.text(cases["g-bl-st-a"]["spec"])) == b("srgb4-ctl")
    assert b("srgb4-ctl") == pins.blob(S4.R10_CTL_BIN)
    assert tex.assemble(tex.text(S4.tri_spec(S.TRI_LOD))) == b("srgb4-trir")
    assert b("srgb4-trir") == pins.blob(S4.R13_TRI_BIN)
    # srgb3-x1's program, rebuilt by this generator's path, is r13-tex's published one
    x1 = S4.spec_a4([((0, 1, 0x5A, 0xA5), (1, 0, 0xA5, 0x5A))] * 33, 0)
    assert tex.assemble(tex.text(x1)) == pins.blob("data:render/closing-r13-tex/bins/srgb3-x1.bin")


def test_r11_template():
    a = pins.blob(tex.TEMPLATE).decode().splitlines()
    b = pins.blob(S4.R11).decode().splitlines()
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(a) == len(b) and diff == [("mov.skipinv.end o0, r10", "mov.skipinv.end o0, r11")]
    for r in ("srgb4-b2x1", "srgb4-ax", "srgb4-ay", "srgb4-axy"):
        assert "mov.skipinv.end o0, r11" in open(os.path.join(KP, "bins", r + ".s")).read()


def test_r11_point_decode_on_e723():
    """Post hoc, the alpha models' premise: E723's r11 point jobs read half(sRGB(byte 2)) low and
    half(byte 3 / 255) high on every pixel; byte 3 decoded sRGB misses."""
    import json
    R = S.rule()
    TM = pins.module("data:texture/p1141/support/texmodel.py")
    cases = {c["name"]: c for c in json.loads(pins.blob(S.E723_CASES))}
    for n in ("g-st8x4-r11", "g-tw8x8-r11"):
        px = pins.kept_pixels(E723 % n)
        tx = TM.render(cases[n]["spec"])
        lin = [R.half_rne(R.s2l(t >> 16 & 255)) | R.half_rne((t >> 24) / 255.0) << 16 for t in tx]
        srgb = [R.half_rne(R.s2l(t >> 16 & 255)) | R.half_rne(R.s2l(t >> 24)) << 16 for t in tx]
        assert lin == px, n
        assert sum(a == b for a, b in zip(srgb, px)) < 64, n


def test_rows_part_their_models():
    total = {}
    for name, st, tmpl, sp, pin, models in S4.jobs():
        if st != "heldout":
            continue
        p = S4.parts(models)
        if name.startswith("srgb4-t"):
            assert p[("TRI-RNE", "TRI-RNTU")] > 0, name
            for riv in ("TRI-BF11", "TRI-OUT", "TRI-G15"):
                k = tuple(sorted(("TRI-RNTU", riv)))
                total[riv] = total.get(riv, 0) + p[k]
        else:
            assert p[("A-LIN", "A-SRGB")] > 1000 and p[("A-BYTE", "A-LIN")] > 1000, name
    assert min(total.values()) > 100, total
    by = {n: m for n, st, t, sp, pin, m in S4.jobs()}
    dark = S4.parts(by["srgb4-tdark"])
    assert dark[("TRI-G15", "TRI-RNTU")] > 100 and dark[("TRI-RNTU", "TRI-RNTU-NF")] > 100
    assert dark[("TRI-G15", "TRI-G15-NF")] > 100 and dark[("TRI-OUT", "TRI-RNTU")] > 100
    t12 = S4.parts(by["srgb4-t12"])
    assert t12[("QN-TRI-RNTU", "TRI-RNTU")] > 1000


def test_lod_fractions():
    assert [S4.lod_f(lod)[1] for _, lod, _, _ in S4.TRI_ROWS] == [8, 32, 48, 63, 16, 12, 8]
    assert [S4.lod_f(lod)[0] for _, lod, _, _ in S4.TRI_ROWS] == [1, 1, 1, 1, 0, 1, 0]
    assert S4.lod_f(0x3F99999A, near=True) == (1, 13)


def test_uv5_forms_on_r13_rows():
    """C-LOG4 with the M regions is r13-tex's kept 64 x 16 and 16 x 64 uv5 rows, every pixel
    (E1026, post hoc); CO-WH2 misses them."""
    A5.with_forms()
    for w, h in ((64, 16), (16, 64)):
        j = (f"addr4-{w}x{h}-uv5", "fit", w, h, 5, 5, "uv5", A.FMT32)
        kept = pins.kept_pixels(R13 % f"addr4/addr4-{w}x{h}-uv5")
        for corner, ok in (("C-LOG4", True), ("CO-WH2", False)):
            got = [None] * 2048
            for m in ("IN-M", "LR-M", "AB-M", corner):
                for p in range(2048):
                    i = A5.predict(j, m, p % 64, p // 64)
                    if i is not None:
                        got[p] = A.value(A.FMT32, i)
            assert None not in got
            assert (got == kept) == ok, (w, h, corner)


def test_uv5_regions_and_reads():
    A5.with_forms()
    for w, h in A5.SHAPES + A5.LAST:
        j = A5.job(w, h)
        assert set(A.regions(j)) == {"II", "IO", "OI", "OO"}, j[0]
        assert A.BASE + A5.farthest(j) < A.PAGES * 1024, j[0]
    text = open(os.path.join(KP, "bins", "addr5-128x128-uv5.s")).read()
    assert "mov r22, #0x5cafc000" in text


def test_type_programs():
    for ty, (case, binpin, kept) in A5.TYPES.items():
        ref = open(os.path.join(KP, "bins", f"addr5-ty{ty}-u0.bin"), "rb").read()
        assert ref == pins.blob(binpin) == tex.assemble(tex.text(A5.type_spec(ty, 0)))
        a = tex.text(A5.type_spec(ty, 0)).splitlines()
        b = open(os.path.join(KP, "bins", f"addr5-ty{ty}-u4.s")).read().splitlines()
        d = [(x, y) for x, y in zip(a, b) if x != y]
        assert len(d) == 1 and d[0][0].startswith("mov r20, ")
        assert int(d[0][1].split("#")[1], 16) == int(d[0][0].split("#")[1], 16) | 4 << 6
        # E567's kept reads: names, inside 16 pages with the offset added
        px = pins.kept_pixels(kept)
        assert all(v >> 28 == 0xD for v in px)
        assert max(v & 0x0FFFFFFF for v in px) + A5.TYPE_OFFSET < A5.TYPE_PAGES * 1024


def test_kept_gz_names():
    for p in TEST_PINS:
        if p.endswith(".gz"):
            assert gzip.decompress(pins.blob(p))
