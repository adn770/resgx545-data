"""Round 7 plan, Q293 (offline, read-only): the first dwords of the kept parameter-buffer dumps of r6-render4x stage t
(t7: tri -n 2 --geometry 1 at CR_TE_AA 0x40000000 with 2:par:11=1; t8: one render, 0x40000000) as hex, 8 a line, and every
dword index holding the format word 0x00040101, to see how many objects the dump holds and what precedes each."""
import gzip, struct, sys
T = "/Users/jtorra/src/scratch/resgx545/closing6/r6-render4x/out/20261112-144822/t/"
for name in ("t8-ctl-te40-1array", "t7-tri-te40-poke11"):
    b = gzip.open(T + name + ".tri.param.bin.gz").read()
    w = struct.unpack("<%dI" % (len(b) // 4), b[: len(b) // 4 * 4])
    nz = [i for i, v in enumerate(w) if v]
    print(name, "dwords", len(w), "non-zero", len(nz), "last non-zero", nz[-1] if nz else None)
    print("  format word 0x00040101 at dwords", [i for i, v in enumerate(w) if v == 0x00040101][:20])
    for i in range(0, min(96, len(w)), 8):
        print("  %4d: %s" % (i, " ".join("%08x" % v for v in w[i:i + 8])))
    # runs of non-zero dwords (start, length) in the first 64 KiB
    runs, s = [], None
    for i, v in enumerate(w[:16384]):
        if v and s is None:
            s = i
        if not v and s is not None and (i + 1 >= len(w) or not w[i + 1]):
            runs.append((s, i - s)); s = None
    print("  non-zero runs (start, len) in the first 16384 dwords:", runs[:24])
