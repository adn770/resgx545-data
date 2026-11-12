# SPDX-License-Identifier: MIT
"""Round 6 planning, Q230 (1/w): the words known after E859, split FIT / HELD OUT.  Standard library only.
Sources (all published in resgx545-data): E842's score-g4-rw.txt, E859's score-g5-rwa.txt and score-g5-rw.txt, and the earlier w
transcribed in the fold's fold/posthoc_r5.py section C (E754, E782, E783, E795, E796, E798).
HELD OUT = the 30 dense-table words E859's frozen hash marked HELD OUT (score-g5-rw.txt column `half`; score/rwdesign5.py split()).
FIT = every other mantissa (they were all explored before: E851's exploration, E859's post hoc section C).
load(held=False) never parses a HELD OUT row's `got` word: the fit scripts cannot see those deltas."""
import pathlib, re, struct
DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
R4S = DATA / "closing-r4-pixel/out/20261111-210423/score-g4-rw.txt"
R5A = DATA / "closing-r5-pixel/out/20261112-091752/score-g5-rwa.txt"
R5B = DATA / "closing-r5-pixel/out/20261112-091752/score-g5-rw.txt"
def bits(x): return struct.unpack("<I", struct.pack("<f", x))[0]
EARLY0 = [3, 7, 0.003, 3e-5, 0.3, 1.3, 5, 6, 11, 19, 23, 1.5, 1 + 2**-23, 1 - 2**-23, 1.0000004, 1.3125, 1.625, 1.0625, 0.5, 2, 1.1, 0.875, 1.4375]
EARLY1 = [9, 0.7, 1.40625, 1.59375, 1.6875]
ROW = re.compile(r"(\S+-\w+)\s+(\d)\s+(\S+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+|-)\s+(\S+)\s+(FIT|HELD OUT|\?)")
def load(held=False):
    """{24-bit mantissa M (2^23 <= M < 2^24): delta} of the FIT set (held=False) or of the HELD OUT set (held=True)."""
    out, hold = {}, set()
    def add(w, d):
        M = (w & 0x7fffff) | 0x800000
        assert out.setdefault(M, d) == d, hex(M)
    for p in (R5B, R5A, R4S):
        for ln in p.read_text().splitlines():
            m = ROW.match(ln)
            if not m or m[6] == "-": continue
            w = int(m[4], 16)
            if p == R5B and m[8] == "HELD OUT" and m[1].startswith("d-"):
                hold.add((w & 0x7fffff) | 0x800000)
                if held: add(w, int(m[6], 16) - int(m[5], 16))
                continue
            if not held: add(w, int(m[6], 16) - int(m[5], 16))
    if not held:
        for w in EARLY0: add(bits(w), 0)
        for w in EARLY1: add(bits(w), 1)
        assert not (set(out) & hold), "a HELD OUT mantissa is also in the FIT set"
    return out
if __name__ == "__main__":
    f = load()
    print(f"FIT mantissas {len(f)}: RZ + 1 {sum(f.values())}; HELD OUT mantissas (deltas not read here): 30 expected")
