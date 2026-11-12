#!/usr/bin/env python3
"""g_q287.py: r7-rp's stages s0 (session gate, 4 jobs) and q287 (Q287 odd widths, 25 jobs): tables/{s0,q287}.txt and
predictions/{s0,q287}.tsv, from gen/models_q287.py.  Deterministic.   PY gen/g_q287.py
Table line: name|set|risk|knobs|tool|args       Prediction line: case<TAB>quantity<TAB>value<TAB>model<TAB>set
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import os  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score")]
import models_q287 as M  # noqa: E402
import scorekit  # noqa: E402

# the two screen/viewport poke words of the twins (plan 3.2; checked against sgxfive_drm.h, render.c: cmd:9 = mte_screen,
# blk:6 / blk:7 = vp0 / vp1 = the x half-width scale and offset, 10.0 at W 20): W 19 emulated = x field 18, half width 9.5
POKE_SCREEN = "--poke cmd:9=0x00110012"                      # (H - 1) << 16 | (W - 1), W 19, H 18
POKE_VP = "--poke blk:6=0x41180000 --poke blk:7=0x41180000"   # 9.5f
TWINS = (("z-pk-20x18-scr", POKE_SCREEN, "screen"), ("z-pk-20x18-vp", POKE_VP, "vp"), ("z-pk-20x18-both", POKE_SCREEN + " " + POKE_VP, "both"))


def q287_spec():
    """(name, set, width, ramp, tool, extra knobs, extra args)"""
    s = [("z-dry-33x18", "gate", 33, "x", "t7", "gateodd oddw", "")]
    s += [("z-ctl-34x18-x-t4", "control", 34, "x", "t4", "", ""), ("z-ctl-34x18-x-t6", "control", 34, "x", "t6", "", ""),
          ("z-ctl-34x18-x-t7", "control", 34, "x", "t7", "", ""), ("z-ctl-34x18-y-t7", "control", 34, "y", "t7", "", "")]
    s += [("z-fit-19x18-x-r%d" % r, "fit", 19, "x", "t7", "oddw", "") for r in (1, 2)]
    for w in (7, 11, 23, 35):
        s += [("z-%dx18-x-r%d" % (w, r), "heldout", w, "x", "t7", "oddw", "") for r in (1, 2)]
    s += [("z-%dx18-y" % w, "heldout", w, "y", "t7", "oddw", "") for w in (19, 23, 35)]
    s += [("z-43x18-x", "heldout", 43, "x", "t7", "oddw", ""), ("z-51x18-x", "heldout", 51, "x", "t7", "oddw", "")]
    s += [("z-%dx18-x" % w, "confirm", w, "x", "t7", "oddw", "") for w in (17, 21)]
    for name, extra, _ in TWINS:
        s.append((name, "twin", 20, "x", "t7", "", " " + extra))
    return s


def twin_widths(kind):
    """(H-SCR width, H-VP width) the band uses for a twin: the screen word's W, the viewport's 2 x half width."""
    scr = 19 if kind in ("screen", "both") else 20
    vp = 19 if kind in ("vp", "both") else 20
    return scr, vp


def _summ(preds, name, sset, w, h, rule_models):
    preds.append((name, "size", "%dx%d" % (w, h), "all", sset))
    preds.append((name, "dead", "0", "all", sset))
    preds.append((name, "pitch_tiles", str(M.pitch_tiles()), "all", sset))
    preds.append((name, "pages", str(M.pages(w, h)), "all", sset))
    for model, (wb, hb) in rule_models:
        st = M.band(model, wb, hb) if model in M.RULES else None
        preds.append((name, "stored_count", str(len(st)), model, sset))
        preds.append((name, "stored_set_sha", M.set_sha(st), model, sset))
        preds.append((name, "extent", "%d,%d" % M.G.extent(model, wb, hb), model, sset))


def q287():
    rows, preds = [], []
    H = M.ODD_H
    for name, sset, w, ramp, tool, knobs, extra in q287_spec():
        assert M.band_fits(w), w
        k = ("expectdiff " + knobs).strip()
        rows.append("%s|%s|safe|%s|%s|%s" % (name, sset, k, tool, M.depth_args(w, H, ramp, extra)))
        if sset == "twin":
            kind = [t[2] for t in TWINS if t[0] == name][0]
            sw, vw = twin_widths(kind)
            preds.append((name, "size", "%dx%d" % (w, H), "all", sset))
            preds.append((name, "dead", "0", "all", sset))
            preds.append((name, "pitch_tiles", str(M.pitch_tiles()), "all", sset))
            preds.append((name, "pages", str(M.pages(w, H)), "all", sset))
            for model, bw in (("H-SCR", sw), ("H-VP", vw)):
                st = M.band("A", bw, H)
                preds.append((name, "stored_count", str(len(st)), model, sset))
                preds.append((name, "stored_set_sha", M.set_sha(st), model, sset))
                preds.append((name, "extent", "%d,%d" % M.G.extent("A", bw, H), model, sset))
            preds.append((name, "separates", "yes" if sw != vw else "no", "H-SCR-vs-H-VP", sset))
            continue
        _summ(preds, name, sset, w, H, [(r, (w, H)) for r in M.RULES])
        preds.append((name, "separates", "yes" if M.band("A", w, H) != M.band("FLOOR", w, H) else "no", "A-vs-FLOOR", sset))
        preds.append((name, "tool_accepts", "no" if (tool == "t4" and w % 2) else "yes", "all", sset))
        if sset == "control":
            preds.append((name, "stored_count", "924", "E831", sset))
    head = ["#stage q287", "#limit 1",
            "# Q287 odd WIDTHS at H 18 (round 6 did odd heights at W 34: E885).  E831's g-z row (the full-screen triangle's depth ramp,",
            "# buffer pre-filled 0xdeadbeef, a dword stored iff it is not 1.0f), x ramp, with t7 (resgx545 1c64f3a: the colour row pitch",
            "# is (W + 1) & ~1, so odd widths are accepted); t4 and t6 refuse them.  --depth-pages 18 = the store's extent (2 tile rows x",
            "# 2 tiles at G = 1 x 512 dwords = 2 pages) + 16; the tool's own minimum (W * H dwords) is smaller and not the extent.",
            "# Frozen: rule A (x + 0.5 < 1.25 W) against FLOOR (x < floor(1.25 W)), ROUND, CEIL, RSTRICT, cut at the tile area.",
            "# Separating (A != FLOOR): 19 (fit), 7, 11, 23, 35, 43, 51 (held out; 19, 23, 35 also with the y ramp); .25 cells 17, 21",
            "# (and the gate 33) have A = FLOOR.  Controls that can fail: the gate (33 x 18: A = FLOOR = 902), 34 x 18 with t4, t6, t7",
            "# (E831's 924, rule A's set) and t7's y ramp.  Poke twins at W 20 (t7; they gate nothing): cmd:9 = MTE_SCREEN set to W 19,",
            "# blk:6 / blk:7 = the viewport's x scale / offset set to 9.5 (W 19): the band's W is the screen word's (H-SCR) or twice and a",
            "# half the viewport's half width (H-VP).",
            "# gateodd (the first row): if the module refuses the odd width (`Invalid argument`, rc 1, no `diff:`) every row with knob",
            "# oddw is skipped, the stage exits 21 and the twins still run; any fault or hang stops the stage (rc 4)."]
    return head, rows, preds


def s0():
    rows, preds = [], []
    for t in ("t4", "t6", "t7"):
        n = "s0-tri-" + t
        rows.append("%s|control|safe|expectdiff|%s|tri" % (n, t))
        preds.append((n, "size", "64x64", "all", "control"))
        preds.append((n, "diff", "0 of 4096", "all", "control"))
    n = "s0-z-ctl-34x18-y-t4"
    rows.append("%s|control|safe|expectdiff|t4|%s" % (n, M.depth_args(34, 18, "y")))
    preds.append((n, "size", "34x18", "all", "control"))
    preds.append((n, "dead", "0", "all", "control"))
    preds.append((n, "pitch_tiles", str(M.pitch_tiles()), "all", "control"))
    preds.append((n, "pages", str(M.pages(34, 18)), "all", "control"))
    st = M.band("A", 34, 18)
    preds.append((n, "stored_count", str(len(st)), "A", "control"))
    preds.append((n, "stored_count", "924", "E831", "control"))
    preds.append((n, "stored_set_sha", M.set_sha(st), "A", "control"))
    head = ["#stage s0", "#limit 0",
            "# Session gate (the driver stops, exit 40, on a miss): the default 64 x 64 triangle with t4, t6 and t7 draws exactly (diff 0 of 4096), and",
            "# E831's z-ctl-34x18-y with t4 stores 924 dwords, rule A's set (so a t7 that changed an even width would show at q287's",
            "# t7 controls, and the module on this boot still stores E831's band)."]
    return head, rows, preds


STAGES = {"s0": s0, "q287": q287}


def producible(row):
    a = row["args"]
    keys = {"diff"}
    if "--depth-dump" in a and "--depth-pages" in a and "--depth" in a.split():
        keys |= {"stored_count", "stored_set_sha", "dead", "extent"}
    return keys


def controls(stage):
    if stage == "s0":
        return [dict(name="s0-tri-" + t, reads=["diff"]) for t in ("t4", "t6", "t7")] + \
            [dict(name="s0-z-ctl-34x18-y-t4", reads=["stored_count", "stored_set_sha"])]
    if stage == "q287":
        return [dict(name=n, reads=["stored_count", "stored_set_sha"]) for n in
                ("z-dry-33x18", "z-ctl-34x18-x-t4", "z-ctl-34x18-x-t6", "z-ctl-34x18-x-t7", "z-ctl-34x18-y-t7")]
    return []


def write(kp=KP):
    for st, fn in STAGES.items():
        head, rows, preds = fn()
        byname = {}
        for ln in rows:
            n, s, r, k, t, a = ln.split("|", 5)
            byname[n] = dict(name=n, set=s, risk=r, knobs=k, tool=t, args=a)
        scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), byname[c["name"]]) for c in controls(st)}, producible)
        with open(os.path.join(kp, "tables", st + ".txt"), "w") as f:
            f.write("\n".join(head + rows) + "\n")
        with open(os.path.join(kp, "predictions", st + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\n")
            for p in preds:
                f.write("\t".join(p) + "\n")
    os.makedirs(os.path.join(kp, "gen", "data"), exist_ok=True)
    with open(os.path.join(kp, "gen", "data", "sources-q287.lst"), "w") as f:
        f.write("/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/gen/r3_geo.py\n")
    with open(os.path.join(kp, "gen", "data", "bins-q287.txt"), "w") as f:
        f.write("# q287 and s0 generate no bins/ file\n")


if __name__ == "__main__":
    write(KP)
    print("tables:", ", ".join("%s %d" % (s, sum(1 for ln in open(os.path.join(KP, "tables", s + ".txt")) if not ln.startswith("#")))
                               for s in STAGES))
