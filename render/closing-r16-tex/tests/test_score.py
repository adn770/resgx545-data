# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on records it must hold on and must fail on.

ty: E1055's kept ty-ty1u4r as the control (PASS), E1000's kept image (a different one) FAILED; the
frozen N13 image holds N13, H-HALF, H-LIN1 and fails NQ13, H-WHOLE and H-MODE0 (a row reading its
reference holds R-W / H-MODE0 and H-WHOLE only); the 64 x 16 row given N13-H's image holds N13-H and
H-HALF and H-LIN1 (c is free) but fails N13 (the offset of the wrong side); modes 6 and 7 given L13's
image hold L13, H-HALF and fail H-AS-U4 and LQ13; mode 5 given one halved name holds H-FLAT and
H-HALF and fails H-AS-U4, given the mode 4 image holds H-AS-U4 and fails H-FLAT; the type 4
references hold R-32; E1055's own kept 32 x 32 mode 4 rows (r15-tex) hold H-HALF and H-LIN1 and the
fitted N13 / N4 at W = 32 as a replay of the scorer's forms."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
CTL = "data:render/closing-r15-tex/out/20261114-073318/ty/ty-ty1u4r.txt.gz"
E1000 = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
K32 = "data:render/closing-r15-tex/out/20261114-073318/ty/ty-32-ty%d-u4.txt.gz"


def kept(tmp, stage, outputs):
    """A kept directory: NAME.txt.gz per output, cases.tsv with each a completed job."""
    d = tmp / stage
    d.mkdir()
    table = {ln.split("|")[0]: ln.split("|") for ln in open(os.path.join(KP, "tables", stage + ".txt"))
             if ln.strip() and not ln.startswith("#")}
    rows = ["\t".join(COLS)]
    for n, text in outputs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        t = table[n]
        rows.append("\t".join([n, stage, t[1], t[2], t[3], t[4], "x", "0", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "ty", str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, name):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {name}:") or
            ln.startswith(f"{kind} {name} (")][0]


def k(pin):
    return gzip.decompress(pins.blob(pin)).decode(errors="replace")


def as_rows(values, case="x"):
    return "".join(f"probe {case}: row {y}: " + " ".join("%08x" % v for v in values[64 * y:64 * y + 64])
                   + "\n" for y in range(len(values) // 64))


def pred(name, model):
    return [int(t, 16) for t in
            open(os.path.join(KP, f"predictions/ty/{name}.{model}.txt")).read().split()]


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def test_control(tmp_path):
    out = score(kept(tmp_path, "ty", {"ty-ty1u4r": k(CTL)}))
    assert line(out, "CONTROL", "ty-ty1u4r").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score(kept(tmp_path / "b", "ty", {"ty-ty1u4r": k(E1000)}))
    assert line(out, "CONTROL", "ty-ty1u4r").endswith("FAILED")


def test_mode4_rows(tmp_path):
    ctl = {"ty-ty1u4r": k(CTL)}
    ref = pred("ty-64-ty1-u0", "R-W")
    out = score(kept(tmp_path, "ty", dict(ctl, **{
        "ty-64-ty1-u0": as_rows(ref),
        "ty-64-ty1-u4": as_rows(pred("ty-64-ty1-u4", "N13")),
        "ty-08-ty1-u0": as_rows(pred("ty-08-ty1-u0", "R-W")),
        "ty-08-ty1-u4": as_rows(pred("ty-08-ty1-u4", "NQ13")),
        "ty-6416-ty1-u0": as_rows(pred("ty-6416-ty1-u0", "R-W")),
        "ty-6416-ty1-u4": as_rows(pred("ty-6416-ty1-u4", "N13-H")),
        "ty-64-ty4-u0": as_rows(pred("ty-64-ty4-u0", "R-W")),
        "ty-64-ty4-u4": as_rows(pred("ty-64-ty4-u0", "R-W"))})))
    assert line(out, "ROW", "ty-64-ty1-u0").endswith("held R-W")
    assert line(out, "ROW", "ty-64-ty1-u4").endswith("held N13, H-HALF, H-LIN1")
    assert line(out, "ROW", "ty-08-ty1-u4").endswith("held NQ13, H-HALF, H-LIN1"), line(
        out, "ROW", "ty-08-ty1-u4")            # H-LIN1's c is free: any linear name map holds it
    assert line(out, "ROW", "ty-6416-ty1-u4").endswith("held N13-H, H-HALF, H-LIN1")
    assert line(out, "ROW", "ty-6416-ty1-u0").endswith("held R-W")
    r4 = line(out, "ROW", "ty-64-ty4-u4")
    assert r4.endswith("held H-MODE0, H-WHOLE"), r4       # a row reading its reference
    assert "SUMMARY: ty: N13 (heldout) is not supported" in out    # one of its rows is not N13's


def test_modes_5_to_7(tmp_path):
    ctl = {"ty-ty1u4r": k(CTL)}
    flat = [half(0xD0000000 | 163)] * 2048
    out = score(kept(tmp_path, "ty", dict(ctl, **{
        "ty-64-ty1-u0": as_rows(pred("ty-64-ty1-u0", "R-W")),
        "ty-64-ty1-u5": as_rows(flat),
        "ty-64-ty1-u6": as_rows(pred("ty-64-ty1-u6", "L13")),
        "ty-64-ty1-u7": as_rows(pred("ty-64-ty1-u7", "LQ13")),
        "ty-08-ty1-u0": as_rows(pred("ty-08-ty1-u0", "R-W")),
        "ty-08-ty1-u5": as_rows(pred("ty-08-ty1-u5", "H-AS-U4"))})))
    r5 = line(out, "ROW", "ty-64-ty1-u5")
    assert r5.endswith("held H-HALF, H-FLAT"), r5
    assert "row 0 lowest names 163 to 163" in r5, r5
    assert line(out, "ROW", "ty-64-ty1-u6").endswith("held L13, H-HALF")
    assert line(out, "ROW", "ty-64-ty1-u7").endswith("held LQ13, H-HALF")
    assert line(out, "ROW", "ty-08-ty1-u5").endswith("held H-AS-U4, H-HALF")


def test_e1055_kept_32_rows_through_the_scorer_forms(tmp_path):
    """The scorer's forms on E1055's own 32 x 32 rows: H-HALF and H-LIN1 hold (c + U with c)."""
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    for ty in (1, 3, 4):
        px = pins.kept_pixels(K32 % ty)
        assert S.form("half<32768", px)[0] and S.form("lin1:map:32<32768", px)[0], ty
        assert not S.form("flat<32768", px)[0]
        assert not S.form("whole<32768", px)[0]
    assert S.form("flat<32768", [half(0xD0000000 | 163)] * 2048)[0]
    assert not S.form("flat<32768", [half(0xD0000000 | 163)] * 2047 + [half(0xD0000000 | 165)])[0]


def test_read_files_reads_what_score_reads(tmp_path):
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    d = kept(tmp_path, "ty", {"ty-ty1u4r": k(CTL)})
    S.read_files("ty", str(d))
    assert list(S.REQUIRED) == ["ty"] and S.REQUIRED["ty"][0] == ".txt"
