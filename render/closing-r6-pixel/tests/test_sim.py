#!/usr/bin/env python3
"""Build the scratch sgx-sim harness (debug-src/simcheck -> debug/simcheck, target debug/target; offline cargo build against the
resgx545 tree's crates/sgx-sim and usse-isa) that tests/test_o5.py, test_rw5.py and the fake tool run the staged programs in, and
check it on two known programs: R4's c-u (eight output words) and R4's rw-k1 (w = 3, 9 at the first two vertices); R6: --list prints the
simulator's decode of every instruction (the fake tool's readback worlds interpret it), and rd-4's readback runs (o0 = o4's word).  ok / FAIL."""
import os
import pathlib
import shutil
import subprocess
import sys

R6 = R5 = pathlib.Path(__file__).resolve().parent.parent
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


src, dst = R5 / "debug-src/simcheck", R5 / "debug/simcheck"
dst.mkdir(parents=True, exist_ok=True)
for f in ("Cargo.toml", "Cargo.lock", "src/main.rs"):
    (dst / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / f, dst / f)
env = dict(os.environ, CARGO_TARGET_DIR=str(R5 / "debug/target"))
r = subprocess.run(["cargo", "build", "--offline", "--manifest-path", str(dst / "Cargo.toml")], env=env, capture_output=True, text=True)
check("the scratch harness builds offline against the resgx545 tree's sgx-sim", r.returncode == 0, r.stderr[-300:])
H = R5 / "debug/target/debug/simcheck"
o = subprocess.run([str(H), str(R5 / "bins/r4o-u-x.bin"), "0x20", "--pixel", "--set", "pa0=0x3f000000"], capture_output=True, text=True).stdout
check("R4's c-u-x in the sim: ended, o0 = pa0 | 0x4141 (marker 0x105, tag 1), o4 tag 5", "ended" in o and "o0 = 0x3f004141" in o and "o4 = 0x3f004145" in o, o.replace("\n", " ")[:120])
o = subprocess.run([str(H), str(R5 / "bins/rw-k1.bin"), "0x40", "--set", "pa0=0xbf400000", "--set", "pa1=0xbf400000", "--set", "pa2=0",
                    "--set", "pa3=0x3f800000"], capture_output=True, text=True).stdout
check("R4's rw-k1 in the sim at x = -0.75: o3 = 3.0 (w = 4 x + 6)", "o3 = 0x40400000" in o, o.replace("\n", " ")[:120])
o = subprocess.run([str(H), str(R5 / "bins/r6o-rd-4-x.bin"), "0x20", "--list", "--tri-pixel", "0,0", "--set", "pa0=0x11110000"],
                   capture_output=True, text=True).stdout.splitlines()
ins = [x for x in o if x.startswith("insn ")]
check("--list: the decode of rd-4-x, its last two instructions the readback", ins[-2:] == ["insn 10 mov.skipinv r10, o4", "insn 11 mov.skipinv.end o0, r10"], str(ins[-2:]))
o0 = next((x for x in o if x.startswith("o0 = ")), "")
o4 = next((x for x in o if x.startswith("o4 = ")), "")
check("rd-4-x in the sim: ended, o0 = o4's word (the readback ran)", any(x.startswith("ended") for x in o) and o0[5:] == o4[5:] and o4.endswith("d5"), f"{o0} {o4}")
sys.exit(0 if ok else 1)
