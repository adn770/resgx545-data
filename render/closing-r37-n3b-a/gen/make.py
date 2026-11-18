#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of r37-n3b-a and r37-n3b-b (closing29/n3b/design.md, N3b: breadcrumbs
that split E1148's causes; the two sessions differ in STEP and the arm only). Writes
tables/own.txt, tables/post.txt, predictions/own.tsv, predictions/post.tsv and
gen/constants.txt; every input is read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stage own (flagged, the task `emitsb` armed once on slot 0, entry 0): one row, one tester
command 1 with `"ticks": true` (the runner reads HostCtl dword 12 right before the command write
and 30 ms after the window). emitsb is emitsa (r36-n3, E1148) plus two stores: X0 = 0x5a5a3303
in slot 1 dword 2 (page dword 70) right after the emitpds, and S1 = 0x5a5a3304 in slot 5 dword 0
(page dword 84) as entry 1's first work. The host fills slots 2-5 (dwords 72-87) with 0xdeadc0de
first, so a store that did not happen shows the fill.

Step A (r37-n3b-a): arm `slots=0x1 entry=0`, the kernel's v1 image (douta, douta, doutu, halt:
E1148's). Step B (r37-n3b-b): arm `slots=0x1 entry=0 pds=crumb`, the crumb image (three movs tim
breadcrumbs, T1 = 0, T2 = 0x200, T3 = 0x005a3305; each with bit 24 clear: the EDM tick stops at
T1 by design until the next reset). The outcome tables are the design's §1.4, frozen in
predictions/own.tsv; the controls are §1.5's. Stage post: the stock firmware's triangle and fill
(the health pair's argv) after the disarm.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "A"
ARM = {"A": "slots=0x1 entry=0", "B": "slots=0x1 entry=0 pds=crumb"}[STEP]
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SOURCE = "asm/fwtask/emitsb.s"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1 = 0x5A5A3301           # entry 0's marker (slot 1 dword 0)
X0 = 0x5A5A3303           # past the emit (slot 1 dword 2)
M4 = 0x5A5A3302           # entry 1's marker (slot 4)
S1 = 0x5A5A3304           # entry 1's first store (slot 5 dword 0)
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5 = 0x44, 0x48, 0x4C, 0x50, 0x54
X0_AT, S1_AT = SLOT1 + 2, SLOT5           # dwords 70 and 84
FILL = 0xDEADC0DE
FILL_AT, FILL_N = SLOT_PA, 16             # slots 2, 3, 4 and 5 (dwords 72-87)
TIMEOUT_MS = 200
T3 = 0x005A3305                           # the crumb image's dword 7
# the hooks' fallback for V0-V3 (a snap0 without ta3dctl lines: the kit mock's fake regs only):
# TA3DCtl dwords 0-3 in a kept snap0 of r35-sa (E1144), module 7CE8E38E
SNAP_PIN = "data:render/closing-r35-sa/out/20261118-085610/a/c0a-k.snap0.regs.gz"
ROWS = [("c1-a", "fit")]
DESIGN = "n3b design §1.4"

# §1.4's tables: {model: {quantity: value}}. Values: 0xV; `fill` (the host's fill); `@runid`;
# `any`; `LO-HI` and `>=N` (Δtick, the record's ticks); `running` (T: bit 24 set, bits 23:0 at
# most 400000, two reads differ). T = 0x0acc in snap9 and in the stop dump.
OUTCOMES = {
    "A": {
        "A-ISSUER": {f"res:0x{X0_AT:x}": "fill", f"res:0x{S1_AT:x}": "fill",
                     f"res:0x{SLOT4:x}": "fill", "res:0x2": "0x0", "ticks": "0-2"},
        "A-PAST": {f"res:0x{X0_AT:x}": f"0x{X0:08x}", f"res:0x{S1_AT:x}": "fill",
                   f"res:0x{SLOT4:x}": "fill", "res:0x2": "0x0", "ticks": "any"},
        "A-E1": {f"res:0x{X0_AT:x}": f"0x{X0:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                 f"res:0x{SLOT4:x}": "fill", "res:0x2": "0x0", "ticks": "any"},
        # Δtick: the window ends at done (fwtask_run.py one_cmd), then 30 ms: at least 25 ticks
        # when the tick ran (the design's >= 150 assumed the full 200 ms window)
        "A-DONE": {f"res:0x{X0_AT:x}": f"0x{X0:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                   f"res:0x{SLOT4:x}": f"0x{M4:08x}", f"res:0x{SLOT4 + 1:x}": "@runid",
                   "res:0x2": "0x2", "ticks": ">=25"},
    },
    "B": {
        "B-1": {"T": "running", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                "res:0x2": "0x0"},
        "B-1p": {"T": "0x00000000", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                 "res:0x2": "0x0"},
        "B-2a": {"T": "0x00000200", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                 "res:0x2": "0x0"},
        "B-2b": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                 "res:0x2": "0x0"},
        "B-3": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                f"res:0x{SLOT4:x}": "fill", "res:0x2": "0x0"},
        "B-NONE": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                   f"res:0x{SLOT4:x}": f"0x{M4:08x}", f"res:0x{SLOT4 + 1:x}": "@runid",
                   "res:0x2": "0x2"},
    },
}
WHAT = {
    "A-ISSUER": "the emit stops or ends the issuing task",
    "A-PAST": "issuer on; no entry-1 store: (1), (2) or early (3)",
    "A-E1": "(3): entry 1 stopped after its first store",
    "A-DONE": "E1148 not reproduced",
    "B-1": "(1) the program never ran",
    "B-1p": "(1') started, stopped at a douta",
    "B-2a": "(2a) stopped at the doutu (never issued)",
    "B-2b": "(2b) doutu issued, our code never stored",
    "B-3": "(3) entry 1 started, stopped after its first store",
    "B-NONE": "none: all ran",
}
# §1.5: every row; all can fail
CONTROLS = [
    ("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
    (f"res:0x{SLOT1:x}", f"0x{M1:08x}", "E0: entry 0 ran this command (slot 1 marker)"),
    (f"res:0x{SLOT1 + 1:x}", "@runid", "E0: entry 0 ran this command (slot 1 run id)"),
    ("res:0x1", "0x0", "E0: cmd 0 (entry 0 cleared it)"),
    ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
    ("snap9:0x0c08", "0x0", "B: no BIF fault after the job (a fault is its own outcome)"),
]


def snap_v():
    """TA3DCtl dwords 0-3 of the pinned snap0 (`ta3dctl 0xOO 0xVVVVVVVV` lines)."""
    t = pins.blob(SNAP_PIN).decode()
    v = {int(m.group(1), 16) // 4: int(m.group(2), 16)
         for m in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$", t, re.M)}
    return [v[i] for i in range(4)]


def source_facts():
    """What emitsb.s stores where, read at the frozen commit: the res patches (byte offsets), the
    markers in order, the attribute reads, the emit count and the two breadcrumbs' places."""
    s = pins.blob("resgx545:" + SOURCE).decode()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip() and not ln.startswith(";")]
    emit = next(i for i, ln in enumerate(lines) if ln.startswith("emitpds"))
    e1 = lines.index("@entry 1")
    return dict(patches=[int(x) for x in re.findall(r"@patch res\+(\d+)", s)],
                marks=[int(x, 16) for x in re.findall(r"mov r7, #(0x5a5a33[0-9a-f]{2})", s)],
                pa=re.findall(r"mov r[4-7], (pa[0-3])", s),
                sa=re.findall(r"mov r[4-7], (sa[0-3])", s),
                emit=sum(1 for ln in lines if ln.startswith("emitpds")),
                after_emit=lines[emit + 1:emit + 5],
                entry1=[ln for ln in lines[e1 + 1:] if not ln.endswith(":")][:5])


def own_job():
    return ('{"cmd": 1, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true}'
            % (FILL_AT, ", ".join([str(FILL)] * FILL_N), TIMEOUT_MS))


def tables():
    own = ["#stage own",
           "#limit 0",
           f"# own: N3b step {STEP} (closing29/n3b/design.md), the task emitsb armed once",
           f"# ({ARM}); one command 1 with ticks, the fill 0xdeadc0de in slots 2-5 first. One",
           "# row by design: no planned fault or hang, and any stop ends the session (rc 4);",
           "# run/hooks.sh stops it (rc 24, on_stop end) after an ok end whose markers, run id,",
           "# cmd, state or sa0-sa3 are wrong."]
    for n, st in ROWS:
        own.append(f"{n}|{st}|flagged|-|owntask|{own_job()}")
    post = ["#stage post",
            "#limit 0",
            "# post: the stock firmware (own_arm off since own's disarm) draws the health pair's",
            "# triangle and fill exactly.",
            "p1-tri|control|safe|reads:diff|t30|tri",
            "p2-fill|control|safe|reads:diff|t30|fill"]
    return "\n".join(own) + "\n", "\n".join(post) + "\n"


def predictions():
    own = [HEAD]
    for n, st in ROWS:
        for model, qs in OUTCOMES[STEP].items():
            for q, v in qs.items():
                own.append(f"{n}\t{q}\t{v}\t{model}\t{st}\t{DESIGN}: {WHAT[model]}\n")
        for q, v, why in CONTROLS:
            own.append(f"{n}\t{q}\t{v}\tCTL\t{st}\tn3b design §1.5 {why}\n")
    post = [HEAD,
            "p1-tri\tdiff\t0\tCTL\tcontrol\tthe kit's health triangle (E1134's health pair)\n",
            "p2-fill\tdiff\t0\tCTL\tcontrol\tthe kit's health fill (E1134's health pair)\n"]
    return "".join(own), "".join(post)


def constants():
    v = snap_v()
    out = [f"STEP {STEP}", f"ARM {ARM}", f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}",
           f"S1 0x{S1:08x}", f"T3 0x{T3:08x}"] + [f"V{i} 0x{x:08x}" for i, x in enumerate(v)]
    return "\n".join(out) + "\n"


def build():
    to, tp = tables()
    po, pp = predictions()
    return {"tables/own.txt": to, "tables/post.txt": tp, "predictions/own.tsv": po,
            "predictions/post.tsv": pp, "gen/constants.txt": constants()}


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
