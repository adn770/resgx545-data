# SPDX-License-Identifier: MIT
"""r9-geo's own tests: the generator current and faithful to its published inputs, every row
carrying the flags its premise needs (E934's slip), the models against the kept records they rest
on, the argv twin (every table row answered by the mock from its argv alone) and the scorer on
kept records it must hold on and must fail on."""
import gzip
import hashlib
import os
import re
import shlex
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.path.insert(0, os.path.join(KP, "score"))
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import kitscore as K  # noqa: E402
import score as SC  # noqa: E402
import seam as S  # noqa: E402
import texprog as T  # noqa: E402
import world as Wd  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
P1141 = DATA + "/texture/p1141/out-hw/p1141tex-dumps"
R8 = DATA + "/render/closing-r8-geo"
R8OUT = R8 + "/out/20261113-015842"
STAGES = ("seam1", "seam4", "cube2", "addr2")


def gz(path):
    return gzip.open(path, "rt").read()


# ---- the generator and its inputs --------------------------------------------------------------
def test_generator_is_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_copied_inputs_are_r8_geos_published_files():
    for rel in ("q284_rule.json", "o8/q141_r8pred.tsv", "o8/q141_r8pred_cases.json",
                "o8/q141_r8pred_sets.json", "o8/q141_r8pred.py", "o8/q141_r8pred.sha256"):
        assert open(os.path.join(KP, "gen", rel), "rb").read() == \
            open(os.path.join(R8, "gen", rel), "rb").read(), rel
    assert open(os.path.join(KP, "predictions/seam1.tsv"), "rb").read() == \
        open(os.path.join(R8, "gen/o8/q141_r8pred.tsv"), "rb").read()


def test_the_replicated_programs_are_byte_for_byte_the_ones_that_ran():
    pairs = (("cube-ctl-xn", DATA + "/render/closing-r4-render4x/bins/p1141-cube__4.bin"),
             ("addr-ctl-u0", R8 + "/bins/addr-ctl-u0.bin"), ("addr-u4-rep", R8 + "/bins/addr-u4.bin"),
             ("addr-u5-rep", R8 + "/bins/addr-u5.bin"))
    for name, path in pairs:
        assert open(os.path.join(KP, "bins", name + ".bin"), "rb").read() == \
            open(path, "rb").read(), name


def test_the_stages_have_the_plans_job_counts():
    assert {s: len(K.table(KP, s)) for s in STAGES} == \
        {"seam1": 24, "seam4": 25, "cube2": 17, "addr2": 11}


# ---- every row carries its premise (E934) ------------------------------------------------------
def poke(args, idx):
    m = re.search(r"--poke cmd:%d=(0x[0-9a-f]+)" % idx, args)
    return int(m.group(1), 16) if m else None


def test_every_multisampled_row_has_aa4_and_seam1_rows_the_one_array_knob():
    for st in ("seam1", "seam4"):
        for r in K.table(KP, st):
            a = r["args"].split()
            te = poke(r["args"], 1)
            assert te is not None, r["name"]
            if te >> 30 & 3:
                assert "--aa4" in a, r["name"]
            assert "expectdiff" in r["knobs"], r["name"]
            dbg = [k for k in r["knobs"] if k.startswith("dbg:")]
            assert dbg == (["dbg:render_rgn_arrays=1"] if st == "seam1" else []), r["name"]


def test_the_knob_is_declared_with_its_values():
    import tomllib
    c = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
    assert c["knobs"]["render_rgn_arrays"] == {"default": "0", "values": ["0", "1"]}


def test_probe_rows_carry_their_scratch_and_texture_words():
    for r in K.table(KP, "cube2"):
        a = r["args"]
        n = [j for j in C.jobs() if j[0] == r["name"]][0][3]
        assert ("--scratch-pages 32" in a) == (n == 64), r["name"]
        text = open(os.path.join(KP, "bins", r["name"] + ".s")).read()
        assert "#0x%08x" % C.T1[n] in text, r["name"]
    for r in K.table(KP, "addr2"):
        assert "--scratch-pages 32" in r["args"], r["name"]
        text = open(os.path.join(KP, "bins", r["name"] + ".s")).read()
        assert "#0x5cafc000" in text, r["name"]


