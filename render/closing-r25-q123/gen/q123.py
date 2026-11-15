# SPDX-License-Identifier: MIT
"""q123.py: r25-q123's placed programs and models (rank-round24.md 2.3, R24-4 a), shared by
gen/make.py, mock/world.py and the tests. Standard library only.

q123s (the code step, held out): E492's read and jump programs (usse/place-more's
p25_link_read.bin and p25_link_jump.bin, byte for byte) followed by pads, at E492's 0x300008
(control) and four new placements chosen so that every other candidate step predicts another link.
q123w (indices 256 to 8191, held out): an 8192-word program at 0x40000 (E1098's in-step form),
a lapc (six) or a ba (four) to target words drawn by SEED; control E1098's c-lapc (word 590)."""
import random

STEP = 0x80000
PAD = 0xB0000000            # placed word k ends the task with o0 = PAD | k
WPAD = 0xC0DE0000           # word k of the probe's own program (heap base) ends with WPAD | k
LAND = 0xFA11               # the word after a jump that falls through
PHAS = "phas #0, #0, pixel, end, parallel"
LINK_MASK = 0x3FFFF         # pclink keeps 18 bits (E475)
SPAN = 32                   # words of a q123s placed program: E492's words, then pads

# the ten old placements and the links read there (E476: place-link; E492: place-more)
OLD = {0x10000: 0x2002, 0x100000: 0x2, 0x1FF000: 0xFE02, 0x200000: 0x2, 0x400000: 0x2,
       0x2FF000: 0xFE02, 0x1A0000: 0x4002, 0x3A8000: 0x5002, 0x4FF000: 0xFE02, 0x300008: 0x3}
CONTROL_OFF = 0x300008      # E492's placement repeated (link 0x3)
NEW = (0x0C3010, 0x2CA7F8, 0x3D0100, 0x1C8008)   # rank-round24.md 2.3, frozen before the run

# q123w: the seed and the draw (frozen with the predictions; the generator re-draws and checks)
SEED = 0x25123
LO, HI = 256, 8191
WOFF, WN = 0x40000, 8192


def link(off, u):
    """the link of br.savelink #1 at word 1 of a program placed at off, the code base the
    placement rounded down to u (u None: no step, code base 0); 18 bits kept"""
    return ((off % u if u else off) // 8 + 2) & LINK_MASK


def fits(u):
    return sum(link(x, u) == v for x, v in OLD.items())


def multiples_fitting_all(top=0x1000000):
    """every multiple of 8 up to top that fits the ten old links (E1098's post hoc fit: 0x80000
    only); early exit on the first link that does not fit"""
    items = sorted(OLD.items(), key=lambda kv: kv[0] % 0x8000 == 0)
    out = []
    for u in range(8, top + 1, 8):
        for x, v in items:
            if (x % u) // 8 + 2 != v:
                break
        else:
            out.append(u)
    return out


def rivals():
    """{model: step} of the other candidates: every power of two from 0x1000 to 0x1000000 that
    fits five or more of the ten old links, and no step"""
    out = {}
    for b in range(12, 25):
        u = 1 << b
        if u != STEP and fits(u) >= 5:
            out[f"H-STEP{u:X}"] = u
    out["H-NOSTEP"] = None
    return out


def step_models(off):
    """{model: o0} of a q123s row (read and jump alike: o0 = the link, the jump lands at link + 8
    on the hardware's own count)"""
    m = {"H-STEP80000": link(off, STEP)}
    for name, u in rivals().items():
        m[name] = link(off, u)
    return m


def draw():
    """the ten q123w targets in run order: 256 and 8191 and eight more distinct words of 257 to
    8190 (not 590, the control's), shuffled; the first six lapc, the last four ba"""
    r = random.Random(SEED)
    pool = [t for t in range(LO + 1, HI) if t != 590]
    ts = [LO, HI] + r.sample(pool, 8)
    r.shuffle(ts)
    return [("lapc" if i < 6 else "ba", t) for i, t in enumerate(ts)]


def pad(k):
    return f"mov.skipinv.end o0, #0x{PAD | k:08X}"


def placed(kind, n, t, idx0):
    """E1098's placed program (gen/q123.py of r23-pk): word 0 phas; a lapc / ba to the absolute
    index idx0 + t; every other word a pad that ends the task with its own word number"""
    w = [PHAS]
    if kind == "lapc":
        w += ["nop", f"mov.skipinv r5, #0x{idx0 + t:05X}", "mov pclink, r5", "nop", "lapc",
              f"mov.skipinv.end o0, #0x{LAND:04X}"]
    elif kind == "ba":
        w += [f"ba #0x{idx0 + t:05X}", f"mov.skipinv.end o0, #0x{LAND:04X}"]
    w += [pad(k) for k in range(len(w), n)]
    assert len(w) == n and w[t] == pad(t)
    return w


def heap_base_prog():
    return [f"mov.skipinv.end o0, #0x{WPAD | k:08X}" for k in range(256)]


def word_models(t):
    """{model: o0} of a q123w row: H-INDEX lands on the target word itself; H-WRAP256 keeps the
    index's low 8 bits (the probe's own page: the heap base's word t & 0xff)"""
    return {"H-INDEX": PAD | t, "H-WRAP256": WPAD | (t & 0xFF)}
