#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r35-sa's post hoc readings (formed after the run, frozen nowhere: they decide
nothing). Reads the kept texts through the session's own scorer (score/score.py's pixel decode,
which c0 and c1 passed) and prints, for stage a, every writer's odd pixels as (x, y) with the
pattern they follow, and for stage t every U row's values with counts and positions.

  python3 fold/posthoc.py out/ATTEMPT"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "kit")]
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402


def xy(i):
    return (i % 64, i // 64)


def guess(n):
    """The post hoc pattern: sa_n's base pixel x = (n & 1) + 2 (n >> 2), y = (n >> 1) & 1, and
    copies at x + 16 and y + 8."""
    x, y = (n & 1) + 2 * (n >> 2), (n >> 1) & 1
    return sorted(xx + yy * 64 for xx in (x, x + 16) for yy in (y, y + 8))


def stage_a(d):
    tab = K.table(KP, "a")
    cases = K.rows(d, "cases.tsv")
    fits = 0
    total = 0
    for r in tab:
        if r["set"] not in ("fit", "heldout") or not r["name"].endswith("-w"):
            continue
        w = score.read_writer(r, cases, d)
        for n, pos in sorted(w["pos"].items()):
            ok = list(pos) == guess(n)
            fits += ok
            total += 1
            print(f"a {r['name']}: sa{n} 0x{w['ms'][n]:08x} at {[xy(i) for i in pos]}: "
                  f"POST HOC pattern {'fits' if ok else 'DOES NOT fit'}")
    print(f"a: POST HOC pattern (x, y) = ((n & 1) + 2 (n >> 2) + {{0, 16}}, ((n >> 1) & 1) + "
          f"{{0, 8}}) fits {fits} of {total} sa positions sets")


def stage_t(d):
    tab = K.table(KP, "t")
    cases = K.rows(d, "cases.tsv")
    for r in tab:
        if not r["name"].endswith("-u"):
            continue
        t = score.ok_text(r, cases, d)
        px = score.pixels(t) if t else None
        if px is None:
            print(f"t {r['name']}: no pixels")
            continue
        ms = score.multiset(px)
        parts = []
        for v, c in sorted(ms.items(), key=lambda kv: -kv[1]):
            pos = [xy(i) for i, p in enumerate(px) if p == v]
            parts.append(f"0x{v:08x} x{c}" + (f" at {pos}" if c <= 32 else ""))
        print(f"t {r['name']}: " + "; ".join(parts))


if __name__ == "__main__":
    root = sys.argv[1]
    stage_a(os.path.join(root, "a"))
    stage_t(os.path.join(root, "t"))
