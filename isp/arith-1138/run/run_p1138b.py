#!/usr/bin/env python3
"""run_p1138b.py: run_p1138.py for the follow-up set (cases-fine.tsv: a 17th column, the vertex unit 1/2^K pixel, passed as
--tri-unit K; the tool is ~/sgxfive-test-1138b).  Only D jobs.  Everything else (markers, health, keeping every output) is
run_p1138.py's, imported unchanged."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_p1138 as R  # noqa: E402

_load = R.load_cases
_vtx = R.vtx_args


def load_cases(path):
    cases = _load(path)
    units = {}
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 17:
            units[int(f[0])] = int(f[16])
    for c in cases:
        c["unit"] = units[c["id"]]
    return cases


def vtx_args(c):
    return ["--tri-unit", str(c["unit"])] + _vtx(c)


def install():
    R.load_cases = load_cases
    R.vtx_args = vtx_args


def uninstall():
    R.load_cases = _load
    R.vtx_args = _vtx


if __name__ == "__main__":
    install()
    R.main()
