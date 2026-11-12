# SPDX-License-Identifier: MIT
"""o5model.py: the frozen model family of stage p5-o4 (Q276: what the tag-5 word is), shared by the generator (it writes the frozen
predictions), the scorer's tests and the mock world.  The scorer reads the predictions from predictions/p5-o4.tsv, not from here.

Plan: closing5/pixel/exp-pixel-r5.md sections 1.2 and 2 (decision R5-3 a, pixel D2 a).  Of 821 declared bitwise models (OR, AND, XOR
over a subset of one instance's o0 to o7, and MUX(i; j) = bits 2:0 of o_i with bits 5:3 of o_j), nine reproduce the tag-5 word in all
eight kept configurations of E808 (R3 p-c3) and E838 (R4 p4-o4) (closing5/pixel/o4_family.py, o4_family.out) [infer: a declared family
checked against kept data, post hoc].  A word is the low 16 bits of an output: marker << 6 | variant bits (5:4) << 4 | tag (3:0); the
marker is common to every output of a job, so every model keeps it (XOR has an odd count).
Labels of what a configuration reads at the tag-5 positions: "5:B" (tag 5, bits 5:4 = B), "4:B" (tag 4), "d1" (the word is tag 1: it
lands off its own pixel as a displaced tag-1 word), "none" (no word), "other:T.B"; "nofrozen" = the model gives no word there
("none frozen" in the plan: cannot tell by design for that model)."""
from __future__ import annotations

import functools
import sys

sys.dont_write_bytecode = True

TAG = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8}
MODELS = ["OR(o0,o3)", "AND(o4,o6)", "XOR(o0,o2,o6)", "XOR(o3,o5,o6)",
          "MUX(o4;o0)", "MUX(o4;o2)", "MUX(o4;o3)", "MUX(o4;o5)", "MUX(o4;o6)"]
READS_O4 = [m for m in MODELS if "o4" in m]                                  # AND(o4,o6) and the five MUX
READS_O3 = ["OR(o0,o3)", "XOR(o3,o5,o6)", "MUX(o4;o3)"]                      # plan 2.2: the P3 gate
OPS = {"OR": lambda a, b: a | b, "AND": lambda a, b: a & b, "XOR": lambda a, b: a ^ b}


def parse(model):
    """('MUX', [i, j]) or (op, [outputs])."""
    op, rest = model.split("(", 1)
    return op, [int(t.strip()[1:]) for t in rest.rstrip(")").replace(";", ",").split(",")]


def combine(model, words):
    """The tag-5 word of a model from one instance's output words (low 16 bits, {j: word or None}); None if an output it reads was
    not written."""
    op, outs = parse(model)
    if any(words.get(j) is None for j in outs):
        return None
    if op == "MUX":
        i, j = outs
        return (words[i] & ~0x38 & 0xffff) | (words[j] & 0x38)
    return functools.reduce(OPS[op], [words[j] for j in outs])


def label(w):
    if w is None:
        return "nofrozen"
    tag, v = w & 15, (w >> 4) & 3
    if tag == 5:
        return f"5:{v}"
    if tag == 4:
        return f"4:{v}"
    if tag == 1:
        return "d1"
    return f"other:{tag}.{v}"


# ---------------------------------------------------------------- configurations: the low 6 bits of each output's final word
def base():
    return dict(TAG)


def walk(j):
    """w-j: o_j's word carries bit 4, every other output's word carries bit 5, tags unchanged."""
    return {i: TAG[i] | (0x10 if i == j else 0x20) for i in range(8)}


def all4():
    return {i: TAG[i] | 0x10 for i in range(8)}


INDEP = {"z-o3": {3: 0}, "l-o4": {4: 4}, "l-o6": {6: 3}, "n-o4": {4: None}}
PRED_K = (0, 3, 7)
ORDERS = ("pa", "ps")                     # pa: the p1 write first, then the !p1 write; ps: swapped
# predicate sets: output, the p1 word, the !p1 word (low 6 bits)
PSETS = {"p4": (4, 0x05, 0x04), "p3": (3, 0x04, 0x14)}


def indep(name):
    w = base()
    w.update(INDEP[name])
    return w


def pred_words(pset, order, k, gating):
    """The final words of the landing instance (lane 0: every pair source is (even, even), E808, o4_offline.out D): gated = only the
    write whose predicate holds runs (p1 = lane == k), ignored = both run in program order and the last stays."""
    j, wp1, wnp1 = PSETS[pset]
    seq = [("p1", wp1), ("!p1", wnp1)] if order == "pa" else [("!p1", wnp1), ("p1", wp1)]
    p1 = (k == 0)
    if gating == "gated":
        seq = [(p, w) for p, w in seq if (p == "p1") == p1]
    w = base()
    w[j] = seq[-1][1]
    return w


def predict(model, words6, marker=0):
    """Label of the tag-5 word under `model` for low-6 words (the marker added, so the test of a kept marker is real)."""
    ws = {j: (None if v is None else (marker << 6) | v) for j, v in words6.items()}
    return label(combine(model, ws))


def walk_vector(model):
    return tuple(predict(model, walk(j)) for j in range(8))


if __name__ == "__main__":
    for m in MODELS:
        print(m.ljust(16), " ".join(walk_vector(m)), "|", " ".join(predict(m, indep(n)) for n in INDEP))
