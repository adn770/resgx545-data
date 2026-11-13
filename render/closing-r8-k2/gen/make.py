#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r8-k2's tables and predictions from one spec (the plan's K2 rows,
closing8/rank/rank-round8.md section 3; decisions R8-5 and R8-6).

  python3 gen/make.py          write tables/{xf,tri}.txt and predictions/{xf,tri}.tsv
  python3 gen/make.py --check  exit 1 when a written file is not what the spec gives

Every knob row sets vm_pte_addr to the first page of ONE mapping the tool makes (MAPS: the
tool's own allocation order, README "Addresses") and vm_pte_flags to one flag; the kernel then
logs `vm_map ADDR +SIZE: PTE flags F`, the row's premise (score.py: without it, cannot tell).
Outcomes (score.py classifies each kept row as one of them):
  exact   job: ok, diff 0, the hash of the stage's knob-free control
  diff    job: ok, pixels differ from the CPU reference
  fault   job faulted, and a kernel `BIF fault ... at A` line with A's page inside the mapping
(readings only: fault-elsewhere, hang, rejected, other)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import scorekit as SK  # noqa: E402

PTE_ADDR, PTE_FLAGS = "vm_pte_addr", "vm_pte_flags"
WO, CACHED, EDMPROT, RO = 0x2, 0x8, 0x10, 0x4

# the mappings a knob row aims at: (first page, bytes, the tool's own READONLY, the access the
# job makes of it). fill 64 x 32 stride 256 and copy 64 x 32: pages_for() = 2 + a guard page;
# tri 64 x 64: 4 + 1; the render's GENERAL page holds its VDM stream, indices and vertices.
MAPS = {
    "fill-dst": (0x3E001000, 0x3000, False, "write"),
    "copy-src": (0x3E001000, 0x3000, True, "read"),
    "tri-fb": (0x3E001000, 0x5000, False, "write"),
    "tri-gen": (0x3E000000, 0x1000, False, "read"),
}
ARGS = {"fill": "fill", "copy": "copy --print-addrs", "tri": "tri", "isolation": "isolation"}

SRC_FILL = "data:render/closing-r7-rp/out/20261112-205431/p7-rd/begin.fill1.txt.gz"
SRC_TRI = "data:render/closing-r7-rp/out/20261112-205431/p7-rd/begin.health1.txt.gz"
SRC_COPY = "data:texture/copy-addresses/output.txt"
SRC_RO = "data:render/client-jobs/output.txt"
CTL = {
    "fill": {"job": ("ok", SRC_FILL), "hash": ("0xb60c6095080bd325", SRC_FILL)},
    "copy": {"job": ("ok", SRC_COPY), "hash": ("0x9b1c0be484ac0d25", SRC_COPY),
             "src": ("0x3e001000", SRC_COPY + " (0x3e002000 behind --page-before's page)")},
    "tri": {"job": ("ok", SRC_TRI), "hash": ("0x99385a04ee01c585", SRC_TRI),
            "fb": ("0x3e001000", SRC_TRI)},
    "isolation": {"ro": ("PASS", SRC_RO), "rostat": ("0x80020", SRC_RO),
                  "ropage": ("0x3e200000", SRC_RO)},
}
SRC_Q = "Q108; doc/specs/hw_spec.md section 4 (the GPL CE DDK's sgxmmu.h names)"
# the hypotheses, each a function of (flag, the job's access of the mapping) -> outcome
HYPS = {
    WO: {
        "H-WO": lambda acc: "fault" if acc == "read" else "exact",
        "H-WO-NONE": lambda acc: "exact",
        "H-WO-ALL": lambda acc: "fault",
    },
    CACHED: {
        "H-CC-NEW": lambda acc: "exact",
        "H-CC-STALE": lambda acc: "diff",
    },
    EDMPROT: {
        "H-EDM-NONE": lambda acc: "exact",
        "H-EDM-CLIENT": lambda acc: "fault",
    },
}
WHY = {
    "H-WO": "WRITEONLY stops a read of the page (a fault naming it, like E021's READONLY write) "
            "and lets a write through (plan K2, frozen)",
    "H-WO-NONE": "WRITEONLY does nothing to a client's reads or writes (rival)",
    "H-WO-ALL": "WRITEONLY faults every access (rival)",
    "H-CC-NEW": "a unit reads the host's writes made after the map (plan K2, frozen)",
    "H-CC-STALE": "a unit reads stale data (rival)",
    "H-EDM-NONE": "EDMPROTECT has no effect on a client requestor (plan K2, rival)",
    "H-EDM-CLIENT": "EDMPROTECT faults a client requestor (the TA, the 3D, a transfer's pixel "
                    "side) (plan K2, rival)",
}

# (stage, name, set, risk, command, map, flag, knob words besides the dbg: ones)
ROWS = [
    ("xf", "xf-c-fill", "control", "safe", "fill", None, None, "reads:job,hash"),
    ("xf", "xf-c-copy", "control", "safe", "copy", None, None, "reads:job,hash,src"),
    ("xf", "xf-c-addr", "control", "medium", "fill", "fill-dst", 0, "after reads:job,hash"),
    ("xf", "xf-c-ro", "control", "medium", "isolation", None, None, "expectfault reads:ro,rostat"),
    ("xf", "xf-wo-fill", "heldout", "medium", "fill", "fill-dst", WO, "expectfault expectdiff after"),
    ("xf", "xf-cc-copy", "heldout", "medium", "copy", "copy-src", CACHED, "expectfault expectdiff after"),
    ("xf", "xf-edm-fill", "heldout", "medium", "fill", "fill-dst", EDMPROT, "expectfault expectdiff after"),
    ("xf", "xf-wo-copy", "heldout", "medium", "copy", "copy-src", WO, "expectfault expectdiff after"),
    ("xf", "xf-c-end", "control", "safe", "fill", None, None, "after reads:job,hash"),
    ("tri", "tri-c", "control", "safe", "tri", None, None, "reads:job,hash,fb"),
    ("tri", "tri-wo-fb", "heldout", "medium", "tri", "tri-fb", WO, "expectfault expectdiff after"),
    ("tri", "tri-cc-gen", "heldout", "medium", "tri", "tri-gen", CACHED, "expectfault expectdiff after"),
    ("tri", "tri-edm-fb", "heldout", "medium", "tri", "tri-fb", EDMPROT, "expectfault expectdiff after"),
    ("tri", "tri-edm-gen", "heldout", "medium", "tri", "tri-gen", EDMPROT, "expectfault expectdiff after"),
    ("tri", "tri-wo-gen", "heldout", "medium", "tri", "tri-gen", WO, "expectfault expectdiff after"),
    ("tri", "tri-c-end", "control", "safe", "tri", None, None, "after reads:job,hash,fb"),
]
# a stage stops (rc 24) at its 4th fault or hang with rows left: the rivals allow 3 a stage
# (xf: the RO control, EDMPROT's fill, RO|WO's copy; tri: EDMPROT twice, WO's read), the plan's
# budget of 6
LIMIT = {"xf": 4, "tri": 4}
HEAD = {
    "xf": [
        "# xf (Q108, the transfer's requestors): the knob-free fill and copy (hashes as r7-rp's",
        "# health fill and copy-addresses), the address alone (flags 0: nothing logged, nothing",
        "# changes), isolation's READONLY write fault (E021 redone by the tool, 0x80020 at page",
        "# 0x3e200000 in render/client-jobs), then WO on a fill's destination (a write), CACHED on a",
        "# copy's read-only source, EDMPROT on a fill's destination, WO on the copy's source (RO|WO",
        "# 0x6, decision R8-6: a reading row), and the knob-free fill again.",
    ],
    "tri": [
        "# tri (Q108, the TA's and the 3D's requestors): the knob-free 64 x 64 triangle (hash and",
        "# fb as r7-rp's health triangle), WO on its colour target (a write), CACHED on its GENERAL",
        "# page (VDM stream, indices, vertices: reads), EDMPROT on the colour target and on the",
        "# GENERAL page, WO on the GENERAL page (a read), and the knob-free triangle again.",
    ],
}


def knobs(r):
    stage, name, sset, risk, cmd, mp, flag, extra = r
    words = []
    if mp is not None:
        words += [f"dbg:{PTE_ADDR}=0x{MAPS[mp][0]:08x}", f"dbg:{PTE_FLAGS}=" + (f"0x{flag:x}" if flag else "0")]
    return " ".join(words + extra.split())


def pte(mp, flag):
    a, size, ro, acc = MAPS[mp]
    return (RO if ro else 0) | flag


def table(stage):
    out = [f"#stage {stage}", f"#limit {LIMIT[stage]}"] + HEAD[stage]
    for r in ROWS:
        if r[0] == stage:
            out.append("|".join([r[1], r[2], r[3], knobs(r), "t4", ARGS[r[4]]]))
    return "\n".join(out) + "\n"


def predictions(stage):
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for r in ROWS:
        if r[0] != stage:
            continue
        _, name, sset, _, cmd, mp, flag, _ = r
        if sset == "control":
            for q, (v, src) in CTL[cmd].items():
                out.append(f"{name}\t{q}\t{v}\tH-CTL\tcontrol\t{src}")
            continue
        a, size, ro, acc = MAPS[mp]
        out.append(f"{name}\tmap\t0x{a:08x}+0x{size:x}\tKNOB\t{sset}\tthe tool's allocation order (README)")
        out.append(f"{name}\tpte\t0x{pte(mp, flag):x}\tKNOB\t{sset}\tthe fork's sgxfive_vm_pte_flags (RO the tool's own)")
        out.append(f"{name}\taccess\t{acc}\tKNOB\t{sset}\tthe tool's source (cmd_fill, cmd_copy, render.c)")
        for h, f in HYPS[flag].items():
            out.append(f"{name}\toutcome\t{f(acc)}\t{h}\t{sset}\t{SRC_Q}: {WHY[h]}")
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
        keys.add("fb")
    return keys


def files():
    out = {}
    for s in LIMIT:
        out[f"tables/{s}.txt"] = table(s)
        out[f"predictions/{s}.tsv"] = predictions(s)
    return out


def check_controls():
    ctl = {}
    for r in ROWS:
        if r[2] == "control":
            reads = tuple(next(w for w in r[7].split() if w.startswith("reads:"))[6:].split(","))
            ctl[r[1]] = (reads, {"args": ARGS[r[4]]})
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
