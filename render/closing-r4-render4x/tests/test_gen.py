#!/usr/bin/env python3
"""tests/test_gen.py: the generated tables and predictions of R4-G against the kept records they came from, the page model against E824's
dumps, the cube builder against E726's published programs, the insertion finder against E728's real pairs.  Prints `ok ...` and
`FAIL ...` lines; exit 1 on any FAIL."""
import gzip
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import cubegen as C  # noqa: E402
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import score_r as S  # noqa: E402
import worlds as WD  # noqa: E402

bad = 0


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


def rows(stage):
    return WD.table(stage)


# ---- the generator is reproducible ---------------------------------------------------------------------------------------------------
r = subprocess.run([sys.executable, os.path.join(KP, "gen", "rgen.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0 and "checked:" in r.stdout, "gen/rgen.py --check regenerates every table, prediction, program and TABLES.md byte for byte (%s)" % r.stdout.strip()[:80])

# ---- the tables ------------------------------------------------------------------------------------------------------------------------
want = {"s0": 3, "c": 3, "p": 6, "o": 8, "t": 7, "h": 4}
for st, n in want.items():
    check(len(rows(st)) == n, "stage %s has %d rows" % (st, n))
check(sum(want.values()) == 31, "31 table rows; plan counts: S0 3, P 6, O 8, T 6 (+1: t4b, the point baseline), H 4 cells (about 16 runs), plus the Q113 row c (3)")
KNOB = re.compile(r"^(-|expectdiff|stophang|rgn:1|held|dumpheld|strict|pb:0x[0-9a-f]{2,3}|hypo:[a-z0-9]+:[0-9]+|needs:[a-z0-9-]+=(fault|ok)|cell:(ctx|fill|health))$")
for st in want:
    for rw in rows(st):
        ks = rw["knobs"].split()
        if not all(KNOB.match(k) for k in ks):
            check(False, "%s: knobs %s are not allowed" % (rw["name"], ks))
        if rw["args"].startswith("tri "):
            if "expectdiff" not in ks or "--keep-going" not in rw["args"]:
                check(False, "%s: a tri row needs expectdiff and --keep-going" % rw["name"])
        for m in re.finditer(r"pb:(0x[0-9a-f]+)", rw["knobs"]):
            if not (0x23 <= int(m.group(1), 16) <= 0x422):
                check(False, "%s: pb value %s outside 0x23..0x422" % (rw["name"], m.group(1)))
check(True, "every knob of every row is on the allowed list; every tri row has expectdiff and --keep-going; every pb value is in 0x23..0x422")
names = [rw["name"] for st in want for rw in rows(st)]
check(len(names) == len(set(names)), "row names are unique")
o = rows("o")
check([x["name"] for x in o][-1].startswith("o8"), "o8 (1x 4096 x 4096) is the last row of stage o (decision 5a)")
check(open(os.path.join(KP, "stages.txt")).read().split() == ["s0", "c", "p", "o", "t", "h"], "stage order s0, c, p, o, t, h: stage h (the TA write faults) is last")
check(any("needs:o5" in x["knobs"] and x["name"].startswith("o6") for x in o), "o6 runs only if o5 faults (needs:o5...=fault)")
h = rows("h")
check(len(h) == 4 and all("cell:" in x["knobs"] and "held" in x["knobs"] and "rgn:1" in x["knobs"] for x in h), "stage h: four held cells at render_rgn_arrays 1, no --aa4")
check(all("--aa4" not in x["args"] for x in h), "no cell runs with --aa4 (the c1 shape faults only on one array)")
check(all("--aa4" in x["args"] for x in rows("p")), "stage p rows run on four-array contexts (--aa4)")
for st in ("s0", "p", "o"):
    for x in rows(st):
        w, hh, mw, mh = WD.dims(x["args"])
        if (mw, mh) != (w, hh):
            check(False, "%s: --max-width/--max-height differ from the size" % x["name"])
check(True, "every size row has --max-width/--max-height equal to its size")

# ---- the page model, fitted on E824's ten dumps -----------------------------------------------------------------------------------------
fit = [ln.split("\t") for ln in open(os.path.join(KP, "gen", "data", "pbfit.tsv")).read().splitlines()[1:]]
check(len(fit) == 10 and all(int(f[3]) == int(f[5]) and int(f[4]) == int(f[6]) and int(f[7]) == int(f[8]) for f in fit),
      "the page model reproduces E824's ten dumps: scene pages = U4, non-zero pages = U4 + 3 (the rank's ceil(tiles32/8) + 4) and the TA data size, 10 of 10 [post hoc fit]")
for st in ("p",):
    P = L.load_predictions(st + ".tsv")
    for x in rows(st):
        w, hh, _, _ = WD.dims(x["args"])
        u = int(L.pred(P, x["name"], "pb_used"))
        check(u == M.u4(w, hh) and M.u4_rank(w, hh) == u + 3 and u + M.PB_FIXED_RESERVE <= M.PB_PAGES, "%s: U4 %d (rank form %d), %d usable" % (x["name"], u, M.u4_rank(w, hh), M.usable(M.PB_PAGES)))
        check(int(L.pred(P, x["name"], "tadata_size")) == M.tadata_4x(w, hh), "%s: TA data 0x%x from the layout formula" % (x["name"], M.tadata_4x(w, hh)))
check(sorted(M.u4(w, h) for w, h in [(4096, 960), (960, 4096), (2048, 1920), (3072, 1280)]) == [961] * 4,
      "four of the six sizes need 961 pages (63 to spare): a width or height limit would fail 4096 x 960 and 960 x 4096 while the page need passes")
check(M.u4(2048, 2048) == 1025 and M.overflows(M.u4(2048, 2048), M.PB_PAGES) and M.u4(4096, 4096) == 4097 and M.u1(4096, 4096) == 2049,
      "j4's scene: U4 4097 against 1024 usable (3073 over); at 1x 2049 [model]; 2048 x 2048 is one page over")
check(M.usable(0x83) == M.u1(1024, 768) == 97 and M.usable(0x82) == 96 and M.usable(0xe3) == M.u4(1024, 768) == 193 and M.usable(0xe2) == 192,
      "o1/o2 and o3/o4 are boundary pairs one page apart (97 / 96 at 1x, 193 / 192 at 4x)")
check(M.overflows(M.u4(288, 144), 0x23) and M.overflows(M.u4(4096, 1152), 0x422) and M.overflows(M.u1(4096, 4096), 0x422), "o5, o7 and o8 all overflow by the rule")

# ---- values come from the kept records ------------------------------------------------------------------------------------------------
Ps = L.load_predictions("s0.tsv")
check(L.pred(Ps, "s0-1x-1024x768", "target_hash") == "0xc9e301d225fe2325" and L.pred(Ps, "s0-4x-288x144", "target_hash") == "0x4a61860dcb4ab325"
      and L.pred(Ps, "s0-4x-1024x768", "target_hash") == "0xde0b9233c9822325", "s0 hashes are the plan's (E827/E828, E828 j1r, E824 h8)")
check(L.pred(Ps, "s0-4x-288x144", "tadata_size") == "32768" and L.pred(Ps, "s0-4x-1024x768", "tadata_size") == "122880", "s0 TA data 0x8000 and 0x1e000")
check(L.pred(Ps, "s0-4x-288x144", "pb_used") == "12" and L.pred(Ps, "s0-4x-1024x768", "pb_used") == "193", "s0 PB pages 12 and 193")
c1 = open(os.path.join(KP, "..", "render4x", "c1.snap1.txt")).read()
check(L.reg(c1, 0x0724) == "0x000b000b" and L.pred(Ps, "s0-4x-288x144", "reg0724") == "0x000b000b", "reg 0x0724 reading of K2's held c1 is 0x000b000b = U4 - 1 in both halves")
Pt = L.load_predictions("t.tsv")
e40 = L.read_bytes(L.REG + "/pb-e40-m2-64a.tri.param.bin.gz")
check(L.pred(Pt, "t6-ctl-te40-1array", "par_0_64") == L.words(e40, 0, 64) and L.pred(Pt, "t6-ctl-te40-1array", "target_hash") == "0xfc5ff15e0434a325",
      "t6's frozen words and hash are E827's pb-e40-m2-64a")
for case, par in (("t3b-line-base", L.LINE + "/ln-ctl64-r1.param.bin.gz"), ("t4b-point-base", L.POINT + "/pp-c-s1.param.bin.gz")):
    b = L.read_bytes(par)
    check(L.pred(Pt, case, "par_0_32") == L.words(b, 0, 32), "%s: the frozen head is the 11.31 dump's" % case)
for case, par in (("t3-line-te40", L.LINE + "/ln-ctl64-r1.param.bin.gz"), ("t4-point-te40", L.POINT + "/pp-c-s1.param.bin.gz")):
    w = L.dwords(L.read_bytes(par))
    check(int(L.pred(Pt, case, "insert_pos")) == w.index(0x00040101), "%s: the predicted insertion is right before the first format word (dword %d)" % (case, w.index(0x00040101)))

# ---- stage h: the job words against the layout formula ----------------------------------------------------------------------------------
Ph = L.load_predictions("h.tsv")
for case, w, hh in (("h1-288x144-health", 288, 144), ("h2-640x480-health", 640, 480), ("h3-288x144-ctx", 288, 144), ("h4-288x144-fill", 288, 144)):
    td = M.layout(w, hh, 1)[3]
    page = 0x20000 + td // 4096
    word = int(L.pred(Ph, case, "job_word"), 16)
    check(word >> 12 == page, "%s: the job's fault page 0x%x is the end of the one-array TA data (0x%x bytes: %s)" % (case, word >> 12, td, "c1 and f2 are in the fit, 640 x 480 is E507's page"))
hl = M.layout(64, 64, 1)[3]
check(0x20000 + hl // 4096 == 0x20006, "the health context (64 x 64, one array) has its TA data end at page 0x20006 (K2's reading of 1.2)")

# ---- the cube programs ------------------------------------------------------------------------------------------------------------------
tpl = L.read_text(L.DATA + "/texture/p1141/templates/tx_map.s")
import tomllib  # noqa: E402
toml = tomllib.load(open(L.DATA + "/texture/p1141/probes/p1141-cube.toml", "rb"))["probe"][0]
asm = L.MAIN + "/tools/usse-asm/usse-asm"
okb = True
for i, nm in enumerate(["cu-zp", "cu-xp", "cu-yp", "cu-zn", "cu-xn", "cu-yn"]):
    spec = C.E726[nm]
    same_text = C.setup_text(*spec) == toml["cases"][C.E726_BIN[nm]][1]
    data = C.assemble(asm, C.program_text(tpl, *spec), os.path.join(KP, "debug", "asm-test.bin"))
    pub = L.read_bytes(L.DATA + "/texture/p1141/stage-bins/p1141-cube__%d.bin" % C.E726_BIN[nm])
    okb &= same_text and data == pub
check(okb, "the cube builder rebuilds E726's six axis programs: the setup text and the assembled bytes equal the published ones")
import numpy as np  # noqa: E402
allok = True
for nm, spec in list(C.E726.items()) + [("cu-w02", C.W02), ("cu-w11", C.W11)]:
    f, _ = C.faces(*spec)
    o = C.observed(L.read_text(L.CUBE + "/%s.txt.gz" % nm))
    allok &= bool((f == o).all())
check(allok, "the face rule reproduces E726's 8 jobs, 2048 of 2048 pixels each (the fit set)")
tot = np.zeros(6, int)
for nm, spec in C.HELDOUT.items():
    f, g = C.faces(*spec)
    tot += C.hist(f)
    check(float(g.min()) >= 0.0078, "%s: no pixel within 0.0078 of a tie (smallest gap %.5f), faces %s" % (nm, float(g.min()), C.hist(f)))
    cs = C.coords(*spec)
    check(((np.stack(cs) == 0).sum(0) <= 1).all() and all((np.abs(c) > 0).any() for c in cs),
          "%s: no pixel lies on an axis (at most one coordinate is zero in any pixel: the ramps cross zero, the constant never does)" % nm)
    check(len(set(np.argmax(np.stack([np.abs(c) for c in cs]), 0))) >= 2, "%s: the dominant axis changes inside the image" % nm)
check((tot > 0).all(), "the two held-out jobs together read all six faces (%s)" % tot.tolist())
for nm in C.HELDOUT:
    b = L.read_bytes(os.path.join(KP, "bins", nm + ".bin"))
    check(b is not None and len(b) == 176, "bins/%s.bin: 176 bytes like the published cube programs" % nm)
check(L.read_bytes(os.path.join(KP, "bins", "p1141-cube__4.bin")) == L.read_bytes(L.DATA + "/texture/p1141/stage-bins/p1141-cube__4.bin"), "bins/p1141-cube__4.bin is E726's cu-xn program, byte for byte")
old = "/Users/jtorra/src/sgxhumation/debug/wt-phase10/debug/phase11/p1131/stage-bins/"
if os.path.isdir(old):
    check(L.read_bytes(os.path.join(KP, "bins", "p1131-green__0.bin")) == L.read_bytes(old + "p1131-green__0.bin")
          and L.read_bytes(os.path.join(KP, "bins", "p1131-psizes__1.bin")) == L.read_bytes(old + "p1131-psizes__1.bin"),
          "the line and point programs rebuilt from resgx545 probes/ta equal the ones the 11.31 session ran, byte for byte")

# ---- the insertion finder on real pairs ---------------------------------------------------------------------------------------------------
def rg(n):
    return L.dwords(L.read_bytes(L.REG + "/%s.tri.param.bin.gz" % n))


check(S.insertion(rg("pb-e20-m2-64"), rg("pb-e40-m2-64a")) == (11, 0), "insertion(): E827's pb-e20 -> pb-e40 pair: one zero dword at 11")
check(S.insertion(rg("pb-e20-m2-64"), rg("pb-e80-m2-64")) == (11, 0), "insertion(): pb-e20 -> pb-e80: one zero dword at 11")
check(S.insertion(rg("pb-e20-m2-64"), rg("pb-e20-m2-64")) is None, "insertion(): equal dumps have no insertion")
ln = L.dwords(L.read_bytes(L.LINE + "/ln-ctl64-r1.param.bin.gz"))
check(S.insertion(ln, ln[:9] + [0x2] + ln[9:]) == (9, 2) and S.insertion(ln, ln[:3] + [0] + ln[3:]) == (3, 0), "insertion(): synthetic insertions at 9 and 3 are found with their values")
check(S.insertion(ln, ln[:9] + [0x2, 0x3] + ln[9:]) is None, "insertion(): two inserted dwords are not one")

print("ALL gen tests: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(bad)
