# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- Must hold: E1058's kept bl64left output (render/closing-r16-tw, attempt 20261114-093404) as
  bl64leftr's: the control PASSes (its frozen image is that output's).
- The mock's worlds as kept stages: model (H-WIDE 7 of 7, H-WIDE-PT 3 of 3, the LEFT-WRAP rule
  names H-WIDE, every rival FAILED where it parts), wideg (the LEFT-WRAP rule names H-WIDE-G),
  next, unwrap, ffrac, point (each world's forms hold where they part, H-WIDE fails there).
- Must fail: E1058's kept bl64in output as bl64leftr's (another image): the control FAILED, every
  held-out row cannot tell and LEFT-WRAP cannot tell; a ref256 with one pixel off: the W 256 rows
  cannot tell, the others decided; a held-out row that faulted: every model of it FAILED; a
  bilinear image off by 2 in one byte of one pixel: its model FAILED (TOL 1); left-wrap pixels
  within 1 but exact on half: LEFT-WRAP cannot tell; the W <= 128 rows alone (a stop before the
  new widths): LEFT-WRAP still decided (93 pixels, MIN_LEFT 64)."""
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
import tw17 as T  # noqa: E402
import world as Wd  # noqa: E402

PY = sys.executable
HEAD = "\t".join(K.COLUMNS) + "\n"


def kept(d, rows):
    """rows: {name: (class, out text)} -> a kept tw17 directory."""
    os.makedirs(d, exist_ok=True)
    lines = [HEAD]
    for r in K.table(KP, "tw17"):
        if r["name"] not in rows:
            continue
        cls, out = rows[r["name"]]
        lines.append("\t".join([r["name"], "tw17", r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], "0" if cls == "ok" else "3", cls, "-", "-",
                                "999999"]) + "\n")
        with gzip.open(os.path.join(d, r["name"] + ".txt.gz"), "wb") as f:
            f.write(out.encode())
    open(os.path.join(d, "cases.tsv"), "w").write("".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(HEAD)
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def score(d):
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), "tw17", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def summary(out, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: tw17: {model}: "))


def control(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"CONTROL {name}: "))


def rowline(out, name, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"ROW {name} {model}: "))


def probe(name, world):
    a = Wd.tw17(["probe", "--temps", "32", "--coords", "--pixels", "--scratch-pages", "256",
                 os.path.join(KP, "bins", name + ".bin")], set(world))
    return a["out"]


def world_rows(world):
    return {r["name"]: ("ok", probe(r["name"], {world})) for r in K.table(KP, "tw17")}


def e1058(name):
    return gzip.decompress(pins.blob(T.KEPT16 + name + ".txt.gz")).decode(errors="replace")


def test_bl64leftr_holds_on_e1058s_kept_output(tmp_path):
    rows = world_rows("model")
    rows["bl64leftr"] = ("ok", e1058("bl64left"))
    out = score(kept(str(tmp_path / "k"), rows))
    assert control(out, "bl64leftr").endswith(": PASS"), out
    assert out.count("CONTROL ") == 4 and out.count(": PASS") == 4


def test_model_world(tmp_path):
    out = score(kept(str(tmp_path / "k"), world_rows("model")))
    assert "(7 of 7 rows decided)" in summary(out, "H-WIDE"), out
    assert "(3 of 3 rows decided)" in summary(out, "H-WIDE-PT"), out
    assert "0 held, 3 FAILED" in summary(out, "H-TWP")
    assert "0 held, 7 FAILED" in summary(out, "H-POINT")
    assert "3 held, 4 FAILED" in summary(out, "H-WIDE-NEXT")
    assert "2 held, 5 FAILED" in summary(out, "UNWRAP-G")
    assert "(7 of 7 rows decided)" in summary(out, "H-WIDE-G")   # within 1: one image
    assert summary(out, "LEFT-WRAP").endswith(
        "189 parting pixels, H-WIDE exact 189, H-WIDE-G exact 0: column -1 reads W' - 1 (H-WIDE)")
    assert "RIGHTWRAP bl2048edge: 320 parting pixels; H-WIDE 320; H-WIDE-NEXT 0" in out


def test_alt_worlds(tmp_path):
    """Each world's forms hold on every row (their images are the frozen ones) and H-WIDE fails
    where they part (wideg: only the LEFT-WRAP rule parts them)."""
    for world, bil, pt in (("next", "H-WIDE-NEXT", "H-WIDE-PT"), ("unwrap", "UNWRAP-G", "H-TWP"),
                           ("ffrac", "F-FRAC", "H-TWP"), ("point", "H-POINT", "H-WIDE-PT")):
        out = score(kept(str(tmp_path / world), world_rows(world)))
        assert "(7 of 7 rows decided)" in summary(out, bil), (world, out)
        assert "(3 of 3 rows decided)" in summary(out, pt), (world, out)
        assert "FAILED" in summary(out, "H-WIDE"), world
    out = score(kept(str(tmp_path / "wideg"), world_rows("wideg")))
    assert summary(out, "LEFT-WRAP").endswith(
        "189 parting pixels, H-WIDE exact 0, H-WIDE-G exact 189: column -1 reads W - 1 (H-WIDE-G)")


def tweak(text, y, fn, x=0):
    out = []
    for ln in text.splitlines():
        if f": row {y}: " in ln:
            head, vals = ln.split(f": row {y}: ")
            v = vals.split()
            v[x] = "%08x" % fn(int(v[x], 16))
            ln = f"{head}: row {y}: " + " ".join(v)
        out.append(ln)
    return "\n".join(out) + "\n"


def test_must_fail(tmp_path):
    rows = world_rows("model")
    rows["bl64leftr"] = ("ok", e1058("bl64in"))
    out = score(kept(str(tmp_path / "z"), rows))
    assert control(out, "bl64leftr").endswith(": FAILED")
    assert "controls FAILED" in summary(out, "H-WIDE")
    assert "cannot tell" in rowline(out, "bl16left", "H-WIDE")
    assert "cannot tell (control bl64leftr: FAILED)" in summary(out, "LEFT-WRAP")

    rows = world_rows("model")
    rows["ref256"] = ("ok", tweak(rows["ref256"][1], 3, lambda v: v ^ 1))
    out = score(kept(str(tmp_path / "r"), rows))
    assert control(out, "ref256").endswith(": FAILED")
    assert "cannot tell" in rowline(out, "bl256edge", "H-WIDE")
    assert "cannot tell" in rowline(out, "pt256off", "H-WIDE-PT")
    assert rowline(out, "bl512edge", "H-WIDE").endswith(": held")
    assert "column -1 reads W' - 1" in summary(out, "LEFT-WRAP")      # 189 - 31 - 1 = 157

    rows = world_rows("model")
    rows["bl2048edge"] = ("fault", rows["bl2048edge"][1].split("row 0:")[0])
    out = score(kept(str(tmp_path / "f"), rows))
    assert "6 held, 1 FAILED" in summary(out, "H-WIDE"), out


def test_tolerances(tmp_path):
    rows = world_rows("model")
    rows["bl16left"] = ("ok", tweak(rows["bl16left"][1], 5, lambda v: v ^ 0x00000200, x=9))
    out = score(kept(str(tmp_path / "t"), rows))
    assert "6 held, 1 FAILED" in summary(out, "H-WIDE"), out


def test_left_wrap_rule_noise_and_a_short_session(tmp_path):
    """Left-wrap pixels within 1 of H-WIDE but exact on half of them: cannot tell. A session that
    stopped before the new widths: the W <= 128 rows alone decide it (93 pixels)."""
    rows = world_rows("model")
    for n in ("bl16left", "bl64grid", "bl128off3", "bl256edge", "bl512edge", "bl256corner",
              "bl2048edge"):
        a, b = T.tokens(n, "H-WIDE"), T.tokens(n, "H-WIDE-G")
        ix = [i for i in range(2048) if a[i] != b[i]]
        text = rows[n][1]
        for i in ix[::2]:
            text = tweak(text, i // 64, lambda v: v ^ 0x00000001, x=i % 64)   # byte 0 off by 1
        rows[n] = ("ok", text)
    out = score(kept(str(tmp_path / "n"), rows))
    assert "(7 of 7 rows decided)" in summary(out, "H-WIDE")
    assert summary(out, "LEFT-WRAP").endswith("cannot tell (neither rule met)"), out

    rows = world_rows("model")
    short = {n: rows[n] for n in rows if T.row(n)[2] <= 128}
    out = score(kept(str(tmp_path / "s"), short))
    assert summary(out, "LEFT-WRAP").endswith(
        "93 parting pixels, H-WIDE exact 93, H-WIDE-G exact 0: column -1 reads W' - 1 (H-WIDE)")
    assert "cannot tell" in rowline(out, "bl256edge", "H-WIDE")
