#!/usr/bin/env python3
"""rgen.py: writes everything r6-render4x's stage A generates, before any job: tables/{s0,a,t}.txt, predictions/{s0,a,h,t}.tsv,
TABLES.md, stages.txt, bins/*.bin (the line and point programs of stage t), gen/data/*.tsv (the twins, the recorded cells) and
gen/data/sources.lst.
  rgen.py            write everything (refuses to run once FROZEN.sha256 exists: the freeze is never rewritten)
  rgen.py --check    regenerate into memory and compare with the files on disk (the freeze test uses it)
Plan: closing6/render4x/exp-render4x-r6.md section 2 (stage A) and section 5 (Q293's four rows), decisions DECISIONS-R6.md R6-2 (a),
R6-5 (a), R6-6 (a) and the plan's decisions 5 (a) and 7 (a).  Built from r5-render4x's generator (closing5/r5-render4x/gen/rgen.py)
with its two build rules: every frozen page need of a control comes from a kept TWIN of the row's own argv (gen/twins.py), and every
row that asks for a dump freezes the name its verb gives the dump (rlib.dump_stem).
Stage B (the new kernel, plan section 4) is NOT generated here: it is a second freeze added later (README.md "Stage B"), whose files
this generator never writes or reads, so stage A's freeze stays byte for byte.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import twins as TW  # noqa: E402

KP = L.KP
S4X = "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"
REGS = "--regs 0x0700-0x072c"
DUMP = '--dump-render "$W/dump"'
STAGES = ["s0", "a", "t"]
LIMIT = {"s0": 1, "a": 8, "t": 1}
T7_VALUE = 0x00000001          # the non-zero value t7 pokes into the inserted dword (the plan leaves it open; E829 p4 had 0xffffffff)
TA_TOML = L.MAIN + "/probes/ta/p1131-progs.toml"
TA_TEMPLATES = L.MAIN + "/probes/ta/templates"
SOURCES = []                  # every file read from outside this directory (the freeze pins them by absolute path)
SLOT = 4 << 20                # a parameter slot's TA-data room: 4 MiB

# stage a: (name, set, W, H, MW, MH, held, group).  The plan's table (section 2) in the order the runner takes them: the premise a4
# first, the five rows where H-TPM and the dead size rules disagree, then the predicted faults, the two held rows last.
AROWS = [("a4-1024x768-max2048x1024", "control", 1024, 768, 2048, 1024, False, None),
         ("a1-1024x1280", "heldout", 1024, 1280, 1024, 1280, False, "a1"),
         ("a1r-1024x1280", "replicate", 1024, 1280, 1024, 1280, False, "a1"),
         ("a12-992x1280", "heldout", 992, 1280, 992, 1280, False, "q292"),
         ("a13-512x1536", "heldout", 512, 1536, 512, 1536, False, "q292"),
         ("a8-1024x1024-max1024x1280", "heldout", 1024, 1024, 1024, 1280, False, "q292"),
         ("a9-1024x800-max1024x1280", "heldout", 1024, 800, 1024, 1280, False, "q292"),
         ("a2-1024x1296", "heldout", 1024, 1296, 1024, 1296, False, "q292"),
         ("a3-1040x1280", "heldout", 1040, 1280, 1040, 1280, False, "q292"),
         ("a5-1024x800-max2048x1024", "heldout", 1024, 800, 2048, 1024, False, "q292"),
         ("a14-1024x1536", "heldout", 1024, 1536, 1024, 1536, False, "q292"),
         ("h1-1024x800-held", "heldout", 1024, 800, 1024, 800, True, "q292"),
         ("h2-1280x768-held", "heldout", 1280, 768, 1280, 768, True, "q292")]
GROUP_MAX = {"a1": 1, "q292": LIMIT["a"]}


def src(p):
    if p not in SOURCES:
        SOURCES.append(p)
    return p


def t(path):
    return L.read_text(src(path))


def b(path):
    return L.read_bytes(src(path))


def row4x(w, h, mw=None, mh=None, dump=True):
    mw, mh = mw or w, mh or h
    a = ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d --aa4 %s'
         % (w, h, mw, mh, S4X))
    return a + (" %s %s" % (DUMP, REGS) if dump else "")


def row1x(w, h):
    """The DEFAULT triangle at 1x (E827 ctl-u-1024-n1's form)."""
    return 'tri --width %d --height %d -n 1 --keep-going --keep-overflow --wait-ms 20000 %s %s' % (w, h, DUMP, REGS)


class Stage:
    def __init__(self, name):
        self.name, self.rows, self.needs, self.preds = name, [], [], []

    def row(self, name, sset, risk, knobs, args):
        self.rows.append((name, sset, risk, knobs, args))

    def pred(self, case, q, val, model, sset, source):
        self.preds.append((case, q, str(val), model, sset, source))


def dump_pred(s, name, args):
    """Every row that asks for a dump freezes its file names (the name census)."""
    dn = L.dump_names(name, args)
    if dn:
        s.pred(name, "dump_param", dn[0], "the verb's dump name (rlib.dump_stem: tri -> tri, probe PROG.bin -> PROG)", "census", "sgxfive-test.c dump_render")


def build():
    st = {n: Stage(n) for n in STAGES}
    hset = Stage("h")
    tb = TW.table()
    for r in TW.kept_rows():
        src(r[5])
        src(r[6])
    twin_rows = []

    def need(stage, name, args, knobs):
        got, tw = TW.need_of(args, knobs, tb)
        if got is None or got == "DISAGREE":
            raise SystemExit("BUILD FAILS: %s has no usable twin (%s): a control cannot carry a model need" % (name, got))
        tri1 = None
        for s_, n_, _ in tw:
            o = L.read_text(src(os.path.join(TW.DATA, "render", os.path.dirname(s_), n_ + ".txt.gz")))
            tri1 = tri1 or L.tri_counts_text(o)
        twin_rows.append((stage, name, got, "; ".join("%s/%s" % (s_, n_) for s_, n_, _ in tw), tri1 or "-"))
        return got, "kept twins (%d): %s" % (len(tw), ", ".join("%s/%s %d" % (s_.split("/out/")[0], n_, p_) for s_, n_, p_ in tw)), tri1

    # ---- s0: r5's three controls (round 4's, passed again in E865 to E869's session), with their kept hashes ------------------------
    s = st["s0"]
    j5 = t(L.RGN4 + "/j5-ctl-1x.out")
    j1r = t(L.RGN4 + "/j1r-aa4-auto.out")
    h8 = t(L.K2 + "/h8-1024x768-k4.txt.gz")
    j1r_ta = len(b(L.K2 + "/h1-288x144-k4.tri.tadata.bin.gz"))
    h8_ta = len(b(L.K2 + "/h8-1024x768-k4.tri.tadata.bin.gz"))
    rows = [("s0-1x-1024x768", row1x(1024, 768), j5, None, "E827 ctl-u-1024-n1, E828 j5 (closing-r3-rgn4 j5-ctl-1x.out); r5 s0 PASS"),
            ("s0-4x-288x144", row4x(288, 144), j1r, j1r_ta, "E828 j1r (closing-r3-rgn4), E824 h1 (TA data 0x%x); r5 s0 PASS" % j1r_ta),
            ("s0-4x-1024x768", row4x(1024, 768), h8, h8_ta, "E824 h8 (closing-r3k-pixel k-f4); r5 s0 PASS")]
    for case, args, text, ta_size, source in rows:
        s.row(case, "control", "safe", "expectdiff", args)
        s.pred(case, "rc", 0, "kept", "ctl", source)
        s.pred(case, "echo", L.echo(text), "kept", "ctl", source)
        s.pred(case, "target_hash", L.target_hash(text), "kept", "ctl", source)
        s.pred(case, "diff", L.diff_text(text), "kept", "ctl", source)
        s.pred(case, "tri1", L.tri_counts_text(text), "kept", "ctl", source)
        s.pred(case, "renders", L.renders(text), "kept", "ctl", source)
        if ta_size:
            s.pred(case, "tadata_size", ta_size, "kept", "ctl", source)
        n_, why, _ = need("s0", case, args, "expectdiff")
        s.pred(case, "pb_used", n_, why, "ctl", "gen/data/twins.tsv")
        dump_pred(s, case, args)

    # ---- a: H-TPM against the dead size rules, the two held faults -----------------------------------------------------------------
    a = st["a"]
    for name, sset, w, h, mw, mh, held, grp in AROWS:
        assert w % 2 == 0 and h % 2 == 0 and M.tadata_4x(mw, mh) <= SLOT and R.u4(w, h) <= M.usable(M.PB_PAGES)
        k = ["expectdiff"] + (["held", "dumpheld"] if held else []) + ["strict"] + (["hypo:%s:%d" % (grp, GROUP_MAX[grp])] if grp else [])
        args = row4x(w, h, mw, mh, dump=not held)
        htpm = R.fault(R.HTPM, w, h, mw, mh)
        risky = any(R.fault(r, w, h, mw, mh) is not False for r in R.ALL)
        a.row(name, sset, "risky" if risky else "safe", " ".join(k), args)
        dump_pred(a, name, args)
        ps = {"control": "ctl", "heldout": "heldout", "replicate": "rep"}[sset]
        end, rgn = R.entries_end(w, h), R.lay(mw, mh)["rgn"]
        a.pred(name, "htpm", "fault" if htpm else "complete",
               "H-TPM [E870, post hoc fit on E869's dump; this row held out]: the target's entries end 0x%x %s td.rgn 0x%x of the %dx%d maximum"
               % (end, ">" if htpm else "<=", rgn, mw, mh), ps, "gen/rules.py; exp 1.2")
        a.pred(name, "entries_end", "0x%x" % end, "4 x (Z(2tx - 1, 2ty - 1) + 1), y on the even bits", "model", "gen/rules.py")
        a.pred(name, "td_rgn", "0x%x" % rgn, "the maximum's layout on the rgn4 kernel (room 4 side^2 + 3 pages)", "model", "gen/rules.py")
        for r in R.ALL:
            if r != R.HTPM:
                a.pred(name, "rule:" + r, R.pred_word(r, w, h, mw, mh), "rules.py from the argv (target %dx%d, maximum %dx%d)" % (w, h, mw, mh),
                       "compare", "gen/rules.py")
        a.pred(name, "fault_int", "0x0100", "the 3D-side word of every 4x fault on record (E845, E867-E869)", ps, "E845")
        a.pred(name, "fault_page", "0x10000", "the request base: a zero stream offset (E869)", ps, "E869")
        if not held:
            a.pred(name, "diff", "0 of %d pixels" % (w * h), "a completed 4x full triangle draws exactly (E824)", ps, "E824")
            a.pred(name, "pb_used", R.u4(w, h), "page model U4 = 1 + ceil(2 tiles16 / 32) (E824's ten dumps; r5 m, l, x: 6 of 6)", "model", "gen/pbmodel.py")
            a.pred(name, "tadata_size", M.tadata_4x(mw, mh), "the layout of the CONTEXT'S maximum, four arrays (r5: 6 of 6)", "model", "gen/pbmodel.py")
            a.pred(name, "hdr_off", 0, "the doubled-grid rule: grid of the target, base td.rgn of the maximum (r5 m0, m1, m2, m4: 0 off)", "model", "gen/rlib.py headers")
            a.pred(name, "nonzero_below_rgn", 0, "every completed four-array dump of r5 is zero below td.rgn (cells.out)", "model", "cells.out")
        else:
            lo = R.lost(w, h, mw, mh)
            hset.pred(name, "lost", ",".join("0x%x" % o for o in lo),
                      "H-TPM: the headers of in-target tiles whose word-1 dword is an in-target tile's entry 4 x Z(x, y) lose their stream "
                      "offset (cells.py lost(); E869's dump: 1023 of 1023)", "heldout", "gen/rules.py lost()")
            hset.pred(name, "lost_count", len(lo), "H-TPM", "heldout", "gen/rules.py lost()")
            hset.pred(name, "lost_first", "0x%x" % lo[0], "H-TPM", "heldout", "gen/rules.py lost()")
            hset.pred(name, "lost_last", "0x%x" % lo[-1], "H-TPM", "heldout", "gen/rules.py lost()")
            hset.pred(name, "header0_lost", "yes" if lo[0] == rgn else "no", "H-TPM: whether header 0 (at td.rgn) is among them", "heldout", "gen/rules.py lost()")
            xl = R.lost(w, h, mw, mh, yeven=False)
            hset.pred(name, "lost_xeven_count", len(xl), "the other interleave (x on the even bits): its set, for the verdict's variants", "compare", "gen/rules.py lost()")
            hset.pred(name, "held_pages", R.u4(w, h), "the TA finished: the held parameter dump has U4 scene pages (E869: 321 at 1280 x 1024)", "explore", "gen/pbmodel.py")
    # ---- t: Q293's four rows (plan section 5, decision 5 a; the reworded Q293 on main) -------------------------------------------------
    tt = st["t"]
    tt.needs = ["$S/p1131-green__0.bin", "$S/p1131-psizes__1.bin"]
    rg = lambda n, ext: L.REG + "/" + n + ext  # noqa: E731
    e40 = t(rg("pb-e40-m2-64a", ".txt.gz"))
    e40p = b(rg("pb-e40-m2-64a", ".tri.param.bin.gz"))
    e40t = b(rg("pb-e40-m2-64a", ".tri.tadata.bin.gz"))
    p4 = t(L.Q285 + "/pb-p4a-ffff.txt.gz")
    ln_line = _case_args(L.DATA + "/ta/line-point/cases.tsv", "ln-ctl64-r1")
    pt_line = _case_args(L.DATA + "/ta/points/cases.tsv", "pp-c-s1")
    ln_par = b(L.LINE + "/ln-ctl64-r1.param.bin.gz")
    pt_par = b(L.POINT + "/pp-c-s1.param.bin.gz")
    ln_args = _probe_args(ln_line)
    pt_args = _probe_args(pt_line)
    pokes = "--poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"
    t8 = ('tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 --poke cmd:1=0x40000000 '
          + pokes + " " + DUMP)
    t7 = ('tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 -n 2 --geometry 1 '
          '--poke cmd:1=0x40000000 ' + pokes + ' --kpoke-render 2:par:11=0x%08x ' % T7_VALUE + DUMP)
    poke = lambda a_, v: a_.replace("--pixels", "--cmd 1=0x%08x --pixels" % v, 1)  # noqa: E731
    trows = [("t8-ctl-te40-1array", "control", "expectdiff rgn:1", t8),
             ("t5-line-tec0", "heldout", "rgn:1", poke(ln_args, 0xC0000000)),
             ("t6-point-tec0", "heldout", "rgn:1", poke(pt_args, 0xC0000000)),
             ("t7-tri-te40-poke11", "heldout", "expectdiff rgn:1", t7)]
    for name, sset, knobs, args in trows:
        tt.row(name, sset, "risky" if "kpoke" in args else "safe", knobs, args)
        dump_pred(tt, name, args)
    srcp = "E827 rg-pb pb-e40-m2-64a (closing-r3k-regress); r5's t6 PASS (E865)"
    tt.pred("t8-ctl-te40-1array", "rc", 1, "kept", "ctl", srcp)
    tt.pred("t8-ctl-te40-1array", "target_hash", L.target_hash(e40), "kept", "ctl", srcp)
    tt.pred("t8-ctl-te40-1array", "diff", L.diff_text(e40), "kept", "ctl", srcp)
    tt.pred("t8-ctl-te40-1array", "tri1", L.tri_counts_text(e40), "kept", "ctl", srcp)
    tt.pred("t8-ctl-te40-1array", "par_0_64", L.words(e40p, 0, 64), "kept", "ctl", srcp)
    tt.pred("t8-ctl-te40-1array", "tadata_size", len(e40t), "kept", "ctl", srcp)
    for case, par, nm in (("t5-line-tec0", ln_par, "line"), ("t6-point-tec0", pt_par, "point")):
        bw = L.dwords(par)
        pos = bw.index(0x00040101)
        sk = "11.31 %s dump (resgx545-data ta/%s), replicated by r5's t3b/t4b (E865)" % (nm, "line-point" if nm == "line" else "points")
        tt.pred(case, "base_0_64", L.words(par, 0, 64), "the unpoked baseline's head: the kept 11.31 dump, equal to r5's in-session baseline", "base", sk)
        tt.pred(case, "rc", 0, "kept form", "heldout", sk)
        tt.pred(case, "insert_pos", pos, "the inserted dword sits right before the first format word 0x00040101 (E865 at 0x40 and 0x80; 0xc0 held out)", "heldout", sk)
        tt.pred(case, "insert_val", "0x00000000", "H-PAD [infer]: the inserted dword is zero; H-FIELD: non-zero", "heldout", sk)
        tt.pred(case, "image", "empty", "the 3D reads the displaced layout: nothing drawn (E865: empty at 0x40 and 0x80)", "heldout", "E865")
    q = "t7-tri-te40-poke11"
    sp4 = "E829 pb-p4a-ffff (closing-r4-q285): the same shape with 0xffffffff at dword 11"
    tt.pred(q, "kpoke", "par:11=0x%08x" % T7_VALUE, "the kernel's 'kpoke ... applied' line: the poke landed (E829: 16 of 16)", "heldout", sp4)
    tt.pred(q, "dword11", "0x%08x" % T7_VALUE, "the dump's dword 11 is the poked value", "heldout", sp4)
    tt.pred(q, "dword12", "0x00040101", "the TA's format word stays at 12 (E728)", "heldout", "E728")
    tt.pred(q, "tri2", L.tri_counts_text(p4, 2), "H-OLD (E829): the 3D reads dword 11 as the format word: a non-zero value there draws nothing", "heldout", sp4)
    tt.pred(q, "renders", L.renders(p4), "kept form", "heldout", sp4)
    return st, hset, tb, twin_rows


def _case_args(cases_tsv, name):
    for ln in t(cases_tsv).splitlines():
        f = ln.split("\t")
        if f[0] == name:
            return f[5]
    raise KeyError(name)


def _probe_args(line):
    """A 11.31 job's kept command made into a row: the staged programs, the dump directory and the pixels from this session's."""
    import re
    a = line
    a = re.sub(r"--dump-render \S+", DUMP, a)
    a = re.sub(r"/home/jtorra/sgxprobes-stage/p1131-green__0\.bin", '"$S/p1131-green__0.bin"', a)
    a = re.sub(r"/home/jtorra/sgxprobes-stage/p1131-psizes__1\.bin", '"$S/p1131-psizes__1.bin"', a)
    if "--pixels" not in a:
        a = a.replace("--dump-render", "--pixels --dump-render")
    return a


def build_bins():
    """The line and point programs of stage t, assembled from probes/ta/p1131-progs.toml and compared with r5's published copies."""
    sys.path.insert(0, L.MAIN + "/tools/usse-asm")
    import pathlib
    import tempfile
    import probe as P
    ps = {p.name: p for p in P.load(pathlib.Path(src(TA_TOML)))}
    done = {}
    os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.path.join(KP, "debug")) as td:
        src(L.MAIN + "/tools/usse-asm/probe.py")
        src(L.MAIN + "/tools/usse-asm/usse-asm")
        for nm in ("p1131-green", "p1131-psizes"):
            src(TA_TEMPLATES + "/" + ps[nm].source)
            P.build(ps[nm], pathlib.Path(td), pathlib.Path(TA_TEMPLATES))
        for f in ("p1131-green__0.bin", "p1131-psizes__1.bin"):
            done[f] = open(os.path.join(td, f), "rb").read()
            pub = b(L.R5X + "/bins/" + f)
            if pub != done[f]:
                raise SystemExit("BUILD FAILS: %s differs from r5-render4x's published program" % f)
    return done


