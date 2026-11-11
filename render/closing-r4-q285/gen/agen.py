#!/usr/bin/env python3
"""agen.py: the R4-A tables and predictions (Q285 rerun with controls of the stage's own job shape).

  agen.py extract   read the R3K-regress kept files of the two-render rows (resgx545-data render/closing-r3k-regress, attempt
                    20261110-222647, stage rg-pb: pb-n40-a, pb-n40-b, pb-n40-c at TE 0x40 and pb-n60 at TE 0x60, all
                    `-n 2 --geometry 1`, the shape of K2's k-pb0 and k-pb) into gen/data/ctl_values.tsv (job, quantity, value)
  agen.py build     write tables/a-pb0.txt, tables/a-pb.txt (K2's commands byte for byte, from resgx545-data
                    render/closing-r3k-pixel/tables, each row with the knob rgn:1), predictions/a-pb0.tsv, predictions/a-pb.tsv and
                    TABLES.md from ctl_values.tsv

Run once, before the freeze; the freeze pins the outputs and ctl_values.tsv, and the source files by absolute path.
"""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
import alib as L  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
REG_REL = "render/closing-r3k-regress/out/20261110-222647/rg-pb"
REG = os.path.join(DATA, REG_REL)
K2T = os.path.join(DATA, "render/closing-r3k-pixel/tables")
JOBS = ("pb-n40-a", "pb-n40-b", "pb-n40-c", "pb-n60")
VALUES = os.path.join(HERE, "data", "ctl_values.tsv")
QS = ("rc", "echo", "geometry1", "target_hash", "diff", "tri2", "renders", "param_sha256", "param_size", "tadata_sha256",
      "tadata_size", "par_0_64")
PB0 = ("pb-d0-te40", "pb-p0-te60", "pb-p1-te40")
PB = ("pb-p2-own11", "pb-p3a-twin", "pb-p3b-twin", "pb-p4a-ffff", "pb-p4b-ffff")
# the control of each row: its regress job (same shape, same TE)
CTL_SRC = {"pb-d0-te40": "pb-n40-a", "pb-p1-te40": "pb-n40-a", "pb-p0-te60": "pb-n60"}
TWIN2_HASH = "0xd2bfb75560f4c325"   # the twin's two-render target hash (E825 p0, E827 pb-n60)


def _gz(p):
    with gzip.open(p, "rb") as f:
        return f.read()


def _rc(job):
    return L.read_cases(REG)[job]["rc"]


def extract():
    rows = ["job\tquantity\tvalue\tsource\n"]
    for job in JOBS:
        out = _gz(os.path.join(REG, job + ".txt.gz")).decode()
        par = _gz(os.path.join(REG, job + ".tri.param.bin.gz"))
        tad = _gz(os.path.join(REG, job + ".tri.tadata.bin.gz"))
        v = {"rc": _rc(job), "echo": L.echo(out), "geometry1": L.geometry1(out), "target_hash": L.target_hash(out),
             "diff": L.diff_text(out), "tri2": L.tri_text(out, 2), "renders": L.renders(out), "param_sha256": L.sha256(par),
             "param_size": "%d" % len(par), "tadata_sha256": L.sha256(tad), "tadata_size": "%d" % len(tad),
             "par_0_64": L.words(par, 0, 64)}
        for q in QS:
            rows.append("%s\t%s\t%s\tresgx545-data:%s/%s\n" % (job, q, v[q], REG_REL, job))
    open(VALUES, "w").write("".join(rows))
    print("wrote %s (%d rows)" % (VALUES, len(rows) - 1))


def load_values():
    v = {}
    for ln in open(VALUES).read().splitlines()[1:]:
        job, q, val, _src = ln.split("\t")
        v.setdefault(job, {})[q] = val
    return v


def k2_rows():
    rows = {}
    for st in ("k-pb0", "k-pb"):
        for ln in open(os.path.join(K2T, st + ".txt")).read().splitlines():
            if ln and not ln.startswith("#"):
                f = ln.split("|", 5)
                rows[f[0]] = f
    return rows


def pokes(cmd):
    import re
    return ["par:%s=%s" % m.groups() for m in re.finditer(r"--kpoke-render 2:par:(\d+)=(0x[0-9a-f]{8})", cmd)]


HEAD0 = """#stage a-pb0
# R4-A, Q285 (decision 10, reruns): the controls of the split flow (-n 2 --geometry 1), K2's k-pb0 commands byte for byte, every row at
# render_rgn_arrays 1 (rgn:1: fork a2788bd8 refuses TE_AA bit 30 or 31 on a context without the 4x flag at the default 0; a forced 1 is
# the one-array layout R3K-regress measured).  Frozen from R3K-regress's kept two-render rows (pb-n40-a/b/c, pb-n60), not from E728's
# one-render jobs (K2's k-pb0 lesson, E825).  a-pb runs only if all three pass (the gate, computed from the kept a-pb0).
"""
HEAD1 = """#stage a-pb
# R4-A, Q285, the pokes (K2's k-pb commands byte for byte, rgn:1): par space, dword index from the parameter buffer's first page,
# armed before render 2 and applied once after render 1's geometry-only kick, so they change render 1's object (dwords 0-26) before
# render 2's TA appends its own (from dword 27).  p2 own dword 11 (a control); p3a/p3b the twin's dwords 11-25 and 0 at 26 (H-OLD: the
# twin's picture; H-FIELD: not); p4a/p4b dword 11 = 0xffffffff (H-FIELD: pixels drawn; H-OLD: none).  A hang is a stop.
"""


