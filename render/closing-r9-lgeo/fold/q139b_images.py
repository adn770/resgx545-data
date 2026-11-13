#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q139b_images.py (post hoc, the fold, not frozen): H-EVEN alone and H-EVEN with H-LAST (a
tile is drawn iff its surviving header's slot is at or before the slot of the last target tile
the TA writes in block order, the header with the last-region flag; fold/q139b_lastflag.py) on
every kept whole image of resgx545-data ta/mtile-fields and ta/mtile-fields-risky, as the round 9
seeds plan's even_images.py scanned them (E877's loader, its published copy; the same filters).
Read only.
    python3 -I -B fold/q139b_images.py [DATA_REPO]"""
import importlib.util
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402

data = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"
spec = importlib.util.spec_from_file_location("q139_model", os.path.join(data, "cited/closing6/fold-misc/q139/q139_model.py"))
sys.path.insert(0, os.path.join(data, "cited/closing6/fold-misc/q139"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
F = E.F


def wrong(w, h, a, last):
    pred = E.predict(w, h, a, "H-EVEN")
    if not last:
        return E.wrong(pred)
    n = E.geometry(w, h, a)[0]
    key = Q.KEYS["blkrow"]
    drawn = [t for t, v in pred.items() if v is not None]
    if not drawn:
        return set(pred)
    lt = max(drawn, key=lambda t: key(t[1], t[0], 0, 0, n))
    return {t for t, v in pred.items() if v is None or v > pred[lt]}


tot = {False: [0, 0], True: [0, 0]}
for ds in ("ta/mtile-fields", "ta/mtile-fields-risky"):
    for line in list(open(os.path.join(data, ds, "cases.tsv")))[1:]:
        p = line.rstrip("\n").split("\t")
        name, w, h = p[0], int(p[2]), int(p[3])
        args = p[4] if len(p) > 4 else ""
        if any(i not in ("143", "144", "146") for i in re.findall(r"ta:(\d+)=", args)):
            continue
        try:
            m1, m2, s = F.words(w, h, args)
            n, bx, by = F.bounds(m1, m2)
        except Exception:
            continue
        if bx[1] <= 0 or by[1] <= 0 or max(bx[-1] + bx[1], by[-1] + by[1]) > 1024:
            continue
        W, H, job, bad = M.load(os.path.join(data, ds, "dumps", name + ".txt.gz"))
        if bad is None:
            continue
        res = {}
        for last in (False, True):
            ok = wrong(w, h, args, last) == set(bad)
            tot[last][0] += ok
            tot[last][1] += 1
            res[last] = ok
        if not all(res.values()):
            print("%-6s %-40s obs %3d  H-EVEN %s  H-EVEN + H-LAST %s" % (ds.split("/")[1][-5:], name, len(bad),
                                                                         "ok" if res[False] else "NO", "ok" if res[True] else "NO"))
print("H-EVEN alone: %d of %d whole images; with H-LAST: %d of %d" % (*tot[False], *tot[True]))
