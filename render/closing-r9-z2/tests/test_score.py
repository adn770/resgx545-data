# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept directories it must hold on and must fail on. No
kept record has a negative stored depth (Q101's gap), so the dumps are synthetic: ramp b's
format-0 reference and the format-1 (bit 19) and format-2 dumps each model makes of it. The model
that made a dump is held, the others FAILED; the control PASSes at 32768 changed dwords and FAILs
at another count; a row whose reference did not run cannot tell."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import z2 as Z  # noqa: E402
from test_gen import ramp  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def kept(d, outputs, dumps):
    d.mkdir()
    table = {ln.split("|")[0]: ln.split("|") for ln in open(os.path.join(KP, "tables/z2.txt"))
             if ln.strip() and not ln.startswith("#")}
    rows = ["\t".join(COLS)]
    for n, text in outputs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        t = table[n]
        rows.append("\t".join([n, "z2", t[1], t[2], t[3], t[4], "x", "0", "ok", "-", "-", "0"]))
    for n, v in dumps.items():
        (d / f"{n}.depth.1.bin.gz").write_bytes(gzip.compress(struct.pack("<%dI" % len(v), *v)))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "z2", str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def made(z0, fmt, b19, model):
    v = [0xDEADBEEF] * len(z0)
    for i, x in Z.predict(z0, fmt, b19, model).items():
        v[i] = x
    return v


def line(out, n):
    return [ln for ln in out.splitlines() if ln.startswith(f"ROW {n}:") or ln.startswith(f"CONTROL {n}:")][0]


def test_each_model_held_on_its_own_dump(tmp_path):
    z0 = ramp(-0.25)
    for m in ("H-ABS", "H-CLAMP", "H-WRAP"):
        out = score(kept(tmp_path / m, {"z2-b-f0": "job: ok\ndepth #1: 24576 dwords, 32768 changed\n",
                                        "z2-b-f1-b19": "job: ok\n", "z2-b-f2": "job: ok\n"},
                         {"z2-b-f0": z0, "z2-b-f1-b19": made(z0, 1, True, m),
                          "z2-b-f2": made(z0, 2, False, m)}))
        assert line(out, "z2-b-f0").endswith("PASS")
        for n in ("z2-b-f1-b19", "z2-b-f2"):
            held = line(out, n).split("held ")[1].split(", ")
            assert m in held and not {"H-ABS", "H-CLAMP", "H-WRAP"} - {m} & set(held), (m, n)


def test_control_fails_and_no_reference(tmp_path):
    z0 = ramp(-0.25)
    out = score(kept(tmp_path / "a", {"z2-b-f0": "job: ok\ndepth #1: 24576 dwords, 30000 changed\n",
                                      "z2-a-f1": "job: ok\n"},
                     {"z2-b-f0": z0, "z2-a-f1": made(z0, 1, False, "H-ABS")}))
    assert line(out, "z2-b-f0").endswith("FAILED")
    assert line(out, "z2-a-f1").endswith("cannot tell")
    assert "controls FAILED" in out
