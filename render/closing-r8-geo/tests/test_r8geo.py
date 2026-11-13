# SPDX-License-Identifier: MIT
"""r8-geo's own tests: the generator current and faithful, the models against the kept records
they rest on, the argv twin (every table row answered by the mock from its argv alone), and the
scorer on kept records it must hold on and must fail on."""
import gzip
import hashlib
import os
import shlex
import subprocess
import sys

import pytest

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
import vdm as V  # noqa: E402
import world as Wd  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
P1141 = DATA + "/texture/p1141/out-hw/p1141tex-dumps"
STAGES = ("cube", "seam", "addr", "vdm")


def gz(path):
    return gzip.open(path, "rt").read()


# ---- the generator -----------------------------------------------------------------------------
def test_generator_is_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_cube_control_program_is_e726s_cu_xn_byte_for_byte():
    a = open(os.path.join(KP, "bins/cube-ctl-xn.bin"), "rb").read()
    b = open(DATA + "/render/closing-r4-render4x/bins/p1141-cube__4.bin", "rb").read()
    assert a == b


def test_the_frozen_rule_is_the_offline_freeze_and_fits_e726():
    R = C.rule()
    for lab, spec in (("cu-xn", (C.NEG, C.RX, C.RY)), ("cu-xp", (C.ONE, C.RX, C.RY))):
        px = T.pixels(gz(P1141 + "/tex-h-cube/%s.txt.gz" % lab))
        pp = C.pixel_predictions(R, spec, 16)
        assert all(s == "ok" and v == px[p] for p, (s, v) in pp.items()), lab


def test_every_coordinate_is_exact_in_float32():
    specs = [j[2] for j in C.jobs()] + [A.coords(a) for a in "uv"]
    for spec in specs:
        for s in spec:
            for y in range(T.H):
                for x in range(T.W):
                    assert T.exact_f32(T.coord(s, x, y)), (s, x, y)


def test_the_new_programs_reach_all_six_faces_and_the_sizes_use_e725s_field():
    R = C.rule()
    faces = set()
    for k, spec in C.OFF.items():
        faces |= {(v & 0xffffff) // 256 for s, v in C.pixel_predictions(R, spec, 16).values()
                  if s == "ok"}
    assert faces == set(range(6))
    assert C.T1[8] & 0x00ffffff == 0x007007 and C.T1[32] & 0x00ffffff == 0x01f01f


def test_the_edge_jobs_have_out_and_in_pixels():
    R = C.rule()
    for k, spec in C.EDGE.items():
        kinds = {kk for f, kk in C.edge_cells(R, spec).values()}
        assert kinds == {"in", "out"}, k


def test_the_region_model_is_the_landed_one_and_holds_on_e504s_kept_controls():
    M = S.model()
    for lab, mode, te in (("t29-m2-e0-64x64-ctl", 2, 0xe0000000),
                          ("t29-m2-20-64x64-ctl", 2, 0x20000000)):
        px = SC.pixels(gz(P1141 + "/msaa-b-te29/%s.txt.gz" % lab), 64, 64)
        got = {p for p, v in px.items() if v == S.TRI}
        assert got == S.stored(M, 64, 64, mode, te, None), lab


def test_the_o8_table_is_the_model_called_as_this_session_calls_it():
    M = S.model()
    P = K.predictions(KP, "seam")
    for name, st, w, h, mode, te, verts in S.jobs():
        stored = S.stored(M, w, h, mode, te, verts)
        union = S.stored(M, w, h, mode, te, verts, halves=False)
        for m, cells in (("H-REGION", stored), ("H-UNION", union)):
            if verts is None:
                cells = {(x, y) for y in range(h) for x in range(w)} - cells
                q = "holes"
            else:
                q = "stored"
            assert S.cells_sha(cells) == P[name][q + "_sha256"][m], (name, m)
            assert len(cells) == int(P[name][q][m]), (name, m)


