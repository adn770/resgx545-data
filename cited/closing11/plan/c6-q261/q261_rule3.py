# Q261 round 3 [post hoc]: written after round 2 (q261_score2.out) fitted exactly one of 51 candidates,
# clip[-16,64+16]/exact-halfup (48 of 48 rows), with the neighbours G = 2, 4, 8 missing only far-x24p
# d = -416.  Scans the one integer parameter of the clip family with E607's half-up rounding:
#   S1: symmetric guard [-G, 64+G], G = 1 .. 48
#   S2: asymmetric (lo guard, hi guard) = [-a, 64+b], a, b in {8, 12, 16, 20, 24, 32}
#   S3: the guard on one axis only (x only or y only), G = 16
# PASS CRITERION (frozen): all 48 rows pixel exact (the interval of G that fits is the result; a fit is
# not a prediction, the scan is post hoc on the rows that suggested it).
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
assert hashlib.sha256(open(os.path.join(HERE, "q261_rule2.py"), "rb").read()).hexdigest() == \
    open(os.path.join(HERE, "q261_rule2.sha256")).read().split()[0]
import q261_rule2 as R2
from q261_rule2 import prep as _prep, decide, Cand


def candidates():
    out = [Cand("exact", "exact")]
    for g in range(1, 49):
        out.append(Cand("S1 G=%d" % g, "clip", lo=-g, hi=64 + g, interp="exact-halfup"))
    for a in (8, 12, 16, 20, 24, 32):
        for b in (8, 12, 16, 20, 24, 32):
            out.append(Cand("S2 lo=-%d hi=64+%d" % (a, b), "clip", lo=-a, hi=64 + b, interp="exact-halfup"))
    return out


def prep(V, cand):
    return _prep(V, cand)
