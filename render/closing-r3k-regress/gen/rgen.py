#!/usr/bin/env python3
"""rgen.py: regenerate tables/, predictions/, TABLES.md, stages.txt of R3K-regress (module-regression session).

  rgen.py extract    read the OLD records (published data, E728's kept dumps, K2's k-pb0 out) once and write gen/data/old_values.tsv
                     (case, quantity, value, source); run by hand, then rgen.py, then run/freeze_k.sh freeze
  rgen.py            read gen/data/old_values.tsv only and write tables/*.txt, predictions/*.tsv, TABLES.md, stages.txt

Why this session: the laptop's gma500 module changed from srcversion B21FDA82BD5E5CB5A627E3B (rounds 1-2, L1-L3) to
230E0EF50FFFD606C53AE3C (fork resgx545 at 8fc748b0).  K2's stage k-pb0 got target hash 0x8ea26cdfee74a325 where E728 froze
0xfc5ff15e0434a325.  Two stages:

  rg-ctl  23 control rows from closing sessions that passed on the old module (plain tri and geometry jobs, fills, the
          closing probes), each with its OLD value as the frozen prediction.  Spread over sizes (8x8 to 2048x1536), 1 to 4 renders
          and geometry kicks, TE 0x20 / 0xe0 (4x) and the flows of L1 and L2.
  rg-pb   the k-pb0 diagnosis: E728's own job shapes (ONE render, TE 0x40 / 0x80 / 0xc0, mode 0 and 2, 64x64 and 128x128) three
          times at TE 0x40, with E728's values as the prediction (H-OLD); K2's shape (-n 2 --geometry 1) with K2's k-pb0
          value as the prediction (H-NEW) three times.  The pinned tool prints render 2 in other colours, so K2's shape can not
          give E728's hash even on the old module [infer from the tool source, lines 2761 and 2797].
Predictions come from the records, never from the run.
"""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import rlib  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
K2 = "/Users/jtorra/src/scratch/resgx545/closing3/r3k-pixel/out/20261110-193547/k-pb0"
OLDV = os.path.join(KP, "gen", "data", "old_values.tsv")

TE_WORDS = "--poke cmd:1=%s --poke cmd:10=0xeaa26e26 --poke cmd:13=%s --poke cmd:16=0xeaa26e26"
SRC_U = DATA + "/render/closing-r1-pixgeo/out/g-u1"
SRC_Q = DATA + "/render/closing-r3-pixel/out/20261110-160415/q-t"
SRC_DD = DATA + "/render/closing-r3-geo/out/g-dd"
SRC_A = DATA + "/render/closing-r2-pixel/out/20261110-105258/r2-a-safe"
SRC_E = DATA + "/texture/p1141/out-hw/p1141tex-dumps/msaa-b-te29"

# --- rg-ctl: (case, set, command, source dir, source job name, dump file prefix or None, record) -------------------------------
U_OPT = "--keep-going --keep-overflow --wait-ms 20000"


def utri(w, h, n, extra=""):
    return "tri --width %d --height %d -n %d %s%s" % (w, h, n, extra + " " if extra else "", U_OPT)


