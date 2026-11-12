#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""postrun/posthoc_rules.py: a search made at the fold (2026-11-12), after the run (POST HOC).

Does any extent 4 k A B, with A one of the doubled tile columns, the doubled macrotile span, the doubled side or the doubled larger span
across, B the same down, and k in 1/4, 1/2, 1, 2, split the four-array 4x cells on record as measured, against the maximum's tail room,
state page or region offset (gen/rules.py lay())?  The cells: gen/rules.py FIT without its two 4096-wide cells (11) and the session's 13
decided rows of m, l and x.  Prints every cell with its layout, then the extents that fit (none, at the fold).  Run from the session
directory: python3 postrun/posthoc_rules.py > postrun/posthoc_rules.out
"""
import itertools
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import rules as R  # noqa: E402

rows = [((w, h, w, h), f, rec) for (w, h), f, rec in R.FIT_CLEAN]
SESSION = [((1024, 768, 2048, 2048), 0, "m0"), ((1280, 1024, 1280, 1040), 0, "m1"), ((1280, 1024, 2048, 2048), 0, "m2"),
           ((1280, 1024, 2048, 1024), 1, "m3"), ((2048, 1536, 4096, 4096), 0, "m4"), ((2048, 240, 2048, 240), 1, "l1"),
           ((256, 1536, 256, 1536), 0, "l2"), ((768, 2048, 768, 2048), 1, "l3"), ((1280, 768, 1280, 768), 1, "l4"),
           ((1024, 1024, 1024, 1024), 1, "l5"), ((1024, 512, 1024, 512), 0, "x1"), ((1184, 768, 1184, 768), 1, "x2"),
           ((1024, 800, 1024, 800), 1, "x3")]
rows += SESSION
print("%d cells (%d of record below 4096 wide, %d of this session)" % (len(rows), len(R.FIT_CLEAN), len(SESSION)))
for (w, h, mw, mh), f, rec in rows:
    t, m = R.lay(w, h), R.lay(mw, mh)
    print("%4d x %-4d on %4d x %-4d %-8s %-28s tiles %3d x %3d n %d mt %2d x %2d side %3d | max: tail 0x%05x state 0x%05x rgn 0x%05x" % (
        w, h, mw, mh, "fault" if f else "complete", rec, t["tx"], t["ty"], t["n"], t["mx"], t["my"], t["side"], m["ctl"], m["state"],
        m["rgn"]))


def spans(t):
    big = 2 * max(t["n"] * t["mx"], t["n"] * t["my"])
    return {"2tx": 2 * t["tx"], "2nmx": 2 * t["n"] * t["mx"], "2side": 2 * t["side"], "2span": big}, \
           {"2ty": 2 * t["ty"], "2nmy": 2 * t["n"] * t["my"], "2side": 2 * t["side"], "2span": big}


fits = 0
for a, b in itertools.product(["2tx", "2nmx", "2side", "2span"], ["2ty", "2nmy", "2side", "2span"]):
    for lim in ("ctl", "state", "rgn"):
        for k in (0.25, 0.5, 1, 2):
            ok = True
            for (w, h, mw, mh), f, _ in rows:
                across, down = spans(R.lay(w, h))
                if (4 * k * across[a] * down[b] > R.lay(mw, mh)[lim]) != bool(f):
                    ok = False
                    break
            if ok:
                fits += 1
                print("FITS: 4 * %s * %s * %s > %s" % (k, a, b, lim))
print("extents tried: %d; fitting: %d" % (4 * 4 * 3 * 4, fits))
