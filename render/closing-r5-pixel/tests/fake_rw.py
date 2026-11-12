#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fake_rw.py ARGS...: the g5-rw branch of the fake tool (tests/fake_tool.sh).  It answers by the command's argv: the command must be
R4's CMD shape exactly (--tri vtxuse, 64x64, --vtx-coords 2, --dump-render DIR, the pix_green pixel slot; anything else writes no
dump), and the staged vertex program named by the LAST argument runs in sgx-sim (debug/target/debug/simcheck, code index 0x40) at
the tool's three vertices (clip x = -0.75, 0.75, -0.375, y = -0.75, -0.375, 0.75, z 0, w 1): its o0, o1 and o3 give each vertex's
window 32 + 32 o0 / o3 and its w.  A vertex outside the guard band (-16 .. 80, E777) writes a REAL clipped object (R4's kept rw-15
dump, 7 vertices); else a REAL kept object (R4's rw-01: its first page and streams, tests/fixtures/rwdump) is rewritten with the three
windows, depth 0x3f000000 and the world's 1/w words.  FAKE_RW_RULE: hmant (default: word = RZ + the frozen H-MANT delta of the
mantissa, a hash bit for a mantissa not read: a hidden mantissa rule), exp (as hmant, one ulp more at w >= 16: the delta follows the
exponent), rz (RZ always), noscale (as hmant, but x and y read unscaled: R4's design, the quarter jobs clip).
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


def delta(wb, rule):
    global KD
    if rule == "rz":
        return 0
    KD = D.known_deltas() if KD is None else KD
    d = KD.get(wb & 0x7fffff)
    if d is None:
        d = hashlib.sha256(struct.pack("<I", wb & 0x7fffff)).digest()[0] & 1
    if rule == "exp" and b2f(wb) >= 16:
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
    rule = os.environ.get("FAKE_RW_RULE", "hmant")
    vs = []
    for x, y in zip(VX, VY):
        o = vertex(binf, x, y)
        sx, sy, w = b2f(o["o0"]), b2f(o["o1"]), o["o3"]
        if rule == "noscale":
            sx, sy = x, y
        vs.append((32 + 32 * sx / b2f(w), 32 + 32 * sy / b2f(w), w))
    clip = any(not -16 <= c <= 80 for v in vs for c in v[:2])
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
