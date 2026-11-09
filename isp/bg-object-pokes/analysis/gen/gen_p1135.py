#!/usr/bin/env python3
"""Generator of the 11.35 case tables and the declared predictions (written before any run).
python3 gen/gen_p1135.py -> gen/table-*.txt, declared.tsv, predictions-declared.tsv, hashes.txt

Sets: fit = a case whose outcome an earlier record gave or the poke path's own check; heldout = never
used to adjust a model; control = repeats that must give the control's outcome; explore = no outcome
can fail it (`?`)."""
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent
declared, preds = [], []
def D(case, script, sset, size): declared.append((case, script, sset, size))
def Pr(case, q, v, model): preds.append((case, q, v, model))

# ------------------------------------------------------------------ Q066: bg-words
# The background object of a 64x64 render with the user's PDS words: 17 dwords (SGX_XFER_BGOBJ_DWORDS):
# 0-2 the three PDS state words (the EDM writes them again at the kick, E162), 3-8 zero, 9-16 the
# rectangle's vertices: with x0 = y0 = 0x100000, x1 = y1 = 0x104000 (24-bit fixed point, 8 fraction
# bits, offset 4096): 9 = 0x00100000, 10 = 0x1000, 11 = 0, 12 = 0x10400010, 13 = 0, 14 = 0x00104000,
# 15 = 0x1000, 16 = 0.
DEF = {9: 0x00100000, 10: 0x1000, 11: 0, 12: 0x10400010, 13: 0, 14: 0x00104000, 15: 0x1000, 16: 0}
FLIP_ALL = [0, 3, 7, 8, 15, 16, 24, 31]
FLIP_EDM = [0, 8, 16, 31]
# H66-E: words 0-2 are written by the EDM at the kick, a poke is lost: image == control.
# H66-N: words 3-8 are not read by the ISP: image == control (the null; any change refutes it).
# H66-V: vertex coordinate bits that move an edge by one pixel or more change the image; bits of
# fractions and the zero words are `?`. Word -> bit -> (differs / ?):
VDIFF = {9: {8, 15, 16}, 10: {0, 3, 7, 8, 15, 16}, 12: {16, 24, 31}, 14: {8, 15, 16}, 15: {0, 3, 7, 8, 15, 16},
         11: {24, 31}}
table = []
def case_bg(word, kind, val):
    tag = {"f": "f%d" % val, "z": "z", "o": "o"}[kind] if kind == "f" else kind
    name = "b66-w%02d-%s" % (word, tag)
    if kind == "f":
        spec = "bg:%d^=0x%x" % (word, 1 << val)
    elif kind == "z":
        spec = "bg:%d=0x0" % word
    else:
        spec = "bg:%d=0xffffffff" % word
    return name, spec
for c in (1, 2, 3):
    n = "b66-control-%d" % c
    table.append((n, "control", "tri --pixels --dump-render \"$W/dump\"", None))
    D(n, "bg-words", "control", "64x64")
    Pr(n, "image-vs-control", "same", "control")
    Pr(n, "diff-of-4096", "0", "control")
for word in range(0, 17):
    kinds = [("f", b) for b in (FLIP_EDM if word < 3 else FLIP_ALL)] + [("z", 0), ("o", 0)]
    for kind, val in kinds:
        name, spec = case_bg(word, kind, val)
        table.append((name, "", "tri --pixels --dump-render \"$W/dump\" --kpoke-render 1:" + spec, word))
        if word < 3:
            sset, pred, model = "heldout", "same", "H66-E"
        elif word < 9:
            sset, pred, model = "heldout", "same", "H66-N"
            if kind == "z":            # a zero word set to zero: nothing is poked
                sset = "control"
        else:
            sset, model = "heldout", "H66-V"
            if kind == "f":
                pred = "differs" if val in VDIFF.get(word, ()) else "?"
            elif kind == "o":
                pred = "differs" if word in VDIFF else "?"
            else:
                if DEF[word] == 0:
                    pred, sset = "same", "control"
                else:
                    pred = "differs"
        if pred == "?":
            sset = "explore"
        D(name, "bg-words", sset, "64x64")
        Pr(name, "image-vs-control", pred, model)
        if word >= 3:
            Pr(name, "poke-in-object", "yes", "poke path")   # the kept parameter dump shows the poked word
        else:
            Pr(name, "poke-in-object", "no", "H66-E")
table = [(n, ("heldout" if s == "" else s), a, w) for n, s, a, w in table]
# set column of the table is rewritten from declared
sets = {c: s for c, _, s, _ in declared}
# order of the run: control, the words the EDM rewrites (0-2), the vertices (9-16), a control, the six
# zero words (3-8, the unknown ones, last), a control
def order(item):
    n, _, a, w = item
    if w is None:
        return {"b66-control-1": 0, "b66-control-2": 3, "b66-control-3": 5}[n]
    return 1 if w < 3 else (2 if w >= 9 else 4)
table = sorted(table, key=order)   # stable: the words keep their order inside a group
with open(P / "gen/table-bg-words.txt", "w") as f:
    for n, _, a, w in table:
        f.write("%s|%s|64|64|%s\n" % (n, sets[n], a))