def test_the_probe_buffers_hold_every_read():
    """64 x 64 faces end at 6 x 4096 dwords (24 pages of 32); every addr2 rival reads inside the
    32 pages (12288 + index)."""
    assert 6 * 64 * 64 <= 32 * 1024
    for name, st, n, um, vm, t3, kind in A.jobs():
        for m in A.models(name, um, n, kind):
            assert max(A.image(n, um, vm, kind, m).values()) + A.BASE < A.PAGES * 1024


def test_every_coordinate_is_exact_in_float32():
    specs = [j[2] for j in C.jobs()] + [A.coords(j[2], j[6]) for j in A.jobs()]
    for spec in specs:
        for s in spec:
            for y in range(T.H):
                for x in range(T.W):
                    assert T.exact_f32(T.coord(s, x, y)), (s, x, y)


# ---- the models on the kept records they rest on -----------------------------------------------
def test_the_region_model_holds_on_e504s_kept_controls_and_e502s_control_set():
    M = S.model()
    for lab, mode, te in (("t29-m2-e0-64x64-ctl", 2, 0xe0000000),
                          ("t29-m2-20-64x64-ctl", 2, 0x20000000)):
        px = SC.pixels(gz(P1141 + "/msaa-b-te29/%s.txt.gz" % lab), 64, 64)
        assert {p for p, v in px.items() if v == S.TRI} == S.stored(M, 64, 64, mode, te, None)
    e502 = T.pixels(gz(DATA + "/isp/msaa-ident/dumps/A-m1-te60-64x64-x.txt.gz"), 64, 64)
    holes = {p for p, v in e502.items() if v == S.BG}
    P = K.predictions(KP, "seam1")
    assert len(holes) == 64 and S.cells_sha(holes) == P["ctl-a-m1-6-64x64"]["holes_sha256"]["H-REGION"]


def test_the_o8_table_is_the_model_called_as_this_session_calls_it():
    M = S.model()
    P = K.predictions(KP, "seam1")
    for name, st, w, h, mode, te, verts in S.jobs():
        for m, halves in (("H-REGION", True), ("H-UNION", False)):
            cells = S.stored(M, w, h, mode, te, verts, halves=halves)
            q = "stored"
            if verts is None:
                cells = {(x, y) for y in range(h) for x in range(w)} - cells
                q = "holes"
            assert S.cells_sha(cells) == P[name][q + "_sha256"][m], (name, m)


def test_j1r_is_a_control_every_seam4_rival_passes():
    M = S.model()
    assert S.stored(M, 288, 144, 2, 0xe0000000, None) == {(x, y) for y in range(144) for x in range(288)}
    text = open(DATA + "/render/closing-r3-rgn4/out/rgn4/j1r-aa4-auto.out").read()
    assert SC.HASH.search(text).group(1) == S.J1R_HASH
    assert re.search(r"41472 triangle, 0 background", text)


def test_e561s_law_is_e930s_post_hoc_index_and_morton_is_not():
    R = C.rule()
    for k in ("b1", "b2", "b3"):
        px = T.pixels(gz(R8OUT + "/cube/cube-n32-%s.txt.gz" % k))
        for law, want in (("E561", True), ("PAIRSWAP", True), ("MORTON", False)):
            pp = C.pixel_predictions(R, C.SIZED[k], 32, law)
            ok = [p for p, (s, v) in pp.items() if s == "ok"]
            assert all(px[p] == pp[p][1] for p in ok) is want, (k, law)


