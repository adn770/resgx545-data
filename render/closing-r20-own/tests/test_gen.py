# SPDX-License-Identifier: MIT
"""The tables and predictions are what gen/make.py writes, and the twin of the plan's rows:
closing20/plan/rank-round20.md section 4 (S2): ow 4 (control, two -128,-96-like moves, one 64,64),
owt 2 (unmoved, short register list), owp 5 (0x30 x2, 0x30 moved, 0x2c, 0x34), t18b under rt
only, render_keep armed, no --final-pb-pages; and gen/cover.py's covers."""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
import cover as C  # noqa: E402
import kitscore as K  # noqa: E402

LONG = "0x0620-0x0634,0x0658,0x065c,0x0674,0x0694,0x0698,0x0700-0x0728"
SHORT = "0x062c,0x0634,0x0694,0x0698"
PLAN = {
    "ow": [("control", "0x422", None, LONG), ("fit", "0x422", "1:-112,-80", LONG),
           ("fit", "0x422", "1:-112,-80", LONG), ("heldout", "0x422", "1:64,64", LONG)],
    "owt": [("control", "0x422", None, SHORT), ("heldout", "0x422", None, SHORT)],
    "owp": [("control", "0x30", None, LONG), ("fit", "0x30", None, LONG),
            ("heldout", "0x30", "1:-112,-80", LONG), ("heldout", "0x2c", None, LONG),
            ("heldout", "0x34", None, LONG)],
}
FORM = ("tri --width 1024 --height 768 -n 1 --keep-overflow --wait-ms 20000 --ctx2 "
        "--close-first-early --kept-copy \"$W\" --words \"$W\" --kpoke-render 1:ta:7^=0xc").split()


def test_generated_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen", "make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_twin_of_the_plan():
    n = 0
    for stage, want in PLAN.items():
        rows = K.table(KP, stage)
        got = []
        for r in rows:
            k = dict(w.split("=", 1) for w in r["knobs"] if w.startswith("dbg:"))
            assert k["dbg:render_keep"] == "1" and r["tool"] == "rt" and r["risk"] == "safe"
            s = r["args"].split()
            assert s[:2] == ["0", "0.3"] and s[3:5] == ["--", '"$HOME/sgxfive-test-t18b"']
            t = s[5:]
            assert t[:len(FORM)] == FORM, r["name"]
            assert len(t) in (len(FORM), len(FORM) + 2)
            mv = t[-1] if len(t) > len(FORM) else None
            assert mv is None or t[-2] == "--move"
            assert "expectfault" not in r["knobs"] and "expectdiff" not in r["knobs"]
            got.append((r["set"], k["dbg:render_pb_pages"], mv, s[2]))
            n += 1
        assert got == want, stage
    assert n == 11


def test_controls_first_and_read():
    for stage in PLAN:
        rows = K.table(KP, stage)
        assert rows[0]["set"] == "control" and rows[0]["reads"] == ("ovf", "kept", "size")
        assert all(r["set"] != "control" for r in rows[1:])


def test_covers():
    assert C.cover(0, 0) == [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 13]     # E1087's lists
    assert C.cover(-128, -96) is None                                # the plan's: rules differ
    assert C.cover(-112, -80) == [0, 1, 2, 3, 4, 5, 6, 8, 9, 12]
    assert C.cover(64, 64) == [0, 1, 4, 5, 6, 7, 9, 10, 11, 13, 14]
