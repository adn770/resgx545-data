"""Round 7 plan, Q293 (offline, read-only): every kept parameter-buffer dump (*.param.bin.gz) of the published closing
sessions under resgx545-data/render/closing-*: the dwords that open an object as the one-triangle scene's does
(0x04000004 0x00030001 0x04000000) and, for each such object, the offset of the format word 0x00040101 from the object's
start and the dword right before it.  An object whose format word sits at +12 has the inserted dword at +11 (Q293); +11 is
the plain layout.  Prints one line a dump with two or more objects, and the totals."""
import glob, gzip, struct, collections
ROOT = "/Users/jtorra/src/resgx545-data/render/"
HEAD = (0x04000004, 0x00030001, 0x04000000)
tot = collections.Counter()
for p in sorted(glob.glob(ROOT + "closing-*/**/*param.bin.gz", recursive=True)):
    try:
        b = gzip.open(p).read(4096 * 4)
    except OSError:
        tot["unreadable"] += 1
        continue
    w = struct.unpack("<%dI" % (len(b) // 4), b[: len(b) // 4 * 4])
    objs = []
    for i in range(len(w) - 16):
        if w[i:i + 3] == HEAD:
            off = next((k for k in range(8, 16) if w[i + k] == 0x00040101), None)
            objs.append((i, off, w[i + off - 1] if off else None))
    tot["dumps"] += 1
    tot["objects %d" % len(objs)] += 1
    if len(objs) >= 2:
        tot["two-object dumps"] += 1
        kinds = tuple("+%s/prev=%s" % (o[1], "%#x" % o[2] if o[2] is not None else "-") for o in objs)
        tot["kinds " + " | ".join(kinds)] += 1
        print(p[len(ROOT):], [(o[0],) + (o[1],) + ("%#x" % o[2] if o[2] is not None else None,) for o in objs])
for k in sorted(tot):
    print("%6d  %s" % (tot[k], k))
