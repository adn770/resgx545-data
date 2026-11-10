#!/usr/bin/env python3
"""Q082 T5 offline proof: the vertex loop of templates/vtx_loop.s (the staged bins/t5v-*__0.bin) runs as intended in sgx-sim
wherever the tool places it, and the absolute-branch form that R1-events used does not.

  - the tool places a vtxuse program at instruction 0x40 of its page (sgxfive_tri_probe.h: UV_VTX 0x200 bytes) and absolute
    indices count from the code base (E476): a `ba #label` loop lands in other code; `br -#7` counts from the branch itself
    (E075: `br #1` is the next instruction) and does not care;
  - debug/simcheck (a scratch cargo crate over crates/sgx-sim, path dependency, read-only) runs a .bin as a vertex task at a
    chosen Machine::code_index; the loop is run at five code indices and every one gives z = 0.25 + 4N ulp and 8 steps an
    iteration; the `ba` variant ends only at code index 0 and stops ("a ba to an index before the program in its code base")
    at the placement the tool uses;
  - the stored depth of every vertex is then 0x3f200000 + N (tests/test_models.py): a loop that does not run N times on every
    vertex shows in the object, the E770 failure mode.
Prints ok/FAIL; exit 1 on any FAIL.  Builds the harness with `cargo build --offline` into debug/target (no network)."""
import sys
sys.dont_write_bytecode = True

import os  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
HOME = pathlib.Path.home()
sys.path[:0] = [str(HOME / "src/resgx545/tools/usse-asm"), str(R2 / "gen")]
import probe  # noqa: E402

ok = True
(R2 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R2 / "debug/tmp")                 # scratch files stay under r2-geo


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


HARNESS = R2 / "debug/target/debug/simcheck"
if not HARNESS.exists():
    env = dict(os.environ, CARGO_TARGET_DIR=str(R2 / "debug/target"))
    r = subprocess.run(["cargo", "build", "--offline", "--manifest-path", str(R2 / "debug/simcheck/Cargo.toml")], env=env,
                       capture_output=True, text=True)
    check("the scratch harness builds offline", r.returncode == 0, r.stderr[-200:])
PA = ["--set", "pa0=0x3f000000", "--set", "pa1=0x3e800000", "--set", "pa2=0", "--set", "pa3=0x3f800000"]


def sim(binf, ci):
    r = subprocess.run([str(HARNESS), str(binf), hex(ci)] + PA, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    return lines[0], {m[1]: int(m[2], 16) for ln in lines if (m := re.fullmatch(r"(o\d+) = (0x[0-9a-f]+)", ln))}


# the placement the tool uses: instruction 0x40 of the page, plus the page's own index (the heap base rounds to 512 KiB)
CODE_INDEXES = [0, 0x40, 0x41, 0x1040, 0x10040]
ITERS = [1, 3, 28, 53, 55, 110, 220, 440, 880, 1760, 3520, 7040]
bad, steps = [], {}
for N in ITERS:
    b = R2 / "bins" / ("t5v-n%d__0.bin" % N if N in (1, 3) else "t5v-i%d__0.bin" % N)
    for ci in CODE_INDEXES:
        status, o = sim(b, ci)
        steps.setdefault(N, set()).add(status)
        if not status.startswith("ended") or o.get("o2") != 0x3e800000 + 4 * N or o.get("o0") != 0x3f000000 or o.get("o3") != 0x3f800000:
            bad.append((N, hex(ci), status, o.get("o2")))
check("the staged loop bins give z = 0x3e800000 + 4N (stored depth 0x3f200000 + N), x and w untouched, at 5 code indices for 12 lengths",
      not bad, str(bad[:3]))
check("every length ends in the same number of steps at every code index (placement independent)", all(len(s) == 1 for s in steps.values()),
      str({n: s for n, s in steps.items() if len(s) > 1}))
per = (int(steps[3].copy().pop().split()[1]) - int(steps[1].copy().pop().split()[1])) / 2
check("the body is 8 instructions an iteration (as E769's body 8): steps(3) - steps(1) = 16", per == 8, str(per))
check("7040 iterations: 14 + 8 * 7040 steps (56000+ instructions a vertex)", steps[7040].copy().pop().split()[1] == str(14 + 8 * 7040) or
      abs(int(steps[7040].copy().pop().split()[1]) - (14 + 8 * 7040)) <= 8, str(steps[7040]))
# the absolute-branch form (R1-events' loops): ends at code index 0, stops at the placement the tool uses
src = (R2 / "templates/vtx_loop.s").read_text().replace("{N}", "0x00000003").replace("{ZB}", "0x3E800000")
src_ba = src.replace("p1 br -#0x00000007", "p1 ba #12")
with tempfile.TemporaryDirectory() as d:
    f = pathlib.Path(d) / "ba.bin"
    probe._assemble(src_ba, f)
    s0, o0 = sim(f, 0)
    s40, o40 = sim(f, 0x40)
    s10040, _ = sim(f, 0x10040)
check("the same loop with an absolute `ba #12` ends at code index 0 (a fill's placement)", s0.startswith("ended") and o0.get("o2") == 0x3e80000c, f"{s0} {o0.get('o2')}")
check("... and stops with 'a ba to an index before the program in its code base' at index 0x40 and 0x10040 (the vtxuse placement): "
      "the E770 mechanism", "before the program" in s40 and "before the program" in s10040, f"{s40} | {s10040}")
# the second phase index: the first phas's next-phase field is the index of the second phas
code = [re.sub(r"\s*;.*$", "", ln).strip() for ln in (R2 / "templates/vtx_loop.s").read_text().splitlines()]
code = [c for c in code if c]
idx = [i for i, c in enumerate(code) if c.startswith("phas")]
check("vtx_loop.s: the first phas names the second phas (#22) and the br is 7 instructions back to the first imae",
      len(idx) == 2 and int(re.match(r"phas #(\d+)", code[idx[0]])[1]) == idx[1] == 22
      and code.index("p1 br -#0x00000007") - 7 == next(i for i, c in enumerate(code) if c.startswith("imae")), str(idx))
# the sgx-sim command line (code index 0) agrees with the harness
cli = subprocess.run([str(HOME / "src/resgx545/target/debug/sgx-sim"), "--task", "vertex", "--temps", "16"] + PA +
                     [str(R2 / "bins/t5v-i55__0.bin")], capture_output=True, text=True)
check("the landed sgx-sim command line agrees with the harness at code index 0 (o2 = 0x3e8000dc, 14 + 8 * 55 steps)",
      "ended after 454 steps" in cli.stdout and "o2 = 0x3e8000dc" in cli.stdout, cli.stdout.splitlines()[0])
sys.exit(0 if ok else 1)
