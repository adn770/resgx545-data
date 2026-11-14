# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r17-tw's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the copied files are r16-tw's published ones;
bl64leftr reruns E1058's bl64left program byte for byte; each reference differs from a bit-14 row
in T3 (and its filter) only; the coordinates are exact, in range, and step at most one texel a
pixel, with whole-64th weights under every bilinear form; H-WIDE is re-derived from the kept files
(R17-2 a: 16384 of 16384 within 1, the left wrap 124 of 128 exact against 0 of 128); the SAFE
CLASS premise: every rival's farthest dword is below 262144 (t14's 1 MiB scratch) on every row,
in fact below 150000, inside E1058's reach of 224351; the widths never run with bit 14 last,
each after its reference; and on every held-out row the frozen forms part as the plan says."""
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import derive  # noqa: E402
import law  # noqa: E402
import pins  # noqa: E402
import tex  # noqa: E402
import tw17 as T  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
SCRATCH_DW = 256 * 1024
E1058_REACH = 224351


def binfile(name):
    return open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    T.jobs()
    derive.bilinear()
    derive.point()
    for p in (T.R16 + "gen/pins.py", T.R16 + "gen/tex.py", T.R16 + "gen/law.py",
              T.R16 + "lead/build_tool14.sh", "data:render/closing-r14-flag/lead/build_tool14.sh",
              T.KEPT16 + "cases.tsv", derive.KEPT15 + "cases.tsv", T.BL64L_BIN, tex.TEMPLATE,
              tex.BUILD, tex.TEXMODEL, "resgx545:tools/usse-asm/closing_tables.py",
              "resgx545:crates/sgx-sim/src/tex.rs",
              "resgx545:crates/sgx-pipe/tests/texture_t3b14.rs"):
        pins.blob(p)                       # the programs' inputs and what the replay reads
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))
    assert set(CFG["freeze"]["pins"]) <= pins.READ, sorted(set(CFG["freeze"]["pins"]) - pins.READ)


def test_copied_files_are_r16_tws():
    """gen/law.py and gen/tex.py are r16-tw's byte for byte; gen/pins.py r16-tw's but for the
    lines naming the session; lead/build_tool14.sh is the published recipe t14 was built with
    (closing14/k14/TOOL14.built; r14-flag's, r16-tw's copy)."""
    for f in ("law.py", "tex.py"):
        assert open(os.path.join(KP, "gen", f), "rb").read() == pins.blob(T.R16 + "gen/" + f), f
    strip = lambda t: [ln for ln in t.splitlines() if "r16" not in ln and "r17" not in ln]  # noqa
    assert strip(pins.blob(T.R16 + "gen/pins.py").decode()) == \
        strip(open(os.path.join(KP, "gen/pins.py")).read())
    rec = open(os.path.join(KP, "lead/build_tool14.sh"), "rb").read()
    assert rec == pins.blob(T.R16 + "lead/build_tool14.sh")
    assert rec == pins.blob("data:render/closing-r14-flag/lead/build_tool14.sh")


def test_bl64leftr_is_e1058s_program_and_the_specs():
    assert binfile(T.CTL_REP) == pins.blob(T.BL64L_BIN)
    assert tex.assemble(tex.text(T.spec(T.CTL_REP))) == pins.blob(T.BL64L_BIN)
    assert T.spec(T.CTL_REP) == T.tw16().spec("bl64left")
    for n, _, w, h, kind, b14, _, _ in T.ROWS:
        sp = T.spec(n)
        assert sp["t1"] == 12 << 24 | (w - 1) << 12 | (h - 1) and sp["base"] == 0, n
        assert sp["t3"] == T.T3 | (T.B14 if b14 else 0), n
        assert sp["t0"] == (T.T0_BL if kind == "bil" else T.T0_PT), n
        assert b14 == (kind != "ref"), n
    # a reference and a bit-14 point program of the same size differ in the T3 word only
    a = tex.assemble(tex.text(dict(T.spec("ref256"), t3=T.T3 | T.B14)))
    b = binfile("ref256")
    assert len(a) == len(b) and len([i for i in range(0, len(a), 8) if a[i:i + 8] != b[i:i + 8]]) == 1


def test_coordinates_exact_ranges_lod_and_whole_64ths():
    """Every pixel's u and v are exact float32 values and equal texmodel's ev() of the spec; u
    steps at most one texel a pixel, v at most one texel a pixel row, v in (0, 1]; every
    bilinear form's weights are whole 64ths on every pixel (taps() asserts it)."""
    tm = pins.module(tex.TEXMODEL)
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        sp = T.spec(n)
        us, vs = [], []
        for x, y in T.pixels():
            u, v = T.uv(n, x, y)
            assert tex.exact_f32(u) and tex.exact_f32(v), (n, x, y)
            assert T.F(tm.ev(sp["u"], x, y)) == u and T.F(tm.ev(sp["v"], x, y)) == v
            if kind == "bil":
                for m in T.BIL:
                    if m != "H-POINT":
                        T.taps(m, u, v, w, h)
            us.append(u)
            vs.append(v)
        assert 0 < (us[1] - us[0]) * w <= 1, n
        assert 0 < (T.uv(n, 0, 1)[1] - T.uv(n, 0, 0)[1]) * h <= 1, n
        assert 0 < min(vs) and max(vs) <= 1, n