def test_the_rivals_part_on_every_decided_job():
    R = C.rule()
    for name, st, spec, n, t0, kind in C.jobs():
        if kind == "size":
            e = C.pixel_predictions(R, spec, n, "E561")
            mo = C.pixel_predictions(R, spec, n, "MORTON")
            ps = C.pixel_predictions(R, spec, n, "PAIRSWAP")
            assert any(e[p] != mo[p] for p in e), name
            assert any(e[p] != ps[p] for p in e) == (n == 64), name
        if kind == "n4":
            a = C.pixel_predictions(R, spec, n, "MORTON", 16)
            b = C.pixel_predictions(R, spec, n, "MORTON", 64)
            assert any(a[p] != b[p] for p in a), name
        if kind == "facetie":
            cells = C.tie_cells(spec)
            assert len(cells) == 32, name
            hi = {C.tie_face(c, "H-HIGHAXIS") for c in cells.values()}
            lo = {C.tie_face(c, "H-LOWAXIS") for c in cells.values()}
            assert len(hi) == 1 and hi != lo, name
        if kind == "edge":
            cells = C.edge_cells(R, spec)
            outs = [p for p, (f, k) in cells.items() if k == "out"]
            assert len(outs) == 96, name
            for p in outs:
                c = tuple(T.coord(s, *p) for s in spec)
                a = C.blend_bytes(C.blend(R, c, n, "H-SEAM-ADJ"))
                b = C.blend_bytes(C.blend(R, c, n, "H-SEAM-WRAP"))
                assert any(abs(x - y) > 2 * C.TOL for x, y in zip(a, b)), (name, p)
    # H-POS goes with H-LOWAXIS on two tie jobs and with H-HIGHAXIS on the other two
    face = {(k, rv): {C.tie_face(c, rv) for c in C.tie_cells(C.FTIE[k]).values()}
            for k in C.FTIE for rv in C.TIE_RIVALS}
    assert sum(face[(k, "H-POS")] == face[(k, "H-LOWAXIS")] for k in C.FTIE) == 2
    assert sum(face[(k, "H-POS")] == face[(k, "H-HIGHAXIS")] for k in C.FTIE) == 2


def test_the_edge_premise_holds_on_e931s_kept_in_pixels():
    """The in pixels of E931's two kept edge jobs read their exact in-face blend within TOL
    (1536 of 1536), the premise the edge rows are gated on."""
    R = C.rule()
    r8edge = {"dx": (C.const(0.75), C.lin("x", 0.1875, 0.376953125), C.const(0.046875)),
              "dz": (C.lin("y", -0.1875, -0.37890625), C.const(0.046875), C.const(0.75))}
    for k, spec in r8edge.items():
        px = T.pixels(gz(R8OUT + "/cube/cube-edge-%s.txt.gz" % k))
        n = 0
        for p, (f, kind) in C.edge_cells(R, spec).items():
            if kind != "in":
                continue
            b = C.blend_bytes(C.blend(R, tuple(T.coord(s, *p) for s in spec), 16, "H-SEAM-ADJ"))
            assert all(abs(((px[p] >> (8 * i)) & 255) - b[i]) <= C.TOL for i in range(4)), (k, p)
            n += 1
        assert n == 768, k


