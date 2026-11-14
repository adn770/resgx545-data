# SPDX-License-Identifier: MIT
"""f2.py: stage f2 (r14-flag, Q139 H-EVEN at fx 2 or 3 mod 4; closing14/plan/rank-round14.md
section 2 "F2"; planned faults, user OK R14-5 a). r10-geo q139c's form (E1007): `tri --tri-full
--pixels ... --wait-ms 20000 --keep-going --dump-render "$W"`, the first macrotile's width fx
poked in CR_TE_MTILE1 (`--kpoke-render 1:ta:143=V`), the TA data dumped and its region headers read
from the header base of an unpoked baseline of the same size (score/lib_dump.py, r10-geo's).

The plan's premise "a faulting row still yields its TA dump" does not hold for t10's tri: after a
failed render it breaks before `dump_render` (sgxfive-test.c at a581c06: the dump runs only when
ret is 0; its own comment: recovery resets the TA data). So a planned row decodes only if it draws.
Of the 22 kept jobs at fx 2 or 3 mod 4 (closing9/seeds/q139/fx_status.out, its x-side lines) the
19 that faulted or were cut all have fx below the target's width in tiles, and the 3 that drew
(256 x 256 fx 10 and 11, 640 x 480 fx 23) a first macrotile that covers the target's width; so the
rows here are words of that kind, never run:

  f2-h-256-fx14, -fx15   256 x 256 (8 tiles wide), CR_TE_MTILE1 B2 = 14 and 15 (E950's named
                         held-out fx): H-EVEN and R7-BLK part on the wrong-tile set and the slots
  f2-h-768-fx26, -fx27   768 x 640 (24 tiles wide, n = 4), B1 = 26 and 27: H-EVEN and R7-BLK
                         part, and the flag's two rivals part (the only words found where they do
                         with fx covering the target, fit/f2search.py)

Frozen per row:
  end     H-COVER [infer, post hoc on the 22 kept jobs]: a job at fx 2 or 3 mod 4 draws iff the
          first macrotile covers the target's width (every row: ok); H-FAULT23: it faults (the
          19 kept faults read as fx alone)
  slots   every target tile's surviving header slot and the wrong-tile set (H-PRESENT) under
          H-EVEN (8 floor(fx / 2) slots a block row, E950) and R7-BLK (16 floor(fx / 4), E907)
  flag    the slot of the one header with flag bit 7 and the image's wrong-tile set (a tile drawn
          iff its header lies at or before the flag, E959, E1007) under H-LASTBLOCK (the flag on
          H-EVEN's slot of the last target tile in block order, E1007's H-FLAGSLOT) and
          H-HIGHSLOT (on the highest slot of a target tile's surviving header, E1011's rival)

Controls (first in each size, reads:hash,dump): the 256 x 256 baseline (E1007's
q139c-ctl-256x256) and the 768 x 640 baseline (E959's), unpoked: exact image and one header with
a stream for every target tile (lib_dump.baseline_layout, the header base the rows are read from).
The planned rows are expectfault (#limit 4: a fault there is a reading, H-FAULT23's), with
expectdiff (a wrong image prints `diff:` with `job: ok`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q139_fit as Fit  # noqa: E402
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402

STAGE = "f2"
CMD = ("tri --tri-full --pixels --width {w} --height {h} --max-width {w} --max-height {h}{poke} "
       "--wait-ms 20000 --keep-going --dump-render \"$W\"")
# name, set, w, h, fx (None: the baseline)
ROWS = [
    ("f2-ctl-256", "control", 256, 256, None),
    ("f2-h-256-fx14", "heldout", 256, 256, 14),
    ("f2-h-256-fx15", "heldout", 256, 256, 15),
    ("f2-ctl-768", "control", 768, 640, None),
    ("f2-h-768-fx26", "heldout", 768, 640, 26),
    ("f2-h-768-fx27", "heldout", 768, 640, 27),
]
SLOT_MODELS = ("H-EVEN", "blkrow")
FLAG_MODELS = ("H-LASTBLOCK", "H-HIGHSLOT")
# the kept datasets whose words these rows must not repeat (tests/test_gen.py)
DATASETS = ("data:ta/mtile-fields/output.txt", "data:ta/mtile-fields-risky/output.txt")


def word(w, h, fx):
    """CR_TE_MTILE1 with the first macrotile fx tiles wide: B2 at n = 2, B1 at n = 4 (bits 29:22,
    E877's field order), the rule's other bounds kept."""
    m1, n = Fit.rule(w, h)[5], Fit.rule(w, h)[2]
    if n == 2:
        return (m1 & ~(0xFF << 12)) | fx << 12
    return (m1 & ~(0xFF << 22)) | fx << 22


def args_of(w, h, fx):
    poke = "" if fx is None else " --kpoke-render 1:ta:143=0x%08x" % word(w, h, fx)
    return CMD.format(w=w, h=h, poke=poke)


def kp(w, h, fx):
    return "" if fx is None else "--kpoke-render 1:ta:143=0x%08x" % word(w, h, fx)


def flags(w, h, k):
    """{flag model: (its slot, the image's wrong tiles)} on H-EVEN's surviving headers."""
    pred = E.predict(w, h, k, "H-EVEN")
    key = Q.KEYS["blkrow"]
    n = E.geometry(w, h, k)[0]
    surv = {t: v for t, v in pred.items() if v is not None}
    last = max(surv, key=lambda t: key(t[1], t[0], 0, 0, n))
    out = {}
    for m, sl in (("H-LASTBLOCK", surv[last]), ("H-HIGHSLOT", max(surv.values()))):
        out[m] = (sl, {t for t, v in pred.items() if v is None or v > sl})
    return out


def jobs():
    """[(name, set, knobs, args, {quantity: {model: value}}, {file: text})], run order."""
    out = []
    for name, sset, w, h, fx in ROWS:
        k = kp(w, h, fx)
        q = {"size": {"all": "%dx%d" % (w, h)}, "wrong": {}, "slots": {}}
        files = {}
        for m in SLOT_MODELS:
            pred = E.predict(w, h, k, m)
            q["wrong"][m] = E.tiles_text(E.wrong(pred))
            files["%s.%s.slots" % (name, m)] = E.slots_text(pred) + "\n"
        fs = flags(w, h, k)
        q["flagslot"] = {m: str(fs[m][0]) for m in FLAG_MODELS}
        q["image"] = {m: E.tiles_text(fs[m][1]) for m in FLAG_MODELS}
        if sset == "control":
            q["end"] = {"all": "ok"}
            knobs = "expectdiff reads:hash,dump"
        else:
            q["end"] = {"H-COVER": "ok", "H-FAULT23": "fault"}
            knobs = "expectfault expectdiff"
        out.append((name, sset, knobs, args_of(w, h, fx), q, files))
    return out
