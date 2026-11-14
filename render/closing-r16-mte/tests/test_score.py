# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on, and
on the mock's worlds.

Kept: r3k-regress's ctl-green-128x128 and ctl-green-256x256 (probe --tri pixel --tri-full of the
same program, one value 0xff00ff00 over the target, read from their o0 line) hold as e128-on-full
(the whole target's clip) and FAIL as p128-c12-r12 and p256-c2-r39 (a partial clip: a full image
is H-NOCLIP's). Worlds: model holds every row, both controls PASS, one form of each dimension is
left (RETIRE yes); flip, pixel, untouched, always, offdrop, noclip each FAIL the frozen rows they
part and leave their own value; excl fails the gate control (no headline); a row that did not
complete or prints a short image is cannot tell, never a pass."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "score", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402
import model as M  # noqa: E402
import score as SC  # noqa: E402

R3K = "render/closing-r3k-regress/out/20261110-222647/rg-ctl/"


def lines_of(world, tmp_path, only=None):
    d = kept.from_world("rclip", str(tmp_path / world), world, only=only)
    return kept.score("rclip", d)


def find(lines, start):
    return [ln for ln in lines if ln.startswith(start)]


def test_model_world_holds_and_retires(tmp_path):
    ls = lines_of("model", tmp_path)
    assert len(find(ls, "ROW ")) == 13 and all(": held;" in ln for ln in find(ls, "ROW "))
    assert all(ln.endswith(": PASS") for ln in find(ls, "CONTROL "))
    assert find(ls, "READING rclip form:") == ["READING rclip form: H-TILECLIP"]
    assert find(ls, "READING rclip outside:") == ["READING rclip outside: H-BG"]
    assert find(ls, "READING rclip enable:") == ["READING rclip enable: H-EN"]
    assert find(ls, "RETIRE rclip: yes")
    s = find(ls, "SUMMARY: rclip:")[0]
    assert "(13 of 13 rows decided)" in s and "not supported" not in s
    # the straddling row's edge pixels: the frozen map allows either colour
    got = find(ls, "ROW s128-tri:")[0].split("rivals allowing it: ")[1]
    assert got == "TILECLIP+BG+ALWAYS, TILECLIP+BG+OFFDROP"         # bit 31 set: one image


def test_rival_worlds_fail_the_frozen_rows_and_leave_their_value(tmp_path):
    for world, dim, val in (("flip", "form", "H-FLIP"), ("pixel", "form", "H-PIXEL"),
                            ("noclip", "form", "H-NOCLIP"), ("untouched", "outside", "H-UNTOUCHED"),
                            ("always", "enable", "H-ALWAYS"), ("offdrop", "enable", "H-OFFDROP")):
        ls = lines_of(world, tmp_path)
        assert any(": FAILED;" in ln for ln in find(ls, "ROW ")), world
        s = find(ls, "SUMMARY: rclip:")[0]
        assert "not supported" in s or (world == "pixel" and "controls FAILED" in s), (world, s)
        got = find(ls, "READING rclip %s:" % dim)[0]
        assert val in got.split(": ", 1)[1].split(", "), (world, got)
        assert not find(ls, "RETIRE rclip: yes") or world in ("flip", "pixel", "untouched", "always",
                                                              "offdrop"), world


def test_flip_world_reads_exactly_flip(tmp_path):
    ls = lines_of("flip", tmp_path)
    assert find(ls, "READING rclip form:") == ["READING rclip form: H-FLIP"]
    assert find(ls, "RETIRE rclip: yes: one form (H-FLIP)")       # a rival retires it too (R16-6)


def test_excl_world_fails_the_gate(tmp_path):
    ls = lines_of("excl", tmp_path)
    assert find(ls, "CONTROL g-clear-64:")[0].endswith(": FAILED")
    assert find(ls, "CONTROL g-twin-64:")[0].endswith(": PASS")
    assert "controls FAILED" in find(ls, "SUMMARY: rclip:")[0]
    assert find(ls, "RETIRE rclip: no")


def test_incomplete_rows_cannot_tell(tmp_path):
    ls = lines_of("model", tmp_path, only={"g-clear-64", "g-twin-64", "vp64-e348"})
    assert ": held;" in find(ls, "ROW vp64-e348:")[0]
    assert ": cannot tell;" in find(ls, "ROW p128-c12-r12:")[0]
    assert "(1 of 13 rows decided)" in find(ls, "SUMMARY: rclip:")[0]
    ls = lines_of("model", tmp_path / "x", only={"vp64-e348"})
    assert find(ls, "CONTROL g-clear-64:")[0].endswith(": cannot tell")
    assert "cannot tell" in find(ls, "SUMMARY: rclip:")[0]


def test_short_image_is_no_image():
    text = "".join("probe pix_green: row %d: %s\n" % (y, " ".join(["ff00ff00"] * 64)) for y in range(63))
    assert SC.image(text, 64, 64) is None
    assert SC.image(text + "probe pix_green: row 63: " + " ".join(["ff00ff00"] * 63) + "\n", 64, 64) is None
    assert SC.image(text + "probe pix_green: row 63: " + " ".join(["ff00ff00"] * 64) + "\n", 64, 64) == "G" * 4096


def test_kept_full_triangles_hold_as_full_clip_and_fail_as_partial(tmp_path):
    t128 = kept.data(R3K + "ctl-green-128x128.txt.gz").decode()
    t256 = kept.data(R3K + "ctl-green-256x256.txt.gz").decode()
    assert "probe pix_green: o0 0xff00ff00 (16384 of 16384)" in t128
    assert SC.image(t128, 128, 128) == "G" * 16384 and SC.image(t256, 256, 256) == "G" * 65536
    d = kept.from_text("rclip", str(tmp_path / "k"), {"e128-on-full": t128, "p128-c12-r12": t128,
                                                     "p256-c2-r39": t256, "e128-off": t128})
    ls = kept.score("rclip", d)
    assert ": held;" in find(ls, "ROW e128-on-full:")[0]
    assert ": held;" in find(ls, "ROW e128-off:")[0]                  # H-EN: bit 31 clear, no clip
    assert ": FAILED;" in find(ls, "ROW p128-c12-r12:")[0]
    assert "NOCLIP+BG+EN" in find(ls, "ROW p128-c12-r12:")[0]
    assert ": FAILED;" in find(ls, "ROW p256-c2-r39:")[0]
    assert "cannot tell" in find(ls, "SUMMARY: rclip:")[0]            # no control ran


def test_producible_and_premise():
    import kitscore as K
    import scorekit as SK
    SK.refuse_unreadable(K.controls(KP, "rclip"), SC.producible)
    assert SC.producible({"args": M.args(M.row("g-clear-64"))}) == {"pixels", "o0"}