CTL = [
    # closing-r1-pixgeo g-u1 (E773), pinned tool, old module; the record's --dump-render/--words/--regs are left out
    ("ctl-u-1024-n1", "heldout", utri(1024, 768, 1), SRC_U, "u-ctl-1", None, "E773 g-u1 u-ctl-1"),
    ("ctl-u-1024-n2g", "heldout", utri(1024, 768, 2, "--geometry 1 --move 2:0,288"), SRC_U, "u-ctl-2a", None, "E773 g-u1 u-ctl-2a"),
    ("ctl-u-1024-m32", "heldout", utri(1024, 768, 1, "--move 1:32,0"), SRC_U, "u-m32", None, "E773 g-u1 u-m32"),
    ("ctl-u-1024-m0-96", "heldout", utri(1024, 768, 1, "--move 1:0,96"), SRC_U, "u-m0-96", None, "E773 g-u1 u-m0-96"),
    ("ctl-u-1024-n2-256-192", "heldout", utri(1024, 768, 2, "--geometry 1 --move 2:256,192"), SRC_U, "u-2-256-192", None,
     "E773 g-u1 u-2-256-192"),
    ("ctl-u-1024-n3-stk", "heldout", utri(1024, 768, 3, "--geometry 1 --geometry 2 --move 2:16,0 --move 3:0,16"), SRC_U, "u-3-stk",
     None, "E773 g-u1 u-3-stk"),
    ("ctl-u-1024-n4-corners", "heldout",
     utri(1024, 768, 4, "--geometry 1 --geometry 2 --geometry 3 --move 2:512,0 --move 3:0,384 --move 4:512,384"), SRC_U,
     "u-4-corners", None, "E773 g-u1 u-4-corners"),
    ("ctl-u-640x480", "heldout", utri(640, 480, 1), SRC_U, "u-640", None, "E773 g-u1 u-640"),
    ("ctl-u-1280x1024", "heldout", utri(1280, 1024, 1), SRC_U, "u-1280", None, "E773 g-u1 u-1280"),
    ("ctl-u-512x384-m128", "heldout", utri(512, 384, 1, "--move 1:128,0"), SRC_U, "u-512-m128", None, "E773 g-u1 u-512-m128"),
    ("ctl-u-2048x1536", "heldout", utri(2048, 1536, 1), SRC_U, "u-2048-1536", None, "E773 g-u1 u-2048-1536"),
]
for w, h in ((8, 8), (16, 16), (32, 16), (32, 32), (64, 32), (128, 128), (256, 256)):
    CTL.append(("ctl-green-%dx%d" % (w, h), "control" if (w, h) == (16, 16) else "heldout",
                'probe --tri pixel --temps 32 --width %d --height %d --tri-full "$S/pix_green.bin"' % (w, h), SRC_Q,
                "t-ctl-green-%dx%d" % (w, h), None, "E806 q-t t-ctl-green-%dx%d" % (w, h)))
for n in ("dd-p1", "dd-p2"):
    CTL.append(("ctl-" + n, "control" if n == "dd-p1" else "heldout",
                'probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render "$W/dump" '
                '--slot "pixel=$S/pix_green.bin" "$S/%s__0.bin"' % n, SRC_DD, n, n + "." + n + "__0", "E798 g-dd " + n))
A_BASE = "tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d "
for nm, srcn, w, h, mw, mh, te, st in (("ctl-a4-320x400-te20-max544", "a4-ctl-320x400-te20", 320, 400, 544, 400, "0x20000000", "heldout"),
                                        ("ctl-a1-256x160-tee0", "a1-256x160-dump", 256, 160, 256, 160, "0xe0000000", "heldout"),
                                        ("ctl-a2-320x128-tee0", "a2-320x128-dump", 320, 128, 320, 128, "0xe0000000", "heldout")):
    CTL.append((nm, st, (A_BASE % (w, h, mw, mh)) + TE_WORDS % (te, "0x80000002") + ' --dump-render "$W/dump"', SRC_A, srcn, "tri",
                "E763 / E788 r2-a-safe " + srcn))
CTL_RC_FROM_CASES = {SRC_U: "cases.tsv", SRC_Q: "cases.tsv", SRC_DD: "cases.tsv", SRC_A: "cases.tsv"}

# --- rg-pb ----------------------------------------------------------------------------------------------------------------
E_BASE = "tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d "
DUMP = ' --dump-render "$W/dump"'
# (case, set, size, TE, mode word, E728 job name, expected rc, record)
PB_E = [
    ("pb-e20-m2-64", "control", 64, "0x20000000", "0x80000002", "t29-m2-20-64x64-ctl", 0),
    ("pb-ee0-m2-64", "control", 64, "0xe0000000", "0x80000002", "t29-m2-e0-64x64-ctl", 0),
    ("pb-e40-m2-64a", "heldout", 64, "0x40000000", "0x80000002", "t29-m2-40-64x64", 1),
    ("pb-e40-m2-64b", "replicate", 64, "0x40000000", "0x80000002", "t29-m2-40-64x64", 1),
    ("pb-e40-m2-64c", "replicate", 64, "0x40000000", "0x80000002", "t29-m2-40-64x64", 1),
    ("pb-e80-m2-64", "heldout", 64, "0x80000000", "0x80000002", "t29-m2-80-64x64", 1),
    ("pb-ec0-m2-64", "heldout", 64, "0xc0000000", "0x80000002", "t29-m2-c0-64x64", 1),
    ("pb-e40-m0-64", "heldout", 64, "0x40000000", "0x80000000", "t29-m0-40-64x64", 1),
    ("pb-e40-m2-128", "heldout", 128, "0x40000000", "0x80000002", "t29-m2-40-128x128", 1),
]
# K2's shape (-n 2 --geometry 1): the k-pb0 values are the prediction (H-NEW), E728's the alternative (H-OLD)
PB_N = [("pb-n40-a", "heldout", "0x40000000", "pb-d0-te40"), ("pb-n40-b", "replicate", "0x40000000", "pb-p1-te40"),
        ("pb-n40-c", "replicate", "0x40000000", "pb-p1-te40"), ("pb-n60", "heldout", "0x60000000", "pb-p0-te60")]
