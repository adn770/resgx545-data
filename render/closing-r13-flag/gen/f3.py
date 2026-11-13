# SPDX-License-Identifier: MIT
"""f3.py: stage f3 (r13-flag, Q163 VDM_STATE1 bits 11:9 hang sequences; closing13/plan/
rank-round13.md section 2 "F3"; hangs the kernel recovers, user OK R13-4 a). Built on the kit
words `noreset` (no GPU reset before the row: it starts from the state the row before left) and
`idle:S` (resgx545 0493e36). Two job forms:

  2blk   E700's two-block stream (probe --tri pixel, 12 vertices, two objects of 6, p1131-blue
         and p1131-green, the second block marked by --obj2-blk 6 and 2), bits 11:9 of block 1's
         state word set to v1 by `--vdm 1^=`, block 2's to v2 by `--vdm 9^=` (word 9: 0x0a022405,
         bits 7:0 = 5, the grid's completing value; xor (v ^ 2) << 9, v = 2 the plain word)
  1blk   E413's one-triangle library job (`tri --poke vdm:1^=0xa00`: one block at v = 7), 64 x 64,
         or 128 x 128 for the shape row (`--width 128 --height 128`)

E700's counter, frozen (M1; E1021 held it out for v 3 to 7): c = 0 after a GPU reset or a hang; a
job adds the sum over its blocks of g(v) = v - 2 (g(1) = -1, g(0) = 0); it hangs iff c + add > 8; a
completed job keeps c. The health fill and triangle, a fill and the plain triangle add 0 (E413:
the alternation runs across the unpoked control) [infer]. Frozen per row (model: the whole run
order replayed, the kit's semantics: a row without noreset is reset first, a hang is reset after):

  M1           E700's counter as above
  M3           E701's post hoc variant: a block-2 v = 1 job hangs at c = 0 (otherwise M1); with the
               grid's bits 7:0 at 5 this is E1021's [infer] reading "the grid's bits decide, and c
               = 0 hangs" (rows 4 to 7 completed at c 1 to 4)
  H-C05        c decides: a block-2 v = 1 job hangs at c = 0 and at c = 5 (E1021's three c = 5
               hangs read as c, whatever the grid's bits) [post hoc]
  H-SHAPE      the 128 x 128 one-block pair: the second job completes (the counter's threshold or
               step is the stream's, not the word's)
  H-DECAY      60 s idle before the second v = 7 job clears c: it completes
  H-FILLCLR    a fill job between the two clears c: the second completes
  H-RESETKEEP  a debugfs reset that follows no hang leaves c: the second hangs
  H-HEALTHCLR  the kit's health fill and triangle between the two clear c: the second completes

Each clause rival is M1 elsewhere. The control that can fail (first): E413's v = 7 pair, the second
job must hang (E413, 55 of 55 alternating); if it completes, the counter is not there to read and
hook_check stops the stage (24). Planned rows (expectfault, #limit 8): the eight rows whose end is
a reading; the last of them is the stage's last row. Every other row (the opening jobs of each
sequence, the fill and the plain triangle between) must complete: a hang there stops the stage (4)."""

STAGE = "f3"
GREEN = "data:render/closing-r6-render4x/bins/p1131-green__0.bin"
GREEN_SRC = "resgx545:probes/ta/templates/pix_green.s"
OP_SRC = "resgx545:probes/ta/templates/pix_op.s"
PROGS = "resgx545:probes/ta/p1131-progs.toml"
BLUE_OP = "mov.skipinv.end o0, #0xFF0000FF"
LIMIT = 8

TWO = ('probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 '
       '--obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/bins/p1131-green__0.bin"')
BLUE = '"$S/bins/p1131-blue__0.bin"'


def xor(v):
    return (v ^ 2) << 9


def two(v1, v2):
    w = "".join(f" --vdm {n}^=0x{xor(v):08x}" for n, v in ((1, v1), (9, v2)) if v != 2)
    return f"{TWO}{w} {BLUE}"


def one(v, size=64):
    s = f" --width {size} --height {size}" if size != 64 else ""
    return f"tri{s} --poke vdm:1^=0x{xor(v):x}"


