#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r30-evst2's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

Every row is one plain 64 x 64 triangle (E547's `tri --width 64 --height 64`; e5: `-n 3`) of t10
under regtimeline (rt), which samples the registers read-only through /dev/mem from LEAD seconds
before the job to TOTAL seconds (or the job's end). No knob, no write, no fault, no hang."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
TRI = "tri --width 64 --height 64"
# the register sets: R1 the densest (CR_EVENT_STATUS alone); R4 adds CR_EVENT_STATUS2, CR_CACHE_CTRL
# and CR_USE0_SERV_EVENT; RW is r23-dpm's timeline set (E1099-E1101) with E547's 0x0218 and R4
R1 = "0x012c"
R4 = "0x0118,0x012c,0x0804,0x0b14"
RW = ("0x0118,0x012c,0x0218,0x0480-0x0490,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,"
      "0x070c-0x0710,0x0720-0x0734,0x0748,0x0804,0x0a74,0x0b14")
# (stage, regs, TOTAL, LEAD, tri args, controls' extra keys, fit rows, held-out rows, ivl window ns)
STAGES = [
    ("e1", R1, "1.5", "0.5", TRI, (), 0, 8, (300, 2500)),
    ("e5", R1, "1.5", "0.5", TRI + " -n 3", (), 0, 5, (300, 2500)),
    ("e2", R4, "1.5", "0.5", TRI, ("idle2", "cache", "se16"), 0, 10, (600, 4000)),
    ("e3", RW, "0", "0.3", TRI, ("idle2", "cache", "se16"), 0, 8, (2000, 15000)),
    ("e4", R4, "6", "5.5", TRI, ("idle2", "cache", "se16"), 0, 1, (600, 4000)),
]
HEAD = {
    "e1": "e1 (10, the 1-register contrast, CR_EVENT_STATUS alone): two controls (first and last) and 8 plain triangles, every model frozen from E1115 (held out). Frozen: H-ALONE (bit 26 as 0x24000000 only), H-WIDE1 (its first episode 40 to 140 us), H-BEFORE (first rise 60 to 200 us before the first rise of bit 18 or 0, fallen before it), H-SW, H-SUB (bits 6, 9, 20 never seen), H-IDLE (0x20000000 outside the job); H-PART (seen in 0 to 7 of 8) against H-EVERY (8 of 8). Stop: a row that does not draw exactly, a missing or cut timeline.",
    "e5": "e5 (7, bit 26 per render): -n 3 in one context, CR_EVENT_STATUS alone. Frozen (restated from E1115): H-ONCE (at most 2 of 5 rows with two or more bit 26 episodes) against H-EACH (3 or more rows with three or more, one a render); anything else refutes both. Stop as e1.",
    "e2": "e2 (12, the read rule's other registers): CR_EVENT_STATUS2, CR_CACHE_CTRL and CR_USE0_SERV_EVENT beside CR_EVENT_STATUS. Frozen from E1116's post-hoc readings (held out here): H-ALONE, H-SW, H-IDLE, H-NARROW4 (bit 26's first episode 3 to 12 us with these four registers), H-CC-KICK (0x0804 0x0000ffff after the reset, 0x1000ffff from the kick to the end of the run, its change 15 to 60 us before bit 26's first rise where bit 26 precedes the render end) against H-CC-FLAT (no change), H-SE-EVENTS (0x0b14 7 to 13 counts beyond the ticks over the job) against H-SE-TICKS (within 1). Stop as e1, and a tick stop (0x0b14 bit 16 clear in the last sample, or under half a count a ms): the session ends.",
    "e3": "e3 (10, 27 registers): r23-dpm's register set with R4. Frozen: e2's models with H-NARROW27 (bit 26's first episode 8 to 20 us) in place of H-NARROW4; H-DENSITY (e1's seen fraction at least 0.2 above e3's) against H-INDEP (within 0.2) [infer: E1115 and E1116 0.32]. Stop as e2.",
    "e4": "e4 (2, idle): 5.5 s of R4 before one triangle. Frozen: the controls' idle words (0x0804 0x0000ffff after the reset), 0x0b14 0.9 to 1.1 counts a ms (E009, E1116), H-IDLE, and e2's row models on e4-01. Stop as e2.",
}


def rows(st):
    name, regs, total, lead, tri, extra, nfit, nheld, _ = st
    keys = ",".join(("diff", "idle", "ivl") + extra)
    rt = f"{total} {lead} {regs} -- {T10} {tri}"
    out = [(f"{name}-c1", "control", f"reads:{keys}", rt)]
    out += [(f"{name}-{i + 1:02d}", "fit" if i < nfit else "held", "-", rt)
            for i in range(nfit + nheld)]
    if name != "e4":
        out.append((f"{name}-c2", "control", f"reads:{keys}", rt))
    return out


def table(st):
    lines = [f"#stage {st[0]}", "#limit 0", "# " + HEAD[st[0]]]
    lines += [f"{n}|{s}|safe|{k}|rt|{a}" for n, s, k, a in rows(st)]
    return "\n".join(lines) + "\n"


# the frozen values: (quantity, value, model, source); a value "lo..hi" is a closed window
CTL = [("diff", "0", "H-DRAW", "E1115, E1116 (47 of 47 jobs drew exactly)"),
       ("idle", "0x20000000", "H-IDLE", "E1115 (14 of 14), E547")]
CTL4 = [("idle2", "0x00000400", "H-IDLE", "E547, E1116 (CR_EVENT_STATUS2 idle)"),
        ("cache", "0x0000ffff", "H-IDLE", "the kit's snap0.regs after the reset (r29-kreg s0, r30-evst; E1116): 0x0804 0x0000ffff"),
        ("se16", "1", "H-IDLE", "E009, E1116 (bit 16 set in the first sample)")]
ROWE = [("b26word", "0x24000000", "H-ALONE", "E1115, E1116 (29 of 29 episodes)"),
        ("swmaster", "1", "H-SW", "E547, E1115"),
        ("outside", "0", "H-IDLE", "E1115, E1116 (0x20000000 outside the job)")]
ROW1 = [("b26first", "40..140", "H-WIDE1", "E1115 (first episodes 55 to 93 us in 7 of 8; 21.1 in one)"),
        ("b26lead", "60..200", "H-BEFORE", "E1115 (87.7 to 118.7 us, 8 of 8)"),
        ("b26clear", "1", "H-BEFORE", "E1115 (8 of 8)"),
        ("sub", "0", "H-SUB", "E1115 (14 of 14)")]
ROWR = [("ccword", "0x1000ffff", "H-CC-KICK", "E1116 post hoc (24 of 24 rows)"),
        ("ccback", "0", "H-CC-KICK", "E1116 post hoc (held to the end, 24 of 24)"),
        ("cc26", "15..60", "H-CC-KICK", "E1116 post hoc (21.3 to 40.0 us in 7 of 10; only where bit 26 precedes the render end)"),
        ("ccchg", "0", "H-CC-FLAT", "E258 [infer] (refuted post hoc by E1116)"),
        ("seextra", "7..13", "H-SE-EVENTS", "E1116 post hoc (9 to 11, 24 of 24)"),
        ("seextra", "-1..1", "H-SE-TICKS", "E009 (ticks only measured)")]
WIDTH = {"e2": ("3..12", "H-NARROW4", "E1116 post hoc (4.9 to 7.6 us, 7 episodes)"),
         "e4": ("3..12", "H-NARROW4", "E1116 post hoc (4.9 to 7.6 us, 7 episodes)"),
         "e3": ("8..20", "H-NARROW27", "E1116 post hoc (11.8 to 12.6 us, 3 episodes)")}
STAGEQ = {
    "e1": [("seen", "8..8", "H-EVERY", "-"), ("seen", "0..7", "H-PART", "E1115 (8 of 14)")],
    "e5": [("multi", "0..2", "H-ONCE", "E1115 (1 of 5 rows with two)"),
           ("each", "3..5", "H-EACH", "-")],
    "e2": [],
    "e3": [("density", "0.2..1", "H-DENSITY", "E1115, E1116 (0.57 against 0.25) [infer]"),
           ("density", "-0.2..0.2", "H-INDEP", "-")],
    "e4": [("tickrate", "0.9..1.1", "H-IDLE", "E009, E1116 (0.9976)")],
}


def predictions(st):
    name, regs = st[0], st[1]
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for n, s, _, _ in rows(st):
        if s == "control":
            ctl = CTL + (CTL4 if "0x0b14" in regs else [])
            ctl = ctl + [("ivl", "%d..%d" % st[8], "H-RATE", "E1115, E1116 (539 to 548 ns with 1 register, 1406 to 1542 with 4, 8989 to 9234 with 27)")]
            out += [f"{n}\t{q}\t{v}\t{m}\tcontrol\t{src}" for q, v, m, src in ctl]
        else:
            r = ROWE + (ROW1 if name == "e1" else [])
            if name in WIDTH:
                r = r + [("b26first",) + WIDTH[name]] + ROWR
            out += [f"{n}\t{q}\t{v}\t{m}\t{s}\t{src}" for q, v, m, src in r]
    out += [f"{name}\t{q}\t{v}\t{m}\tstage\t{src}" for q, v, m, src in STAGEQ[name]]
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