TABLE_NOTES = {
    "s0": ["# s0: r5's three controls (E827 ctl-u-1024-n1; E828 j1r; E824 h8; all PASS in r5).  A miss voids the session: every later",
           "# stage's gate is closed."],
    "a": ["# a: H-TPM held out (plan section 2).  a4 is the premise (no hypothesis knob: a fault there stops the stage); a1, a12, a13, a8,",
          "# a9 are where H-TPM says complete and the dead size rules fault; a2, a3, a5, a14 their one-step neighbours (H-TPM: fault);",
          "# a1r replicates a1 only if a1 completed (group a1, at most 1 event); h1, h2 held faults with the TA data read in the hold.",
          "# Fault limit 8 for the stage (6 predicted: a2, a3, a5, a14, h1, h2), strict health after each fault."],
    "t": ["# t: Q293's four rows (plan section 5).  t8 is r5's t6 control (E827); t5, t6 CR_TE_AA 0xc0000000 on the 11.31 line and point;",
          "# t7 the 0x40 triangle with 0x%08x poked into dword 11 before render 2 (E829's shape).  rgn:1: the module refuses TE_AA bits" % T7_VALUE,
          "# 31:30 on a context made without --aa4 unless the knob forces a count.  No fault predicted: the first fault ends the stage."],
}


