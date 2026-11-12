# SPDX-License-Identifier: MIT
"""R5-pixel fold, 2026-11-12: post hoc readings of the kept files (added at the fold, not by the run; nothing here is held out).

A. E850's family check (closing5/pixel/o4_family.py) modelled every one of its 8 configurations with o4 written at the tag-5 pair
   source.  For each configuration: the program's o4 write, whether a predicate guards it, and whether the guard is true at lane 0
   (g25 = 0 at the (even, even) sources every tag-5 pair has, E808).  Programs: E709's o4g-3 (data vdm/verification-1141ta), R3's
   generator gen/r3_c.py (render/closing-r3-pixel), R4's gen/r4_o4.py program kinds (render/closing-r4-pixel).
B. P3 of p5-o4 (frozen verdict cannot tell, the k = 0 rows undecided): each job's class against OR(o0,o3) gated and ignored.
C. The 1/w words: every word read of a kept vertex (E754, E782, E783, E795, E796, E798 as transcribed in closing5/pixel/rw_explore.py,
   and the five RZ w of sgx-pipe's lists that it leaves out; E842's score-g4-rw.txt; E859's score-g5-rw.txt), grouped by the 23-bit mantissa of w: mantissas read at more than one exponent,
   any with both RZ and RZ + 1, the exponents read, and the table (mantissa, delta) sgx-pipe takes.
Run from the session directory with RESGX545_DATA set (default ../.. of this file):
  python -I fold/posthoc_r5.py > fold/posthoc_r5.txt"""
import collections
import os
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
SESSION = HERE.parent
DATA = pathlib.Path(os.environ.get("RESGX545_DATA", SESSION.parent.parent))
R3 = DATA / "render/closing-r3-pixel"
R4 = DATA / "render/closing-r4-pixel"
ATT = SESSION / "out/20261112-091752"


def bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


# ---------------------------------------------------------------- A
print("A. E850's eight configurations: the o4 write at the tag-5 pair source (lane 0)")
sys.path.insert(0, str(R3 / "gen"))
import r3_c  # noqa: E402

e709 = (DATA / "vdm/verification-1141ta/programs/o4g-3-x.s").read_text()


def o4_lines(text):
    return [ln.strip() for ln in text.splitlines() if re.search(r"\bo4,", ln)]


def guard(text):
    m = re.search(r"xor\.testtaz\.chan0 !c0, p1, g25, #(\d+)", text)
    return int(m[1]) if m else None


cfgs = [
    ("R4 base, v-a3, v-a4, v-a-a5 (gen/r4_o4.py kinds u and value: `or.skipinv o4` unpredicated)", None, ["or.skipinv o4, ... (unpredicated)"]),
    ("R4 c-e709-x (E709's o4g-3-x.s)", guard(e709), o4_lines(e709)),
]
for name, cfg in (("R3 o4s-u", "o4s-u"), ("R3 k5", "k5"), ("R3 k7", "k7"), ("R3 k3", "k3")):
    t = r3_c.c_program(cfg, "x", 0x33)
    cfgs.append((name, guard(t), o4_lines(t)))
for name, k, lines in cfgs:
    if k is None:
        at0 = "written (no guard)"
    elif k == 0:
        at0 = "written if the guard is honoured or ignored"
    else:
        at0 = f"NOT written at lane 0 if the predicate gates o4 as it gates o1 (E808); written only if it is ignored (k = {k})"
    print(f"  {name}: guard g25 == {k}; o4 lines {lines}; at lane 0: {at0}")
print("  o4-reading models of E850 (AND(o4,o6), MUX(o4; o0, o2, o3, o5, o6)) fit c-e709-x, k5/k7 and k3 only if o4 is written at lane 0")
sc = (ATT / "score-p5-o4.txt").read_text()
for row in ("n-o4", "l-o4", "c-e709"):
    print("  R5", re.search(rf"^{row}: .*$", sc, re.M)[0])