def test_the_twiddle_reproduces_e565s_kept_mode_0_jobs():
    for lab, st in (("bd-u0", lambda x, y: ((x - 24) % 16, y // 2)),
                    ("bd-v0", lambda x, y: (x // 4, (2 * y - 23) % 16))):
        px = T.pixels(gz(DATA + "/texture/p1132/tx-border/%s.txt.gz" % lab))
        assert all(v == 0xD0000000 | A.index(*st(x, y), 16) for (x, y), v in px.items()), lab


def test_e561s_2d_law_above_16():
    # tiles of 16 x 16 in raster order with s fast: texel (16, 0) is dword 256, (0, 16) 512
    assert A.index(16, 0, 32) == 256 and A.index(0, 16, 32) == 512 and A.index(1, 0, 32) == 2


# ---- the argv twin and the scorer ----------------------------------------------------------------
def kept(tmp, stage, world, subst=None):
    """A kept directory as the runner leaves it, every row answered by the mock from its argv
    (or, for a name in subst, by a kept record's text); a row's dbg knob is the world's knob1."""
    d = tmp / stage
    d.mkdir()
    cases, readings = [], []
    for r in K.table(KP, stage):
        argv = [a.replace("$S", KP).replace("$W", str(tmp)) for a in shlex.split(r["args"])]
        if subst and r["name"] in subst:
            out, rc = subst[r["name"]], 0
        else:
            wd = {world} | ({"knob1"} if "dbg:render_rgn_arrays=1" in r["knobs"] else set())
            a = Wd.answer("t4", argv, wd)
            assert a is not None and a.get("rc", 0) in (0, 1), (r["name"], a)
            out, rc = a.get("out", ""), a.get("rc", 0)
        (d / (r["name"] + ".txt")).write_text(out)
        cases.append("\t".join([r["name"], stage, r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], str(rc), "ok", "-", "-", "999999"]))
        if r["set"] == "control":
            readings.append("%s\t%s\t%s" % (r["name"], ",".join(sorted(K.controls(KP, stage)[r["name"]][0])),
                                             " ".join(hook_reading(out))))
    head = "\t".join(K.COLUMNS) + "\n"
    (d / "cases.tsv").write_text(head + "\n".join(cases) + "\n")
    (d / "void.tsv").write_text(head)
    (d / "readings.tsv").write_text("name\treads\treading\n" + "\n".join(readings) + "\n")
    return str(d)


def hook_reading(out):
    """run/hooks.sh hook_reading's words, in Python (the mock runs the shell one)."""
    w = []
    n = len(re.findall(r"row [0-9]+: ", out))
    if n:
        w.append("pixels=%d" % n)
    if re.search(r"^job: ok", out, re.M):
        w.append("jobok=1")
    m = SC.HASH.search(out)
    if m:
        w.append("hash=" + m.group(1))
    return w


def summary(lines, key):
    return [ln for ln in lines if ln.startswith("SUMMARY") and key in ln]


def test_every_row_is_answered_from_its_argv_and_prints_its_pixels(tmp_path):
    for st in STAGES:
        d = kept(tmp_path, st, "model")
        for r in K.table(KP, st):
            text = K.text(d, r["name"] + ".txt")
            assert SC.pixels(text, *SC.size(r)) is not None, r["name"]
            if r["args"].startswith("tri"):
                assert "job: ok" in text, r["name"]
        assert not K.premise(KP, st, d)


def test_the_world_refuses_e934s_rows_as_the_kernel_does():
    for r in K.table(KP, "seam1"):
        if not poke(r["args"], 1) >> 30 & 3:
            continue
        argv = shlex.split(r["args"].replace(" --aa4", ""))
        assert "job: rejected" in Wd.answer("t4", argv, {"model"})["out"], r["name"]
        assert "job: ok" in Wd.answer("t4", argv, {"model", "knob1"})["out"], r["name"]


def test_scorer_model_world(tmp_path):
    out = SC.score_seam("seam1", kept(tmp_path, "seam1", "model"))
    assert "(22 of 22 rows decided)" in summary(out, "H-REGION")[0]
    assert "not supported" in summary(out, "H-UNION")[0]
    out = SC.score_seam("seam4", kept(tmp_path, "seam4", "model"))
    assert "(23 of 23 rows decided)" in summary(out, "H-SAME4")[0]
    assert "not supported" in summary(out, "H-FULL4")[0]
    out = SC.score_cube(kept(tmp_path, "cube2", "model"))
    assert "(3 of 3" in summary(out, "32 x 32, H-E561")[0]
    assert "(3 of 3" in summary(out, "64 x 64, H-E561")[0]
    assert "not supported" in summary(out, "64 x 64, H-PAIRSWAP")[0]
    assert "(2 of 2" in summary(out, "H-NN")[0]
    assert "(4 of 4" in summary(out, "H-HIGHAXIS")[0]
    assert "not supported" in summary(out, "H-LOWAXIS")[0]
    assert "(2 of 2" in summary(out, "H-SEAM-ADJ")[0]
    assert "not supported" in summary(out, "H-SEAM-WRAP")[0]
    out = SC.score_addr(kept(tmp_path, "addr2", "model"))
    assert "(4 of 4" in summary(out, "8 x 8 and 32 x 32, H-OFF180")[0]
    assert "not supported" in summary(out, "H-OFFSCALE")[0]
    assert "(3 of 3" in summary(out, "H-T3-INERT")[0]
    assert "(1 of 1" in summary(out, "replicate addr-u5-rep, H-U5-E932")[0]


def test_scorer_alt_world(tmp_path):
    out = SC.score_seam("seam1", kept(tmp_path, "seam1", "alt"))
    assert "controls FAILED" in summary(out, "H-UNION")[0]
    out = SC.score_seam("seam4", kept(tmp_path, "seam4", "alt"))
    assert "(17 of 17" in summary(out, "H-FULL4")[0]
    assert "not supported" in summary(out, "H-SAME4")[0]
    out = SC.score_cube(kept(tmp_path, "cube2", "alt"))
    assert "(3 of 3" in summary(out, "32 x 32, H-MORTON")[0]
    assert "(3 of 3" in summary(out, "64 x 64, H-PAIRSWAP")[0]
    assert "(2 of 2" in summary(out, "H-PAD64")[0]
    assert "(4 of 4" in summary(out, "H-LOWAXIS")[0]
    assert "(2 of 2" in summary(out, "H-SEAM-WRAP")[0]
    out = SC.score_addr(kept(tmp_path, "addr2", "alt"))
    assert "(4 of 4" in summary(out, "H-OFFSCALE")[0]
    assert "(1 of 1" in summary(out, "H-OFF360")[0]
    assert "not supported" in summary(out, "H-T3-INERT")[0]


def test_scorer_holds_on_the_kept_records_and_fails_on_the_wrong_ones(tmp_path):
    for sub in "abcdefgh":
        (tmp_path / sub).mkdir()
    xn, xp = gz(P1141 + "/tex-h-cube/cu-xn.txt.gz"), gz(P1141 + "/tex-h-cube/cu-xp.txt.gz")
    ok = SC.score_cube(kept(tmp_path / "a", "cube2", "model", {"cube-ctl-xn": xn}))
    assert "CONTROL cube-ctl-xn: 2048 of 2048 pixels as E726 kept them: PASS" in ok
    bad = SC.score_cube(kept(tmp_path / "b", "cube2", "model", {"cube-ctl-xn": xp}))
    assert "controls FAILED" in summary(bad, "32 x 32, H-E561")[0]
    # E932's kept rows, whose programs these rows replicate byte for byte
    u0, u4, u5 = (gz(R8OUT + "/addr/addr-%s.txt.gz" % k) for k in ("ctl-u0", "u4", "u5"))
    ok = SC.score_addr(kept(tmp_path / "c", "addr2", "model",
                            {"addr-ctl-u0": u0, "addr-u4-rep": u4, "addr-u5-rep": u5}))
    assert "CONTROL addr-ctl-u0: the mode 0 repeat image at page 12: PASS" in ok
    assert "(1 of 1" in summary(ok, "replicate addr-u4-rep, H-OFF180")[0]
    assert "(1 of 1" in summary(ok, "replicate addr-u5-rep, H-U5-E932")[0]
    bad = SC.score_addr(kept(tmp_path / "d", "addr2", "model", {"addr-ctl-u0": u4}))
    assert "controls FAILED" in summary(bad, "H-OFF180")[0]
    # E504's control (r8-geo kept it again, job: ok) holds; E934's rejected control is no reading
    tf = gz(R8OUT + "/seam/ctl-tf-64x64-m2-2.txt.gz")
    rej = gz(R8OUT + "/seam/ctl-a-m1-6-64x64.txt.gz")
    ok = SC.score_seam("seam1", kept(tmp_path / "e", "seam1", "model", {"ctl-tf-64x64-m2-2": tf}))
    assert "(22 of 22" in summary(ok, "H-REGION")[0]
    bad = SC.score_seam("seam1", kept(tmp_path / "f", "seam1", "model", {"ctl-a-m1-6-64x64": rej}))
    assert "cannot tell" in summary(bad, "H-REGION")[0]
    ok = SC.score_seam("seam4", kept(tmp_path / "g", "seam4", "model", {"f4-ctl-tf-64x64-m2-2": tf}))
    assert "(23 of 23" in summary(ok, "H-SAME4")[0]
    j1r = open(DATA + "/render/closing-r3-rgn4/out/rgn4/j1r-aa4-auto.out").read()
    bad = SC.score_seam("seam4", kept(tmp_path / "h", "seam4", "model", {"f4-ctl-j1r-288x144": j1r}))
    assert "cannot tell" in summary(bad, "H-SAME4")[0]      # no pixel rows kept there


def test_a_void_or_missing_row_is_cannot_tell(tmp_path):
    d = kept(tmp_path, "cube2", "model")
    os.remove(os.path.join(d, "cube-n32-c1.txt"))
    out = SC.score_cube(d)
    assert any(ln.startswith("ROW cube-n32-c1") and ln.endswith("cannot tell") for ln in out)
    assert "(2 of 3 rows decided)" in summary(out, "32 x 32, H-E561")[0]


def test_the_frozen_per_pixel_files_are_checked():
    for st, key in (("cube2", "pixels_sha"), ("addr2", "image_sha")):
        P = K.predictions(KP, st)
        for r in K.table(KP, st):
            for m, want in P[r["name"]][key].items():
                b = open(os.path.join(KP, "predictions", st, f"{r['name']}.{m}.txt"), "rb").read()
                assert hashlib.sha256(b).hexdigest() == want, (r["name"], m)
