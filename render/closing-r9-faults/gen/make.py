#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r9-faults's tables and predictions from one spec. Two plans, one session:

- Q108 (stages xf2, tri2): closing9/seeds/exp-seeds-r9.md section 2, S9-k2, decision S-6 (a)
  (DECISIONS-R9.md, the seeds plan's R9-6): r8-k2's generator (closing8/r8-k2/gen/make.py)
  extended. xf2 = E946's 9 rows token for token, then 3 new; tri2 = 7 rows.
- Q076 (stage bif): closing9/rank/rank-round9.md R9c-G, decision X-4 (a) (the ranking's R9-4):
  debugfs alias_skip on `tri -n 2 --keep-going` on a new VM (E457's form, E745's wait).

  python3 gen/make.py          write tables/{xf2,tri2,bif}.txt and predictions/{xf2,tri2,bif}.tsv
  python3 gen/make.py --check  exit 1 when a written file is not what the spec gives

Q108 outcomes (score.py): exact (job ok, diff 0, the stage's knob-free hash), diff (job ok,
pixels differ), fault (a kernel `BIF fault S at A` line with A's page inside the flagged
mapping), fault@PAGE (the same, naming the page of the first such line: the WO page and
flags-together hypotheses); readings matching no hypothesis: fault-elsewhere, hang.
Q076 outcomes: exact (every render drawn as the mask-free control, diff 0 and its hashes),
needed (a fault whose page lies in a buffer the mask leaves out), and the readings
fault-elsewhere and hang."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import scorekit as SK  # noqa: E402

PTE_ADDR, PTE_FLAGS, SKIP, PBP = "vm_pte_addr", "vm_pte_flags", "alias_skip", "render_pb_pages"
WO, CACHED, EDMPROT, RO = 0x2, 0x8, 0x10, 0x4
PAGE = 0x1000

# ---- Q108: the mappings a knob row aims at --------------------------------------------------
# (first page, bytes, the tool's own READONLY, the access the job makes of it, the page of the
# last pixel written or None). The tool's own allocation order (README "Addresses"; the library
# mock's --emit-scene, --print-addrs and `layout: fb` / `depth` lines, tests/test_twin.py):
# fill 64 x 32 stride 256: 2 pages + a guard; fill 64 x 16 at y 16: the same 3 pages (y + h
# rows), only the second written; fill 64 x 64: 4 + 1; copy's read-only source 2 + 1; tri 64 x 64
# colour target 4 + 1; tri --depth --depth-store: the depth buffer 0x3e001000 and the store
# 0x3e015000, 20 pages each (64 x 64 dwords + 16 pages), the colour target after them.
MAPS = {
    "fill-dst": (0x3E001000, 0x3000, False, "write", 0x3E002000),
    "fill-dst-low": (0x3E001000, 0x3000, False, "write", 0x3E002000),
    "fill-dst-64": (0x3E001000, 0x5000, False, "write", 0x3E004000),
    "copy-src": (0x3E001000, 0x3000, True, "read", None),
    "tri-fb": (0x3E001000, 0x5000, False, "write", 0x3E004000),
    # the depth store's buffer: the ZLS store writes it (rd:13 points at it)
    "zst": (0x3E015000, 0x14000, False, "write", None),
    # the depth buffer: rd:12 (the load base) points at it; the clearing control 0x0017100c has
    # bit 1 (the load) clear (doc/specs/3d.md section 11.5, E467) and the store goes to zst, so
    # no requestor is known to touch it [infer]: a reading row
    "zbuf": (0x3E001000, 0x14000, False, "none", None),
}
ARGS = {
    "fill": "fill", "copy": "copy --print-addrs", "tri": "tri", "isolation": "isolation",
    "fill-low": "fill --width 64 --height 16 --y 16", "fill-64": "fill --width 64 --height 64",
    "tri-depth": "tri --depth --depth-store",
}

SRC_FILL = "data:render/closing-r7-rp/out/20261112-205431/p7-rd/begin.fill1.txt.gz"
SRC_TRI = "data:render/closing-r7-rp/out/20261112-205431/p7-rd/begin.health1.txt.gz"
SRC_COPY = "data:texture/copy-addresses/output.txt"
SRC_RO = "data:render/client-jobs/output.txt"
SRC_DEPTH = ("tests/test_twin.py: the library mock of the tool's source (fb after the two depth "
             "buffers); doc/specs/3d.md section 11.6 (E465): 0x0017100c stores (th - 1)(G + 1) + "
             "tw = 8 tiles of 512 dwords at 64 x 64, G = 1")
CTL = {
    "fill": {"job": ("ok", SRC_FILL), "hash": ("0xb60c6095080bd325", SRC_FILL)},
    "copy": {"job": ("ok", SRC_COPY), "hash": ("0x9b1c0be484ac0d25", SRC_COPY),
             "src": ("0x3e001000", SRC_COPY + " (0x3e002000 behind --page-before's page)")},
    "tri": {"job": ("ok", SRC_TRI), "hash": ("0x99385a04ee01c585", SRC_TRI),
            "fb": ("0x3e001000", SRC_TRI)},
    "isolation": {"ro": ("PASS", SRC_RO), "rostat": ("0x80020", SRC_RO),
                  "ropage": ("0x3e200000", SRC_RO)},
    "tri-depth": {"job": ("ok", SRC_DEPTH), "fb": ("0x3e029000", SRC_DEPTH),
                  "dstore": ("4096", SRC_DEPTH)},
}
SRC_Q = "Q108; doc/specs/hw_spec.md section 4 (the GPL CE DDK's sgxmmu.h names)"


def last_page(mp):
    return MAPS[mp][0] + MAPS[mp][1] - PAGE


# the hypotheses of each group: (the knob's flags, the access, the mapping) -> outcome
HYPS = {
    "WRITEONLY": {
        "H-WO": lambda acc, mp: "fault" if acc == "read" else "exact",
        "H-WO-NONE": lambda acc, mp: "exact",
        "H-WO-ALL": lambda acc, mp: "fault",
    },
    "WO-PAGE": {
        "H-LASTROW": lambda acc, mp: f"fault@0x{MAPS[mp][4]:08x}",
        "H-MAPEND": lambda acc, mp: f"fault@0x{last_page(mp):08x}",
        "H-FIRST": lambda acc, mp: f"fault@0x{MAPS[mp][0]:08x}",
    },
    "CACHECONSISTENT": {
        "H-CC-NEW": lambda acc, mp: "exact",
        "H-CC-STALE": lambda acc, mp: "diff",
    },
    "EDMPROTECT": {
        "H-EDM-NONE": lambda acc, mp: "exact",
        "H-EDM-CLIENT": lambda acc, mp: "fault",
    },
    "EDM-XF": {
        "H-EDM-WRITE": lambda acc, mp: "fault" if acc == "write" else "exact",
        "H-EDM-REQ": lambda acc, mp: "fault" if acc in ("read", "write") else "exact",
    },
    "EDM-3D": {
        "H-EDM-WRITE": lambda acc, mp: "fault" if acc == "write" else "exact",
        "H-EDM-3D": lambda acc, mp: "fault" if mp == "tri-fb" else "exact",
    },
    "WO+EDM": {
        "H-OR": lambda acc, mp: "fault",
        "H-CANCEL": lambda acc, mp: "exact",
    },
    "WO+EDM-PAGE": {
        "H-EDM-FIRST": lambda acc, mp: f"fault@0x{MAPS[mp][0]:08x}",
        "H-WO-FIRST": lambda acc, mp: f"fault@0x{MAPS[mp][4]:08x}",
    },
}
WHY = {
    "H-WO": "WRITEONLY stops a read of the page (a fault naming it, like E021's READONLY write) "
            "and lets a write through (plan K2, frozen)",
    "H-WO-NONE": "WRITEONLY does nothing to a client's reads or writes (rival)",
    "H-WO-ALL": "WRITEONLY faults every access (rival)",
    "H-LASTROW": "a WRITEONLY write faults at the page of the last pixel written (E946 post hoc: "
                 "xf-wo-fill at 0x3e002000; E945 tri-wo-fb at 0x3e004000) (S9-k2, frozen)",
    "H-MAPEND": "a WRITEONLY write faults at the flagged mapping's last page (rival)",
    "H-FIRST": "a WRITEONLY write faults at the flagged mapping's first page (rival)",
    "H-CC-NEW": "a unit reads the host's writes made after the map (plan K2, frozen)",
    "H-CC-STALE": "a unit reads stale data (rival)",
    "H-EDM-NONE": "EDMPROTECT has no effect on a client requestor (plan K2, rival)",
    "H-EDM-CLIENT": "EDMPROTECT faults a client requestor (the TA, the 3D, a transfer's pixel "
                    "side) (plan K2, rival)",
    "H-EDM-WRITE": "EDMPROTECT faults every client write and no client read (E945: the colour "
                   "write faulted, the VDM's reads did not) (S9-k2, frozen)",
    "H-EDM-REQ": "EDMPROTECT faults every access of the transfer's requestors, reads too (rival)",
    "H-EDM-3D": "EDMPROTECT faults only the pixel back end's colour write: the ZLS store and load "
                "pass (rival)",
    "H-OR": "WRITEONLY and EDMPROTECT together fault the colour write, as each does alone "
            "(E945) (S9-k2, frozen)",
    "H-CANCEL": "the two flags together let the colour write through (rival)",
    "H-EDM-FIRST": "together, the fault is EDMPROTECT's: at the target's first page, before "
                   "the image is written (E945 tri-edm-fb at 0x3e001001) (rival, not favoured)",
    "H-WO-FIRST": "together, the fault is WRITEONLY's: at the last pixel's page, after the image "
                  "is written (E945 tri-wo-fb at 0x3e0041f1) (rival, not favoured)",
}
# the summaries over held-out rows only: the hypotheses new in S9-k2 (E946's own hypotheses are
# scored over every row they name, repeats included, as r8-k2 froze them)
HELDOUT_ONLY = {"WO-PAGE", "EDM-XF", "EDM-3D", "WO+EDM", "WO+EDM-PAGE"}

# (stage, name, set, risk, command, map, flag, the groups scored, knob words besides dbg:)
KF = "expectfault expectdiff after"
QROWS = [
    # E946's 9 rows, token for token (closing8/r8-k2/tables/xf.txt)
    ("xf2", "xf-c-fill", "control", "safe", "fill", None, None, (), "reads:job,hash"),
    ("xf2", "xf-c-copy", "control", "safe", "copy", None, None, (), "reads:job,hash,src"),
    ("xf2", "xf-c-addr", "control", "medium", "fill", "fill-dst", 0, (), "after reads:job,hash"),
    ("xf2", "xf-c-ro", "control", "medium", "isolation", None, None, (), "expectfault reads:ro,rostat"),
    ("xf2", "xf-wo-fill", "repeat", "medium", "fill", "fill-dst", WO, ("WRITEONLY", "WO-PAGE"), KF),
    ("xf2", "xf-cc-copy", "repeat", "medium", "copy", "copy-src", CACHED, ("CACHECONSISTENT",), KF),
    ("xf2", "xf-edm-fill", "repeat", "medium", "fill", "fill-dst", EDMPROT, ("EDMPROTECT", "EDM-XF"), KF),
    ("xf2", "xf-wo-copy", "repeat", "medium", "copy", "copy-src", WO, ("WRITEONLY",), KF),
    ("xf2", "xf-c-end", "control", "safe", "fill", None, None, (), "after reads:job,hash"),
    # S9-k2's 3 new rows
    ("xf2", "xf-wo-fill-low", "heldout", "medium", "fill-low", "fill-dst-low", WO, ("WRITEONLY", "WO-PAGE"), KF),
    ("xf2", "xf-wo-fill-64", "heldout", "medium", "fill-64", "fill-dst-64", WO, ("WRITEONLY", "WO-PAGE"), KF),
    ("xf2", "xf-edm-copy", "heldout", "medium", "copy", "copy-src", EDMPROT, ("EDM-XF",), KF),
    # tri2: the knob-free depth control right after the plain one (a control before the rows it
    # gates); the plan lists it sixth
    ("tri2", "tri-c", "control", "safe", "tri", None, None, (), "reads:job,hash,fb"),
    ("tri2", "tri-c-depth", "control", "safe", "tri-depth", None, None, (), "after reads:job,fb,dstore"),
    ("tri2", "tri-woedm-fb", "heldout", "medium", "tri", "tri-fb", WO | EDMPROT, ("WO+EDM", "WO+EDM-PAGE"), KF),
    ("tri2", "tri-edm-dst", "heldout", "medium", "tri-depth", "zst", EDMPROT, ("EDM-3D",), KF),
    ("tri2", "tri-edm-dld", "reading", "medium", "tri-depth", "zbuf", EDMPROT, ("EDM-3D",), KF),
    ("tri2", "tri-wo-dst", "heldout", "medium", "tri-depth", "zst", WO, ("WRITEONLY",), KF),
    ("tri2", "tri-c-end", "control", "safe", "tri", None, None, (), "after reads:job,hash,fb"),
]

# ---- Q076: alias_skip ------------------------------------------------------------------------
# the firmware buffers' addresses (debugfs layout, ids 0 to 14; bit 15 names none: E573), each
# buffer up to the next one's address (14: one page) [infer: the layout of B60AB0B4 is the one
# read on 5AD04F33 in 11.33; the kernel lays the buffers out the same way since]
SRC_LAYOUT = "data:bif/alias-skip/dumps/bif-alias-safe/b76-control-1.layout.txt.gz"
BUF = [0x30000000, 0x3000D000, 0x3000E000, 0x3000F000, 0x30010000, 0x30011000, 0x32000000,
       0x32002000, 0x32003000, 0x32004000, 0x32005000, 0x32006000, 0x32007000, 0x3200E000,
       0x3200F000]


def buf_range(i):
    return BUF[i], (BUF[i + 1] if i + 1 < len(BUF) and BUF[i + 1] > BUF[i] else BUF[i] + PAGE)


def buffers(mask):
    return [i for i in range(len(BUF)) if mask >> i & 1]


BIF_ARGS = "tri -n 2 --keep-going --wait-ms 6000"
BIF_3R = "tri -n 3 --keep-going --wait-ms 6000"
BIF_OVF = "tri -n 2 --keep-going --wait-ms 6000 --width 1024 --height 768 --keep-overflow"
SRC_S1 = "data:render/closing-s1/out/p-f/f-12-r1.txt.gz"
SRC_S1B = "data:render/closing-s1b/out/p-f/f-dpm-0.txt.gz"
SRC_E457 = "data:bif/render-directories/kernel.log"
SRC_C1 = "data:render/closing-s1/out/p-f/f-ctl0-r1.dmesg.gz"
BCTL = {
    "plain": {"job": ("ok", SRC_TRI), "renders": ("2ok", SRC_S1),
              "hash": ("0x99385a04ee01c585", SRC_TRI),
              "hash2": ("0xab267bd98022a81d", SRC_S1 + " (E745: mask 0x6 exact as without a mask)")},
    "ovf": {"job": ("overflowed", SRC_S1B), "renders": ("0of2ovf2", SRC_S1B),
            "hash": ("0xc9e301d225fe2325", SRC_S1B), "hash2": ("0xed1bce7108aded25", SRC_S1B)},
    "ta3d": {"fstat": ("0x90400", SRC_E457), "fpage": ("0x32004000", SRC_E457)},
    "buf0": {"fstat": ("0x91000", SRC_C1), "fpage": ("0x3000b000", SRC_C1 + " (E573: 0x3000b022)")},
}
BWHY = {
    "H-ONLY09": "a buffer is needed in the client directory only if leaving it out alone faults: "
                "of 0 to 14 only 0 and 9 (E457, E573, E745, E761: HI), so any mask without them "
                "renders exactly (frozen)",
    "H-SET": "a set of buffers each unneeded alone is needed together: the mask's fault lies in "
             "a buffer it leaves out (HJ, rival)",
}
# (name, set, mask, args, the control whose hashes an exact row matches, knob words besides dbg:)
BROWS = [
    ("bif-c0", "control", 0x0, BIF_ARGS, "plain", "after reads:job,renders,hash,hash2"),
    ("bif-c9", "control", 0x200, BIF_ARGS, "ta3d", "expectfault reads:fstat,fpage"),
    ("bif-1213", "heldout", 0x3000, BIF_ARGS, "plain", "expectfault after"),
    ("bif-1214", "heldout", 0x5000, BIF_ARGS, "plain", "expectfault after"),
    ("bif-1314", "heldout", 0x6000, BIF_ARGS, "plain", "expectfault after"),
    ("bif-12to14", "heldout", 0x7000, BIF_ARGS, "plain", "expectfault after"),
    ("bif-h32", "heldout", 0x7DC0, BIF_ARGS, "plain", "expectfault after"),
    ("bif-most", "heldout", 0x7DFE, BIF_ARGS, "plain", "expectfault after"),
    ("bif-most-r2", "replicate", 0x7DFE, BIF_ARGS, "plain", "expectfault after"),
    ("bif-most-3r", "heldout", 0x7DFE, BIF_3R, "plain", "expectfault after"),
    ("bif-c-ovf", "control", 0x0, BIF_OVF, "ovf", "after reads:job,renders,hash,hash2"),
    ("bif-most-ovf", "heldout", 0x7DFE, BIF_OVF, "ovf", "expectfault after"),
    ("bif-c1", "control", 0x1, BIF_ARGS, "buf0", "expectfault reads:fstat,fpage"),
    ("bif-c0-end", "control", 0x0, BIF_ARGS, "plain", "after reads:job,renders,hash,hash2"),
]

# #limit: the expectfault rows that are not controls, plus one (S-6 (a); a control's own fault
# is not counted by the kit, f32dfac's tools/closing/test_kit.py checks it)
STAGES = ("xf2", "tri2", "bif")


def expectfault_rows(stage):
    if stage == "bif":
        return [r[0] for r in BROWS if r[1] != "control" and "expectfault" in r[5].split()]
    return [r[1] for r in QROWS if r[0] == stage and r[2] != "control" and "expectfault" in r[8].split()]


LIMIT = {s: len(expectfault_rows(s)) + 1 for s in STAGES}
HEAD = {
    "xf2": [
        "# xf2 (Q108, the transfer's requestors): E946's nine rows token for token (the knob-free",
        "# fill and copy, the address alone, isolation's READONLY fault: a control, not counted in",
        "# #limit), WO, CACHED, EDMPROT on a fill's destination and a copy's source, the fill",
        "# again), then WO on a fill that writes only the second page (y 16) and on a 64 x 64 fill",
        "# (the WO fault's page: last row, mapping end or first page), and EDMPROT on the copy's",
        "# read-only source (PTE 0x14: EDMPROTECT on a transfer read).",
    ],
    "tri2": [
        "# tri2 (Q108, the 3D's requestors): the knob-free 64 x 64 triangle and the same with a",
        "# depth buffer and a depth store (fb after them), WO|EDMPROT together (0x12) on the",
        "# colour target, EDMPROT on the ZLS store's buffer (a write) and on the depth buffer (no",
        "# load at control 0x0017100c: a reading), WO on the ZLS store's buffer, the triangle again.",
    ],
    "bif": [
        "# bif (Q076, the client directory's alias of the firmware buffers): alias_skip leaves",
        "# buffers out of a new render VM's alias (E457's form). Controls: no mask (twice), TA3DCtl",
        "# left out (E457's fault 0x90400 at 0x32004000), buffer 0 left out (E745's 0x91000 at",
        "# 0x3000b000), the overflowing 1024 x 768 scene without a mask (E761). Held out: the",
        "# pairs and the three of 12 to 14, the 0x32 heap without TA3DCtl, every buffer but 0 and",
        "# 9 (two runs, three renders, and with both renders overflowing at render_pb_pages 0x23).",
    ],
}


# ---- the tables ------------------------------------------------------------------------------
def qknobs(r):
    stage, name, sset, risk, cmd, mp, flag, groups, extra = r
    words = []
    if mp is not None:
        words += [f"dbg:{PTE_ADDR}=0x{MAPS[mp][0]:08x}", f"dbg:{PTE_FLAGS}=" + (f"0x{flag:x}" if flag else "0")]
    return " ".join(words + extra.split())


def bknobs(r):
    name, sset, mask, args, ctl, extra = r
    words = [f"dbg:{SKIP}=0x{mask:x}" if mask else f"dbg:{SKIP}=0"]
    if args == BIF_OVF:
        words.append(f"dbg:{PBP}=0x23")
    return " ".join(words + extra.split())


def pte(mp, flag):
    return (RO if MAPS[mp][2] else 0) | flag


def table(stage):
    out = [f"#stage {stage}", f"#limit {LIMIT[stage]}"] + HEAD[stage]
    if stage == "bif":
        for r in BROWS:
            out.append("|".join([r[0], r[1], "medium", bknobs(r), "t4", r[3]]))
    else:
        for r in QROWS:
            if r[0] == stage:
                out.append("|".join([r[1], r[2], r[3], qknobs(r), "t4", ARGS[r[4]]]))
    return "\n".join(out) + "\n"


def predictions(stage):
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    if stage == "bif":
        for name, sset, mask, args, ctl, _ in BROWS:
            if sset == "control":
                for q, (v, src) in BCTL[ctl].items():
                    out.append(f"{name}\t{q}\t{v}\tH-CTL\tcontrol\t{src}")
                continue
            left = ",".join(str(i) for i in buffers(mask))
            out.append(f"{name}\tmask\t0x{mask:x}\tKNOB\t{sset}\tthe buffers left out: {left} ({SRC_LAYOUT})")
            out.append(f"{name}\tcontrol\tbif-c-ovf\tKNOB\t{sset}\tthe control whose hashes an exact row matches"
                       if ctl == "ovf" else
                       f"{name}\tcontrol\tbif-c0\tKNOB\t{sset}\tthe control whose hashes an exact row matches")
            out.append(f"{name}\toutcome\texact\tH-ONLY09\t{sset}\tQ076: {BWHY['H-ONLY09']}")
            out.append(f"{name}\toutcome\tneeded\tH-SET\t{sset}\tQ076: {BWHY['H-SET']}")
        return "\n".join(out) + "\n"
    for r in QROWS:
        if r[0] != stage:
            continue
        _, name, sset, _, cmd, mp, flag, groups, _ = r
        if sset == "control":
            for q, (v, src) in CTL[cmd].items():
                out.append(f"{name}\t{q}\t{v}\tH-CTL\tcontrol\t{src}")
            continue
        a, size, ro, acc, _ = MAPS[mp]
        out.append(f"{name}\tmap\t0x{a:08x}+0x{size:x}\tKNOB\t{sset}\tthe tool's allocation order (README)")
        out.append(f"{name}\tpte\t0x{pte(mp, flag):x}\tKNOB\t{sset}\tthe fork's sgxfive_vm_pte_flags (RO the tool's own)")
        out.append(f"{name}\taccess\t{acc}\tKNOB\t{sset}\tthe tool's source (cmd_fill, cmd_copy, render.c, depth_arm)")
        for g in groups:
            q = "outcome" if not g.endswith("PAGE") else "page"
            for h, f in HYPS[g].items():
                out.append(f"{name}\t{q}:{g}\t{f(acc, mp)}\t{h}\t{sset}\t{SRC_Q}: {WHY[h]}")
    return "\n".join(out) + "\n"


def producible(cmd_args):
    """The reading keys a row's job can produce (score.py's producible uses this)."""
    a = cmd_args.split()
    if a[:1] == ["isolation"]:
        return {"ro", "rostat"}
    keys = {"job", "hash"}
    if a[:1] == ["copy"] and "--print-addrs" in a:
        keys.add("src")
    if a[:1] == ["tri"]:
        keys |= {"fb", "renders", "fstat", "fpage"}
        if "-n" in a and int(a[a.index("-n") + 1]) > 1:
            keys.add("hash2")
        if "--depth-store" in a:
            keys.add("dstore")
    return keys


def files():
    out = {}
    for s in STAGES:
        out[f"tables/{s}.txt"] = table(s)
        out[f"predictions/{s}.tsv"] = predictions(s)
    return out


def check_controls():
    ctl = {}
    for r in QROWS:
        if r[2] == "control":
            reads = tuple(next(w for w in r[8].split() if w.startswith("reads:"))[6:].split(","))
            ctl[r[1]] = (reads, {"args": ARGS[r[4]]})
    for r in BROWS:
        if r[1] == "control":
            reads = tuple(next(w for w in r[5].split() if w.startswith("reads:"))[6:].split(","))
            ctl[r[0]] = (reads, {"args": r[3]})
    SK.refuse_unreadable(ctl, lambda row: producible(row["args"]))


def main(argv):
    check_controls()
    bad = 0
    for rel, text in files().items():
        p = os.path.join(KP, rel)
        if "--check" in argv:
            have = open(p).read() if os.path.exists(p) else None
            if have != text:
                print(f"{rel} is not current (python3 gen/make.py)")
                bad = 1
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(text)
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
