#!/usr/bin/env python3
"""kgen.py: regenerate tables/, predictions/, TABLES.md, stages.txt, conditional.txt of R3K-pixel (kernel-batch session K2:
pixel and fault rows on the new gma500 module).  Run from anywhere; writes inside this directory only.  Then run/freeze_k.sh
freeze.  Frozen quantities come from records and from the kernel's layout formula (closing3/kernel/layout_f4.py), never from
the runs:

  k-f4   (Q140, decision R3-K6): the four-array layout.  render_rgn_arrays = 4 for the held-out rows, 1 for everything else.
         Held out: 8 sizes; controls c1 (E729's fault, held, last), c2 (4 at 64x64), c3 (1 at 64x64).  The layout model
         (klib.layout(w, h, f)) fits 19 of 19 rows on record POST HOC (layout_f4.out); the rows here are the held-out part.
  k-pb0  (Q285, decision R3-K7, controls): the split flow (-n 2 --geometry 1) at TE 0x60 (the twin), TE 0x40 (E728's empty
         image) and the dump run (TE 0x40, the parameter buffer from dword 0).
  k-pb   (Q285, the pokes into the parameter buffer between the TA and the 3D by the kernel's par space): p2 (its own value),
         p3 x2 (the twin's 16 dwords 11-26), p4 x2 (dword 11 = 0xffffffff).  Runs only if k-pb0's controls passed.
  k-bif  (Q003 "what clears", decision R3-K4): n0 (idle), f1, f1r (E444's TA read), f2 (E788's a6 at knob 1), f3 (S3's texture
         fetch); the four kregnow writes with a regs read after each, then a 2.5 s watch, then the kernel's reset.
"""
import hashlib
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import klib as L  # noqa: E402

TE_E0 = "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"


def te_words(te):
    return "--poke cmd:1=%s --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26" % te


def tri_f4(w, h):
    return ("tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d %s "
            '--dump-render "$W/dump"' % (w, h, w, h, TE_E0))


def tri_pb(te, pokes=()):
    ks = "".join(" --kpoke-render 2:par:%d=0x%08x" % (i, v) for i, v in pokes)
    return ("tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 -n 2 --geometry 1 "
            '%s%s --dump-render "$W/dump"' % (te_words(te), ks))


PROBE_TEX = 'probe --temps 32 --coords --pixels --scratch-pages 16 "$S/s1d-tw64x64-l2e2__0.bin"'

# ---- k-f4 -----------------------------------------------------------------------------------------------------------
F4_HELD = [("h1-288x144-k4", 288, 144), ("h2-256x288-k4", 256, 288), ("h3-384x384-k4", 384, 384), ("h4-320x160-k4", 320, 160),
           ("h5-512x384-k4", 512, 384), ("h6-640x480-k4", 640, 480), ("h7-320x400-k4", 320, 400), ("h8-1024x768-k4", 1024, 768)]
F4_SIZES = {"h1-288x144-k4": 0x8000, "h2-256x288-k4": 0x8000, "h3-384x384-k4": 0xb000, "h4-320x160-k4": 0x8000,
            "h5-512x384-k4": 0xb000, "h6-640x480-k4": 0x13000, "h7-320x400-k4": 0xc000, "h8-1024x768-k4": 0x1e000}


def f4_rows():
    rows = [("c3-64x64-k1", "control", "safe", "rgn:1 expectdiff", tri_f4(64, 64), 64, 64, 1),
            ("c2-64x64-k4", "control", "safe", "rgn:4 expectdiff", tri_f4(64, 64), 64, 64, 4)]
    for n, w, h in F4_HELD:
        cmd = tri_f4(w, h)
        if n.startswith("h8"):
            cmd = cmd.replace("--keep-going", "--keep-going --keep-overflow")
        rows.append((n, "heldout", "risky", "rgn:4 expectdiff hypo:h4:2", cmd, w, h, 4))
    rows.append(("c1-288x144-k1", "control", "risky", "held rgn:1 expectdiff hypo:c1:1", tri_f4(288, 144), 288, 144, 1))
    return rows


