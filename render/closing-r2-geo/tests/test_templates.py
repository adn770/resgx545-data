#!/usr/bin/env python3
"""The three vertex templates of decision R2-15 (vtx_zab_pa1.s for T2, vtx_zw.s for T3, vtx_wzclip.s for T4), assembled
with the landed probe tool and checked three ways, all offline on the Mac:
  1. the source: pa1 is vtx_zab.s with ONE instruction changed; every template's second phase (`phas #N`) is the index of
     its second phas instruction;
  2. the landed simulator (target/debug/sgx-sim --task vertex, read-only) runs each assembled bin for the triangle's three
     vertices and the outputs o2 (z) and o3 (w) are the arithmetic the row assumes, bit for bit (dyadic inputs);
  3. the landed tool's `--mock` accepts each bin (probe --tri vtxuse, rc 0).  NOTE: the mock does not execute the vertex
     program (every variant draws the host-computed 1098-pixel triangle), so it checks acceptance, not behaviour; the
     simulator is the behavioural check.
One laptop rebuild covers all three (stage_r1.sh); T3 and T4 have no rows in R1.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import difflib  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

R1 = pathlib.Path(__file__).resolve().parent.parent
os.makedirs(R1 / "debug/tmp", exist_ok=True)
tempfile.tempdir = str(R1 / "debug/tmp")                 # scratch files stay under r2-geo
REPO = pathlib.Path.home() / "src/resgx545"
sys.path[:0] = [str(REPO / "tools/usse-asm"), str(R1 / "gen")]
import probe  # noqa: E402
from rcommon import f32  # noqa: E402

TOOL = pathlib.Path(os.environ.get("TOOL_SRC", REPO)) / "userspace/libsgxfive/build/sgxfive-test"
SIM = pathlib.Path(os.environ.get("TOOL_SRC", REPO)) / "target/debug/sgx-sim"
DIS = pathlib.Path(os.environ.get("TOOL_SRC", REPO)) / "tools/usse-dis/usse-dis"
E3T = REPO / "probes/mte/templates"
TPL = R1 / "templates"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


hx = lambda v: f"0x{v:08X}"
W = pathlib.Path(tempfile.mkdtemp())
VERT = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]


def build(name, src, inputs, vals, src_dir, **kw):
    d = dict(name=name, question="r1", source=src, host="tri", slot="vtxuse", size=[64, 64], pixels=True, inputs=inputs,
             cases=[[hx(v) for v in vals]], dump_render=True, temps=8, vtx_coords=2, slots={"pixel": "pix_green.s"}, **kw)
    p = probe._probe(d, "r1.toml")
    out = probe.build(p, W, src_dir)[0]
    probe.build_helpers([p], W, src_dir)
    return out


def sim(binf, x, y):
    """The simulator's outputs of one vertex (pa0 = x, pa1 = y, pa2 = z 0, pa3 = w 1): {'o2': word, ...}."""
    r = subprocess.run([str(SIM), "--task", "vertex", "--set", f"pa0={hx(f32(x))}", "--set", f"pa1={hx(f32(y))}",
                        "--set", "pa2=0", "--set", f"pa3={hx(f32(1.0))}", str(binf)], capture_output=True, text=True, timeout=60)
    if not r.stdout.startswith("ended"):
        return {"error": r.stdout[:120]}
    return {m[1]: int(m[2], 16) for m in re.finditer(r"^(o\d) = (0x[0-9a-f]+)$", r.stdout, re.M)}


def mock(binf):
    argv = [str(TOOL), "--mock", "probe", "--temps", "8", "--pixels", "--tri", "vtxuse", "--width", "64", "--height", "64",
            "--vtx-coords", "2", "--slot", f"pixel={W / 'pix_green.bin'}", str(binf)]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    n = sum(ln.count("ff00ff00") for ln in r.stdout.splitlines() if ": row " in ln)
    return r.returncode, n


def phas_ok(path):
    code = [re.sub(r"\s*;.*$", "", ln).strip() for ln in path.read_text().splitlines()]
    code = [c for c in code if c]
    idx = [i for i, c in enumerate(code) if c.startswith("phas")]
    return len(idx) == 2 and int(re.match(r"phas #(\d+)", code[idx[0]])[1]) == idx[1], idx


