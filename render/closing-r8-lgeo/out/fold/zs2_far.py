#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/zs2_far.py (added at the fold, 2026-11-13; POST HOC, read after zs2_read.py): for each zs2
sweep, whether a vertex of the HA-rounded triangle lies past the target's far edge (x > W or y > H)
or before its near edge (x < 0 or y < 0), against the rows that miss HA's image and the aimed
pixel's distance from its edge. Reads the kept files through the frozen scorer's readers.
  python3 out/fold/zs2_far.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "score"))
import score as S  # noqa: E402
Z, K = S.Z, S.K


def main(att):
    d = os.path.join(att, "zs2")
    P, cases = K.predictions(KP, "zs2"), K.rows(d)
    sweeps = {}
    for t in K.table(KP, "zs2"):
        n = t["name"]
        if t["set"] == "control":
            continue
        w, h, v = S.zs_args(t)
        img = S.tri_image(K.text(d, n + ".txt"), w, h)
        sp = Z.spans_parse(open(os.path.join(KP, "predictions/zs2/%s.HA.spans" % n)).read(), h)
        r = [Z.rnd(x, "HA") / 256.0 for x in v]
        far = any(r[i] > (w if i % 2 == 0 else h) for i in range(6))
        sw = P[n]["sweep"]["all"]
        s = sweeps.setdefault(sw, dict(far=far, wh="%dx%d" % (w, h), off=[], le=float(P[n]["longest_edge"]["H-HA"])))
        s["off"].append(len(S.off_pixels(img, sp)))
    tab = {}
    for sw, s in sweeps.items():
        miss = any(s["off"])
        tab.setdefault((s["far"], miss), []).append(sw)
        print("%-22s %s far vertex %-5s longest %4.0f px  off HA per step %s" % (sw, s["wh"], s["far"], s["le"], s["off"]))
    for (far, miss), sws in sorted(tab.items()):
        print("far vertex %-5s misses %-5s: %d sweeps" % (far, miss, len(sws)))


if __name__ == "__main__":
    main(sys.argv[1])
