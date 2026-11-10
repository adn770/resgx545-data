#!/usr/bin/env python3
"""R3-pixel loop programs (decision R3-P1), checked offline before anything is frozen:
  1. every pixel loop (kinds b2 b4 b8 b12 b16 b8n ld8, relative `p0 br -#(BODY-1)` with the MARK proof) assembles with the
     landed usse-asm and ends in sgx-sim (scratch harness debug/simcheck, --pixel) at the code indices a fill (0), a --tri
     pixel slot (0x20) and a higher page (0x1020) give, with o0 = MARK = 0xC0DE0000 | N (never 0: E770's unwritten register
     cannot pass), in exactly prologue + BODY * N + 1 steps;
  2. the absolute `ba` loop of E431 (the q-f0 abs control, fills only) ends at code index 0 and STOPS ("a ba to an index
     before the program in its code base") at 0x20 and 0x1020: E770's mechanism, and why the generator refuses `ba` for a
     --tri slot (a refusal tested here);
  3. the vertex loops (b8v, b16v, b4v; templates/vtx_loop.s) end at every vertex code index (0, 0x40, 0x41, 0x1040) with
     z = 0x3e800000 + 4 N (stored depth 0x3f200000 + N) in 14 + BODY * N steps, the second `phas` index right and the `br`
     BODY - 1 back to the first body instruction.
Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_loops.py"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen"), str(pathlib.Path.home() / "src/resgx545/tools/usse-asm")]
(R3 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R3 / "debug/tmp")
import probe  # noqa: E402
import r3loops as L  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


HARNESS = R3 / "debug/target/debug/simcheck"
if not HARNESS.exists():
    env = dict(os.environ, CARGO_TARGET_DIR=str(R3 / "debug/target"))
    r = subprocess.run(["cargo", "build", "--offline", "--manifest-path", str(R3 / "debug/simcheck/Cargo.toml")], env=env,
                       capture_output=True, text=True)
    check("the scratch harness builds offline", r.returncode == 0, r.stderr[-200:])
PA = ["--set", "pa0=0x3f000000", "--set", "pa1=0x3e800000", "--set", "pa2=0", "--set", "pa3=0x3f800000"]


def sim(binf, ci, pixel):
    r = subprocess.run([str(HARNESS), str(binf), hex(ci)] + (["--pixel"] if pixel else []) + PA, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    return lines[0], {m[1]: int(m[2], 16) for ln in lines if (m := re.fullmatch(r"(o\d+) = (0x[0-9a-f]+)", ln))}


def asm(text, name):
    d = pathlib.Path(tempfile.mkdtemp(prefix="loops-"))
    f = d / (name + ".bin")
    probe._assemble(text, f)
    return f


# ---- 1. the pixel loops
KINDS = ["b2", "b4", "b8", "b12", "b16", "b8n", "ld8"]
NS = {"b2": [1, 500, 16000], "b4": [1, 40, 640], "b8": [1, 53, 56, 3520], "b12": [1, 8, 136], "b16": [1, 6, 104],
      "b8n": [1, 60, 3840], "ld8": [1, 20, 320]}
bad, bodyerr = [], []
for kind in KINDS:
    for n in NS[kind]:
        name, text, info = L.pixel_loop_source(kind, n)
        # the tool patches the SCRATCH_IMM immediate (0x5CAF0000) with the scratch buffer's address: the harness's is 0x3e003000
        f = asm(text.replace("0x5CAF0000", "0x3E003000"), name)
        for ci in (0, 0x20, 0x1020):
            status, o = sim(f, ci, True)
            want_steps = info["prologue"] + info["body"] * n + 1
            if not status.startswith("ended") or o.get("o0") != (0xC0DE0000 | n) or int(status.split()[1]) != want_steps:
                bad.append((kind, n, hex(ci), status, o.get("o0")))
check("every pixel loop (7 kinds, 21 lengths) ends at code indices 0, 0x20, 0x1020 with o0 = 0xC0DE0000 | N in "
      "prologue + BODY * N + 1 steps", not bad, str(bad[:3]))
check("the bodies have the instruction counts of the design (b2 2, b4 4, b8 8, b12 12, b16 16, b8n 8, ld8 8)",
      all(L.pixel_loop_source(k, 7)[2]["body"] == b for k, b in (("b2", 2), ("b4", 4), ("b8", 8), ("b12", 12), ("b16", 16), ("b8n", 8), ("ld8", 8))))
tx = L.pixel_loop_source("b8", 53)[1]
check("the loop closes with a RELATIVE branch p0 br -#7 (never ba) and the MARK is in the prologue",
      "p0 br -#0x00000007" in tx and "\nba" not in tx and " ba " not in tx and "0xC0DE0035" in tx)
for kind, nm in (("b16", 15), ("b12", 11), ("b4", 3), ("b2", 1), ("b8n", 7), ("ld8", 7)):
    check(f"{kind}: the branch is -#{nm} (BODY - 1)", f"p0 br -#0x{nm:08x}" in L.pixel_loop_source(kind, 9)[1])
check("o0 = MARK is not 0, so an unwritten output register (E770) cannot pass the proof",
      all((0xC0DE0000 | n) != 0 for n in (1, 53, 16000)))
# b8n has no multiply-add; b2 has neither; the others have the stated number
count = lambda t: len(re.findall(r"^imae", t, re.M))
check("imae counts: b16 14, b12 10, b8 6, b4 2, b2 0, b8n 0, ld8 4",
      [count(L.pixel_loop_source(k, 9)[1]) for k in ("b16", "b12", "b8", "b4", "b2", "b8n", "ld8")] == [14, 10, 6, 2, 0, 0, 4])

# ---- 2. the absolute loop and the refusal
name, text, info = L.pixel_loop_source("b8", 53, form="abs")
f = asm(text, name)
s0, o0 = sim(f, 0, True)
s20, _ = sim(f, 0x20, True)
s1020, _ = sim(f, 0x1020, True)
check("E431's absolute `ba` loop (the abs control of q-f0, a FILL) ends at code index 0 with o0 = 0 (2048 of 2048, E431)",
      s0.startswith("ended") and o0.get("o0") == 0, f"{s0} {o0}")
check("... and stops at the code index of a --tri pixel slot (0x20, 0x1020): 'a ba to an index before the program' (E770)",
      "before the program" in s20 and "before the program" in s1020, f"{s20} | {s1020}")
try:
    L.assert_no_ba(text, "a --tri slot")
    check("the generator refuses a `ba` loop for a --tri slot", False)
except L.LoopError as e:
    check("the generator refuses a `ba` loop for a --tri slot", "ba" in str(e), str(e))
try:
    L.assert_no_ba(L.pixel_loop_source("b8", 53)[1], "a --tri slot")
    check("the relative loop passes the --tri check", True)
except L.LoopError as e:
    check("the relative loop passes the --tri check", False, str(e))
try:
    L.pixel_loop_source("b16", 20, form="abs")
    check("the abs form exists for b8 only (E431's control)", False)
except L.LoopError:
    check("the abs form exists for b8 only (E431's control)", True)

# ---- 3. the vertex loops
bad, steps = [], {}
for kind, per in (("b8v", 8), ("b16v", 16), ("b4v", 4)):
    for n in (1, 3, 110, 1760):
        name, text = L.vertex_loop_source(kind, n)
        f = asm(text, name)
        for ci in (0, 0x40, 0x41, 0x1040):
            status, o = sim(f, ci, False)
            steps.setdefault((kind, n), set()).add(status)
            if not status.startswith("ended") or o.get("o2") != 0x3e800000 + 4 * n or o.get("o0") != 0x3f000000:
                bad.append((kind, n, hex(ci), status, o.get("o2")))
check("the vertex loops (b8v, b16v, b4v) give z = 0x3e800000 + 4N (stored depth 0x3f200000 + N), x untouched, at 4 code indices",
      not bad, str(bad[:3]))
check("every length ends in one step count at every code index (placement independent)", all(len(v) == 1 for v in steps.values()))
per = {k: (int(next(iter(steps[(k, 3)])).split()[1]) - int(next(iter(steps[(k, 1)])).split()[1])) / 2 for k in ("b8v", "b16v", "b4v")}
check("the bodies are 8, 16 and 4 instructions an iteration (steps(3) - steps(1) = 2 * BODY)", per == {"b8v": 8, "b16v": 16, "b4v": 4}, str(per))
for kind, B in (("b8v", 8), ("b16v", 16), ("b4v", 4)):
    text = L.vertex_loop_source(kind, 5)[1]
    code = [re.sub(r"\s*;.*$", "", ln).strip() for ln in text.splitlines()]
    code = [c for c in code if c]
    idx = [i for i, c in enumerate(code) if c.startswith("phas")]
    first = next(i for i, c in enumerate(code) if c.startswith("imae"))
    br = next(i for i, c in enumerate(code) if c.startswith("p1 br"))
    check(f"{kind}: the first phas names the second phas (#{idx[1]}) and the br is {B - 1} back to the first body instruction",
          len(idx) == 2 and int(re.match(r"phas #(\d+)", code[idx[0]])[1]) == idx[1] and br - (B - 1) == first
          and f"p1 br -#0x{B - 1:08x}" in text, f"{idx} first {first} br {br}")
try:
    L.assert_no_ba(L.vertex_loop_source("b8v", 5)[1], "a vertex slot")
    check("the vertex loops carry no `ba`", True)
except L.LoopError as e:
    check("the vertex loops carry no `ba`", False, str(e))

# ---- 4. EVERY staged loop program (bins/), as the tables run it: rebuilt from the generator (the bytes are the frozen ones) and run
# in sgx-sim at the code indices of its slot (a fill: 0; a --tri pixel slot 0x20 and 0x1020; a vertex slot 0, 0x40, 0x41, 0x1040)
nbin = nbad = 0
badlist = []
used = {m for t_ in (R3 / "tables").glob("*.txt") for m in re.findall(r"\$S/((?:v)?loop-[\w-]+)\.bin", t_.read_text())}
for f in sorted((R3 / "bins").glob("loop-*.bin")) + sorted((R3 / "bins").glob("vloop-*.bin")):
    m = re.fullmatch(r"(v?loop)-(?:(rel|abs)-)?(\w+?)-i(\d+)\.bin", f.name)
    nbin += 1
    if m[1] == "loop":
        form, kind, n = m[2], m[3], int(m[4])
        name, text, info = L.pixel_loop_source(kind, n, form)
        rebuilt = asm(text, name)
        same = rebuilt.read_bytes() == f.read_bytes()
        runf = f
        if kind == "ld8":                                   # the tool patches 0x5CAF0000; the harness's scratch is at 0x3e003000
            runf = asm(text.replace("0x5CAF0000", "0x3E003000"), name)
        cis = (0,) if form == "abs" else (0, 0x20, 0x1020)
        for ci in cis:
            status, o = sim(runf, ci, True)
            want = 0 if form == "abs" else (0xC0DE0000 | n)
            if not status.startswith("ended") or o.get("o0") != want or (form == "rel" and int(status.split()[1]) != info["prologue"] + info["body"] * n + 1):
                badlist.append((f.name, hex(ci), status, o.get("o0")))
        if not same:
            badlist.append((f.name, "bytes differ from the generator"))
    else:
        kind, n = m[3], int(m[4])
        name, text = L.vertex_loop_source(kind, n)
        same = asm(text, name).read_bytes() == f.read_bytes()
        for ci in (0, 0x40, 0x41, 0x1040):
            status, o = sim(f, ci, False)
            if not status.startswith("ended") or o.get("o2") != 0x3e800000 + 4 * n:
                badlist.append((f.name, hex(ci), status, o.get("o2")))
        if not same:
            badlist.append((f.name, "bytes differ from the generator"))
check(f"every staged loop program ({nbin} in bins/: pixel loops and vertex loops) equals the generator's output and ends in sgx-sim at "
      "every code index of its slot with the MARK / the depth z = 0x3e800000 + 4N", nbin == len(used) and not badlist, str(badlist[:3]))
sys.exit(0 if ok else 1)
