# SPDX-License-Identifier: MIT
"""Stages p6-rd (58 jobs), p6-l3 (8, optional set L3) and p6-s (22, optional set S, last in the session) of R6-pixel (Q276; plan
closing6/pixel/exp-pixel-r6.md section 2, decisions R6-2 a, pixel decisions 2 a, 3 a, 4 a, 5 a).
Command: R5's C_BASE byte for byte (`probe --tri pixel --temps 32 --pixels` on the 64x64 triangle with the PDS iteration slot, R4's
and R5's shape); p6-s adds exactly two options after `--blk 4=0x00030001`: `--blk 1=0x05d00200 --kpoke rd:9=1` (E406's setup; word 4
as now), and its two restore rows `--kpoke rd:9=0` alone (render details dword 9 is 0 in the kernel's build: the default value, one
poke applied and dropped).  Word layout and tags: R5's (score/o5model.py).  Markers: new ones from 0x181 (R5's end at 0x172).
p6-rd rows, in order:
  controls (14): c-e709 (E709's o4g-3: G-o4), c-u (R4's program: G-o1), c-all4 (R5's program and marker: 5:1), c-ow (the last o0
                 write is the pixel), c-rd-0 (readback through r10 of a register known to hold its word; defines TRI), c-prd-0-k1 and
                 -k7 (the predicate on o0, lane by lane; gates the predicate rows)
  readback rd-1..rd-7 (14, HELD OUT), independent n-rd-1, n-rd-4, x-rd-4, x-rd-5 (8, HELD OUT), predicate prd-3/4-k0,1,2,3,7
  (20, HELD OUT), replicate rd-4 (2).
p6-l3: R5's p3-pa-k0 and -k3 programs byte for byte (the determinism control), new p3-pa-k1, -k2 (HELD OUT).
p6-s: c-s-all4, s-0..s-7, s-n4 under the setup, then r-u (R4's c-u program, --kpoke rd:9=0: the restore check, G-o1).
Every row: knobs `stophang s2` (p6-s: `stophang s2 kpoke`), no regtimeline."""
from __future__ import annotations

import sys

import r5common as K
import r5_o4 as R5O
from r5common import DATA, REPO, Row, build_bin

sys.path.insert(0, str(K.R5 / "score"))
import o5model as M  # noqa: E402
import rdmodel as RM  # noqa: E402

C_BASE = R5O.C_BASE
SETUP = "--blk 4=0x00030001 --blk 1=0x05d00200 --kpoke rd:9=1"
RESTORE = "--blk 4=0x00030001 --kpoke rd:9=0"
C_SETUP = C_BASE.replace("--blk 4=0x00030001", SETUP)
C_RESTORE = C_BASE.replace("--blk 4=0x00030001", RESTORE)
KNOBS = "stophang s2"
KNOBS_S = "stophang s2 kpoke"
M0 = 0x180
R4PIX = DATA / "render/closing-r4-pixel"
R5PIX = DATA / "render/closing-r5-pixel"


def r5_markers():
    return {a: int(b) for a, b in (ln.split("\t") for ln in (R5PIX / "bins/p5o4-markers.tsv").read_text().splitlines() if ln)}


def program(ax, m, cfg):
    """The pixel program of a readback configuration (rdmodel.config)."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    w, j_read, pred = cfg["words"], cfg["read"], cfg["pred"]
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {imm(w[0])}"]
    if pred:
        ops.append(f"xor.testtaz.chan0 !c0, p1, g25, #{pred[1]}")
    if w[1] is not None:
        ops += [f"or.skipinv o1, {pa}, {imm(12 | (w[1] & 0x30))}", f"or.skipinv o1, {pa}, {imm(w[1])}"]
    for j in range(2, 8):
        if pred and j == pred[0]:
            ops += [f"or.skipinv o{j}, {pa}, {imm(w[j])}", f"p1 or.skipinv o{j}, {pa}, {imm(w[j] | 0x10)}"]
        elif w[j] is not None:
            ops.append(f"or.skipinv o{j}, {pa}, {imm(w[j])}")
    ops += [f"mov.skipinv r10, o{j_read}", "mov.skipinv.end o0, r10"]
    return "\n".join(ops) + "\n"


def special(ax, m, name):
    """c-ow, c-rd-0, c-prd-0-kK (plan 2.2).  c-prd-0 ends with an UNPREDICATED write (o7, tag 8) carrying .end: no row of this
    session ends on a predicated instruction (the plan's `p1 or.skipinv.end o0` would end the task under a predicate, a form no kept
    job ran; the deviation is in README.md)."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    head = "phas #0, #0, pixel, end, parallel"
    if name == "c-ow":
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", f"or.skipinv.end o0, {pa}, {imm(0x11)}"]
    elif name == "c-rd-0":
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", "mov.skipinv r10, o0", f"or.skipinv o0, {pa}, {imm(0x31)}",
               "mov.skipinv.end o0, r10"]
    elif name.startswith("c-prd-0-k"):
        k = int(name[len("c-prd-0-k"):])
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", f"xor.testtaz.chan0 !c0, p1, g25, #{k}",
               f"p1 or.skipinv o0, {pa}, {imm(0x11)}", f"or.skipinv.end o7, {pa}, {imm(0x08)}"]
    else:
        raise ValueError(name)
    return "\n".join(ops) + "\n"


