#!/usr/bin/env python3
"""Every depth program of R3 (the vertex programs of g-da, g-db, g-dc, g-dd: vtx_wzclip.s and vtx_zw.s, R1's simulator-checked templates,
unchanged), assembled by the generator, run in the landed simulator (target/debug/sgx-sim --task vertex, read-only) for the triangle's
three vertices: the outputs are the arithmetic the row assumes, bit for bit: o2 = Z and o3 = W at every vertex (vtx_wzclip: x and y scaled
by W), or o2 = A x + B and o3 = C x + D (vtx_zw).  The frozen Z and W of every row are therefore what the vertex program stores before the
hardware's divide.  The tool's `--mock` acceptance of every command is tests/mock_all.py.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import os  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
REPO = pathlib.Path.home() / "src/resgx545"
sys.path[:0] = [str(REPO / "tools/usse-asm"), str(R3 / "gen")]
import r3_geo as G  # noqa: E402
import r3models as M  # noqa: E402

SIM = REPO / "target/debug/sgx-sim"
ok = True
hx = lambda v: f"0x{v:08X}"
VERT = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def sim(binf, x, y):
    r = subprocess.run([str(SIM), "--task", "vertex", "--set", f"pa0={hx(M.word(M.f32(x)))}", "--set", f"pa1={hx(M.word(M.f32(y)))}",
                        "--set", "pa2=0", "--set", f"pa3={hx(M.word(M.f32(1.0)))}", str(binf)], capture_output=True, text=True, timeout=60)
    if not r.stdout.startswith("ended"):
        return {"error": r.stdout[:120]}
    return {m[1]: int(m[2], 16) for m in re.finditer(r"^(o\d) = (0x[0-9a-f]+)$", r.stdout, re.M)}


for st in ("g-da", "g-db", "g-dc", "g-dd"):
    getattr(G, "g_" + st[2:])()
check("57 depth programs registered (27 + 16 + 10 + 4)", len(G.PROGRAMS) == 57, str(len(G.PROGRAMS)))
bad = []
for name, (tpl, inp, blk) in G.PROGRAMS.items():
    binf = R3 / "bins" / f"{name}__0.bin"
    if not binf.exists():
        bad.append((name, "no bin"))
        continue
    for x, y in VERT:
        r = sim(binf, x, y)
        fx, fy = M.f32(x), M.f32(y)
        if tpl == "vtx_wzclip.s":
            want = dict(o0=M.rnd(fx * inp["S"], "rn"), o1=M.rnd(fy * inp["S"], "rn"), o2=inp["Z"], o3=inp["B"])
        else:
            want = dict(o0=fx, o1=fy, o2=M.rnd(inp["A"] * fx + inp["B"], "rn"), o3=M.rnd(inp["C"] * fx + inp["D"], "rn"))
        got = {k: r.get(k) for k in want}
        if any(got[k] != M.word(v) for k, v in want.items()):
            bad.append((name, x, y, got, {k: hex(M.word(v)) for k, v in want.items()}))
            break
check("every depth program in the simulator: o2 = Z, o3 = W (x, y scaled by W), or the z / w lines of vtx_zw, bit for bit at the three vertices", not bad, str(bad[:2]))
check("the viewport rows carry --blk 10 and --blk 11 with the frozen words",
      all(re.search(r"--blk 10=0x[0-9A-Fa-f]+ --blk 11=0x[0-9A-Fa-f]+", ln.split("|", 6)[6]) for ln in (R3 / "tables/g-dc.txt").read_text().splitlines() if ln and not ln.startswith("#")))
sys.exit(0 if ok else 1)
