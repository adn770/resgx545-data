# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

srgb3: E723's g-bl-st-a as srgb3-ctl (PASS), g-bl-st-b in its place (FAILED); p1132's an-t0b27
as srgb3-an27 (PASS). addr4: E1000's addr3-16x64-u4 as addr4-ctl (PASS, the reading +564),
E565's bd-uv5 as addr4-bduv5 (PASS), bd-uv5 in addr4-ctl's place (FAILED). t3c: E564's an-t3b11
as t3c-ctl (PASS), an-ctl in its place (FAILED); the bit-14 row without its reference is GATED.
sb12: E383's 0x208 colour 0 job as sb12-ctl-m8 (PASS) and its 0x1200 run as sb12-rep-m0-c0
(PASS, inset 4096), and as the colour 1 row of mode 0 (H-FIXED and H-FIXED-PX held); the 0x208
image in a colour 1 row's place (H-O0 held, H-FIXED FAILED)."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import sb as SB  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
E723 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/%s.txt.gz"
E564 = "data:texture/p1132/tx-lod/%s.txt.gz"
E1000 = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
BDUV5 = "data:texture/p1132/tx-border/bd-uv5.txt.gz"


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


def test_srgb3_holds_and_fails(tmp_path):
    out = score("srgb3", kept(tmp_path, "srgb3", {"srgb3-ctl": k(E723 % "g-bl-st-a"),
                                                   "srgb3-an27": k(E564 % "an-t0b27")}))
    assert line(out, "CONTROL", "srgb3-ctl").endswith("PASS")
    assert line(out, "CONTROL", "srgb3-an27").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("srgb3", kept(tmp_path / "b", "srgb3", {"srgb3-ctl": k(E723 % "g-bl-st-b")}))
    assert line(out, "CONTROL", "srgb3-ctl").endswith("FAILED")
    assert "controls FAILED" in out


def test_srgb3_rows_against_their_own_models(tmp_path):
    """The generator's FTZ-OUT image as the kept x1 row: FTZ-OUT and FTZ-IN held (the x stage
    alone cannot part them), R10-BF11 and FTZ-T64 FAILED."""
    toks = open(os.path.join(KP, "predictions/srgb3/srgb3-x1.FTZ-OUT.txt")).read().split()
    out = score("srgb3", kept(tmp_path, "srgb3", {
        "srgb3-ctl": k(E723 % "g-bl-st-a"), "srgb3-an27": k(E564 % "an-t0b27"),
        "srgb3-x1": as_rows([int(t, 16) for t in toks])}))
    row = line(out, "ROW", "srgb3-x1")
    assert row.endswith("held FTZ-OUT, FTZ-IN"), row
    assert "SUMMARY: srgb3: R10-BF11 (heldout) is not supported: 0 held, 1 FAILED" in out


def test_addr4_holds_and_fails(tmp_path):
    out = score("addr4", kept(tmp_path, "addr4", {"addr4-ctl": k(E1000), "addr4-bduv5": k(BDUV5)}))
    assert line(out, "CONTROL", "addr4-ctl").endswith("PASS")
    assert line(out, "CONTROL", "addr4-bduv5").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("addr4", kept(tmp_path / "b", "addr4", {"addr4-ctl": k(BDUV5)}))
    assert line(out, "CONTROL", "addr4-ctl").endswith("FAILED")


def test_addr4_sweep_reading(tmp_path):
    toks = open(os.path.join(KP, "predictions/addr4/addr4-32x64-u4.H-MAX.txt")).read().split()
    out = score("addr4", kept(tmp_path, "addr4", {
        "addr4-ctl": k(E1000), "addr4-bduv5": k(BDUV5),
        "addr4-32x64-u4": as_rows([int(t, 16) for t in toks])}))
    row = line(out, "ROW", "addr4-32x64-u4")
    assert "held H-MAX, H-H" in row and "+564 x2048" in row, row
    assert "SUMMARY: addr4: H-W (heldout) is not supported" in out


def test_t3c_holds_fails_and_gates(tmp_path):
    toks = open(os.path.join(KP, "predictions/t3c/t3c-b14bl.H-FOOT.txt")).read().split()
    img = [sum(int(b) << 8 * i for i, b in enumerate(t[2:].split(","))) for t in toks]
    out = score("t3c", kept(tmp_path, "t3c", {"t3c-ctl": k(E564 % "an-t3b11"),
                                               "t3c-b14bl": as_rows(img)}))
    assert line(out, "CONTROL", "t3c-ctl").endswith("PASS")
    assert "held H-FOOT" in line(out, "ROW", "t3c-b14bl")
    assert "GATED t3c-b14bl: its reference t3c-b14bl-ref did not hold H-BILIN" in out
    (tmp_path / "b").mkdir()
    out = score("t3c", kept(tmp_path / "b", "t3c", {"t3c-ctl": k(E564 % "an-ctl")}))
    assert line(out, "CONTROL", "t3c-ctl").endswith("FAILED")


def test_sb12_holds_and_fails(tmp_path):
    m8 = SB.kept(pins.blob, 0x208)[0]
    m0 = SB.kept(pins.blob, 0x1200)[0]
    out = score("sb12", kept(tmp_path, "sb12", {
        "sb12-ctl-m8": as_rows(m8, "sb-c0"), "sb12-rep-m0-c0": as_rows(m0, "sb-c0"),
        "sb12-m0-c1": as_rows(m0, "sb-c1"), "sb12-m1-c1": as_rows(m8, "sb-c1")}))
    assert line(out, "CONTROL", "sb12-ctl-m8").endswith("PASS")
    assert "inset 4096 (frozen >=4055)" in line(out, "CONTROL", "sb12-rep-m0-c0")
    assert line(out, "CONTROL", "sb12-rep-m0-c0").endswith("PASS")
    assert line(out, "ROW", "sb12-m0-c1").endswith("held H-FIXED-PX, H-FIXED")
    assert line(out, "ROW", "sb12-m1-c1").endswith("held H-O0")
    (tmp_path / "b").mkdir()
    out = score("sb12", kept(tmp_path / "b", "sb12", {"sb12-ctl-m8": as_rows(m0, "sb-c0")}))
    assert line(out, "CONTROL", "sb12-ctl-m8").endswith("FAILED")


def test_read_files_reads_what_score_reads(tmp_path):
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    d = kept(tmp_path, "t3c", {"t3c-ctl": k(E564 % "an-t3b11")})
    S.read_files("t3c", str(d))
    assert all(S.REQUIRED[s][0] == ".txt" for s in S.REQUIRED)
