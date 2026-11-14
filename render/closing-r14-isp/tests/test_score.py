# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on,
and on the mock's worlds.

wind: E977's kept z242-c-f0 (the ramp; its pixel rows added: all 3200 drawn) in the places of the
reversed control, the always control and the three reversed bit rows, E998's kept x-w0b15 (no
pixel) in the bit 15 control's: every control PASS, H-CULL held 3 of 3, H-KILL FAILED; E998's in
the bit rows' places: H-KILL held, H-CULL FAILED; E977's in the bit 15 control's place: FAILED, no
headline. The z rows from the worlds: model H-CLAMP held 2 of 2, zclip H-ZCLIP, raw H-RAW.
g14: E979's kept far-ctl and E1023's t128-1 as the two controls PASS; E1023's t128-2 in t128-1's
place FAILED. Worlds: model H-VP held on every held-out row, every rival FAILED; tgt H-TGT held,
H-VP FAILED (the vp rows); min4 H-MIN4 held, H-VP FAILED.
clipr: E979's far-ctl and E1024's far-x30p as the controls PASS. Worlds: model CLIP-HU 3 of 3,
IN-E607 2 of 2, H-VP held, H-SAT, H-WRAP, H-CULL FAILED; ha CLIP-HA held and CLIP-HU FAILED;
rne, tr likewise; inhu IN-HU held, IN-E607 FAILED."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "score", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402

E977 = "render/closing-r9-x/out/20261113-081821/zls/z242-c-f0"
E998 = "render/closing-r10-x/out/20261113-101116/isp0x/x-w0b15"
R9X = "render/closing-r9-x/out/20261113-081821/far/"
R13 = "render/closing-r13-isp/out/20261113-215416/"
GREEN = "\n".join("row %d: %s" % (y, " ".join(["0xff00ff00"] * 80)) for y in range(40)) + "\n"
BG = "\n".join("row %d: %s" % (y, " ".join(["0xff203040"] * 80)) for y in range(40)) + "\n"


def line(lines, start):
    return [ln for ln in lines if ln.startswith(start)][0]


def summ(lines, key):
    return kept.summary(lines, key)[0]


def held(s, n):
    return "(%d of %d rows decided)" % (n, n) in s and "not supported" not in s


def failed(s):
    return "not supported" in s and " 0 held" in s


# ---- wind --------------------------------------------------------------------------------------
def wind_kept(tmp_path, bits_from=E977, b15_from=E998):
    f = lambda p: {".txt": p + ".txt.gz", ".depth.1.bin": p + ".depth.1.bin.gz"}  # noqa: E731
    files = {"wind-ctl-rev": f(E977), "wind-ctl-b15": f(b15_from), "wind-ctl-always": f(E977)}
    extra = {"wind-ctl-rev": GREEN, "wind-ctl-always": GREEN, "wind-ctl-b15": GREEN if b15_from == E977 else BG}
    for b in (15, 16, 17):
        files["wind-rev-b%d" % b] = f(bits_from)
        extra["wind-rev-b%d" % b] = GREEN if bits_from == E977 else BG
    return kept.from_files("wind", str(tmp_path), files, extra=extra)


def test_wind_cull_on_e977_and_e998(tmp_path):
    out = kept.score("wind", wind_kept(tmp_path / "a"))
    for c in ("wind-ctl-rev", "wind-ctl-b15", "wind-ctl-always"):
        assert line(out, "CONTROL " + c).endswith(": PASS"), out
    assert held(summ(out, "wind: H-CULL"), 3)
    assert failed(summ(out, "wind: H-KILL"))
    out = kept.score("wind", wind_kept(tmp_path / "b", bits_from=E998))
    assert held(summ(out, "wind: H-KILL"), 3)
    assert failed(summ(out, "wind: H-CULL"))
    out = kept.score("wind", wind_kept(tmp_path / "c", b15_from=E977))
    assert line(out, "CONTROL wind-ctl-b15").endswith(": FAILED")
    assert "controls FAILED" in summ(out, "wind: H-CULL")


