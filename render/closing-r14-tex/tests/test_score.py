# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

srgb4: E723's g-bl-st-a as srgb4-ctl (PASS), g-bl-st-b in its place (FAILED); r13-tex's
srgb3-tri as srgb4-trir (PASS); srgb3-x1's kept image as srgb4-b2x1 (PASS: its low halves),
g-bl-st-a in its place (FAILED); TRI-G15's image of srgb4-t1125 holds TRI-G15 and fails TRI-RNTU
on its 7 parting pixels and TRI-OUT; an alpha row's B2-FTZ-OUT low and A-LIN high halves hold
both and nothing else. addr5: E1000's addr3-16x64-u4 as addr5-ctl (PASS), E565's bd-uv5 as
addr5-bduv5 (PASS) and in addr5-ctl's place (FAILED); E567's rt1-2d as addr5-ty1-u0 (held H-E567)
and as addr5-ty1-u4 (T-MODE0 held, T-OFFSET FAILED), plus 180 (T-OFFSET held); the mode 4 row
without its reference is cannot tell."""
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
E723 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/%s.txt.gz"
R13 = "data:render/closing-r13-tex/out/20261113-214825/srgb3/%s.txt.gz"
E1000 = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
BDUV5 = "data:texture/p1132/tx-border/bd-uv5.txt.gz"
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


def test_srgb4_controls(tmp_path):
    out = score("srgb4", kept(tmp_path, "srgb4", {
        "srgb4-ctl": k(E723 % "g-bl-st-a"), "srgb4-trir": k(R13 % "srgb3-tri"),
        "srgb4-b2x1": k(R13 % "srgb3-x1")}))
    for c in ("srgb4-ctl", "srgb4-trir", "srgb4-b2x1"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    (tmp_path / "b").mkdir()
    out = score("srgb4", kept(tmp_path / "b", "srgb4", {
        "srgb4-ctl": k(E723 % "g-bl-st-b"), "srgb4-b2x1": k(E723 % "g-bl-st-a")}))
    assert line(out, "CONTROL", "srgb4-ctl").endswith("FAILED")
    assert line(out, "CONTROL", "srgb4-b2x1").endswith("FAILED")


def test_srgb4_tri_row_on_a_kept_image(tmp_path):
    """srgb3-tri's kept image where srgb4-trir's own prediction is the reference: the trir
    control's H-R13 holds; scored as the frozen models on a LOD 1.25 row it would give
    TRI-G15 (gen tests); here: a tri row given TRI-G15's own image holds TRI-G15 and not
    TRI-OUT."""
    toks = open(os.path.join(KP, "predictions/srgb4/srgb4-t1125.TRI-G15.txt")).read().split()
    out = score("srgb4", kept(tmp_path, "srgb4", {
        "srgb4-ctl": k(E723 % "g-bl-st-a"), "srgb4-trir": k(R13 % "srgb3-tri"),
        "srgb4-b2x1": k(R13 % "srgb3-x1"), "srgb4-t1125": as_rows([int(t, 16) for t in toks])}))
    row = line(out, "ROW", "srgb4-t1125")
    assert "held TRI-G15, TRI-G15-NF" in row and "TRI-RNTU 2041/2048" in row, row
    assert "SUMMARY: srgb4: TRI-OUT (heldout) is not supported" in out


def test_srgb4_alpha_tokens(tmp_path):
    lo = open(os.path.join(KP, "predictions/srgb4/srgb4-ax.B2-FTZ-OUT.txt")).read().split()
    hi = open(os.path.join(KP, "predictions/srgb4/srgb4-ax.A-LIN.txt")).read().split()
    img = [int(a[2:], 16) | int(b[2:], 16) << 16 for a, b in zip(lo, hi)]
    out = score("srgb4", kept(tmp_path, "srgb4", {"srgb4-ax": as_rows(img)}))
    row = line(out, "ROW", "srgb4-ax")
    assert row.endswith("held B2-FTZ-OUT, A-LIN"), row


def test_addr5_controls(tmp_path):
    out = score("addr5", kept(tmp_path, "addr5", {"addr5-ctl": k(E1000), "addr5-bduv5": k(BDUV5)}))
    assert line(out, "CONTROL", "addr5-ctl").endswith("PASS")
    assert line(out, "CONTROL", "addr5-bduv5").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("addr5", kept(tmp_path / "b", "addr5", {"addr5-ctl": k(BDUV5)}))
    assert line(out, "CONTROL", "addr5-ctl").endswith("FAILED")


def test_addr5_corner_row(tmp_path):
    img = [0xD0000000] * 2048
    for m in ("IN-M", "LR-M", "AB-M", "C-LOG4"):
        for p, t in enumerate(open(os.path.join(
                KP, f"predictions/addr5/addr5-128x32-uv5.{m}.txt")).read().split()):
            if t != "-":
                img[p] = int(t, 16)
    out = score("addr5", kept(tmp_path, "addr5", {"addr5-128x32-uv5": as_rows(img)}))
    row = line(out, "ROW", "addr5-128x32-uv5")
    assert "held IN-M, IN-W, LR-M, LR-W, AB-M, AB-W, C-LOG4, C-FLOOR16" in row, row
    assert "corners read 28 x128, 29 x128, 30 x128, 31 x128" in row, row


def test_addr5_type_rows(tmp_path):
    from_ = pins.kept_pixels(RT1)
    out = score("addr5", kept(tmp_path, "addr5", {
        "addr5-ty1-u0": k(RT1), "addr5-ty1-u4": k(RT1),
        "addr5-ty3-u0": k(RT1), "addr5-ty3-u4": as_rows([v + 180 for v in from_]),
        "addr5-ty4-u4": k(RT1)}))
    assert line(out, "ROW", "addr5-ty1-u0").endswith("held H-E567")
    assert line(out, "ROW", "addr5-ty1-u4").endswith("held T-MODE0")
    assert "+0 x2048" in line(out, "ROW", "addr5-ty1-u4")
    assert line(out, "ROW", "addr5-ty3-u4").endswith("held T-OFFSET")
    assert "has no image" in line(out, "ROW", "addr5-ty4-u4")
    assert line(out, "ROW", "addr5-ty4-u4").endswith("cannot tell")


def test_read_files_reads_what_score_reads(tmp_path):
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    d = kept(tmp_path, "addr5", {"addr5-ctl": k(E1000)})
    S.read_files("addr5", str(d))
    assert all(S.REQUIRED[s][0] == ".txt" for s in S.REQUIRED)
