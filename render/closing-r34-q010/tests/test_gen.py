# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, every kept input read at
the frozen data commit, its hash checked against the values the generator freezes)."""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP, capture_output=True,
                       text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