def f4_preds(rows):
    out = []
    for n, sset, risk, knobs, cmd, w, h, f in rows:
        lay = L.layout(w, h, f)
        if n.startswith("c1"):
            out += [(n, "outcome", "fault", "F4", "control"), (n, "fault_word", "0x90004", "F4", "control"),
                    (n, "fault_page", "0x20006", "F4", "control"), (n, "max_echo", "%dx%d" % (w, h), "F4", "control")]
            continue
        want = F4_SIZES.get(n, 0x6000)
        assert lay["size"] == want, (n, hex(lay["size"]), hex(want))
        s = "control" if sset == "control" else "heldout"
        out += [(n, "outcome", "complete", "F4", s), (n, "diff", "0 of %d" % (w * h), "F4", s),
                (n, "max_echo", "%dx%d" % (w, h), "F4", s), (n, "tadata_size", hex(lay["size"]), "F4", s),
                (n, "slots_written", "4", "F4", s), (n, "rgn", hex(lay["rgn"]), "F4", s), (n, "rgn_size", hex(lay["rgn_size"]), "F4", s),
                (n, "below_rgn", "0", "F4", s)]
        if n.startswith("h"):
            # the knob's proof: the size knob 1 would give (a context that did not take the knob has THIS size)
            out.append((n, "tadata_size_if_knob_1", hex(L.layout(w, h, 1)["size"]), "LEAK", s))
    out += [("c2-64x64-k4", "tadata_sha_equals", "c3-64x64-k1", "F4", "control"),
            ("c2-64x64-k4", "target_hash_equals", "c3-64x64-k1", "F4", "control")]
    return out


# ---- k-pb -----------------------------------------------------------------------------------------------------------
def pb_words():
    own, twin = {}, {}
    for ln in open(os.path.join(KP, "gen", "data", "pb_words.tsv")).read().splitlines():
        if ln.startswith("#") or ln.startswith("index"):
            continue
        i, a, b = ln.split("\t")
        own[int(i)], twin[int(i)] = int(a, 16), int(b, 16)
    return own, twin


EMPTY_HASH, FULL_HASH = "0xfc5ff15e0434a325", "0xd0530839d87ea325"   # E728's empty image (TE 0x40), the twin's (te-m2-60, TE 0x60)


def pb0_rows():
    return [("pb-d0-te40", "control", "safe", "expectdiff", tri_pb("0x40000000")),
            ("pb-p0-te60", "control", "safe", "expectdiff", tri_pb("0x60000000")),
            ("pb-p1-te40", "control", "safe", "expectdiff", tri_pb("0x40000000"))]


def pb_rows():
    own, twin = pb_words()
    p3 = [(i, twin[i]) for i in range(11, 27)]
    return [("pb-p2-own11", "control", "risky", "expectdiff", tri_pb("0x40000000", [(11, own[11])])),
            ("pb-p3a-twin", "heldout", "risky", "expectdiff", tri_pb("0x40000000", p3)),
            ("pb-p3b-twin", "replicate", "risky", "expectdiff", tri_pb("0x40000000", p3)),
            ("pb-p4a-ffff", "heldout", "risky", "expectdiff", tri_pb("0x40000000", [(11, 0xffffffff)])),
            ("pb-p4b-ffff", "replicate", "risky", "expectdiff", tri_pb("0x40000000", [(11, 0xffffffff)]))]


def pb_preds():
    own, twin = pb_words()
    j = lambda d, a, b: ",".join("%08x" % d[i] for i in range(a, b))
    P = []
    add = lambda c, q, v, m, s: P.append((c, q, str(v), m, s))
    for c in ("pb-d0-te40", "pb-p1-te40", "pb-p2-own11"):
        add(c, "stream_0_2", j(own, 0, 3), "E728", "control")
        add(c, "par_11_26", j(own, 11, 27), "E728", "control")
        add(c, "diff", "3969 of 4096", "E728", "control")
        add(c, "target_hash", EMPTY_HASH, "E728", "control")
        add(c, "tri2", "0 triangle, 4096 background", "E728", "control")
    add("pb-p1-te40", "param_sha_equals", "pb-d0-te40", "E728", "control")
    add("pb-p2-own11", "param_sha_equals", "pb-d0-te40", "E728", "control")
    add("pb-p2-own11", "applied", 1, "E728", "control")
    add("pb-p0-te60", "stream_0_2", j(twin, 0, 3), "twin", "control")
    add("pb-p0-te60", "par_11_26", j(twin, 11, 27), "twin", "control")
    add("pb-p0-te60", "diff", "0 of 4096", "twin", "control")
    add("pb-p0-te60", "target_hash", FULL_HASH, "twin", "control")
    add("pb-p0-te60", "tri2", "4096 triangle, 0 background", "twin", "control")
    for c, s in (("pb-p3a-twin", "heldout"), ("pb-p3b-twin", "replicate")):
        add(c, "applied", 16, "H-OLD", s)
        add(c, "diff", "0 of 4096", "H-OLD", s)
        add(c, "target_hash", FULL_HASH, "H-OLD", s)
        add(c, "tri2_triangle", 4096, "H-OLD", s)
        add(c, "diff_not_twin", "yes", "H-FIELD", s)
        add(c, "par_11_26_in_dump", j(twin, 11, 27), "landed", s)
    for c, s in (("pb-p4a-ffff", "heldout"), ("pb-p4b-ffff", "replicate")):
        add(c, "applied", 1, "H-FIELD", s)
        add(c, "tri2_triangle", "above 0", "H-FIELD", s)
        add(c, "tri2_triangle", 0, "H-OLD", s)
        add(c, "par_11_in_dump", "ffffffff", "landed", s)
    return P