E728_QUANT = ("rc", "echo", "target_hash", "diff", "diff_first", "tri_last", "renders_ok", "tadata_sha256", "param_sha256", "stream_0_2",
              "par_11_26")


def pb_cmd_e(size, te, mode):
    return (E_BASE % (size, size, size, size)) + TE_WORDS % (te, mode) + DUMP


def pb_cmd_n(te):
    return (E_BASE % (64, 64, 64, 64)) + "-n 2 --geometry 1 " + TE_WORDS % (te, "0x80000002") + DUMP


def rg_rows():
    return [(c[0], c[1], "safe", "expectdiff" if c[2].startswith("tri") else "stophang", "-", c[2]) for c in CTL]


def pb_rows():
    r = [(n, s, "safe", "expectdiff", "-", pb_cmd_e(sz, te, md)) for n, s, sz, te, md, _, _ in PB_E]
    r += [(n, s, "safe", "expectdiff", "-", pb_cmd_n(te)) for n, s, te, _ in PB_N]
    return r


# --- extraction of the OLD values --------------------------------------------------------------------------------------------
def _gz(path):
    import gzip
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as f:
        return f.read()


def _rc_from_cases(d, name):
    p = os.path.join(d, "cases.tsv")
    lines = open(p).read().splitlines()
    head = lines[0].split("\t")
    for ln in lines[1:]:
        f = ln.split("\t")
        if f[0] == name and "rc" in head and len(f) > head.index("rc"):
            return int(f[head.index("rc")])
    raise KeyError((d, name))