# ------------------------------------------------------------------ Q045: keep-closed
# tri -n 1 --ctx2 --close-first-early: the first context renders (render flags poked with
# --kpoke-render 1:ta:7^=V: bit 2 keeps the DPM owner, bit 3 the owner's deallocation off, E458),
# is closed, the second renders in the same VM. keep = debugfs render_keep armed before the run
# (the first context's close keeps its mappings, slot and memory); ramp = debugfs tadata_fill
# "3 0xa5000000 ramp" armed before it: the first context's state page (page 3 of a 64x64
# context's TA data) holds word i = 0xa5000000 + i at its first render's kick. After the tool
# exits the kept context's TA data is read through debugfs render_kept.
# H45-K: with the closed context's mappings and memory kept the second render is exact (the
# fault of E458 needed the mapping gone). H45-F (the null): it still faults. H45-S: the slot step
# stores the kept owner's DPM state into the kept state page: after the second render the page
# differs from the ramp in 34 dwords (17 lists of 2, as E464's partial store) or fewer; H45-N: the
# page equals the ramp (the step only reads it).
K = [  # (tag, keep, flag xor, ramp, set, copies), in the order they run: the cases that fault last
    ("keep-0", 1, "0x0", 0, "control", 2),
    ("keep-4", 1, "0x4", 0, "heldout", 2),
    ("keep-4-ramp", 1, "0x4", 1, "heldout", 2),
    ("nokeep-c", 0, "0xc", 0, "fit", 2),
    ("keep-c", 1, "0xc", 0, "heldout", 4),
    ("keep-c-ramp", 1, "0xc", 1, "heldout", 3),
]
ktable = []
for tag, keep, flag, ramp, sset, n in K:
    for i in range(1, n + 1):
        name = "k45-%s-%d" % (tag, i)
        ktable.append((name, sset, keep, flag, ramp))
        D(name, "keep-closed", sset, "64x64")
        if keep == 0:
            Pr(name, "second-render", "faults", "E458")
        else:
            Pr(name, "second-render", "exact", "H45-K")
        if keep and ramp:
            if flag == "0xc":
                Pr(name, "state-page-vs-ramp", "changed", "H45-S")
            else:
                Pr(name, "state-page-vs-ramp", "equal", "H45-N")
        if keep:
            Pr(name, "kept-readable", "yes", "render_kept")
with open(P / "gen/table-keep-closed.txt", "w") as f:
    for name, sset, keep, flag, ramp in ktable:
        f.write("%s|%s|%d|%s|%d\n" % (name, sset, keep, flag, ramp))

# ------------------------------------------------------------------ Q076: dirs
# The client directory = the PD word of the newest render context (debugfs render_words ctx:2,
# SGX_RENDER_CTX_PD) against CR_BIF_DIR_LIST_BASE0..15 (0x0c34..0x0c70 in the regs snapshot) read in
# the same second. H76-D: right after a reset the first kick of a VM writes that directory into list 1
# (E360): PD == BASE1, and != BASE15 (the EDM's own). H76-L: the kth render context created after a
# reset since the first (new VM each: a tool process each) has its PD in BASEk. H76-S: two contexts of
# one VM (--ctx2) give the same PD word and have it in BASE1 and BASE2. H76-P: a partial render
# (1024x768 on 0x28 pages) under alias_skip masks 0, 0xc0, 0xdc0: exact image-or-overflow as E464
# and PD == BASE1 (a mask does not change the list).
dtable = []
for i in (1, 2, 3):
    dtable.append(("d76-one-%d" % i, "heldout", "reset", "tri -n 2 --keep-going --wait-ms 6000", "0x0"))
    D("d76-one-%d" % i, "dirs", "heldout", "64x64")
    Pr("d76-one-%d" % i, "pd-in-list", "1", "H76-D")
    Pr("d76-one-%d" % i, "pd-eq-base15", "no", "H76-D")
for k in (1, 2, 3, 4):
    n = "d76-seq-%d" % k
    dtable.append((n, "heldout", "reset" if k == 1 else "noreset", "tri -n 2 --keep-going --wait-ms 6000", "0x0"))
    D(n, "dirs", "heldout", "64x64")
    Pr(n, "pd-in-list", str(k), "H76-L")
for i in (1, 2):
    n = "d76-ctx2-%d" % i
    dtable.append((n, "heldout", "reset", "tri -n 1 --ctx2 --wait-ms 6000", "0x0"))
    D(n, "dirs", "heldout", "64x64")
    Pr(n, "pd-in-list", "1,2", "H76-S")
for mask in ("0x0", "0xc0", "0xdc0"):
    for i in (1, 2):
        n = "d76-part-%s-%d" % (mask, i)
        dtable.append((n, "heldout", "reset", "tri --width 1024 --height 768 --keep-overflow --wait-ms 8000", mask))
        D(n, "dirs", "heldout", "1024x768")
        Pr(n, "pd-in-list", "1", "H76-P")
with open(P / "gen/table-dirs.txt", "w") as f:
    for n, sset, rst, args, mask in dtable:
        f.write("%s|%s|%s|%s|%s\n" % (n, sset, rst, args, mask))

with open(P / "declared.tsv", "w") as f:
    f.write("case\tscript\tset\tsize\n")
    for r in declared:
        f.write("\t".join(r) + "\n")
with open(P / "predictions-declared.tsv", "w") as f:
    f.write("case\tquantity\tvalue\tmodel\n")
    for r in preds:
        f.write("\t".join(r) + "\n")
print(len(declared), "cases,", len(preds), "predictions")