# ---- k-bif ----------------------------------------------------------------------------------------------------------
BIF_ROWS = [("n0-idle", "control", "safe", "idle bif", "-"),
            ("f1-ta-read", "heldout", "risky", "held bif hypo:bif:4 expectdiff", "tri --fault --keep-going --wait-ms 20000"),
            ("f1r-ta-read", "replicate", "risky", "held bif hypo:bif:4 expectdiff", "tri --fault --keep-going --wait-ms 20000"),
            ("f2-ta-write", "heldout", "risky", "held bif rgn:1 hypo:bif:4 expectdiff",
             "tri --tri-full --keep-going --wait-ms 20000 --width 320 --height 400 --max-width 320 --max-height 400 "
             "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 --dump-render \"$W/dump\""),
            ("f3-tex", "heldout", "risky", "held bif hypo:bif:4", PROBE_TEX)]
# fault word, BIF_FAULT page (E444: 0x90008 at 0x3e000001; E789 / E788 a6: 0x90004, 0x20008061; E765: 0x90002 at 0x3e017001)
BIF_FAULTS = {"f1-ta-read": ("0x90008", "0x3e000"), "f1r-ta-read": ("0x90008", "0x3e000"), "f2-ta-write": ("0x90004", "0x20008"),
              "f3-tex": ("0x90002", "0x3e017")}
# the three hypotheses of "what clears": cleared after the INT_STAT write of the set bits, and after the BIF_CTRL bit 4 flip
BIF_H = {"H-W1C": ("yes", "yes"), "H-CLR": ("no", "yes"), "H-RST": ("no", "no")}


def bif_preds():
    P = []
    add = lambda c, q, v, m, s: P.append((c, q, str(v), m, s))
    add("n0-idle", "int_stat", "0x80000", "idle", "control")
    add("n0-idle", "bif_fault", "0x0", "idle", "control")
    for step in ("after1", "after2", "after3", "after4", "after5"):
        add("n0-idle", step + "_changed", "no", "idle", "control")
    add("n0-idle", "ctrl_restored", "yes", "idle", "control")
    for c, (word, page) in BIF_FAULTS.items():
        s = "replicate" if c == "f1r-ta-read" else "heldout"
        add(c, "fault_word", word, "record", "control")
        add(c, "fault_page", page, "record", "control")
        # the unset bit 0x1 changes nothing (all three agree: the control that can fail)
        for h in BIF_H:
            add(c, "cleared_after1", "no", h, "control")
        for h, (c2, c3) in BIF_H.items():
            add(c, "cleared_after2", c2, h, s)
            add(c, "cleared_after3", c3, h, s)
            add(c, "cleared_after4_still", c3, h, s)
        add(c, "ctrl_restored", "yes", "all", "control")
        # E767: the halt makes both read clear; the new reset line prints them after the halt
        add(c, "reset_halt_int_stat", "0x80000", "E767", s)
        add(c, "reset_halt_fault", "0x0", "E767", s)
        add(c, "reset_clear_int_stat", "0x80000", "E767", s)
    return P


STAGES = {"k-f4": None, "k-pb0": None, "k-pb": None, "k-bif": None}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)


def line(r, rt="-"):
    name, sset, risk, knobs, cmd = r[:5]
    return "%s|%s|%s|%s|%s|%s\n" % (name, sset, risk, knobs, rt, cmd)


def tsv(P):
    return "case\tquantity\tvalue\tmodel\tset\n" + "".join("\t".join(r) + "\n" for r in P)


