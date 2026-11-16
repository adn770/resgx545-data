#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r34-ev2's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

The follow-up of r34-ev (E1137, E1138). Q111 (platform, high): r34-ev's post hoc readings frozen
as held-out hypotheses: CR_EVENT_STATUS bit 1 (DPM_OUT_OF_MEMORY_MT) in every overflowing job at
the PBs of 0xe2 and 0x82 pages and in none at 0x2b6 and 0x1c2 (rival: bit 1 by chance, at any
size), four new rows a size; a copy's bit 18 against its form, six rows of each. Q036 (vdm,
medium): r34-ev's d1, which its gate stopped (d0 sampled 0x0660 + 0x0748 at 4.1 us): 0x0748
alone with its own calibration (c0) and CR_DPM_3D_PAGE_COUNTS (0x0660) alone in stages of its
own (p0, p1).

Every job runs after the kit's reset under regtimeline (rt, read only through /dev/mem, TOTAL 0,
LEAD 5 ms), in one of r34-ev's three forms, all run without a fault on this module (E1137):

  ovf    t10 `probe --tri pixel --width 3072 --height 2048 --vertices 1500 p1139-green.bin` with
         debugfs render_pb_pages P (expect:rc3-overflow; 0x422 completes with rc 0)
  copy   t30 `copy` (64 x 32)
  lcopy  t30 `copy --width 256 --height 256 --src-stride 1024 --dst-stride 1024`