# ---------------------------------------------------------------- B
print("\nB. P3 (p1 o3 = tag 4, !p1 o3 = tag 4 + bit 4), read per job against OR(o0,o3) gated / ignored (frozen predictions)")
pred = collections.defaultdict(dict)
for ln in (SESSION / "predictions/p5-o4.tsv").read_text().splitlines():
    f = ln.split("\t")
    if len(f) >= 4 and f[0].startswith("p3-") and f[3].startswith("OR(o0,o3)+"):
        pred[f[0][:-2]][f[3].split("+")[1]] = f[2]
for m in re.finditer(r"^(p3-\S+): reads (\S+)\s+d1 \d+\s+x \{(.*?)\}\s+y \{(.*?)\}", sc, re.M):
    cfg = m[1]
    print(f"  {cfg}: x {{{m[3]}}} y {{{m[4]}}}  gated {pred[cfg]['gated']}  ignored {pred[cfg]['ignored']}")

# ---------------------------------------------------------------- C
print("\nC. 1/w words of kept vertices, by the mantissa of w")
obs = []  # (w word, delta, source)
row = re.compile(r"^(\S+)\s+(\d)\s+(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+|-)\s+(-?\d+|-)\s")
for src, path in (("E842", R4 / "out/20261111-210423/score-g4-rw.txt"), ("E859", ATT / "score-g5-rw.txt")):
    seen = set()
    for ln in path.read_text().splitlines():
        m = row.match(ln)
        if m and m[7] != "-" and (m[1], m[2]) not in seen:
            seen.add((m[1], m[2]))
            obs.append((int(m[4], 16), int(m[7]), src))
for w in [3, 7, 0.003, 3e-5, 0.3, 1.3, 5, 6, 11, 19, 23, 1.5, 1 + 2**-23, 1 - 2**-23, 1.0000004, 1.3125, 1.625, 1.0625]:
    obs.append((bits(w), 0, "earlier"))
for w in [0.5, 2, 1.1, 0.875, 1.4375]:  # RZ, in sgx-pipe's ALIKE_W / PERSPECTIVE_W (E782, E783, E795, E796), not in rw_explore's list
    obs.append((bits(w), 0, "sgx-pipe lists"))
for w in [9, 0.7, 1.40625, 1.59375, 1.6875]:
    obs.append((bits(w), 1, "earlier"))
cnt = collections.Counter(s for _, _, s in obs)
print(f"  {len(obs)} words ({dict(cnt)}): RZ {sum(1 for o in obs if o[1] == 0)}, RZ + 1 {sum(1 for o in obs if o[1] == 1)}, "
      f"other {sum(1 for o in obs if o[1] not in (0, 1))}")
by = collections.defaultdict(set)
ex = collections.defaultdict(set)
for w, d, _ in obs:
    by[w & 0x7fffff].add(d)
    ex[w & 0x7fffff].add((w >> 23) - 127)
multi = {m: e for m, e in ex.items() if len(e) > 1}
both = sorted(m for m in by if len(by[m]) > 1)
print(f"  distinct mantissas {len(by)}; read at more than one exponent {len(multi)}; with both RZ and RZ + 1: {len(both)} {[hex(m) for m in both]}")
exps = collections.Counter((w >> 23) - 127 for w, _, _ in obs)
print(f"  exponents of w read (count of words): {dict(sorted(exps.items()))}")
held = sorted({(w >> 23) - 127 for w, _, s in obs if s == "E859"})
print(f"  exponents of the E859 words: {held}")
print("  table for sgx-pipe (23-bit mantissa, delta), one word or more read:")
tab = sorted((m, min(ds)) for m, ds in by.items() if len(ds) == 1)
for i in range(0, len(tab), 6):
    print("    " + " ".join(f"(0x{m:06x}, {d})," for m, d in tab[i:i + 6]))
print(f"  {len(tab)} entries, {sum(d for _, d in tab)} RZ + 1")
