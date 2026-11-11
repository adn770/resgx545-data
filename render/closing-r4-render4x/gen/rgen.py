#!/usr/bin/env python3
"""rgen.py: writes everything R4-G (r4-render4x) generates, before any job: tables/*.txt, predictions/*.tsv, TABLES.md, stages.txt,
bins/*.bin (the staged cube and TA programs), gen/data/*.tsv (what was extracted from kept data, and the model fit).
  rgen.py            write everything (refuses to run once FROZEN.sha256 exists: the freeze is never rewritten)
  rgen.py --check    regenerate into memory and compare with the files on disk (the freeze test uses it)
Plan: closing4/render4x/exp-render4x-r4.md section 3 (decisions as recommended: scope a, four H cells last, o8 last in O) plus the
Q113 held-out cube row of decision R4-3 (stage c).  The numbers are read from the kept records, never typed: S0's hashes from E824,
E827, E828; the cube control and the faces from E726; the T baselines from the 11.31 line and point dumps and E827's rg-pb.  The
page-need model is gen/pbmodel.py, fitted on E824's ten dumps (gen/data/pbfit.tsv); everything it predicts at a larger size is held
out.  A prediction that no record supports is a model and says so in its `model` column ([infer] where the name is ours).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cubegen as C  # noqa: E402
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402

KP = L.KP
S4X = "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"
REGS = "--regs 0x0700-0x072c"
STAGES = ["s0", "c", "p", "o", "t", "h"]
LIMIT = {"s0": 1, "c": 1, "p": 2, "o": 5, "t": 1, "h": 5}
ASM = L.MAIN + "/tools/usse-asm/usse-asm"
TA_TOML = L.MAIN + "/probes/ta/p1131-progs.toml"
TA_TEMPLATES = L.MAIN + "/probes/ta/templates"
CUBE_TEMPLATE = L.DATA + "/texture/p1141/templates/tx_map.s"
SOURCES = []                  # every file read from outside this directory (the freeze pins them by absolute path)


def src(p):
    if p not in SOURCES:
        SOURCES.append(p)
    return p


def t(path):
    return L.read_text(src(path))


def b(path):
    return L.read_bytes(src(path))


def row4x(w, h):
    return ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d --aa4 %s '
            '--dump-render "$W/dump" %s' % (w, h, w, h, S4X, REGS))


def row1x(w, h, n=1):
    return ('tri --width %d --height %d -n %d --keep-going --keep-overflow --wait-ms 20000 --dump-render "$W/dump" %s' % (w, h, n, REGS))


def row_c1(w, h):
    """The c1 / j2 shape: the 4x words on a one-array context (E729, E828 j2, K2 c1): a TA write fault at the end of the TA data."""
    return ('tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d %s' % (w, h, w, h, S4X))


class Stage:
    def __init__(self, name):
        self.name, self.rows, self.needs, self.notes = name, [], [], []
        self.preds = []

    def row(self, name, sset, risk, knobs, args):
        self.rows.append((name, sset, risk, knobs, args))

    def pred(self, case, q, val, model, sset, source):
        self.preds.append((case, q, str(val), model, sset, source))


def build():
    st = {n: Stage(n) for n in STAGES}
    fit = []

    # ---- the page model: fitted on E824's ten dumps, post hoc [infer] ------------------------------------------------------------
    for name, w, h in [("c2-64x64-k4", 64, 64), ("c3-64x64-k1", 64, 64), ("h1-288x144-k4", 288, 144), ("h2-256x288-k4", 256, 288),
                       ("h3-384x384-k4", 384, 384), ("h4-320x160-k4", 320, 160), ("h5-512x384-k4", 512, 384),
                       ("h6-640x480-k4", 640, 480), ("h7-320x400-k4", 320, 400), ("h8-1024x768-k4", 1024, 768)]:
        pb = b("%s/%s.tri.param.bin.gz" % (L.K2, name))
        ta = b("%s/%s.tri.tadata.bin.gz" % (L.K2, name))
        fit.append((name, w, h, M.pages_nonzero(pb), M.pages_nonzero_all(pb), M.u4(w, h), M.u4_rank(w, h), len(ta), M.tadata_4x(w, h)))
    with open(os.path.join(HERE, "data", "pbfit.tsv"), "w") as f:
        f.write("job\tw\th\tnonzero_0_421\tnonzero_all\tu4\tu4_rank\ttadata_size\ttadata_model\n")
        for r in fit:
            f.write("\t".join(str(x) for x in r) + "\n")

    # ---- s0: the controls (3 jobs) ---------------------------------------------------------------------------------------------
    s = st["s0"]
    j5 = t(L.RGN4 + "/j5-ctl-1x.out")
    j1r = t(L.RGN4 + "/j1r-aa4-auto.out")
    h8 = t(L.K2 + "/h8-1024x768-k4.txt.gz")
    j1r_ta = len(b(L.K2 + "/h1-288x144-k4.tri.tadata.bin.gz"))
    h8_ta = len(b(L.K2 + "/h8-1024x768-k4.tri.tadata.bin.gz"))
    s.row("s0-1x-1024x768", "control", "safe", "expectdiff", row1x(1024, 768))
    s.row("s0-4x-288x144", "control", "safe", "expectdiff", row4x(288, 144))
    s.row("s0-4x-1024x768", "control", "safe", "expectdiff", row4x(1024, 768))
    for case, text, w, h, e, u, ta_size, source in [
            ("s0-1x-1024x768", j5, 1024, 768, None, M.u1(1024, 768), None, "E827 ctl-u-1024-n1, E828 j5 (closing-r3-rgn4 j5-ctl-1x.out)"),
            ("s0-4x-288x144", j1r, 288, 144, True, M.u4(288, 144), j1r_ta, "E828 j1r (closing-r3-rgn4), E824 h1 (TA data 0x%x)" % j1r_ta),
            ("s0-4x-1024x768", h8, 1024, 768, True, M.u4(1024, 768), h8_ta, "E824 h8 (closing-r3k-pixel k-f4)")]:
        s.pred(case, "rc", 0, "kept", "ctl", source)
        s.pred(case, "echo", L.echo(text), "kept", "ctl", source)
        s.pred(case, "target_hash", L.target_hash(text), "kept", "ctl", source)
        s.pred(case, "diff", L.diff_text(text), "kept", "ctl", source)
        s.pred(case, "tri1", L.tri_counts_text(text), "kept", "ctl", source)
        s.pred(case, "renders", L.renders(text), "kept", "ctl", source)
        if ta_size:
            s.pred(case, "tadata_size", ta_size, "kept", "ctl", source)
            s.pred(case, "pb_used", u, "page model U4 (fit post hoc on E824's ten dumps; this row is in the fit)", "ctl", "gen/data/pbfit.tsv")
            s.pred(case, "reg0724", "0x%04x%04x" % (u - 1, u - 1), "K2 c1's held reading (0x000b000b at 288 x 144), applied as U4 - 1 in both halves [infer]", "rep", "closing4/render4x/c1.snap1.txt")
        else:
            s.pred(case, "pb_used", u, "page model U1 [infer: no 1x scene was measured at this form]", "rep", "gen/pbmodel.py")

    # ---- c: Q113's held-out cube row (decision R4-3), after s0 ------------------------------------------------------------------
    c = st["c"]
    cube_dir = L.DATA + "/texture/p1141"
    for n in ("p1141-cube__4",):
        src("%s/stage-bins/%s.bin" % (cube_dir, n))
    xn = t(L.CUBE + "/cu-xn.txt.gz")
    c.needs = ["$S/p1141-cube__4.bin", "$S/r4g-cube-a.bin", "$S/r4g-cube-b.bin"]
    c.row("c-cu-xn", "control", "safe", "-", 'probe --temps 32 --coords --pixels "$S/p1141-cube__4.bin"')
    c.row("c-cube-a", "heldout", "safe", "-", 'probe --temps 32 --coords --pixels "$S/r4g-cube-a.bin"')
    c.row("c-cube-b", "heldout", "safe", "-", 'probe --temps 32 --coords --pixels "$S/r4g-cube-b.bin"')
    obs = C.observed(xn)
    fx, _ = C.faces(*C.E726["cu-xn"])
    assert (obs == fx).all()
    c.pred("c-cu-xn", "rc", 0, "kept", "ctl", "E726 cu-xn")
    c.pred("c-cu-xn", "faces_hist", ",".join(str(x) for x in C.hist(obs)), "kept", "ctl", "E726 cu-xn (face 1 on 2048 of 2048)")
    c.pred("c-cu-xn", "pix_sha256", L.sha256(",".join("%08x" % int(v) for v in _pixels(xn)).encode()), "kept", "ctl", "E726 cu-xn (the recompute's canonical hash)")
    for nm, spec in C.HELDOUT.items():
        case = "c-" + nm.replace("r4g-", "")
        f, gap = C.faces(*spec)
        c.pred(case, "rc", 0, "kept form of E726's probes", "heldout", "gen/cubegen.py")
        c.pred(case, "faces_hist", ",".join(str(x) for x in C.hist(f)), "dominant-axis rule [infer, post hoc from E726's 8 jobs; fits 8 of 8 here]", "heldout", "gen/cubegen.py")
        c.pred(case, "faces_sha256", C.faces_sha256(f), "the same rule, per pixel (raster order)", "heldout", "gen/cubegen.py")
        c.pred(case, "min_gap", "%.7f" % float(gap.min()), "smallest gap between the two largest magnitudes over the 2048 pixels", "model", "gen/cubegen.py")

    # ---- p: the 4x page need, held out (6 jobs) --------------------------------------------------------------------------------
    p = st["p"]
    for w, h in [(1280, 1024), (2048, 1536), (2048, 1920), (4096, 960), (960, 4096), (3072, 1280)]:
        case = "p-%dx%d" % (w, h)
        p.row(case, "heldout", "safe", "expectdiff hypo:p:2", row4x(w, h))
        u = M.u4(w, h)
        assert M.u4_rank(w, h) == u + 3 and u < M.usable(M.PB_PAGES), (w, h)
        n = w * h
        mdl = "page model U4 = 1 + ceil(2 tiles16 / 32); TA data = layout_f4 formula (fit: E824's ten dumps; this size is held out)"
        s_ = "fit/held: 10 of 10 in the fit, this row held out"
        p.pred(case, "rc", 0, "H-PB: completes", "heldout", s_)
        p.pred(case, "echo", "%dx%d" % (w, h), "kept form", "heldout", "gen")
        p.pred(case, "diff", "0 of %d pixels" % n, "H-PB: 0 wrong (every 4x full triangle in the fit drew 0 wrong)", "heldout", "E824")
        p.pred(case, "tri1", "%d triangle, 0 background, 0 other" % n, "the full triangle covers the target (E824 h1-h8, E828 j1r)", "heldout", "E824")
        p.pred(case, "renders", "1 renders ok", "kept form", "heldout", "E824")
        p.pred(case, "tadata_size", M.tadata_4x(w, h), mdl, "heldout", "gen/pbmodel.py")
        p.pred(case, "pb_used", u, mdl, "heldout", "gen/pbmodel.py")
        p.pred(case, "reg0724", "0x%04x%04x" % (u - 1, u - 1), "U4 - 1 in both halves [infer from one held reading]; reported, gated by the two 4x controls of s0", "rep", "c1.snap1.txt")

    # ---- o: overflow at 4x (8 jobs, o6 only if o5 faults) ------------------------------------------------------------------------
    o = st["o"]
    need1, need4 = M.u1(1024, 768), M.u4(1024, 768)
    assert (need1, need4) == (97, 193) and M.usable(0x83) == 97 and M.usable(0x82) == 96 and M.usable(0xe3) == 193 and M.usable(0xe2) == 192
    o.row("o1-1x-1024x768-p83", "control", "safe", "expectdiff pb:0x83", row1x(1024, 768))
    o.row("o2-1x-1024x768-p82", "control", "safe", "expectdiff pb:0x82", row1x(1024, 768))
    o.row("o3-4x-1024x768-pe3", "control", "safe", "expectdiff pb:0xe3", row4x(1024, 768))
    o.row("o4-4x-1024x768-pe2", "heldout", "risky", "expectdiff pb:0xe2 strict hypo:o:4", row4x(1024, 768))
    o.row("o5-4x-288x144-p23-held", "heldout", "risky", "expectdiff pb:0x23 held dumpheld strict hypo:o:4",
          row4x(288, 144).replace(" --dump-render \"$W/dump\" " + REGS, " --pixels"))
    o.row("o6-4x-288x144-p23-fill7", "exploratory", "risky", "expectdiff pb:0x23 held dumpheld strict needs:o5-4x-288x144-p23-held=fault hypo:o:4",
          row4x(288, 144).replace(" --dump-render \"$W/dump\" " + REGS, " --pixels --tadata-fill-render 1:7:0x00012340"))
    o.row("o7-4x-4096x1152-p422", "heldout", "risky", "expectdiff strict hypo:o:4", row4x(4096, 1152))
    o.row("o8-1x-4096x4096-p422", "heldout", "risky", "expectdiff strict hypo:o8:1",
          'tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 4096 --height 4096 --max-width 4096 --max-height 4096 '
          '--dump-render "$W/dump" ' + REGS)
    mdl_ok = "page rule: completes when P - 0x22 >= need (E625, E735, E773); need U1 97 [model] / U4 193 [fit]"
    for case, w, h, mode in [("o1-1x-1024x768-p83", 1024, 768, "1x"), ("o3-4x-1024x768-pe3", 1024, 768, "4x")]:
        o.pred(case, "outcome", "complete", mdl_ok, "ctl", "E735, E773, E824 h8")
        o.pred(case, "diff", "0 of %d pixels" % (w * h), mdl_ok, "ctl", "E827 / E824")
    o.pred("o2-1x-1024x768-p82", "outcome", "overflow", "the same rule: 0x82 - 0x22 = 96 < 97 (-ENOSPC, no fault at 1x: E311, E438, E412)", "ctl", "E735")
    for case in ("o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held", "o7-4x-4096x1152-p422"):
        why = {"o4-4x-1024x768-pe2": "0xe2 - 0x22 = 192 < 193", "o5-4x-288x144-p23-held": "0x23 - 0x22 = 1 < 12",
               "o7-4x-4096x1152-p422": "1024 < 1153"}[case]
        mdl = "H-SPM4 [infer]: an overflowing 4x scene faults on the 3D side (%s); the word is E828 j4's and E511's HS family" % why
        o.pred(case, "outcome", "fault", mdl, "heldout", "E828 j4, E511")
        o.pred(case, "fault_int", "0x0100", mdl, "heldout", "E828 j4 (BIF_INT_STAT 0x90100, bits 15:0)")
        o.pred(case, "fault_page", "0x10000", mdl, "heldout", "E828 j4 (BIF_FAULT 0x1000001x), hw_spec 5.5")
        o.pred(case, "fault_sb", 1, mdl, "heldout", "E828 j4, E511")
    o.pred("o4-4x-1024x768-pe2", "other_outcome", "-ENOSPC, no fault", "the refuting reading: 4x gives -ENOSPC like 1x (the fault is about the size)", "alt", "-")
    o.pred("o6-4x-288x144-p23-fill7", "frozen_either_or", "page leaves 0x10000 | stays 0x10000",
           "exploratory: page 7 is the ext-Z region-header page of a 288 x 144 four-array context; leaves = the 3D read a header from that buffer", "explore", "-")
    o.pred("o8-1x-4096x4096-p422", "outcome", "overflow", "U1(4096 x 4096) = 2049 > 1024 [model]: -ENOSPC, no fault, as at 1x everywhere (E311, E438, E412); a fault would say j4 is not about 4x", "heldout", "E828 j4")

    # ---- t: Q293, dword 11 (6 jobs + the two in-session baselines of the line and point rows) ----------------------------------------
    tt = st["t"]
    tt.needs = ["$S/p1131-green__0.bin", "$S/p1131-psizes__1.bin"]
    rg = lambda n, ext: L.REG + "/" + n + ext  # noqa: E731
    e40 = t(rg("pb-e40-m2-64a", ".txt.gz"))
    e40p = b(rg("pb-e40-m2-64a", ".tri.param.bin.gz"))
    e40t = b(rg("pb-e40-m2-64a", ".tri.tadata.bin.gz"))
    ln_line = _case_args(L.DATA + "/ta/line-point/cases.tsv", "ln-ctl64-r1")
    pt_line = _case_args(L.DATA + "/ta/points/cases.tsv", "pp-c-s1")
    ln_out = t(L.LINE + "/ln-ctl64-r1.txt.gz")
    pt_out = t(L.POINT + "/pp-c-s1.txt.gz")
    ln_par = b(L.LINE + "/ln-ctl64-r1.param.bin.gz")
    pt_par = b(L.POINT + "/pp-c-s1.param.bin.gz")
    green, psizes1 = '"$S/p1131-green__0.bin"', '"$S/p1131-psizes__1.bin"'
    ln_args = _probe_args(ln_line, green)
    pt_args = _probe_args(pt_line, psizes1)
    t1 = ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 --aa4 '
          '--poke cmd:1=0x%08x --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 --dump-render "$W/dump"')
    tt.row("t1-aa4-te40", "heldout", "safe", "expectdiff", t1 % 0x40000000)
    tt.row("t2-aa4-te80", "heldout", "safe", "expectdiff", t1 % 0x80000000)
    tt.row("t3b-line-base", "control", "safe", "-", ln_args)
    tt.row("t3-line-te40", "heldout", "safe", "rgn:1", ln_args.replace("--pixels", "--cmd 1=0x40000000 --pixels"))
    tt.row("t4b-point-base", "control", "safe", "-", pt_args)
    tt.row("t4-point-te40", "heldout", "safe", "rgn:1", pt_args.replace("--pixels", "--cmd 1=0x40000000 --pixels"))
    tt.row("t6-ctl-te40-1array", "control", "safe", "expectdiff rgn:1",
           'tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 --poke cmd:1=0x40000000 '
           '--poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 --dump-render "$W/dump"')
    srcp = "E827 rg-pb pb-e40-m2-64a (closing-r3k-regress)"
    tt.pred("t6-ctl-te40-1array", "rc", 1, "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "target_hash", L.target_hash(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "diff", L.diff_text(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "tri1", L.tri_counts_text(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "par_0_64", L.words(e40p, 0, 64), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "tadata_size", len(e40t), "kept", "ctl", srcp)
    # the object's insertion in the tri job: dword 11 is the inserted zero, the format word moves from dword 11 to 12 (E728)
    w40 = L.dwords(e40p)
    assert w40[11] == 0 and w40[12] == 0x00040101
    mdl = "H-SAME [infer]: the 3D reads the displaced layout with four arrays as with one (E728 on one array)"
    for case in ("t1-aa4-te40", "t2-aa4-te80"):
        tt.pred(case, "dword11", "0x00000000", mdl + "; H-PAD", "heldout", srcp)
        tt.pred(case, "dword12", "0x00040101", mdl, "heldout", srcp)
        tt.pred(case, "tri1", L.tri_counts_text(e40), mdl + ": an empty image (E728: 9 of 9 jobs)", "heldout", srcp)
    for nm, case_b, case_t, out, par, ln in [("line", "t3b-line-base", "t3-line-te40", ln_out, ln_par, ln_line),
                                              ("point", "t4b-point-base", "t4-point-te40", pt_out, pt_par, pt_line)]:
        bw = L.dwords(par)
        pos = bw.index(0x00040101)
        sk = "11.31 %s dump (resgx545-data ta/%s)" % (nm, "line-point" if nm == "line" else "points")
        tt.pred(case_b, "rc", 0, "kept", "ctl", sk)
        tt.pred(case_b, "par_0_32", L.words(par, 0, 32), "kept (the probe's parameter-buffer head; tool, module and date differ: the control can fail)", "ctl", sk)
        tt.pred(case_b, "o0", _o0(out), "kept", "ctl", sk)
        tt.pred(case_t, "rc", 0, "kept form", "heldout", sk)
        tt.pred(case_t, "insert_pos", pos, "the inserted dword sits right before the first format word 0x00040101 [infer: in the tri job it sits at dword 11, before the format word that moves to 12]", "heldout", sk)
        tt.pred(case_t, "insert_val", "0x00000000", "H-PAD [infer]: the inserted dword is zero for an object that has a width too; H-FIELD: non-zero", "heldout", sk)
        tt.pred(case_t, "baseline_head", L.words(par, 0, 32), "the in-session baseline row's head (and the kept dump's)", "model", sk)

    # ---- h: the four health-replay cells (stage h, last) ---------------------------------------------------------------------------
    h = st["h"]
    cells = [("h1-288x144-health", 288, 144, "health", 0x20006061, "c1 (K2 E824), E828 j2, E729: page 0x20006"),
             ("h2-640x480-health", 640, 480, "health", 0x2000a061, "E507: page 0x2000a (the low 12 bits 0x061 as c1 and f2); never seen in a health fault"),
             ("h3-288x144-ctx", 288, 144, "ctx", 0x20006061, "c1 (K2 E824), E828 j2"),
             ("h4-288x144-fill", 288, 144, "fill", 0x20006061, "c1 (K2 E824), E828 j2")]
    for case, w, hh, kind, word, source in cells:
        h.row(case, "heldout", "risky", "held rgn:1 expectdiff hypo:h:4 cell:%s" % kind, row_c1(w, hh))
        h.pred(case, "job_class", "fault", "E729, E828 j2, E824 c1: the c1 shape faults", "heldout", source)
        h.pred(case, "job_int", "0x90004", "BIF_INT_STAT of a TA write fault", "heldout", source)
        h.pred(case, "job_word", "0x%08x" % word, "the TA data ends at the page the fault names (layout formula)", "heldout", source)
        mdl = "H-REPLAY [infer]: the TA's pending region-header write survives the soft reset and is issued again when the TA next runs"
        if kind == "health":
            h.pred(case, "replay_word", "0x%08x" % word, mdl + ": every failing health triangle reads the failed job's own word (4 of 4 in K2)", "heldout", "closing3/netconsole-r3k.log")
            h.pred(case, "health_own_word", "0x20006", mdl + ": a health fault at the health context's own first unmapped page 0x20006 REFUTES the replay (control that can fail)", "ctl" if case.startswith("h2") else "model", "layout formula")
        elif kind == "ctx":
            h.pred(case, "ctx_step", "ok", mdl + ": a 64 x 64 triangle on a context for 1024 x 768 maps the page: no fault", "heldout", "layout formula")
        else:
            h.pred(case, "fill_step", "ok", mdl + ": a fill runs no TA and draws", "heldout", "-")
            h.pred(case, "replay_word", "0x%08x" % word, mdl + ": the first health triangle after the fill still faults at the job's word", "heldout", source)
    return st, fit


def _pixels(text):
    import re
    vals = []
    for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", text, re.M):
        vals += [int(x, 16) for x in m.group(2).split()]
    return vals


def _o0(text):
    import re
    m = re.search(r"o0 (mixed .*|[^\n]*)$", text or "", re.M)
    return m.group(1).strip() if m else None


def _case_args(cases_tsv, name):
    for ln in t(cases_tsv).splitlines():
        f = ln.split("\t")
        if f[0] == name:
            return f[5]
    raise KeyError(name)


def _probe_args(line, binq):
    """A 11.31 job's kept command made into a row: the staged programs, the dump directory and the pixels from this session's."""
    import re
    a = line
    a = re.sub(r"--dump-render \S+", '--dump-render "$W/dump"', a)
    a = re.sub(r"/home/jtorra/sgxprobes-stage/p1131-green__0\.bin", '"$S/p1131-green__0.bin"', a)
    a = re.sub(r"/home/jtorra/sgxprobes-stage/p1131-psizes__1\.bin", '"$S/p1131-psizes__1.bin"', a)
    if "--pixels" not in a:
        a = a.replace("--dump-render", "--pixels --dump-render")
    return a


def build_bins(out_dir):
    """The staged programs: the cube probes of stage c and the line and point programs of stage t, assembled here and compared with
    the published ones (the builder must reproduce E726's cu-xn and the 11.31 programs byte for byte)."""
    os.makedirs(out_dir, exist_ok=True)
    template = t(CUBE_TEMPLATE)
    done = {}
    for nm, spec in C.HELDOUT.items():
        done[nm + ".bin"] = C.assemble(src(ASM), C.program_text(template, *spec), os.path.join(KP, "debug", "asm-%s.bin" % nm))
    done["p1141-cube__4.bin"] = b(L.DATA + "/texture/p1141/stage-bins/p1141-cube__4.bin")
    sys.path.insert(0, L.MAIN + "/tools/usse-asm")
    import pathlib
    import probe as P
    ps = {p.name: p for p in P.load(pathlib.Path(src(TA_TOML)))}
    import tempfile
    with tempfile.TemporaryDirectory(dir=os.path.join(KP, "debug")) as td:
        src(L.MAIN + "/tools/usse-asm/probe.py")
        for nm in ("p1131-green", "p1131-psizes"):
            src(TA_TEMPLATES + "/" + ps[nm].source)
            P.build(ps[nm], pathlib.Path(td), pathlib.Path(TA_TEMPLATES))
        done["p1131-green__0.bin"] = open(td + "/p1131-green__0.bin", "rb").read()
        done["p1131-psizes__1.bin"] = open(td + "/p1131-psizes__1.bin", "rb").read()
    return done


def write_all(st, bins, root):
    for d in ("tables", "predictions", "bins"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    out = {}
    for n in STAGES:
        s = st[n]
        lines = ["#stage %s" % n, "#limit %d" % LIMIT[n]]
        for need in s.needs:
            lines.append("#need %s" % need)
        lines += TABLE_NOTES[n]
        for name, sset, risk, knobs, args in s.rows:
            lines.append("|".join([name, sset, risk, knobs, "-", args]))
        out["tables/%s.txt" % n] = "\n".join(lines) + "\n"
        pl = ["case\tquantity\tvalue\tmodel\tset\tsource"]
        for r in s.preds:
            pl.append("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r))
        out["predictions/%s.tsv" % n] = "\n".join(pl) + "\n"
    out["stages.txt"] = "\n".join(STAGES) + "\n"
    out["TABLES.md"] = tables_md(st)
    for nm, data in bins.items():
        out["bins/" + nm] = data
    return out


TABLE_NOTES = {
    "s0": ["# s0: three controls (E827 ctl-u-1024-n1; E828 j1r; E824 h8).  A miss voids the session: every later stage's gate is closed."],
    "c": ["# c: Q113's held-out cube row (decision R4-3): the control is E726's own cu-xn program; the two held-out programs sample TEXTYPE 2 at",
          "# off-axis directions (all three coordinates non-zero, the dominant axis changing inside the image).  Frozen: the face of every pixel."],
    "p": ["# p: the 4x page need held out (H-PB).  Predicted safe.  Two fault-class events end the stage (limit 2)."],
    "o": ["# o: overflow at 4x.  o1 to o3 are the controls that can fail; o4, o5, o7 are predicted to fault (3D side, hypothesis group o, at most 4",
          "# events: o6 included); o8 (the 1x control of j4) runs last.  strict: the first health fill and triangle after a 3D-side fault must draw."],
    "t": ["# t: Q293.  t6 and the two baselines (t3b, t4b) are the controls; t1, t2 on a four-array context, t3, t4 on one array (rgn:1: the module",
          "# refuses TE_AA bits 31:30 on a context made without --aa4 unless the knob forces a count)."],
    "h": ["# h: Q140, health triangles after a TA write fault.  LAST.  Each cell: the c1-shaped job held (hold_recovery Y), the fault read, a debugfs",
          "# reset, the follow-up, then health triangles one by one until one draws (four at most).  The cell's job faults are the stage's events."],
}


def tables_md(st):
    L_ = ["# R4-G (r4-render4x): tables and frozen predictions", "",
          "Generated by gen/rgen.py; the frozen predictions are predictions/*.tsv (hashes in PREDICTIONS.sha256).", ""]
    for n in STAGES:
        s = st[n]
        L_ += ["## %s (%d rows, limit %d)" % (n, len(s.rows), LIMIT[n]), ""]
        for name, sset, risk, knobs, args in s.rows:
            L_ += ["### %s  (%s, %s) knobs [%s]" % (name, sset, risk, knobs), "", "    " + args, ""]
            for case, q, val, model, ps, source in s.preds:
                if case == name:
                    L_.append("- %s = %s  [%s, %s] (%s)" % (q, val, ps, model, source))
            L_.append("")
    return "\n".join(L_)


def main():
    check = "--check" in sys.argv
    if os.path.exists(os.path.join(KP, "FROZEN.sha256")) and not check:
        print("FROZEN.sha256 exists: the freeze is never rewritten (use --check)")
        return 1
    st, fit = build()
    bins = build_bins(os.path.join(KP, "bins"))
    out = write_all(st, bins, KP)
    with open(os.path.join(HERE, "data", "sources.lst"), "w") as f:
        for p in sorted(SOURCES):
            f.write(p + "\n")
    bad = 0
    for rel, data in sorted(out.items()):
        data_b = data if isinstance(data, bytes) else data.encode()
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != data_b:
                print("DIFFERS: " + rel)
                bad = 1
        else:
            open(p, "wb").write(data_b)
    print("%s: %d files, %d rows, %d predictions, %d sources" % ("checked" if check else "written", len(out),
          sum(len(s.rows) for s in st.values()), sum(len(s.preds) for s in st.values()), len(SOURCES)))
    return bad


if __name__ == "__main__":
    sys.exit(main())
