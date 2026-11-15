# SPDX-License-Identifier: MIT
"""q123.py: r23-pk's placed programs (rank-round22.md 2.2, R22-2 a), shared by gen/make.py and
mock/world.py: the rows, the programs' words and each row's o0 under each model. Standard
library only."""

STEP = 0x80000
PAD = 0xB0000000            # placed word k ends the task with o0 = PAD | k
WPAD = 0xC0DE0000           # word k of the probe's own program (heap base) ends with WPAD | k
LAND = 0xFA11               # the word after a jump that falls through
PHAS = "phas #0, #0, pixel, end, parallel"


def code_index(off, form):
    """The index the DOUTU starts at, counted from the code base: cbase keeps the offset's bits
    18:3 (code base = the offset rounded down to 0x80000, E492), exe18 bits 20:3 (code base 0)."""
    return (off % STEP) // 8 if form == "cbase" else off // 8


def code_base(off, form):
    return off - off % STEP if form == "cbase" else 0


def pad(k):
    return f"mov.skipinv.end o0, #0x{PAD | k:08X}"


def placed(kind, n, t, idx0):
    """The placed program: word 0 phas; a straight run of nops to word t (run), or a lapc / ba
    to the absolute index idx0 + t (lapc, ba); every other word a pad that ends the task with
    its own word number, so any landing in the program names itself."""
    w = [PHAS]
    if kind == "run":
        w += ["nop"] * (t - 1)
    elif kind == "lapc":
        # word 1 a nop: qword 1 a limm mov would be run by the library mock as its own fill
        w += ["nop", f"mov.skipinv r5, #0x{idx0 + t:05X}", "mov pclink, r5", "nop", "lapc",
              f"mov.skipinv.end o0, #0x{LAND:04X}"]
    elif kind == "ba":
        w += [f"ba #0x{idx0 + t:05X}", f"mov.skipinv.end o0, #0x{LAND:04X}"]
    elif kind == "end":
        pass
    w += [pad(k) for k in range(len(w), n)]
    assert len(w) == n and (kind == "end" or w[t] == pad(t))
    return w


def heap_base_prog():
    """The probe's own program (FILE, at the code heap's base, never started): 256 words, word k
    ends the task with o0 = WPAD | k, so a landing at the base (a wrap) names its word."""
    return [f"mov.skipinv.end o0, #0x{WPAD | k:08X}" for k in range(256)]


# name, stage, set, form, offset, kind, words, target word t; o0 under each model
Q123 = [
    ("c-run", "q123", "control", "cbase", 0x40000, "run", 600, 590),
    ("c-lapc", "q123", "control", "cbase", 0x40000, "lapc", 600, 590),
    ("x18-b16", "q123", "heldout", "exe18", 0x80040, "end", 8, 1),
    ("b16-run", "q123", "heldout", "cbase", 0x7fe00, "run", 600, 590),
    ("b16-ba", "q123", "heldout", "cbase", 0x7fe00, "ba", 600, 80),
    ("b16-lapc", "q123", "heldout", "cbase", 0x7fe00, "lapc", 600, 80),
    ("b16-long", "q123", "heldout", "cbase", 0x78000, "run", 8192, 8100),
    ("b17-run", "q123h", "heldout", "exe18", 0xffe00, "run", 600, 590),
    ("b17-ba", "q123h", "heldout", "exe18", 0xffe00, "ba", 600, 80),
    ("b17-lapc", "q123h", "heldout", "exe18", 0xffe00, "lapc", 600, 80),
]


def q123_models(off, form, kind, n, t, bits=16):
    """{model: o0} for one row. H-CARRY18: the 18-bit counter carries across the step and every
    target is reached (o0 = PAD | t). H-WRAP (bits 16, q123) or H-WRAP17 (bits 17, q123h): the
    counter's low 16 (17) bits wrap and the bits above stay, so a run that crosses lands on the
    window's first word and a target past it is taken modulo the window, at the heap base's page
    (an assert: every landing a model allows is mapped). For the exe18 start at 0x80040: H-EXE18
    (EXE bit 16 honoured: placed word 1) against H-EXE16 (bit 16 dropped: the heap base's word
    idx0 & 0xffff)."""
    idx0, base = code_index(off, form), code_base(off, form)
    if kind == "end":
        assert base == 0 and (idx0 & 0xffff) < 256
        return {"H-EXE18": PAD | 1, "H-EXE16": WPAD | (idx0 & 0xffff)}
    tgt, win = idx0 + t, (1 << bits) - 1
    carry = PAD | t
    wrap = "H-WRAP" if bits == 16 else "H-WRAP17"
    if (idx0 & ~win) == (tgt & ~win):
        return {"H-CARRY18": carry, wrap: carry}
    wrapped = (idx0 & ~win) + (0 if kind == "run" else tgt & win)
    assert base == 0 and wrapped < 256, "a wrap must land in the heap base's program"
    return {"H-CARRY18": carry, wrap: WPAD | wrapped}