# ------------------------------------------------------------------------------------------------ T2
a = [ln for ln in (E3T / "vtx_zab.s").read_text().splitlines() if not ln.lstrip().startswith(";")]
b = [ln for ln in (TPL / "vtx_zab_pa1.s").read_text().splitlines() if not ln.lstrip().startswith(";")]
dl = [ln for ln in difflib.unified_diff(a, b, lineterm="", n=0) if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
code = lambda ln: re.sub(r"\s*;.*$", "", ln).strip()
check("T2: vtx_zab_pa1.s differs from vtx_zab.s in exactly one instruction (pa0 -> pa1 in the fmad)",
      len(dl) == 2 and code(dl[0][1:]) == "fmad.skipinv o2, pa0, r1, r2" and code(dl[1][1:]) == "fmad.skipinv o2, pa1, r1, r2", str(dl))
p0 = build("zx", "vtx_zab.s", ["A", "B"], [f32(2.0), f32(-1.0)], E3T)
p1 = build("zy", "vtx_zab_pa1.s", ["A", "B"], [f32(2.0), f32(-1.0)], TPL)
x0, x1 = p0.read_bytes(), p1.read_bytes()
nd = [i for i in range(0, len(x0), 8) if x0[i:i + 8] != x1[i:i + 8]]
check("T2: the two bins have the same size and differ in exactly one 64-bit instruction (index 9)",
      len(x0) == len(x1) and nd == [72], f"{len(x0)} bytes, differing words at byte offsets {nd}")
check("T2 phas: the second phase is at #11", phas_ok(TPL / "vtx_zab_pa1.s") == (True, [0, 11]), str(phas_ok(TPL / "vtx_zab_pa1.s")))
res = [(sim(p1, x, y), sim(p0, x, y)) for x, y in VERT]
check("T2 sim: o2 = 2 y - 1 from y for the pa1 variant, 2 x - 1 from x for vtx_zab (exact)",
      all(r1.get("o2") == f32(2 * y - 1) and r0.get("o2") == f32(2 * x - 1) for (r1, r0), (x, y) in zip(res, VERT)), str(res[0]))
rc, n = mock(p1)
check("T2 mock: accepted (rc 0, draws the host triangle)", rc == 0 and n > 500, f"rc {rc}, {n} green px")
# ------------------------------------------------------------------------------------------------ T3
A, B, C, D = 2.0, 1.0, 0.5, 1.25
t3 = build("zw", "vtx_zw.s", ["A", "B", "C", "D"], [f32(A), f32(B), f32(C), f32(D)], TPL)
check("T3: 16 instructions (vtx_zab's 13 + the three of the w line), second phase #14",
      t3.stat().st_size == 16 * 8 and phas_ok(TPL / "vtx_zw.s") == (True, [0, 14]), f"{t3.stat().st_size} bytes {phas_ok(TPL / 'vtx_zw.s')}")
res = [sim(t3, x, y) for x, y in VERT]
check("T3 sim: z = 2 x + 1 and w = 0.5 x + 1.25 at the three vertices (exact), x and y untouched",
      all(r.get("o2") == f32(A * x + B) and r.get("o3") == f32(C * x + D) and r.get("o0") == f32(x) and r.get("o1") == f32(y)
          for r, (x, y) in zip(res, VERT)), str(res[0]))
rc, n = mock(t3)
check("T3 mock: accepted (rc 0)", rc == 0 and n > 500, f"rc {rc}, {n} green px")
# ------------------------------------------------------------------------------------------------ T4
Z, Wv = -2.1, 3.0
t4 = build("wz", "vtx_wzclip.s", ["S", "A", "B", "Z"], [f32(Wv), 0, f32(Wv), f32(Z)], TPL)
ref = build("wref", "vtx_wclip.s", ["S", "A", "B"], [f32(Wv), 0, f32(Wv)], E3T)
check("T4: vtx_wclip's instructions + one (the `mov o2, #Z`), second phase #15",
      t4.stat().st_size == ref.stat().st_size + 8 and phas_ok(TPL / "vtx_wzclip.s") == (True, [0, 15]),
      f"{ref.stat().st_size} -> {t4.stat().st_size} bytes, {phas_ok(TPL / 'vtx_wzclip.s')}")
res = [sim(t4, x, y) for x, y in VERT]
rref = [sim(ref, x, y) for x, y in VERT]
check("T4 sim: o2 = Z (-2.1), o3 = w = 3, x and y scaled by 3 (exact); vtx_wclip alone leaves o2 = pa2 = 0",
      all(r.get("o2") == f32(Z) and r.get("o3") == f32(Wv) and r.get("o0") == f32(3 * x) and r.get("o1") == f32(3 * y)
          for r, (x, y) in zip(res, VERT)) and all(r.get("o2") == 0 for r in rref), str(res[0]))
rc, n = mock(t4)
check("T4 mock: accepted (rc 0)", rc == 0 and n > 500, f"rc {rc}, {n} green px")
sys.exit(0 if ok else 1)
