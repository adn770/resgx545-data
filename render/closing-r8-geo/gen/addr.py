# SPDX-License-Identifier: MIT
"""addr.py: stage addr (R8-5, Q177): T0 address modes 4 to 7 on a 16 x 16 twiddled texture placed
at page 12 of a 24-page scratch buffer whose every dword is named (dword i = 0xD0000000 | i, the
probe's own fill), so every read decodes to the dword it came from. Standard library only.

The texture is E565's (T1 0x0c00f00f, T3 0x00800800); its base is moved by the program's T2 word
0x5CAFC000 (the probe loads the scratch buffer's address + 0xC000 for it: SCRATCH_IMM, not
--scratch-at, which only `tri` takes) and the buffer grown by `probe --scratch-pages 24` (16 to 64
accepted). The swept coordinate takes 128 positions at one texel a step, -4 + (p + 1/2) / 16 for
p = x | (y & 1) << 6, on every pair of rows (16 replicates a job); the other coordinate sits on
texel 8's centre (0.53125). Texel s = floor(16 u), t = floor(16 v); a 16 x 16 twiddled index has t
in bit 0 (E565's bd-u0 and bd-v0, tests/test_gen.py): idx = Morton(s, t) with t the low bit.

Rivals, frozen before the run, nothing fitted (every job held out):
  H-MASK-V       the swept axis wraps as E565's v axis does in that mode: 4, 5 repeat, 6, 7 clamp
  H-NOMASK-PAGE  no wrap: idx = Morton(s mod 16, t mod 16) + 256 (s div 16) + 256 (t div 16),
                 a texel past the texture names the dword of the next 16 x 16 block, in the
                 neighbouring pages of the buffer
  H-BORDER       inside the texture the twiddled texel, outside it one constant (any value, the
                 same at every outside position)
The v jobs are scored on the same three; H-MASK-V on v is E565's v-axis reading at a pitch of one
texel (E565 swept v at two). The control is mode 0 on u (repeat, E033 and E565's controls), whose
image the twiddle above gives exactly; it can fail."""
import texprog as T

BASE_PAGE = 12
PAGES = 24
BASE = BASE_PAGE * 1024           # dwords
T0_BASE = 0x07fe0000
T1 = 0x0c00f00f
T2 = 0x5cafc000                   # SCRATCH_IMM | 0xC000: the scratch address + 12 pages
T3 = 0x00800800
SMP = "smp2d r10, r24, r20, drc0"
SWEEP = ("p7", T.bits(8.0), T.bits(-11.96875))      # -4 + (p + 1/2) / 16
INSIDE = ("bits", T.bits(0.53125))                  # texel 8's centre
MODELS = ("H-MASK-V", "H-NOMASK-PAGE", "H-BORDER")


def jobs():
    """[(name, set, axis, mode)]: the control first."""
    out = [("addr-ctl-u0", "control", "u", 0)]
    out += [("addr-u%d" % m, "heldout", "u", m) for m in (4, 5, 6, 7)]
    out += [("addr-v%d" % m, "heldout", "v", m) for m in (4, 5, 6, 7)]
    return out


def coords(axis):
    return (SWEEP, INSIDE) if axis == "u" else (INSIDE, SWEEP)


def twords(axis, mode):
    t0 = T0_BASE | (mode << 6 if axis == "u" else mode << 3)
    return (t0, T1, T2, T3)


def morton(s, t):
    i = 0
    for b in range(4):
        i |= ((t >> b) & 1) << (2 * b) | ((s >> b) & 1) << (2 * b + 1)
    return i


def wrap(v, how):
    return v % 16 if how == "repeat" else min(max(v, 0), 15)


def texel(axis, x, y):
    """(s, t) of the pixel, unwrapped."""
    cs = [T.coord(c, x, y) for c in coords(axis)]
    return tuple(int((c * 16).__floor__()) for c in cs)


def predict(axis, mode, model, x, y):
    """The dword index read, None for H-BORDER's constant (outside the texture)."""
    s, t = texel(axis, x, y)
    if mode == 0 or model == "H-MASK-V":
        how = "repeat" if mode in (0, 4, 5) else "clamp"
        return BASE + morton(wrap(s, how), wrap(t, how))
    if model == "H-NOMASK-PAGE":
        return BASE + morton(s % 16, t % 16) + 256 * (s // 16) + 256 * (t // 16)
    if model == "H-BORDER":
        return BASE + morton(s, t) if 0 <= s < 16 and 0 <= t < 16 else None
    raise ValueError(model)


def image(axis, mode, model):
    return {(x, y): predict(axis, mode, model, x, y) for y in range(T.H) for x in range(T.W)}