def write_all(st, hset, bins, twin_rows):
    out = {}
    for n in STAGES:
        s = st[n]
        lines = ["#stage %s" % n, "#limit %d" % LIMIT[n]]
        for nd in s.needs:
            lines.append("#need %s" % nd)
        lines += TABLE_NOTES[n]
        for name, sset, risk, knobs, args in s.rows:
            lines.append("|".join([name, sset, risk, knobs, "-", args]))
        out["tables/%s.txt" % n] = "\n".join(lines) + "\n"
    for s in [st[n] for n in STAGES] + [hset]:
        pl = ["case\tquantity\tvalue\tmodel\tset\tsource"]
        for r in s.preds:
            pl.append("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r))
        out["predictions/%s.tsv" % s.name] = "\n".join(pl) + "\n"
    out["stages.txt"] = "\n".join(STAGES) + "\n"
    out["TABLES.md"] = tables_md(st, hset)
    for nm, data in bins.items():
        out["bins/" + nm] = data
    tw = ["stage\tcase\tneed\ttwins\ttwin_tri1"] + ["\t".join(str(x) for x in r) for r in twin_rows]
    out["gen/data/twins.tsv"] = "\n".join(tw) + "\n"
    ft = ["w\th\tmw\tmh\tseen\trecord\tentries_end\ttd_rgn\t" + "\t".join(R.TPM)]
    for w, h, mw, mh, f, rec in R.RECORDED:
        ft.append("%d\t%d\t%d\t%d\t%s\t%s\t0x%x\t0x%x\t%s" % (w, h, mw, mh, "F" if f else "c", rec, R.entries_end(w, h), R.lay(mw, mh)["rgn"],
                  "\t".join("agree" if R.fault(v, w, h, mw, mh) == bool(f) else "MISS" for v in R.TPM)))
    out["gen/data/recorded_cells.tsv"] = "\n".join(ft) + "\n"
    return out


def tables_md(st, hset):
    L_ = ["# r6-render4x stage A: tables and frozen predictions", "",
          "Generated by gen/rgen.py; the frozen predictions are predictions/*.tsv (hashes in PREDICTIONS.sha256).", ""]
    for n in STAGES:
        s = st[n]
        L_ += ["## %s (%d rows, limit %d)" % (n, len(s.rows), LIMIT[n]), ""]
        for name, sset, risk, knobs, args in s.rows:
            L_ += ["### %s  (%s, %s) knobs [%s]" % (name, sset, risk, knobs), "", "    " + args, ""]
            for case, q, val, model, ps, source in s.preds + hset.preds:
                if case == name and not q.startswith("rule:"):
                    if q == "lost":
                        val = "%d offsets (predictions/h.tsv)" % (val.count(",") + 1)
                    L_.append("- %s = %s  [%s, %s] (%s)" % (q, val, ps, model, source))
            rl = ["%s %s" % (q[5:], val.split(" ")[0]) for case, q, val, model, ps, source in s.preds if case == name and q.startswith("rule:")]
            if rl:
                L_.append("- the other rules (compare, never a verdict): " + ", ".join(rl))
            L_.append("")
    return "\n".join(L_)


def main():
    check = "--check" in sys.argv
    if os.path.exists(os.path.join(KP, "FROZEN.sha256")) and not check:
        print("FROZEN.sha256 exists: the freeze is never rewritten (use --check)")
        return 1
    st, hset, tb, twin_rows = build()
    bins = build_bins()
    out = write_all(st, hset, bins, twin_rows)
    srcl = "".join(p + "\n" for p in sorted(SOURCES))
    out["gen/data/sources.lst"] = srcl
    bad = 0
    for rel, data in sorted(out.items()):
        data_b = data if isinstance(data, bytes) else data.encode()
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != data_b:
                print("DIFFERS: " + rel)
                bad = 1
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data_b)
    print("%s: %d files, %d rows, %d predictions, %d sources" % ("checked" if check else "written", len(out),
          sum(len(s.rows) for s in st.values()), sum(len(s.preds) for s in st.values()) + len(hset.preds), len(SOURCES)))
    return bad


if __name__ == "__main__":
    sys.exit(main())
