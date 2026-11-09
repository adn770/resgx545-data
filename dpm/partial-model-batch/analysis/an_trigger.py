#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 trigger model against every kept job of the single-triangle scene at 1024x768 and 4096x4096.
Model T (first abort at page status P - 0x22 = thr0; threshold raised by 0x20 at the first partial render;
U_b = the scene's whole-buffer page count (19 at 1024x768, 287 at 4096x4096): overflow iff thr0 < U_b;
partial renders = 1 + floor((U_b + 2 - thr0) / (thr0 + 0x1f)); last abort status thr0 if one, else thr0 + 0x20;
TA3DCtl dword 35 = last abort status - 2). Prints observed against model and the tally. Declared as an assumption
set, not a prediction file: the frozen R1 used U = 289 for counts and 21 at 1024x768 for the boundary."""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r

UB = {1024: 19, 4096: 287}
rows, hit = [], 0
cs = r.load_cases(sys.argv[1])
print("case\tP\tobs_status\tmodel_status\tobs_partials\tmodel_partials\tobs_dw35\tmodel_dw35\tmatch")
n = ok = 0
for name, c in cs.items():
    if not re.match(r"(tg-(1024|4096)-(bd|n)|tg-4096-poke|fr-(1024|4096)-0x|st-4096|fa-)", name):
        continue
    w = int(r.arg(c, "--width", 4096 if "4096" in name else 1024))
    P = int(c["P"], 0)
    pk = re.search(r"--kpoke-render 1:pb:11=(0x[0-9a-f]+)", c["args"])
    k = r.Case(name, c)
    st = r.job1_status(k.out)
    thr0 = int(pk.group(1), 0) if pk else P - 0x22
    u = UB[1024 if w < 2048 else 4096]
    mst = "overflow" if thr0 < u else "ok"
    mp = 1 + (u + 2 - thr0) // (thr0 + 0x1f) if mst == "overflow" else 0
    md = (thr0 - 2 if mp == 1 else thr0 + 0x20 - 2) if mp else 0
    op = r.partials(k.tl)
    w35 = k.ta3d(1)
    od = w35[35] if w35 else None
    md &= 0xffffffff if md >= 0 else 0xffff
    if thr0 == 1 and mp:
        md = 0xffff if mp == 1 else 0x1f
    m = (st == mst) and (op is None or op == mp) and (od is None or od == md)
    n += 1
    ok += m
    print(f"{name}\t{P:#x}\t{st}\t{mst}\t{op}\t{mp}\t{od if od is None else hex(od)}\t{md:#x}\t{'yes' if m else 'NO'}")
print(f"\nmodel T: {ok} of {n} jobs match (status, partial count where a timeline was kept, dword 35)")
