#!/usr/bin/env python3
"""Offline option checks with the tool's mock and --emit-scene (no laptop): the words a table's options write land where the
table assumes.  Prints ok/FAIL lines.  Output files under out/mock/em."""
import json, pathlib, shlex, subprocess, sys
S1 = pathlib.Path(__file__).resolve().parent.parent
TOOL = pathlib.Path.home() / "src/resgx545/userspace/libsgxfive/build/sgxfive-test"
EM = S1 / "out/mock/em"; (EM / "dump").mkdir(parents=True, exist_ok=True)
ok = True
def emit(name, args):
    f = EM / f"{name}.json"
    a = args.replace("$W", str(EM)).replace("$S", str(S1 / "bins")).replace("--pixels", f"--pixels --emit-scene {f}")
    subprocess.run([str(TOOL), "--mock"] + shlex.split(a), capture_output=True, text=True, timeout=120)
    j = json.load(open(f))
    return {m["role"]: [int(x, 16) for x in m["dwords"]] for m in j["memory"]}, j
def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else "")); ok &= bool(cond)
row = lambda st, nm: next(l for l in open(S1 / f"tables/{st}.txt") if l.startswith(nm + "|")).rstrip("\n").split("|", 6)[6]
# E4: the flip changes exactly bit 24 of the index-list header and nothing else of the gen page
a, _ = emit("e4-ctl", row("g-e4", "ix-c"))
b, _ = emit("e4-24", row("g-e4", "ix-24-r1"))
d = [(i, x ^ y) for i, (x, y) in enumerate(zip(a["gen"], b["gen"])) if x != y]
check("E4: --vdm 2^=0x01000000 flips only bit 24 of one gen-page dword", len(d) == 1 and d[0][1] == 0x01000000, str(d))
# E3: the viewport x offset (block word 6) and the w clamp (block word 14)
c, _ = emit("e3-ctl", row("g-e3", "e3o-x1000"))
pv = c["pdsv"]; i0 = pv.index(0xdf43)
check("E3: --blk 6 lands at block word 6 (1000.0)", pv[i0 + 6] == 0x447a0000, hex(pv[i0 + 6]))
e, _ = emit("e3-k", row("g-e3", "e3k-above"))
pv = e["pdsv"]; i0 = pv.index(0xdf43)
check("E3: --blk 14 lands at block word 14", pv[i0 + 14] == 0x3a831270, hex(pv[i0 + 14]))
# E8b: obj2 block words 1 and 10 (second block in the gen page) and the first block's word 1
f, _ = emit("e8b", row("g-e8b", "t-2-far"))
pv, gen = f["pdsv"], f["gen"]; i0 = pv.index(0xdf43); g0 = gen.index(0xdf43)
check("E8b: first block word 1 = 0x00400200, second block word 1 = 0x02400200, second word 10 = 0.75f",
      pv[i0 + 1] == 0x00400200 and gen[g0 + 1] == 0x02400200 and gen[g0 + 10] == 0x3f400000)
sys.exit(0 if ok else 1)
