# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, every input read at
the frozen data commit), and the offline fits' outputs are what their scripts print at the frozen
commits: O29-1 (fit/o29_1.out) finds no candidate word, so f3 (Q241) is not built; O29-2
(fit/o29_2.out) finds H-PREV16 fitting E1035's 3 of 3 and E701's c = 8 completion, so h2 is
built, and h2's frozen ends are the ones the fit's deciders give on its rows."""
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402


def run(*a):
    return subprocess.run([sys.executable, "-B", *a], cwd=KP, capture_output=True, text=True, env=ENV)


def test_generator_current():
    r = run("gen/make.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_o29_1_output_current_and_f3_not_built():
    r = run("fit/o29_1.py", CFG["freeze"]["data"][:9])
    assert r.returncode == 0, r.stderr
    assert r.stdout == open(os.path.join(KP, "fit", "o29_1.out")).read()
    assert "candidates (zero in both jobs, an address role, read by bit 10's requestor): none" in r.stdout
    assert "no (f3 is not built)" in r.stdout
    assert "f3" not in CFG["stages"]


def test_o29_2_output_current_and_h2_built():
    r = run("fit/o29_2.py", CFG["freeze"]["data"][:9])
    assert r.returncode == 0, r.stderr
    assert r.stdout == open(os.path.join(KP, "fit", "o29_2.out")).read()
    assert "H-PREV16: fit 15 of 15, held out 3 of 3, E701's c = 8 completion right" in r.stdout
    assert "D-PREVADD: fit 15 of 15, held out 1 of 3" in r.stdout
    assert "yes, H-PREV16 (h2 is built" in r.stdout


def test_h2_ends_follow_the_deciders():
    sys.path.insert(0, os.path.join(KP, "fit"))
    sys.path.insert(0, os.path.join(KP, "gen"))
    import make
    import o29_2
    rows = [(n, v1, v2) for n, _, _, _, v1, v2 in make.H2_ROWS]
    seq = []
    for i, (n, v1, v2) in enumerate(rows):
        seq.append(("r29", "h2", n, v1, v2, 5, i % 3 == 0, "ok"))
    v1 = o29_2.v1_rows(seq)
    fit = [r for r in o29_2.v1_rows(o29_2.jobs(CFG["freeze"]["data"][:9])) if r["src"] != "E1035"]
    d = o29_2.deciders(fit)
    p = K.predictions(KP, "h2")
    for r in v1:
        for m in ("H-PREV16", "D-PREVADD", "D-C", "H-ALWAYS"):
            assert p[r["name"]]["end"][m] == ("hang" if d[m](r) else "ok"), (r["name"], m)
    assert [r["c"] for r in v1] == [8, 3, 1]
