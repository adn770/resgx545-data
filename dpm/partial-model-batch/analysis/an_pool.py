#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39: the free-list walk after every render of the fr-* jobs (corrected decoder), the pages whose content
changed between consecutive dumps, and whether those are the head prefix of the previous walk (H-head)."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r


def runs(seq):
    out, s = [], seq[0]
    for a, b in zip(seq, seq[1:] + [None]):
        if b != a + 1:
            out.append(f"{s:#x}" if s == a else f"{s:#x}-{a:#x}")
            s = b
    return ",".join(out)


def main(run, prefix):
    cs = r.load_cases(run)
    for n, c in cs.items():
        if not n.startswith(prefix):
            continue
        k = r.Case(n, c)
        prev = None
        line = []
        for i in (1, 2, 3):
            d = k.dump("param", i)
            if not d:
                break
            seq, ok = r.walk(d)
            ch = []
            if prev is not None:
                ch = [p for p in range(1, 0x423) if prev[(p - 1) * 4096:p * 4096] != d[(p - 1) * 4096:p * 4096]]
            hp = "-"
            if prev is not None and pseq:
                hp = "head" if sorted(ch) == sorted(pseq[:len(ch)]) else "NOT"
            line.append(f"r{i}: walk {len(seq)} ok={ok} head={seq[0]:#x} tail={seq[-1]:#x} prev_tail={seq[-2]:#x}"
                        + (f" changed {len(ch)} ({hp})" if prev is not None else ""))
            prev, pseq = d, seq
        print(n, c["P"], "|", " | ".join(line))


main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "fr-")