class Builder:
    def __init__(self, stage, m0):
        self.stage, self.m = stage, m0
        self.rows, self.preds, self.needs, self.markers, self.texts = [], [], [], {}, {}

    def P(self, n, q, v, mdl, st):
        self.preds.append((n, q, v, mdl, st))

    def job(self, jn, prog, st, role, cmd=C_BASE, knobs=KNOBS):
        self.needs.append(f"$S/{prog}.bin")
        self.rows.append(Row(jn, st, K.SAFE, knobs, "-", cmd.format(prog=prog), role))

    def new(self, cfgname, st, role, text_of, cmd=C_BASE, knobs=KNOBS, prefix="r6o"):
        """A pair of jobs (x, y) with new markers and the program text_of(ax, m) -> text."""
        for ax in "xy":
            self.m += 1
            prog = f"{prefix}-{cfgname}-{ax}"
            t = text_of(ax, self.m)
            build_bin(prog, t)
            self.texts[prog] = t
            self.markers[f"{cfgname}-{ax}"] = self.m
            self.job(f"{cfgname}-{ax}", prog, st, role + ("" if ax == "x" else " (the y job)"), cmd, knobs)
        self.P(f"{cfgname}-x", "marker", f"{self.markers[cfgname + '-x']:#x}", "frozen program marker (x job; the y job's is +1)", st)
        return f"{cfgname}-x"


def common_bins():
    K.BINS.mkdir(exist_ok=True)
    K.probe._assemble((REPO / "probes/usse/templates/pds_iter_xy.s").read_text(), K.BINS / "pds_iter_xy.bin", "pds")
    K.probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), K.BINS / "vtx_coords.bin")
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":
        build_bin(f"r4o-e709-{ax}", (PD / f"o4g-3-{ax}.s").read_text())
        (K.BINS / f"r4o-u-{ax}.bin").write_bytes((R4PIX / "bins" / f"r4o-u-{ax}.bin").read_bytes())
    return ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]


def copy_r5(prog):
    (K.BINS / f"{prog}.bin").write_bytes((R5PIX / "bins" / f"{prog}.bin").read_bytes())


def ctl_o4(b, st="control"):
    """R5's three bridge-shape controls: c-e709 (G-o4), c-u (G-o1), c-all4 (5:1), R5's programs byte for byte."""
    r5m = r5_markers()
    for ax in "xy":
        b.job(f"c-e709-{ax}", f"r4o-e709-{ax}", st, "G-o4 control: E709's o4g-3 unchanged (R4, R5)")
    for q, v, why in (("g_o4_words", "10..100", "tag-5 words in the x and y job (R1 to R5: 22 to 63)"),
                      ("g_o4_pairs", "5..60", "pairs (R4, R5: 8 to 42)"), ("g_o4_parity", "even,even", "every pair source (even x, even y)"),
                      ("g_o4_tag5p_max", "2", "no tag-13 word in the x job")):
        b.P("c-e709-x", q, v, "G-o4 structural, as R4 and R5 (" + why + ")", st)
    for ax in "xy":
        b.job(f"c-u-{ax}", f"r4o-u-{ax}", st, "G-o1 control: R4's own c-u program byte for byte")
    b.P("c-u-x", "marker", "0x105", "R4's program marker", st)
    b.P("c-u-x", "ctl_min_frac", "0.98", "frozen criterion (R1 to R5: tag-2 fraction 0.990 to 0.996)", st)
    for ax in "xy":
        copy_r5(f"r5o-c-all4-{ax}")
        b.job(f"c-all4-{ax}", f"r5o-c-all4-{ax}", st, "R5's c-all4 program byte for byte: every output with bit 4, read 5:1 (E858)")
    b.P("c-all4-x", "marker", f"{r5m['c-all4-x']:#x}", "R5's program marker (bins/p5o4-markers.tsv of R5)", st)
    b.P("c-all4-x", "o4_word", "5:1", "E858: c-all4 read 5:1 in R5; any other reading voids the stage (not the session)", st)


