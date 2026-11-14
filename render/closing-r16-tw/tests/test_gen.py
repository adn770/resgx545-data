# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r16-tw's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the copied files are r15-tw's published ones;
bl32r reruns E1049's tw-bl32 program byte for byte and each bit-14 row differs from its reference
in T3 only; the coordinates are exact, in range, and step at most one texel a pixel; the SAFE CLASS
premise (R16-2 a): every rival's farthest dword lies inside t14's 1 MiB scratch on every row, with
the rows in reach order, H 64 last, no bilinear row above H 32 and frac(u) <= 0.4 at H 64; the
frozen forms reproduce E1049's kept images where the fold says they do; the H 16 sentinel guards
the H 64 rows; and on every held-out row the frozen models part."""
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
import tw16 as T  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
SCRATCH_DW = 256 * 1024
E1049_POINT = ("tw16-u0", "tw16-u1", "tw64-u0", "tw64-u2", "tw128-u0", "tw128-u2")


def binfile(name):
    return open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    T.jobs()
    for n in E1049_POINT + ("tw-bl32", "tw-bl16"):
        T.kept15(n)
    for p in (T.R15 + "gen/pins.py", T.R15 + "gen/tex.py", T.R15 + "gen/law.py",
              T.R15 + "lead/build_tool14.sh", T.R15 + "fold/bilin_forms.py",
              T.KEPT15 + "cases.tsv", T.BL32_BIN, tex.TEMPLATE, tex.BUILD, tex.TEXMODEL):
        pins.blob(p)                       # the programs' inputs (gen/make.py reads them)
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))
    assert set(CFG["freeze"]["pins"]) <= pins.READ, sorted(set(CFG["freeze"]["pins"]) - pins.READ)


def test_copied_files_are_r15_tws():
    """gen/law.py and gen/tex.py are r15-tw's byte for byte; gen/pins.py r15-tw's but for the
    lines naming the session; lead/build_tool14.sh is the published recipe t14 was built with
    (closing14/k14/TOOL14.built; r15-tw's copy of r14-flag's)."""
    for f in ("law.py", "tex.py"):
        assert open(os.path.join(KP, "gen", f), "rb").read() == pins.blob(T.R15 + "gen/" + f), f
    strip = lambda t: [ln for ln in t.splitlines() if "r15" not in ln and "r16" not in ln]  # noqa
    assert strip(pins.blob(T.R15 + "gen/pins.py").decode()) == \
        strip(open(os.path.join(KP, "gen/pins.py")).read())
    assert open(os.path.join(KP, "lead/build_tool14.sh"), "rb").read() == \
        pins.blob(T.R15 + "lead/build_tool14.sh")


def test_bl32r_is_e1049s_program_and_bit14_rows_differ_in_t3_only():
    assert binfile(T.BL32) == pins.blob(T.BL32_BIN)
    assert tex.assemble(tex.text(T.spec(T.BL32))) == pins.blob(T.BL32_BIN)
    assert T.spec(T.BL32) == T.tw15().spec("tw-bl32")
    for ref, b14 in (("ref32h8", "pt32h8"), ("ref16h64", "pt16h64u0")):
        a, b = binfile(ref), binfile(b14)
        assert len(a) == len(b)
        assert len([i for i in range(0, len(a), 8) if a[i:i + 8] != b[i:i + 8]]) == 1, (ref, b14)
        assert T.spec(b14) == dict(T.spec(ref), t3=T.spec(ref)["t3"] | T.B14)
    for n, _, w, h, kind, b14, _, _ in T.ROWS:
        sp = T.spec(n)
        assert sp["t1"] == 12 << 24 | (w - 1) << 12 | (h - 1) and sp["base"] == 0, n
        assert sp["t3"] == T.T3 | (T.B14 if b14 else 0), n
        assert sp["t0"] == (T.T0_BL if kind == "bil" else T.T0_PT), n


def test_coordinates_exact_ranges_and_lod():
    """Every pixel's u and v are exact float32 values and equal texmodel's ev() of the spec; u
    steps at most one texel a pixel, v at most one texel a pixel row, v in (0, 1]; the bilinear
    weights are whole 64ths; the H 64 rows keep frac(u) <= 0.4 and read tile rows 2 and 3."""
    tm = pins.module(tex.TEXMODEL)
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        sp = T.spec(n)
        us, vs = [], []
        for y in range(32):
            for x in range(64):
                u, v = T.uv(n, x, y)
                assert tex.exact_f32(u) and tex.exact_f32(v), (n, x, y)
                assert T.F(tm.ev(sp["u"], x, y)) == u and T.F(tm.ev(sp["v"], x, y)) == v
                if kind == "bil":
                    T.taps("F-FRAC", u, v, w, h)               # asserts whole 64ths
                us.append(u)
                vs.append(v)
        assert (us[1] - us[0]) * w <= 1, n
        assert (T.uv(n, 0, 1)[1] - T.uv(n, 0, 0)[1]) * h <= 1, n
        assert 0 < min(vs) and max(vs) <= 1, n
        if h == 64:
            assert max(u - T.fl(u) for u in us) <= T.F(2, 5), n
            assert {T.fl(v * h) // 16 for v in vs} == {2, 3}, n


def edge_pixels(n, which):
    _, _, w, h, _, _, _, _ = T.row(n)
    out = 0
    for x, y in T.pixels():
        u, v = T.uv(n, x, y)
        bx = T.fl(w * (u - T.fl(u)) - T.F(1, 2))
        y0 = T.fl(v * h - T.F(1, 2))
        out += {"left": bx == -1, "right": bx == w - 1, "inside": 0 <= bx < w - 1,
                "vedge": y0 % h == h - 1}[which]
    return out


def test_the_plans_bilinear_footprints():
    """Inside rows (bl64in, bl16h16in) keep every footprint inside the texture; bl64left puts
    992 pixels on the left edge (X = -1), bl128right and bl128h16right 1024 on the right edge
    (X = W - 1) and 1024 on the left; bl128vedge every pixel on the v edge."""
    assert edge_pixels("bl64in", "inside") == 2048 and edge_pixels("bl16h16in", "inside") == 2048
    assert edge_pixels("bl64left", "left") == 992                # x < 31 on each pixel row
    for n in ("bl128right", "bl128h16right"):
        assert edge_pixels(n, "right") == 1024 and edge_pixels(n, "left") == 1024, n
    assert edge_pixels("bl128vedge", "vedge") == 2048
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        if kind == "bil":
            assert h <= 32, n                                   # R16-2 a: no bilinear row above 32


def test_safe_class_reach_inside_the_scratch_and_in_order():
    """R16-2 a: every frozen model's (every rival's) farthest read on every row is a dword below
    262144 (here below 230000), H-MOVEH's too on the rows that do not score it; the rows run in
    ascending reach, the H 64 rows last (bl32r is E1049's own row: every bilinear model of this
    stage and of E1049 on it stays inside too)."""
    order = [r[0] for r in T.jobs()]
    reach = {n: T.reach(n) for n in order}
    assert max(reach.values()) == 224351 < 230000 < SCRATCH_DW, reach
    assert [reach[n] for n in order] == sorted(reach[n] for n in order)
    assert order[-4:] == ["pt16h64u0", "pt16h64u1", "pt64h64u0", "pt64h64u1"]
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        ms = T.models(n) if n != T.BL32 else T.BIL
        for m in ms + (("H-MOVEH",) if kind == "point" and h <= 16 else ()):
            for rd in T.reads(n, m):
                assert all(0 <= i < SCRATCH_DW for i in rd), (n, m)
    t15 = T.tw15()
    for m in t15.BIL:
        assert all(0 <= i < SCRATCH_DW for rd in t15.reads("tw-bl32", m) for i in rd)


def test_moveh_at_h64_would_pass_the_scratch_and_the_sentinel_guards_it():
    """H-MOVEH (not scored at H 64) reads past the scratch there, so the H 64 rows rest on the H 16
    move: each H 16 row's sentinel (H-TWP-H's farthest dword) is in H-TWP-H's image, in no H-MOVEH
    image, and run/hooks.sh greps exactly it; both H 16 rows run before every row that reads
    farther than any H 16 row."""
    far = max(max(r) for n in ("pt16h64u0", "pt64h64u0") for r in T.reads(n, "H-TWP-H"))
    moveh64 = max(T.tile(T.fl(T.uv(n, x, y)[0] * 64) % 64 + T.fl(128 * 64 * (T.uv(n, x, y)[0]
                         - T.fl(T.uv(n, x, y)[0]))), T.fl(T.uv(n, x, y)[1] * 64), 64 + 8192, 16)
                  for n in ("pt64h64u0",) for x, y in T.pixels())
    assert moveh64 >= SCRATCH_DW > far
    hooks = open(os.path.join(KP, "run/hooks.sh")).read()
    order = [r[0] for r in T.jobs()]
    for n in T.SENTINEL_ROWS:
        s = T.sentinel(n)
        assert s in T.tokens(n, "H-TWP-H") and s not in T.tokens(n, "H-MOVEH"), n
        assert f"{n}) s={s} ;;" in hooks, n
    last16 = max(order.index(n) for n in T.SENTINEL_ROWS)
    reach16 = max(T.reach(n) for n in T.SENTINEL_ROWS)
    assert all(T.reach(n) <= reach16 for n in order[:last16 + 1])
    assert all(T.row(n)[3] < 64 or not T.row(n)[5] for n in order[:last16 + 1])  # ref16h64: bit clear


def test_forms_on_e1049s_kept_images():
    """E1049's six point images: H-TWP-H, H-TWP-T16, H-MOVEH and H-TWP-V32 are H-TWP at H 32
    (2048 of 2048 each); H-TWP-STRIP and H-TWP4128 give 1024 (refuted there, carried as the plan's
    rivals). Its two bilinear images: F-FRAC 2048 of 2048 each (fold/bilin_forms.py's H-FOOT-FR),
    H-FOOT-SHIFT 1062 and 2048, H-FOOT-TW (= F-WRAP2) 1523 and 1912, F-VNEXT 2031 and 2039: the
    v edge's next tile row already fails E1049's last pixel row (post hoc, carried as the plan's
    rival)."""
    t15 = T.tw15()
    for n in E1049_POINT:
        w, px = t15.row(n)[2], T.kept15(n)
        for m in T.POINT:
            hit = sum(T.name_of(T.point_index(m, *t15.uv(n, x, y), w, 32)) == px[y * 64 + x]
                      for x, y in T.pixels())
            assert hit == (1024 if m in ("H-TWP-STRIP", "H-TWP4128") else 2048), (n, m, hit)
    want = {"tw-bl32": {"F-FRAC": 2048, "F-VNEXT": 2031, "H-FOOT-SHIFT": 1062, "H-FOOT-TW": 1523,
                        "F-WRAP2": 1523},
            "tw-bl16": {"F-FRAC": 2048, "F-VNEXT": 2039, "H-FOOT-SHIFT": 2048, "H-FOOT-TW": 1912,
                        "F-WRAP2": 1912}}
    for n, models in want.items():
        w, px = t15.row(n)[2], T.kept15(n)
        for m, k in models.items():
            hit = 0
            for x, y in T.pixels():
                t, kx, ky = T.taps(m, *t15.uv(n, x, y), w, 32)
                v = T.blend([T.name_of(i) for i in t], kx, ky)
                hit += all(abs((v >> 8 * c & 255) - (px[y * 64 + x] >> 8 * c & 255)) <= 1
                           for c in range(4))
            assert hit == k, (n, m, hit)
    assert T.bl32_tokens() == ["t:" + ",".join(str(v >> 8 * c & 255) for c in range(4))
                               for v in T.kept15("tw-bl32")]


def test_f_wrap2_is_h_foot_tw():
    for n, _, w, h, kind, _, _, _ in T.ROWS:
        if kind == "bil":
            for x, y in T.pixels():
                u, v = T.uv(n, x, y)
                assert T.taps("F-WRAP2", u, v, w, h) == T.taps("H-FOOT-TW", u, v, w, h)


def parted(a, b):
    n = 0
    for x, y in zip(a, b):
        if x.startswith("t:"):
            xa, ya = ([int(v) for v in t[2:].split(",")] for t in (x, y))
            n += max(abs(p - q) for p, q in zip(xa, ya)) >= 3          # past both tolerances
        else:
            n += x != y
    return n


# row: {rival: the fewest pixels it parts from the frozen form (F-FRAC / H-TWP-H) on}
PARTS = {
    "pt32h8": {"H-TWP-T16": 2048, "H-MOVEH": 2048}, "pt128h8": {"H-TWP-T16": 2048, "H-MOVEH": 2048},
    "pt32h16": {"H-MOVEH": 2048}, "pt128h16": {"H-MOVEH": 2048},
    "pt16h64u0": {"H-TWP-V32": 2048, "H-TWP4128": 2048, "H-TWP-STRIP": 1024},
    "pt16h64u1": {"H-TWP-V32": 2048, "H-TWP4128": 2048, "H-TWP-STRIP": 1024},
    "pt64h64u0": {"H-TWP-V32": 2048, "H-TWP4128": 2048, "H-TWP-STRIP": 1024},
    "pt64h64u1": {"H-TWP-V32": 2048, "H-TWP4128": 2048, "H-TWP-STRIP": 1024},
    "bl64in": {"H-POINT": 256}, "bl16h16in": {"H-POINT": 256},
    "bl64left": {"H-FOOT-SHIFT": 256, "H-POINT": 256},
    "bl128right": {"H-FOOT-SHIFT": 256, "H-FOOT-TW": 256, "H-POINT": 256},
    "bl128h16right": {"H-FOOT-SHIFT": 256, "H-FOOT-TW": 256, "H-POINT": 256},
    "bl128vedge": {"F-VNEXT": 256, "H-POINT": 256},
}


def test_frozen_models_part_on_every_held_out_row():
    """Each held-out row parts its frozen form from the rivals PARTS names on at least that many
    pixels (bilinear: past both tolerances), and every rival is parted on at least one row; the
    rivals PARTS does not name on a row are that row's form there (one image, say so in the
    record: at one tile row the pitch rivals are H-TWP-H)."""
    seen = set()
    for n, sset, _, h, kind, _, _, _ in T.ROWS:
        if sset == "control":
            continue
        ms = T.models(n)
        main = "F-FRAC" if kind == "bil" else "H-TWP-H"
        im = {m: T.tokens(n, m) for m in ms}
        for m in ms:
            if m == main:
                continue
            p = parted(im[main], im[m])
            if m in PARTS[n]:
                assert p >= PARTS[n][m], (n, m, p)
                seen.add(m)
            elif kind == "point":
                assert p == 0, (n, m, p)
    assert seen == (set(T.POINT) | set(T.BIL)) - {"H-TWP-H", "F-FRAC"}


def test_controls_and_point_images():
    """The references are E561's law (law.index, tiles min(W, 16) x min(H, 16)); H-POINT is
    H-TWP-H's point image; a model's image names only scratch dwords."""
    for n in ("ref32h8", "ref16h64"):
        _, _, w, h, _, _, _, _ = T.row(n)
        want = ["%08x" % T.name_of(law.index(T.fl(u * w) % w, T.fl(v * h) % h, w, h))
                for u, v in (T.uv(n, x, y) for x, y in T.pixels())]
        assert T.tokens(n, "REF") == want
    # E561's tile at H 8 is 16 x 8: the bit-clear 32 x 8 reads dwords 0 to 255, both tiles
    assert {int(t, 16) & 0xFFFF for t in T.tokens("ref32h8", "REF")} == set(range(256))
    for n in ("bl64in", "bl128right"):
        assert all(t.startswith("t:") and t.endswith(",208") for t in T.tokens(n, "H-POINT")), n