The bit 2 bound: E1057's bit 2 clears are 3890 to 4090 ns wide, so a sampler whose interval is at
most 3890 ns sees each one; r34-ev's d0 read 4095 and 4168 ns with two registers (E1138). c0's
median decides which of d1 (at most 3890 ns: every hypothesis of r34-ev's d1) and d1s (above it,
at most 12000 ns: only the readings a coarser sampler keeps: bit 2 summed over the stage, bit 4
once and its length, bit 3's 20 to 30 us clears) runs; exactly one opens."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
T30 = '"$HOME/sgxfive-test-t30"'
PROBE = 'probe --tri pixel --width 3072 --height 2048 --vertices 1500 "$S/bins/p1139-green.bin"'
FORM = {"ovf": f"{T10} {PROBE}",
        "copy": f"{T30} copy",
        "lcopy": f"{T30} copy --width 256 --height 256 --src-stride 1024 --dst-stride 1024"}
REGS = {"e0": "0x012c", "e1": "0x012c", "c0": "0x0748", "d1": "0x0748", "d1s": "0x0748",
        "p0": "0x0660", "p1": "0x0660"}
CAL = {"e1": "e0", "d1": "c0", "d1s": "c0", "p1": "p0"}
STAGES = ["e0", "e1", "c0", "d1", "d1s", "p0", "p1"]
PR = {"0x422": 0, "0x2b6": 1, "0x1c2": 2, "0xe2": 4, "0x82": 7}
SMALL = ("0xe2", "0x82")        # the PBs where r34-ev saw bit 1 (6 of 6 rows)
IMG = {"0x422": 1748705, "0x2b6": 1675156, "0x1c2": 1666112, "0xe2": 1667517, "0x82": 1669806}
S_IMG = ("r13-dpm pr2, r15-dpm pr4 and r34-ev (E1032, E1057, E1137) kept outputs: the same count in "
         "every row of a size")
SHORT = {"0x422": "c0", "0x2b6": "p1", "0x1c2": "p2", "0xe2": "p4", "0x82": "p7"}


def ovf(st, pb, i, s="held"):
    return (f"{st}-{SHORT[pb]}{i}", s, "ovf", pb)


# (name, set, form, pb) in run order
E1_PB = ["0x2b6", "0xe2", "0x1c2", "0x82", "0x82", "0x1c2", "0xe2", "0x2b6",
         "0xe2", "0x2b6", "0x82", "0x1c2", "0x1c2", "0x82", "0x2b6", "0xe2"]
E1_CP = ["copy", "lcopy", "lcopy", "copy", "copy", "lcopy", "lcopy", "copy", "copy", "lcopy",
         "lcopy", "copy"]


def e1_rows():
    out = [ovf("e1", "0x422", "a", "control")]
    seen = {}
    for j, pb in enumerate(E1_PB):
        seen[pb] = seen.get(pb, 0) + 1
        out.append(ovf("e1", pb, seen[pb]))
        if j % 4 == 3:                      # three copies after every four probes
            for f in E1_CP[(j // 4) * 3:(j // 4) * 3 + 3]:
                seen[f] = seen.get(f, 0) + 1
                k = "cp" if f == "copy" else "lc"
                s = "control" if seen[f] == 1 else "held"
                out.append((f"e1-{k}{seen[f]}", s, f, None))
    return out + [ovf("e1", "0x422", "b", "control")]


D_ROWS = [("0x422", "a", "control"), ("0x2b6", "1", "held"), ("0x1c2", "1", "held"),
          ("0xe2", "1", "held"), ("0x82", "1", "held"), ("0x82", "2", "held"),
          ("0xe2", "2", "held"), ("0x1c2", "2", "held"), ("0x2b6", "2", "held"),
          ("0x422", "b", "control")]
ROWS = {
    "e0": [("e0-o1", "control", "ovf", "0x422"), ("e0-c1", "control", "copy", None),
           ("e0-l1", "control", "lcopy", None), ("e0-l2", "control", "lcopy", None),
           ("e0-c2", "control", "copy", None), ("e0-o2", "control", "ovf", "0x422")],
    "e1": e1_rows(),
    "c0": [("c0-o1", "control", "ovf", "0x422"), ("c0-o2", "control", "ovf", "0x422"),
           ("c0-o3", "control", "ovf", "0x422")],
    "d1": [ovf("d1", pb, i, s) for pb, i, s in D_ROWS],
    "d1s": [ovf("d1s", pb, i, s) for pb, i, s in D_ROWS],
    "p0": [("p0-o1", "control", "ovf", "0x422"), ("p0-o2", "control", "ovf", "0x422")],
    "p1": [ovf("p1", pb, i, s) for pb, i, s in D_ROWS],
}
STAGE_CASE = {"e1": "e1-all", "d1": "d1-all", "d1s": "d1s-all"}


def reads(st, form):
    keys = ["ivl"] + ["r" + r[2:] for r in REGS[st].split(",")]
    keys += ["img"] if form == "ovf" else ["diff"]
    if st in ("c0", "d1", "d1s"):
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
    "e0": "e0 (6, calibration of 0x012c alone; Q111): two of each form (ovf at 0x422, copy, lcopy), every row a control (the first sample = snap0, the kept image or the copy's own check, the interval read); its windows gate e1.",
    "e1": "e1 (30, 0x012c alone; Q111): ovf at 0x422 first and last (controls), four new rows at each of 0x2b6, 0x1c2, 0xe2, 0x82 in a frozen shuffle; six plain and six large copies, three after every four probes. H-OOM-SMALL (bit 1 at 0xe2 and 0x82 in every row, at 0x2b6 and 0x1c2 in none) against H-OOM-CHANCE (bit 1 at any size: 2 or more rows at 0x2b6 and 0x1c2); H-C18-LARGE (bit 18 in 5 or 6 large copies, at most 3 plain) against H-C18-ANY (2 to 6 of each form, within 2 of each other); H-THR-NEVER, H-IMG.",
    "c0": "c0 (3, calibration of 0x0748 alone; Q036): ovf at 0x422, controls (0x0748's first sample 0x1f, no bit 2 clear, the kept image); its median opens d1 (at most 3890 ns) or d1s (above it, at most 12000 ns).",
    "d1": "d1 (10, 0x0748 alone, run when c0's median is at most 3890 ns; Q036): ovf at 0x422 first and last (controls: no bit 2 clear), 0x2b6, 0x1c2, 0xe2, 0x82 twice each, the second replicate reversed. r34-ev's d1 hypotheses: H-B2PR against H-B2-NONE, H-B4-ONE against H-B4-PR, H-B4-LEN, H-B1-PR, H-B3-LONG against H-B3-SHORT, H-B0-N.",
    "d1s": "d1s (10, the rows of d1, run when c0's median is above 3890 ns and at most 12000; Q036): only what a coarser sampler keeps: H-B2PR (summed) against H-B2-NONE, H-B4-ONE against H-B4-PR, H-B4-LEN, H-B3-LONG against H-B3-SHORT.",
    "p0": "p0 (2, calibration of CR_DPM_3D_PAGE_COUNTS 0x0660 alone; Q036): ovf at 0x422, controls (the first sample = snap0, the kept image); gates p1.",
    "p1": "p1 (10, 0x0660 alone; Q036): the rows of d1. H-PC-ONCE against H-PC-RENDER (a word a render), H-PC-FIN (the final word of each PB size).",
}


def table(st):
    lines = [f"#stage {st}", "#limit 0", "# " + HEAD[st]]
    lines += [f"{n}|{s}|safe|{k}|{t}|{a}" for n, s, k, t, a in rows(st)]
    return "\n".join(lines) + "\n"


S_SNAP = ("@snap0: the first sample of 0x012c and 0x0660 equals the row's snap0 in r13-dpm pr2 (6 of "
          "6) and r34-ev (34 of 34, E1137, E1138)")
S_748 = ("0x0748 is not in the kit's snapshot: 0x1f, the first sample of 20 of 20 kept overflow rows "
         "(E1032, E1057, E1138) and E358's idle value")
S_DIFF = "the copy's own per-dword check (`copy: ok`), E1137's 14 of 14 copies"
S_CAL = "the calibration stage's measured job-window interval for the same register set and form (T1)"
S_SMALL = ("E1137 post hoc (fold/posthoc.txt of render/closing-r34-ev): bit 1 in 6 of 6 overflowing "
           "rows at 0xe2 and 0x82, in 0 of 5 at 0x2b6 and 0x1c2")
S_CHANCE = ("the alternative: bit 1 is a pulse a ~4 us sampler catches by chance at any PB size (E547: "
            "3 of 5, 0 of 5 partial jobs; r13-dpm 1 of 6), so 2 or more of the 8 rows at 0x2b6 and "
            "0x1c2 show it")
S_THR = "no kept sample sets bit 3: E547, E771, r13-dpm pr2, E1137 (14 of 14)"
S_C18L = ("E1137 post hoc: bit 18 in 5 of 6 large copies and 5 of 8 plain ones; frozen as the large "
          "copy always ending with it and the plain one at most half the time")
S_C18A = "the alternative: bit 18 ends a copy of either form as often (2 to 6 of 6 each, within 2)"
S_C0 = "E1137: no bit 0 in 14 of 14 copies"
S_B2 = ("E1057 (0x0748 alone at 1.7 us): bit 2 clears 0 times at PR 0 (2 of 2), 17 times in the 8 "
        "rows with a partial render, each 3.9 to 4.1 us; E1138: 0 at PR 0 (2 of 2)")
S_B2N = "the alternative: no bit 2 clear in any overflowing row"
S_B4 = ("r15-dpm pr4 (10 of 10) and E1138 (2 of 2): bit 4 clears once a job, 20.3 ms at PR 0, 138 at "
        "PR 1, 170 at PR 4, 190 at PR 7")
S_B4P = "the alternative: bit 4 clears once per render (two or more in an overflowing job)"
S_B1 = "r15-dpm pr4: bit 1 clears 1-2 at PR 0, 4 at PR 1, 7-10 at PR 4, 14-21 at PR 7, each about 4 us"
S_B3 = ("r15-dpm pr4: bit 3's longest clear 26 to 30 us at PR 4 and 7 (6 of 6), 4.2 to 7.9 us at PR 0 "
        "and 1; E1138: 4.3 and 4.4 us at PR 0")
S_B3S = "the alternative: bit 3's clears stay under 10 us at PR 4 and 7"
S_B0 = "r15-dpm pr4: 44 to 68 bit 0 clears a job (1.7 us); E1138: 39 and 41 (4.1 us)"
S_PC1 = ("r13-dpm pr2 (8 of 8) and E1138 (2 of 2): CR_DPM_3D_PAGE_COUNTS changes at most once a "
         "job, to its own final word")
S_PCR = "the alternative: a word a render, two or more changes in an overflowing job"
S_PCF = ("r13-dpm pr2: 0x70305 at 0x422 (and E1138 2 of 2), 0x60294 at 0x2b6, 0x401a0 at 0x1c2, "
         "0x200c0 at 0xe2 (2 of 2 each)")
S_PC82 = "[infer] from the kept sizes: the low half 0x82 - 0x22 = 0x60, the high half 0 to 2"


def d1_preds(n, s, pb, coarse):
    out, h, p = [], "held", PR[pb]
    if p > 0 and not coarse:
        out.append((n, "b2wmax", "0..7000", "H-B2PR", h, S_B2))
    out.append((n, "b4n", "1", "H-B4-ONE", h, S_B4))
    if p > 0:
        out.append((n, "b4n", "2..1000", "H-B4-PR", h, S_B4P))
    b4 = {0: "15..26", 1: "110..175", 2: "120..200", 4: "135..215", 7: "150..240"}[p]
    out.append((n, "b4ms", b4, "H-B4-LEN", h, S_B4 + "; PR 2 between PR 1 and 4 [infer]"))
    if not coarse:
        b1 = {0: "0..4", 1: "2..8", 2: "3..12", 4: "5..14", 7: "10..28"}[p]
        out.append((n, "b1n", b1, "H-B1-PR", h, S_B1 + "; PR 2 between PR 1 and 4 [infer]"))
        out.append((n, "b1wmax", "0..7000", "H-B1-PR", h, S_B1))
        out.append((n, "b0n", "30..90", "H-B0-N", h, S_B0))
    if p >= 4:
        out.append((n, "b3max", "20000..60000", "H-B3-LONG", h, S_B3))
        out.append((n, "b3max", "0..10000", "H-B3-SHORT", h, S_B3S))
    if p == 0:
        out.append((n, "b3max", "0..10000", "H-B3-LONG", h, S_B3))
    return out


def preds(st):
    out = [("case", "quantity", "value", "model", "set", "source")]
    regs = REGS[st].split(",")
    for n, s, form, pb in ROWS[st]:
        if s == "control":
            for r in regs:
                v, src = ("0x1f", S_748) if r == "0x0748" else ("@snap0", S_SNAP)
                out.append((n, f"reg:{r}", v, "H-CTL", s, src))
            if form == "ovf":
                out.append((n, "img", str(IMG[pb]), "H-CTL", s, S_IMG))
            else:
                out.append((n, "diff", "0", "H-CTL", s, S_DIFF))
            if st in CAL:
                out.append((n, "ivl", f"@cal:{CAL[st]}", "H-CTL", s, S_CAL))
            if st in ("c0", "d1", "d1s"):
                out.append((n, "b2n", "0", "H-CTL", s, S_B2 + " (E1057's PR 0 control)"))
        if st in ("e0", "c0", "p0"):
            continue
        h = "held"
        if form == "ovf" and s != "control":
            out.append((n, "img", str(IMG[pb]), "H-IMG", h, S_IMG))
        if st == "e1":
            if form == "ovf" and PR[pb] > 0:
                want = "1..1000000" if pb in SMALL else "0"
                out.append((n, "mt", want, "H-OOM-SMALL", h, S_SMALL))
            if form == "ovf":
                out.append((n, "thr", "0", "H-THR-NEVER", h, S_THR))
            else:
                out.append((n, "e0", "0", "H-COPY-NO0", h, S_C0))
        if st in ("d1", "d1s"):
            out += d1_preds(n, s, pb, st == "d1s")
        if st == "p1":
            out.append((n, "pcn", "0..1", "H-PC-ONCE", h, S_PC1))
            if PR[pb] > 0:
                out.append((n, "pcn", "2..1000", "H-PC-RENDER", h, S_PCR))
            if pb == "0x82":
                out.append((n, "pclo", "0x60", "H-PC-FIN", h, S_PC82))
                out.append((n, "pchi", "0..2", "H-PC-FIN", h, S_PC82))
            else:
                fin = {"0x422": "0x70305", "0x2b6": "0x60294", "0x1c2": "0x401a0",
                       "0xe2": "0x200c0"}[pb]
                out.append((n, "pcfin", fin, "H-PC-FIN", h, S_PCF))
    if st == "e1":
        out.append(("e1-all", "mtbig", "2..8", "H-OOM-CHANCE", "held", S_CHANCE))
        out.append(("e1-all", "mtbig", "0", "H-OOM-SMALL", "held", S_SMALL))
        out.append(("e1-all", "c18large", "5..6", "H-C18-LARGE", "held", S_C18L))
        out.append(("e1-all", "c18plain", "0..3", "H-C18-LARGE", "held", S_C18L))
        out.append(("e1-all", "c18both", "2..6", "H-C18-ANY", "held", S_C18A))
        out.append(("e1-all", "c18gap", "0..2", "H-C18-ANY", "held", S_C18A))
    if st in ("d1", "d1s"):
        out.append((f"{st}-all", "b2tot", "1..60", "H-B2PR", "held", S_B2 + " (summed over PR 1-7)"))
        out.append((f"{st}-all", "b2tot", "0", "H-B2-NONE", "held", S_B2N))
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
