#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r33-tim2's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

The rerun of r33-tim (E1131, whose controls failed on the sample interval: the builder froze the
idle loop's spacing): the same 15 jobs, each one plain 64 x 64 triangle of t10 (`tri --width 64
--height 64`) after the kit's reset, under regtimeline (rt, read only through /dev/mem): t1
samples CR_EVENT_STATUS (0x012c), CR_CACHE_CTRL (0x0804) and CR_EVENT_TIMER (0x0acc) for 60 ms
from 5 ms before the tool starts; t1d samples 0x0acc alone for 40 ms. No knob, no kreg, no
register write, no planned fault or hang. The interval premise and every held-out value come
from E1131's post-hoc readings (fold/posthoc.txt of render/closing-r33-tim) and the earlier
timer records (E008, E009, E532, E746, E747, E751); every row is held out."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
TRI = "tri --width 64 --height 64"
RT = {"t1": f"0.06 0.005 0x012c,0x0804,0x0acc -- {T10} {TRI}",
      "t1d": f"0.04 0.005 0x0acc -- {T10} {TRI}"}
STAGES = ["t1", "t1d"]

P = "E1131 post hoc"
S_EN = (f"{P}: bit 24 alone in 31:24 in every sample of 15 of 15 rows and every snapshot; E008, "
        "E746, E751")
S_RANGE = (f"{P}: no sample above 400000 in 15 rows, one of exactly 400000 (t1-c2); hw_spec 12.2 "
           "(E746, E751)")
S_24 = "the alternative: a free 24-bit counter (pds_isa 8.9's 25-bit load, E146's VALUE 23:0)"
S_RELOAD = (f"{P}: largest count 399960 to 400000 in 15 rows; E008, E532: the boot loads 0x61a80 "
            "| bit 24")
S_399 = (f"{P}: 398.96 to 399.01 counts/us and 1002.497 to 1002.535 us in 15 of 15 rows; E009 "
         "via hw_spec 12: 997.46 Hz x 400000 = 398.98")
S_400 = "the alternative: the DDK's SYS_SGX_CLOCK_SPEED 400 MHz (boot_sequence 2.1)"
S_LEAD = {"t1": f"{P}: 1213 to 1283 ns (11 rows); E1120's 1.45 us for four registers",
          "t1d": f"{P}: 622 to 782 ns (4 rows); E1115, E1122 (about 541 ns)"}
S_JOB = f"{P}: 4592 to 5714 ns (t1), 5218 to 6190 ns (t1d) [infer: the CPU shared with t10]"
S_ONE = "E1131 post hoc (11 of 11), E1122, E1123, E1127: one change 0x0000ffff -> 0x1000ffff"
S_LAT = f"{P}: 22.93 to 24.10 ms; E1122 18.3 to 25.2 ms; E1127 24.4 and 25.2 ms"
S_LINE = (f"{P}: on the line fitted before the change, the 120 to 300 us median within 93 counts "
          "in 10 of 11 rows and 347 in t1-c2; the window's median within 28 to 633 (a +568 to "
          "+633 step 18 to 40 us after the change in 5 rows, gone by 120 us [infer: the host's "
          "read timing]); hw_spec 12.2: the firmware writes the timer only at boot and resume")
S_WRITE = ("the alternative: the kick pass writes, reloads or stops the timer, which leaves the "
           "count off its line after the window")
S_ASYNC = (f"{P}: the line's count at the change 7389 to 384863 over 11 rows; E746, E747: a kick at "
           "any phase")
S_SYNC = "the alternative: the kick pass runs at a fixed phase of the tick"

HEAD = {
    "t1": "t1 (11, regtimeline 0x012c,0x0804,0x0acc for 60 ms from 5 ms before the triangle; the rerun of r33-tim, E1131): three controls (diff, the interval as E1131 measured it in the job, every 0x0acc sample a running count up to 400000; snap0 and snap9 0x0acc the same, scored), 8 rows held out. The sample spacing before and in the job (H-SPACING); the timer over the whole timeline: bit 24 set (H-TIM-EN), bits 23:0 up to 400000 (H-TIM-RANGE), a reload to 400000 (H-TIM-RELOAD), 399 counts/us and a 1002.5 us period (H-TIM-399 against H-TIM-400); against the line fitted on the 1 ms before CR_CACHE_CTRL's change, the window to bit 26's fall and the 120 to 300 us after it stay near the line (H-TIM-LINE against H-TIM-WRITE); the line's count at the change spread over the period across rows (H-TIM-ASYNC against H-TIM-SYNC). Stop: a row that does not draw exactly, lacks `tri: 1 renders ok`, or has no whole timeline with rc 0; the session ends.",
    "t1d": "t1d (4, regtimeline 0x0acc alone for 40 ms, the densest): one control as t1's, 3 rows held out; the spacing, rate, period, reload and range as t1's. Stop as t1.",
}


def rows(st):
    rt = RT[st]
    if st == "t1":
        out = [("t1-c1", "control")] + [(f"t1-{i:02d}", "held") for i in (1, 2, 3, 4)]
        out += [("t1-c2", "control")] + [(f"t1-{i:02d}", "held") for i in (5, 6, 7, 8)]
        out += [("t1-c3", "control")]
    else:
        out = [("t1d-c1", "control")] + [(f"t1d-{i:02d}", "held") for i in (1, 2, 3)]
    return [(n, s, "reads:diff,ivl,ten" if s == "control" else "-", "rt", rt) for n, s in out]


def table(st):
    lines = [f"#stage {st}", "#limit 0", "# " + HEAD[st]]
    lines += [f"{n}|{s}|safe|{k}|{t}|{a}" for n, s, k, t, a in rows(st)]
    return "\n".join(lines) + "\n"


IVL = {"t1": ("3500..6500", "E1131 post hoc: TOTAL / samples 4061 to 4992 ns over 11 rows (the "
                            "job's spacing: the window is almost all job time)"),
       "t1d": ("2500..5000", "E1131 post hoc: TOTAL / samples 3002 to 3696 ns over 4 rows")}
LEAD = {"t1": "1100..1500", "t1d": "550..900"}


def preds(st):
    out = [("case", "quantity", "value", "model", "set", "source")]
    for n, s, _, _, _ in rows(st):
        if s == "control":
            out.append((n, "diff", "0", "H-DRAW", s, "E1122, E1123, E1126 (every plain triangle "
                        "drew exactly)"))
            out.append((n, "ivl", IVL[st][0], "H-RATE", s, IVL[st][1]))
            out.append((n, "ten", "1", "H-TIM-EN", s, S_EN))
            out.append((n, "ten0", "1", "H-TIM-EN", s, S_EN + "; snap0"))
            out.append((n, "ten9", "1", "H-TIM-EN", s, S_EN + "; snap9"))
        # every row, the controls too: the timer's own quantities, held out
        out.append((n, "lead", LEAD[st], "H-SPACING", "held", S_LEAD[st]))
        out.append((n, "job", "3500..7500", "H-SPACING", "held", S_JOB))
        out.append((n, "tnoen", "0", "H-TIM-EN", "held", S_EN))
        out.append((n, "tover", "0", "H-TIM-RANGE", "held", S_RANGE))
        out.append((n, "tover", "1..100000000", "H-TIM-24", "held", S_24))
        out.append((n, "tmax", "399500..400000", "H-TIM-RELOAD", "held", S_RELOAD))
        out.append((n, "rate", "398.9..399.1", "H-TIM-399", "held", S_399))
        out.append((n, "rate", "399.5..400.5", "H-TIM-400", "held", S_400))
        out.append((n, "period", "1002.4..1002.65", "H-TIM-399", "held", S_399))
        out.append((n, "period", "998.8..1001.2", "H-TIM-400", "held", S_400))
        if st == "t1":
            out.append((n, "ccn", "1", "H-CC-ONE", "held", S_ONE))
            out.append((n, "ccword", "0x1000ffff", "H-CC-ONE", "held", S_ONE))
            out.append((n, "ccstart", "18..27", "H-CC-LAT", "held", S_LAT))
            out.append((n, "as120", "0..400", "H-TIM-LINE", "held", S_LINE))
            out.append((n, "wmed", "0..800", "H-TIM-LINE", "held", S_LINE))
            out.append((n, "as120", "2000..200000", "H-TIM-WRITE", "held", S_WRITE))
    if st == "t1":
        out.append(("t1-all", "tccspread", "100000..400000", "H-TIM-ASYNC", "held", S_ASYNC))
        out.append(("t1-all", "tccspread", "0..20000", "H-TIM-SYNC", "held", S_SYNC))
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