def test_the_twiddle_reproduces_e565s_kept_mode_0_jobs():
    """E565's bd-u0: u = -1.5 + (x + 1/2) / 16 (s = x - 24, repeat), v = y / 32 (t = y // 2);
    bd-v0: u = x / 64 (s = x // 4), v = -1.4375 + y / 8 (t = 2 y - 23, repeat)."""
    for lab, st in (("bd-u0", lambda x, y: ((x - 24) % 16, y // 2)),
                    ("bd-v0", lambda x, y: (x // 4, (2 * y - 23) % 16))):
        px = T.pixels(gz(DATA + "/texture/p1132/tx-border/%s.txt.gz" % lab))
        assert all(v == 0xD0000000 | A.morton(*st(x, y)) for (x, y), v in px.items()), lab


def test_vdm_natural_words_and_flips():
    assert V.word7(8, 3) == V.NATURAL7[8] and V.word7(2, 2) == V.NATURAL7[2]
    assert V.flip6(8) == 0x80000000 and V.flip6(11) == 0x50000000   # E703's
    src = os.path.join(KP, "debug/tool4-src/userspace/libsgxfive/build/sgxfive-test")
    if not os.path.exists(src):
        pytest.skip("no dry-run build (bash lead/dryrun_vdm.sh)")
    for n in (8, 2):
        d = DATA + "/render/closing-s1/bins"
        out = os.path.join(KP, "debug", "n%d.json" % n)
        subprocess.run([src, "--mock", "probe", "--tri", "pixpds:12", "--temps", "32", "--width",
                        "64", "--height", "64", "--vertices", "126", "--vtx-coords", str(n),
                        "--emit-scene", out, "--slot", "pixel=%s/pix_pa0.bin" % d,
                        "--slot", "vtxuse=%s/vtx_c%d.bin" % (d, n), "%s/p1131-fmt-%d__0.bin" % (d, n)],
                       capture_output=True, check=True)
        import json
        g = [m for m in json.load(open(out))["memory"] if m["role"] == "gen"][0]["dwords"]
        assert int(g[7], 16) == V.NATURAL7[n] and int(g[6], 16) >> 28 == 15


# ---- the argv twin and the scorer --------------------------------------------------------------
def kept(tmp, stage, world, subst=None):
    """A kept directory as the runner leaves it, every row answered by the mock from its argv
    (or, for a name in subst, by a kept record's text)."""
    d = tmp / stage
    d.mkdir()
    cases, readings = [], []
    for r in K.table(KP, stage):
        argv = [a.replace("$S", KP).replace("$W", str(tmp)) for a in shlex.split(r["args"])]
        if subst and r["name"] in subst:
            out, rc = subst[r["name"]], 0
        else:
            a = Wd.answer("t4", argv, {world})
            assert a is not None and a.get("rc", 0) in (0, 1), (r["name"], a)
            out, rc = a.get("out", ""), a.get("rc", 0)
        (d / (r["name"] + ".txt")).write_text(out)
        cases.append("\t".join([r["name"], stage, r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], str(rc), "ok", "-", "-", "999999"]))
        if r["set"] == "control":
            n = sum(1 for ln in out.splitlines() if " row " in " " + ln or ln.startswith("row "))
            readings.append("%s\tpixels\tpixels=%d" % (r["name"], n))
    head = "\t".join(K.COLUMNS) + "\n"
    (d / "cases.tsv").write_text(head + "\n".join(cases) + "\n")
    (d / "void.tsv").write_text(head)
    (d / "readings.tsv").write_text("name\treads\treading\n" + "\n".join(readings) + "\n")
    return str(d)


def summary(lines, key):
    return [ln for ln in lines if ln.startswith("SUMMARY") and key in ln]


def test_every_row_is_answered_from_its_argv_and_prints_its_pixels(tmp_path):
    for st in STAGES:
        d = kept(tmp_path, st, "model")
        for r in K.table(KP, st):
            w, h = SC.size(r) if st != "vdm" else (64, 64)
            assert SC.pixels(K.text(d, r["name"] + ".txt"), w, h) is not None, r["name"]
        assert not K.premise(KP, st, d)


def test_scorer_model_world(tmp_path):
    out = SC.score_cube(kept(tmp_path, "cube", "model"))
    assert "(4 of 4 rows decided)" in summary(out, "off-axis")[0]
    assert "(6 of 6 rows decided)" in summary(out, "8 x 8")[0]
    assert "H-CLAMP" in summary(out, "H-CLAMP")[0] and "(2 of 2" in summary(out, "H-CLAMP")[0]
    assert "not supported" in summary(out, "H-SEAM")[0]
    out = SC.score_seam(kept(tmp_path, "seam", "model"))
    assert "(22 of 22 rows decided)" in summary(out, "H-REGION")[0]
    out = SC.score_addr(kept(tmp_path, "addr", "model"))
    assert "(4 of 4" in summary(out, "on u, H-MASK-V")[0]
    out = SC.score_vdm(kept(tmp_path, "vdm", "model"))
    assert "(2 of 2" in summary(out, "H-LAYOUT")[0]
    assert "not supported" in summary(out, "H-COUNT")[0]


def test_scorer_alt_world(tmp_path):
    out = SC.score_cube(kept(tmp_path, "cube", "alt"))
    assert "(2 of 2" in summary(out, "H-SEAM")[0]
    out = SC.score_seam(kept(tmp_path, "seam", "alt"))
    assert "controls FAILED" in summary(out, "H-UNION")[0]
    out = SC.score_addr(kept(tmp_path, "addr", "alt"))
    assert "(4 of 4" in summary(out, "on u, H-NOMASK-PAGE")[0]
    out = SC.score_vdm(kept(tmp_path, "vdm", "alt"))
    assert "(2 of 2" in summary(out, "H-COUNT")[0]


def test_scorer_holds_on_the_kept_records_and_fails_on_the_wrong_ones(tmp_path):
    xn, xp = gz(P1141 + "/tex-h-cube/cu-xn.txt.gz"), gz(P1141 + "/tex-h-cube/cu-xp.txt.gz")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    ok = SC.score_cube(kept(tmp_path / "a", "cube", "model", {"cube-ctl-xn": xn}))
    assert "CONTROL cube-ctl-xn: 2048 of 2048" in "\n".join(ok) and "PASS" in "\n".join(ok)
    bad = SC.score_cube(kept(tmp_path / "b", "cube", "model", {"cube-ctl-xn": xp}))
    assert "controls FAILED" in summary(bad, "off-axis")[0]
    e0 = gz(P1141 + "/msaa-b-te29/t29-m2-e0-64x64-ctl.txt.gz")
    e20 = gz(P1141 + "/msaa-b-te29/t29-m2-20-64x64-ctl.txt.gz")
    (tmp_path / "c").mkdir()
    (tmp_path / "d").mkdir()
    ok = SC.score_seam(kept(tmp_path / "c", "seam", "model", {"ctl-tf-64x64-m2-2": e20}))
    assert "(22 of 22" in summary(ok, "H-REGION")[0]
    bad = SC.score_seam(kept(tmp_path / "d", "seam", "model", {"ctl-a-m1-6-64x64": e0}))
    assert "controls FAILED" in summary(bad, "H-REGION")[0]


def test_a_void_or_missing_row_is_cannot_tell(tmp_path):
    d = kept(tmp_path, "cube", "model")
    os.remove(os.path.join(d, "cube-off-a1.txt"))
    out = SC.score_cube(d)
    assert any(ln.startswith("ROW cube-off-a1") and ln.endswith("cannot tell") for ln in out)
    assert "(3 of 4 rows decided)" in summary(out, "off-axis")[0]


def test_the_frozen_per_pixel_files_are_checked():
    P = K.predictions(KP, "cube")
    for r in K.table(KP, "cube"):
        model = "E726" if r["set"] == "control" else "RULE"
        b = open(os.path.join(KP, "predictions/cube", r["name"] + ".txt"), "rb").read()
        assert hashlib.sha256(b).hexdigest() == P[r["name"]]["pixels_sha"][model]
