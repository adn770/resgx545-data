#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r31-cc's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

Every row is one plain 64 x 64 triangle (`tri --width 64 --height 64`; c5: the default `fill`,
64 x 32) of t10 under regtimeline (rt), which samples the registers read-only through /dev/mem
from LEAD seconds before the job to TOTAL seconds (or the job's end). No knob, no write, no
fault, no hang. Every model is frozen from E1120's kept rows (post hoc there) or the kit's kept
snapshots, so every non-control row is held out."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
TRI = "tri --width 64 --height 64"
FILL = "fill"
# the register sets: CR_CACHE_CTRL alone (the densest); with CR_USE0_SERV_EVENT (the served
# events' count); with CR_BIF_CTRL (the firmware's BIF invalidations before its write, E013's
# dataflow); and together with CR_EVENT_STATUS and CR_DMS_CTRL (the TA path's write, E1120 e3)
R1 = "0x0804"
RS = "0x0804,0x0b14"
RB = "0x0804,0x0c00"
R5 = "0x012c,0x0804,0x0a74,0x0b14,0x0c00"
R4 = "0x012c,0x0804,0x0b14,0x0c00"
# (stage, regs, tool args, held-out rows, ivl window ns)
STAGES = [
    ("c1", R1, TRI, 8, (300, 2500)),
    ("c2", RS, TRI, 10, (400, 3000)),
    ("c3", RB, TRI, 10, (400, 3000)),
    ("c4", R5, TRI, 8, (800, 5000)),
    ("c5", R4, FILL, 6, (600, 4000)),
]
HEAD = {
    "c1": "c1 (10, CR_CACHE_CTRL alone at the densest sampling): two controls (first and last), 8 plain triangles held out. Frozen from E1120 (19 of 19 rows): H-CC-ONE (one change, 0x0000ffff to 0x1000ffff, held to the end); H-CC-LAT (the change 10 to 40 ms after the tool starts; E1120 18.6 to 25.1). Stop: a row that does not draw exactly, a missing or cut timeline, regtimeline's rc not 0: the session ends.",
    "c2": "c2 (12, the change against the served events' count): CR_USE0_SERV_EVENT beside CR_CACHE_CTRL. Frozen from E1120's e2 and e4 rows (post hoc there): H-CNT-LAG (no count in the 30 us before the change, 0 in 21 decided rows; the next count 0 to 12 us after it, 5.0 to 7.3 us in 11 of 12 and in the change's sample in one) against H-CNT-LEAD (a count in the 30 us before the change); a row with a tick the lead's cadence may put in a window cannot tell. Stop as c1, and a tick stop (bit 16 clear in the last sample, or under half a count a ms).",
    "c3": "c3 (12, the change against CR_BIF_CTRL): the firmware's kick pass tests the command's cache control bits 0 and 1 (a BIF routine each) before bit 3's CR_CACHE_CTRL |= 0x10000000 (E013's dataflow, doc/specs/edm_dataflow.md COMMAND+0x004; the kernel's TA kick carries 0xb). Frozen: H-BIF-FIRST (a CR_BIF_CTRL word other than its first shows in the 30 us before the change: the firmware's response precedes it, H-CC-FW) against H-BIF-LATER (only in the 15 us after it, H-CC-HW); a row with no such word, or one only in the change's own sample, cannot tell. Stage: H-BIF-HIDDEN (no row decides; E258 never saw 0x0c00 move at about 15 us a sample) against H-BIF-VISIBLE (1 or more). Stop as c1.",
    "c4": "c4 (10, the kick's order): CR_EVENT_STATUS, CR_CACHE_CTRL, CR_DMS_CTRL, CR_USE0_SERV_EVENT and CR_BIF_CTRL. Frozen: c2's and c3's models; H-CC-ONE; H-CCFIRST (the change before every CR_EVENT_STATUS event, E1120 24 of 24); H-CC-26 (bit 26 15 to 120 us after the change where it precedes the render end, E1120 19.6 to 106.6); H-DMS (CR_DMS_CTRL written 20 to 70 us after the change, E1120 e3 31.1 to 48.6); H-WAIT (after bit 26's first rise) against H-NOWAIT (before it) [infer: the firmware waits for the invalidation before the TA path]; H-IDLE. Stop as c2.",
    "c5": "c5 (8, a transfer kick): t10's default fill (64 x 32), whose kick the kernel sends with INVAL_DATA (bit 3) and no TA. Frozen from the kit's kept snapshots (post hoc: 0x0804 0x0000ffff before and 0x1000ffff after a plain fill, r8-k2 and r9-faults xf-c-fill, r30-pde s0-pfill, r14-bif refill, r13-flag f3-fill-a): H-CC-XFER (one change, as a triangle's) against H-CC-TA (no change: only a TA kick sets the bit); c2's and c3's models and H-CCFIRST held out on a fill. Stop as c2 (the fill must say `fill: ok` and draw exactly).",
}


def rows(st):
    name, regs, args, nheld, _ = st
    keys = ["diff", "ivl", "cache"]
    for reg, k in (("0x012c", "idle"), ("0x0b14", "se16"), ("0x0c00", "bif0"),
                   ("0x0a74", "dms0")):
        if reg in regs.split(","):
            keys.append(k)
    rt = f"1.5 0.5 {regs} -- {T10} {args}"
    out = [(f"{name}-c1", "control", "reads:" + ",".join(keys), rt)]
    out += [(f"{name}-{i + 1:02d}", "held", "-", rt) for i in range(nheld)]
    out.append((f"{name}-c2", "control", "reads:" + ",".join(keys), rt))
    return out


def table(st):
    lines = [f"#stage {st[0]}", "#limit 0", "# " + HEAD[st[0]]]
    lines += [f"{n}|{s}|safe|{k}|rt|{a}" for n, s, k, a in rows(st)]
    return "\n".join(lines) + "\n"


SNAP = "the kit's snap0.regs after the reset (r30-evst2 e2-c1: 0x0804 0x0000ffff, 0x0c00 0, 0x0a74 0x00208200, 0x0b14 bit 16 set)"
CTL = {"diff": ("0", "H-DRAW", "E1120, E1121 (41 of 41 jobs drew exactly)"),
       "cache": ("0x0000ffff", "H-IDLE", SNAP + "; E1120 24 of 24 first samples"),
       "idle": ("0x20000000", "H-IDLE", "E1120, E1121, E547"),
       "se16": ("1", "H-IDLE", "E009, E1120 (bit 16 set in the first sample)"),
       "bif0": ("0x00000000", "H-IDLE", SNAP + "; E258"),
       "dms0": ("0x00208200", "H-IDLE", SNAP)}
IVL_SRC = "E1121 (539 to 547 ns with 1 register), E1120 (1406 to 1492 with 4, 9001 to 9063 with 27)"
ONE = [("ccn", "1", "H-CC-ONE", "E1120 (19 of 19 rows, 24 with the controls)"),
       ("ccword", "0x1000ffff", "H-CC-ONE", "E1120 (24 of 24)"),
       ("ccback", "0", "H-CC-ONE", "E1120 (24 of 24)")]
XFER = [("ccn", "1", "H-CC-XFER", "post hoc, the kit's kept snapshots of plain fills after the reset (0x0000ffff, then 0x1000ffff: r8-k2, r9-faults xf-c-fill, r30-pde s0-pfill, r14-bif refill, r13-flag f3-fill-a)"),
        ("ccword", "0x1000ffff", "H-CC-XFER", "as above"),
        ("ccback", "0", "H-CC-XFER", "as above"),
        ("ccn", "0", "H-CC-TA", "- [infer: a hardware set at the TA kick only]")]
LAT = [("ccstart", "10..40", "H-CC-LAT", "E1120 (18.6 to 25.1 ms, 24 of 24) post hoc")]
CNT = [("cntpre", "0", "H-CNT-LAG", "E1120 e2, e3, e4 (0 in 21 of 21 decided rows) post hoc"),
       ("cntlag", "0..12", "H-CNT-LAG", "E1120 e2, e4 (5.0 to 7.3 us in 11 of 12 decided, the change's sample in one) post hoc"),
       ("cntpre", "1", "H-CNT-LEAD", "- [infer: the kick's event counted before the firmware writes]")]
BIF = [("biford", "pre", "H-BIF-FIRST", "E013 (doc/specs/edm_dataflow.md COMMAND+0x004: bits 0, 1 call the BIF routine before bit 3's write) [infer]"),
       ("biford", "post", "H-BIF-LATER", "- [infer: a hardware set at the kick, before the firmware runs]")]
ORDER = [("ccfirst", "1", "H-CCFIRST", "E1120 (24 of 24)"),
         ("outside", "0", "H-IDLE", "E1120, E1121")]
TA = [("cc26", "15..120", "H-CC-26", "E1120 (19.6 to 106.6 us where bit 26 precedes the render end) post hoc"),
      ("dmslag", "20..70", "H-DMS", "E1120 e3 (31.1 to 48.6 us at 9 us a sample, 10 of 10) post hoc"),
      ("dms26", "1", "H-WAIT", "E1120 e3-05 (1 of 1 decided) [infer]"),
      ("dms26", "0", "H-NOWAIT", "-")]
ROWS = {"c1": ONE + LAT, "c2": ONE + LAT + CNT, "c3": ONE + LAT + BIF,
        "c4": ONE + LAT + CNT + BIF + ORDER + TA, "c5": XFER + CNT + BIF + ORDER}
STAGEQ = {"c3": [("bifdecided", "1..10", "H-BIF-VISIBLE", "-"),
                 ("bifdecided", "0..0", "H-BIF-HIDDEN", "E258 (0x0c00 0 in every sample of 21 jobs at about 15 us a sample) [infer]")],
          "c4": [("bifdecided", "1..8", "H-BIF-VISIBLE", "-"),
                 ("bifdecided", "0..0", "H-BIF-HIDDEN", "E258 [infer]")],
          "c5": [("bifdecided", "1..6", "H-BIF-VISIBLE", "-"),
                 ("bifdecided", "0..0", "H-BIF-HIDDEN", "E258 [infer]")]}


def predictions(st):
    name = st[0]
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for n, s, k, _ in rows(st):
        if s == "control":
            for q in k[len("reads:"):].split(","):
                if q == "ivl":
                    out.append(f"{n}\tivl\t{st[4][0]}..{st[4][1]}\tH-RATE\tcontrol\t{IVL_SRC}")
                else:
                    v, m, src = CTL[q]
                    out.append(f"{n}\t{q}\t{v}\t{m}\tcontrol\t{src}")
        else:
            out += [f"{n}\t{q}\t{v}\t{m}\t{s}\t{src}" for q, v, m, src in ROWS[name]]
    out += [f"{name}\t{q}\t{v}\t{m}\tstage\t{src}" for q, v, m, src in STAGEQ.get(name, [])]
    return "\n".join(out) + "\n"


def files():
    out = {}
    for st in STAGES:
        out[f"tables/{st[0]}.txt"] = table(st)
        out[f"predictions/{st[0]}.tsv"] = predictions(st)
    return out


def main(argv):
    bad = 0
    for p, txt in files().items():
        f = os.path.join(HERE, p)
        if "--check" in argv:
            cur = open(f).read() if os.path.exists(f) else None
            if cur != txt:
                print(f"{p} is not what gen/make.py writes")
                bad = 1
        else:
            with open(f, "w") as fh:
                fh.write(txt)
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
