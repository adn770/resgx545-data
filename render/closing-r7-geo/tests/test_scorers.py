#!/usr/bin/env python3
"""test_scorers.py: the scorers on ARGV-DRIVEN worlds (worlds.kept: every row of the frozen table answered from its argv, as the
runner keeps it): each verdict follows the world, the controls gate what they must, void rows are cannot tell."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "score"))
os.environ["R7G_NO_FREEZE_CHECK"] = "1"
import worlds as W  # noqa: E402
import score_g as S  # noqa: E402

bad = n = 0


def check(c, what):
    global bad, n
    n += 1
    print(("ok   " if c else "FAIL ") + what)
    bad += 0 if c else 1


CASES = [
    ("xf", "model", ["Q206 both fields: H-INDEP held (8 of 8", "H-XFIRST held is not supported", "H-YFIRST held is not supported"]),
    ("xf", "xfirst", ["H-XFIRST held (8 of 8", "H-INDEP held is not supported"]),
    ("xf", "yfirst", ["H-YFIRST held (8 of 8", "H-INDEP held is not supported"]),
    ("tx", "model", ["Q283 type 4 S32 held (5 of 5", "Q283 types 1 and 3 RASTERW held (6 of 6", "Q178 type 5 H-STEP held (3 of 3",
                     "does not follow the texture) held (2 of 2", "Q283 type 4 SMAXW held is not supported"]),
    ("tx", "s2wcap", ["Q283 type 4 S2WCAP held (5 of 5", "Q283 type 4 S32 held is not supported"]),
    ("tx", "fix16", ["Q178 type 5 H-FIX16 held (3 of 3", "Q178 type 5 H-STEP held is not supported"]),
    ("tx", "mem", ["does not follow the texture) held is not supported: 1 held, 1 FAILED"]),
    ("zi", "model", ["Q262 iteration H-ITER held (24 of 24", "Q262 iteration H-E606 held (24 of 24"]),
    ("zs", "model", ["Q260 H-HU exact on the held-out rows (143 of 143", "FIT SETUP(c) on the -0.5 x sweep: c in [8]", "Q260 H-HA exact on the held-out rows is not supported"]),
    ("zs", "ha", ["Q260 H-HA exact on the held-out rows (143 of 143", "c in [7]", "Q260 H-HU exact on the held-out rows is not supported"]),
    ("zs", "setup5", ["c in [5]", "Q260 SETUP(c=5) exact on the held-out rows (143 of 143", "Q260 H-HA exact on the held-out rows is not supported"]),
    ("zs", "far", ["Q260 H-FAR exact on the held-out rows (143 of 143", "Q260 H-HU exact on the held-out rows is not supported"]),
    ("zs", "norecord", ["Q260 H-HU: controls FAILED: zs-ctl-e683-1401234"]),
    ("zd", "zls-dead,depth-off,big-fail", ["Q262 depth H-ZLS held on every size is not supported", "Q262 depth H-DEPTH held on every size is not supported",
                                           "Q262 depth H-E606 held on every size (97 of 100", "SIZE H-E606 4096x4096: 1 held, 0 FAILED, 3 cannot tell"]),
    ("zf", "tiny-refuse", ["Q240 family H-E606 held on every size (192 of 240", "SIZE H-E606 16x8: 0 held, 0 FAILED, 24 cannot tell"]),
    ("zf", "norecord", ["Q240 family H-E606: controls FAILED: zf-ctl-e606-128x128"]),
]
for st, world, want in CASES:
    d = tempfile.mkdtemp(prefix="scorers.", dir=os.path.join(KP, "debug"))
    W.kept(d, st, world)
    out = "\n".join(S.score(st, d))
    miss = [k for k in want if k not in out]
    check(not miss, "%s in world %s: %s" % (st, world, "; ".join(want)[:150] if not miss else "MISSING " + " | ".join(miss)))
    if miss:
        print("\n".join(l for l in out.splitlines() if l.startswith(("SUMMARY", "SIZE", "FIT")))[:1500])
print("%d of %d scorer checks" % (n - bad, n))
sys.exit(1 if bad else 0)
