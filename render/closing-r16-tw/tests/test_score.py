# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- Must hold: E1049's kept tw-bl32 output (render/closing-r15-tw, attempt 20261114-074356) as
  bl32r's: the control PASSes (its frozen image is that output's).
- The mock's worlds as kept stages: model (H-TWP-H 8 of 8, F-FRAC 6 of 6, H-MOVEH and H-POINT
  FAILED on every row they part), alt, alt2, alt3, alt4 (each world's own forms hold where they
  part, H-TWP-H or F-FRAC fail there).
- Must fail: E1049's kept tw-bl16 output as bl32r's (another image): the control FAILED and every
  held-out row cannot tell; a ref16h64 with one pixel off: the H 64 rows cannot tell, the others
  decided; a held-out row that faulted: every model of it FAILED (no model predicts a fault); a
  bilinear image off by 2 in one byte of one pixel: its model FAILED (TOL 1)."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import pins  # noqa: E402
import tw16 as T  # noqa: E402
import world as Wd  # noqa: E402

PY = sys.executable
HEAD = "\t".join(K.COLUMNS) + "\n"


def kept(d, rows):
    """rows: {name: (class, out text)} -> a kept tw16 directory."""
    os.makedirs(d, exist_ok=True)
    lines = [HEAD]
    for r in K.table(KP, "tw16"):
        if r["name"] not in rows:
            continue
        cls, out = rows[r["name"]]
        lines.append("\t".join([r["name"], "tw16", r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], "0" if cls == "ok" else "3", cls, "-", "-",
                                "999999"]) + "\n")
        with gzip.open(os.path.join(d, r["name"] + ".txt.gz"), "wb") as f:
            f.write(out.encode())
    open(os.path.join(d, "cases.tsv"), "w").write("".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(HEAD)
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def score(d):
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), "tw16", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def summary(out, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: tw16: {model}: "))


def control(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"CONTROL {name}: "))


def rowline(out, name, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"ROW {name} {model}: "))


def probe(name, world):
    a = Wd.tw16(["probe", "--temps", "32", "--coords", "--pixels", "--scratch-pages", "256",
                 os.path.join(KP, "bins", name + ".bin")], set(world))
    return a["out"]


def world_rows(world):
    return {r["name"]: ("ok", probe(r["name"], {world})) for r in K.table(KP, "tw16")}


def e1049(name):
    return gzip.decompress(pins.blob(T.KEPT15 + name + ".txt.gz")).decode(errors="replace")


def test_bl32r_holds_on_e1049s_kept_output(tmp_path):
    rows = world_rows("model")
    rows["bl32r"] = ("ok", e1049("tw-bl32"))
    out = score(kept(str(tmp_path / "k"), rows))
    assert control(out, "bl32r").endswith(": PASS"), out
    assert out.count("CONTROL ") == 3 and out.count(": PASS") == 3


def test_model_world(tmp_path):
    out = score(kept(str(tmp_path / "k"), world_rows("model")))
    assert "(8 of 8 rows decided)" in summary(out, "H-TWP-H"), out
    assert "(6 of 6 rows decided)" in summary(out, "F-FRAC"), out
    assert "0 held, 4 FAILED" in summary(out, "H-MOVEH")
    assert "6 held, 2 FAILED" in summary(out, "H-TWP-T16")
    for m in ("H-TWP-V32", "H-TWP-STRIP", "H-TWP4128"):
        assert "4 held, 4 FAILED" in summary(out, m), m
    assert "0 held, 6 FAILED" in summary(out, "H-POINT")
    for n, m in (("bl64left", "H-FOOT-SHIFT"), ("bl128right", "H-FOOT-SHIFT"),
                 ("bl128right", "H-FOOT-TW"), ("bl128h16right", "H-FOOT-TW"),
                 ("bl128vedge", "F-VNEXT")):
        assert ": FAILED" in rowline(out, n, m), (n, m)
    assert "READING pt64h64u1: 2048 of 2048 pixels name a scratch dword; dwords" in out


def test_alt_worlds(tmp_path):
    """Each world's forms hold on every row (their images are the frozen ones) and the stage's
    forms fail where they part."""
    for world, point, bil in (("alt", ("H-TWP-T16", "H-TWP-V32"), "H-FOOT-SHIFT"),
                              ("alt2", ("H-TWP-STRIP",), "H-FOOT-TW"),
                              ("alt3", ("H-MOVEH", "H-TWP4128"), "F-VNEXT"),
                              ("alt4", (), "H-POINT")):
        out = score(kept(str(tmp_path / world), world_rows(world)))
        assert "(6 of 6 rows decided)" in summary(out, bil), (world, out)
        assert "0 held" not in summary(out, bil)
        assert "FAILED" in summary(out, "F-FRAC"), world
        for m in point:
            assert "FAILED" in summary(out, "H-TWP-H"), (world, m)
            assert any(ln.startswith(f"ROW ") and f" {m}: " in ln and ln.endswith(": held")
                       for ln in out.splitlines()), (world, m)


def test_must_fail(tmp_path):
    rows = world_rows("model")
    rows["bl32r"] = ("ok", e1049("tw-bl16"))
    out = score(kept(str(tmp_path / "z"), rows))
    assert control(out, "bl32r").endswith(": FAILED")
    assert "controls FAILED" in summary(out, "H-TWP-H")
    assert "cannot tell" in rowline(out, "pt32h16", "H-TWP-H")
    assert "cannot tell" in rowline(out, "bl64in", "F-FRAC")

    rows = world_rows("model")
    rows["ref16h64"] = ("ok", tweak(rows["ref16h64"][1], 3, lambda v: v ^ 1))
    out = score(kept(str(tmp_path / "r"), rows))
    assert control(out, "ref16h64").endswith(": FAILED")
    assert "cannot tell" in rowline(out, "pt64h64u0", "H-TWP-H")
    assert rowline(out, "pt32h8", "H-TWP-H").endswith(": held")

    rows = world_rows("model")
    rows["pt64h64u1"] = ("fault", rows["pt64h64u1"][1].split("row 0:")[0])
    out = score(kept(str(tmp_path / "f"), rows))
    assert "7 held, 1 FAILED" in summary(out, "H-TWP-H"), out


def tweak(text, y, fn):
    out = []
    for ln in text.splitlines():
        if f": row {y}: " in ln:
            head, vals = ln.split(f": row {y}: ")
            v = vals.split()
            v[0] = "%08x" % fn(int(v[0], 16))
            ln = f"{head}: row {y}: " + " ".join(v)
        out.append(ln)
    return "\n".join(out) + "\n"


def test_tolerances(tmp_path):
    rows = world_rows("model")
    rows["bl64in"] = ("ok", tweak(rows["bl64in"][1], 5, lambda v: v ^ 0x00000200))   # byte 1 +-2
    out = score(kept(str(tmp_path / "t"), rows))
    assert "5 held, 1 FAILED" in summary(out, "F-FRAC"), out
