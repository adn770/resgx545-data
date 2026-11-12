#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""r7-faults, post hoc (written at the fold, 2026-11-12, after the scoring; not frozen): every
boot after a 0x90004 fault in stages d and m, by page and by size, and the registers read at
the hold (snap 1, NAME.regs) against the held reset's boot.

    posthoc.py OUT_ATTEMPT        e.g. out/20261112-222800; prints the tables (posthoc.out)

Standard library only. A boot is the kernel's 'SGX boot: kicking the EDM' followed by 'EDM up
after' (U) or 'no INIT_COMPLETE' (T); it is paired with the last 'BIF fault' line before it in
the row's kept slice (NAME.row.dmesg.gz); the dump after a T boot gives reg 0x008, 0xc04, 0xc08.
"""
import collections
import gzip
import pathlib
import re
import sys

CELLS = {"d": ["d0-640x480", "d1-288x144", "d2-320x400", "d3-256x288", "d4-128x528",
               "d5-384x384", "d6-320x400"],
         "m": ["m0a-none", "m1a-clr", "m2a-long", "m2b-long", "m1b-clr", "m0b-none"]}


def boots(path):
    """[(fault word, fault address, 'T' or 'U', dump)] of the row's slice, in order."""
    out, fault, cur = [], None, None
    for line in gzip.open(path, "rt"):
        m = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", line)
        if m:
            fault = (m.group(1), m.group(2))
        if "kicking the EDM" in line:
            cur = [fault, None, {}]
            fault = None
        elif cur and cur[1] is None and "EDM up after" in line:
            cur[1] = "U"
            out.append(cur)
            cur = None
        elif cur and cur[1] is None and "no INIT_COMPLETE" in line:
            cur[1] = "T"
            out.append(cur)
        elif cur and cur[1] == "T":
            m = re.search(r"reg 0x(008|c04|c08) = (0x[0-9a-f]+)", line)
            if m:
                cur[2][m.group(1)] = m.group(2)
            if "recovery failed" in line:
                cur = None
    return [(b[0], b[1], b[2]) for b in out]


def regs(path):
    r = {}
    for line in gzip.open(path, "rt"):
        m = re.match(r"reg (0x[0-9a-f]+) (\S+)", line)
        if m:
            r[m.group(1)] = m.group(2)
    return r


def main():
    att = pathlib.Path(sys.argv[1])
    by_page, by_size = collections.Counter(), collections.Counter()
    held = {}
    print("== boots after a 0x90004 fault (row slice order: the held reset first, then the steps)")
    for st, cells in CELLS.items():
        for c in cells:
            size = c.split("-")[1] if c[0] == "d" else "288x144"
            seq = [b for b in boots(att / st / f"{c}.row.dmesg.gz") if b[0] and b[0][0] == "0x90004"]
            for k, (f, r, dump) in enumerate(seq):
                page = f[1][:7]
                by_page[page, r] += 1
                by_size[size, r] += 1
                if k == 0:
                    held[c] = r
                d = " ".join(f"{a}={v}" for a, v in sorted(dump.items()))
                print(f"{st} {c:12} {'held' if k == 0 else 'step':4} {f[1]} {r} {d}")
    print("== by page: timed out / boots")
    for p in sorted({p for p, _ in by_page}):
        print(f"{p} {by_page[p, 'T']} / {by_page[p, 'T'] + by_page[p, 'U']}")
    print("== by size: timed out / boots")
    for s in sorted({s for s, _ in by_size}):
        print(f"{s} {by_size[s, 'T']} / {by_size[s, 'T'] + by_size[s, 'U']}")
    print("== at the hold (snap 1): 0x0284 CR_TE_DIAG2, 0x0290 CR_TE_DIAG5, 0x0724, the held reset's boot")
    snaps = {}
    for st, cells in CELLS.items():
        for c in cells:
            snaps[c] = regs(att / st / f"{c}.regs.gz")
            s = snaps[c]
            print(f"{c:12} {s.get('0x0284')} {s.get('0x0290')} {s.get('0x0724')} {held[c]}")
    print("== registers of snap 1 whose values split the held boots T from U (none shared)")
    keys = sorted(set().union(*snaps.values()))
    for k in keys:
        t = {snaps[c].get(k) for c in snaps if held[c] == "T"}
        u = {snaps[c].get(k) for c in snaps if held[c] == "U"}
        if not t & u:
            every = len(t | u) == len(snaps)
            print(f"{k} {'(a different value in every dump)' if every else ''} T {sorted(t)} U {sorted(u)}")


if __name__ == "__main__":
    main()
