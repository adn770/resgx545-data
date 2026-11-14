# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

chain: E562's shp-32x16-l5 and shp-128x16-l7-x0 as chain-ctl32 and chain-ctl128 (PASS), swapped
(FAILED); a held-out row given A's (A-TX's) image holds A only, B's image FAILS A; a u16 row's
`h:` tokens compare the low 16 bits. ty: E1000's kept image as ty-ctl and E1039's addr5-ty1-u4 as
ty-ty1u4r (PASS), swapped (FAILED); E1039's addr5-ty1-u4 as a mode 5 row holds H-AS-U4, H-HALF and
H-LIN1 and fails H-MODE0 and H-WHOLE; E567's rt1-2d as a mode 6 row holds H-MODE0 and H-WHOLE and
fails H-HALF; a 32 x 32 mode 4 row reading its reference holds H-MODE0 and H-WHOLE, one reading
halved names c + U holds H-HALF and H-LIN1, the same with one column moved fails H-LIN1, with its
rows differing fails H-HALF; the n16 row given NAME-U's image holds NAME-U and H-HALF."""
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
SHP = "data:texture/p1132/tx-shapes/%s.txt.gz"
E1000 = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
TY1U4 = "data:render/closing-r14-tex/out/20261114-054258/addr5/addr5-ty1-u4.txt.gz"
RT1 = "data:texture/p1132/tx-types-risky/rt1-2d.txt.gz"


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


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
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


def pred(stage, name, model):
    toks = open(os.path.join(KP, f"predictions/{stage}/{name}.{model}.txt")).read().split()
    return [int(t[2:] if t.startswith("h:") else t, 16) for t in toks]


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def test_chain_controls(tmp_path):
    out = score("chain", kept(tmp_path, "chain", {
        "chain-ctl32": k(SHP % "shp-32x16-l5"), "chain-ctl128": k(SHP % "shp-128x16-l7-x0")}))
    assert line(out, "CONTROL", "chain-ctl32").endswith("PASS")
    assert line(out, "CONTROL", "chain-ctl128").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("chain", kept(tmp_path / "b", "chain", {
        "chain-ctl32": k(SHP % "shp-128x16-l7-x0"), "chain-ctl128": k(SHP % "shp-32x16-l5")}))
    assert line(out, "CONTROL", "chain-ctl32").endswith("FAILED")
    assert line(out, "CONTROL", "chain-ctl128").endswith("FAILED")


def test_chain_rows(tmp_path):
    ctl = {"chain-ctl32": k(SHP % "shp-32x16-l5"), "chain-ctl128": k(SHP % "shp-128x16-l7-x0")}
    out = score("chain", kept(tmp_path, "chain", dict(ctl, **{
        "chain-1d-lw": as_rows(pred("chain", "chain-1d-lw", "A")),
        "chain-64x32-lw": as_rows(pred("chain", "chain-64x32-lw", "B")),
        "chain-h16x64-lh": as_rows([0xBEEF0000 | v for v in pred("chain", "chain-h16x64-lh",
                                                                  "A-TX")])})))
    assert line(out, "ROW", "chain-1d-lw").endswith("held A")
    assert line(out, "ROW", "chain-64x32-lw").endswith("held B")
    assert line(out, "ROW", "chain-h16x64-lh").endswith("held A-TX")
    assert "SUMMARY: chain: A (heldout) is not supported" in out


def test_ty_controls(tmp_path):
    out = score("ty", kept(tmp_path, "ty", {"ty-ctl": k(E1000), "ty-ty1u4r": k(TY1U4)}))
    assert line(out, "CONTROL", "ty-ctl").endswith("PASS")
    assert line(out, "CONTROL", "ty-ty1u4r").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("ty", kept(tmp_path / "b", "ty", {"ty-ctl": k(TY1U4), "ty-ty1u4r": k(E1000)}))
    assert line(out, "CONTROL", "ty-ctl").endswith("FAILED")
    assert line(out, "CONTROL", "ty-ty1u4r").endswith("FAILED")


def test_ty_16_rows(tmp_path):
    out = score("ty", kept(tmp_path, "ty", {"ty-16-ty1-u5": k(TY1U4), "ty-16-ty1-u6": k(RT1)}))
    r5 = line(out, "ROW", "ty-16-ty1-u5")
    assert r5.endswith("held H-AS-U4, H-HALF, H-LIN1"), r5
    assert "c + U with c in [404, 660]" in r5 and "row 0 lowest names 419 to 435" in r5, r5
    assert line(out, "ROW", "ty-16-ty1-u6").endswith("held H-MODE0, H-WHOLE")


def test_ty_32_rows(tmp_path):
    ref = pred("ty", "ty-32-ty1-u0", "R-W")
    lin = [half(0xD0000000 | (900 + 32 + x % 32)) for y in range(32) for x in range(64)]
    moved = list(lin)
    for y in range(32):
        moved[64 * y + 5] = half(0xD0000000 | 3000)
    differ = lin[:64] * 31 + [half(0xD0000000 | (901 + 32 + x % 32)) for x in range(64)]
    out = score("ty", kept(tmp_path, "ty", {
        "ty-32-ty1-u0": as_rows(ref), "ty-32-ty1-u4": as_rows(ref),
        "ty-32-ty3-u0": as_rows(pred("ty", "ty-32-ty3-u0", "R-16")),
        "ty-32-ty3-u4": as_rows(lin), "ty-32-ty4-u4": as_rows(moved)}))
    assert line(out, "ROW", "ty-32-ty1-u0").endswith("held R-W")
    assert line(out, "ROW", "ty-32-ty1-u4").endswith("held H-MODE0, H-WHOLE")
    assert line(out, "ROW", "ty-32-ty3-u0").endswith("held R-16")
    assert line(out, "ROW", "ty-32-ty3-u4").endswith("held H-HALF, H-LIN1")
    r4 = line(out, "ROW", "ty-32-ty4-u4")
    assert r4.endswith("held H-HALF") and "no c + U" in r4 and "has no image" in r4, r4
    (tmp_path / "b").mkdir()
    out = score("ty", kept(tmp_path / "b", "ty", {"ty-32-ty1-u4": as_rows(differ)}))
    r = line(out, "ROW", "ty-32-ty1-u4")
    assert "rows differ" in r and r.endswith("no frozen model exact"), r


def test_ty_n16(tmp_path):
    out = score("ty", kept(tmp_path, "ty", {
        "ty-16-ty1-n16": as_rows(pred("ty", "ty-16-ty1-n16", "NAME-U"))}))
    assert line(out, "ROW", "ty-16-ty1-n16").endswith("held NAME-U, H-HALF")


def test_read_files_reads_what_score_reads(tmp_path):
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    d = kept(tmp_path, "ty", {"ty-ctl": k(E1000)})
    S.read_files("ty", str(d))
    assert all(S.REQUIRED[s][0] == ".txt" for s in S.REQUIRED)
