# SPDX-License-Identifier: MIT
"""o4model.py: the frozen model family of stage p4-o4 (Q276, the o4 clause), shared by the generator (it writes the frozen
predictions) and the tests.  The scorer reads the predictions from predictions/p4-o4.tsv, not from here.

What is modelled (plan section 3.4, closing4/pixel/exp-pixel-r4.md 0.5): the o4 words that land in a triangle's pixel program
when it writes o4 once or twice.  E808: with the tag-5' write (tag 13, bit 3 set) first and tag 5 last, and with 5 first and 5'
last, every o4 word read was tag 5 (16 jobs), so "the last write wins" and "the first write wins" are each contradicted.
A write is the low six bits of the word: bit 5 and bit 4 are variant bits, bits 3:0 the tag.
  A = 5 (tag 5), A4 = 5 | 0x10, A5 = 5 | 0x20, A3 = 13 (tag 5', bit 3).
Model = (B, R): B the single-write path, R the rule that combines the writes that executed, in program order.
  B  V1 drops bit 3 of the word (13 lands as 5);  V2 a word with bit 3 set does not land;  V3 the word as written.
  R  last, first, and (bitwise AND), or (bitwise OR), min.
Only the 12 models that reproduce E808 are kept: V1 and V2 with the five rules, V3 with `and` and `min` (V3 with last, first
or or reads 13 in one of E808's orders).  [infer] The family is a reading of E808, not a result.
Predicate rows (p1 A / !p1 A4, and the swapped order): the o4 words that land come from the instance whose lane is 0 (every
pair source in 571 of 571 pairs was (even x, even y), E808, G-o4), so p1 = (0 == k).  Gating `gated`: only the write whose
predicate holds executes; `ignored`: both execute in program order.  Labels: A, A4, A5, A3, none, other:XX.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

A, A3, A4, A5 = 0x05, 0x0D, 0x15, 0x25
LABELS = {A: "A", A3: "A3", A4: "A4", A5: "A5"}
RULES = ("last", "first", "and", "or", "min")
BITS = ("V1", "V2", "V3")


def label(w6):
    if w6 is None:
        return "none"
    return LABELS.get(w6, f"other:{w6:02x}")


def single(b, w):
    """The word after the single-write path, or None (does not land)."""
    if b == "V1":
        return w & ~0x08
    if b == "V2":
        return None if w & 0x08 else w
    return w


def combine(rule, ws):
    if not ws:
        return None
    if rule == "last":
        return ws[-1]
    if rule == "first":
        return ws[0]
    if rule == "min":
        return min(ws)
    out = ws[0]
    for w in ws[1:]:
        out = out & w if rule == "and" else out | w
    return out


def lands(b, rule, writes):
    """Label of what lands when `writes` (words, program order) all execute."""
    ws = [x for x in (single(b, w) for w in writes) if x is not None]
    return label(combine(rule, ws))


def models():
    ms = [(b, r) for b in ("V1", "V2") for r in RULES] + [("V3", "and"), ("V3", "min")]
    return [m for m in ms if fits_e808(*m)]


def fits_e808(b, rule):
    """E808: both orders of (5', 5) read tag 5 = A."""
    return lands(b, rule, [A3, A]) == "A" and lands(b, rule, [A, A3]) == "A"


def name(m):
    return f"{m[0]}/{m[1]}"


# value configurations: name -> writes in program order
VALUE = {"a3": [A3], "a4": [A4], "a-a4": [A, A4], "a4-a": [A4, A], "a-a5": [A, A5], "a5-a": [A5, A], "a3-a4": [A3, A4]}
# predicate configurations: order 'pa' = (p1 A, !p1 A4), 'ps' = swapped; k = 0, 3, 7
PRED_K = (0, 3, 7)
PRED_ORDERS = {"pa": [("p1", A), ("!p1", A4)], "ps": [("!p1", A4), ("p1", A)]}


def pred_name(order, k):
    return f"{order}-k{k}"


def pred_lands(m, gating, order, k):
    p1 = (k == 0)                      # the landing instance has lane 0
    ws = PRED_ORDERS[order]
    if gating == "gated":
        ws = [w for p, w in ws if (p == "p1") == p1]
    else:
        ws = [w for p, w in ws]
    return lands(m[0], m[1], ws)


def value_pred(m, cfg):
    return lands(m[0], m[1], VALUE[cfg])
