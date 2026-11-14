# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator current, its inputs pinned, and its models replayed on the
kept records they were fitted on and held out of:

- E1055's fit (N13 = 39 W + 52 + (x mod W) on types 1 and 3, N4 = 40 W + 20 + (x mod W); modes 6
  and 7 the last column N(W) + W - 1) reproduces every kept mode 4, 6 and 7 row at 16 x 16 and 32 x
  32 (E1055's, 10 of 10, with the halving types_post.py's), the references R-W (types 1, 3) and R-32
  (type 4) the kept mode 0 images at 16 x 16 (E567) and 32 x 32; the rivals fail where frozen;
- the control's program is E1055's, the type programs are E567's but for T0's u mode, T1's size and
  the `map` widths (the rebuilt 16 x 16 mode 4 program is r14-tex's byte for byte);
- every row parts the tested form from each rival (at least 256 pixels), the reads of every frozen
  model are inside the 32 mapped pages; the rivals' extra premises (README.md "Deviations" 3)."""
import gzip
import json
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import tex  # noqa: E402
import ty as TY  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R15 = TY.R15_OUT
E567 = {1: "data:texture/p1132/tx-types-risky/rt1-2d.txt.gz",
        3: "data:texture/p1132/tx-types/ty3-2d.txt.gz",
        4: "data:texture/p1132/tx-types-risky/rt4-2d.txt.gz"}
TYPES_POST = "data:render/closing-r15-tex/fold/types_post.py"
R14_KEPT = "data:render/closing-r14-tex/out/20261114-054258/addr5/addr5-ty%d-u4.txt.gz"
R14_BIN = "data:render/closing-r14-tex/bins/addr5-ty1-u4.bin"
TEST_PINS = ({TYPES_POST, R14_BIN} | set(E567.values()) | {R14_KEPT % t for t in (1, 3, 4)}
             | {R15 % f"ty-32-ty{t}-{m}" for t in (1, 3, 4) for m in ("u0", "u4")}
             | {R15 % f"ty-16-ty{t}-u{m}" for t in (1, 4) for m in (5, 6, 7)})


def tokens(name, model):
    return open(os.path.join(KP, f"predictions/ty/{name}.{model}.txt")).read().split()


def kept(pin):
    return ["%08x" % v for v in pins.kept_pixels(pin)]


def jobs():
    return {j[0]: j for j in TY.jobs()}


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_input_is_pinned():
    import make
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))
    assert TEST_PINS <= set(CFG["freeze"]["pins"]), sorted(TEST_PINS - set(CFG["freeze"]["pins"]))


def test_halving_is_types_posts():
    src = pins.blob(TYPES_POST).decode()
    assert "return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))" in src


def test_fit_on_e1055s_kept_rows():
    """The two sizes the fit was made on: every mode 4 row, and modes 6 and 7 as the last column."""
    for ty in (1, 3, 4):
        for sz, pin in ((16, R14_KEPT % ty), (32, R15 % f"ty-32-ty{ty}-u4")):
            want = TY.name_tokens(lambda x: TY.n_fit(ty, sz, sz, x))
            assert kept(pin) == want, (ty, sz)
            assert kept(pin) != TY.name_tokens(lambda x: TY.n_fit(ty, sz, sz, x) + 1)
    for ty in (1, 4):
        for m in (6, 7):
            want = TY.name_tokens(lambda x: TY.n_fit(ty, 16, 16, 15))
            assert kept(R15 % f"ty-16-ty{ty}-u{m}") == want, (ty, m)
        assert len(set(kept(R15 % f"ty-16-ty{ty}-u5"))) == 1       # mode 5: one value
    # the quadratic rival passes through the same two sizes (a fit point, not a test)
    for ty in (1, 3, 4):
        for sz in (16, 32):
            assert [TY.n_quad(ty, sz, sz, x) for x in range(64)] == [
                TY.n_fit(ty, sz, sz, x) for x in range(64)], (ty, sz)


def test_references_on_kept_images():
    for ty in (1, 3, 4):
        for sz, pin in ((16, E567[ty]), (32, R15 % f"ty-32-ty{ty}-u0")):
            m = TY.ref_models(ty, sz, sz)
            held = {k for k, v in m.items() if v == kept(pin)}
            assert TY.STRIDE_W[ty] in held, (ty, sz, held)
            if ty != 4:
                assert held == ({"R-W", "R-16"} if sz == 16 else {"R-W", "R-32"}), (ty, sz)
        # 16 x 16: type 4's constant 32 is also 2 W
        assert {k for k, v in TY.ref_models(4, 16, 16).items() if v == kept(E567[4])} == {
            "R-32", "R-2W"}


