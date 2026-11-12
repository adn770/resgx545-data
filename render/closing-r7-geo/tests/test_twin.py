#!/usr/bin/env python3
"""test_twin.py: the argv-twin test (round 4's slip: a row's command that is not its plan row).  Every row of every table is parsed
back (tool, command, size, triangle, depth recipe, unit, program, knobs) and compared with the plan typed here by hand from
closing7/rank/rank-round7.md R7-2..R7-5 (DECISIONS-R7 R7-2 a); every control is its record's own kept command token for token
(E884: r6-misc's q289 table row; E606: run/run_p1138.py's build_cmd of the dataset, imported; E680, E681, E683: the dataset's
jobs.tsv command less --pixels-rle)."""
import importlib.util
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402

D = "/Users/jtorra/src/resgx545-data"
bad = n = 0


def check(c, what):
    global bad, n
    n += 1
    print(("ok   " if c else "FAIL ") + what)
    bad += 0 if c else 1


def rows(st):
    out = []
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            name, sset, risk, knobs, tool, args = ln.split("|", 5)
            out.append(dict(name=name, set=sset, knobs=knobs.split(), tool=tool, args=args, a=shlex.split(args)))
    return out


def o(r, k, cast=str):
    return cast(r["a"][r["a"].index(k) + 1]) if k in r["a"] else None


spec = importlib.util.spec_from_file_location("run_p1138", os.path.join(D, "isp/arith-1138/run/run_p1138.py"))
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)
E606 = {c["id"]: c for c in RP.load_cases(os.path.join(D, "isp/arith-1138/cases.tsv"))}
JOBS = {ln.split("\t")[0]: ln.rstrip("\n").split("\t")[6].split()[1:] for ln in open(os.path.join(D, "isp/coverage-envelope/main/jobs.tsv"))}

# ---- xf: R7-5, 8 both-axes fills at 128 x 64 + E884's 128 x 64 x ^ 0x10 control (+ the baseline)
R = rows("xf")
r6 = {ln.split("|")[0]: ln.rstrip("\n").split("|", 5)[5] for ln in open(os.path.join(D, "render/closing-r6-misc/tables/q289.txt")) if not ln.startswith("#")}
check(len(R) == 10 and all(r["tool"] == "t4" and r["a"][0] == "fill" and (o(r, "--width", int), o(r, "--height", int), o(r, "--stride", int)) == (128, 64, 512)
                           for r in R), "xf: 10 fills, t4, 128 x 64, stride 512")
check(R[0]["args"] == r6["f-128x64-x10"] and R[1]["args"] == r6["f-base-128x64"], "xf: the controls are r6-misc's (E884's) rows token for token")
both = [M.split_poke(int(o(r, "--poke").split("^=")[1], 16)) for r in R[2:]]
check(len(both) == 8 and all(fx > 0 and fy > 0 for fx, fy in both) and len(set(both)) == 8, "xf: 8 distinct pokes moving both fields")

# ---- tx: R7-4
R = rows("tx")
plan = [("ctl", 3, 32, 16)] + [(None, t, w, h) for t in (1, 3, 4) for w, h in ((4, 16), (64, 8), (128, 8))] + [(None, 4, 64, 32), (None, 4, 128, 32)] + \
    [(None, 5, 16, 16), (None, 5, 8, 8), (None, 5, 32, 32), (None, 5, 64, 64), ("zero", 5, 16, 16), ("ones", 5, 16, 16)]
sys.path.insert(0, HERE)
import worlds as WD  # noqa: E402
got = []
for r in R:
    t1 = WD.t1_of(os.path.join(KP, "bins", r["a"][-1].split("/")[-1]))
    got.append((t1 >> 29, ((t1 >> 12) & 0xFFF) + 1, (t1 & 0xFFF) + 1))
check(len(R) == 18 and got == [(t, w, h) for _, t, w, h in plan], "tx: the 18 programs load the plan's T1 (type, width, height) in order (read back by the disassembler)")
check(all(r["tool"] == "t4" and r["a"][:4] == ["probe", "--temps", "32", "--coords"] and "after" in r["knobs"] for r in R), "tx: probes on t4 with a health check after each")
dis = {r["name"]: os.popen("%s %s" % (WD.DIS, os.path.join(KP, "bins", r["a"][-1].split("/")[-1]))).read() for r in R}
check(dis["tx-ty5-16x16-zero"].count("stad") == 112 and dis["tx-ty5-16x16-ones"].count("#0xFFFFFFFF") == 112 and dis["tx-ty5-16x16"].count("stad") == 0,
      "tx: the memory controls store 112 dwords (0, all ones) before the sample; the plain program stores none")

# ---- zd: R7-2 (a) Q262 depth
R = rows("zd")
for r in R[:2]:
    cid = int(r["name"].split("-")[-1]) if False else None
