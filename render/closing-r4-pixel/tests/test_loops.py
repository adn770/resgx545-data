#!/usr/bin/env python3
"""R4-pixel loop programs, checked offline before anything is frozen (R3-pixel's test_loops.py for the programs R4 stages):
  1. every pixel loop the tables stage (b8 relative `p0 br -#7` with the MARK proof; ld8; ld0 and ldo, the load-then-loop programs with
     two counters) is rebuilt from the generator (bytes equal the staged ones) and ends in sgx-sim (scratch harness debug/simcheck,
     --pixel) at the code indices a fill (0), a --tri pixel slot (0x20) and a higher page (0x1020) give, with o0 = MARK and the step
     count the generator computes; ld0 / ldo reach the MARK only when BOTH counters end;
  2. every vertex loop (b8v, b12v, b2v) ends at the vertex code indices (0, 0x40, 0x41, 0x1040) with o2 = 0x3e800000 + 4 N (stored depth
     0x3f200000 + N) in the step count of its body, the second `phas` index right; b2v's depth word is only right if its counter ended
     at 0 (a counter that did not reach 0 changes o2);
  3. the relative branches: ld0 / ldo carry -#7 (inner) and -#12 (outer), no `ba` anywhere in a staged program (a --tri or vertex slot).
Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_loops.py"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
MAIN = os.environ.get("RESGX545_MAIN", str(pathlib.Path.home() / "src/resgx545"))
sys.path[:0] = [str(R4 / "gen"), str(pathlib.Path(MAIN) / "tools/usse-asm")]
(R4 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R4 / "debug/tmp")
import probe  # noqa: E402
import r4loops as L  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


HARNESS = R4 / "debug/target/debug/simcheck"
if not HARNESS.exists():
    env = dict(os.environ, CARGO_TARGET_DIR=str(R4 / "debug/target"))
    r = subprocess.run(["cargo", "build", "--offline", "--manifest-path", str(R4 / "debug/simcheck/Cargo.toml")], env=env, capture_output=True, text=True)
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


# ---- every staged loop program, rebuilt from the generator and run in the simulator at the code indices of its slot
used = {m for t_ in (R4 / "tables").glob("*.txt") for m in re.findall(r"\$S/((?:v)?loop-[\w-]+)\.bin", t_.read_text())}
bins = sorted((R4 / "bins").glob("loop-*.bin")) + sorted((R4 / "bins").glob("vloop-*.bin"))
bad, nbin, kinds = [], 0, {}
for f in bins:
    nbin += 1
    name = f.stem
    m = re.fullmatch(r"loop-rel-(ld0)-k(\d+)", name) or re.fullmatch(r"loop-rel-(ldo)-k(\d+)-m(\d+)", name)
    if m:
        k = int(m[2])
        mm = int(m[3]) if m[1] == "ldo" else None
        nm, text, info = L.pixel_load_source(k, mm)
        kinds[m[1]] = kinds.get(m[1], 0) + 1
        runf = asm(text.replace("0x5CAF0000", "0x3E003000"), nm)
        same = asm(text, nm).read_bytes() == f.read_bytes()
        for ci in (0, 0x20, 0x1020):
            status, o = sim(runf, ci, True)
            if not status.startswith("ended") or o.get("o0") != info["mark"] or int(status.split()[1]) != info["steps"]:
                bad.append((f.name, hex(ci), status, hex(o.get("o0", 0)), info["steps"]))
        if not same:
            bad.append((f.name, "bytes differ from the generator"))
        continue
    m = re.fullmatch(r"loop-rel-(\w+?)-i(\d+)", name)
    if m:
        kind, n = m[1], int(m[2])
        nm, text, info = L.pixel_loop_source(kind, n)
        kinds[kind] = kinds.get(kind, 0) + 1
        runf = asm(text.replace("0x5CAF0000", "0x3E003000"), nm) if kind == "ld8" else f
        same = asm(text, nm).read_bytes() == f.read_bytes()
        for ci in (0, 0x20, 0x1020):
            status, o = sim(runf, ci, True)
            if not status.startswith("ended") or o.get("o0") != (0xC0DE0000 | n) or int(status.split()[1]) != info["prologue"] + info["body"] * n + 1:
                bad.append((f.name, hex(ci), status, hex(o.get("o0", 0))))
        if not same:
            bad.append((f.name, "bytes differ from the generator"))
        continue
    m = re.fullmatch(r"vloop-(\w+?)-i(\d+)", name)
    kind, n = m[1], int(m[2])
    nm, text = L.vertex_loop_source(kind, n)
    kinds[kind] = kinds.get(kind, 0) + 1
    same = asm(text, nm).read_bytes() == f.read_bytes()
    steps = set()
    for ci in (0, 0x40, 0x41, 0x1040):
        status, o = sim(f, ci, False)
        steps.add(status)
        if not status.startswith("ended") or o.get("o2") != 0x3e800000 + 4 * n or o.get("o0") != 0x3f000000:
            bad.append((f.name, hex(ci), status, hex(o.get("o2", 0))))
    if len(steps) != 1:
        bad.append((f.name, "step count depends on the code index", steps))
    if not same:
        bad.append((f.name, "bytes differ from the generator"))
check(f"every staged loop program ({nbin} in bins/, kinds {dict(sorted(kinds.items()))}) equals the generator's output and ends in sgx-sim at every "
      "code index of its slot with the MARK / the depth z = 0x3e800000 + 4N, in the generator's step count", nbin == len(used) and not bad, str(bad[:3]))
check("the table-staged loop programs are exactly those in bins/ (no unused, no missing)", used == {f.stem for f in bins}, str(used ^ {f.stem for f in bins}))

# ---- body step counts: the vertex bodies are 8 (b8v), 13 (b12v) and 2 (b2v) instructions an iteration
per = {}
for kind in ("b8v", "b12v", "b2v", "b16v", "b4v"):
    s = {}
    for n in (1, 3):
        f = asm(L.vertex_loop_source(kind, n)[1], f"{kind}{n}")
        s[n] = int(sim(f, 0x40, False)[0].split()[1])
    per[kind] = (s[3] - s[1]) / 2
check("the vertex bodies are 8, 13 and 2 instructions an iteration (b8v, b12v, b2v; b16v 16 and b4v 4 as round 3)",
      per == {"b8v": 8, "b12v": 13, "b2v": 2, "b16v": 16, "b4v": 4}, str(per))
# b2v: the depth proof is the counter reaching zero: a program whose counter ended elsewhere changes o2
text = L.vertex_loop_source("b2v", 7)[1]
broken = text.replace("p1 br -#0x00000001", "nop.nosched")        # no branch: the counter ends at N - 1, not 0: the proof word must differ
f = asm(broken, "b2v-broken")
st, o = sim(f, 0x40, False)
check("b2v: a counter that did not end at 0 changes o2 (the stored depth word is then not 0x3f200000 + N)", o.get("o2") != 0x3e800000 + 4 * 7, f"{st} {o}")
f = asm(L.vertex_loop_source("b2v", 7)[1], "b2v7")
st, o = sim(f, 0x40, False)
check("b2v: the second phas names the right index and the br is -#1", "phas #14" in text and "p1 br -#0x00000001" in text and o.get("o2") == 0x3e800000 + 28, st)
for kind, nimae in (("b12v", 10), ("b8v", 5)):
    t = L.vertex_loop_source(kind, 5)[1]
    code = "\n".join(re.sub(r";.*$", "", ln) for ln in t.splitlines())
    check(f"{kind}: {nimae} imae in the body, a relative p1 br, no ba", len(re.findall(r"^\s*imae", code, re.M)) == nimae and "p1 br -#" in code and not re.search(r"\bba\b", code))
# ---- relative branches of ld0 / ldo
tx = L.pixel_load_source(28)[1]
check("ld0 closes its loop with p0 br -#7 (inner) and carries ONE load", tx.count("ldad") == 1 and "p0 br -#0x00000007" in tx and "p1 br" not in tx)
tx = L.pixel_load_source(28, 4)[1]
check("ldo carries p0 br -#7 (inner), p1 br -#12 (outer), one load in the outer body, and the or of both counters before the proof",
      "p0 br -#0x00000007" in tx and "p1 br -#0x0000000c" in tx and tx.count("ldad") == 1 and "or.skipinv r1, r1, r20" in tx)
bad_ba = []
for f in bins:
    m = re.fullmatch(r"loop-rel-(ld0)-k(\d+)", f.stem) or re.fullmatch(r"loop-rel-(ldo)-k(\d+)-m(\d+)", f.stem)
    if m:
        txt = L.pixel_load_source(int(m[2]), int(m[3]) if m[1] == "ldo" else None)[1]
        try:
            L.assert_no_ba(txt, "a --tri slot")
        except L.LoopError:
            bad_ba.append(f.name)
check("no staged load loop carries an absolute `ba` (E770's mechanism)", not bad_ba, str(bad_ba))
# marks of the new programs are distinct from every R3 mark and from each other
marks = {L.load_mark(k) for k in (28, 53, 70, 110)} | {L.load_mark(k, m) for k, m in ((28, 4), (28, 16), (40, 8), (70, 1), (70, 4), (110, 2), (220, 1))}
staged_n = {int(m[1]) for f in bins if (m := re.fullmatch(r"loop-rel-(?:b8|ld8)-i(\d+)", f.stem))}
check("the 11 load-loop marks are distinct and none equals a b8 / ld8 mark of the tables", len(marks) == 11 and not marks & {L.mark(n) for n in staged_n})
sys.exit(0 if ok else 1)
