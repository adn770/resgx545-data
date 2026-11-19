#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of r38-n3c-s1 (closing29/n3c/design.md, N3c session S1: rows R1 `n0`
and R2 `th`, §2.1). Writes tables/own.txt, tables/tim.txt, tables/post.txt,
predictions/own.tsv, predictions/tim.tsv, predictions/post.tsv and gen/constants.txt; every
input is read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stage own (flagged, the task `emitsn` armed once on slot 0, entry 0, no pds= word): one row n0,
one tester command 1 with `"ticks": true`, the host's fill 0xdeadc0de in slots 2-5 (dwords
72-87) first: r37 A's job (E1149) word for word. emitsn is emitsb's entry 0 without the emit: M1
and the run id in slot 1, cmd 0, a fence, X0 = 0x5a5a3303 (slot 1 dword 2, page dword 70), a
fence, then M4 = 0x5a5a3302 and the run id in slot 4 (dwords 80-81), the echo, state 2, the
tail call. The outcome table is the design's R1 table.

Stage tim (flagged, last of the design's rows): one row th, the stock firmware, t30 `probe` with
the recorded pds-timer-tim-host program and its USE program (resgx545-data
pds/timer/pds-timer-tim-host/bins/, staged as bins/), the recorded harness's options (probe.py
tool_args: --temps 32 --pds 36 --use), under regtimeline sampling 0x0acc alone, the shape of
E1133's t1d (TOTAL 0.06, LEAD 0.005). The program loads `tim` with 0x00abcde0 (bit 24 clear:
stopped) and stores `tim` back to scratch (dwords 2-5 and 10-13). The outcome table is the
design's R2 table. Stage post: the stock firmware's triangle and fill (the health pair's argv)
after the tim stage's last reset.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

ARM = "slots=0x1 entry=0"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SOURCE = "asm/fwtask/emitsn.s"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1 = 0x5A5A3301           # entry 0's marker (slot 1 dword 0)
X0 = 0x5A5A3303           # X0 (slot 1 dword 2)
M4 = 0x5A5A3302           # done's marker (slot 4)
SLOT1, SLOT4 = 0x44, 0x50
X0_AT = SLOT1 + 2         # dword 70
FILL = 0xDEADC0DE
FILL_AT, FILL_N = 0x48, 16                # slots 2, 3, 4 and 5 (dwords 72-87)
TIMEOUT_MS = 200
DESIGN = "n3c design §2.1"
OWN_ROWS = [("n0", "fit")]

# R2: the recorded probe and its harness (pins at the frozen data commit)
BINS = "pds/timer/pds-timer-tim-host/bins/"
PROG, USE = "pds-timer-tim-host__0.bin", "sa_dump.bin"
TIM_VALUE = 0x00ABCDE0
SCRATCH_TIM = (0x008, 0x00C, 0x010, 0x014, 0x028, 0x02C, 0x030, 0x034)  # tim after 0..64 nops
RT_TOTAL, RT_LEAD, RT_REGS = "0.06", "0.005", "0x0acc"
IVL = "2500..5000"         # E1133's bounds for one register (t1d: TOTAL / samples, ns)
PROBE = (f'{RT_TOTAL} {RT_LEAD} {RT_REGS} -- "$HOME/sgxfive-test-t30" probe --temps 32 --pds 36 '
         f'--use $S/bins/{USE} $S/bins/{PROG}')

# R1's table: {model: {quantity: value}}. Values: 0xV; `@runid`; `ok`; `>=N` (Δtick, the record's
# ticks); `<25|nodone` (N0-STOP: the record's ticks below 25, or the job not done).
OWN = {
    "N0-OK": {f"res:0x{X0_AT:x}": f"0x{X0:08x}", f"res:0x{SLOT4:x}": f"0x{M4:08x}",
              f"res:0x{SLOT4 + 1:x}": "@runid", "res:0x2": "0x2", "ticks": ">=25", "gate": "ok"},
    "N0-STOP": {"end": "<25|nodone"},
}
OWN_WHAT = {"N0-OK": "the stop needs the emit (expected)",
            "N0-STOP": "our path stops the tick without any emit"}
OWN_CONTROLS = [
    ("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
    (f"res:0x{SLOT1:x}", f"0x{M1:08x}", "E0: entry 0 ran this command (slot 1 marker)"),
    (f"res:0x{SLOT1 + 1:x}", "@runid", "E0: entry 0 ran this command (slot 1 run id)"),
    ("res:0x1", "0x0", "E0: cmd 0 (entry 0 cleared it)"),
    ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
    ("snap9:0x0c08", "0x0", "B: no BIF fault after the job (a fault is its own outcome)"),
]
# R2's table. tl: 0x0acc in the timeline after the change (`0xV`: the first stored sample that is
# not a running count is V and no stored sample after it differs; `running`: every stored sample
# is a running count); snap9: 0x0acc in NAME.snap9.regs; scratch: the eight tim reads.
TIM = {
    "V0-HOLDS": {"tl": f"0x{TIM_VALUE:08x}", "snap9:0x0acc": f"0x{TIM_VALUE:08x}",
                 "scratch": f"0x{TIM_VALUE:08x}"},
    "V0-NOT": {"tl": "running", "snap9:0x0acc": "running", "scratch": f"0x{TIM_VALUE:08x}"},
}
TIM_WHAT = {"V0-HOLDS": "the host sees the PDS write (expected)",
            "V0-NOT": "a PDS tim is not the host's 0x0acc"}
TIM_CONTROLS = [
    ("ivl", IVL, "the timeline's interval, ns a sample (TOTAL / samples), E1133's bounds"),
    ("pre", "running", "every stored sample before the change a running count (at least one)"),
]


def source_facts():
    """What emitsn.s stores where, read at the frozen commit."""
    s = pins.blob("resgx545:" + SOURCE).decode()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip() and not ln.startswith(";")]
    return dict(patches=[int(x) for x in re.findall(r"@patch res\+(\d+)", s)],
                marks=[int(x, 16) for x in re.findall(r"mov r7, #(0x5a5a33[0-9a-f]{2})", s)],
                emit=sum(1 for ln in lines if ln.startswith("emitpds")),
                pds=len(re.findall(r"@patch pds", s)),
                entries=[ln for ln in lines if ln.startswith("@entry")])


def bins():
    """{name: bytes} of the recorded program and USE program at the frozen data commit."""
    return {n: pins.blob("data:" + BINS + n) for n in (PROG, USE)}


def own_job():
    return ('{"cmd": 1, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true}'
            % (FILL_AT, ", ".join([str(FILL)] * FILL_N), TIMEOUT_MS))


def tables():
    own = ["#stage own",
           "#limit 0",
           "# own: N3c row R1 n0 (closing29/n3c/design.md §2.1), the task emitsn armed once",
           f"# ({ARM}); one command 1 with ticks, the fill 0xdeadc0de in slots 2-5 first (r37 A's",
           "# job). One row by design: any stop ends the session (rc 4; on_stop end); run/hooks.sh",
           "# stops it (rc 24) after an ok end whose markers, run id, cmd, state or fill are wrong."]
    for n, st in OWN_ROWS:
        own.append(f"{n}|{st}|flagged|-|owntask|{own_job()}")
    tim = ["#stage tim",
           "#limit 0",
           "# tim: N3c row R2 th, the instrument: the stock firmware runs the recorded",
           "# pds-timer-tim-host probe (movs tim with 0x00abcde0, bit 24 clear: the EDM tick stops",
           "# by design until the next reset) under regtimeline on 0x0acc; the stage's last reset",
           "# restarts the counter.",
           f"th|held|flagged|-|rt|{PROBE}"]
    post = ["#stage post",
            "#limit 0",
            "# post: the stock firmware draws the health pair's triangle and fill exactly after",
            "# the tim stage's last reset.",
            "p1-tri|control|safe|reads:diff|t30|tri",
            "p2-fill|control|safe|reads:diff|t30|fill"]
    return ["\n".join(t) + "\n" for t in (own, tim, post)]


def predictions():
    own = [HEAD]
    for n, st in OWN_ROWS:
        for model, qs in OWN.items():
            for q, v in qs.items():
                own.append(f"{n}\t{q}\t{v}\t{model}\t{st}\t{DESIGN} R1: {OWN_WHAT[model]}\n")
        for q, v, why in OWN_CONTROLS:
            own.append(f"{n}\t{q}\t{v}\tCTL\t{st}\t{DESIGN} R1 control {why}\n")
    tim = [HEAD]
    for model, qs in TIM.items():
        for q, v in qs.items():
            tim.append(f"th\t{q}\t{v}\t{model}\theld\t{DESIGN} R2: {TIM_WHAT[model]}\n")
    for q, v, why in TIM_CONTROLS:
        tim.append(f"th\t{q}\t{v}\tCTL\theld\t{DESIGN} R2 control {why}\n")
    post = [HEAD,
            "p1-tri\tdiff\t0\tCTL\tcontrol\tthe kit's health triangle (E1134's health pair)\n",
            "p2-fill\tdiff\t0\tCTL\tcontrol\tthe kit's health fill (E1134's health pair)\n"]
    return "".join(own), "".join(tim), "".join(post)


def constants():
    import hashlib
    out = [f"ARM {ARM}", f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}",
           f"TIM 0x{TIM_VALUE:08x}", f"PROBE {PROBE}"]
    out += [f"BIN {n} {hashlib.sha256(b).hexdigest()}" for n, b in sorted(bins().items())]
    return "\n".join(out) + "\n"


def build():
    to, tt, tp = tables()
    po, pt, pp = predictions()
    return {"tables/own.txt": to, "tables/tim.txt": tt, "tables/post.txt": tp,
            "predictions/own.tsv": po, "predictions/tim.tsv": pt, "predictions/post.tsv": pp,
            "gen/constants.txt": constants()}


def main(argv):
    out = build()
    check = "--check" in argv
    bad = []
    for rel, body in out.items():
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p).read() != body:
                bad.append(rel)
        else:
            open(p, "w").write(body)
    if bad:
        print("not current: " + ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