def build_rd():
    b = Builder("p6-rd", M0)
    b.needs += common_bins()
    ctl_o4(b)
    x = b.new("c-ow", "control", "c-ow: o0 = tag 1 bits 2, then o0 = tag 1 bits 1 (.end): the last o0 write is the pixel",
              lambda ax, m: special(ax, m, "c-ow"))
    b.P(x, "own_word", "1:1>=0.95", "the last o0 write is the pixel: bits 1 at >= 95 percent of the TRI pixels (else the stage is void)", "control")
    x = b.new("c-rd-0", "control", "c-rd-0: o0 = W_A (bits 2); mov r10, o0; o0 = W_B (bits 3); mov.end o0, r10: W_A read back (E373)",
              lambda ax, m: special(ax, m, "c-rd-0"))
    b.P(x, "own_word", "1:2>=0.95", "a register known to hold its word, read through r10 (E373): W_A at >= 95 percent of TRI; W_B or "
        "neither: readback cannot be read, the stage is void", "control")
    b.P(x, "tri", f">={RM.TRI_MIN}", "TRI = the pixels whose word is their own (job marker, tag 1, source the pixel) in both c-rd-0 jobs", "control")
    for k in RM.CPRD_K:
        x = b.new(f"c-prd-0-k{k}", "control", f"c-prd-0 k = {k}: o0 = W_0 (bits 2), p1 = (g25 == {k}), p1 o0 = W_1 (bits 1), o7 .end",
                  lambda ax, m, k=k: special(ax, m, f"c-prd-0-k{k}"))
        b.P(x, "lanes", ",".join(RM.cprd_lanes(k)), "[infer from E808's o1 result] W_1 on lane k = (x & 1) | (y & 1) << 1, W_0 on the "
            "others, each at >= 95 percent of the lane's TRI pixels; gates the predicate rows only", "control")
    for j in RM.RD_J:
        name = f"rd-{j}"
        x = b.new(name, "heldout", f"readback rd-{j}: the walk row w-{j} (o{j} bit 4, the rest bit 5), then mov r10, o{j}; mov.end o0, r10",
                  lambda ax, m, n=name: program(ax, m, RM.config(n)))
        b.P(x, "labels", " ".join(f"{c}={v}" for c, v in RM.labels(name).items()), "class labels (rdmodel.labels)", "heldout")
        for mdl in RM.MODELS:
            b.P(x, "class", RM.rd_class(mdl, j), mdl, "heldout")
    for name, txt, frozen, why in (
            ("n-rd-1", "read o1 with no write to o1", "!S", "a word with bit 4 cannot exist in the job: not S"),
            ("n-rd-4", "read o4 with no write to o4", "!S", "a word with bit 4 cannot exist in the job: not S"),
            ("x-rd-4", "rd-4 with o4's word tag 13", "S", "the read follows the written word, not the register's number: S shows tag 13"),
            ("x-rd-5", "rd-5 with o5's word tag 14", "S", "the read follows the written word, not the register's number: S shows tag 14")):
        x = b.new(name, "heldout", f"independent row: {txt}", lambda ax, m, n=name: program(ax, m, RM.config(n)))
        b.P(x, "labels", " ".join(f"{c}={v}" for c, v in RM.labels(name).items()), "class labels (rdmodel.labels)", "heldout")
        b.P(x, "class", frozen, why + (" (scored if rd-%s reads S)" % name[-1] if name.startswith("x-") else ""), "heldout")
    for j in RM.PRD_J:
        for k in RM.PRD_K:
            name = f"prd-{j}-k{k}"
            x = b.new(name, "heldout", f"predicate on o{j} by readback, k = {k}: o{j} = bits 0, p1 o{j} = bit 4, then read o{j}",
                      lambda ax, m, n=name: program(ax, m, RM.config(n)))
            for pm in RM.PMODELS:
                b.P(x, "lanes", ",".join(RM.prd_lanes(j, k, pm)), pm, "heldout")
    for ax in "xy":
        b.job(f"rd-4-{ax}-rep", f"r6o-rd-4-{ax}", "replicate", f"replicate of rd-4-{ax} (same program)")
    b.P("rd-4-x-rep", "marker", f"{b.markers['rd-4-x']:#x}", "frozen program marker (identical program)", "replicate")
    b.P("rd-4-x-rep", "class", "=rd-4", "the replicate reads rd-4's class", "replicate")
    P = lambda q, v, why, st="heldout": b.P("@p6-rd", q, v, why, st)
    P("premise", "o4..o7's own words reach no pixel of any kept image (0 of 12143 words of w-4..w-7, no tag-8 word in E570); E081's o4..o7 "
      "counts are leftovers", "E871 (resgx545 main d9b2969): the image cannot say where they land; readback asks whether the write is stored")
    P("models", " ".join(f"{m}={','.join(RM.rd_vector(m))}" for m in RM.MODELS), "plan 2.1: the rd vector over j = 1..7 per model "
      "(!S = any decided class but S; at j = 4 H-MOD4's A4 is o0's word, named A0)")
    P("class_rule", f"one class at >= {RM.CLASS_SHARE} of the TRI pixels of both jobs; X: < {RM.X_SHARE} carry the job's marker; "
      f"O: >= {RM.O_SHARE} one other marker; else cannot tell", "plan 2.1")
    P("lane_rule", f"a lane reads a label with >= {RM.LANE_SHARE} of its TRI pixels in both jobs", "plan 2.4")
    P("prd_gate", "prd-j scored only if rd-j reads S and both c-prd-0 rows pass; else cannot tell by design", "plan 2.4")
    P("verdict", "the predicate gates the o_j write iff gated at k = 0, 1, 2, 3 and 7", "plan 2.4")
    head = """Q276 (pixel), stage p6-rd: is an o4..o7 write stored (readable back in the instance), and does the predicate gate it.  R5's
command and word layout; each rd-j program is the walk row w-j with `mov.skipinv r10, oJ; mov.skipinv.end o0, r10` last, so the
own pixel shows what oJ held (E373).  TRI = own pixels of c-rd-0 in both jobs.  Models over rd-1..rd-7: H-STORE (S everywhere),
H-FOUR (S at 1..3, not S at 4..7), H-O0 (A0 everywhere), H-MOD4 (S at 1..3, o_(j-4)'s word at 4..7).  Controls first: c-e709
(G-o4), c-u (G-o1), c-all4 (5:1), c-ow, c-rd-0 (readback through r10), c-prd-0 k1/k7 (gates prd).  Bridge (the driver's gate):
c-e709, c-u, c-ow, c-rd-0.  No fault is expected; any fault, hang or STATUS2 other than 0x400 after a reset stops the stage."""
    return b, head


