# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O5 (post hoc reading of E858's kept dumps; exploration).
Do the kept memory dumps of the walk jobs (--dump-render: the parameter buffer NAME.*.param.bin and the TA data NAME.*.tadata.bin)
hold any dword whose low 16 bits are a word the job's program wrote (marker << 6 | bits 5:4 | tag)?  Positive control: none known
(the image itself is not in these dumps), so a zero is a statement about these two buffers only.
Reads only render/closing-r5-pixel of resgx545-data.  Standard library only."""
import collections, gzip, pathlib, struct
R5 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
ATT = R5 / "out/20261112-091752/p5-o4"
mk = dict(ln.split("\t") for ln in (R5 / "bins/p5o4-markers.tsv").read_text().splitlines())
tot = collections.Counter()
for name in sorted(mk):
    if not name.startswith("w-"):
        continue
    m = int(mk[name])
    for p in sorted(ATT.glob(f"{name}.*.bin.gz")):
        b = gzip.open(p).read()
        n = len(b) // 4
        hits = collections.Counter()
        for (v,) in struct.iter_unpack("<I", b[:n * 4]):
            if v and ((v & 0xffff) >> 6) == m and (v & 15) in range(1, 9) and (v >> 4 & 3) in (1, 2) and (v >> 16) not in (0, 0xffff):
                hits[(v & 15, v >> 4 & 3)] += 1
        kind = p.name.split(".")[-3]
        tot[kind] += sum(hits.values())
        print(f"{p.name:40s} {n:8d} dwords  hits {dict(hits)}")
print("total hits by dump:", dict(tot))
