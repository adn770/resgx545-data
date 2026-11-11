#!/usr/bin/env python3
"""dword 36 against the global list on the E625 batch's `tri` jobs (ta3d.N.bin after render N, tri.N.tadata.bin):
the unraised jobs there have 1-page global lists (E627), so this tests what g - 2 gives below 2."""
import sys, pathlib, gzip, struct, re, collections
sys.dont_write_bytecode = True
HOME = pathlib.Path.home()
D = HOME / "src/resgx545-data/dpm/partial-model-batch/dumps"


def gz(p):
    return gzip.open(p).read() if p.exists() else None


def dwords(b):
    return list(struct.unpack("<%dI" % (len(b) // 4), b[: len(b) // 4 * 4]))


def state_lists(td, off):
    d = dwords(td[off:off + 0x88]) if td and len(td) >= off + 0x88 else []
    out = []
    for i in range(17):
        w0, w1 = d[2 * i], d[2 * i + 1]
        out.append((i, w0 >> 16, w0 & 0xffff, w1) if (w0 or w1) else None)
    return out


def main():
    hits = collections.Counter()
    for sub in sorted(D.iterdir()):
        cs = sub / "cases.tsv"
        if not cs.exists():
            continue
        lines = cs.read_text().splitlines()
        hdr = lines[0].split("\t")
        for ln in lines[1:]:
            c = dict(zip(hdr, ln.split("\t")))
            n, args = c["name"], c["args"]
            if not args.startswith("tri") or "--ctx2" in args:
                continue
            w = int(re.search(r"--width (\d+)", args)[1]) if "--width" in args else 64
            h = int(re.search(r"--height (\d+)", args)[1]) if "--height" in args else 64
            off = 0x3000 if (w <= 64 and h <= 64) else 0x6000 if (w <= 1024 and h <= 768) else 0x42000
            # render N dumps: take every N with both files
            for N in range(1, 5):
                cb = gz(sub / f"{n}.ta3d.{N}.bin.gz")
                td = gz(sub / f"{n}.tri.{N}.tadata.bin.gz")
                if cb is None or td is None:
                    continue
                cb = dwords(cb)
                if len(cb) < 41 or not any(cb[35:41]):
                    continue
                ls = state_lists(td, off)
                g = ls[16]
                raised = cb[37] != 0 or cb[38] != 0
                gc = g[1] if g else 0
                key = ("raised" if raised else "unraised", f"g={gc}", f"dw36={cb[36]}")
                hits[key] += 1
    for k in sorted(hits):
        print(k, hits[k])


if __name__ == "__main__":
    main()
