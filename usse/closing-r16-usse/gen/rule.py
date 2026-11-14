# SPDX-License-Identifier: MIT
"""rule.py: the frozen hypotheses of r16-usse as code.

Class 9 test field (Q137). A test word's enc[43:36] is the field enc[43:40] (taz 1, tanz 2, nat 4,
pat 8), the join enc[39] (1 `a`, 0 `o`) and the chan field enc[38:36] (chan0-chan3, andall, orall,
and02, or02). H-RULE is the rule sgx-sim gives (crates/sgx-sim/src/usse.rs at the pinned commit:
canonical_test_word, predicate, test_one; E499's a join, E529's o join, E530 and the Test
channels page's channels): the zero part is tanz if bit 41, else taz if bit 40, else true; the
sign part is pat if bit 43, else nat if bit 42, else true (`p` reads a zero result as positive);
the parts ANDed (`a`) or ORed (`o`) on each channel the chan field names, a channel with no lane
read as a positive nonzero value, the channels ANDed (chan0-3, andall, and02) or ORed (orall,
or02). The sim refuses what was not run (the raw fields of shifts and sums, the o join outside
and/or/xor, the write mask on a test): there the rule is the sim's rule carried over, which is
what these rows test. Rivals (each can be told from H-RULE on the rows that carry it):
  H-SETAND  the AND of every condition whose bit is set (field 0 true): E499's rival (69 of 90)
  H-AJOIN   the join bit ignored, every word the a join (o rows only)
  H-ORFALSE the o join with an absent part false (E529's first prediction, 75 of 90; o rows)
  H-SETOR   the OR of every condition whose bit is set (field 0 false; o rows; E529's rival)
  H-CHAN0   the chan field ignored, every word tests chan0 (lane rows)

iaddu32's value (Q126): H-ZX (E521) writes (src1 & 0xffff) + src2 mod 2^32, H-SX
sext16(src1) + src2; with a write mask (the repeat of the other forms, sgx-sim's "component k
writes d + k from sources advanced by k, immediates stay"): H-ZX-ADV, against H-NOREP (only d)
and H-NOADV (every component d's value)."""
M = 0xFFFFFFFF
CHANS = {0: ((0,), True), 1: ((1,), True), 2: ((2,), True), 3: ((3,), True),
         4: ((0, 1, 2, 3), True), 5: ((0, 1, 2, 3), False), 6: ((0, 2), True), 7: ((0, 2), False)}
CHAN_NAME = ("chan0", "chan1", "chan2", "chan3", "andall", "orall", "and02", "or02")


def parts(field):
    """(sign, zero) of a field: each 't', 'n'/'p' or 'z'/'nz' (the canonical reading)."""
    zero = "nz" if field & 2 else "z" if field & 1 else "t"
    sign = "p" if field & 8 else "n" if field & 4 else "t"
    return sign, zero


def text_name(field, join):
    """The assembler's test name for a field it can write (neither part both bits), else None."""
    if field & 0xC == 0xC or field & 3 == 3:
        return None
    sign, zero = parts(field)
    return f"test{sign}{join}{zero}"


def sign_ok(sign, v):
    return True if sign == "t" else v < 0 if sign == "n" else v >= 0


def zero_ok(zero, v):
    return True if zero == "t" else v == 0 if zero == "z" else v != 0


def channel(field, join, v, model="H-RULE"):
    """One channel's test of a value class v (-1, 0, 1) under a model."""
    if model == "H-SETAND" or model == "H-SETOR":
        conds = [v == 0 for b in (1,) if field & b] + [v != 0 for b in (2,) if field & b] + \
                [v < 0 for b in (4,) if field & b] + [v >= 0 for b in (8,) if field & b]
        if model == "H-SETAND":
            return all(conds)
        return any(conds)
    if model == "H-AJOIN":
        join = "a"
    sign, zero = parts(field)
    if model == "H-ORFALSE" and join == "o":
        s = sign != "t" and sign_ok(sign, v)
        z = zero != "t" and zero_ok(zero, v)
        return s or z
    s, z = sign_ok(sign, v), zero_ok(zero, v)
    return (s and z) if join == "a" else (s or z)


def predicate(field, join, chan, classes, model="H-RULE"):
    """p0 of a test word: classes are the four channels' value classes (a channel with no lane
    is 1, a positive nonzero value)."""
    if model == "H-CHAN0":
        chan, model = 0, "H-RULE"
    chans, every = CHANS[chan]
    vals = [channel(field, join, classes[c], model) for c in chans]
    return all(vals) if every else any(vals)


def word(base, field, join, chan):
    """A test word with enc[43:36] replaced."""
    t = field << 4 | (8 if join == "a" else 0) | chan
    return base & ~(0xFF << 36) | t << 36


def fields_of(w):
    return (w >> 40) & 0xF, "a" if w >> 39 & 1 else "o", (w >> 36) & 7


# ---- iaddu32's value -------------------------------------------------------------------------
def sext16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def iaddu32(a, b, model="H-ZX"):
    lo = (a & 0xFFFF) if model in ("H-ZX", "H-ZX-ADV") else sext16(a)
    return (lo + b) & M
