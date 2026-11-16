#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r34-ev's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

Q111 (platform, high: which event sets which bit of CR_EVENT_STATUS and CR_EVENT_STATUS2) and Q036
(vdm, medium: 0x0748 bit by bit, CR_DPM_3D_PAGE_COUNTS' high half), round 34 plan sections 3.3 and
3.4. Every job runs after the kit's reset under regtimeline (rt, read only through /dev/mem, TOTAL
0: sampling lasts as long as the command, LEAD 5 ms). Three job forms, each one a past session ran
without a fault:

  ovf    t10 `probe --tri pixel --width 3072 --height 2048 --vertices 1500 p1139-green.bin` with
         debugfs render_pb_pages P (expect:rc3-overflow; 0x422 completes with rc 0, the others
         overflow with rc 3): r13-dpm pr2 (E1032) and r15-dpm pr4 (E1057), 18 of 18 rows, no fault
  copy   t30 `copy` (64 x 32, the kit's plain copy; E547's copies, r34-q010's t30 copies)
  lcopy  t30 `copy --width 256 --height 256 --src-stride 1024 --dst-stride 1024`: the large copy,
         a size no record ran (the library checks it: SGXFIVE_TEX_MAX 4096, stride 0x8000)

Stages: e0 (calibration of 0x012c alone, the three forms), e1 (0x012c alone: the overflow at five
PB sizes, copies, large copies), e2c (calibration of 0x012c + 0x0118), e2 (0x012c + 0x0118), d0
(calibration of 0x0660 + 0x0748), d1 (0x0660 + 0x0748: the overflow at five PB sizes). Every
control premise is read, not remembered (HACKING "Session kit", T1): register values `@snap0`
(0x0748, which the kit does not snapshot, keeps its constant 0x1f from E1032 and E1057's kept
rows), intervals `@cal:STAGE`. Every non-calibration row's hypotheses are frozen from kept rows of
other sessions and modules: every row is held out."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
T30 = '"$HOME/sgxfive-test-t30"'
PROBE = 'probe --tri pixel --width 3072 --height 2048 --vertices 1500 "$S/bins/p1139-green.bin"'
FORM = {"ovf": f"{T10} {PROBE}",
        "copy": f"{T30} copy",
        "lcopy": f"{T30} copy --width 256 --height 256 --src-stride 1024 --dst-stride 1024"}
REGS = {"e0": "0x012c", "e1": "0x012c", "e2c": "0x012c,0x0118", "e2": "0x012c,0x0118",
        "d0": "0x0660,0x0748", "d1": "0x0660,0x0748"}
CAL = {"e1": "e0", "e2": "e2c", "d1": "d0"}
STAGES = ["e0", "e1", "e2c", "e2", "d0", "d1"]
# PB pages -> the partial-render label (E1032, E1057: the knob, not a reading)
PR = {"0x422": 0, "0x2b6": 1, "0x1c2": 2, "0xe2": 4, "0x82": 7}
# the kept image of each PB size: the green count of `o0 mixed 0xff203040 xA 0xff00ff00 xG`
# (r13-dpm pr2 and r15-dpm pr4, 18 of 18 rows, 2 or 3 a size; 0x82 r15 only)
IMG = {"0x422": 1748705, "0x2b6": 1675156, "0x1c2": 1666112, "0xe2": 1667517, "0x82": 1669806}
S_IMG = "r13-dpm pr2 and r15-dpm pr4 kept outputs (E1032, E1057): the same count in every row of a size"

# (name, set, form, pb) in run order
ROWS = {
    "e0": [("e0-o1", "control", "ovf", "0x422"), ("e0-c1", "control", "copy", None),
           ("e0-l1", "control", "lcopy", None), ("e0-l2", "control", "lcopy", None),
           ("e0-c2", "control", "copy", None), ("e0-o2", "control", "ovf", "0x422")],
    "e1": [("e1-c0a", "control", "ovf", "0x422"), ("e1-p1a", "held", "ovf", "0x2b6"),
           ("e1-p2a", "held", "ovf", "0x1c2"), ("e1-p4a", "held", "ovf", "0xe2"),
           ("e1-p7a", "held", "ovf", "0x82"), ("e1-cpc", "control", "copy", None),
           ("e1-cp1", "held", "copy", None), ("e1-lcc", "control", "lcopy", None),
           ("e1-lc1", "held", "lcopy", None), ("e1-lc2", "held", "lcopy", None),
           ("e1-cp2", "held", "copy", None), ("e1-p7b", "held", "ovf", "0x82"),
           ("e1-p4b", "held", "ovf", "0xe2"), ("e1-p2b", "held", "ovf", "0x1c2"),
           ("e1-p1b", "held", "ovf", "0x2b6"), ("e1-c0b", "control", "ovf", "0x422")],
    "e2c": [("e2c-o1", "control", "ovf", "0x422"), ("e2c-c1", "control", "copy", None),
            ("e2c-c2", "control", "copy", None), ("e2c-o2", "control", "ovf", "0x422")],
    "e2": [("e2-c0", "control", "ovf", "0x422"), ("e2-p1", "held", "ovf", "0x2b6"),
           ("e2-p4", "held", "ovf", "0xe2"), ("e2-cpc", "control", "copy", None),
           ("e2-cp1", "held", "copy", None), ("e2-p7", "held", "ovf", "0x82")],
    "d0": [("d0-o1", "control", "ovf", "0x422"), ("d0-o2", "control", "ovf", "0x422")],
    "d1": [("d1-c0a", "control", "ovf", "0x422"), ("d1-p1", "held", "ovf", "0x2b6"),
           ("d1-p2", "held", "ovf", "0x1c2"), ("d1-p4a", "held", "ovf", "0xe2"),
           ("d1-p7a", "held", "ovf", "0x82"), ("d1-p7b", "held", "ovf", "0x82"),
           ("d1-p4b", "held", "ovf", "0xe2"), ("d1-c0b", "control", "ovf", "0x422")],
}
STAGE_CASE = {"d1": "d1-all"}


def reads(st, form):
    """A control's reading keys (run/hooks.sh's hook_reading prints them)."""
    keys = ["ivl"]
    keys += ["r" + r[2:] for r in REGS[st].split(",")]
    keys += ["img"] if form == "ovf" else ["diff"]
    if st == "d1":
        keys.append("b2n")
    return keys


def rows(st):
    out = []
    for n, s, form, pb in ROWS[st]:
        k = []
        if pb:
            k += [f"dbg:render_pb_pages={pb}", "expect:rc3-overflow"]
        if s == "control":
            k.append("reads:" + ",".join(reads(st, form)))
        out.append((n, s, " ".join(k) or "-", "rt", f"0 0.005 {REGS[st]} -- {FORM[form]}"))
    return out


HEAD = {
    "e0": "e0 (6, calibration of 0x012c alone; Q111): two of each form (ovf at 0x422, copy, lcopy), every row a control: the job's output (the kept image, or the copy's own check), 0x012c's first sample = the row's snap0, and the job window's interval (ivl), whose median and +-25 % window per form gate e1 (score.py gate). Stop: a row without its whole timeline, the overflow's or the copy's line (hook_check).",
    "e1": "e1 (16, 0x012c alone at the interval e0 measured; Q111): the overflow probe at 0x422 (2 controls, no partial render) and at 0x2b6, 0x1c2, 0xe2, 0x82 (1, 2, 4, 7 partial renders, two each, the second replicate in reversed order); copy and lcopy (a control and two held each). H-OOM-SET against H-OOM-NONE (bit 1 or 2 in an overflowing job), H-OOM-MT against H-OOM-GBL (bit 2), H-THR-NEVER (bit 3), H-SHORT (bits 0 and 13 at most 8 us), H-PR0-QUIET; H-COPY against H-COPY-END (bit 18 in a copy). Stop as e0.",
    "e2c": "e2c (4, calibration of 0x012c + 0x0118; Q111): two ovf at 0x422 and two copies, every row a control as e0's (both registers' first samples = snap0). Gates e2.",
    "e2": "e2 (6, 0x012c + 0x0118; Q111): ovf at 0x422 (control), 0x2b6, 0xe2, 0x82; copy (a control and one held). H-OOM-SET against H-OOM-NONE again; H-S2-SET against H-S2-NONE (CR_EVENT_STATUS2 bit 12 or 0 in an overflowing job); H-S2-COPYIDLE (STATUS2 keeps its idle word in a copy). Stop as e0.",
    "d0": "d0 (2, calibration of 0x0660 + 0x0748; Q036): two ovf at 0x422, controls as e0's (0x0660's first sample = snap0, 0x0748's = 0x1f). Gates d1 (also on a median of at most 3500 ns: E1057's bit 2 pulse is about 4 us).",
    "d1": "d1 (8, 0x0660 + 0x0748; Q036): ovf at 0x422 (2 controls, which must read no bit 2 clear: E1057's control) and at 0x2b6, 0x1c2, 0xe2 (two), 0x82 (two). 0x0748 bit by bit: H-B2PR against H-B2-NONE, H-B4-ONE against H-B4-PR, H-B4-LEN, H-B1-PR, H-B3-LONG against H-B3-SHORT, H-B0-N; CR_DPM_3D_PAGE_COUNTS: H-PC-ONCE against H-PC-RENDER (a word per render), H-PC-FIN (the final word of each PB size). Stop as e0.",
}


def table(st):
    lines = [f"#stage {st}", "#limit 0", "# " + HEAD[st]]
    lines += [f"{n}|{s}|safe|{k}|{t}|{a}" for n, s, k, t, a in rows(st)]
    return "\n".join(lines) + "\n"


# ---- sources (records and kept rows) ---------------------------------------------------------
S_SNAP = ("@snap0: r13-dpm pr2 kept rows (E1032), 6 of 6: the first sample of 0x012c, 0x0118 and "
          "0x0660 equals the row's snap0 (0x0660 holds the row before's final word: not reset)")
S_748 = ("0x0748 is not in the kit's snapshot (sessioncheck.SNAP_REGS): 0x1f, the first sample of "
         "18 of 18 kept overflow rows (E1032 pr2, E1057 pr4) and E358's idle value")
S_DIFF = "the copy's own per-dword check (`copy: ok`), E547's copies and r34-q010's"
S_CAL = "the calibration stage's measured job-window interval for the exact register set (T1)"
S_OOM = ("E547 kept partial jobs (tl-partial, 1024x768 -n 2 --keep-overflow): bit 1 in 3 of 5 at "
         "3.7 us a sample, 0 of 5 at 5.5 us; r13-dpm pr2 (7.5 us): bit 1 in 1 of 6 overflowing rows")
S_NONE = "the alternative: the firmware acknowledges both OOM bits within one sample"
S_MT = ("every kept OOM sample is bit 1 (DPM_OUT_OF_MEMORY_MT), never bit 2 (E547 partial, "
        "r13-dpm pr2): the global list is not what runs out [infer]")
S_GBL = "the alternative: bit 2 (DPM_OUT_OF_MEMORY_GBL) shows in an overflowing job"
S_THR = ("no kept sample sets bit 3 (DPM_REACHED_MEM_THRESH): E547, E771, r13-dpm pr2 (8 of 8)")
S_SHORT = ("E547: bits 0, 13 and 18 pulse 4.2 to 6.1 us in partial jobs (kept tl-partial: bit 0 "
           "4.2 to 6.0, bit 13 4.2 to 5.8)")
S_PR0 = "r13-dpm pr2 c0 rows (no overflow): no bit 1 or 2 (2 of 2)"
S_COPY = ("E547's kept copies (10 of 10 at 1.7 and 3.7 us): bits 14 with 31, once 26, never 18 or "
          "0; a fill shows 18 (7 of 10); E1123: the copy's kick sets bit 26 too")
S_CEND = "the alternative: a copy ends with PIXELBE_END_RENDER (bit 18) as a fill does"
S_S2 = ("E547 kept partial jobs: STATUS2 bit 12 (OTPM_MEM_CLEARED) in 3 of 10; E547's DPM_TA_FREE_LOAD "
        "(bit 0) in some partial jobs")
S_S2N = "the alternative: STATUS2 keeps its idle word through an overflowing job"
S_S2C = "E547's kept copies: STATUS2 0x400 (DCU_INVAL_COMPLETE) in every sample (10 of 10)"
S_B2 = ("E1057 (r15-dpm pr4, 0x0748 alone at 1.7 us): bit 2 clears 0 times at PR 0 (2 of 2), "
        "17 times in the 8 rows with a partial render, each 3.9 to 4.1 us wide")
S_B2N = "the alternative: no bit 2 clear in any overflowing row (as E1032's 7.5 us sampler saw)"
S_B4 = ("r15-dpm pr4 kept rows (gen/fit.py, gen/fit.txt): bit 4 clears once a job (10 of 10), "
        "20 ms at PR 0, 138 ms at PR 1, 170 ms at PR 4, 190 ms at PR 7; E358: bit 4 while the TA "
        "takes pages")
S_B4P = "the alternative: bit 4 clears once per render (two or more clears in an overflowing job)"
S_B1 = ("r15-dpm pr4 kept rows: bit 1 clears 1-2 at PR 0, 4 at PR 1, 7-10 at PR 4, 14-21 at PR 7, "
        "each 3.9 to 4.9 us; E358: before each page the 3D frees")
S_B3 = ("r15-dpm pr4 kept rows: bit 3's longest clear is 26 to 30 us at PR 4 and 7 (6 of 6), 4.2 "
        "to 7.9 us at PR 0 and 1 (4 of 4)")
S_B3S = "the alternative: bit 3's clears stay short (under 10 us) at PR 4 and 7"
S_B0 = "r15-dpm pr4 kept rows: bit 0 clears 44 to 68 times a job (10 of 10)"
S_PC1 = ("r13-dpm pr2 kept rows (E1032, 7.5 us): CR_DPM_3D_PAGE_COUNTS changes once a job, from "
         "the row before's word to its own (8 of 8); edm_dataflow: one EDM write site")
S_PCR = "the alternative (plan's H-HI3D): a word a render, two or more changes in an overflowing job"
S_PCF = ("r13-dpm pr2 kept rows: 0x70305 at 0x422, 0x60294 at 0x2b6, 0x401a0 at 0x1c2, 0x200c0 at "
         "0xe2 (2 of 2 each): the low half P - 0x22 when the job overflows")
S_PC82 = ("[infer] from the four kept sizes: the low half 0x82 - 0x22 = 0x60, the high half 0 to 2 "
          "(the kept high halves 7, 6, 4, 2 fall with the size; E358 reads 0 and 1 at 2 to 5 pages)")


def preds(st):
    out = [("case", "quantity", "value", "model", "set", "source")]
    regs = REGS[st].split(",")
    for n, s, form, pb in ROWS[st]:
        if s == "control":
            for r in regs:
                if r == "0x0748":
                    out.append((n, "reg:0x0748", "0x1f", "H-CTL", s, S_748))
                else:
                    out.append((n, f"reg:{r}", "@snap0", "H-CTL", s, S_SNAP))
            if form == "ovf":
                out.append((n, "img", str(IMG[pb]), "H-CTL", s, S_IMG))
            else:
                out.append((n, "diff", "0", "H-CTL", s, S_DIFF))
            if st in CAL:
                out.append((n, "ivl", f"@cal:{CAL[st]}", "H-CTL", s, S_CAL))
            if st == "d1":
                out.append((n, "b2n", "0", "H-CTL", s, S_B2 + " (E1057's PR 0 control)"))
        if st in ("e0", "e2c", "d0"):
            continue
        h = "held"
        if form == "ovf" and s != "control":
            out.append((n, "img", str(IMG[pb]), "H-IMG", h, S_IMG))
        if st in ("e1", "e2"):
            if form == "ovf" and PR[pb] > 0:
                out.append((n, "oom", "1..1000000", "H-OOM-SET", h, S_OOM))
                out.append((n, "oom", "0", "H-OOM-NONE", h, S_NONE))
                out.append((n, "gbl", "0", "H-OOM-MT", h, S_MT))
                out.append((n, "gbl", "1..1000000", "H-OOM-GBL", h, S_GBL))
                if st == "e1":
                    out.append((n, "w0max", "0..8000", "H-SHORT", h, S_SHORT))
                    out.append((n, "w13max", "0..8000", "H-SHORT", h, S_SHORT))
                if st == "e2":
                    out.append((n, "s2", "1..1000000", "H-S2-SET", h, S_S2))
                    out.append((n, "s2", "0", "H-S2-NONE", h, S_S2N))
            if form == "ovf":
                out.append((n, "thr", "0", "H-THR-NEVER", h, S_THR))
                if PR[pb] == 0:
                    out.append((n, "oom", "0", "H-PR0-QUIET", h, S_PR0))
            if form in ("copy", "lcopy"):
                out.append((n, "e18", "0", "H-COPY", h, S_COPY))
                out.append((n, "e0", "0", "H-COPY", h, S_COPY))
                out.append((n, "e18", "1..1000000", "H-COPY-END", h, S_CEND))
                if st == "e2":
                    out.append((n, "s2words", "1", "H-S2-COPYIDLE", h, S_S2C))
        if st == "d1":
            p = PR[pb]
            if p > 0:
                out.append((n, "b2wmax", "0..7000", "H-B2PR", h, S_B2))
            out.append((n, "b4n", "1", "H-B4-ONE", h, S_B4))
            if p > 0:
                out.append((n, "b4n", "2..1000", "H-B4-PR", h, S_B4P))
            b4 = {0: "15..26", 1: "110..175", 2: "120..200", 4: "135..215", 7: "150..240"}[p]
            out.append((n, "b4ms", b4, "H-B4-LEN", h, S_B4 + "; PR 2 between PR 1 and 4 [infer]"))
            b1 = {0: "0..4", 1: "2..8", 2: "3..12", 4: "5..14", 7: "10..28"}[p]
            out.append((n, "b1n", b1, "H-B1-PR", h, S_B1 + "; PR 2 between PR 1 and 4 [infer]"))
            out.append((n, "b1wmax", "0..7000", "H-B1-PR", h, S_B1))
            if p >= 4:
                out.append((n, "b3max", "20000..60000", "H-B3-LONG", h, S_B3))
                out.append((n, "b3max", "0..10000", "H-B3-SHORT", h, S_B3S))
            if p == 0:
                out.append((n, "b3max", "0..10000", "H-B3-LONG", h, S_B3))
            out.append((n, "b0n", "30..90", "H-B0-N", h, S_B0))
            out.append((n, "pcn", "0..1", "H-PC-ONCE", h, S_PC1))
            if p > 0:
                out.append((n, "pcn", "2..1000", "H-PC-RENDER", h, S_PCR))
            if pb == "0x82":
                out.append((n, "pclo", "0x60", "H-PC-FIN", h, S_PC82))
                out.append((n, "pchi", "0..2", "H-PC-FIN", h, S_PC82))
            else:
                fin = {"0x422": "0x70305", "0x2b6": "0x60294", "0x1c2": "0x401a0",
                       "0xe2": "0x200c0"}[pb]
                out.append((n, "pcfin", fin, "H-PC-FIN", h, S_PCF))
    if st == "d1":
        out.append(("d1-all", "b2tot", "1..60", "H-B2PR", "held", S_B2 + " (summed over PR 1-7)"))
        out.append(("d1-all", "b2tot", "0", "H-B2-NONE", "held", S_B2N))
    return "".join("\t".join(r) + "\n" for r in out)


def files():
    out = {}
    for st in STAGES:
        out[f"tables/{st}.txt"] = table(st)
        out[f"predictions/{st}.tsv"] = preds(st)
    return out


def main(argv):
    bad = 0
    for rel, text in files().items():
        p = os.path.join(HERE, rel)
        if "--check" in argv:
            if not os.path.exists(p) or open(p).read() != text:
                print(f"{rel}: not what gen/make.py writes")
                bad = 1
        else:
            open(p, "w").write(text)
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
