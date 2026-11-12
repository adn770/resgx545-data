#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fake_rw.py ARGS...: the g5-rw branch of the fake tool (tests/fake_tool.sh).  It answers by the command's argv: the command must be
R4's CMD shape exactly (--tri vtxuse, 64x64, --vtx-coords 2, --dump-render DIR, the pix_green pixel slot; anything else writes no
dump), and the staged vertex program named by the LAST argument runs in sgx-sim (debug/target/debug/simcheck, code index 0x40) at
the tool's three vertices (clip x = -0.75, 0.75, -0.375, y = -0.75, -0.375, 0.75, z 0, w 1): its o0, o1 and o3 give each vertex's
window 32 + 32 o0 / o3 and its w.  A vertex outside the guard band (-16 .. 80, E777) writes a REAL clipped object (R4's kept rw-15
dump, 7 vertices); else a REAL kept object (R4's rw-01: its first page and streams, tests/fixtures/rwdump) is rewritten with the three
windows, depth 0x3f000000 and the world's 1/w words.  A mantissa read before keeps its delta (H-MANT's table and R5's d-01, d-02
words); another one follows FAKE_RW_RULE (R6-pixel's worlds, plan section 5 M-G):
  smooth (default)  RZ + 1 iff frac >= 1 - e(M), e constant on blocks of 2^20 mantissas (0.2 to 0.35): windows at strides 1 and 2^8
                    are separable, H-FRAC holds
  hash              e(M) hashed in [0, 0.5): no window separable (inversions), H-FRAC holds
  below             smooth, and a sixteenth of the mantissas with frac < 0.5 store RZ + 1: H-FRAC refuted
  exp               smooth, and a read mantissa's delta flips at w >= 16: H-MANT refuted at exponents 5, 8, 12
  clip12            smooth, and a job with w >= 2^12 is clipped (FAILED shape): "no object at this exponent"
  badwin            smooth, and a job whose three mantissas were never read lands one pixel to the right (L and B FAILED shape)
  hmant             R5's world (a hash bit for a mantissa not read); rz (RZ always); noscale (hmant, x and y unscaled: R4's design).
Writes DIR/PROG.param.bin and DIR/PROG.tadata.bin."""
import gzip
import hashlib
import os
import pathlib
import re
import struct
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "score")]
import rwdesign5 as D  # noqa: E402
import rwdesign6 as D6  # noqa: E402

HARNESS = HERE.parent / "debug/target/debug/simcheck"
SHAPE = re.compile(r"^probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render (\S+) "
                   r"--slot pixel=\S+/pix_green\.bin (\S+\.bin)$")
VX, VY = (-0.75, 0.75, -0.375), (-0.75, -0.375, 0.75)
f2b = lambda f: struct.unpack("<I", struct.pack("<f", f))[0]
b2f = lambda b: struct.unpack("<f", struct.pack("<I", b))[0]
KD = None


def vertex(binf, x, y):
    r = subprocess.run([str(HARNESS), str(binf), "0x40", "--set", f"pa0={f2b(x):#x}", "--set", f"pa1={f2b(y):#x}", "--set", "pa2=0",
                        "--set", "pa3=0x3f800000"], capture_output=True, text=True)
    return {m[1]: int(m[2], 16) for ln in r.stdout.splitlines() if (m := re.fullmatch(r"(o\d+) = (0x[0-9a-f]+)", ln))}


def known():
    global KD
    if KD is None:
        KD = dict(D.known_deltas())
        for n in ("d-01", "d-02"):
            ws, gs = D6.r5_words(n)
            for w, g in zip(ws, gs):
                KD[w & 0x7fffff] = g - D.rz_word(w)
    return KD


def h01(M, salt):
    return int(hashlib.sha256(salt + struct.pack("<I", M)).hexdigest()[:8], 16) / 2 ** 32


def delta(wb, rule):
    if rule == "rz":
        return 0
    d = known().get(wb & 0x7fffff)
    M = (wb & 0x7fffff) | 0x800000
    if d is None:
        if rule in ("hmant", "noscale"):
            d = hashlib.sha256(struct.pack("<I", wb & 0x7fffff)).digest()[0] & 1
        else:
            f = D6.frac(M)
            e = h01(M, b"e") / 2 if rule == "hash" else 0.2 + 0.15 * ((M >> 20) % 8) / 8
            d = int(f >= 1 - e)
            if rule == "below" and f < 0.5 and h01(M, b"below") < 1 / 16:
                d = 1
    elif rule == "exp" and b2f(wb) >= 16:
        d ^= 1
    return d


def main(argv):
    m = SHAPE.match(" ".join(argv))
    print(f"probe {pathlib.Path(argv[-1]).stem}: tri 64x64 (2 coordinates), vtxuse pixel replaced")
    if not m:
        print("probe: o0 mixed 0xff203040 x4096")
        return 0
    out, binf = pathlib.Path(m[1]), m[2]
    name = pathlib.Path(binf).stem
    rule = os.environ.get("FAKE_RW_RULE", "smooth")
    vs = []
    for x, y in zip(VX, VY):
        o = vertex(binf, x, y)
        sx, sy, w = b2f(o["o0"]), b2f(o["o1"]), o["o3"]
        if rule == "noscale":
            sx, sy = x, y
        vs.append((32 + 32 * sx / b2f(w), 32 + 32 * sy / b2f(w), w))
    if rule == "badwin" and not any((v[2] & 0x7fffff) in known() for v in vs):
        vs = [(wx + 1, wy, wb) for wx, wy, wb in vs]
    clip = any(not -16 <= c <= 80 for v in vs for c in v[:2]) or (rule == "clip12" and any(b2f(v[2]) >= 4096 for v in vs))
    src = HERE / "fixtures/rwdump" / ("clip" if clip else "base")
    p = bytearray(gzip.open(f"{src}.param.bin.gz").read())
    t = gzip.open(f"{src}.tadata.bin.gz").read()
    if not clip:
        ws = list(struct.unpack("<1024I", bytes(p[:4096])))
        last = max(i for i, x in enumerate(ws) if x)
        for v, (wx, wy, wb) in enumerate(vs):
            ws[3 + 3 * v] = D.rz_word(wb) + delta(wb, rule)          # PB_OBJ.RHW: 3 dwords a vertex in this object
        pk0 = last + 1 - 8                                           # the 8 packed dwords end the first page's words (pbdump.obj)
        big = sum(ws[pk0 + i] << (32 * i) for i in range(8)) & ~((1 << 240) - 1)
        for v, (wx, wy, wb) in enumerate(vs):
            big |= (round((wy + 4096) * 256) | round((wx + 4096) * 256) << 24 | 0x3f000000 << 48) << (80 * v)
        for i in range(8):
            ws[pk0 + i] = (big >> (32 * i)) & 0xffffffff
        p[:4096] = struct.pack("<1024I", *ws)
    (out / f"{name}.param.bin").write_bytes(bytes(p))
    (out / f"{name}.tadata.bin").write_bytes(t)
    print(f"probe {name}: o0 mixed 0xff203040 x3459 0xff00ff00 x637")
    print("job: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
