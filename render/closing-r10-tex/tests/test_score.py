# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

addr3: E957's kept addr-ctl-u0 (control PASS; addr-u4-rep in its place FAILED) and addr-u4-rep
(every rival held: all give + 180 at 16 x 16); E957's addr-u4-n8 in the 4 x 4 row's place (no
frozen model). cube3: E726's cu-xn (PASS), cu-xp in its place (FAILED); r8-geo's kept cube-off-a2
as the replay: H-FMADNE held with lower 4, H-HIGHAXIS FAILED. t3b: E566's s64x32-ctl and
s64x32-t3b14 (PASS), s64x16-ctl in t3b-ctl's place (FAILED); E975's b14-u01 as the replicate
(R-4096, H-E975 held); a held-out row whose reference did not run is GATED (cannot tell). srgb2:
E723's g-bl-st-a (PASS), g-bl-st-b in its place (FAILED). Edges: the generator's own H-SEAM-FLOAT
bytes (rounded) as the kept edge row: H-SEAM-FLOAT held, H-SEAM-ADJ FAILED."""
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
R9G = "data:render/closing-r9-geo/out/20261113-081038/addr2/%s.txt.gz"
E566 = "data:texture/p1132/tx-t3/%s.txt.gz"
E726 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-h-cube/%s.txt.gz"
E723 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/%s.txt.gz"


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


def as_rows(values, prefix="probe x: "):
    return "".join(prefix + "row %d: " % y + " ".join("%08x" % v for v in values[64 * y:64 * y + 64])
                   + "\n" for y in range(32))


def test_addr3_holds_and_fails(tmp_path):
    out = score("addr3", kept(tmp_path, "addr3", {
        "addr3-ctl-u0": k(R9G % "addr-ctl-u0"), "addr3-u4-rep": k(R9G % "addr-u4-rep"),
        "addr3-4x4-u4": k(R9G % "addr-u4-n8")}))
    assert line(out, "CONTROL", "addr3-ctl-u0").endswith("PASS")
    assert "held H-W, H-H, H-SQ, H-WH" in line(out, "ROW", "addr3-u4-rep")
    assert "+180 x2048" in line(out, "ROW", "addr3-u4-rep")
    assert line(out, "ROW", "addr3-4x4-u4").endswith("no frozen model exact")
    (tmp_path / "b").mkdir()
    out = score("addr3", kept(tmp_path / "b", "addr3", {"addr3-ctl-u0": k(R9G % "addr-u4-rep")}))
    assert line(out, "CONTROL", "addr3-ctl-u0").endswith("FAILED")
    assert "controls FAILED" in out


def test_cube3_holds_and_fails(tmp_path):
    a2 = k("data:render/closing-r8-geo/out/20261113-015842/cube/cube-off-a2.txt.gz")
    out = score("cube3", kept(tmp_path, "cube3", {"cube3-ctl-xn": k(E726 % "cu-xn"),
                                                   "cube3-a2-replay": a2}))
    assert line(out, "CONTROL", "cube3-ctl-xn").endswith("PASS")
    row = line(out, "ROW", "cube3-a2-replay")
    assert "H-FMADNE 2048/2048 pixels, lower 4 (frozen 4)" in row and row.endswith("held H-FMADNE")
    assert "H-HIGHAXIS" in row and "lower 4 (frozen 0)" in row
    (tmp_path / "b").mkdir()
    out = score("cube3", kept(tmp_path / "b", "cube3", {"cube3-ctl-xn": k(E726 % "cu-xp")}))
    assert line(out, "CONTROL", "cube3-ctl-xn").endswith("FAILED")


def test_cube3_edges(tmp_path):
    toks = open(os.path.join(KP, "predictions/cube3/cube3-edge-yx.H-SEAM-FLOAT.txt")).read().split()
    vals = []
    for t in toks:
        if t == "-":
            vals.append(0xD0000000)
        else:
            vals.append(sum(int(float(b) + 0.5) << 8 * i for i, b in enumerate(t[2:].split(","))))
    out = score("cube3", kept(tmp_path, "cube3", {"cube3-ctl-xn": k(E726 % "cu-xn"),
                                                   "cube3-edge-yx": as_rows(vals)}))
    row = line(out, "ROW", "cube3-edge-yx")
    assert "H-SEAM-FLOAT in 1024/1024, out 512/512 within 1" in row
    assert row.endswith("held H-SEAM-FLOAT")
    assert "SUMMARY: cube3: H-SEAM-ADJ (heldout) is not supported: 0 held, 1 FAILED" in out


def test_t3b_holds_fails_and_gates(tmp_path):
    out = score("t3b", kept(tmp_path, "t3b", {
        "t3b-ctl": k(E566 % "s64x32-ctl"), "t3b-b14ref": k(E566 % "s64x32-t3b14"),
        "t3b-u01": k("data:render/closing-r9-x/out/20261113-081821/t3/b14-u01.txt.gz"),
        "t3b-s256": k("data:render/closing-r9-x/out/20261113-081821/t3/b14-u01.txt.gz")}))
    assert line(out, "CONTROL", "t3b-ctl").endswith("PASS")
    assert line(out, "CONTROL", "t3b-b14ref").endswith("PASS")
    row = line(out, "ROW", "t3b-u01")
    assert "R-4096 2048/2048" in row and "H-E975 2048/2048" in row
    assert "GATED t3b-s256: its reference t3b-s256-ref did not hold H-TEXMODEL" in out
    assert "SUMMARY: t3b: R-4096 (heldout): cannot tell: no row decided" in out
    (tmp_path / "b").mkdir()
    out = score("t3b", kept(tmp_path / "b", "t3b", {"t3b-ctl": k(E566 % "s64x16-ctl")}))
    assert line(out, "CONTROL", "t3b-ctl").endswith("FAILED")


def test_srgb2_holds_and_fails(tmp_path):
    out = score("srgb2", kept(tmp_path, "srgb2", {"srgb2-ctl": k(E723 % "g-bl-st-a")}))
    assert line(out, "CONTROL", "srgb2-ctl").endswith("PASS")
    (tmp_path / "b").mkdir()
    out = score("srgb2", kept(tmp_path / "b", "srgb2", {"srgb2-ctl": k(E723 % "g-bl-st-b")}))
    assert line(out, "CONTROL", "srgb2-ctl").endswith("FAILED")


def test_read_files_reads_what_score_reads(tmp_path):
    sys.path.insert(0, os.path.join(KP, "score"))
    import score as S
    d = kept(tmp_path, "t3b", {"t3b-ctl": k(E566 % "s64x32-ctl")})
    S.read_files("t3b", str(d))
    assert S.REQUIRED["t3b"][0] == ".txt"
