#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r35-pk's post-hoc readings (not frozen), from the kept files of one attempt.

  python3 fold/posthoc.py out/ATT

1. r3's mode 4 rows: the stored alpha bit against the pixel's alpha (from r3-m00-ref): the
   largest alpha stored clear and the smallest stored set, and whether the rest of each half
   equals the 0x80 reference.
2. Modes 9, 10, 12, 13: where each stored dword's pixel is (the ramp's colours are unique), as
   (dword index or scratch offset) against (x, y); the stride, the rows and columns covered.
3. Every row equal between its two replicates (r1, r3, pw)."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-fA-F ]+)$", re.M)
SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+)$", re.M)
SENT = 0xDEADBEEF


def load(att, st, n):
    t = gzip.open(os.path.join(att, st, n + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()] for m in ROW.finditer(t)}
    return ([v for y in range(64) for v in rows[y]],
            {int(o, 16): int(v, 16) for o, v in SCR.findall(t)})


def mode4(att):
    ref0, _ = load(att, "r3", "r3-m00-ref")
    ref4, _ = load(att, "r3", "r3-m04-ref")
    print("1. r3 mode 4 (alpha bit against the pixel's alpha; low 15 bits against r3-m04-ref)")
    for n in ("w02000040-a", "w020000c0-a", "w02000040-b", "w020000c0-b"):
        img, _ = load(att, "r3", "r3-m04-" + n)
        clear, sets, low_ok = [], [], 0
        for i in range(4096):
            h = (img[i // 2] >> (16 * (i % 2))) & 0xFFFF
            r = (ref4[i // 2] >> (16 * (i % 2))) & 0xFFFF
            low_ok += (h & 0x7FFF) == (r & 0x7FFF)
            (sets if h >> 15 else clear).append(ref0[i] >> 24)
        same = img == ref4
        print(f"   r3-m04-{n}: clear alphas {min(clear)}..{max(clear)} ({len(clear)} px), set "
              f"{min(sets) if sets else '-'}..{max(sets) if sets else '-'} ({len(sets)} px); low "
              f"15 bits as the reference {low_ok}/4096; image = reference: {same}; tail "
              f"sentinel {all(v == SENT for v in img[2048:])}")
    r, _ = load(att, "r3", "r3-m04-ref")
    clear = [ref0[i] >> 24 for i in range(4096) if not (r[i // 2] >> (16 * (i % 2) + 15)) & 1]
    sets = [ref0[i] >> 24 for i in range(4096) if (r[i // 2] >> (16 * (i % 2) + 15)) & 1]
    print(f"   r3-m04-ref (0x80): clear {min(clear)}..{max(clear)}, set {min(sets)}..{max(sets)}")


def layout(att):
    ref0, _ = load(att, "r1", "r1-m00-ref")
    pos = {v: (i % 64, i // 64) for i, v in enumerate(ref0) if v != 0xFF203040}
    print("2. layout of modes 9, 10, 12, 13 (dword index -> pixel x, y of the colour it holds)")
    for st, n in (("r1", "r1-m09-a"), ("r1", "r1-m10-a"), ("pw", "pw-m12-a"), ("pw", "pw-m13-a")):
        img, scr = load(att, st, n)
        wr = [i for i, v in enumerate(img) if v != SENT]
        tri = [(i, pos[img[i]]) for i in wr if img[i] in pos]
        st_ = sorted({b - a for a, b in zip(wr, wr[1:])})[:3]
        print(f"   {n}: {len(wr)} dwords written, steps {st_}, {len(tri)} hold a triangle "
              f"colour; first {tri[:4]}; last {tri[-2:]}")
        if tri:
            fits = {}
            for name, f in (("i = y*64 + x", lambda x, y: y * 64 + x),
                            ("i = (y//4)*64 + x (rows 4n)", lambda x, y: (y // 4) * 64 + x),
                            ("i = (y//2)*64 + x", lambda x, y: (y // 2) * 64 + x),
                            ("i = y*64 + 2x", lambda x, y: y * 64 + 2 * x),
                            ("i = y*64 + 4x", lambda x, y: y * 64 + 4 * x)):
                fits[name] = sum(f(x, y) == i for i, (x, y) in tri)
            print(f"      maps: {fits}")
            ys = sorted({y for _, (x, y) in tri})
            print(f"      pixel rows stored in the target: {ys[:8]}...{ys[-4:]} ({len(ys)})")
        if scr:
            offs = sorted(scr)
            stp = sorted({b - a for a, b in zip(offs, offs[1:])})[:3]
            stri = [(o, pos[v]) for o, v in sorted(scr.items()) if v in pos]
            print(f"      scratch: {len(scr)} dwords, offsets 0x{offs[0]:x}..0x{offs[-1]:x}, "
                  f"steps {stp}, {len(stri)} triangle colours; first {stri[:3]}")
            ys = sorted({y for _, (x, y) in stri})
            print(f"      pixel rows in the scratch: {ys[:4]}...{ys[-4:]} ({len(ys)})")


def replicates(att):
    print("3. replicates (a against b), dword for dword")
    for st in ("r1", "r3", "pw"):
        d = os.path.join(att, st)
        for f in sorted(os.listdir(d)):
            if f.endswith("-a.txt.gz"):
                n = f[:-len(".txt.gz")]
                a = load(att, st, n)
                b = load(att, st, n[:-1] + "b")
                print(f"   {n[:-2]}: {'equal' if a == b else 'differ'}")


if __name__ == "__main__":
    att = sys.argv[1]
    mode4(att)
    layout(att)
    replicates(att)
