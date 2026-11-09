#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39: the threshold raise (TA3DCtl dwords 37 = 1 << 16 | P - 0x22 and 38 = 0x20 after the first abort) against the
rule 'raised iff 2 * thr0 < U + 2' (thr0 = P - 0x22 or the poked descriptor dword 11, U the whole-buffer page need
of the scene: 19 at 1024x768, 287 at 4096x4096, the default triangle), over every overflowed job of that scene;
and the sign of the stored depth against the raise (the dp-*, w4096-* jobs)."""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r

cs = r.load_cases(sys.argv[1])
U = {1024: 19, 4096: 287}
n = ok = 0
print("case\tthr0\tU\trule_raise\tdw37\tdw38\tobs_raise\tsigned\tmatch")
for name, c in cs.items():
    if not re.match(r"(tg-(1024|4096)-(bd|n)|tg-4096-poke|fr-(1024|4096)-0x|st-mv0_0|st-sweep|st-repeat|st-4096|dp-z05-g1|fa-)", name):
        continue
    k = r.Case(name, c)
    if r.job1_status(k.out) != "overflow":
        continue
    w = int(r.arg(c, "--width", 1024))
    P = int(c["P"], 0)
    pk = re.search(r"--kpoke-render 1:pb:11=(0x[0-9a-f]+)", c["args"])
    thr0 = int(pk.group(1), 0) if pk else P - 0x22
    u = U[1024 if w < 2048 else 4096]
    rule = 2 * thr0 < u + 2
    w1 = k.ta3d(1)
    obs = w1[38] == 0x20
    d = k.depth()
    sg = r.depth_facts(c, d)["signed"] > 0 if d and "dp-z05" in name else "-"
    n += 1
    ok += rule == obs
    print(f"{name}\t{thr0}\t{u}\t{rule}\t{w1[37]:#x}\t{w1[38]:#x}\t{obs}\t{sg}\t{'yes' if rule == obs else 'NO'}")
print(f"\nrule 2*thr0 < U+2: {ok} of {n} overflowed jobs of the default triangle match dword 38 = 0x20")
