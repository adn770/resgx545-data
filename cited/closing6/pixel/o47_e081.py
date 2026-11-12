# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O6 (post hoc reading of E081's kept images; exploration).
E081's shader writes pa0 (x job) or pa1 (y job) to ONE register oN (N = 0..7) and nothing to o0, no marker.  E373 later showed
that an unwritten o0 keeps the earlier job's words.  Are the o4..o7 images of E081 words of the oN write, or the o0 job's left over?
Per case N: non-background pixels; pixels equal to case 0's word at the same pixel (the o0 job's own image); pixels equal to the
previous case's image.  Reads only usse/output-registers of resgx545-data.  Standard library only."""
import pathlib, re
D = pathlib.Path("/Users/jtorra/src/resgx545-data/usse/output-registers")
BG = 0xff203040
for ax in "xy":
    g = {}
    for line in (D / f"usse-output-registers-oreg-{ax}/raw.txt").read_text().splitlines():
        m = re.match(r"probe \S+__(\d+): row (\d+): (.*)$", line)
        if m: g.setdefault(int(m[1]), {})[int(m[2])] = [int(v, 16) for v in m[3].split()]
    img = {n: [r[i] for i in sorted(r)] for n, r in g.items()}
    for n in sorted(img):
        a = img[n]; nb = [(x, y) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != BG]
        same0 = sum(1 for x, y in nb if a[y][x] == img[0][y][x])
        prev = sum(1 for x, y in nb if n and a[y][x] == img[n - 1][y][x])
        vals0 = {v for r in img[0] for v in r}
        known = sum(1 for x, y in nb if a[y][x] in vals0)
        print(f"oreg-{ax} o{n}: non-background {len(nb)}; equal to the o0 job's word at that pixel {same0}; equal to the case before {prev}; a word the o0 job holds anywhere {known}")
