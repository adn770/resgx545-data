# SPDX-License-Identifier: MIT
"""The tables and predictions are what gen/make.py writes, and the twin of the plan's rows:
closing19/plan/rank-round19.md section 4 (S3): own2 6 jobs (0xc x2 at 0x28, 0x4 x1, P 0x30 and
0x24, 2048x1536), own1 6 jobs (64x64 0xc x2, 0x4 x1, 1024x768 at 0x422 x2, P 0x200), t18b only,
render_keep armed in every row, no --final-pb-pages."""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402

PLAN = {
    "own2": [("control", "1024", "768", "0x28", "0xc"), ("fit", "1024", "768", "0x28", "0xc"),
             ("fit", "1024", "768", "0x28", "0x4"), ("heldout", "1024", "768", "0x30", "0xc"),
             ("heldout", "1024", "768", "0x24", "0xc"), ("heldout", "2048", "1536", "0x28", "0xc")],
    "own1": [("control", "64", "64", "0x422", "0x4"), ("fit", "64", "64", "0x422", "0xc"),
             ("fit", "64", "64", "0x422", "0xc"), ("heldout", "1024", "768", "0x422", "0xc"),
             ("heldout", "1024", "768", "0x422", "0xc"), ("heldout", "64", "64", "0x200", "0xc")],
}


def test_generated_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen", "make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def a(args, name):
    s = args.split()
    return s[s.index(name) + 1] if name in s else None


def test_twin_of_the_plan():
    for stage, want in PLAN.items():
        rows = K.table(KP, stage)
        assert len(rows) == 6
        got = []
        for r in rows:
            k = dict(w.split("=", 1)[0:2] for w in r["knobs"] if w.startswith("dbg:"))
            assert k["dbg:render_keep"] == "1", r["name"]
            assert r["tool"] == "t18b" and r["risk"] == "safe"
            s = r["args"].split()
            assert s[0] == "tri" and "--ctx2" in s and "--close-first-early" in s
            assert a(r["args"], "--kept-copy") == '"$W"' and a(r["args"], "--words") == '"$W"'
            assert "--final-pb-pages" not in s and "--geometry" not in s and "expectfault" not in r["knobs"]
            kp = a(r["args"], "--kpoke-render")
            assert kp.startswith("1:ta:7^=")
            got.append((r["set"], a(r["args"], "--width"), a(r["args"], "--height"),
                        k["dbg:render_pb_pages"], kp[8:]))
        assert got == want, stage


def test_controls_first_and_read():
    for stage in PLAN:
        rows = K.table(KP, stage)
        assert rows[0]["set"] == "control" and rows[0]["reads"] == ("ovf", "kept", "size")
        assert all(r["set"] != "control" for r in rows[1:])
