#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r34-sa0's readers read POST HOC (labelled so; not the frozen scorer).

  python3 fold/posthoc.py out/ATT/s

Every reader's pixels came in pairs {x, x ^ key} (key K2 for sa0, K4 for pa0), about 1904 and 144
of 2048: the frozen decode (every pixel = the value read ^ key) does not hold. Post hoc model
[infer]: what a reader reads aliases what other instances of the same job already wrote to o0,
so instances that read first output v ^ key, later ones read that back and output v. The value
read before the job's own writes, v, is then the more frequent member of each pair. Prints per
reader: the pixel pairs, dword 0, v, and v against its group's marker M and the job before's
output (its own kept o0 line, the t10 fill's colour, the t10 tri's two colours)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score as S  # noqa: E402


def pairs(ms, key):
    out, seen = [], set()
    for x in sorted(ms, key=lambda v: -ms[v]):
        if x in seen:
            continue
        y = x ^ key
        seen |= {x, y}
        out.append((x, ms[x], ms.get(y, 0)))
    return out


def main(d):
    tab = K.table(KP, "s")
    preds = K.predictions(KP, "s")
    cases = K.rows(d, "cases.tsv")
    marker = {r["name"].split("-")[0]: int(preds[r["name"]]["sa"]["H-REF"], 16)
              for r in tab if r["name"].endswith("-w")}
    vread = {}
    for i, r in enumerate(tab):
        n = r["name"]
        if r["set"] not in ("heldout", "fit"):
            continue
        t = K.text(d, n + ".txt")
        ms, oth = S.o0_multiset(t)
        key = S.K2 if "/bins/r.bin" in r["args"] else S.K4
        dw = re.search(r"scratch \+0x000 (0x[0-9a-f]{8})", t)
        ps = pairs(ms, key)
        v = {x for x, a, b in ps}
        vread[n] = v
        prevrow = tab[i - 1]
        prev = S.job_output(prevrow, cases, d)
        if prev and prev[0] == "tri":
            pset, ptop = set(S.TRI), None
        elif prev and prevrow["name"] in vread and "/bins/r.bin" in prevrow["args"]:
            pset = set(prev[1])
        else:
            pset = set(prev[1]) if prev else set()
        m = marker.get(n.split("-")[0])
        lab = ("M" if m is not None and v == {m} else
               "PREV" if v and v <= pset else
               "other")
        print(f"{n}: pairs " + ", ".join("0x%08x x%d / ^key x%d" % p for p in ps)
              + f"; dword 0 {dw.group(1) if dw else '-'}; v = "
              + ",".join("0x%08x" % x for x in sorted(v))
              + f"; job before {prevrow['name']}: "
              + (",".join("0x%08x" % x for x in sorted(pset)) or "none")
              + f": POST HOC {lab}")


if __name__ == "__main__":
    main(sys.argv[1])
