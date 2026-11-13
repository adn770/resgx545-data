# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin and the library-mock replay (t9: resgx545 97447b04's
sgxfive-test on libsgxfive's in-process mock, debug/libmock, TOOLSRC.sha256), against the plan
(closing9/k1/exp-k1-r9.md section 3) and the tool builder's open checks:

- E934's twin: a row with --bg-layer has both knob words, render_bg_layer=Y and render_bg_src at
  the one address, and a row with either knob word has --bg-layer; the library mock refuses a row
  with the option and no knob words, and a row with the knob words and no option (usage, rc 2);
- the rows replay on the library mock with their knob words as --mock-knob: no `job: rejected`,
  no usage refusal (the kit's libmock does the same over every row; here a sample of each shape);
- no poke of the words 0-2 (the EDM rewrites them, E590), bg pokes only through --kpoke-render
  1:bg:N with N 3-22 (bg:17-22 need the knob at write time: every such row has it);
- every probe row has a bgpds slot and a bgpixel one (check 2: the copy at 0xf00 is unused under
  a bgpds slot, and a bgpixel slot alone is refused);
- check 4: the source at render_bg_src (0x3e800000, 16 KiB at 64 x 64) is clear of every
  allocation the tool makes (the render's general-heap pages, the colour buffer, the probe's
  scratch), on the library mock's own addresses; a source at the general heap's first page maps
  (it is mapped first) and the render context's own mapping then fails (EEXIST, rc 1, `render
  context: File exists`), as mock/world.py's eexist world says;
- run/hooks.sh's hook_reading and kept.py's reading agree on the world's outputs;
- the recipe in lead/ is the tool builder's (its commit and the source hash)."""
import hashlib
import os
import re
import shlex
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import bgl_model as M  # noqa: E402
import kept as KD  # noqa: E402
import kitscore as K  # noqa: E402
import make as G  # noqa: E402
import session as S  # noqa: E402

LAYER = ["dbg:render_bg_layer=Y", "dbg:render_bg_src=0x3e800000"]
KNOBS = ["--mock-knob", "render_bg_layer=Y", "--mock-knob", "render_bg_src=0x3e800000"]


def all_rows():
    return [r for s in G.STAGES for r in K.table(KP, s)]


@pytest.fixture(scope="module")
def lib():
    c = S.config(KP)
    b, why = S.libmock_build(KP, c, "t9")
    assert b is not None, why
    return str(b)


def run(lib, argv, knobs=(), cwd=None):
    return subprocess.run([lib, "--mock", *knobs, *argv], capture_output=True, text=True,
                          timeout=60, cwd=cwd)


def argv_of(row, w):
    return shlex.split(row["args"].replace("$W", w).replace("$S", KP))


def test_layer_option_and_knob_words_go_together():
    for r in all_rows():
        a = r["args"].split()
        dbg = [k for k in r["knobs"] if k.startswith("dbg:")]
        if "--bg-layer" in a:
            assert dbg == LAYER, r["name"]
        else:
            assert dbg == [], r["name"]
        assert r["tool"] == "t9" and r["risk"] == "safe"


def test_pokes_are_words_3_to_22_through_kpoke_render():
    for r in all_rows():
        a = r["args"].split()
        for i, x in enumerate(a):
            if x == "--kpoke-render":
                m = re.fullmatch(r"1:bg:(\d+)=0x[0-9a-f]{8}", a[i + 1])
                assert m and 3 <= int(m[1]) <= 22, (r["name"], a[i + 1])
                assert "--bg-layer" in a
            if x == "--poke":
                assert re.fullmatch(r"cmd:24=0x3000[014]", a[i + 1]), r["name"]
        assert "--kpoke" not in a


def test_probe_rows_have_both_background_slots():
    for r in all_rows():
        a = r["args"].split()
        if a[0] == "probe":
            assert a[1:3] == ["--tri", "bgpds:12"] and "--slot" in a
            assert a[a.index("--slot") + 1].startswith("bgpixel=$S/bins/r9k-pa")
            assert a[-1] in ("$S/bins/r9k-raw.bin", "$S/bins/r9k-pos.bin")


def test_every_shape_replays_on_the_library_mock(lib):
    seen = set()
    for r in all_rows():
        shape = (r["args"].split()[0], "--bg-layer" in r["args"], "--kpoke-render" in r["args"],
                 "--poke" in r["args"], "--words" in r["args"], "r9k-pa1" in r["args"])
        if shape in seen:
            continue
        seen.add(shape)
        with tempfile.TemporaryDirectory() as w:
            kn = KNOBS if "--bg-layer" in r["args"] else []
            p = run(lib, argv_of(r, w), kn, cwd=w)
            assert "job: rejected" not in p.stdout, (r["name"], p.stdout)
            assert not (p.returncode == 2 and "usage" in p.stderr), (r["name"], p.stderr)
            if "--bg-layer" in r["args"]:
                assert "bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y\n" in p.stdout
    assert len(seen) >= 6


def test_a_row_without_its_knob_words_is_refused(lib):
    """The missing-knob world: the kit's libmock replay would stop the mock on these."""
    r = K.table(KP, "s1")[0]
    with tempfile.TemporaryDirectory() as w:
        p = run(lib, argv_of(r, w), [], cwd=w)                       # option, no knob
        assert p.returncode == 2 and "render_bg_layer" in p.stderr
        off = argv_of(r, w)
        off.remove("--bg-layer")
        p = run(lib, off, KNOBS, cwd=w)                              # knob, no option
        assert p.returncode == 2 and "--bg-layer" in p.stderr
        p = run(lib, argv_of(r, w), KNOBS[:2], cwd=w)                # src 0
        assert p.returncode == 2 and "render_bg_src" in p.stderr


def test_the_source_is_clear_of_every_allocation(lib):
    with tempfile.TemporaryDirectory() as w:
        t = run(lib, ["tri", "--bg-layer"], KNOBS, cwd=w).stdout
        fb = int(re.search(r"^layout: fb (0x[0-9a-f]+)$", t, re.M)[1], 16)
        assert fb + 64 * 64 * 4 + 0x10000 < M.SRC          # a page-rounded target, with margin
        p = run(lib, argv_of(K.table(KP, "s0p")[2], w), KNOBS, cwd=w).stdout
        sc = int(re.search(r"scratch at (0x[0-9a-f]+) \(64 KiB\)", p)[1], 16)
        assert sc + 0x10000 <= M.SRC
        # the general heap's first page is the render's own: a source there cannot be mapped
        p = run(lib, ["tri", "--bg-layer"], ["--mock-knob", "render_bg_layer=Y", "--mock-knob",
                                             "render_bg_src=0x3e000000"], cwd=w)
        # the source maps first (the tool's order), so the overlap fails the render context's own
        # mapping: `render context: File exists`, rc 1, no image (mock/world.py's eexist world)
        assert p.returncode == 1 and "render context: File exists" in p.stderr
        assert "layer texels" not in p.stdout


def test_hook_reading_agrees_with_kept(tmp_path):
    w = KD.world()
    hooks = os.path.join(KP, "run/hooks.sh")
    for st, i in (("s0t", 0), ("s0t", 1), ("s0p", 2), ("s0p", 3)):
        r = K.table(KP, st)[i]
        rc, out, _ = KD.answer(w, r, ("model",), str(tmp_path / r["name"]))
        jw = tmp_path / ("jw-" + r["name"])
        jw.mkdir()
        (jw / (r["name"] + ".out")).write_text(out)
        sh = 'JW=%s; . %s; hook_reading %s' % (shlex.quote(str(jw)), shlex.quote(hooks), r["name"])
        got = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30).stdout
        got = dict(x.split("=", 1) for x in got.split())
        assert got == KD.reading(r["name"], out), r["name"]
        assert set(r["reads"]) <= set(got), r["name"]


def test_hook_check_stops_on_a_v_that_is_not_v(tmp_path):
    w = KD.world()
    hooks = os.path.join(KP, "run/hooks.sh")
    r = K.table(KP, "s0p")[3]
    assert r["name"] == "c-rawv"
    for tokens, stops in ((("model",), False), (("rawvbad",), True), (("none",), False)):
        _, out, _ = KD.answer(w, r, tokens, str(tmp_path / tokens[0]))
        jw = tmp_path / ("jw-" + tokens[0])
        jw.mkdir()
        (jw / "c-rawv.out").write_text(out)
        sh = "JW=%s; args=%s; dbgs=%s; . %s; hook_check c-rawv" % (
            shlex.quote(str(jw)), shlex.quote(" " + r["args"]),
            shlex.quote(" render_bg_layer=Y render_bg_src=0x3e800000"), shlex.quote(hooks))
        got = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30).stdout
        assert bool(got.strip()) == stops, (tokens, got)


def test_recipe_is_the_tool_builders():
    text = open(os.path.join(KP, "lead/build_tool9.sh")).read()
    assert "COMMIT=97447b04b38cadac7733f0cd12503e2ef207a3bf" in text
    assert "SRCSHA=5de429431a93ddbdcd9c20141f5c286dcc5cc72265f95d662279e09b655a3f50" in text
    blob = subprocess.run(["git", "-C", KD.REPOS["resgx545"], "show",
                           "97447b04b38cadac7733f0cd12503e2ef207a3bf:userspace/libsgxfive/tools/"
                           "sgxfive-test.c"], capture_output=True, check=True, timeout=60).stdout
    assert hashlib.sha256(blob).hexdigest() == S.config(KP)["tools"]["t9"]["source_sha256"]
    assert open(os.path.join(KP, "TOOLSRC.sha256")).read().count("97447b04b38cadac") == 1