def extract():
    rows = []
    for case, sset, cmd, d, srcn, dump, rec in CTL:
        out = _gz(os.path.join(d, srcn + ".txt.gz")).decode()
        rc = _rc_from_cases(d, srcn)
        ta = par = None
        if dump == "tri":
            ta, par = _gz(os.path.join(d, srcn + ".tri.tadata.bin.gz")), _gz(os.path.join(d, srcn + ".tri.param.bin.gz"))
        elif dump:
            ta, par = _gz(os.path.join(d, dump + ".tadata.bin.gz")), _gz(os.path.join(d, dump + ".param.bin.gz"))
        src = "%s; %s/%s" % (rec, d.replace(DATA + "/", "resgx545-data/"), srcn)
        for q, v in rlib.observe(out, rc, ta, par).items():
            rows.append((case, q, v, "OLD", src))
    for case, sset, size, te, mode, srcn, rc in PB_E:
        out = _gz(os.path.join(SRC_E, srcn + ".txt.gz")).decode()
        ta, par = _gz(os.path.join(SRC_E, srcn + ".tri.tadata.bin.gz")), _gz(os.path.join(SRC_E, srcn + ".tri.param.bin.gz"))
        src = "E728 p1141tex msaa-b-te29; resgx545-data/texture/p1141/out-hw/p1141tex-dumps/msaa-b-te29/" + srcn
        for q, v in rlib.observe(out, rc, ta, par).items():
            rows.append((case, q, v, "H-OLD", src))
    for case, sset, te, k2n in PB_N:
        out = _gz(os.path.join(K2, k2n + ".txt.gz")).decode()
        ta, par = _gz(os.path.join(K2, k2n + ".tri.tadata.bin.gz")), _gz(os.path.join(K2, k2n + ".tri.param.bin.gz"))
        src = "K2 k-pb0 closing3/r3k-pixel/out/20261110-193547/k-pb0/" + k2n + " (PREFLIGHT.md section 3, score-k-pb0.txt)"
        for q, v in rlib.observe(out, _rc_from_cases(K2, k2n), ta, par).items():
            rows.append((case, q, v, "H-NEW", src))
        # E728's values as the alternative: the same shape's quantities that E728 froze (hash, diff, image, dwords)
        e = "t29-m2-20-64x64-ctl" if te == "0x60000000" else "t29-m2-40-64x64"
        eo = _gz(os.path.join(SRC_E, e + ".txt.gz")).decode()
        ep = _gz(os.path.join(SRC_E, e + ".tri.param.bin.gz"))
        src2 = "E728 p1141tex msaa-b-te29 / the twin (TE 0x60: te-m2-60, E504's full image hash of the 0x20 control %s)" % e
        for q in ("target_hash", "diff", "par_11_26"):
            v = rlib.observe(eo, 1, None, ep).get(q)
            if te == "0x60000000" and q == "par_11_26":
                continue   # the twin's own dwords are not E728's record
            rows.append((case, q, v, "H-OLD", src2))
    # sanity: every case has its rows
    os.makedirs(os.path.dirname(OLDV), exist_ok=True)
    with open(OLDV, "w") as f:
        f.write("case\tquantity\tvalue\tmodel\tsource\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print("extracted %d old values for %d cases" % (len(rows), len({r[0] for r in rows})))


# --- generation ------------------------------------------------------------------------------------------------------------
def old_values():
    out = []
    for ln in open(OLDV).read().splitlines()[1:]:
        out.append(tuple(ln.split("\t")))
    return out


def tab_line(r):
    return "%s|%s|%s|%s|%s|%s\n" % r


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        extract()
        return
    vals = old_values()
    sets = {c[0]: c[1] for c in CTL}
    sets.update({r[0]: r[1] for r in pb_rows()})
    ctl = ["#stage rg-ctl\n", "#need $S/pix_green.bin\n", "#need $S/dd-p1__0.bin\n", "#need $S/dd-p2__0.bin\n"]
    ctl += ["# %s\n" % x for x in (
        "Module regression, control rows: %d jobs from closing sessions that passed on the OLD module (srcversion B21FDA82...), each with" % len(CTL),
        "its OLD kept value frozen (predictions/rg-ctl.tsv; the record and kept file are in the last column).  Plain tri and geometry",
        "jobs (E773), fills (E806), the closing probes (E798) and the r2-a-safe tri rows (E763, E788), through the pinned tool only.",
        "No fault, no hold, no firmware task, no kreg/kregnow/kpoke, no BIF write, no clock gate, knobs at their defaults.")]
    ctl += [tab_line(r) for r in rg_rows()]
    pb = ["#stage rg-pb\n"] + ["# %s\n" % x for x in (
        "The k-pb0 diagnosis.  E728's own shapes (one render; TE 0x40/0x80/0xc0, cmd:13 mode 0 and 2) with E728's values (H-OLD);",
        "pb-e20 / pb-ee0 are E728's own controls (TE 0x20, 0xe0).  K2's shape (-n 2 --geometry 1) with K2's k-pb0 value (H-NEW).",
        "E728 ran through ~/sgxfive-test-1138b; this session uses the pinned ~/sgxfive-test-r1 (tool differences are a confound,")
    ] + ["# rg-ctl's pinned-tool controls bound it).\n"]
    pb += [tab_line(r) for r in pb_rows()]
    write(os.path.join(KP, "tables", "rg-ctl.txt"), "".join(ctl))
    write(os.path.join(KP, "tables", "rg-pb.txt"), "".join(pb))
    for st, names in (("rg-ctl", [c[0] for c in CTL]), ("rg-pb", [r[0] for r in pb_rows()])):
        lines = ["case\tquantity\tvalue\tmodel\tset\tsource\n"]
        for case, q, v, m, src in vals:
            if case in names:
                lines.append("\t".join((case, q, v, m, sets[case], src)) + "\n")
        write(os.path.join(KP, "predictions", st + ".tsv"), "".join(lines))
    write(os.path.join(KP, "stages.txt"), "rg-ctl\nrg-pb\n")
    md = "# R3K-regress tables and frozen predictions (generated by gen/rgen.py)\n\nquantity = value [model, set]; source in predictions/*.tsv.\n"
    for st in ("rg-ctl", "rg-pb"):
        md += "\n## %s\n\n" % st
        for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
            if ln.startswith("#") or not ln:
                continue
            nm = ln.split("|")[0]
            md += "- `%s` (%s): `%s`\n" % (nm, ln.split("|")[1], ln.split("|", 5)[5])
            for case, q, v, m, src in vals:
                if case == nm and q not in ("tadata_size",):
                    md += "  - %s = %s [%s]\n" % (q, v if len(v) < 90 else v[:87] + "...", m)
    write(os.path.join(KP, "TABLES.md"), md)
    print("generated: %d rg-ctl rows, %d rg-pb rows" % (len(CTL), len(pb_rows())))


if __name__ == "__main__":
    main()