def build_l3():
    b = Builder("p6-l3", M0 + 0x50)
    b.needs += common_bins()
    r5m = r5_markers()
    for k in (0, 3):
        cfg = f"p3-pa-k{k}"
        for ax in "xy":
            copy_r5(f"r5o-{cfg}-{ax}")
            b.job(f"{cfg}-{ax}", f"r5o-{cfg}-{ax}", "control", f"R5's {cfg} program byte for byte: the determinism control")
        b.P(f"{cfg}-x", "marker", f"{r5m[cfg + '-x']:#x}", "R5's program marker", "control")
        want = {0: ("5:0", "5:1"), 3: ("5:1", "5:1")}[k]
        b.P(f"{cfg}-x", "job_x", want[0], "E858 (R5 p5-o4): the x job's tag-5 label", "control")
        b.P(f"{cfg}-x", "job_y", want[1], "E858 (R5 p5-o4): the y job's tag-5 label", "control")
    hy = {"H-Y1": ("5:0", "5:1"), "H-Y2": ("5:1", "5:0"), "H-YN": ("5:1", "5:1")}
    for i, k in enumerate((1, 2)):
        cfg = f"p3-pa-k{k}"
        x = b.new(cfg, "heldout", f"P3 k = {k}, p1 first (R5's p3-pa shape): p1 o3 = tag 4, !p1 o3 = tag 4 with bit 4",
                  lambda ax, m, k=k: R5O.program(ax, m, M.base(), ("p3", "pa", k)), prefix="r6o")
        b.P(x, "job_x", "5:1", "the x job's o3 word is lane 0's (R5)", "heldout")
        for h, v in hy.items():
            b.P(x, "job_y", v[i], h, "heldout")
    b.P("@p6-l3", "job_rule", "a job's label: >= 10 tag-5 words of one label, no other above 2 (R4's class rule per job)", "plan 2.5", "heldout")
    b.P("@p6-l3", "verdict", "H-Y1 / H-Y2 / H-YN by the y jobs of k = 1 and 2, only if both controls read as R5", "plan 2.5", "heldout")
    head = """Q276 (pixel), optional set L3: which instance's o3 enters the OR.  R5's p3-pa-k0 and p3-pa-k3 programs byte for byte (must
read x 5:0 / y 5:1 and 5:1 / 5:1, as R5: the determinism control) and new p3-pa-k1, p3-pa-k2 (HELD OUT): the x job 5:1; the y job
H-Y1 5:0 at k = 1 and 5:1 at k = 2, H-Y2 the reverse, H-YN 5:1 at both."""
    return b, head


