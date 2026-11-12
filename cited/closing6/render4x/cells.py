#!/usr/bin/env python3
"""cells.py (round 6, offline): (1) flag bytes of word 0 in the completed four-array dumps of r5-render4x (is bit 27 ever set?);
(2) H-TPM's numbers for candidate rows: the end of the Z-order entries of the target's tiles and of the header grid's tiles against
the maximum's td.rgn on the rgn4 kernel, the scene pages U4 and the TA-data size; (3) the stream offsets H-TPM says a faulting row
loses.  Standard library only."""
import gzip, os, struct, sys, collections, glob, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from morton import lay, z, rup, ATT

def flags():
    print("(1) flag bytes (word 0 bits 31:24) of the completed four-array dumps:")
    for p in sorted(glob.glob(ATT + "/[mlx]/*.tri.tadata.bin.gz")):
        m = re.search(r"-(\d+)x(\d+)(?:-max(\d+)x(\d+))?\.tri", p)
        w, h = int(m.group(1)), int(m.group(2)); mw, mh = int(m.group(3) or w), int(m.group(4) or h)
        t, mm = lay(w, h), lay(mw, mh)
        n = 16 * t["n"] ** 2 * (2 * t["mx"] // 4) * (2 * t["my"] // 4)
        b = gzip.open(p).read()
        c = collections.Counter(struct.unpack_from("<I", b, mm["rgn"] + 12 * i)[0] >> 24 for i in range(n))
        nzb = sum(1 for o in range(0, mm["rgn"], 4) if b[o:o + 4] != b"\0\0\0\0")
        print("   %-34s headers %6d flags %s; non-zero dwords below td.rgn %d" % (os.path.basename(p)[:34], n, dict(sorted(c.items())), nzb))

def u4(w, h): return 1 + math.ceil(2 * math.ceil(w / 16) * math.ceil(h / 16) / 32)
def ends(w, h):
    t = lay(w, h)
    X, Y, GX, GY = 2 * t["tx"], 2 * t["ty"], 2 * t["n"] * t["mx"], 2 * t["n"] * t["my"]
    return 4 * z(X - 1, Y - 1) + 4, 4 * z(GX - 1, GY - 1) + 4
def tasize(mw, mh):
    m = lay(mw, mh); rs = 0xc0 * (m["mx"] // 4) * (m["my"] // 4) * m["n"] ** 2
    return m["rgn"] + rup(4 * rs, 4096) + rup(rs, 4096)
def lost(w, h, mw, mh, rgn=None):
    """headers whose stream offset (word 1) is the entry of an in-target tile: (count, first offset, last offset)"""
    t = lay(w, h); base = rgn if rgn is not None else lay(mw, mh)["rgn"]
    X, Y = 2 * t["tx"], 2 * t["ty"]
    ent = {4 * z(x, y) for x in range(X) for y in range(Y)}
    n = t["n"]; i = 0; out = []
    for col in range(n):
        for row in range(n):
            for by in range(2 * t["my"] // 4):
                for bx in range(2 * t["mx"] // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * t["mx"] + bx * 4 + xx, row * 2 * t["my"] + by * 4 + yy
                            if x < X and y < Y and (base + 12 * i + 4) in ent: out.append(base + 12 * i)
                            i += 1
    return (len(out), out[0], out[-1]) if out else (0, 0, 0)
def row(name, w, h, mw, mh, rgn=None):
    et, eg = ends(w, h); m = lay(mw, mh); r = rgn if rgn is not None else m["rgn"]
    pt, pg = ("fault" if et > r else "complete"), ("fault" if eg > r else "complete")
    n, a, b = lost(w, h, mw, mh, r)
    print("   %-5s %4d x %-4d on %4d x %-4d  rgn 0x%05x  target end 0x%05x grid end 0x%05x  H-TPM %-8s H-TPM-grid %-8s  U4 %4d  lost offsets %5d (0x%05x..0x%05x)  header 0 lost %s"
          % (name, w, h, mw, mh, r, et, eg, pt, pg, u4(w, h), n, a, b, "yes" if n and a == r else "no"))

if __name__ == "__main__":
    flags()
    print("(2) candidate rows on the rgn4 kernel (room = the maximum's 4 side^2):")
    for a in sys.argv[1:]:
        f = a.split(",")
        row(f[0], *[int(v) for v in f[1:5]], *( [int(f[5], 16)] if len(f) > 5 else []))