# name, set, knobs, args, job: ("2blk", v1, v2) | ("1blk", v, size) | ("fill",) | ("plain",)
ROWS = [
    ("f3-c-a", "prime", "-", one(7), ("1blk", 7, 64)),
    ("f3-c-b", "control", "noreset expectfault reads:job", one(7), ("1blk", 7, 64)),
    ("f3-v1c0", "heldout", "expectfault", two(2, 1), ("2blk", 2, 1)),
    ("f3-v1c2-p", "prime", "-", two(4, 2), ("2blk", 4, 2)),
    ("f3-v1c2", "heldout", "noreset expectfault", two(2, 1), ("2blk", 2, 1)),
    ("f3-v1c5-p", "prime", "-", two(7, 2), ("2blk", 7, 2)),
    ("f3-v1c5", "heldout", "noreset expectfault", two(2, 1), ("2blk", 2, 1)),
    ("f3-shape-a", "prime", "-", one(7, 128), ("1blk", 7, 128)),
    ("f3-shape-b", "heldout", "noreset expectfault", one(7, 128), ("1blk", 7, 128)),
    ("f3-idle-a", "prime", "-", one(7), ("1blk", 7, 64)),
    ("f3-idle-b", "heldout", "noreset idle:60 expectfault", one(7), ("1blk", 7, 64)),
    ("f3-fill-a", "prime", "-", one(7), ("1blk", 7, 64)),
    ("f3-fill-m", "between", "noreset", "fill", ("fill",)),
    ("f3-fill-b", "heldout", "noreset expectfault", one(7), ("1blk", 7, 64)),
    ("f3-rst-a", "prime", "-", one(7), ("1blk", 7, 64)),
    ("f3-rst-m", "between", "-", "tri", ("plain",)),
    ("f3-rst-b", "heldout", "noreset expectfault", one(7), ("1blk", 7, 64)),
    ("f3-hl-a", "prime", "after", one(7), ("1blk", 7, 64)),
    ("f3-hl-b", "heldout", "noreset expectfault", one(7), ("1blk", 7, 64)),
]
MODELS = ("M1", "M3", "H-C05", "H-SHAPE", "H-DECAY", "H-FILLCLR", "H-RESETKEEP", "H-HEALTHCLR")
# the rows each model is scored on (its own clause; M1 and M3, M1 with E701's v = 1 clause,
# on every held-out row)
HELD = tuple(n for n, s, _, _, _ in ROWS if s == "heldout")
CLAUSE = {"M3": HELD, "H-C05": ("f3-v1c0", "f3-v1c2", "f3-v1c5"),
          "H-SHAPE": ("f3-shape-b",), "H-DECAY": ("f3-idle-b",), "H-FILLCLR": ("f3-fill-b",),
          "H-RESETKEEP": ("f3-rst-b",), "H-HEALTHCLR": ("f3-hl-b",)}


def g(v):
    return -1 if v == 1 else 0 if v == 0 else v - 2


def simulate(model):
    """{row: "ok" or "hang"} of the run order under one model."""
    c, out = 0, {}
    for name, _, knobs, _, job in ROWS:
        words = knobs.split()
        if "noreset" not in words:
            c = 0
        if any(w.startswith("idle:") for w in words) and model == "H-DECAY":
            c = 0
        kind = job[0]
        if kind == "fill":
            if model == "H-FILLCLR":
                c = 0
            out[name] = "ok"
            continue
        if kind == "plain":
            out[name] = "ok"
            continue
        blocks = (job[1], job[2]) if kind == "2blk" else (job[1],)
        add = sum(g(v) for v in blocks)
        hang = c + add > 8
        if kind == "2blk" and job[2] == 1:
            if model == "M3" and c == 0:
                hang = True
            if model == "H-C05" and c in (0, 5):
                hang = True
        if kind == "1blk" and job[2] == 128 and model == "H-SHAPE" and name.endswith("-b"):
            hang = False
        if name == "f3-rst-b" and model == "H-RESETKEEP":
            hang = c + 5 + add > 8          # the reset before f3-rst-m kept f3-rst-a's 5
        out[name] = "hang" if hang else "ok"
        c = 0 if hang else c + add
        if "after" in words and model == "H-HEALTHCLR":
            c = 0
    return out


def predictions():
    """{row: {model: end}}: every model's end for the rows it is scored on (M1 on all), and the
    control's and the opening rows' ends under M1."""
    sims = {m: simulate(m) for m in MODELS}
    out = {}
    for name, sset, _, _, _ in ROWS:
        p = {"M1": sims["M1"][name]}
        for m, rows in CLAUSE.items():
            if name in rows:
                p[m] = sims[m][name]
        out[name] = p
    return out


def blue_text(blob):
    return blob(OP_SRC).decode().replace("{OP}", BLUE_OP)


def planned():
    return [n for n, s, k, _, _ in ROWS if "expectfault" in k.split() and s != "control"]