def main():
    tabs, preds = {}, {}
    f4 = f4_rows()
    tabs["k-f4"] = ["#stage k-f4\n"] + ["# %s\n" % x for x in (
        "Q140 (decision R3-K6): the layout with four region-header arrays (debugfs render_rgn_arrays 4; the knob is 1 for every other row).",
        "FIT post hoc: the formula reproduces 19 of 19 rows on record (closing3/kernel/layout_f4.out).  HELD OUT: h1-h8 (completes, 0 wrong, 4 arrays,",
        "the TA data size of the four-array layout).  Controls: c3 (knob 1, 64x64), c2 (knob 4, 64x64: same TA data and image as c3), c1 (knob 1 at",
        "288x144, HELD, last: E729's fault 0x90004 at page 0x20006).  An h row that faults is the refutation (the fault page says where); 2 such ends the h rows.")]
    tabs["k-f4"] += [line(r[:5]) for r in f4]
    preds["k-f4"] = f4_preds(f4)
    tabs["k-pb0"] = ["#stage k-pb0\n"] + ["# %s\n" % x for x in (
        "Q285 (decision R3-K7), the controls of the split flow (-n 2 --geometry 1): the dump run (TE 0x40, the parameter buffer from dword 0),",
        "p0 (TE 0x60, the twin: its full image) and p1 (TE 0x40: E728's empty image).  k-pb runs only if all three pass (the gate).")]
    tabs["k-pb0"] += [line(r) for r in pb0_rows()]
    tabs["k-pb"] = ["#stage k-pb\n"] + ["# %s\n" % x for x in (
        "Q285, the pokes (the kernel's par space, dword index from the parameter buffer's first page, applied between the TA and the 3D):",
        "p2 own dword 11 (0), p3 x2 the twin's dwords 11-26 (H-OLD: the twin's image; H-FIELD: not), p4 x2 dword 11 = 0xffffffff (H-FIELD:",
        "pixels drawn; H-OLD: none).  Cannot tell: p3 and p4 both empty (park under Q030).  A garbage word may hang the ISP: hang = stop.")]
    tabs["k-pb"] += [line(r) for r in pb_rows()]
    tabs["k-bif"] = ["#stage k-bif\n", "#need $S/s1d-tw64x64-l2e2__0.bin\n"] + ["# %s\n" % x for x in (
        "Q003 'what clears' (decision R3-K4).  n0: the four writes with nothing held (nothing changes).  f1, f1r: E444's TA read (0x90008);",
        "f2: E788's a6 at knob 1 (0x90004 at page 0x20008); f3: S3's texture fetch (0x90002 at 0x3e017001), last.  Per held fault, in the hold:",
        "0x0c04=0x1 (an unset bit: nothing changes), 0x0c04=<the set bits without bit 19> (H-W1C), 0x0c00^=0x10 (H-CLR), 0x0c00^=0x10 back, a",
        "2.5 s watch, then the kernel's reset (its new log lines).  A laptop that does not answer within 10 s after a write ends the session.")]
    tabs["k-bif"] += [line(r) for r in BIF_ROWS]
    preds["k-pb"] = pb_preds()
    preds["k-bif"] = bif_preds()
    for st, lines in tabs.items():
        write(os.path.join(KP, "tables", st + ".txt"), "".join(lines))
    for st in ("k-f4", "k-pb", "k-bif"):
        write(os.path.join(KP, "predictions", st + ".tsv"), tsv(preds[st]))
    write(os.path.join(KP, "stages.txt"), "k-f4\nk-pb0\nk-pb\nk-bif\n")
    write(os.path.join(KP, "conditional.txt"), "")
    # TABLES.md: the readable view
    md = "# R3K-pixel tables and frozen predictions (generated by gen/kgen.py)\n\nquantity = value [model] per case; set in brackets.\n"
    for st in ("k-f4", "k-pb0", "k-pb", "k-bif"):
        md += "\n## %s\n\n" % st
        for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
            if ln.startswith("#") or not ln:
                continue
            nm = ln.split("|")[0]
            md += "- `%s` (%s): `%s`\n" % (nm, ln.split("|")[1], ln.split("|", 5)[5])
            P = preds.get(st) or []
            if st == "k-pb0":
                P = [r for r in preds["k-pb"] if False]
            for r in P:
                if r[0] == nm:
                    md += "  - %s = %s [%s, %s]\n" % (r[1], r[2], r[3], r[4])
    # k-pb0's rows are scored against k-pb's frozen controls (same file: predictions/k-pb.tsv carries all three stages' pb cases)
    for nm in ("pb-d0-te40", "pb-p0-te60", "pb-p1-te40"):
        md += "\n(pb0 prediction rows for `%s` are in predictions/k-pb.tsv)\n" % nm
    write(os.path.join(KP, "TABLES.md"), md)
    os.makedirs(os.path.join(KP, "bins"), exist_ok=True)
    binp = os.path.join(KP, "bins", "s1d-tw64x64-l2e2__0.bin")
    assert hashlib.sha256(open(binp, "rb").read()).hexdigest() == "7540ac804e438d872756eeb09e217f7b0af5b21e3fc3dc4dde924792124eb5fc"
    print("generated: %d f4 rows, %d pb0, %d pb, %d bif" % (len(f4), 3, 5, 5))


if __name__ == "__main__":
    main()
