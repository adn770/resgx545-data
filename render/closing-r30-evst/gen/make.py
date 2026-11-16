#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r30-evst's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

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
    ("e1", R1, "1.5", "0.5", TRI, (), 6, 8, (300, 2500)),
    ("e5", R1, "1.5", "0.5", TRI + " -n 3", (), 2, 3, (300, 2500)),
    ("e2", R4, "1.5", "0.5", TRI, ("idle2", "cache", "se16"), 4, 6, (600, 4000)),
    ("e3", RW, "0", "0.3", TRI, ("idle2", "cache", "se16"), 3, 5, (2000, 15000)),
    ("e4", R4, "6", "5.5", TRI, ("idle2", "cache", "se16"), 0, 1, (600, 4000)),
]
HEAD = {
    "e1": "e1 (16, Q111 bit 26; densest sampling, CR_EVENT_STATUS alone): two controls (first and last) and 14 plain triangles. Frozen: H-ALONE (bit 26 shows as the word 0x24000000 only), H-WIDE (40 to 140 us), H-BEFORE (its first rise 60 to 200 us before the first rise of bit 18 or 0, and it falls before that rise), H-SW (14 and 31 together), H-SUB (bits 6, 9, 20 never seen), H-IDLE (0x20000000 outside the job); the seen count decides H-EVERY (seen in 13+ of 14) against H-PART. Stop: a row that does not draw exactly, a missing or cut timeline.",
    "e5": "e5 (7, Q111 bit 26 per render): -n 3 in one context (renders 2 and 3 not FIRST), CR_EVENT_STATUS alone. Frozen: H-ONCE (at most one bit 26 episode a job) against H-EACH (two or more episodes in 2 or more of the 5 rows; 1 row: cannot tell). Stop as e1.",
    "e2": "e2 (12, the read rule's other registers): CR_EVENT_STATUS2, CR_CACHE_CTRL and CR_USE0_SERV_EVENT beside CR_EVENT_STATUS. Frozen: e1's bit 26 models, H-ST2 (0x0118 0x400 throughout, E547), H-CC-FLAT (0x0804 0x1000ffff throughout, E258) against H-CC-SEEN, H-SE-EVENTS (0x0b14 counts 3 or more beyond the ticks over the job) against H-SE-TICKS (within 1). Stop as e1, and a tick stop (0x0b14 bit 16 clear in the last sample, or under half a count a ms): the session ends.",
    "e3": "e3 (10, density): r23-dpm's register set with R4 (27 registers, E547's r7 interval or slower). Frozen: H-DENSITY (bit 26 seen fraction in e1 at least 0.4 above e3's) against H-INDEP (within 0.25); the first change of a pipeline register before bit 26 gives the kick-to-bit-26 lead [infer]. Stop as e2.",
    "e4": "e4 (2, idle): 5.5 s of R4 before one triangle. Frozen: H-IDLE (0x012c 0x20000000, 0x0118 0x400, 0x0804 0x1000ffff in every sample before the job), 0x0b14 bit 16 set and its count 0.9 to 1.1 a ms (E009). Stop as e2.",
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
CTL = [("diff", "0", "H-DRAW", "E547 (every tri64 job drew exactly)"),
       ("idle", "0x20000000", "H-IDLE", "E547 (idle word, six controls)")]
CTL4 = [("idle2", "0x00000400", "H-IDLE", "E547 (CR_EVENT_STATUS2 idle)"),
        ("cache", "0x1000ffff", "H-IDLE", "E258 (platform/register-timelines: 0x0804 in every sample)"),
        ("se16", "1", "H-IDLE", "E009 (bit 16 always set)")]
ROW1 = [("b26word", "0x24000000", "H-ALONE", "E547 tri64 timelines (5 of 5 episodes)"),
        ("b26width", "40..140", "H-WIDE", "E547 tri64 (53 to 81 us at 1.22 and 2.67 us)"),
        ("b26lead", "60..200", "H-BEFORE", "E547 tri64 (88 to 128 us to the first rise of 18 or 0)"),
        ("b26clear", "1", "H-BEFORE", "E547 tri64 (bit 26 fell before 18 or 0 rose, 5 of 5)"),
        ("swmaster", "1", "H-SW", "E547 (14 and 31 together, 41 of 41 jobs)"),
        ("sub", "0", "H-SUB", "E547 (bits 6, 9, 20 not seen in a triangle)"),
        ("outside", "0", "H-IDLE", "E547 (0x20000000 outside the job)")]
ROW4 = [("st2", "0", "H-ST2", "E547 tri64 (0x0118 no pulse, 10 of 10)"),
        ("ccchg", "0", "H-CC-FLAT", "E258 (0x0804 flat in two tri jobs at about 75 us) [infer]"),
        ("seextra", "3..1000", "H-SE-EVENTS", "E009 [infer]: bits 15:0 the event queue's COUNT, so a served event counts"),
        ("seextra", "-1..1", "H-SE-TICKS", "E009 (ticks only measured)")]
STAGEQ = {
    "e1": [("seen", "13..14", "H-EVERY", "-"), ("seen", "0..12", "H-PART", "E547 r2 (4 of 5) [infer]")],
    "e5": [("multi", "0..0", "H-ONCE", "E547 tri256n3 r2 (one a job)"),
           ("multi", "2..5", "H-EACH", "E547 tri256n3 r7 (6 in 4 jobs)")],
    "e2": [],
    "e3": [("density", "0.4..1", "H-DENSITY", "E547 (r2 4 of 5, r7 1 of 5) [infer]"),
           ("density", "-0.25..0.25", "H-INDEP", "-")],
    "e4": [("tickrate", "0.9..1.1", "H-IDLE", "E009 (997.46 Hz)")],
}


def predictions(st):
    name, regs = st[0], st[1]
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for n, s, _, _ in rows(st):
        if s == "control":
            ctl = CTL + (CTL4 if "0x0b14" in regs else [])
            ctl = ctl + [("ivl", "%d..%d" % st[8], "H-RATE", "E547 kept timelines (1.7 to 4.7 us a sample over the whole run, 2 to 7 registers)")]
            out += [f"{n}\t{q}\t{v}\t{m}\tcontrol\t{src}" for q, v, m, src in ctl]
        elif name != "e4":
            r = ROW1 + (ROW4 if "0x0b14" in regs else [])
            out += [f"{n}\t{q}\t{v}\t{m}\t{s}\t{src}" for q, v, m, src in r]
        else:
            out += [f"{n}\toutside\t0\tH-IDLE\t{s}\tE547 (idle word)",
                    f"{n}\tst2\t0\tH-ST2\t{s}\tE547 tri64"]
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
