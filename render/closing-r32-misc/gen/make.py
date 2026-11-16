#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r32-misc's tables and frozen predictions (tables/STAGE.txt, predictions/STAGE.tsv).

  make.py           write them
  make.py --check   exit 1 when a written file is not what this generator writes

Every job is one plain 64 x 64 triangle of t10 (`tri --width 64 --height 64`) after the kit's
reset; m2's under regtimeline (rt, read only through /dev/mem). The kit word `pre:miscinfo`
(resgx545 45bbaaa) reads debugfs miscinfo after the reset and before snap0: one GETMISCINFO
command, served, with no INVAL_DATA. No knob, no kreg, no register write, no planned fault or
hang. Every model is frozen from r31-cc's kept rows and kernel log (E1122, E1123; post hoc
there) or from the kernel's code at the fork pin, so every non-control row is held out."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T10 = '"$HOME/sgxfive-test-t10"'
TRI = "tri --width 64 --height 64"
RT = f"1.5 0.5 0x0804,0x0b14 -- {T10} {TRI}"
W = "pre:miscinfo"
# the boot's own GETMISCINFO after each of r31-cc's 67 resets answered after 130 to 285 us
# (out/20261116-144402/c1..c5/kernel.log); the word's command is the same request
MI_US = "100..400"
FW, HW = "0x0000ffff", "0x1000ffff"
SRC_FW = ("E1123 [infer: the firmware's | 0x10000000 at INVAL_DATA, E013]; r31-cc 52 of 52 "
          "snap0 0x0000ffff after the boot's own served GETMISCINFO (kernel.log)")
SRC_HW = "the design closing29/r31-cc/fold/next-miscinfo.md: any served kick sets bit 28"
SRC_ONE = "E1122, E1123: a triangle's kick leaves 0x1000ffff (r31-cc 52 of 52 snap9)"

STAGES = ["m1", "m2"]
HEAD = {
    "m1": "m1 (9, no timeline): three controls (c1, c3 without the word: the boot's kick alone; c2 with it: the read served), 6 rows with pre:miscinfo held out. snap0 reads CR_CACHE_CTRL after a served GETMISCINFO without INVAL_DATA: H-CC-FW 0x0000ffff against H-CC-HW 0x1000ffff; snap9 after the triangle 0x1000ffff (H-CC-ONE, each row's positive control); the read answered in 100 to 400 us (H-MI-LAT). Stop: a row that does not draw exactly or lacks `tri: 1 renders ok`; a read not served (the kit, rc 19); the session ends.",
    "m2": "m2 (2, regtimeline 0x0804,0x0b14 from 0.5 s before the triangle): both with pre:miscinfo; the timeline's first sample after the read (H-CC-FW against H-CC-HW again), one change to 0x1000ffff (H-CC-ONE), 10 to 40 ms after the tool starts as without the read (H-CC-LAT, E1122). Stop as m1, and a missing or cut timeline or regtimeline's rc not 0.",
}


def rows(st):
    if st == "m1":
        out = [("m1-c1", "control", "reads:diff,cache,cache9,kicks", "t10", TRI)]
        out += [(f"m1-{i:02d}", "held", W, "t10", TRI) for i in (1, 2, 3)]
        out.append(("m1-c2", "control", f"{W} reads:diff,mi,kicks", "t10", TRI))
        out += [(f"m1-{i:02d}", "held", W, "t10", TRI) for i in (4, 5, 6)]
        out.append(("m1-c3", "control", "reads:diff,cache,cache9,kicks", "t10", TRI))
        return out
    return [("m2-c1", "control", f"{W} reads:diff,ivl,mi,kicks", "rt", RT),
            ("m2-01", "held", W, "rt", RT)]


def table(st):
    lines = [f"#stage {st}", "#limit 0", "# " + HEAD[st]]
    lines += [f"{n}|{s}|safe|{k}|{t}|{a}" for n, s, k, t, a in rows(st)]
    return "\n".join(lines) + "\n"


def preds(st):
    out = [("case", "quantity", "value", "model", "set", "source")]
    for n, s, k, t, _ in rows(st):
        word = W in k.split()
        if s == "control":
            out.append((n, "diff", "0", "H-DRAW", s, "E1122, E1123 (52 of 52 jobs drew exactly)"))
            if t == "rt":
                out.append((n, "ivl", "400..3000", "H-RATE", s,
                            "E1122 (849 to 864 ns a sample with 2 registers)"))
            if word:
                out.append((n, "mi", "1", "H-MI", s, "the kit: a read not served stops the "
                            "stage before the job (rc 19), so a served read is the premise"))
                out.append((n, "kicks", "2", "H-KICKS", s, "the boot's GETMISCINFO "
                            "(sgxfive_ident_ask) and the word's, each logs `SGX firmware: core`"))
            else:
                out.append((n, "cache", FW, "H-IDLE", s, SRC_FW))
                out.append((n, "cache9", HW, "H-CC-ONE", s, SRC_ONE))
                out.append((n, "kicks", "1", "H-KICKS", s, "r31-cc kernel.log: 67 resets, 67 "
                            "boot answers (130 to 285 us)"))
            continue
        out.append((n, "cache", FW, "H-CC-FW", s, SRC_FW))
        out.append((n, "cache", HW, "H-CC-HW", s, SRC_HW))
        out.append((n, "cache9", HW, "H-CC-ONE", s, SRC_ONE))
        out.append((n, "mius", MI_US, "H-MI-LAT", s, "r31-cc kernel.log: the boot's answers "
                    "130 to 285 us (post hoc)"))
        if t == "rt":
            out.append((n, "ccfirst", FW, "H-CC-FW", s, SRC_FW))
            out.append((n, "ccfirst", HW, "H-CC-HW", s, SRC_HW))
            out.append((n, "ccn", "1", "H-CC-ONE", s, "E1122 (28 of 28)"))
            out.append((n, "ccword", HW, "H-CC-ONE", s, "E1122 (28 of 28)"))
            out.append((n, "ccstart", "10..40", "H-CC-LAT", s, "E1122 (18.3 to 25.2 ms, 28 of "
                        "28) post hoc"))
    # m2-c1 is a control whose cache readings are not its premise: frozen as a held row's
    if st == "m2":
        out += [("m2-c1", q, v, m, "held", src) for q, v, m, src in (
            ("ccfirst", FW, "H-CC-FW", SRC_FW), ("ccfirst", HW, "H-CC-HW", SRC_HW),
            ("ccstart", "10..40", "H-CC-LAT", "E1122 (18.3 to 25.2 ms) post hoc"))]
    if st == "m1":
        out += [("m1-c2", q, v, m, "held", src) for q, v, m, src in (
            ("cache", FW, "H-CC-FW", SRC_FW), ("cache", HW, "H-CC-HW", SRC_HW),
            ("cache9", HW, "H-CC-ONE", SRC_ONE))]
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
