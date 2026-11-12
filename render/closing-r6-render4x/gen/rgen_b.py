#!/usr/bin/env python3
"""rgen_b.py (set B): writes everything r6-render4x's stage B generates, before any job: tables/{s0b,b,k,r}.txt,
predictions/{s0b,b,k,kh,r}.tsv, TABLES-B.md, stages-B.txt, gen/data/twins-B.tsv and gen/data/sources-B.lst.  Never reads or writes a
file of set A's freeze (stage A's FROZEN.sha256 stays byte for byte).
  rgen_b.py            write everything (refuses once FROZEN-B.sha256 exists)
  rgen_b.py --check    regenerate into memory and compare with the files on disk
Plan: closing6/render4x/exp-render4x-r6.md section 4 (stage B) on the r6-kernel module (linux fork branch r6-kernel, tip 3f0b3e74:
debugfs render_tail_room, default 0 = automatic, 4 x a 1x context's room for an AA_4X context, a whole number of pages sets the room
of either kind, read at context creation; gen/layout_b.py), decisions R6-3 (a), R6-4 (a) and the plan's decisions 2 (a), 3 (a), 6 (a).
DISCLOSED: frozen AFTER stage A ran (out/20261112-144822): H-TPM held 11 of 11, h1 and h2 lost exactly their frozen sets (43, 511),
TPM-y-rgn the only surviving variant.  Stage B's predictions use H-TPM as stage A left it; no number was fitted on stage A's files.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout_b as B  # noqa: E402
import pbmodel as M  # noqa: E402
import rgen as G  # noqa: E402  (set A's generator, imported for its row forms and readers; never run as main here)
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import twins as TW  # noqa: E402

KP = L.KP
STAGES = ["s0b", "b", "k", "r"]
LIMIT = {"s0b": 1, "b": 2, "k": 4, "r": 1}
SOURCES = []
STAGE_A = "r6-render4x stage A, out/20261112-144822 (H-TPM 11 of 11; h1, h2 set equal)"
# (name, set, W, H, room setting, held, dump, group)
BROWS = [("b9-1024x768", "control", 1024, 768, 0, False, True, None)] + [
    ("b%d-%dx%d" % (i + 1, w, h), "heldout", w, h, 0, False, True, "b:2") for i, (w, h) in enumerate(
        [(1280, 1024), (1184, 768), (1024, 800), (2048, 240), (768, 2048), (2048, 1536), (1280, 768), (1024, 1024)])]
KROWS = [("k1-1280x1024-room4000", "control", 1280, 1024, 0x4000, False, True, "k:4"),
         ("k5-1024x768-room4000", "control", 1024, 768, 0x4000, False, True, "k:4"),
         ("k2-1280x1024-roomb000", "heldout", 1280, 1024, 0xb000, False, True, "k:4"),
         ("k4-1024x768-room3000", "heldout", 1024, 768, 0x3000, False, True, "k:4"),
         ("k3-1280x1024-rooma000-held", "heldout", 1280, 1024, 0xa000, True, False, "k:4")]
RROWS = [("r2-2048x2032", "heldout", 2048, 2032, 0, False, True, None),
         ("r1-4096x960", "explore", 4096, 960, 0, False, False, None),
         ("r3-4096x1152", "explore", 4096, 1152, 0, False, False, None)]
# the rgn4 kernel's outcome of the eight own-maximum cells (b1-b8): every one faulted (E845, E868, E869; stage A's own rows)
RGN4_RECORD = {(1280, 1024): "E845, E869", (1184, 768): "E868 x2", (1024, 800): "E868 x3, stage A h1", (2048, 240): "E868 l1",
               (768, 2048): "E868 l3", (2048, 1536): "E845", (1280, 768): "E868 l4, stage A h2", (1024, 1024): "E868 l5"}


def src(p):
    if p not in SOURCES:
        SOURCES.append(p)
    return p


def t(path):
    return L.read_text(src(path))


def b_(path):
    return L.read_bytes(src(path))


def build():
    st = {n: G.Stage(n) for n in STAGES}
    kh = G.Stage("kh")
    tb = TW.table()
    twin_rows = []

    def need(name, args, knobs):
        got, tw = TW.need_of(args, knobs, tb)
        if got is None or got == "DISAGREE":
            raise SystemExit("BUILD FAILS: %s has no usable twin (%s)" % (name, got))
        for s_, n_, _ in tw:
            src(os.path.join(TW.DATA, "render", os.path.dirname(s_), n_ + ".txt.gz"))
        twin_rows.append(("s0b", name, got, "; ".join("%s/%s" % (s_, n_) for s_, n_, _ in tw)))
        return got, "kept twins (%d): %s" % (len(tw), ", ".join("%s/%s %d" % (s_.split("/out/")[0], n_, p_) for s_, n_, p_ in tw)), tw

    # ---- s0b: r5's three controls with the r6-kernel's TA-data sizes, and the 1x full triangle (TA data as before) --------------
    s = st["s0b"]
    j5 = t(L.RGN4 + "/j5-ctl-1x.out")
    j1r = t(L.RGN4 + "/j1r-aa4-auto.out")
    h8 = t(L.K2 + "/h8-1024x768-k4.txt.gz")
    o10 = L.R5X_A + "/o/o10-1xf-1024x768-p53"
    o10t = t(o10 + ".txt.gz")
    o10ta = len(b_(o10 + ".tri.tadata.bin.gz"))
    s1x = len(b_(L.R5X_A + "/s0/s0-1x-1024x768.tri.tadata.bin.gz"))
    row1xf = ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 1024 --height 768 --max-width 1024 --max-height 768 %s %s'
              % (G.DUMP, G.REGS))
    rows = [("s0b-1x-1024x768", G.row1x(1024, 768), j5, s1x, B.layout(1024, 768, False)["size"], "E827, E828 j5; r5 and stage A s0 PASS; TA data r5's kept s0 dump"),
            ("s0b-1xf-1024x768", row1xf, o10t, o10ta, B.layout(1024, 768, False)["size"], "r5 o10 (E866's 1x full pair: 49 pages, TA data 0x%x)" % o10ta),
            ("s0b-4x-288x144", G.row4x(288, 144), j1r, None, B.layout(288, 144, True)["size"], "E828 j1r, E824 h1; r5 and stage A s0 PASS"),
            ("s0b-4x-1024x768", G.row4x(1024, 768), h8, None, B.layout(1024, 768, True)["size"], "E824 h8; r5 and stage A s0 PASS")]
    for case, args, text, ta_kept, ta_b, source in rows:
        s.row(case, "control", "safe", "expectdiff", args)
        s.pred(case, "rc", 0, "kept", "ctl", source)
        s.pred(case, "echo", L.echo(text), "kept", "ctl", source)
        s.pred(case, "target_hash", L.target_hash(text), "kept", "ctl", source)
        s.pred(case, "diff", L.diff_text(text), "kept", "ctl", source)
        s.pred(case, "tri1", L.tri_counts_text(text), "kept", "ctl", source)
        s.pred(case, "renders", L.renders(text), "kept", "ctl", source)
        if ta_kept is not None:
            assert ta_kept == ta_b, (case, ta_kept, ta_b)
        s.pred(case, "tadata_size", ta_b, "the r6-kernel layout (gen/layout_b.py): %s" % (
            "a 1x context's room is unchanged, so its TA data is the kept size" if "1x" in case else
            "an AA_4X context's room is 4 x the 1x room (rgn4: 0x%x)" % M.tadata_4x(*{"s0b-4x-288x144": (288, 144), "s0b-4x-1024x768": (1024, 768)}[case])),
               "ctl", "gen/layout_b.py; fork 56f8b932")
        n_, why, _ = need(case, args, "expectdiff")
        s.pred(case, "pb_used", n_, why, "ctl", "gen/data/twins-B.tsv")
        G.dump_pred(s, case, args)

    # ---- b, k, r ------------------------------------------------------------------------------------------------------------------
    for stn, lst in (("b", BROWS), ("k", KROWS), ("r", RROWS)):
        q = st[stn]
        for name, sset, w, h, room, held, dump, grp in lst:
            lay = B.layout(w, h, True, room)
            assert lay is not None and w % 32 == 0 and h % 16 == 0
            over = R.u4(w, h) > M.usable(M.PB_PAGES)
            k = ["expectdiff"] + (["room:0x%x" % room] if room else []) + (["held", "dumpheld"] if held else []) + ["strict"] + (["hypo:" + grp] if grp else [])
            args = G.row4x(w, h, dump=dump and not held)
            f = B.fault(w, h, w, h, room)
            q.row(name, sset, "risky", " ".join(k), args)
            G.dump_pred(q, name, args)
            ps = {"control": "ctl", "heldout": "heldout", "explore": "explore"}[sset]
            oc = "overflow" if over and not f else ("fault" if f else "complete")
            rg4 = R.fault(R.HTPM, w, h, w, h)
            why = ("H-TPM (E870; held 11 of 11 in %s) on the r6-kernel layout: entries end 0x%x %s td.rgn 0x%x (room 0x%x%s); on the rgn4 "
                   "layout (td.rgn 0x%x) H-TPM says %s" % (STAGE_A, R.entries_end(w, h), ">" if f else "<=", lay["rgn"], lay["room"],
                                                         ", the knob" if room else ", automatic", R.lay(w, h)["rgn"], "fault" if rg4 else "complete"))
            if over:
                why += "; U4 %d pages > %d usable: -ENOSPC with no BIF line (H-ENOSPC4, E866) [explore at 4096 wide]" % (R.u4(w, h), M.usable(M.PB_PAGES))
            q.pred(name, "outcome", oc, why, ps, "gen/layout_b.py; gen/rules.py")
            if (w, h) in RGN4_RECORD and not room:
                q.pred(name, "rgn4_record", "fault (%s)" % RGN4_RECORD[(w, h)], "the same cell on the rgn4 kernel", "compare", RGN4_RECORD[(w, h)])
            q.pred(name, "entries_end", "0x%x" % R.entries_end(w, h), "4 x (Z(2tx - 1, 2ty - 1) + 1)", "model", "gen/rules.py")
            q.pred(name, "td_rgn", "0x%x" % lay["rgn"], "round_up(room, 4K) + 3 pages", "model", "gen/layout_b.py")
            q.pred(name, "room", "0x%x" % lay["room"], "the knob" if room else "automatic: 4 x 4 side^2", "model", "gen/layout_b.py")
            q.pred(name, "fault_int", "0x0100", "the 3D-side word of every 4x fault on record (E845, E867-E869, stage A)", ps, "E845")
            q.pred(name, "fault_page", "0x10000", "the request base: a zero stream offset (E869)", ps, "E869")
            if oc == "complete":
                q.pred(name, "diff", "0 of %d pixels" % (w * h), "a completed 4x full triangle draws exactly (E824)", ps, "E824")
            if oc == "complete" and dump and not held:
                q.pred(name, "pb_used", R.u4(w, h), "page model U4 (widths a multiple of 32: exact on every kept dump)", "model", "gen/pbmodel.py")
                q.pred(name, "tadata_size", lay["size"], "the r6-kernel layout of the maximum, four arrays", "model", "gen/layout_b.py")
                q.pred(name, "hdr_off", 0, "the doubled-grid rule from the r6-kernel's td.rgn", "model", "gen/layout_b.py")
                q.pred(name, "nonzero_below_rgn", 0, "every completed four-array dump of r5 and stage A is zero below td.rgn", "model", "cells.out; stage A")
            if f:
                lo = B.lost(w, h, w, h, room)
                tgt = kh if held else q
                tgt.pred(name, "lost_count", len(lo), "H-TPM's lost offsets from td.rgn 0x%x" % lay["rgn"], "heldout" if held else "explore", "gen/layout_b.py lost()")
                if held:
                    kh.pred(name, "lost", ",".join("0x%x" % o for o in lo), "H-TPM: the headers of in-target tiles whose word-1 dword is an in-target "
                            "tile's entry lose their stream offset (stage A: 43 of 43, 511 of 511)", "heldout", "gen/layout_b.py lost()")
                    kh.pred(name, "lost_first", "0x%x" % lo[0], "H-TPM", "heldout", "gen/layout_b.py")
                    kh.pred(name, "lost_last", "0x%x" % lo[-1], "H-TPM", "heldout", "gen/layout_b.py")
                    kh.pred(name, "header0_lost", "yes" if lo[0] == lay["rgn"] else "no", "H-TPM", "heldout", "gen/layout_b.py")
                    kh.pred(name, "held_pages", R.u4(w, h), "the TA finished: U4 scene pages in the held parameter dump", "explore", "gen/pbmodel.py")
    return st, kh, twin_rows


TABLE_NOTES = {
    "s0b": ["# s0b: set B's controls on the r6-kernel module: r5's three (the 4x TA data now with 4 x the room), the 1x full triangle",
            "# (r5 o10: TA data as before).  A miss voids set B: every later gate is closed."],
    "b": ["# b: the automatic room (plan section 4).  b9 1024 x 768 is the control (no hypothesis knob: a fault stops the stage); b1-b8",
          "# the eight own-maximum cells that faulted on the rgn4 kernel: predicted complete.  Limit 2: the first fault is the refutation."],
    "k": ["# k: the knob, one page apart.  k1 (0x4000 at 1280 x 1024: the old layout) must fault and k5 (0x4000 at 1024 x 768) complete:",
          "# the controls; k2 (0xb000) completes, k4 (0x3000) and k3 (0xa000, held, the lost set frozen) fault.  Limit 4 (3 predicted)."],
    "r": ["# r: the largest targets (explore the 4096-wide residue): r2 2048 x 2032 (1017 pages), r1 4096 x 960 complete, r3 4096 x 1152",
          "# overflows (-ENOSPC, no fault).  No hypothesis knob: any fault stops the stage.  r1, r3 without dumps (r5-dpm's lesson)."],
}


def write_all(st, kh, twin_rows):
    out = {}
    for n in STAGES:
        s = st[n]
        lines = ["#stage %s" % n, "#limit %d" % LIMIT[n]] + TABLE_NOTES[n]
        for name, sset, risk, knobs, args in s.rows:
            lines.append("|".join([name, sset, risk, knobs, "-", args]))
        out["tables/%s.txt" % n] = "\n".join(lines) + "\n"
    for s in [st[n] for n in STAGES] + [kh]:
        pl = ["case\tquantity\tvalue\tmodel\tset\tsource"]
        for r in s.preds:
            pl.append("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r))
        out["predictions/%s.tsv" % s.name] = "\n".join(pl) + "\n"
    out["stages-B.txt"] = "\n".join(STAGES) + "\n"
    md = ["# r6-render4x stage B (set B): tables and frozen predictions", "",
          "Generated by gen/rgen_b.py; frozen in PREDICTIONS-B.sha256 / FROZEN-B.sha256.  Disclosed: frozen after stage A ran (%s)." % STAGE_A, ""]
    for n in STAGES:
        s = st[n]
        md += ["## %s (%d rows, limit %d)" % (n, len(s.rows), LIMIT[n]), ""]
        for name, sset, risk, knobs, args in s.rows:
            md += ["### %s  (%s, %s) knobs [%s]" % (name, sset, risk, knobs), "", "    " + args, ""]
            for case, q, val, model, ps, source in s.preds + kh.preds:
                if case == name:
                    if q == "lost":
                        val = "%d offsets (predictions/kh.tsv)" % (val.count(",") + 1)
                    md.append("- %s = %s  [%s, %s] (%s)" % (q, val, ps, model, source))
            md.append("")
    out["TABLES-B.md"] = "\n".join(md)
    out["gen/data/twins-B.tsv"] = "\n".join(["stage\tcase\tneed\ttwins"] + ["\t".join(str(x) for x in r) for r in twin_rows]) + "\n"
    return out


def main():
    check = "--check" in sys.argv
    if os.path.exists(os.path.join(KP, "FROZEN-B.sha256")) and not check:
        print("FROZEN-B.sha256 exists: set B's freeze is never rewritten (use --check)")
        return 1
    st, kh, twin_rows = build()
    out = write_all(st, kh, twin_rows)
    out["gen/data/sources-B.lst"] = "".join(p + "\n" for p in sorted(SOURCES))
    bad = 0
    for rel, data in sorted(out.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p).read() != data:
                print("DIFFERS: " + rel)
                bad = 1
        else:
            open(p, "w").write(data)
    print("%s: %d files, %d rows, %d predictions, %d sources" % ("checked" if check else "written", len(out),
          sum(len(s.rows) for s in st.values()), sum(len(s.preds) for s in st.values()) + len(kh.preds), len(SOURCES)))
    return bad


if __name__ == "__main__":
    sys.exit(main())
