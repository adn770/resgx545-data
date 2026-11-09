#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 summary of the kept dumps (reads RUNDIR like the recompute; uses its decoders, the corrected copy):
one line a case: status, partial renders (0x0658 stretches), TA3DCtl dwords 35..40 after render 1 and the
last render, state lists, zero dwords, window, sign. Prints a TSV on stdout."""
import os, re, sys, gzip
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r


def main(run):
    cs = r.load_cases(run)
    print("case\tset\tP\tstatus\tpartials\tdw35-40_r1\tdw35-40_last\tstate_sum\tzero\twindow\tsigned\tnonzero")
    for n, c in cs.items():
        k = r.Case(n, c)
        st = r.job1_status(k.out)
        pt = r.partials(k.tl)
        w1 = k.ta3d(1)
        wl = None
        for i in range(8, 0, -1):
            wl = k.ta3d(i)
            if wl:
                break
        f = lambda w: " ".join("%x" % x for x in w[35:41]) if w else "-"
        ls = r.state_lists(k.dump("tadata", 1), r.state_off(c))
        ssum = sum(l[1] for l in ls[:16] if l) if any(ls) else "-"
        d = k.depth()
        df = r.depth_facts(c, d) if d else None
        print("\t".join(str(x) for x in [n, c["set"], c["P"], st, pt, f(w1), f(wl), ssum,
              df["zero"] if df else "-", df["window"] if df else "-", df["signed"] if df else "-", df["nonzero"] if df else "-"]))


main(sys.argv[1])
