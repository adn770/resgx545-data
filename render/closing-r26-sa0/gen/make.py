#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r26-sa0's generator (round 26's plan, closing26/plan/rank-round26.md 2.2, decisions
R26-3 a). Writes tables/STAGE.txt, predictions/STAGE.tsv and the programs bins/NAME.bin, every
input read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Q126 clause (2): what iaddu32 writes into sa0 when one writer alone writes it. Every program runs
as the copy shader (`probe --coords`, pa0 = (y << 16) | x, 64 x 32 = 2048 instances) over eight
(r1, source 2) pairs; the writer is chosen as E513 selects a quad: `xor.testtaz.chan0 !c0, p0,
r7, r9` (r7 = pa0, r9 = the writer's pa0) and `!p0 br` over the body. E513 [HW]: the branch is
taken per 2x2 quad from its TOP-LEFT lane's test, so the writer is the quad whose top-left lane is
(0, 0) (pixels 0, 1, 64, 65) or (62, 30) (the quad of the plan's (63, 31): an odd lane selects
nothing). The four lanes of a selected quad run the same body with the same values.
  uc  gate: c-e521 (E1061's u-ctl-e521 byte for byte, every instance, r10) and c-one-r10 (the
      branch form, writer quad (0, 0), E1061's u-sa0 pairs into r10)
  us  six held-out rows into sa0: s-00-a, s-00-b (quad (0, 0), E1061's pairs), s-6331-a (quad
      (62, 30), the same), s-new-a, s-new-b, s-new-6331 (eight new pairs, seed frozen)
Frozen: H-ZX ((r1 & 0xffff) + source 2: E521, 8 of 8 dwords) against H-SX (sign extension) and
H-MIX (E1061's reading: every dword the zero-extended value of some pair, one not its own)."""
import os
import random
import sys
import tempfile
import pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

import json  # noqa: E402

TOOL = "t24"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("uc", "us")
M = 0xFFFFFFFF
E521_VEC = ("data:vectors/usse/decoder-vectors/usse-decoder-vectors-iaddu32-taz.vec.json",
            "data:vectors/usse/integer/usse-integer-iaddu32-value.vec.json")
E521_PAIRS = [(0x8000, 0x8000), (0xFFFF, 1), (M, 1), (0x7FFFFFFF, 1), (M, 2),
              (0x7C23A2BD, 0x47B003F0), (0xB99EDE85, 0x87261F80), (0x12345678, 0x11111111)]
# E1061's u-sa0 pairs (closing-r16-usse gen/progs.py R1S, R2S)
R1S = [0x8000, 0x8001, 0xABCD, 0xFFFF, 0x7FFF, 0xFFFF8000, 0x1234FEDC, 0xFFFFFFFF]
R2S = [0x8000, 0x7FFF0000, 0x1, M, 0x8001, 0x12345678, 0x80000000, 0x00010000]
E1061_PAIRS = list(zip(R1S, R2S))
SEED = 26126


def new_pairs():
    """Eight new pairs: r1's low half 0x8000-0xffff (the extensions differ in all eight), r1's high
    half and source 2 random, seed 26126 frozen; the eight zero-extended values distinct and none
    one of E1061's."""
    rng = random.Random(SEED)
    out, seen = [], {zx(a, b) for a, b in E1061_PAIRS}
    while len(out) < 8:
        a = rng.getrandbits(16) << 16 | rng.randrange(0x8000, 0x10000)
        b = rng.getrandbits(32)
        if zx(a, b) not in seen and sx(a, b) not in seen:
            seen.add(zx(a, b))
            out.append((a, b))
    return out


def zx(a, b):
    return ((a & 0xFFFF) + b) & M


def sx(a, b):
    lo = a & 0xFFFF
    return ((lo - 0x10000 if lo & 0x8000 else lo) + b) & M


# row: (name, pairs, writer pa0 or None for every instance, destination)
WRITERS = {"00": 0x00000000, "6331": (30 << 16) | 62}
ROWS = {
    "c-e521": (E521_PAIRS, None, "r10"),
    "c-one-r10": (E1061_PAIRS, WRITERS["00"], "r10"),
    "s-00-a": (E1061_PAIRS, WRITERS["00"], "sa0"),
    "s-00-b": (E1061_PAIRS, WRITERS["00"], "sa0"),
    "s-6331-a": (E1061_PAIRS, WRITERS["6331"], "sa0"),
    "s-new-a": (None, WRITERS["00"], "sa0"),
    "s-new-b": (None, WRITERS["00"], "sa0"),
    "s-new-6331": (None, WRITERS["6331"], "sa0"),
}
STAGES = {"uc": ("c-e521", "c-one-r10"),
          "us": ("s-00-a", "s-00-b", "s-6331-a", "s-new-a", "s-new-b", "s-new-6331")}


def pairs_of(name):
    p = ROWS[name][0]
    return new_pairs() if p is None else p


def kept_e521():
    """{(a, b): o0} of E521's kept vector files (the control's frozen readbacks)."""
    kept = {}
    for pin in E521_VEC:
        for v in json.loads(pins.blob(pin))["vectors"]:
            p = v["provenance"]["inputs"]
            kept.setdefault((int(p["A"], 16), int(p.get("B", "0"), 16)), set()).add(
                int(v["readback"]["o0"], 16))
    return kept


def program(name):
    """The row's USSE text: E1061's program (uc c-e521, byte for byte) or the branch form."""
    pairs, writer, dst = ROWS[name]
    lines = [f"; r26-sa0 {name} (gen/make.py)", "phas #0, #0, pixel, end, parallel",
             "mov.skipinv r29, #0x5CAF0000"]
    body = []
    for k, (a, b) in enumerate(pairs_of(name)):
        body += ["mov.skipinv r1, #0x%08X" % a, "mov.skipinv r2, #0x%08X" % b,
                 f"iaddu32.testtaz.chan0 {dst}, p0, r1, r2"]
        if dst == "sa0":
            body += ["mov r3, sa0", f"stad [r29,+#{k}], r3"]
        else:
            body += [f"stad [r29,+#{k}], r10"]
    if writer is not None:
        lines += ["mov.skipinv r10, #0xC0DE0001", "mov.skipinv r7, pa0",
                  "mov.skipinv r9, #0x%08X" % writer,
                  "xor.testtaz.chan0 !c0, p0, r7, r9", f"!p0 br #{len(body) + 1}"]
    lines += body + ["idf drc0, bif", "wdf drc0",
                     "mov.skipinv.end o0, r10"]
    return "\n".join(lines) + "\n"


def asm(text):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, "usse")
        return f.read_bytes()


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def fmt(vals):
    return ",".join("0x%03x=0x%08x" % (4 * k, v) for k, v in enumerate(vals))


def row_text(name):
    return f'probe --coords --temps 32 "$S/bins/{name}.bin"'


def stage(files, st):
    rows, pred = [], [HEAD]
    kept = kept_e521()
    for n in STAGES[st]:
        pairs = pairs_of(n)
        files[f"bins/{n}.bin"] = asm(program(n))
        ctl = n.startswith("c-")
        rows.append(f"{n}|{'control' if ctl else 'heldout'}|safe|{'reads:scratch' if ctl else '-'}"
                    f"|{TOOL}|{row_text(n)}")
        sset = "control" if ctl else "heldout"
        if n == "c-e521":
            vals = []
            for p in pairs:
                assert len(kept[p]) == 1, p
                vals.append(next(iter(kept[p])))
            pred.append(line(n, "dwords", fmt(vals), "H-E521", sset,
                             "E521's kept values (vectors), E1061's u-ctl-e521 program"))
            continue
        why = {"c-one-r10": "E1061's u-sa0 pairs into r10, writer quad (0, 0): H-ZX as E1061's u-i0",
               }.get(n, "rank-round26.md 2.2: one writer quad into sa0")
        pred.append(line(n, "dwords", fmt([zx(a, b) for a, b in pairs]), "H-ZX", sset,
                         why + "; E521: (r1 & 0xffff) + source 2"))
        pred.append(line(n, "dwords", fmt([sx(a, b) for a, b in pairs]), "H-SX", sset,
                         "the sign extension of r1's low half (differs from H-ZX in "
                         f"{sum(zx(a, b) != sx(a, b) for a, b in pairs)} of 8 dwords)"))
        if not ctl:
            pred.append(line(n, "mix", ",".join("0x%08x" % zx(a, b) for a, b in pairs), "H-MIX",
                             sset, "E1061's sa0 reading: every dword the H-ZX value of some pair "
                                   "of the row, at least one not its own pair's"))
    return rows, pred


HEADERS = {
    "uc": """#stage uc
#limit 0
# uc (Q126 clause 2, rank-round26.md 2.2): the controls, gate of us. c-e521: E1061's u-ctl-e521 program (eight of E521's pairs
# into r10, every instance, stored) as `probe --coords`: H-E521, E521's kept values, 8 of 8 dwords. c-one-r10: the branch
# form (writer quad (0, 0), `xor.testtaz` of pa0 and `!p0 br` as E513) with E1061's u-sa0 pairs into r10: H-ZX 8 of 8 dwords.
# Stop: a control without its scratch readout (premise), any fault or hang; us is gated by both controls.""",
    "us": """#stage us
#limit 0
# us (Q126 clause 2, rank-round26.md 2.2): six held-out rows, one writer quad alone writes sa0 (iaddu32.testtaz.chan0 sa0,
# then mov r3, sa0 and the store, eight pairs): quad (0, 0) with E1061's pairs (twice) and eight new pairs (twice), quad
# (62, 30) (the plan's (63, 31): E513's branch is decided by the quad's top-left lane) with each set once. Frozen: H-ZX
# against H-SX and H-MIX (per row, per dword). Stop: the second row without its scratch readout, any fault or hang.""",
}


def build():
    files = {}
    for st in ORDER:
        rows, pred = stage(files, st)
        files[f"tables/{st}.txt"] = (HEADERS[st] + "\n" + "\n".join(rows) + "\n").encode()
        files[f"predictions/{st}.tsv"] = "".join(pred).encode()
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for d in ("bins", "tables", "predictions"):
            full = os.path.join(KP, d)
            bad += [f"{d}/{n}" for n in sorted(os.listdir(full)) if f"{d}/{n}" not in files] \
                if os.path.isdir(full) else []
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