def test_h_wide_rederived_from_the_kept_files():
    """R17-2 (a): on the eight kept bilinear bit-14 rows of E1049 and E1058 H-WIDE gives 16384 of
    16384 pixels within 1 a byte (12408 exact); at the 128 left-wrap pixels H-WIDE is exact on 124
    and H-WIDE-G on 0 (the plan's calc/q078_exact.out, reproduced here); H-WIDE-G and H-WIDE-NEXT
    are H-WIDE's within-1 image there (no kept pixel crosses the right wrap); E1058's post hoc
    UNWRAP-G and E1049's F-FRAC miss kept pixels. On every kept bit-14 point row of both rounds
    H-WIDE-PT and H-TWP name the same dword and H-WIDE-PT gives 2048 of 2048."""
    b = derive.bilinear()
    assert len(b) == 8
    tot = {m: sum(r[m][0] for r in b.values()) for m in T.BIL}
    exact = {m: sum(r[m][1] for r in b.values()) for m in T.BIL}
    assert tot["H-WIDE"] == 16384 and exact["H-WIDE"] == 12408
    assert tot["H-WIDE-G"] == tot["H-WIDE-NEXT"] == 16384
    assert tot["UNWRAP-G"] == 14864 and tot["F-FRAC"] == 13888 and tot["H-POINT"] < 8192
    lw = [sum(r["leftwrap"][k] for r in b.values()) for k in range(3)]
    assert lw == [128, 124, 0]
    assert all(r["H-WIDE"][0] == 2048 for r in b.values())
    p = derive.point()
    assert len(p) == 14 and all(v == (0, 2048) for v in p.values()), p


def test_safe_class_every_rival_inside_the_scratch():
    """SAFE CLASS: on every row, every frozen model's (every rival's) farthest dword is below
    262144 (t14's 256 pages); in fact below 150000, inside E1058's reach (224351), so no row reads
    a range never read before. bl64leftr: every bilinear form of this stage and H-WIDE-PT."""
    worst = 0
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        for m in T.models(n):
            for rd in T.reads(n, m):
                assert all(0 <= i < SCRATCH_DW for i in rd), (n, m)
            worst = max(worst, T.reach(n, m))
    assert worst == 147541 < 150000 < E1058_REACH < SCRATCH_DW, worst


REACH = {  # row: {model: its farthest dword} (README "Reach"; the report)
    "bl16left": {"H-WIDE": 131583, "H-WIDE-NEXT": 131583, "H-WIDE-G": 69879, "UNWRAP-G": 69879,
                 "F-FRAC": 69879, "H-POINT": 69877},
    "bl256edge": {"H-WIDE": 139263, "H-WIDE-NEXT": 139349},
    "bl512edge": {"H-WIDE": 147455, "H-WIDE-NEXT": 147541},
    "bl2048edge": {"H-WIDE": 98303, "H-WIDE-NEXT": 98389},
    "pt128off": {"H-WIDE-PT": 68183, "H-TWP": 68183},
}


def test_reach_per_rival():
    for n, ms in REACH.items():
        for m, r in ms.items():
            assert T.reach(n, m) == r, (n, m, T.reach(n, m))


def test_run_order_new_widths_last_after_their_references():
    """The plan's order: bl64leftr first, the W <= 128 rows, then each new width's reference
    before its rows, the W 256, 512 and 2048 bit-14 rows last; each reference's sentinel is its
    farthest dword, in its frozen image, and run/hooks.sh greps exactly it."""
    order = [r[0] for r in T.jobs()]
    assert order[0] == T.CTL_REP
    first_new = min(i for i, n in enumerate(order) if T.row(n)[2] >= 256)
    assert all(T.row(n)[2] <= 128 for n in order[:first_new])
    assert all(T.row(n)[2] >= 256 for n in order[first_new:])
    for n, ref in T.GATE.items():
        if ref:
            assert order.index(ref) < order.index(n) and T.row(ref)[2] == T.row(n)[2], (n, ref)
    hooks = open(os.path.join(KP, "run/hooks.sh")).read()
    for n in T.SENTINEL_ROWS:
        s = T.sentinel(n)
        assert s in T.tokens(n, "REF"), n
        assert f"{n}) s={s} ;;" in hooks, n


def parted(a, b, tol):
    n = 0
    for x, y in zip(a, b):
        if x.startswith("t:"):
            xa, ya = ([int(v) for v in t[2:].split(",")] for t in (x, y))
            n += max(abs(p - q) for p, q in zip(xa, ya)) > tol
        else:
            n += x != y
    return n


