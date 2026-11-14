# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current (tables/, predictions/, bins/ against its pin), every
repository file the session reads is pinned, and the coverage model and frame hold on kept records:
gen/model.py's port of render.c's sgxfive_tri_expect against r13-flag's kept default 128 x 128
triangle (t10, diff 0: 4284 triangle pixels, "2709 if flipped": the tool's window y is memory row
y), and the frozen maps' counts against predictions/rclip.tsv."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402
import kitscore as K  # noqa: E402
import model as M  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
F3A = "render/closing-r13-flag/out/20261113-220930/f3/f3-shape-a.txt.gz"


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


def test_program_is_its_pin():
    b = open(os.path.join(KP, "bins/pix_green.bin"), "rb").read()
    assert b == kept.blob("render/closing-r3k-regress/bins/pix_green.bin")
    assert CFG["files"]["laptop"] == ["bins/*.bin"]
    assert sorted(os.listdir(os.path.join(KP, "bins"))) == ["pix_green.bin"]


def test_recipe_is_its_pin():
    b = open(os.path.join(KP, "lead/build_tool10.sh"), "rb").read()
    assert b == kept.blob("render/closing-r10-st1/lead/build_tool10.sh")
    assert CFG["tools"]["t10"]["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"


def test_default_triangle_model_on_the_kept_128_triangle():
    text = kept.data(F3A).decode()
    assert "tri 128x128 #1: 4284 triangle, 12100 background, 0 other; wrong 0 inside, 0 outside, " \
           "0 at edges; 2709 if flipped" in text
    assert "job: ok" in text and "diff: 0 of 16384 pixels" in text
    r = dict(w=128, h=128, full=False, clip=None)
    obj = M.object_map(r)
    inside, edge = obj.count(1), obj.count(-1)
    assert inside <= 4284 <= inside + edge
    assert M.default_vertices(128, 128) == ((256, 256), (1792, 640), (640, 1792))
    # the flipped reference is not the image: the frame is memory row = window y
    flip = [M.tri_expect(M.default_vertices(128, 128), x, 127 - y) for y in range(128) for x in range(128)]
    assert sum(1 for a, b in zip(obj, flip) if {a, b} == {0, 1}) > 2000


def test_frozen_counts_match_the_predictions_file():
    preds = K.predictions(KP, "rclip")
    fz = M.combo_name(M.FROZEN)
    for n in M.NAMES:
        p = M.predict(M.row(n), M.FROZEN)
        assert preds[n]["map"][fz] == "sha256:" + M.sha(p)
        assert int(preds[n]["green"][fz]) == p.count("G")
        assert int(preds[n]["either"][fz]) == p.count("g")
        assert int(preds[n]["sentinel"][fz]) == 0
    assert preds["g-clear-64"]["green"][fz] == "4096" and preds["z128-empty"]["green"][fz] == "0"
    # E348's viewport row: column 1 (x 32..63), rows 1 to 3 (y 16..63)
    p = M.predict(M.row("vp64-e348"), M.FROZEN)
    assert all((p[y * 64 + x] == "G") == (x >= 32 and y >= 16) for y in range(64) for x in range(64))


def test_every_repository_read_is_pinned():
    pins = set(CFG["freeze"]["pins"])
    used = set()
    for f in ("gen/make.py", "tests/test_gen.py", "tests/test_score.py"):
        used |= set("data:" + m for m in re.findall(r'"(render/closing-[^"]+[^/"])"', open(os.path.join(KP, f)).read()))
    used |= {"data:" + F3A} | {"data:render/closing-r3k-regress/out/20261110-222647/rg-ctl/"
                                "ctl-green-%s.txt.gz" % s for s in ("128x128", "256x256")}
    assert used <= pins, used - pins
