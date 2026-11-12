#!/usr/bin/env python3
"""g_q086.py: stage q086 of r7-rp (plan closing7/a/exp-pixel-r7.md 1.5, 3.7): the axes of H-COV.

E886 (round 6): on four-array 4x contexts a render with poked CR_TE_MTILE1/2 + stride completes exactly when the words' grid covers
the target's 1x tile grid on BOTH axes (H-COV, B3 + B1 tiles per axis); in its 9 rows "covers in x", "covers in y", "at least as many
tiles" fit as well.  Four rows (U2's 12 x 12 grid on 14 x 10, 10 x 14, 13 x 12, 12 x 13 tiles) split H-COV / H-X / H-Y / H-AREA two
against two.  Bridge rows repeat E886's R 1024 x 768, U2 320 x 160 and FX 320 x 160 on the new module (FX must fault; if it completes
the runner stops rc 19: E886 depended on the old module).  Row shape = E886's (r6-misc gen/models.py q086_args).

  write(kp)       tables/q086.txt, predictions/q086.tsv, gen/data/sources-q086.lst, gen/data/bins-q086.txt
  controls(stage) producible(row)   (scorekit.refuse_unreadable)
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score")]
import rules1126 as RU  # noqa: E402
import scorekit  # noqa: E402

STAGE = "q086"
POS = 0xEAA26E26
U2 = {143: 0x01806006, 144: 0x01806006, 146: 0x24}        # E886's U2 words: a 12 x 12 grid
FX = {143: 0x00802002, 144: 0x00802002, 146: 0x4}         # the closed driver's 64 x 64 words (E886's FX row)
SOURCES = ["/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/gen/rules1126.py",
           "/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/gen/models.py",
           "/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/tables/q086.txt"]
MODELS = ("H-COV", "H-X", "H-Y", "H-AREA", "H-ANY")
NEW_SIZES = [(448, 160), (320, 224), (416, 192), (384, 208)]


# ---- the models -------------------------------------------------------------------------------------------------------------
def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def words(w, h, kp):
    """(mtile1, mtile2, stride) the job runs with: the kpoked words over the rule's (R)."""
    r = RU.words(w, h)
    return kp.get(143, r[0]), kp.get(144, r[1]), kp.get(146, r[2])


def coverage(m1, m2):
    f1, f2 = RU.fields1(m1), RU.fields2(m2)
    return f1[3] + f1[1], f2[2] + f2[0]


def completes(model, w, h, kp):
    cx, cy = coverage(*words(w, h, kp)[:2])
    tx, ty = tiles(w, h)
    return {"H-COV": cx >= tx and cy >= ty, "H-X": cx >= tx, "H-Y": cy >= ty,
            "H-AREA": cx * cy >= tx * ty, "H-ANY": True}[model]


def args(w, h, kp):
    a = ("tri --tri-full --keep-going --wait-ms 20000 --pixels --width %d --height %d --max-width %d --max-height %d --aa4 "
         "--poke cmd:1=0xe0000000 --poke cmd:10=0x%x --poke cmd:13=0x80000002 --poke cmd:16=0x%x" % (w, h, w, h, POS, POS))
    for i in sorted(kp):
        a += (" --kpoke-render 1:ta:%d=0x%08x" % (i, kp[i])) if i != 146 else (" --kpoke-render 1:ta:146=0x%x" % kp[i])
    return a


# ---- the rows -----------------------------------------------------------------------------------------------------------------
def spec():
    """(name, set, w, h, kp, knobs, needs): bridges first, then per new size its R control and its poked row."""
    s = [("q086-1024x768-R", "control", 1024, 768, {}, "expectdiff strict", ()),
         ("q086-320x160-U2", "bridge", 320, 160, U2, "expectdiff strict hypo:u:1", ("q086-1024x768-R",)),
         ("q086-320x160-FX", "bridge", 320, 160, FX, "expectdiff strict expectfault hypo:fx:1", ("q086-1024x768-R",))]
    for w, h in NEW_SIZES:
        r = "q086-%dx%d-R" % (w, h)
        s.append((r, "control", w, h, {}, "expectdiff strict", ()))
        s.append(("q086-%dx%d-U2" % (w, h), "heldout", w, h, U2, "expectdiff strict hypo:cov:4",
                  (r, "q086-320x160-FX")))
    return s