def test_wind_z_models_from_the_worlds(tmp_path):
    for world, model in (("model", "H-CLAMP"), ("zclip", "H-ZCLIP"), ("raw", "H-RAW")):
        d = wind_kept(tmp_path / world)
        kept.from_world("wind", d, world, only={"wind-zhi", "wind-zlo"}, append=True)
        out = kept.score("wind", d)
        assert held(summ(out, "wind: %s" % model), 2), out
        for m in ("H-CLAMP", "H-ZCLIP", "H-RAW"):
            if m != model:
                assert "not supported" in summ(out, "wind: %s" % m)


# ---- g14 ---------------------------------------------------------------------------------------
def test_g14_controls_on_kept_images(tmp_path):
    out = kept.score("g14", kept.from_files("g14", str(tmp_path / "a"), {
        "g14-ctl-far21": {".txt": R9X + "far-ctl.txt.gz"},
        "g14-ctl-t128": {".txt": R13 + "q261/q261-t128-1.txt.gz"}}))
    assert line(out, "CONTROL g14-ctl-far21").endswith(": PASS")
    assert line(out, "CONTROL g14-ctl-t128").endswith(": PASS")
    out = kept.score("g14", kept.from_files("g14", str(tmp_path / "b"), {
        "g14-ctl-t128": {".txt": R13 + "q261/q261-t128-2.txt.gz"}}))
    assert line(out, "CONTROL g14-ctl-t128").endswith(": FAILED")


def test_g14_worlds(tmp_path):
    out = kept.score("g14", kept.from_world("g14", str(tmp_path / "m"), "model"))
    assert held(summ(out, "g14: H-VP"), 19), out
    for m in ("H-TGT", "H-MAX4", "H-MIN4", "H-ABS", "H-EXACT"):
        assert "not supported" in summ(out, "g14: %s:" % m)
    assert "READING g14 family 128x128 vp bound:pos-x: [80] over 1 rows" in out
    out = kept.score("g14", kept.from_world("g14", str(tmp_path / "t"), "tgt"))
    assert held(summ(out, "g14: H-TGT"), 19)
    assert "not supported" in summ(out, "g14: H-VP:")
    out = kept.score("g14", kept.from_world("g14", str(tmp_path / "n"), "min4"))
    assert "not supported" in summ(out, "g14: H-VP:")
    assert line(out, "CONTROL g14-ctl-t128").endswith(": PASS")


# ---- clipr -------------------------------------------------------------------------------------
def test_clipr_controls_on_kept_images(tmp_path):
    out = kept.score("clipr", kept.from_files("clipr", str(tmp_path), {
        "clipr-ctl-far21": {".txt": R9X + "far-ctl.txt.gz"},
        "clipr-ctl-x30p": {".txt": R13 + "far/far-x30p.txt.gz"}}))
    assert line(out, "CONTROL clipr-ctl-far21").endswith(": PASS")
    assert line(out, "CONTROL clipr-ctl-x30p").endswith(": PASS")


def test_clipr_worlds(tmp_path):
    out = kept.score("clipr", kept.from_world("clipr", str(tmp_path / "m"), "model"))
    assert held(summ(out, "clipr: CLIP-HU"), 3), out
    assert held(summ(out, "clipr: IN-E607"), 2)
    assert held(summ(out, "clipr: H-VP:"), 3)
    for m in ("CLIP-HA", "CLIP-RNE", "CLIP-TR", "IN-HU", "IN-RNE", "IN-TR"):
        assert "not supported" in summ(out, "clipr: %s:" % m)
    for m in ("H-SAT", "H-WRAP", "H-CULL"):
        assert failed(summ(out, "clipr: %s:" % m))
    assert "READING clipr family 4096x16 bound:pos-x: [5120] over 1 rows" in out
    for world, m in (("ha", "CLIP-HA"), ("rne", "CLIP-RNE"), ("tr", "CLIP-TR")):
        out = kept.score("clipr", kept.from_world("clipr", str(tmp_path / world), world))
        assert held(summ(out, "clipr: %s:" % m), 3), (world, out)
        assert "not supported" in summ(out, "clipr: CLIP-HU:")
    out = kept.score("clipr", kept.from_world("clipr", str(tmp_path / "i"), "inhu"))
    assert held(summ(out, "clipr: IN-HU:"), 2)
    assert "not supported" in summ(out, "clipr: IN-E607:")
