# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- Must hold: E1047's kept f1-zero output (render/closing-r14-flag, attempt 20261114-060824) as
  tw-zero's: the control PASSes (its frozen image is that output's).
- The mock's worlds as kept stages: model (H-TWP 6 of 6, U16-TX 1 of 1, H-FOOT-TW 2 of 2, every
  rival FAILED; H-CLAMP1 holds the three u-below-1 rows and fails the three past 1), alt (H-TWP4128,
  U16-T32, H-FOOT-SHIFT hold, H-TWP fails), alt2 (H-WRAPW, U16-DW, H-POINT hold).
- Must fail: E1047's kept f1-small output as tw-zero's (another image): the control FAILED and
  every held-out row cannot tell; a held-out row that faulted: every model of it FAILED (no model
  predicts a fault); a bilinear image off by 2 in one byte of one pixel: its model FAILED (TOL 1);
  a u16 image whose high halves differ: still held (only the low 16 bits are predicted)."""
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
import tw  # noqa: E402
import world as Wd  # noqa: E402

PY = sys.executable
HEAD = "\t".join(K.COLUMNS) + "\n"


def kept(d, rows):
    """rows: {name: (class, out text)} -> a kept tw14 directory."""
    os.makedirs(d, exist_ok=True)
    lines = [HEAD]
    for r in K.table(KP, "tw14"):
        if r["name"] not in rows:
            continue
        cls, out = rows[r["name"]]
        lines.append("\t".join([r["name"], "tw14", r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], "0" if cls == "ok" else "3", cls, "-", "-",
                                "999999"]) + "\n")
        with gzip.open(os.path.join(d, r["name"] + ".txt.gz"), "wb") as f:
            f.write(out.encode())
    open(os.path.join(d, "cases.tsv"), "w").write("".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(HEAD)
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def score(d):
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), "tw14", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def summary(out, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: tw14: {model}: "))


def control(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"CONTROL {name}: "))


def probe(name, world):
    a = Wd.tw14(["probe", "--temps", "32", "--coords", "--pixels", "--scratch-pages", "256",
                 os.path.join(KP, "bins", name + ".bin")], set(world))
    return a["out"]


def world_rows(world):
    return {r["name"]: ("ok", probe(r["name"], {world})) for r in K.table(KP, "tw14")}


def e1047(name):
    return gzip.decompress(pins.blob(tw.KEPT + name + ".txt.gz")).decode(errors="replace")


def test_tw_zero_holds_on_e1047s_kept_output(tmp_path):
    rows = world_rows("model")
    rows["tw-zero"] = ("ok", e1047("f1-zero"))
    out = score(kept(str(tmp_path / "k"), rows))
    assert control(out, "tw-zero").endswith(": PASS"), out
    assert out.count(": PASS") == 5


def test_model_world(tmp_path):
    out = score(kept(str(tmp_path / "k"), world_rows("model")))
    assert "(6 of 6 rows decided)" in summary(out, "H-TWP"), out
    assert "(1 of 1 rows decided)" in summary(out, "U16-TX")
    assert "(2 of 2 rows decided)" in summary(out, "H-FOOT-TW")
    assert "3 held, 3 FAILED" in summary(out, "H-CLAMP1")
    for m in ("H-TWP4128", "H-WRAPW", "H-TWP4096"):
        assert "0 held, 6 FAILED" in summary(out, m), m
    for m in ("U16-T32", "U16-DW", "H-FOOT-SHIFT", "H-POINT"):
        assert "0 held" in summary(out, m), m
    assert "READING tw128-u2: 2048 of 2048 pixels name a scratch dword; dwords" in out


def test_alt_worlds(tmp_path):
    out = score(kept(str(tmp_path / "a"), world_rows("alt")))
    for m in ("H-TWP4128", "U16-T32", "H-FOOT-SHIFT"):
        assert "rows decided)" in summary(out, m) and "not supported" not in summary(out, m), m
    assert "0 held, 6 FAILED" in summary(out, "H-TWP")
    out = score(kept(str(tmp_path / "b"), world_rows("alt2")))
    for m in ("H-WRAPW", "U16-DW", "H-POINT"):
        assert "rows decided)" in summary(out, m) and "not supported" not in summary(out, m), m


def test_must_fail(tmp_path):
    rows = world_rows("model")
    rows["tw-zero"] = ("ok", e1047("f1-small"))
    out = score(kept(str(tmp_path / "z"), rows))
    assert control(out, "tw-zero").endswith(": FAILED")
    assert "controls FAILED" in summary(out, "H-TWP") and "ROW tw16-u0 H-TWP" in out
    assert "cannot tell" in next(ln for ln in out.splitlines() if ln.startswith("ROW tw16-u0 H-TWP:"))

    rows = world_rows("model")
    rows["tw128-u2"] = ("fault", rows["tw128-u2"][1].split("row 0:")[0])
    out = score(kept(str(tmp_path / "f"), rows))
    assert "5 held, 1 FAILED" in summary(out, "H-TWP"), out


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
    rows["tw-bl32"] = ("ok", tweak(rows["tw-bl32"][1], 5, lambda v: v ^ 0x00000200))   # byte 1 +-2
    rows["tw-u16"] = ("ok", tweak(rows["tw-u16"][1], 5, lambda v: v ^ 0x12340000))     # high half
    out = score(kept(str(tmp_path / "t"), rows))
    assert "1 held, 1 FAILED" in summary(out, "H-FOOT-TW"), out
    assert "(1 of 1 rows decided)" in summary(out, "U16-TX"), out