c412 = RP.build_cmd("D", E606[412], "T", "B", "$W/depth", mock=True)[2:]
c1206 = RP.build_cmd("D", E606[1206], "T", "B", "$W/depth", mock=True)[2:]
check(R[0]["a"] == c412 and R[1]["a"] == c1206, "zd: the controls are E606's D commands of cases 412 and 1206 token for token (run_p1138.build_cmd)")
sizes = [(512, 256), (640, 480), (1024, 768), (2048, 1024)]
plan = [(w, h, c) for w, h in sizes for c in "s" * 12 + "m" * 12] + [(4096, 4096, c) for c in "smsm"]
got = [(o(r, "--width", int), o(r, "--height", int), r["name"].split("-")[2]) for r in R[2:]]
check(got == plan, "zd: 12 small + 12 medium at 512 x 256, 640 x 480, 1024 x 768, 2048 x 1024, then 4 at 4096 x 4096")
okr = all(r["tool"] == "t4" and o(r, "--depth-ctl") == "0x%x" % M.G.depth_ctl(o(r, "--width", int)) and o(r, "--depth-pages", int) == M.G.depth_pages(o(r, "--width", int), o(r, "--height", int))
          and o(r, "--depth-fill") == "0xdeadbeef" and o(r, "--depth-dump") == "$W/depth" and o(r, "--poke") == "blk:1=0x00400200" and "--tri-unit" not in r["a"]
          and ("--pixels" in r["a"]) == (o(r, "--width", int) == 512) and ("soft" in r["knobs"]) == (o(r, "--width", int) == 4096) for r in R[2:])
check(okr, "zd: E606's depth recipe (pitch, pages, fill, dump, blk poke), 1/256 vertices, --pixels at 512 x 256 only, soft at 4096 only")

# ---- zi
R = rows("zi")
ci = RP.build_cmd("I0", E606[1016], "T", "$S", "$W/depth", mock=True)[2:]
check(R[0]["a"] == ci, "zi: the control is E606's I0 command of case 1016 token for token")
check(R[1]["a"] == JOBS["1400246"][:-1] and JOBS["1400246"][-1] == "--pixels-rle", "zi: E680's 1024 x 768 case 1 command less --pixels-rle")
got = [(o(r, "--width", int), o(r, "--height", int)) for r in R[2:]]
check(got == [s for s in sizes for _ in range(6)] and all(r["a"][:3] == ["probe", "--tri", "pixpds:12"] and r["a"][-1] == "$S/p1138-it-a0__0.bin" for r in R[2:])
      and all(("soft" in r["knobs"]) == (o(r, "--width", int) >= 1024) for r in R[2:]), "zi: 6 I0 probes a size, the iteration program, soft from 1024 x 768")

# ---- zf: R7-2 (a) Q240
R = rows("zf")
check(R[0]["a"] == RP.build_cmd("D", E606[262], "T", "B", "$W/depth", mock=True)[2:] and R[1]["a"] == RP.build_cmd("D", E606[926], "T", "B", "$W/depth", mock=True)[2:],
      "zf: the controls are E606's D commands of cases 262 and 926")
fam = [(64, 128), (128, 64), (256, 64), (128, 96), (128, 144), (32, 16), (16, 8), (4096, 16), (64, 33), (96, 47)]
got = [(o(r, "--width", int), o(r, "--height", int)) for r in R[2:]]
check(got == [s for s in fam for _ in range(24)], "zf: 24 rows at each of the ten family sizes, in the plan's order")
check(all((r["tool"] == "t6") == (o(r, "--height", int) % 2 == 1) for r in R), "zf: t6 exactly on the odd heights (64 x 33, 96 x 47)")
gates = [r["name"] for r in R if "gate" in r["knobs"]]
check(gates == ["zf-32x16-s-00", "zf-16x8-s-00", "zf-64x33-s-00", "zf-96x47-s-00"], "zf: a gate row first in 32 x 16, 16 x 8 and the odd heights")
check(all("--pixels" in r["a"] and o(r, "--depth-pages", int) == M.G.depth_pages(o(r, "--width", int), o(r, "--height", int)) for r in R), "zf: --pixels and the pitch rule's pages everywhere")

# ---- zs: R7-3, decision 4 (a)
R = rows("zs")
for r, cid in zip(R[:2], ("1400606", "1401234")):
    check(r["a"] == JOBS[cid][:-1] + ["--pixels"], "zs: control %s is the record's command with --pixels for --pixels-rle" % cid)
sw = R[2:2 + 6 * 2 * 17]
okw = len(sw) == 204
for k, r in enumerate(sw):
    pos = M.POSITIONS[k // 34]
    ax = "xy"[(k // 17) % 2]
    d = k % 17 - 8
    v = [int(x) for x in o(r, "--tri-v").split(",")]
    p = (M.SW if ax == "x" else M.SH) + 0.5 if pos == "far" else pos
    okw = okw and v[0 if ax == "x" else 1] == int(round(p * 4096)) + 8 + d and o(r, "--tri-unit") == "12" and (o(r, "--width", int), o(r, "--height", int)) == (512, 256)
    okw = okw and sum(1 for x in v if x % 16) == (0 if d in (-8, 8) else 1)
    want = "fit" if (pos, ax) == (-0.5, "x") else ("control" if (pos, ax) == (0.5, "x") else ("mirror" if pos in (0.5, 64.5) else "heldout"))
    okw = okw and r["set"] == want
check(okw, "zs: 6 positions x 2 axes x 17 steps of 1/4096 across the tie, the swept coordinate the plan's, every other coordinate on the grid, sets as planned")
nt = R[206:]
check(len(nt) == 24 and all(sum(1 for x in [int(t) for t in o(r, "--tri-v").split(",")] if x % 16) == 1 for r in nt)
      and all(min(int(t) for t in o(r, "--tri-v").split(",")) < 0 for r in nt), "zs: 24 cases with exactly one off-grid coordinate, negative")
print("%d of %d twin checks" % (n - bad, n))
sys.exit(1 if bad else 0)
