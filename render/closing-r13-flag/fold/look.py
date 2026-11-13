# SPDX-License-Identifier: MIT
"""fold/look.py: r13-flag's post hoc reads of the kept attempt (written after the run, not frozen).
  python3 fold/look.py [R13TEX_SB12_REP]   (run from the session directory)
1. f1: each bit-14 row's end, the kernel's BIF status and fault page, against the probe's mappings
   (the scratch's address the probe printed, 16 pages, and the coordinate buffer's 3 pages after
   it [infer: the general heap's order, gen/README]).
2. f2: why the control failed: f2-ctl's 4096 words against E383's bit-12 mode 0 run, split into
   the high and the low 16 bits, and (optional argument) against r13-tex's sb12-rep-m0-c0, the same
   job in the same sitting; the ungated bit-11 readings.
3. f3: each row's end with the counter c that E700's M1 gives before it."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import f2  # noqa: E402
import f3  # noqa: E402
import pins  # noqa: E402

ATT = os.path.join(KP, "out/20261113-220930")
ROW = re.compile(r"row (\d+): ([0-9a-fA-F ]+)$", re.M)
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")


def text(stage, name):
    return gzip.decompress(open(os.path.join(ATT, stage, name + ".gz"), "rb").read()).decode()


def cases(stage):
    ls = open(os.path.join(ATT, stage, "cases.tsv")).read().splitlines()
    return [dict(zip(ls[0].split("\t"), ln.split("\t"))) for ln in ls[1:]]


def image(t):
    r = {}
    for m in ROW.finditer(t):
        r[int(m.group(1))] = m.group(2).split()
    return [int(v, 16) for y in sorted(r) for v in r[y]]


print("== 1. f1: T3 bit 14 on the twiddled texture")
for c in cases("f1"):
    n = c["name"]
    t, dm = text("f1", n + ".txt"), text("f1", n + ".dmesg")
    sc = int(re.search(r"scratch at (0x[0-9a-f]+)", t).group(1), 16)
    f = FAULT.findall(dm)
    line = f"{n}: {c['class']}, scratch {sc:#x} (+16 pages to {sc + 0x10000:#x}, coordinates to {sc + 0x13000:#x})"
    if f:
        s, a = f[-1]
        a = int(a, 16)
        line += (f"; BIF fault {s} at {a:#x}: page scratch + {(a & ~0xFFF) - sc:#x}, "
                 f"{((a & ~0xFFF) - sc - 0x13000) // 0x1000} pages past the coordinates' end, "
                 f"dword {((a & ~0xFFF) - sc) // 4} from the scratch's first")
    print(line)

print("== 2. f2: the control's words against E383's bit-12 mode 0")
e383 = {}
for m in re.finditer(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", pins.blob(f2.RAW12).decode(), re.M):
    e383.setdefault(m.group(1), {})[int(m.group(2))] = [int(x, 16) for x in m.group(3).split()]
runs = [[v for y in sorted(r) for v in r[y]] for r in e383.values()]
words = set(f2.mode0_words(pins.blob))
ctl = image(text("f2", "f2-ctl.txt"))
others = [("f2-ctl", ctl)]
if len(sys.argv) > 1:
    others.append(("r13-tex sb12-rep-m0-c0", image(gzip.decompress(open(sys.argv[1], "rb").read()).decode())))
print(f"E383's two runs: equal on {sum(a == b for a, b in zip(*runs))} of 4096")
for name, im in others:
    d = [(a, b) for a, b in zip(im, runs[0]) if a != b]
    print(f"{name}: {len(im)} pixels, inset {sum(v in words for v in im)} (frozen >= {f2.INSET_MIN}); "
          f"equal to E383 on {4096 - len(d)}; high 16 bits equal on "
          f"{sum((a >> 16) == (b >> 16) for a, b in zip(im, runs[0]))}; of the {len(d)} that differ, "
          f"{sum((a ^ b) >> 16 == 0 for a, b in d)} in the low 16 bits only")
if len(others) == 2:
    a, b = others[0][1], others[1][1]
    print(f"f2-ctl against r13-tex's replicate: equal on {sum(x == y for x, y in zip(a, b))}, high 16 bits "
          f"on {sum((x >> 16) == (y >> 16) for x, y in zip(a, b))}")
e = f2.e383_faults(pins.blob)
for c in cases("f2")[1:]:
    n = c["name"]
    s, a = FAULT.findall(text("f2", n + ".dmesg"))[-1]
    m = int(n.rsplit("m", 1)[1])
    print(f"{n}: {c['class']}, BIF fault {s} at {a} (page {int(a, 16) & ~0xFFF:#x}); E383 mode {m}: "
          f"{e[m][0]} at {e[m][1]}; runner's latch after the job {c['fault_int']} {c['fault_word']} [ungated]")

print("== 3. f3: ends and E700's c (M1) before each row")
c = 0
for (name, sset, knobs, args, job), row in zip(f3.ROWS, cases("f3")):
    assert row["name"] == name
    if "noreset" not in knobs.split():
        c = 0
    blocks = (job[1], job[2]) if job[0] == "2blk" else (job[1],) if job[0] == "1blk" else ()
    add = sum(f3.g(v) for v in blocks)
    print(f"{name}: {sset}, blocks {blocks or job[0]}, c {c} add {add}: {row['class']}")
    c = 0 if row["class"] == "hang" else c + add
