#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r36-n3's generator (closing29/kernel33/design.md §3: N3, the one own-task `emitpds`
form; rank-round34.md's N3 row, Q128). Writes tables/own.txt, tables/post.txt,
predictions/own.tsv, predictions/post.tsv and gen/constants.txt; every input is read at the
commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stage own (flagged, the task `emitsa` armed once on slot 0, entry 0): every row is one tester
command 1. Entry 0 stores marker M1 and the run id in result slot 1, clears cmd, then the one
`emitpds` of the kernel's image (douta V0 to attribute 0, douta V2 to attribute 2, doutu entry 1);
entry 1 stores pa0-pa3 in slot 2, sa0-sa3 in slot 3, marker M4 and the run id in slot 4, then
state 2 (done). V0 and V2 are TA3DCtl dwords 0 and 2 as the loader built them: what sa0 and sa2
already hold (E002), so the same-value variant changes no attribute the firmware reads. The rows
differ only in the fill the host writes into slots 2-4 before the command (params dwords 72-83:
A or B), so a slot the task did not store shows the fill. e1, e2: exploration (fit); h1-h8: held
out. Stage post: the stock firmware's triangle and fill (the health pair's argv) after the
disarm.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SOURCE = "asm/fwtask/emitsa.s"
M1 = 0x5A5A3301           # entry 0's marker (slot 1)
M4 = 0x5A5A3302           # entry 1's marker (slot 4)
SLOT1, SLOT_PA, SLOT_SA, SLOT4 = 0x44, 0x48, 0x4C, 0x50
FILL = {"a": 0xDEADC0DE, "b": 0x0BADF00D}
FILL_AT, FILL_N = SLOT_PA, 12          # slots 2, 3 and 4 (dwords 0x48-0x53)
TIMEOUT_MS = 200
# the hooks' fallback for V0-V3 (a snap0 without ta3dctl lines: the kit mock's fake regs only):
# TA3DCtl dwords 0-3 in a kept snap0 of r35-sa (E1144), module 7CE8E38E
SNAP_PIN = "data:render/closing-r35-sa/out/20261118-085610/a/c0a-k.snap0.regs.gz"
ROWS = [("e1-a", "fit"), ("e2-b", "fit")] + [(f"h{i}-{'ab'[(i - 1) % 2]}", "heldout")
                                             for i in range(1, 9)]


def snap_v():
    """TA3DCtl dwords 0-3 of the pinned snap0 (`ta3dctl 0xOO 0xVVVVVVVV` lines)."""
    t = pins.blob(SNAP_PIN).decode()
    v = {int(m.group(1), 16) // 4: int(m.group(2), 16)
         for m in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$", t, re.M)}
    return [v[i] for i in range(4)]


def source_facts():
    """What emitsa.s stores where (byte offsets of the results page), read at the frozen commit:
    {marker1, marker4, slot1, slot_pa, slot_sa, slot4} as dword indices."""
    s = pins.blob("resgx545:" + SOURCE).decode()
    patches = [int(x) for x in re.findall(r"@patch res\+(\d+)", s)]
    marks = [int(x, 16) for x in re.findall(r"mov r7, #(0x5a5a33[0-9a-f]{2})", s)]
    return dict(patches=patches, marks=marks,
                pa=re.findall(r"mov r[4-7], (pa[0-3])", s),
                sa=re.findall(r"mov r[4-7], (sa[0-3])", s),
                emit=s.count("emitpds"))


def own_job(fill):
    return ('{"cmd": 1, "params": {"%d": [%s]}, "timeout_ms": %d}'
            % (FILL_AT, ", ".join([str(fill)] * FILL_N), TIMEOUT_MS))


def tables():
    own = ["#stage own",
           "#limit 0",
           "# own: N3 (kernel33 design §3), the task emitsa armed once (slots=0x1 entry=0); one",
           "# command 1 a job, the fill A or B in slots 2-4 first. No planned fault or hang: any",
           "# fault, hang or runner stop ends the session; run/hooks.sh stops it (rc 24, on_stop",
           "# end) when entry 0's or entry 1's marker or run id is wrong, cmd was not cleared, or",
           "# sa0-sa3 are not TA3DCtl dwords 0-3 (the firmware's attributes changed)."]
    for n, st in ROWS:
        own.append(f"{n}|{st}|flagged|-|owntask|{own_job(FILL[n[-1]])}")
    post = ["#stage post",
            "#limit 0",
            "# post: the stock firmware (own_arm off since own's disarm) draws the health pair's",
            "# triangle and fill exactly.",
            "p1-tri|control|safe|reads:diff|t30|tri",
            "p2-fill|control|safe|reads:diff|t30|fill"]
    return "\n".join(own) + "\n", "\n".join(post) + "\n"


def predictions():
    src_ctl = "kernel33 design §3 (emitsa.s protocol)"
    src_sa = "E002 (PDS #11 loads TA3DCtl into sa), kernel33 design §1"
    src_pa = "kernel33 design §3: douta to attributes 0, 2 (E146: the event path lands in pa)"
    own = [HEAD]
    for n, st in ROWS:
        rows = [
            (f"res:0x{SLOT_PA:x}", "@V0", "H-PA", src_pa),
            (f"res:0x{SLOT_PA + 2:x}", "@V2", "H-PA", src_pa),
            (f"res:0x{SLOT_PA:x}", "!@V0", "H-SA", src_pa),
            (f"res:0x{SLOT_PA + 2:x}", "!@V2", "H-SA", src_pa),
            (f"res:0x{SLOT4:x}", f"!0x{M4:08x}", "H-NONE", "kernel33 design §3 (U1 = 0 [infer])"),
            ("res:0x1", "0x0", "CTL", src_ctl),
            ("res:0x2", "0x2", "CTL", src_ctl),
            ("res:0x5", "@runid", "CTL", src_ctl),
            (f"res:0x{SLOT1:x}", f"0x{M1:08x}", "CTL", src_ctl),
            (f"res:0x{SLOT1 + 1:x}", "@runid", "CTL", src_ctl),
            (f"res:0x{SLOT4:x}", f"0x{M4:08x}", "CTL", src_ctl),
            (f"res:0x{SLOT4 + 1:x}", "@runid", "CTL", src_ctl),
            (f"res:0x{SLOT_PA + 1:x}", "!@V0,@V2", "CTL", "no douta writes pa1"),
            (f"res:0x{SLOT_PA + 3:x}", "!@V0,@V2", "CTL", "no douta writes pa3"),
        ] + [(f"res:0x{SLOT_SA + i:x}", f"@V{i}", "CTL", src_sa) for i in range(4)]
        own += [f"{n}\t{q}\t{v}\t{m}\t{st}\t{s}\n" for q, v, m, s in rows]
    post = [HEAD,
            "p1-tri\tdiff\t0\tCTL\tcontrol\tthe kit's health triangle (E1134's health pair)\n",
            "p2-fill\tdiff\t0\tCTL\tcontrol\tthe kit's health fill (E1134's health pair)\n"]
    return "".join(own), "".join(post)


def constants():
    v = snap_v()
    out = [f"M1 0x{M1:08x}", f"M4 0x{M4:08x}"] + [f"V{i} 0x{x:08x}" for i, x in enumerate(v)]
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
