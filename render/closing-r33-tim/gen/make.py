#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r33-tim's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

Every job is one plain 64 x 64 triangle of t10 (`tri --width 64 --height 64`) after the kit's
reset, under regtimeline (rt, read only through /dev/mem): t1 samples CR_EVENT_STATUS (0x012c),
CR_CACHE_CTRL (0x0804) and CR_EVENT_TIMER (0x0acc) for 60 ms from 5 ms before the tool starts;
t1d samples 0x0acc alone (densest) for 40 ms. No knob, no kreg, no register write, no planned
fault or hang. The timer models come from the records that measured it (E008, E009 through
doc/specs/hw_spec.md 12, E532's correction, E746, E747, E751, E813, doc/specs/pds_isa.md 8.9) and
the 208 kit snapshots of r30-evst2, r31-cc and r32-misc (post hoc there); every row is held out."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
TRI = "tri --width 64 --height 64"
RT = {"t1": f"0.06 0.005 0x012c,0x0804,0x0acc -- {T10} {TRI}",
      "t1d": f"0.04 0.005 0x0acc -- {T10} {TRI}"}
STAGES = ["t1", "t1d"]

S_EN = ("E008, E746, E751 (bit 24 set, counting); kit snapshots r30-evst2, r31-cc, r32-misc: "
        "208 of 208 bit 24 set, bits 23:0 below 400000 (post hoc)")
S_RANGE = ("hw_spec 12.2 (E746, E751; 18 of 18 stop samples below 400000, E813-E830); 208 of 208 "
           "kit snapshots (post hoc)")
S_24 = "the alternative: a free 24-bit counter (pds_isa 8.9's 25-bit load, E146's VALUE 23:0)"
S_RELOAD = ("E008, E532 correction: the boot loads 0x61a80 | bit 24 (400000), a tick served at once "
            "samples 0x061a70")
S_399 = ("E009 via hw_spec 12 and boot_sequence 2.1: the tick at 997.46 Hz x 400000 clocks = "
         "398.98 counts/us; 25000 CR_TIMER units a tick at 1/16 (E746, E751)")
S_400 = "the DDK's SYS_SGX_CLOCK_SPEED 400 MHz (boot_sequence 2.1): 400 counts/us"
S_FREE = ("hw_spec 12.2 / E010: the firmware writes EVENT_TIMER only at boot and POWER resume, "
          "so nothing in a kick pass moves it [infer]; E746, E747: a kick's pa2 is the "
          "timer as sampled, agreeing with the CR_TIMER stamps within 5.3 units")
S_WRITE = "the alternative: the kick pass (E1130) writes or reloads EVENT_TIMER in the window"
S_ASYNC = ("E746 (a kick read at three phases gave three values), E747 (138 events any value): "
           "a kick is not served on the tick's phase")
S_SYNC = "the alternative: the kick pass runs at a fixed phase of the tick"
S_ONE = "E1122, E1123, E1127: one change 0x0000ffff -> 0x1000ffff a triangle (44 of 44)"
S_LAT = "E1122 (18.3 to 25.2 ms), E1127 (24.4, 25.2 ms) after the tool starts"

HEAD = {
    "t1": "t1 (11, regtimeline 0x012c,0x0804,0x0acc for 60 ms from 5 ms before the triangle): three controls (diff, the timeline's interval, every 0x0acc sample a running count below 400000; snap0 and snap9 0x0acc the same, scored), 8 rows held out. The timer over the whole timeline: bit 24 set (H-TIM-EN), bits 23:0 below 400000 (H-TIM-RANGE), a reload to 400000 (H-TIM-RELOAD), 399 counts/us and a 1002.6 us period (H-TIM-399 against H-TIM-400); in the window from CR_CACHE_CTRL's change to bit 26's fall the count follows the rate fitted before the change (H-TIM-FREE against H-TIM-WRITE); the count at the change spread over the period across rows (H-TIM-ASYNC against H-TIM-SYNC). Stop: a row that does not draw exactly, lacks `tri: 1 renders ok`, or has no whole timeline with rc 0; the session ends.",
    "t1d": "t1d (4, regtimeline 0x0acc alone for 40 ms, the densest): one control as t1's, 3 rows held out; the rate, period, reload and range as t1's, at about 540 ns a sample. Stop as t1.",
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


IVL = {"t1": ("700..2000", "E1122 (849 to 864 ns with 2 registers), E1120 (about 1470 ns with "
                           "4); every sample stored with 0x0acc in the set [infer]"),
       "t1d": ("400..1200", "E1115, E1122 (540 to 542 ns with one register)")}


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
        out.append((n, "tnoen", "0", "H-TIM-EN", "held", S_EN))
        out.append((n, "tover", "0", "H-TIM-RANGE", "held", S_RANGE))
        out.append((n, "tover", "1..100000000", "H-TIM-24", "held", S_24))
        out.append((n, "tmax", "398500..399999", "H-TIM-RELOAD", "held", S_RELOAD))
        out.append((n, "rate", "398.5..399.5", "H-TIM-399", "held", S_399))
        out.append((n, "rate", "399.5..400.5", "H-TIM-400", "held", S_400))
        out.append((n, "period", "1001.2..1003.8", "H-TIM-399", "held", S_399))
        out.append((n, "period", "998.8..1001.2", "H-TIM-400", "held", S_400))
        if st == "t1":
            out.append((n, "ccn", "1", "H-CC-ONE", "held", S_ONE))
            out.append((n, "ccword", "0x1000ffff", "H-CC-ONE", "held", S_ONE))
            out.append((n, "ccstart", "10..40", "H-CC-LAT", "held", S_LAT))
            out.append((n, "wres", "0..300", "H-TIM-FREE", "held", S_FREE))
            out.append((n, "wtail", "0..300", "H-TIM-FREE", "held", S_FREE))
            out.append((n, "wfit", "0.9..1", "H-TIM-FREE", "held", S_FREE))
            out.append((n, "wtail", "2000..200000", "H-TIM-WRITE", "held", S_WRITE))
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
