# SPDX-License-Identifier: MIT
"""o4world.py: the p5-o4 mock image of one job, shared by the scorer tests (tests/test_o5.py) and the fake tool's o4 branch
(tests/fake_o4.py, which gets the output words by running the STAGED PROGRAM in sgx-sim: the mock answers by the command, not by the
case name).  The image is a real kept R3 p-c3 image (tests/fixtures/p4o4: c-o4-u-x / -y, E808) re-worded: at each pixel the template's
tag says which output landed there (1: o0, 2 and 12: o1, 3: o2, 6: o5, 7: o6, 5 and 13: the tag-5 word of the world's MODEL over the
instance's outputs; anything else stays background); the high half (the source coordinate) is the template's, the low 16 bits are
the program's word.  A model whose word is None (an output it reads was not written) leaves the pixel background."""
import gzip
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "score"))
import o5model as M  # noqa: E402

BG = 0xff203040
FROM = {1: 0, 2: 1, 12: 1, 3: 2, 6: 5, 7: 6}


def template(ax):
    t = gzip.open(HERE / "fixtures/p4o4" / f"c-o4-u-{ax}.txt.gz").read().decode()
    rows = {}
    for ln in t.splitlines():
        m = re.search(r"row (\d+): (.*)$", ln)
        if m:
            rows[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [rows[i] for i in sorted(rows)]


def image(ax, words16, model):
    """64 x 64 words: words16 {j: low 16 bits of o_j's final word or None}."""
    tw = M.combine(model, words16) if model != "none" else None
    out = []
    for r in template(ax):
        row = []
        for v in r:
            if v == BG:
                row.append(BG)
                continue
            t = v & 15
            if t in (5, 13):
                w = tw
            elif t in FROM:
                w = words16.get(FROM[t])
            else:
                w = None
            row.append(BG if w is None else (v & 0xffff0000) | (w & 0xffff))
        out.append(row)
    return out


def text(name, g, w=64, h=64):
    lines = [f"probe {name}: tri {w}x{h} (2 coordinates)", f"probe {name}: o0 mixed 0x{BG:08x} x{sum(r.count(BG) for r in g)}"]
    lines += [f"probe {name}: row {y}: " + " ".join(f"{v:08x}" for v in r) for y, r in enumerate(g)]
    return "\n".join(lines) + "\n"
