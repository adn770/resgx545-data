#!/usr/bin/env python3
"""Offline option checks with the tool's mock and --emit-scene (no laptop): the words a table's options write land where
the table assumes.  The tool is the one S1b stages (TOOL_SRC, default the agent worktree whose libsgxfive has
--index-width).  Prints ok/FAIL lines.  Output files under out/mock/em."""
import sys
sys.dont_write_bytecode = True

import json  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402

S1 = pathlib.Path(__file__).resolve().parent.parent
TOOL = pathlib.Path(os.environ.get("TOOL_SRC", pathlib.Path.home() / "src/resgx545/.claude/worktrees/agent-aed0242cfe8ab4e23")) \
    / "userspace/libsgxfive/build/sgxfive-test"
EM = S1 / "out/mock/em"
(EM / "dump").mkdir(parents=True, exist_ok=True)
ok = True


def emit(name, args):
    f = EM / f"{name}.json"
    a = args.replace("$W", str(EM)).replace("$S", str(S1 / "bins")).replace("--pixels", f"--pixels --emit-scene {f}")
    r = subprocess.run([str(TOOL), "--mock"] + shlex.split(a), capture_output=True, text=True, timeout=120)
    j = json.load(open(f))
    return {m["role"]: [int(x, 16) for x in m["dwords"]] for m in j["memory"]}, r.stdout


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


row = lambda st, nm: next(ln for ln in open(S1 / f"tables/{st}.txt") if ln.startswith(nm + "|")).rstrip("\n").split("|", 6)[6]
# E4w: --index-width 32 writes indices 0..14 as words at gen 0x200 and sets VDM word 2 bit 25; ^=0x02000000 clears it
a, _ = emit("e4w-ctl", row("g-e4w", "ix-c"))
b, out = emit("e4w-25", row("g-e4w", "ix32-25-r1"))
c, _ = emit("e4w-2425", row("g-e4w", "ix32-2425-r1"))
d, _ = emit("e4w-n", row("g-e4w", "ix32-n-r1"))
e, _ = emit("e4w-c25", row("g-e4w", "ix-25"))
check("E4w: ix32-25 index list 0..14 as 32-bit words at gen 0x200", b["gen"][0x80:0x80 + 15] == list(range(15)))
check("E4w: ix32-25 VDM word 2 = ix-c's | bit 25", b["gen"][2] == a["gen"][2] | 0x02000000, hex(b["gen"][2]))
check("E4w: ix32-2425 VDM word 2 = ix-c's | bits 24, 25", c["gen"][2] == a["gen"][2] | 0x03000000, hex(c["gen"][2]))
check("E4w: ix32-n VDM word 2 = ix-c's (bit 25 cleared) over the 32-bit list",
      d["gen"][2] == a["gen"][2] and d["gen"][0x80:0x80 + 15] == list(range(15)))
check("E4w: ix-25 (16-bit list, bit 25) as S1's ix-25: 16-bit pairs", e["gen"][2] == a["gen"][2] | 0x02000000
      and e["gen"][0x80:0x80 + 8] == a["gen"][0x80:0x80 + 8] and a["gen"][0x80] == 0x00010000)
check("E4w: the probe line echoes '32-bit indices' (the scorer's knob proof)", "32-bit indices" in out)
# E3: the clamp word (block word 14) of the clamp ladder, and the in-band program's S and B immediates are the job's
f, _ = emit("e3k-c3e5", row("g-e3", "e3k-i-c3e5"))
pv = f["pdsv"]
i0 = pv.index(0xdf43)
check("E3: --blk 14 lands at block word 14 (3e-5)", pv[i0 + 14] == 0x37fba882, hex(pv[i0 + 14]))
# E8b: the always compare words: first block word 1, the second block's word 1 and its z offset (word 10)
g, _ = emit("e8b-t1", row("g-e8b", "t-1-alw-far"))
pv, gen = g["pdsv"], g["gen"]
i0, g0 = pv.index(0xdf43), gen.index(0xdf43)
check("E8b t-1: first block word 1 = 0x03c00200 (translucent, always), second 0x00400200, z offset 0.25",
      pv[i0 + 1] == 0x03c00200 and gen[g0 + 1] == 0x00400200 and gen[g0 + 10] == 0x3e800000)
h, _ = emit("e8b-t2", row("g-e8b", "t-2-alw-far"))
pv, gen = h["pdsv"], h["gen"]
i0, g0 = pv.index(0xdf43), gen.index(0xdf43)
check("E8b t-2: first block word 1 = 0x00400200, second 0x03c00200, z offset 0.75",
      pv[i0 + 1] == 0x00400200 and gen[g0 + 1] == 0x03c00200 and gen[g0 + 10] == 0x3f400000)
sys.exit(0 if ok else 1)
