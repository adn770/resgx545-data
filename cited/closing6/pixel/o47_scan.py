# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O1 (post hoc reading of E858's kept images; no new job).
Question: does any word of o4..o7 reach the 64x64 image in E709's command?  In walk row w-j only o_j's word carries bit 4
(every other output's word carries bit 5, never bit 4), so in w-4..w-7 ANY image word with the job's marker and bit 4 set is
(or contains, by OR) o4..o7's word.  Positive control: w-0..w-3 (o0..o3 do reach the image).
Reads only render/closing-r5-pixel of resgx545-data (published).  Standard library only.
Prints, per walk job: words with the job's marker by (tag, bits 5:4); words of another marker; background."""
import collections, pathlib, sys
sys.dont_write_bytecode = True
R5 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
sys.path.insert(0, str(R5 / "score"))
import r4lib as L, score_o4 as S4  # the frozen decode
ATT = R5 / "out/20261112-091752/p5-o4"
k = L.Kept(ATT)
mk = dict(ln.split("\t") for ln in (R5 / "bins/p5o4-markers.tsv").read_text().splitlines())
tot = collections.Counter()
for name in k.names():
    base = name[:-4] if name.endswith("-rep") else name
    if base not in mk:
        continue
    g = S4.read_grid(k, name)
    if g is None:
        print(name, "no grid"); continue
    m = int(mk[base])
    own, other, bg = collections.Counter(), collections.Counter(), 0
    for r in g:
        for v in r:
            if v == L.BG:
                bg += 1
            elif ((v & 0xffff) >> 6) == m:
                own[(v & 15, v >> 4 & 3)] += 1
            else:
                other[v & 0xffff] += 1
    print(f"{name:14s} m={m:#x} bg {bg:4d} own " + " ".join(f"{t}:{b}={n}" for (t, b), n in sorted(own.items()))
          + (f"  OTHER-MARKER {dict(other)}" if other else ""))
    if name.startswith("w-") and not name.endswith("-rep"):
        j = int(name[2])
        for (t, b), n in own.items():
            tot[(j, "bit4" if b & 1 else "nobit4", t)] += n
print()
for j in range(8):
    b4 = {t: n for (jj, c, t), n in tot.items() if jj == j and c == "bit4"}
    nb = sum(n for (jj, c, t), n in tot.items() if jj == j and c == "nobit4")
    print(f"w-{j}: words with bit 4 by tag {dict(sorted(b4.items()))}; without bit 4: {nb}")