def test_programs():
    b = lambda n: open(os.path.join(KP, "bins", n + ".bin"), "rb").read()  # noqa: E731
    assert b("ty-ty1u4r") == pins.blob(TY.CTL_BIN) == pins.blob(R14_BIN)
    assert tex.assemble(tex.text(TY.spec(1, 4, 16, 16))) == pins.blob(R14_BIN)
    for name in jobs():
        if name == "ty-ty1u4r":
            continue
        _, sz, ty, um = name.split("-")
        w, h = TY.SIZES[sz]
        t1 = t_word(name, "r21")
        assert t1 >> 29 == int(ty[2:]) and (t1 & 0xFFFFFF) == (w - 1) << 12 | (h - 1), name
        assert t_word(name, "r22") == 0x5CAF0000 and t_word(name, "r23") == 0x00800800, name
        base = tex.text(TY.spec(int(ty[2:]), 0, w, h)).splitlines()
        s = open(os.path.join(KP, "bins", name + ".s")).read().splitlines()
        d = [(x, y) for x, y in zip(base, s) if x != y]
        mode = int(um[1])
        assert len(base) == len(s) and len(d) == (mode != 0), name
        if mode:
            assert d[0][0].startswith("mov r20, ")
            assert int(d[0][1].split("#")[1], 16) == int(d[0][0].split("#")[1], 16) | mode << 6
        assert t_word(name, "r20") >> 6 & 7 == mode and t_word(name, "r20") >> 3 & 7 == 0


def t_word(name, reg):
    import re
    text = open(os.path.join(KP, "bins", name + ".s")).read()
    return int(re.search(rf"mov {reg}, #0x([0-9a-f]+)", text).group(1), 16)


def test_map_widths():
    """u maps log2 W bits of x, v log2 H bits of y (a 64 x 64 texture's rows past 31 are never
    drawn: the fill is 64 x 32)."""
    for name in jobs():
        if name == "ty-ty1u4r":
            continue
        sz = name.split("-")[1]
        w, h = TY.SIZES[sz]
        text = open(os.path.join(KP, "bins", name + ".s")).read()
        assert f"and.skipinv r1, r1, #{w - 1}\n" in text and f"and.skipinv r1, r1, #{h - 1}\n" in text


def test_rows_part_their_models():
    for name, j in jobs().items():
        pix = j[4]
        if name == "ty-ty1u4r":
            continue
        ms = list(pix)
        tested = ms[0]
        for m in ms[1:]:
            d = sum(a != b for a, b in zip(pix[tested], pix[m]))
            if name.endswith("-u0"):
                # references: the strides part on every row but those a coincident stride shares
                # (type 4 at 8 x 8: R-2W and R-16 are one image, both parted from R-32)
                assert d >= 256, (name, tested, m, d)
            elif name.endswith(("-u5",)):
                assert d == 0           # H-AS-U4 is the mode 4 image; scored beside the forms
            elif name.endswith(("-u6", "-u7")) and m == "H-AS-U4":
                assert d >= 2048 - 64
            else:
                assert d >= 256, (name, tested, m, d)
    # mode 6 and 7: the last column parts from the mode 4 image on every pixel but column W - 1
    p = jobs()["ty-64-ty1-u6"][4]
    assert sum(a != b for a, b in zip(p["L13"], p["H-AS-U4"])) == 2048 - 32
    # mode 4 vs the mode 0 reference: names against stride rasters share nothing
    for sz in ("08", "64", "6416"):
        for ty in (1, 4):
            r, m4 = f"ty-{sz}-ty{ty}-u0", f"ty-{sz}-ty{ty}-u4"
            if r in jobs() and m4 in jobs():
                assert all(a != b for a, b in zip(jobs()[r][4][TY.STRIDE_W[ty]],
                                                  jobs()[m4][4]["N13" if ty != 4 else "N4"]))
    # 64 x 16: the width form and the height form (max(W, H) = W: not parted)
    p = jobs()["ty-6416-ty1-u4"][4]
    assert sum(a != b for a, b in zip(p["N13"], p["N13-H"])) == 2048
    assert p["N13"] == jobs()["ty-64-ty1-u4"][4]["N13"]


def test_values_the_plan_states():
    """The plan's numbers: NQ 520 / 3796 at 8 / 64 (types 1, 3); N13 and N4 at 64 x 64 and 8 x 8."""
    assert (TY.n_quad(1, 8, 8, 0), TY.n_quad(1, 64, 64, 0)) == (520, 3796)
    assert (TY.n_quad(4, 8, 8, 0), TY.n_quad(4, 64, 64, 0)) == (500, 3860)
    assert [TY.n_fit(1, m, m, 0) for m in (8, 16, 32, 64)] == [364, 676, 1300, 2548]
    assert [TY.n_fit(4, m, m, 0) for m in (8, 16, 32, 64)] == [340, 660, 1300, 2580]
    assert (TY.n_fit(1, 16, 64, 0), TY.n_fit(1, 64, 64, 63)) == (676, 2611)


def test_reads_inside_the_scratch():
    """Every name a frozen model reads, and every stride raster, is below the 32 mapped pages."""
    top = 0
    for name, j in jobs().items():
        for toks in j[4].values():
            for t in toks:
                if int(t, 16) >> 28 == 0xD:                  # a name (references and the control)
                    top = max(top, int(t, 16) & 0x0FFFFFFF)
    names = [n for n in jobs() if n.endswith("-u4")]
    assert names
    for n in names:                                         # halved names: unhalve and bound
        for toks in jobs()[n][4].values():
            assert all(int(t, 16) >> 24 == 0x68 for t in toks)
    assert top < TY.LIMIT
    assert TY.n_quad(4, 64, 64, 63) < 4096 and TY.LIMIT == 32768


def test_kept_gz_names():
    for p in TEST_PINS:
        if p.endswith(".gz"):
            assert gzip.decompress(pins.blob(p))
    assert json.loads(pins.blob(tex.SPECS))[TY.TYPES[1]]["spec"]["ins"] == "none"
