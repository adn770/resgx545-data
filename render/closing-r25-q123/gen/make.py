#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r25-q123's generator (round 24's plan, closing24/plan/rank-round24.md sections 2.3
and 5, R24-4 a). Writes tables/STAGE.txt, predictions/STAGE.tsv and the programs bins/NAME.bin
(+ bins/NAME.s for the ones this session assembles), every input read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stages, in run order (each control first, on_stop end):
  q123s  the code step held out: E492's read and jump programs at E492's 0x300008 (control, link
         0x3) and at four new placements whose links the 0x80000 step predicts and every other
         candidate (0x20000, 0x40000, 0x100000: the powers of two fitting five or more of the ten
         old links; no step) gets wrong
  q123w  indices 256 to 8191 held out: E1098's c-lapc (control, word 590), then an 8192-word
         program at 0x40000 with a lapc (six) or a ba (four) to ten target words drawn by
         gen/q123.py's SEED (256 and 8191 included)
Inputs: RESGX545_DATA, RESGX545_MAIN (tools/usse-asm: probe.py's assembler)."""
import os
import pathlib
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402
import q123 as Q  # noqa: E402

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

TOOL = "t22"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("q123s", "q123w")

PM = "data:usse/place-more/"
E492_READ = PM + "usse-place-more-read-300008/bins/p25_link_read.bin"
E492_JUMP = PM + "usse-place-more-jump-300008/bins/p25_link_jump.bin"
R23 = "data:render/closing-r23-pk/bins/"
E1098_CLAPC = R23 + "c-lapc.bin"
E1098_BASE = R23 + "q123-base.bin"


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def asm(text, isa="usse"):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, isa)
        return f.read_bytes()


def row(name, st, knobs, off, prog):
    return (f'{name}|{st}|safe|{knobs}|{TOOL}|probe --temps 32 --place 0x{off:x}="$S/bins/{prog}.bin" '
            f'--place-form cbase "$S/bins/q123-base.bin"')


def e492_program(kind):
    """E492's program, byte for byte, then pads to Q.SPAN words (a stray landing names itself)"""
    b = pins.blob(E492_READ if kind == "read" else E492_JUMP)
    n = len(b) // 8
    tail = "\n".join(Q.pad(k) for k in range(n, Q.SPAN)) + "\n"
    # the pads are assembled on their own (their words do not depend on position)
    return b + asm(Q.PHAS + "\n" + tail)[8:]


def q123s(files):
    rows, pred = [], [HEAD]
    for kind in ("read", "jump"):
        files[f"bins/e492-{kind}.bin"] = e492_program(kind)
    for off in (Q.CONTROL_OFF,) + Q.NEW:
        ctl = off == Q.CONTROL_OFF
        st = "control" if ctl else "heldout"
        models = Q.step_models(off)
        if ctl:
            models = {"H-STEP80000": models["H-STEP80000"]}
        for kind in ("read", "jump"):
            name = f"{'c' if ctl else 's'}-{kind}-{off:06x}"
            want = models["H-STEP80000"]
            knobs = f"reads:o0,placed o0:{want:08x}" if ctl else "-"
            rows.append(row(name, st, knobs, off, f"e492-{kind}"))
            src = (f"rank-round24.md 2.3; E492's {kind} program at 0x{off:x} (cbase); "
                   "link = (X mod step) / 8 + 2, 18 bits")
            for m, v in models.items():
                pred.append(line(name, "o0", f"0x{v:08x}", m, st, src))
            pred.append(line(name, "placed", f"{Q.SPAN}/{Q.SPAN}", "H-PLACED", st,
                             "t22: placed words read back as built"))
    return rows, pred


def q123w(files):
    rows, pred = [], [HEAD]
    files["bins/q123-base.bin"] = pins.blob(E1098_BASE)
    files["bins/c-lapc.bin"] = pins.blob(E1098_CLAPC)
    idx0 = Q.WOFF // 8
    rows.append(row("c-lapc", "control", f"reads:o0,placed o0:{Q.PAD | 590:08x}", Q.WOFF,
                    "c-lapc"))
    pred.append(line("c-lapc", "o0", f"0x{Q.PAD | 590:08x}", "H-INDEX", "control",
                     "E1098's c-lapc repeated: lapc at 0x40000 (cbase), 600 words, word 590"))
    pred.append(line("c-lapc", "placed", "600/600", "H-PLACED", "control",
                     "t22: placed words read back as built"))
    for kind, t in Q.draw():
        name = f"w-{kind}-{t:04d}"
        text = "\n".join(Q.placed(kind, Q.WN, t, idx0)) + "\n"
        files[f"bins/{name}.s"] = text.encode()
        files[f"bins/{name}.bin"] = asm(text)
        rows.append(row(name, "heldout", "-", Q.WOFF, name))
        src = (f"rank-round24.md 2.3; {kind} at 0x{Q.WOFF:x} (cbase), {Q.WN} words, target word "
               f"{t} (index 0x{idx0 + t:x}); drawn by seed 0x{Q.SEED:x} (gen/q123.py draw)")
        for m, v in Q.word_models(t).items():
            pred.append(line(name, "o0", f"0x{v:08x}", m, "heldout", src))
        pred.append(line(name, "placed", f"{Q.WN}/{Q.WN}", "H-PLACED", "heldout",
                         "t22: placed words read back as built"))
    return rows, pred


HEADERS = {
    "q123s": """#stage q123s
#limit 0
# q123s (Q123, rank-round24.md 2.3, R24-4 a): the code step held out. E492's read and jump programs byte for byte, then
# pads (0xb0000000 | word), at E492's 0x300008 (controls first, link 0x3, as E492) and at 0x0c3010, 0x2ca7f8, 0x3d0100,
# 0x1c8008, chosen so that 0x20000, 0x40000, 0x100000 (each fitting five or more of E476's and E492's ten links) and no
# step at all predict another link. Frozen H-STEP80000 (o0 = (X mod 0x80000) / 8 + 2, read and jump) against each.
# Stop: a control off its frozen o0, placed words not read back as built, any fault or hang (on_stop end).""",
    "q123w": """#stage q123w
#limit 0
# q123w (Q123, rank-round24.md 2.3, R24-4 a): indices 256 to 8191 held out. E1098's c-lapc first (control, 600 words at
# 0x40000, word 590), then an 8192-word program at 0x40000 (in step) with a lapc (six) or a ba (four) to target words
# drawn by seed 0x25123 from 256 to 8191 (both included); every other word a pad naming itself, the heap base 256 pads
# (0xc0de0000 | word). Frozen H-INDEX (the target word) against H-WRAP256 (the heap base's word t & 0xff).
# Stop: a control off its frozen o0, placed words not read back as built, any fault or hang (on_stop end).""",
}


def build():
    assert Q.multiples_fitting_all() == [Q.STEP], "the ten old links fit 0x80000 only (E1098)"
    for off in Q.NEW:
        m = Q.step_models(off)
        assert all(v != m["H-STEP80000"] for k, v in m.items() if k != "H-STEP80000"), hex(off)
        assert off % 8 == 0 and off % Q.STEP >= 0x40000 and off % 0x100000 >= Q.STEP
    files = {}
    stages = {"q123s": q123s(files), "q123w": q123w(files)}
    for st in ORDER:
        rows, pred = stages[st]
        files[f"tables/{st}.txt"] = (HEADERS[st] + "\n" + "\n".join(rows) + "\n").encode()
        files[f"predictions/{st}.tsv"] = "".join(pred).encode()
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
