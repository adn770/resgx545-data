# SPDX-License-Identifier: MIT
"""q139c.py: stage q139c (round 10 seeds plan section 12, S10-geo, Q139): TA dumps of the four
y-side macrotile words of ta/mtile-fields-risky that drew a whole image, with the 256 x 256 and
640 x 480 baselines as controls. r9-lgeo's q139b form (`tri --tri-full --pixels ... --wait-ms
20000 --keep-going --dump-render "$W"`, needhash, the controls reading hash and dump).

Safe class (decision R10-3 (a), the lead's condition): each word drew whole and never faulted in
any kept job (tests/test_gen.py reads every kept job of the pinned data that ran it):
  0x0200a008 256 x 256  ta/mtile-fields-risky q100-256x256-m2-B2-10 (job: ok, 12288 sentinel
                        pixels) and render/closing-r7-rp q139-f-256x256-m2-B2-10 (t4, job: ok,
                        dumped: E907's fit row)
  0x0200b008 256 x 256  ta/mtile-fields-risky q100-256x256-m2-B2-11 (job: ok)
  0x0280a00a 256 x 256  ta/mtile-fields-risky q100-256x256-part2-10_10_10 (job: ok) and
                        render/closing-r7-rp q139-h-256x256-part2-10_10_10 (t4, job: ok, dumped:
                        E907's held-out row)
  0x05c10018 640 x 480  ta/mtile-fields-risky q100-640x480-m2-B1-23 (job: ok)
No other kept job of resgx545-data (1324301be) names these words.

The seeds plan called the four words never dumped: two of them were (r7-rp, E907, R7-BLK's slots
held there 128 of 128), so those two rows are replicates, and m2-B2-11 (fy 11) and 640 x 480
m2-B1-23 (fy 23, n 4) are the held-out rows. At these words fx is 4 and 8 (the default x words),
so H-EVEN = R7-BLK (blkrow), and every model's wrong-tile set but blkdown's and mtblk's is the
dataset's (debug/q139_check.py). The plan's H-EVENY (a y analogue of H-EVEN) has no form in the
slot rule that differs from R7-BLK on these rows and agrees with E907's fy-10 dumps, so it is not
frozen (README.md "Deviations").

Frozen per row (gen/q139even.py, r9-lgeo's, a byte copy):
  slots      every target tile's surviving header slot under H-EVEN, blkrow, raster, blkdown,
             mtblk (predictions/q139c/NAME.MODEL.slots), and the wrong-tile set of each
  H-LAST     (E959's post hoc reading, held out here) exactly one header has flag bit 7, and a
             target tile is drawn iff a header with a stream naming it lies at or before that
             slot: scored per tile on the row's own dump and image
  H-FLAGSLOT the flagged header is at the slot H-EVEN gives the last target tile in block order
             (E959's model side), and H-EVEN + H-LAST's wrong-tile set
  kept       the dataset's wrong-tile set (a replicate)"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402

STAGE = "q139c"
CMD = ("tri --tri-full --pixels --width {w} --height {h} --max-width {w} --max-height {h}{poke} "
       "--wait-ms 20000 --keep-going --dump-render \"$W\"")
# name, set, w, h, the word (None: the baseline), the dataset case
ROWS = [
    ("q139c-ctl-256x256", "control", 256, 256, None, None),
    ("q139c-ctl-640x480", "control", 640, 480, None, None),
    ("q139c-rep-256x256-m2-B2-10", "replicate", 256, 256, 0x0200a008, "q100-256x256-m2-B2-10"),
    ("q139c-rep-256x256-part2-10_10_10", "replicate", 256, 256, 0x0280a00a,
     "q100-256x256-part2-10_10_10"),
    ("q139c-h-256x256-m2-B2-11", "heldout", 256, 256, 0x0200b008, "q100-256x256-m2-B2-11"),
    ("q139c-h-640x480-m2-B1-23", "heldout", 640, 480, 0x05c10018, "q100-640x480-m2-B1-23"),
]
SAFE_WORDS = {0x0200a008: (256, 256), 0x0200b008: (256, 256), 0x0280a00a: (256, 256),
              0x05c10018: (640, 480)}
DATASET = "data:ta/mtile-fields-risky/output.txt"


def args_of(w, h, word):
    poke = "" if word is None else " --kpoke-render 1:ta:144=0x%08x" % word
    return CMD.format(w=w, h=h, poke=poke)


def kpokes(args):
    return " ".join("--kpoke-render " + x for x in re.findall(r"--kpoke-render (\S+)", args))


def dataset_wrong(output, case):
    """The dataset's wrong tiles ({(c, r)}) of a case, from its `tiles R: ...` lines."""
    blk = output.split("== " + case + " ")[1].split("\n== ")[0]
    if "job: ok" not in blk.splitlines()[1]:
        raise ValueError(case + ": not a whole image in the dataset")
    return {(c, int(r)) for r, s in re.findall(r"tiles +(\d+): (\S+)", blk)
            for c, ch in enumerate(s) if ch != "g"}


def flag_slot(w, h, args):
    """(H-EVEN's slot of the last target tile in block order, H-EVEN + H-LAST's wrong tiles)."""
    pred = E.predict(w, h, args, "H-EVEN")
    key = Q.KEYS["blkrow"]
    n = E.geometry(w, h, args)[0]
    last = max((t for t, v in pred.items() if v is not None), key=lambda t: key(t[1], t[0], 0, 0, n))
    return pred[last], {t for t, v in pred.items() if v is None or v > pred[last]}


def jobs(output):
    """[(name, set, knobs, args, {quantity: {model: value}}, {file: text})]"""
    out = []
    for name, sset, w, h, word, case in ROWS:
        args = args_of(w, h, word)
        kp = kpokes(args)
        q = {"size": {"all": "%dx%d" % (w, h)}, "wrong": {}}
        files = {}
        for m in E.MODELS:
            pred = E.predict(w, h, kp, m)
            q["wrong"][m] = E.tiles_text(E.wrong(pred))
            files["%s.%s.slots" % (name, m)] = E.slots_text(pred) + "\n"
        fs, lw = flag_slot(w, h, kp)
        q["flagslot"] = {"H-FLAGSLOT": str(fs)}
        q["wrong"]["H-FLAGSLOT"] = E.tiles_text(lw)
        if case:
            q["wrong"]["kept"] = E.tiles_text(dataset_wrong(output, case))
        knobs = "expectdiff needhash" + (" reads:hash,dump" if sset == "control" else "")
        out.append((name, sset, knobs, args, q, files))
    return out
