# SPDX-License-Identifier: MIT
"""sim.py: sgx-sim (built from the pinned resgx545 commit by pins.tool) as the frozen predictor.

  run(text, temps=32)  Run(ok, why, regs {name: value}, scratch {byte offset: value}) of one program
                       (usse-asm text) as the probe runs it: one instance, the scratch buffer at
                       0x3e003000 filled with 0xd0000000 | i, a limm of 0x5cafnnnn its address + nnnn
  classes(op, src2, a, b)  the four channels' value classes (-1, 0, 1) of OP.test on (a, b), read
                       from the sim's own single-condition text forms (testtaz, testnat with the a
                       join on chan0 to chan3): what sgx-sim's predicate tests on each channel
  replay(pin)          (match, unsupported, mismatch) of `sgx-sim --vectors` on a kept vector file"""
import collections
import os
import re
import subprocess
import tempfile

import pins

BASE = 0x3E003000
Run = collections.namedtuple("Run", "ok why regs scratch")
_CLS = {}


def run(text, temps=32):
    r = subprocess.run([pins.tool("sgx-sim"), "--temps", str(temps), "-"], input=text,
                       capture_output=True, text=True, timeout=60)
    out = r.stdout + r.stderr
    regs = {m.group(1): int(m.group(2), 16)
            for m in re.finditer(r"^([a-z]+[0-9]+) = 0x([0-9a-f]+)", out, re.M)}
    scr = {}
    for m in re.finditer(r"\[0x([0-9a-f]+)\] = 0x([0-9a-f]+) \(was 0x([0-9a-f]+)\)", out):
        a, v, w = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
        if v != w:
            scr[a - BASE] = v
    ok = "ended after" in out
    why = "" if ok else next((ln for ln in out.splitlines() if ln.startswith("unsupported")),
                             out.strip()[-200:])
    return Run(ok, why, regs, scr)


def classes(op, src2, a, b):
    key = (op, src2, a, b)
    if key in _CLS:
        return _CLS[key]
    out = []
    for c in range(4):
        lines = ["phas #0, #0, pixel, end, parallel", "mov.skipinv r1, #0x%08x" % a,
                 "mov.skipinv r2, #0x%08x" % b]
        for t, reg in (("testtaz", "r10"), ("testnat", "r11")):
            lines += [f"{op}.{t}.chan{c} !c0, p0, r1, {src2}", f"mov {reg}, #0", f"p0 mov {reg}, #1"]
        lines.append("mov.skipinv.end o0, r10")
        r = run("\n".join(lines) + "\n")
        if not r.ok:
            raise SystemExit(f"sgx-sim refuses the class of {op} {src2} {a:#x} {b:#x} chan{c}: "
                             f"{r.why}")
        z, n = r.regs["r10"], r.regs["r11"]
        assert not (z and n), (op, a, b, c)
        out.append(0 if z else -1 if n else 1)
    _CLS[key] = tuple(out)
    return _CLS[key]


def replay(pin):
    with tempfile.TemporaryDirectory(prefix="r16u-vec.") as td:
        p = os.path.join(td, os.path.basename(pin.partition(":")[2]))
        with open(p, "wb") as f:
            f.write(pins.blob(pin))
        r = subprocess.run([pins.tool("sgx-sim"), "--vectors", p], capture_output=True, text=True,
                           timeout=300)
    m = re.search(r"(\d+) match, (\d+) unsupported, (\d+) mismatch", r.stdout + r.stderr)
    if not m:
        raise SystemExit(f"sgx-sim --vectors {pin}: {r.stdout[-300:]} {r.stderr[-300:]}")
    return tuple(int(x) for x in m.groups())


def assemble(text):
    with tempfile.TemporaryDirectory(prefix="r16u-asm.") as td:
        src, out = os.path.join(td, "p.s"), os.path.join(td, "p.bin")
        with open(src, "w") as f:
            f.write(text)
        r = subprocess.run([pins.tool("usse-asm"), "-o", out, src], capture_output=True,
                           text=True, timeout=60)
        if r.returncode:
            raise RuntimeError("usse-asm: " + r.stderr.strip())
        return open(out, "rb").read()


def word(line):
    """The 64-bit word of one instruction's text."""
    b = assemble(line + "\n")
    assert len(b) == 8, line
    return int.from_bytes(b, "little")
