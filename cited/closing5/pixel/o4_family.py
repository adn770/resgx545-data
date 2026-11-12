# SPDX-License-Identifier: MIT
"""Round 5 planning, offline (2026-11-12; a declared family checked against kept data: post hoc, not a result).
Q276: which bitwise combinations of one instance's output words reproduce the tag-5 word in EVERY kept
configuration of R3 p-c3 (E808) and R4 p4-o4 (E838).  Family, declared here before the check: op in
{OR, AND, XOR} over a non-empty subset S of o0..o7 (255 x 3 = 765 models, single outputs included once),
plus MUX(i, j): bits 2:0 and the marker of o_i with bits 5:3 of o_j (64 models).  Word = low 6 bits
(marker bits are common to every output of a job, so a model must keep them: XOR needs |S| odd).
  python -I o4_family.py > o4_family.out"""
import functools
import itertools
import re

TAG = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8}
# kept configurations: (name, {output: low-6 word} overrides, marker bits kept in the low 6, expected low 6 at the tag-5 pixels)
CFG = [
    ("R4 c-u / v rows base (o4 = A)", {}, 0, 0x05),
    ("R4 v-a3 (o4 = 13 alone)", {4: 13}, 0, 0x05),
    ("R4 v-a4 (o4 = 5 | bit 4 alone)", {4: 0x15}, 0, 0x05),
    ("R4 last write A5 (v-a-a5: o4 = 5 | bit 5 if the last write lands)", {4: 0x25}, 0, 0x05),
    ("R4 c-e709-x (every word 0xcf0 | tag: bits 5:4 set in all)", {}, 0x30, 0x35),
    ("R3 marker with bits 5:4 = 3, o4 = 13 last (o4s-u)", {4: 13}, 0x30, 0x35),
    ("R3 k5 / k7 (o1 = 12 at every instance)", {1: 12}, 0x10, 0x15),
    ("R3 k3 (o1 = 12 at lane 0, the source lane)", {1: 12}, 0x30, 0x35),
]
OPS = {"OR": lambda a, b: a | b, "AND": lambda a, b: a & b, "XOR": lambda a, b: a ^ b}


def words(over, mk):
    return {j: (over.get(j, TAG[j]) | mk) for j in range(8)}


surv = []
for op, f in OPS.items():
    for n in range(1, 9):
        for S in itertools.combinations(range(8), n):
            if n == 1 and op != "OR":
                continue
            if op == "XOR" and n % 2 == 0:
                continue
            if all(functools.reduce(f, [words(o, mk)[j] for j in S]) == exp for _, o, mk, exp in CFG):
                surv.append(f"{op}({', '.join('o%d' % j for j in S)})")
for i in range(8):
    for j in range(8):
        if i == j:
            continue
        ok = True
        for _, o, mk, exp in CFG:
            w = words(o, mk)
            if (w[i] & 7) | (w[j] & 0x38) != exp:
                ok = False
        if ok:
            surv.append(f"MUX(bits 2:0 of o{i}, bits 5:3 of o{j})")
print(f"{len(surv)} of 765 + 56 models reproduce the tag-5 word in all {len(CFG)} kept configurations:")
for s in surv:
    print("  ", s)

# what a walk row would read for each survivor: only o_j carries bit 4, every output but o_j carries bit 5
print("\nround 5 walk rows (w-j: bit 4 at o_j only, bit 5 at every output but o_j; tags unchanged): bits 5:4 predicted at the tag-5 words")
print("model".ljust(44), " ".join(f"w-{j}" for j in range(8)))


def walk(model, j):
    w = {i: TAG[i] | (0x10 if i == j else 0x20) for i in range(8)}
    if model.startswith("MUX"):
        a, b = (int(x) for x in re.findall(r"o(\d)", model))
        return ((w[a] & 7) | (w[b] & 0x38)) >> 4
    op = model[:model.index("(")]
    S = [int(x[1]) for x in model[model.index("(") + 1:-1].split(", ")]
    return functools.reduce(OPS[op], [w[i] for i in S]) >> 4


sig = {}
for s in surv:
    v = tuple(walk(s, j) for j in range(8))
    sig.setdefault(v, []).append(s)
    print(s.ljust(44), "   ".join(str(x) for x in v))
print(f"\n{len(sig)} distinct walk signatures among {len(surv)} survivors; models that share one:")
for v, ss in sig.items():
    if len(ss) > 1:
        print("  ", v, ss)
