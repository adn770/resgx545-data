#!/usr/bin/env python3
"""rgen.py: writes everything r5-render4x generates, before any job: tables/*.txt, predictions/*.tsv, TABLES.md, stages.txt, bins/*.bin
(the line and point programs of stage t), gen/data/*.tsv (the twins, the rule fit) and gen/data/sources.lst.
  rgen.py            write everything (refuses to run once FROZEN.sha256 exists: the freeze is never rewritten)
  rgen.py --check    regenerate into memory and compare with the files on disk (the freeze test uses it)
Plan: closing5/render4x/exp-render4x-r5.md, every decision (a) (DECISIONS-R5.md R5-3, R5-4, R5-6): stages s0, t, o, m, l, x, d; 37 jobs.
Built from R4-G's generator (closing4/r4-render4x/gen/rgen.py).  Two build rules round 4 lacked:
  - every frozen page need comes from a kept TWIN of the row's own argv (gen/twins.py); a control without a twin, or whose twins give
    another count, fails the build (round 4's o2: a default triangle frozen with the full triangle's need);
  - every row that asks for a dump freezes the name its verb gives the dump (rlib.dump_stem; round 4's t scorer looked for NAME.tri.*).
The rule predictions of stages m, l, x, d are gen/rules.py's, computed from each row's argv (target and maximum).
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
STAGES = ["s0", "t", "o", "m", "l", "x", "d"]
LIMIT = {"s0": 1, "t": 1, "o": 1, "m": 4, "l": 5, "x": 3, "d": 1}
TA_TOML = L.MAIN + "/probes/ta/p1131-progs.toml"
TA_TEMPLATES = L.MAIN + "/probes/ta/templates"
SOURCES = []                  # every file read from outside this directory (the freeze pins them by absolute path)
SLOT = 4 << 20                # a parameter slot's TA-data room: 4 MiB


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


def row1xf(w, h):
    """The FULL triangle at 1x (default TE_AA, no pokes: round 4's o8 form)."""
    return ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d %s %s'
            % (w, h, w, h, DUMP, REGS))


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
    tb = TW.table()
    for r in TW.kept_rows():
        src(r[5])
        src(r[6])
    twin_rows = []

    def need(stage, name, args, knobs, sset, model_ok=False, model=None):
        got, tw = TW.need_of(args, knobs, tb)
        if got is None or got == "DISAGREE":
            if model is None or not model_ok:
                raise SystemExit("BUILD FAILS: %s has no usable twin (%s) and no allowed model need" % (name, got))
            twin_rows.append((stage, name, model, "[model] " + "no kept twin", "-"))
            return model, "[model] no kept twin of this argv", None
        tri1 = None
        for s_, n_, _ in tw:
            o = L.read_text(src(os.path.join(TW.DATA, "render", os.path.dirname(s_), n_ + ".txt.gz")))
            tri1 = tri1 or L.tri_counts_text(o)
        twin_rows.append((stage, name, got, "; ".join("%s/%s" % (s_, n_) for s_, n_, _ in tw), tri1 or "-"))
        return got, "kept twins (%d): %s" % (len(tw), ", ".join("%s/%s %d" % (s_.split("/out/")[0], n_, p_) for s_, n_, p_ in tw)), tri1

    # ---- s0: round 4's three controls, unchanged, with their kept hashes ------------------------------------------------------------
    s = st["s0"]
    j5 = t(L.RGN4 + "/j5-ctl-1x.out")
    j1r = t(L.RGN4 + "/j1r-aa4-auto.out")
    h8 = t(L.K2 + "/h8-1024x768-k4.txt.gz")
    j1r_ta = len(b(L.K2 + "/h1-288x144-k4.tri.tadata.bin.gz"))
    h8_ta = len(b(L.K2 + "/h8-1024x768-k4.tri.tadata.bin.gz"))
    rows = [("s0-1x-1024x768", row1x(1024, 768), j5, None, "E827 ctl-u-1024-n1, E828 j5 (closing-r3-rgn4 j5-ctl-1x.out)"),
            ("s0-4x-288x144", row4x(288, 144), j1r, j1r_ta, "E828 j1r (closing-r3-rgn4), E824 h1 (TA data 0x%x)" % j1r_ta),
            ("s0-4x-1024x768", row4x(1024, 768), h8, h8_ta, "E824 h8 (closing-r3k-pixel k-f4)")]
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
        n_, why, _ = need("s0", case, args, "expectdiff", "control")
        s.pred(case, "pb_used", n_, why, "ctl", "gen/data/twins.tsv")
        dump_pred(s, case, args)

    # ---- t: Q293 again (9 jobs, none predicted to fault) -------------------------------------------------------------------------
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
    ln_args = _probe_args(ln_line)
    pt_args = _probe_args(pt_line)
    t1 = ('tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 --aa4 '
          '--poke cmd:1=0x%08x --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 ' + DUMP)
    t6 = ('tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 --poke cmd:1=0x40000000 '
          '--poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 ' + DUMP)
    poke = lambda a, v: a.replace("--pixels", "--cmd 1=0x%08x --pixels" % v, 1)  # noqa: E731
    trows = [("t6-ctl-te40-1array", "control", "expectdiff rgn:1", t6),
             ("t3b-line-base", "control", "-", ln_args),
             ("t4b-point-base", "control", "-", pt_args),
             ("t1-aa4-te40", "replicate", "expectdiff", t1 % 0x40000000),
             ("t2-aa4-te80", "replicate", "expectdiff", t1 % 0x80000000),
             ("t3-line-te40", "replicate", "rgn:1", poke(ln_args, 0x40000000)),
             ("t4-point-te40", "replicate", "rgn:1", poke(pt_args, 0x40000000)),
             ("t3c-line-te80", "heldout", "rgn:1", poke(ln_args, 0x80000000)),
             ("t4c-point-te80", "heldout", "rgn:1", poke(pt_args, 0x80000000))]
    for name, sset, knobs, args in trows:
        tt.row(name, sset, "safe", knobs, args)
        dump_pred(tt, name, args)
    srcp = "E827 rg-pb pb-e40-m2-64a (closing-r3k-regress)"
    tt.pred("t6-ctl-te40-1array", "rc", 1, "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "target_hash", L.target_hash(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "diff", L.diff_text(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "tri1", L.tri_counts_text(e40), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "par_0_64", L.words(e40p, 0, 64), "kept", "ctl", srcp)
    tt.pred("t6-ctl-te40-1array", "tadata_size", len(e40t), "kept", "ctl", srcp)
    w40 = L.dwords(e40p)
    assert w40[11] == 0 and w40[12] == 0x00040101
    mdl = "H-SAME [infer]: the 3D reads the displaced layout with four arrays as with one (E728 on one array); replicate of E847"
    for case in ("t1-aa4-te40", "t2-aa4-te80"):
        tt.pred(case, "dword11", "0x00000000", mdl + "; H-PAD", "rep", srcp + "; E847")
        tt.pred(case, "dword12", "0x00040101", mdl, "rep", srcp + "; E847")
        tt.pred(case, "tri1", L.tri_counts_text(e40), mdl + ": an empty image (E728: 9 of 9 jobs)", "rep", srcp + "; E847")
    for nm, case_b, cases, out, par in [("line", "t3b-line-base", (("t3-line-te40", "rep"), ("t3c-line-te80", "heldout")), ln_out, ln_par),
                                         ("point", "t4b-point-base", (("t4-point-te40", "rep"), ("t4c-point-te80", "heldout")), pt_out, pt_par)]:
        bw = L.dwords(par)
        pos = bw.index(0x00040101)
        sk = "11.31 %s dump (resgx545-data ta/%s)" % (nm, "line-point" if nm == "line" else "points")
        tt.pred(case_b, "rc", 0, "kept", "ctl", sk)
        tt.pred(case_b, "par_0_32", L.words(par, 0, 32), "kept (the probe's parameter-buffer head; tool, module and date differ: the control can fail)", "ctl", sk)
        tt.pred(case_b, "o0", _o0(out), "kept", "ctl", sk)
        for case_t, sset in cases:
            v = "0x80" if "te80" in case_t else "0x40"
            tt.pred(case_t, "rc", 0, "kept form", sset, sk)
            tt.pred(case_t, "insert_pos", pos, "the inserted dword sits right before the first format word 0x00040101 (E847 at %s: %s)" % (v, "replicate" if sset == "rep" else "held out: 0x80 never ran on a line or a point"), sset, sk)
            tt.pred(case_t, "insert_val", "0x00000000", "H-PAD [infer]: the inserted dword is zero for an object that has a width too; H-FIELD: non-zero", sset, sk)
            if sset == "heldout":
                tt.pred(case_t, "image", "empty [infer, reported]", "the 3D reads the displaced layout: nothing drawn (E728's empty image); reported, not scored", "explore", "-")

    # ---- o: overflow at 4x, H-ENOSPC4 (11 jobs, none predicted to fault) -----------------------------------------------------------
    o = st["o"]
    orows = [("o1-1x-1024x768-p35", "control", 0x35, "complete", row1x(1024, 768), False),
             ("o2-1x-1024x768-p34", "control", 0x34, "overflow", row1x(1024, 768), False),
             ("o3-4x-1024x768-pe3", "control", 0xe3, "complete", row4x(1024, 768), False),
             ("o4-4x-1024x768-pe2", "replicate", 0xe2, "overflow", row4x(1024, 768), False),
             ("o5-4x-288x144-p23", "replicate", 0x23, "overflow", row4x(288, 144, dump=False) + " --pixels", False),
             ("o6-4x-640x480-p6e", "heldout", 0x6e, "complete", row4x(640, 480), False),
             ("o7-4x-640x480-p6d", "heldout", 0x6d, "overflow", row4x(640, 480), False),
             ("o8-4x-512x384-p53", "heldout", 0x53, "complete", row4x(512, 384), False),
             ("o9-4x-512x384-p52", "heldout", 0x52, "overflow", row4x(512, 384), False),
             ("o10-1xf-1024x768-p53", "explore", 0x53, "complete", row1xf(1024, 768), True),
             ("o11-1xf-1024x768-p52", "explore", 0x52, "overflow", row1xf(1024, 768), True)]
    for name, sset, pb, oc, args, model_ok in orows:
        knobs = "expectdiff pb:0x%02x strict" % pb
        o.row(name, sset, "safe", knobs, args)
        dump_pred(o, name, args)
        w, h = (1024, 768) if "1024x768" in name else (288, 144) if "288x144" in name else (640, 480) if "640x480" in name else (512, 384)
        n_, why, tri1 = need("o", name, args, knobs, sset, model_ok=model_ok, model=M.u1_full(w, h) if model_ok else None)
        rule_ok = (M.usable(pb) >= n_) == (oc == "complete")
        assert rule_ok, (name, pb, n_, oc)
        ps = {"control": "ctl", "replicate": "rep", "heldout": "heldout", "explore": "explore"}[sset]
        o.pred(name, "need", n_, why, ps, "gen/data/twins.tsv")
        o.pred(name, "tri1_scene", tri1 or "%d triangle, 0 background, 0 other" % (w * h),
               "the scene the need was frozen for (the twin's kept triangle counts; the tool's own --mock must print them: tests/mock_all.py)" if tri1 else
               "[model] the full triangle covers the target", "census", "gen/data/twins.tsv")
        txt = "page rule: completes when P - 0x22 >= need (E625, E735, E773): 0x%x - 0x22 = %d %s %d" % (pb, M.usable(pb), ">=" if oc == "complete" else "<", n_)
        if oc == "overflow":
            txt += "; H-ENOSPC4 [infer, E846 post hoc]: an overflowing 4x scene ends in -ENOSPC with no BIF line, as at 1x (E311, E438, E412)" if "4x" in name else "; -ENOSPC, no fault, at 1x (E311, E438, E412)"
        o.pred(name, "outcome", oc, txt, ps, "E846" if "4x" in name else "E735")
        if oc == "complete":
            o.pred(name, "diff", "0 of %d pixels" % (w * h), "a completed render draws exactly", ps, "E824 / E827")
            o.pred(name, "pb_used", n_, "the scene pages of the completed render's dump = its need", ps, "gen/data/twins.tsv")
    o.pred("o10-1xf-1024x768-p53", "e846_correction", "if 49 is measured: E846's 'the frozen need 97 is the model of the full triangle' needs an appended correction (the model was wrong for 1x)", "exp 1.6", "explore", "E846")

    # ---- m, l, x, d: Q292's cause and onset (rules.py from each row's argv) ---------------------------------------------------------
    qrows = {"m": [("m0-1024x768-max2048x2048", "control", 1024, 768, 2048, 2048),
                   ("m1-1280x1024-max1280x1040", "heldout", 1280, 1024, 1280, 1040),
                   ("m2-1280x1024-max2048x2048", "heldout", 1280, 1024, 2048, 2048),
                   ("m3-1280x1024-max2048x1024", "control", 1280, 1024, 2048, 1024),
                   ("m4-2048x1536-max4096x4096", "heldout", 2048, 1536, 4096, 4096)],
             "l": [("l1-2048x240", "heldout", 2048, 240, 2048, 240), ("l2-256x1536", "heldout", 256, 1536, 256, 1536),
                   ("l3-768x2048", "heldout", 768, 2048, 768, 2048), ("l4-1280x768", "heldout", 1280, 768, 1280, 768),
                   ("l5-1024x1024", "heldout", 1024, 1024, 1024, 1024)],
             "x": [("x1-1024x512", "explore", 1024, 512, 1024, 512), ("x2-1184x768", "explore", 1184, 768, 1184, 768),
                   ("x3-1024x800", "explore", 1024, 800, 1024, 800)],
             "d": [("d1-1280x1024-held", "explore", 1280, 1024, 1280, 1024)]}
    for stn, lst in qrows.items():
        q = st[stn]
        for name, sset, w, h, mw, mh in lst:
            assert w % 2 == 0 and h % 2 == 0 and max(w, h, mw, mh) <= 4096 and M.tadata_4x(mw, mh) <= SLOT and R.u4(w, h) <= M.usable(M.PB_PAGES)
            if stn == "d":
                args, knobs = row4x(w, h, mw, mh, dump=False), "expectdiff held dumpheld strict hypo:q292:%d" % LIMIT[stn]
            elif name.startswith("m0"):
                args, knobs = row4x(w, h, mw, mh), "expectdiff strict"
            else:
                args, knobs = row4x(w, h, mw, mh), "expectdiff strict hypo:q292:%d" % LIMIT[stn]
            q.row(name, sset, "risky" if any(R.fault(r, w, h, mw, mh) is not False for r in R.RULES) else "safe", knobs, args)
            dump_pred(q, name, args)
            ps = {"control": "ctl", "heldout": "heldout", "explore": "explore"}[sset]
            for r in R.RULES:
                q.pred(name, "rule:" + r, R.pred_word(r, w, h, mw, mh), "rules.py from the argv (target %dx%d, maximum %dx%d)" % (w, h, mw, mh), ps, "gen/rules.py; exp 1.4")
            htpc = {R.pred_word(r, w, h, mw, mh) for r in R.HTPC}
            q.pred(name, "htpc", htpc.pop() if len(htpc) == 1 else "split", "H-TPC's four variants" + (" agree" if not htpc else ""), ps, "gen/rules.py")
            q.pred(name, "fault_int", "0x0100", "the 3D-side word of every 4x fault on record (E845, E846 o7, E828 j4)", ps, "E845")
            q.pred(name, "fault_page", "0x10000", "the request base: a zeroed header reads as a stream at offset 0 [infer, exp 1.2]", ps, "E845")
            q.pred(name, "diff", "0 of %d pixels" % (w * h), "a completed 4x full triangle draws exactly (E824)", ps, "E824")
            q.pred(name, "pb_used", R.u4(w, h), "page model U4 = 1 + ceil(2 tiles16 / 32) (fit E824's ten dumps; R4-G p held 1 of 1 at 1280 x 1024 before the fault)", "model", "gen/pbmodel.py")
            q.pred(name, "tadata_size", M.tadata_4x(mw, mh), "the layout of the CONTEXT'S maximum, four arrays (sgx_render.c; R4-G p 1 of 1)", "model", "gen/pbmodel.py")
            q.pred(name, "hdr_off", 0, "the doubled-grid rule (exp 1.2, fit 12 of 12): grid of the target, base td.rgn of the maximum [infer]", "model", "gen/rlib.py headers")
            if stn == "d":
                q.pred(name, "held_pages", R.u4(w, h), "H-TPC: the TA finished: the held parameter dump has U4 scene pages", "explore", "gen/rules.py")
                for v, lim in (("d", R.extent(R.lay(w, h), "d")), ("rs", R.extent(R.lay(w, h), "rs")), ("rb", R.extent(R.lay(w, h), "rb"))):
                    q.pred(name, "hdr_zero_below_" + v, "0x%x" % lim, "H-TPC %s: the headers off the rule all lie below this offset of the TA data, header 0 among them, every header past it on the rule" % v, "explore", "gen/rules.py")
                q.pred(name, "held_short", "a held dump shorter than a page is 'held dump not read' (o5's kept 62- and 63-byte files): the dump lines cannot tell", "exp 1.5, 3.5", "explore", "R4-G o5")
    return st, tb, twin_rows


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
    """The line and point programs of stage t, assembled from probes/ta/p1131-progs.toml and compared with R4-G's published copies."""
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
            pub = b(L.R4G + "/bins/" + f)
            if pub != done[f]:
                raise SystemExit("BUILD FAILS: %s differs from R4-G's published program" % f)
    return done


TABLE_NOTES = {
    "s0": ["# s0: round 4's three controls (E827 ctl-u-1024-n1; E828 j1r; E824 h8).  A miss voids the session: every later stage's gate is closed."],
    "t": ["# t: Q293 again with the dump names fixed.  t6, t3b, t4b are the controls; t1 to t4 replicate E847; t3c, t4c (0x80 on a line and a",
          "# point) are held out.  rgn:1: the module refuses TE_AA bits 31:30 on a context made without --aa4 unless the knob forces a count."],
    "o": ["# o: overflow at 4x, H-ENOSPC4.  o1, o2 the default triangle at its measured need (19, 3 kept twins); o3 the 4x control; o4, o5",
          "# replicates; o6 to o9 held out; o10, o11 the 1x full pair (explore).  No fault predicted: the first fault-class event ends the stage."],
    "m": ["# m: the same size with more room (H-TPC against every size rule).  m0 and m3 are the controls that can fail; a fault in m0 stops",
          "# the stage (no hypothesis knob).  Fault limit 4, strict health after each fault."],
    "l": ["# l: width, height and count apart (five jobs, one column a rule).  Fault limit 5, strict health after each fault."],
    "x": ["# x: which H-TPC variant (exploratory).  Runs only if stage m held H-TPC (the gate).  Fault limit 3."],
    "d": ["# d: E845's 1280 x 1024 held, its dumps read in the hold (exploratory, last).  Fault limit 1."],
}


def write_all(st, bins, tb, twin_rows):
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
        pl = ["case\tquantity\tvalue\tmodel\tset\tsource"]
        for r in s.preds:
            pl.append("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r))
        out["predictions/%s.tsv" % n] = "\n".join(pl) + "\n"
    out["stages.txt"] = "\n".join(STAGES) + "\n"
    out["TABLES.md"] = tables_md(st)
    for nm, data in bins.items():
        out["bins/" + nm] = data
    tw = ["stage\tcase\tneed\ttwins\ttwin_tri1"] + ["\t".join(str(x) for x in r) for r in twin_rows]
    out["gen/data/twins.tsv"] = "\n".join(tw) + "\n"
    ft = ["w\th\tseen\trecord\t" + "\t".join(R.RULES)]
    for w, h, f, rec, d in R.fit_table():
        ft.append("%d\t%d\t%s\t%s\t%s" % (w, h, "F" if f else "c", rec, "\t".join("agree" if d[r] else "DISAGREE" for r in R.RULES)))
    out["gen/data/rules_fit.tsv"] = "\n".join(ft) + "\n"
    return out


def tables_md(st):
    L_ = ["# r5-render4x: tables and frozen predictions", "",
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
    st, tb, twin_rows = build()
    bins = build_bins()
    out = write_all(st, bins, tb, twin_rows)
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
          sum(len(s.rows) for s in st.values()), sum(len(s.preds) for s in st.values()), len(SOURCES)))
    return bad


if __name__ == "__main__":
    sys.exit(main())