def build():
    V = load_values()
    k2 = k2_rows()
    t0, t1 = [HEAD0], [HEAD1]
    for n in PB0:
        f = k2[n]
        t0.append("|".join((n, f[1], f[2], "rgn:1 expectdiff", "-", f[5])) + "\n")
    for n in PB:
        f = k2[n]
        t1.append("|".join((n, f[1], f[2], "rgn:1 expectdiff", "-", f[5])) + "\n")
    open(os.path.join(KP, "tables", "a-pb0.txt"), "w").write("".join(t0))
    open(os.path.join(KP, "tables", "a-pb.txt"), "w").write("".join(t1))

    hdr = "case\tquantity\tvalue\tmodel\tset\tsource\n"
    p0 = [hdr]
    for n in PB0:
        job = CTL_SRC[n]
        src = "R3K-regress (E827) kept %s/%s, the same shape (-n 2 --geometry 1) and TE" % (REG_REL, job)
        for q in QS:
            p0.append("\t".join((n, q, V[job][q], "SAME-SHAPE", "control", src)) + "\n")
    p0.append("\t".join(("pb-p1-te40", "param_sha_equals", "pb-d0-te40", "SAME-SHAPE", "control",
                         "in-session: p1 repeats the dump run (E825 d0 = p1)")) + "\n")
    p0.append("\t".join(("pb-d0-te40", "pokes_applied", "none", "SAME-SHAPE", "control", "no --kpoke-render in the row")) + "\n")
    open(os.path.join(KP, "predictions", "a-pb0.tsv"), "w").write("".join(p0))

    n40, n60 = V["pb-n40-a"], V["pb-n60"]
    tw = n60["par_0_64"].split(",")
    p1 = [hdr]
    s40 = "R3K-regress (E827) kept %s/pb-n40-a (the poke writes the word's own value: the job is d0's)" % REG_REL
    for q in ("rc", "target_hash", "diff", "tri2", "renders", "param_sha256", "tadata_sha256", "par_0_64"):
        p1.append("\t".join(("pb-p2-own11", q, n40[q], "SAME-SHAPE", "control", s40)) + "\n")
    p1.append("\t".join(("pb-p2-own11", "applied", ";".join(pokes(k2["pb-p2-own11"][5])), "SAME-SHAPE", "control",
                         "the kernel's `kpoke ... applied` lines in the job's kmsg slice")) + "\n")
    p1.append("\t".join(("pb-p2-own11", "armed_after", "", "SAME-SHAPE", "control", "debugfs kpoke read after the job: empty")) + "\n")
    for n in ("pb-p3a-twin", "pb-p3b-twin"):
        sset = "heldout" if n.endswith("a-twin") else "replicate"
        p1.append("\t".join((n, "applied", ";".join(pokes(k2[n][5])), "gate", sset, "16 pokes, all applied, else NODATA")) + "\n")
        p1.append("\t".join((n, "reading", "twin", "H-OLD", sset, "diff 0 of 4096 and render 2: 4096 triangle, 0 background, 0 other")) + "\n")
        p1.append("\t".join((n, "reading", "not twin", "H-FIELD", sset, "any other completed reading with the pokes applied")) + "\n")
        p1.append("\t".join((n, "target_hash", TWIN2_HASH, "report", sset,
                             "reported, never deciding: the twin's two-render hash (E825 p0, E827 pb-n60); E825: the hash is not the "
                             "picture alone, and render 2's object keeps the TE 0x40 layout")) + "\n")
        p1.append("\t".join((n, "par_11_26_in_dump", ",".join(tw[11:26] + ["00000000"]), "landed", sset,
                             "reported: the poked words read back in the dump")) + "\n")
    for n in ("pb-p4a-ffff", "pb-p4b-ffff"):
        sset = "heldout" if n.endswith("a-ffff") else "replicate"
        p1.append("\t".join((n, "applied", ";".join(pokes(k2[n][5])), "gate", sset, "1 poke applied, else NODATA")) + "\n")
        p1.append("\t".join((n, "reading", "drawn", "H-FIELD", sset, "render 2: triangle pixels above 0")) + "\n")
        p1.append("\t".join((n, "reading", "empty", "H-OLD", sset, "render 2: 0 triangle and 0 other pixels")) + "\n")
        p1.append("\t".join((n, "par_11_in_dump", "ffffffff", "landed", sset, "reported")) + "\n")
    open(os.path.join(KP, "predictions", "a-pb.tsv"), "w").write("".join(p1))

    md = ["# R4-A tables (generated by gen/agen.py build; the frozen files are tables/ and predictions/)\n\n"]
    for st, rows in (("a-pb0", PB0), ("a-pb", PB)):
        md.append("## %s\n\n| row | set | TE | pokes |\n|---|---|---|---|\n" % st)
        for n in rows:
            f = k2[n]
            te = [x for x in f[5].split() if x.startswith("cmd:1=")][0][6:]
            pk = pokes(f[5])
            md.append("| %s | %s | %s | %s |\n" % (n, f[1], te, "%d (%s .. %s)" % (len(pk), pk[0], pk[-1]) if pk else "-"))
        md.append("\n")
    md.append("Controls (a-pb0, from R3K-regress pb-n40-a and pb-n60): d0 and p1 target hash %s, diff `%s`, param sha256 %s; "
              "p0 target hash %s, diff `%s`, param sha256 %s.\n" % (n40["target_hash"], n40["diff"], n40["param_sha256"][:16],
                                                                     n60["target_hash"], n60["diff"], n60["param_sha256"][:16]))
    open(os.path.join(KP, "TABLES.md"), "w").write("".join(md))
    print("wrote tables, predictions and TABLES.md")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "extract":
        extract()
    elif cmd == "build":
        build()
    else:
        print(__doc__)
        sys.exit(2)