def build_s():
    b = Builder("p6-s", M0 + 0x58)
    b.needs += common_bins()
    or_, own = "OR(o0,o3)", "MUX(o4;o4)"
    x = b.new("c-s-all4", "control", "the setup's control: every output with bit 4 (R5's c-all4 words) under E406's setup",
              lambda ax, m: R5O.program(ax, m, M.all4()), cmd=C_SETUP, knobs=KNOBS_S)
    b.P(x, "pattern", "tags 2..4 <= 2 a job, tag 5 >= 10 a job", "E406's setup pattern (tags 1 and 5 only, 27 of 27); else the set is void", "control")
    for j in range(8):
        x = b.new(f"s-{j}", "heldout", f"the walk w-{j} under E406's setup", lambda ax, m, j=j: R5O.program(ax, m, M.walk(j)),
                  cmd=C_SETUP, knobs=KNOBS_S)
        b.P(x, "o4_word", M.predict(or_, M.walk(j)), "H-OR", "heldout")
        b.P(x, "o4_word", M.predict(own, M.walk(j)), "H-OWN4", "heldout")
    x = b.new("s-n4", "heldout", "no o4 write under E406's setup", lambda ax, m: R5O.program(ax, m, M.indep("n-o4")), cmd=C_SETUP,
              knobs=KNOBS_S)
    b.P(x, "o4_word", M.predict(or_, M.indep("n-o4")), "H-OR", "heldout")
    b.P(x, "o4_word", "none", "H-OWN4", "heldout")
    for ax in "xy":
        b.job(f"r-u-{ax}", f"r4o-u-{ax}", "control", "the restore check: R4's c-u program, --kpoke rd:9=0 (dword 9's default), G-o1",
              cmd=C_RESTORE, knobs=KNOBS_S)
    b.P("r-u-x", "marker", "0x105", "R4's program marker", "control")
    b.P("r-u-x", "ctl_min_frac", "0.98", "G-o1 after the setup (the restore check)", "control")
    b.P("@p6-s", "verdict", "H-OR or H-OWN4 by s-0..s-7 and s-n4, only if c-s-all4 shows the pattern; r-u must pass G-o1",
        "plan 2.6", "heldout")
    head = """Q023 / Q276 (pixel), optional set S, last in the session: the walk in E406's full setup (--blk 1=0x05d00200, --kpoke rd:9=1,
word 4 as now).  c-s-all4 must show E406's pattern (tag-2 to tag-4 words <= 2 a job, >= 10 tag-5 words), else the set is void;
H-OR (the tag-5 word is o0 OR o3: 3 2 2 3 2 2 2 2, tag 5 at s-n4) vs H-OWN4 (o4's own word: 2 2 2 2 1 2 2 2, none at s-n4).
Then r-u (c-u with --kpoke rd:9=0, the default value) must pass G-o1: the restore check; the runner also checks that debugfs
kpoke reads empty after every kpoke row and clears it by trap."""
    return b, head
