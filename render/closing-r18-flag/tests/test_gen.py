# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, every input read at
the frozen data commit) and O18-1's output (fit/o18_1.out, record E1073) is what fit/o18_1.py
prints at that commit: H-KIND fits 162 of 162 of E509's faulting cases, so f3 is built, and f3's
two rows are the ones the fit predicts for."""
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def run(*a):
    return subprocess.run([sys.executable, "-B", *a], cwd=KP, capture_output=True, text=True, env=ENV)


def test_generator_current():
    r = run("gen/make.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_o18_1_output_current_and_f3_built():
    r = run("fit/o18_1.py", CFG["freeze"]["data"][:9])
    assert r.returncode == 0, r.stderr
    assert r.stdout == open(os.path.join(KP, "fit", "o18_1.out")).read()
    assert "H-KIND: 162 of 162 kinds (100.0 %)" in r.stdout
    assert "yes, H-KIND (f3 is built)" in r.stdout
    rows = {ln.split()[1]: ln for ln in r.stdout.splitlines() if ln.startswith("f3 ")}
    tab = open(os.path.join(KP, "tables", "f3.txt")).read()
    for name, ln in rows.items():
        poke = ln.split()[4].rstrip(":")
        assert f"{name}|" in tab and poke in tab.split(f"{name}|", 1)[1].splitlines()[0]
    assert "H-KIND 0x90004" in rows["f3-k4"] and "H-KIND 0x90100" in rows["f3-k100"]