# row: {rival: the pixels it parts from the frozen form (H-WIDE / H-WIDE-PT) on, past both
# tolerances (3 or more a byte); H-WIDE-G: the pixels the two differ on exactly (LEFT-WRAP rule)}
PARTS = {
    "bl16left": {"H-WIDE-G": 31, "H-POINT": 1106},
    "bl64grid": {"H-WIDE-G": 31, "H-POINT": 808},
    "bl128off3": {"H-WIDE-G": 31, "UNWRAP-G": 544, "F-FRAC": 640, "H-POINT": 800},
    "bl256edge": {"H-WIDE-G": 31, "H-WIDE-NEXT": 32, "UNWRAP-G": 832, "F-FRAC": 1184,
                  "H-POINT": 830},
    "bl512edge": {"H-WIDE-G": 32, "H-WIDE-NEXT": 64, "UNWRAP-G": 736, "F-FRAC": 1216,
                  "H-POINT": 802},
    "bl256corner": {"H-WIDE-G": 1, "H-WIDE-NEXT": 32, "UNWRAP-G": 821, "F-FRAC": 1167,
                    "H-POINT": 1912},
    "bl2048edge": {"H-WIDE-G": 32, "H-WIDE-NEXT": 320, "UNWRAP-G": 1280, "F-FRAC": 1280,
                   "H-POINT": 844},
    "pt128off": {"H-TWP": 512}, "pt256off": {"H-TWP": 768}, "pt512off": {"H-TWP": 896},
}


def test_frozen_models_part_on_every_held_out_row():
    """Each held-out row parts its frozen form from each rival on exactly PARTS's pixels (a rival
    PARTS does not name is the frozen form's image there within 2 a byte); every rival is parted
    on some row; the left wrap parts on 158 pixels before the W 2048 rows and 189 in all (MIN_LEFT
    64 met by the W <= 128 rows alone: 93); the right wrap parts on 448 pixels, 320 of them on
    bl2048edge (the plan's [check]: 256 or more a row)."""
    seen = set()
    for n, sset, _, _, kind, _, _, _ in T.ROWS:
        if sset == "control":
            continue
        main = T.MAIN_BIL if kind == "bil" else T.MAIN_PT
        im = {m: T.tokens(n, m) for m in T.models(n)}
        for m in T.models(n):
            if m == main:
                continue
            p = parted(im[main], im[m], 0 if m == "H-WIDE-G" else 2)
            assert p == PARTS[n].get(m, 0), (n, m, p)
            seen.add(m) if p else None
    assert seen == (set(T.BIL) | set(T.POINT)) - {T.MAIN_BIL, T.MAIN_PT}
    left = {n: v["H-WIDE-G"] for n, v in PARTS.items() if "H-WIDE-G" in v}
    assert sum(left.values()) == 189 and sum(left[n] for n in ("bl16left", "bl64grid",
                                                                 "bl128off3")) == 93
    right = {n: v.get("H-WIDE-NEXT", 0) for n, v in PARTS.items()}
    assert sum(right.values()) == 448 and right["bl2048edge"] >= 256


def test_wrap_pixels():
    """Where the edges are: the left wrap (x0 = -1) and the right wrap (x0 + 1 = W') pixels of
    each bilinear row; the corner row's every pixel crosses the v edge (y0 = 31)."""
    want = {"bl16left": (32, 0), "bl64grid": (32, 0), "bl128off3": (32, 0),
            "bl256edge": (64, 32), "bl512edge": (128, 96), "bl256corner": (64, 32),
            "bl2048edge": (352, 320)}
    for n, (lw, rw) in want.items():
        assert (len(T.leftwrap(n)), len(T.rightwrap(n))) == (lw, rw), n
    assert all(T.fl(T.uv("bl256corner", x, y)[1] * 32 - T.F(1, 2)) == 31 for x, y in T.pixels())


def test_references_are_e561s_law():
    """The references are E561's law (law.index, tiles 16 x min(H, 16)) read across the u edge:
    columns W - 32 to W - 1 and 0 to 31, every texel row."""
    for n in T.SENTINEL_ROWS:
        _, _, w, h, _, _, _, _ = T.row(n)
        want = ["%08x" % T.name_of(law.index(T.fl(u * w) % w, T.fl(v * h) % h, w, h))
                for u, v in (T.uv(n, x, y) for x, y in T.pixels())]
        assert T.tokens(n, "REF") == want
        cols = {T.fl(T.uv(n, x, 0)[0] * w) % w for x in range(64)}
        assert cols == set(range(w - 32, w)) | set(range(32)), n


def test_derive_out_current():
    """fit/derive.out (the fold cites it) is gen/derive.py's output on the pinned kept files."""
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/derive.py")], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout == open(os.path.join(KP, "fit/derive.out")).read()