def rows_and_preds():
    rows, preds = [], []
    for name, sset, w, h, kp, knobs, needs in spec():
        rows.append("%s|%s|risky|%s|t4|%s" % (name, sset, knobs, args(w, h, kp)))
        m1, m2, st = words(w, h, kp)
        cx, cy = coverage(m1, m2)
        tx, ty = tiles(w, h)
        grp = [k.split(":")[1] for k in knobs.split() if k.startswith("hypo:")]
        preds += [(name, "size", "%dx%d" % (w, h), "all", sset),
                  (name, "words", "0x%08x,0x%08x,0x%x" % (m1, m2, st), "all", sset),
                  (name, "cover", "%d,%d of %d,%d" % (cx, cy, tx, ty), "H-COV", sset)]
        preds += [(name, "class", "ok" if completes(m, w, h, kp) else "fault", m, sset) for m in MODELS]
        preds += [(name, "wrong_if_ok", "0", "all", sset), (name, "group", grp[0] if grp else "-", "all", sset),
                  (name, "needs", ",".join(needs) or "-", "all", sset)]
    return rows, preds


HEAD = ["#stage q086", "#limit 6",
        "# Q086 (r7): E886's row shape on four-array 4x contexts, every pixel read (--pixels); tool t4 (rgn4 build 4623753).",
        "# Bridges (E886 on this module): R 1024 x 768 and U2 320 x 160 complete, FX 320 x 160 faults under every rule (expectfault:",
        "# if it COMPLETES the runner stops rc 19, E886 depended on the old module, the four rows are unscored).",
        "# Then per new size the R control (no hypo: a fault there stops the stage, rc 4) and U2's words (0x01806006 twice, 0x24: a",
        "# 12 x 12 grid) on 14 x 10, 10 x 14, 13 x 12 and 12 x 13 tiles.  Frozen: H-COV (both axes cover: all four fault) against",
        "# H-X (fault, ok, fault, ok), H-Y (ok, fault, ok, fault), H-AREA (ok, ok, fault, fault): each row splits them two against two.",
        "# Budget 6 (FX + 4 predicted = 5): group cov holds 4 (the stage's last rows: no row is skipped), fx 1, u 1; strict health",
        "# after each fault; the fault must be 3D side (BIF_INT_STAT 0x0100, BIF_FAULT 0x100000xx) else rc 18; a -110 stops (rc 18).",
        "# The 11 unrun E886 rows (FX past 320 x 160, HS past 384 x 192) are not pursued, by design: every rule predicts a fault."]


def producible(row):
    """The reading keys a row's job can produce (a --pixels render with --width/--height prints the diff line and every pixel row)."""
    a = row.split("|")[5] if "|" in row else row
    keys = {"class"}
    if "--pixels" in a:
        keys |= {"pixels", "diff"}
    return keys


def controls(stage=STAGE):
    out = []
    for name, sset, w, h, kp, knobs, needs in spec():
        if sset == "control":
            out.append({"name": name, "reads": ["class", "diff", "pixels"]})
        elif name.endswith("FX"):
            out.append({"name": name, "reads": ["class"]})
    return out


def write(kp=KP):
    rows, preds = rows_and_preds()
    by = {r.split("|")[0]: r for r in rows}
    scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), by[c["name"]]) for c in controls()}, producible)
    os.makedirs(os.path.join(kp, "tables"), exist_ok=True)
    os.makedirs(os.path.join(kp, "predictions"), exist_ok=True)
    os.makedirs(os.path.join(kp, "gen", "data"), exist_ok=True)
    with open(os.path.join(kp, "tables", STAGE + ".txt"), "w") as f:
        f.write("\n".join(HEAD + rows) + "\n")
    with open(os.path.join(kp, "predictions", STAGE + ".tsv"), "w") as f:
        f.write("case\tquantity\tvalue\tmodel\tset\n")
        for p in preds:
            f.write("\t".join(p) + "\n")
    with open(os.path.join(kp, "gen", "data", "sources-%s.lst" % STAGE), "w") as f:
        f.write("\n".join(SOURCES) + "\n")
    open(os.path.join(kp, "gen", "data", "bins-%s.txt" % STAGE), "w").close()
    return len(rows)


if __name__ == "__main__":
    print("q086: %d rows" % write())
