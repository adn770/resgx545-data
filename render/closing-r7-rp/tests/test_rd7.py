#!/usr/bin/env python3
"""test_rd7.py: offline tests of stages p7-rdc and p7-rd (r7-rp, Q276; plan closing7/a/exp-pixel-r7.md 1.4, 2.3, 3.4).  A script,
not pytest: prints ok / FAIL lines, exits 1 on any FAIL.   PY tests/test_rd7.py
  1. argv twin: every table row parsed back (tool, size, triangle, slots, block word, program) against the plan's rows TYPED HERE;
     R6's rows byte for byte R6's args; bins pinned; every new program read back from its BYTES (sgx-sim's decode, R6's simcheck
     build) against its plan row and run in sgx-sim; the copied programs/score modules are R6's.
  2. real-tool mock: every row through tests/realmock.py (t4, 4623753 --mock) completes, prints 64 pixel rows and writes the two
     dump files the scorer does not read; a missing dump directory is refused as the world refuses it.
  3. replay before the freeze: score_rd7 on R6's kept p6-rd (the FIT set) under its REAL kept names, mapped explicitly to this
     session's rows: the gate passes (E878), the vector is S S S A0 A4 A4 A4 (H-MOD4) and every own-source count equals
     fold/posthoc_r6.txt section A; a doctored rd-5 (o5's own word) does not read H-MOD4; a rival class above 0.02 cannot tell; a
     renamed file is cannot tell and named missing; R6's original 0.90 rule cannot decide (E878's slip).
  4. every control's scorer on a doctored input fails the gate; refuse_unreadable passes and refuses an unreadable control.
  5. the world: kept directories built from tests/world_rd.py through the runner's naming give the frozen verdict for `model` and
     the rival verdicts (hstore, gatefail, o4none, noall4, norep, rival, fault); the scorer reads only REQUIRED files."""
import ast
import gzip
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score"), os.path.join(KP, "gen")]
import g_rd  # noqa: E402
import rd_r4lib as L  # noqa: E402
import rd_score_rd as SR  # noqa: E402
import realmock  # noqa: E402
import score_rd7 as S  # noqa: E402
import scorekit  # noqa: E402
import sessioncheck  # noqa: E402
import world_rd as W  # noqa: E402

R6 = "/Users/jtorra/src/scratch/resgx545/closing6/r6-pixel"
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
R6K = DATA + "/render/closing-r6-pixel/out/20261112-142113/p6-rd"
SIM = R6 + "/debug/target/debug/simcheck"
TMP = tempfile.mkdtemp(prefix="rd7-", dir=os.path.join(KP, "debug"))
HDR = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info and not cond else ""))
    ok &= bool(cond)


def table(stage):
    rows, head = [], []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines():
        (head if ln.startswith("#") else rows).append(ln.split("|", 5) if not ln.startswith("#") else ln)
    return head, rows


# ============================================================================================ 1. argv twin, typed from the plan
TAG = {i: i + 1 for i in range(8)}
PLAN = {   # plan 3.4, typed by hand: (row config, set, program stem)
    "p7-rdc": [("c-e709", "control", "r4o-e709"), ("c-u", "control", "r4o-u"), ("c-all4", "control", "r5o-c-all4"),
               ("c-ow", "control", "r6o-c-ow"), ("c-rd-0", "control", "r6o-c-rd-0"), ("c-prd-0-k1", "control", "r6o-c-prd-0-k1"),
               ("c-prd-0-k7", "control", "r6o-c-prd-0-k7")],
    "p7-rd": [(f"rd-{j}", "replicate", f"r6o-rd-{j}") for j in range(1, 8)]
    + [("n-rd-4", "replicate", "r6o-n-rd-4"), ("x-rd-4", "replicate", "r6o-x-rd-4"),
       ("x-rd-6", "heldout", "r7o-x-rd-6"), ("x-rd-7", "heldout", "r7o-x-rd-7"), ("n-rd-5", "heldout", "r7o-n-rd-5")]
    + [(f"cl-{j}", "heldout", f"r7o-cl-{j}") for j in (4, 5, 6, 7)] + [("cl-p4", "heldout", "r7o-cl-p4")],
}
JOBS = {"p7-rdc": 14, "p7-rd": 34}
r6args = {}
for ln in open(R6 + "/tables/p6-rd.txt").read().splitlines():
    if ln and not ln.startswith("#"):
        f = ln.split("|", 5)
        r6args[f[0]] = f[5]

for stage in ("p7-rdc", "p7-rd"):
    head, rows = table(stage)
    want = [(f"{c}-{ax}", st, f"{p}-{ax}") for c, st, p in PLAN[stage] for ax in "xy"]
    check(f"{stage}: {JOBS[stage]} jobs, the plan's rows in order", len(rows) == JOBS[stage] and [r[0] for r in rows] == [w[0] for w in want],
          str([r[0] for r in rows]))
    check(f"{stage}: header #stage, #limit 1", head[0] == f"#stage {stage}" and "#limit 1" in head)
    needs = {h.split()[1] for h in head if h.startswith("#need ")}
    bad = []
    for (name, st, prog), r in zip(want, rows):
        n, sset, risk, knobs, tool, args = r
        a = shlex.split(args)
        ok_shape = (a[:4] == ["probe", "--tri", "pixel", "--temps"] and a[4] == "32" and a[5] == "--pixels"
                    and a[6:8] == ["--dump-render", "$W/dump"] and a[8:14] == ["--width", "64", "--height", "64", "--vtx-coords", "2"]
                    and a[14:16] == ["--blk", "4=0x00030001"] and a[16:18] == ["--slot", "pixpds=$S/pds_iter_xy.bin:12"]
                    and a[18:20] == ["--slot", "vtxuse=$S/vtx_coords.bin"] and a[20:] == [f"$S/{prog}.bin"])
        if not (n == name and sset == st and risk == "safe" and knobs == "-" and tool == "t4" and ok_shape):
            bad.append(n)
        if n in r6args and r6args[n] != args:
            bad.append(n + " (not R6's args)")
        for s in re.findall(r"\$S/([A-Za-z0-9_.+-]+)", args):
            if "$S/" + s not in needs or not os.path.exists(os.path.join(KP, "bins", s)):
                bad.append(f"{n} $S/{s} not a #need or not in bins/")
    check(f"{stage}: every row is its plan row (t4, no knob, R6's command: 64x64, 2 coordinates, word 4, the two slots, its program; "
          "R6's rows byte for byte R6's args; every $S file a #need in bins/)", not bad, str(bad[:5]))

pins = dict(reversed(ln.split("  ")) for ln in open(os.path.join(KP, "gen/data/bins-rd.txt")).read().splitlines())
badp = [f for f, h in pins.items() if hashlib.sha256(open(os.path.join(KP, "bins", f), "rb").read()).hexdigest() != h]
r6same = [f for f in pins if not f.startswith("r7o-") and open(os.path.join(KP, "bins", f), "rb").read()
          != open(os.path.join(DATA, "render/closing-r6-pixel/bins", f), "rb").read()]
check("bins: every pinned hash holds; R6's programs equal the published R6 bins byte for byte", not badp and not r6same and len(pins) == 50,
      f"{badp} {r6same} {len(pins)}")


def r6_func_src(name):
    src = open(R6 + "/gen/r6_rd.py").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)


mine = open(os.path.join(KP, "gen/rdprog_rd.py")).read()
check("gen/rdprog_rd.py program() and special() are R6's text (gen/r6_rd.py) unchanged",
      all(r6_func_src(f) and r6_func_src(f) in mine for f in ("program", "special")))


def listing(prog):
    o = subprocess.run([SIM, os.path.join(KP, "bins", prog + ".bin"), "0x20", "--list", "--tri-pixel", "0,0"], capture_output=True,
                       text=True).stdout
    return [ln.split(" ", 2)[2] for ln in o.splitlines() if ln.startswith("insn ")]


def sim(prog, lane):
    x, y = lane & 1, lane >> 1
    o = subprocess.run([SIM, os.path.join(KP, "bins", prog + ".bin"), "0x20", "--tri-pixel", f"{x},{y}", "--set", "pa0=0x11110000",
                        "--set", "pa1=0x22220000"], capture_output=True, text=True).stdout
    return o.splitlines()[0], {int(m[1]): int(m[2], 16) for ln in o.splitlines() if (m := re.fullmatch(r"o(\d+) = (0x[0-9a-f]+)", ln))}


WR = re.compile(r"^(?:(!?p1) )?or\.skipinv(\.end)? o(\d), pa([01]), #0x([0-9A-F]+)$")
NEWW = {  # plan 3.4, typed: the final low-6 word of each written output, the register read, the marker of the x job
    "x-rd-6": ({**{i: TAG[i] | (0x10 if i == 6 else 0x20) for i in range(8)}, 6: 0x1f}, 6, 0x1f0),
    "x-rd-7": ({**{i: TAG[i] | (0x10 if i == 7 else 0x20) for i in range(8)}, 7: 0x10}, 7, 0x1f2),
    "n-rd-5": ({i: TAG[i] | 0x20 for i in range(8) if i != 5}, 5, 0x1f4),
    "cl-4": ({0: 0x21, 4: 0x15}, 4, 0x1f6), "cl-5": ({0: 0x21, 5: 0x16}, 5, 0x1f8),
    "cl-6": ({0: 0x21, 6: 0x17}, 6, 0x1fa), "cl-7": ({0: 0x21, 7: 0x18}, 7, 0x1fc),
}
bad = []
for cfg, (words, j, mx) in NEWW.items():
    for i, ax in enumerate("xy"):
        p = f"r7o-{cfg}-{ax}"
        ins = listing(p)
        w = [(m[1], int(m[3]), int(m[5], 16)) for t in ins if (m := WR.match(t))]
        fin = {o: v & 0x3f for _, o, v in w}
        if fin != words or {v >> 6 for _, _, v in w} != {mx + i} or ins[-2:] != [f"mov.skipinv r10, o{j}", "mov.skipinv.end o0, r10"] \
                or any(p for p, *_ in w) or {m[4] for t in ins if (m := WR.match(t))} != {str(i)}:
            bad.append(p)
        st, o = sim(p, 0)
        if cfg.startswith("n-"):            # the register read is never written: sgx-sim refuses the read (E373: a leftover)
            if f"reads o{j} before the program writes it" not in st:
                bad.append(p + " sim")
        elif not st.startswith("ended") or o.get(0) != o.get(j):
            bad.append(p + " sim")
for i, ax in enumerate("xy"):
    p = f"r7o-cl-p4-{ax}"
    ins = listing(p)
    if ins[1:] != [f"or.skipinv o0, pa{i}, #0x{(0x1fe + i) * 64 + 0x21:08X}", "xor.testtaz.chan0 !c0, p1, g25, #0",
                   f"p1 or.skipinv o4, pa{i}, #0x{(0x1fe + i) * 64 + 0x15:08X}", "mov.skipinv r10, o4", "mov.skipinv.end o0, r10"]:
        bad.append(p)
    st, o = sim(p, 0)
    if not st.startswith("ended") or o[0] & 0x3f != 0x15:
        bad.append(p + " sim lane 0")
    for lane in (1, 2, 3):
        st, o = sim(p, lane)
        if "reads o4 before the program writes it" not in st:
            bad.append(f"{p} sim lane {lane}: {st}")
check("every new program, read from its bytes (sgx-sim decode), is its plan row: x-rd-6 o6 = tag 15 bit 4, x-rd-7 o7 = 0x10, "
      "n-rd-5 no o5, cl-j only o0 = 0x21 and o_j = tag bit 4, markers 0x1f0..0x1ff, then mov r10, oJ; mov.end o0, r10; in sgx-sim "
      "o0 is oJ's word; cl-p4 writes o4 under p1 (g25 == 0) only: lane 0 reads word B, lanes 1..3 read an unwritten o4", not bad, str(bad[:6]))

# ============================================================================================ 2. real-tool mock (t4 4623753)


def mock(args):
    w = tempfile.mkdtemp(prefix="w.rd.", dir=os.path.join(KP, "debug", "realmock") if os.path.isdir(os.path.join(KP, "debug", "realmock"))
                         else TMP)
    os.makedirs(os.path.join(w, "dbgfs"), exist_ok=True)
    # the mock's debugfs has no render_param / render_tadata: every --dump-render probe fails without these two stubs
    open(os.path.join(w, "dbgfs", "render_param"), "wb").write(b"P" * 64)
    open(os.path.join(w, "dbgfs", "render_tadata"), "wb").write(b"T" * 32)
    rc, out, err, kp, w = realmock.run("t4", args, workdir=w)
    dumps = sorted(os.listdir(os.path.join(w, "dump"))) if os.path.isdir(os.path.join(w, "dump")) else []
    shutil.rmtree(w, ignore_errors=True)
    return rc, out, err, dumps


bad = []
for stage in ("p7-rdc", "p7-rd"):
    for r in table(stage)[1]:
        rc, out, err, dumps = mock(r[5])
        prog = shlex.split(r[5])[-1].split("/")[-1][:-4]
        if rc != 0 or len(L.rows_of(out)) != 64 or dumps != [f"{prog}.param.bin", f"{prog}.tadata.bin"]:
            bad.append(f"{r[0]} rc {rc} rows {len(L.rows_of(out))} dumps {dumps} {err[-100:]}")
check("realmock: all 48 rows parse and complete on t4's --mock (rc 0, 64 pixel rows, <prog>.param.bin and .tadata.bin)", not bad, str(bad[:3]))
r = table("p7-rd")[1][0]
rc, out, err, _ = mock(r[5].replace('"$W/dump"', '"$W/nodir"'))
wd = tempfile.mkdtemp(dir=TMP)
wa = W.answer("t4", shlex.split(r[5].replace("$W/dump", wd + "/nodir").replace("$S", os.path.join(KP, "bins"))), {"model"})
check("a missing --dump-render directory: the real tool refuses it (rc 3, `failed: --dump-render: No such file or directory`) and so "
      "does the world", rc == 3 and "failed: --dump-render: No such file or directory" in out and wa["rc"] == 3
      and "failed: --dump-render: No such file or directory" in wa["out"], f"{rc} {wa['rc']}")

# ============================================================================================ 3. replay on R6's kept p6-rd (FIT set)
RDC_MAP = {n: n for n in S.RDC_ROWS}                                     # R6 name -> p7 name (the same row names)
RD_MAP = {f"{c}-{ax}": f"{c}-{ax}" for c in ("rd-1", "rd-2", "rd-3", "rd-4", "rd-5", "rd-6", "rd-7", "n-rd-4", "x-rd-4") for ax in "xy"}
REP_MAP = {**RD_MAP, "rd-4-x-rep": "rd-4-x", "rd-4-y-rep": "rd-4-y"}


def replay(att, rdc_map, rd_map, doctor=None, drop=()):
    """att/p7-rdc and att/p7-rd from R6's kept files: NAME.txt.gz under the p7 name (R6 keeps NAME.txt.gz; its dumps are
    NAME.<prog>.param.bin.gz, which the scorer does not read), cases.tsv in this session's columns."""
    for st, mp in (("p7-rdc", rdc_map), ("p7-rd", rd_map)):
        d = os.path.join(att, st)
        os.makedirs(d)
        lines = [HDR]
        for r6n, n in mp.items():
            src = os.path.join(R6K, r6n + ".txt.gz")
            if n in drop:
                continue
            if doctor and n in doctor:
                g = L.rows_of(gzip.open(src).read().decode())
                g = doctor[n](g)
                txt = "".join(f"probe x: row {y}: " + " ".join(f"{v:08x}" for v in row) + "\n" for y, row in enumerate(g))
                with gzip.open(os.path.join(d, n + ".txt.gz"), "wb") as f:
                    f.write(txt.encode())
            else:
                os.symlink(src, os.path.join(d, n + ".txt.gz"))
            lines.append("\t".join([n, st, "x", "safe", "-", "t4", "probe", "0", "ok", "-", "-", "900000"]))
        open(os.path.join(d, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    return att


def new_att(tag):
    return tempfile.mkdtemp(prefix=f"att-{tag}-", dir=TMP)


att = replay(new_att("fit"), RDC_MAP, RD_MAP)
check("replay p7-rdc on R6's kept controls: gate PASS (E878: c-u 0.990 of 492, c-ow and c-rd-0 1.0 of 1062, c-prd-0 as frozen)",
      S.gate("p7-rdc", att + "/p7-rdc") == 0 and "tag-2 fraction 0.990 of 492" in "\n".join(S.score("p7-rdc", att + "/p7-rdc")[1]))
s, lines, res = S.score_rd(att + "/p7-rd")
check("replay p7-rd: vector S S S A0 A4 A4 A4, H-MOD4 among the fits, every replicate replicated, n-rd-4 and x-rd-4 A0",
      res["vector"] == ("S", "S", "S", "A0", "A4", "A4", "A4") and "H-MOD4" in res["fits"] and not res["notrep"]
      and res["entries"]["n-rd-4"] == "A0" and res["entries"]["x-rd-4"] == "A0", s)
check("replay p7-rd: the held-out and clean rows (not in R6) are cannot tell, not a pass", s.startswith("cannot tell: not decided: x-rd-6"), s)
# the own-source counts against fold/posthoc_r6.txt section A
pa = {}
sec = open(R6 + "/fold/posthoc_r6.txt").read().split("\nB. ")[0]
for ln in sec.splitlines():
    m = re.match(r"^(\S+(?: \(replicate\))?)\s+x .*?of own-source (\d+)/(\d+) = ([\d.]+).*; y .*?of own-source (\d+)/(\d+) = ([\d.]+)", ln)
    if m:
        pa[m[1]] = ((int(m[2]), int(m[3]), m[4]), (int(m[5]), int(m[6]), m[7]))
got, mism = {}, []
for cfg in [f"rd-{j}" for j in range(1, 8)] + ["n-rd-4", "x-rd-4"]:
    r = res["reads"][cfg]
    got[cfg] = tuple((r["owns"][i][r["tops"][i]], r["own"][i], f"{r['shares'][i]:.3f}") for i in range(2))
    if got[cfg] != pa.get(cfg):
        mism.append(f"{cfg} {got[cfg]} vs {pa.get(cfg)}")
shares = [float(x[2]) for v in got.values() for x in v]
check("replay: every own-source count and share equals fold/posthoc_r6.txt section A (9 configurations x 2 jobs), range "
      f"{min(shares):.3f}..{max(shares):.3f}", not mism and len(pa) >= 9 and f"{min(shares):.3f}" == "0.903" and f"{max(shares):.3f}" == "1.000",
      str(mism[:3]))
att2 = replay(new_att("rep"), RDC_MAP, {k: v for k, v in REP_MAP.items() if k not in ("rd-4-x", "rd-4-y")})
s2, _, res2 = S.score_rd(att2 + "/p7-rd")
r = res2["reads"]["rd-4"]
check("replay with R6's replicate (rd-4-x-rep, rd-4-y-rep kept names) as rd-4: A0, counts as posthoc 'rd-4 (replicate)'",
      res2["entries"]["rd-4"] == "A0" and tuple((r["owns"][i][r["tops"][i]], r["own"][i], f"{r['shares'][i]:.3f}") for i in range(2))
      == pa.get("rd-4 (replicate)"), str(pa.get("rd-4 (replicate)")))
# R6's original rule on the same data cannot decide (E878's slip, the reason for the own-source rule)
k = L.Kept(att + "/p7-rd")
preds = S.load("p7-rd")
old = [SR.read_rd(k, preds, f"rd-{j}", res["rdc"]["tri"])["cls"] for j in range(1, 8)]
check("replay: R6's original rule (0.90 of all TRI) decides no rd entry on the same files (E878's frozen cannot tell)", old == [None] * 7, str(old))


def doctor_own(cfg_marker_ax, new6, frac=1.0):
    """A doctor: own-source words carrying the image's top label get low-6 word new6 (a share frac of them, by pixel hash)."""
    m, ax = cfg_marker_ax

    def f(g):
        tri = res["rdc"]["tri"]
        c = {}
        for x, y in tri:
            v = g[y][x]
            if SR.own_label(v, x, y, ax, m)[:1].isdigit():
                c[v & 0x3f] = c.get(v & 0x3f, 0) + 1
        top = max(c, key=c.get)
        for x, y in tri:
            v = g[y][x]
            if SR.own_label(v, x, y, ax, m)[:1].isdigit() and (v & 0x3f) == top and (frac >= 1 or (x * 7 + y * 13) % 100 < frac * 100):
                g[y][x] = (v & ~0x3f) | new6
        return g
    return f


m5 = S.SR.marker_of(preds, "rd-5")
att3 = replay(new_att("doc5"), RDC_MAP, RD_MAP, doctor={"rd-5-x": doctor_own((m5, "x"), 0x16), "rd-5-y": doctor_own((m5 + 1, "y"), 0x16)})
s3, _, res3 = S.score_rd(att3 + "/p7-rd")
check("doctored rd-5 (o5's own word 6:1 at its own pixels): not replicated, the vector does not read H-MOD4, the verdict is not H-MOD4",
      "rd-5" in res3["notrep"] and "H-MOD4" not in res3["fits"] and not s3.startswith("H-MOD4 held") and None in res3["vector"], s3)
att4 = replay(new_att("riv"), RDC_MAP, RD_MAP, doctor={"rd-5-y": doctor_own((m5 + 1, "y"), 0x16, frac=0.05)})
s4, _, res4 = S.score_rd(att4 + "/p7-rd")
check("doctored rd-5 y job (5 percent of its own words S): top still A4 at >= 0.85, a rival above 0.02: rd-5 cannot tell",
      res4["entries"]["rd-5"] is None and "rival class S" in res4["reads"]["rd-5"]["why"], res4["reads"]["rd-5"].get("why"))
att5 = replay(new_att("ren"), RDC_MAP, RD_MAP, drop=("rd-3-x",))
os.rename(att5 + "/p7-rd/rd-3-y.txt.gz", att5 + "/p7-rd/rd-3-y.stdout.gz")  # renamed: not the kept name
s5, _, res5 = S.score_rd(att5 + "/p7-rd")
miss = S.missing("p7-rd", att5 + "/p7-rd")
check("a renamed / missing kept file: rd-3 cannot tell (never a pass), the vector undecided, missing() names it",
      res5["entries"]["rd-3"] is None and None in res5["vector"] and s5.startswith("cannot tell") and miss == ["rd-3-y.txt"], f"{s5[:80]} {miss}")
os.remove(att5 + "/p7-rdc/c-rd-0-y.txt.gz")
check("a missing p7-rdc file is named by missing('p7-rd') too", S.missing("p7-rd", att5 + "/p7-rd") == ["rd-3-y.txt", "../p7-rdc/c-rd-0-y.txt"],
      str(S.missing("p7-rd", att5 + "/p7-rd")))
# ============================================================================================ 4. controls on doctored inputs, refuse_unreadable
mo = S.SR.marker_of(preds, "c-ow")
mr = S.SR.marker_of(preds, "c-rd-0")
for what, doc, drop, want in (
        ("c-ow keeps its first write (1:2)", {"c-ow-x": doctor_own((mo, "x"), 0x21)}, (), 1),
        ("c-prd-0-k1 W_1 on no lane", {f"c-prd-0-k1-{ax}": (lambda g: [[(v & ~0x3f) | 0x21 if (v & 0x3f) == 0x11 else v for v in r] for r in g])
                                         for ax in "xy"}, (), 1),
        ("c-e709 without tag-5 words (G-o4)", {"c-e709-x": lambda g: [[0xff203040 if (v & 15) in (5, 13) else v for v in r] for r in g]}, (), 1),
        ("c-u with its first o1 word (tag 12) everywhere (G-o1)", {"c-u-x": lambda g: [[(v & ~15) | 12 if (v & 15) == 2 else v for v in r] for r in g]}, (), 1),
        ("c-u-y not kept", None, ("c-u-y",), 2),
        ("c-rd-0 dead: W_B (1:3) read back", {"c-rd-0-x": doctor_own((mr, "x"), 0x31)}, (), 1),
        ("c-rd-0-x not kept (no TRI)", None, ("c-rd-0-x",), 2)):
    a = new_att("ctl")
    replay(a, RDC_MAP, RD_MAP, doctor=doc, drop=drop)
    g = S.gate("p7-rdc", a + "/p7-rdc")
    sd, _, rd_ = S.score_rd(a + "/p7-rd")
    check(f"doctored control, {what}: gate {('PASS', 'FAILED', 'CANNOT TELL')[want]} (not PASS), p7-rd cannot tell", g == want and sd.startswith("cannot tell: p7-rdc gate"),
          f"gate {g}; {sd[:100]}")
probs = scorekit.control_read_problems({c["name"]: (tuple(c["reads"]), "|".join(next(r for r in table("p7-rdc")[1] if r[0] == c["name"])))
                                        for c in g_rd.controls("p7-rdc")}, g_rd.producible)
bad_row = "c-ow-x|control|safe|-|t4|probe --tri pixel --temps 32 --dump-render \"$W/dump\" --width 64 --height 64 \"$S/x.bin\""
try:
    scorekit.refuse_unreadable({"c-ow-x": (("class", "pixels"), bad_row)}, g_rd.producible)
    refused = False
except scorekit.ControlReadError:
    refused = True
check("refuse_unreadable: every p7-rdc control reads class and pixels its row produces; a control on a row without --pixels is refused",
      not probs and len(g_rd.controls("p7-rdc")) == 14 and refused, str(probs))

# ============================================================================================ 5. the world, through the runner's naming


def gzw(path, data):
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(data.encode() if isinstance(data, str) else data)


def kept(att, tokens):
    """att/STAGE as the runner keeps it: cases.tsv, NAME.txt.gz, .err.gz, .dmesg.gz, .snap0/.snap9.regs.gz, NAME.<basename>.gz of
    every file the tool wrote in $W/depth and $W/dump."""
    for stage in ("p7-rdc", "p7-rd"):
        d = os.path.join(att, stage)
        os.makedirs(d)
        lines = [HDR]
        for r in table(stage)[1]:
            n, sset, risk, knobs, tool, args = r
            w = tempfile.mkdtemp(prefix="job-", dir=TMP)
            os.makedirs(w + "/depth")
            os.makedirs(w + "/dump")
            argv = shlex.split(args.replace("$W", w).replace("$S", os.path.join(KP, "bins")))
            assert W.handles(tool, argv), n
            a = W.answer(tool, argv, tokens)
            gzw(f"{d}/{n}.txt.gz", a["out"])
            gzw(f"{d}/{n}.err.gz", a["err"])
            gzw(f"{d}/{n}.dmesg.gz", "\n".join(a["kmsg"]))
            gzw(f"{d}/{n}.snap0.regs.gz", "reg 0x0118 0x00000400\n")
            gzw(f"{d}/{n}.snap9.regs.gz", "reg 0x0118 0x00000400\n")
            for sub in ("depth", "dump"):
                for fn in os.listdir(f"{w}/{sub}"):
                    gzw(f"{d}/{n}.{fn}.gz", open(f"{w}/{sub}/{fn}", "rb").read())
            shutil.rmtree(w)
            fault = any("BIF fault" in x for x in a["kmsg"])
            cls = "fault" if fault else ("ok" if a["rc"] == 0 else "fail")
            lines.append("\t".join([n, stage, sset, risk, knobs, tool, args, str(a["rc"]), cls, "-", "0x90100" if fault else "-", "900000"]))
        open(os.path.join(d, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    return att


EXPECT = {
    "model": (0, "H-MOD4 held (17 of 17 entries): rd vector S S S A0 A4 A4 A4 (H-FOUR, H-MOD4) replicated; n-rd-4 A0, x-rd-4 A0; "
              "x-rd-6 A4 (o2's word), x-rd-7 A4 (o3's), n-rd-5 A4 (o1's); cl-4 A0 (word A); cl-5 X (no word of the job), cl-6 X (no "
              "word of the job), cl-7 X (no word of the job) (not word B); cl-p4 1:2,1:2,1:2,1:2 (word A on every lane)"),
    "hstore": (0, "H-STORE at x-rd-6, x-rd-7, cl-4, cl-5, cl-6, cl-7, cl-p4 (lane 0): a read of o4..o7 returns the word written there"),
    "gatefail": (1, "cannot tell: p7-rdc gate FAILED: c-ow (last o0 write): FAILED"),
    "o4none": (1, "cannot tell: p7-rdc gate FAILED: G-o4 c-e709: FAILED"),
    "noall4": (0, "cannot tell: c-all4 does not read 5:1 (FAILED): the stage is void"),
    "norep": (0, "cannot tell: not decided: rd-2 (not replicated: rd-2)"),
    "rival": (0, "cannot tell: not decided: x-rd-6;"),
    "fault": (0, "cannot tell: not decided: x-rd-6;"),
}
for tok, (g_want, s_want) in EXPECT.items():
    toks = {"model"} if tok == "model" else {"model", tok}
    a = kept(new_att("w-" + tok), toks)
    g = S.gate("p7-rdc", a + "/p7-rdc")
    sv = S.verdict(a)
    s_rd = [x for x in sv if x.startswith("SUMMARY: p7-rd:")][0][len("SUMMARY: p7-rd: "):]
    check(f"world {tok}: gate {g_want}, p7-rd verdict '{s_want[:70]}...'", g == g_want and s_rd.startswith(s_want), f"gate {g}; {s_rd}")
    if tok == "model":
        probs = []
        for st in ("p7-rdc", "p7-rd"):
            rows = sessioncheck.kept_rows(a + "/" + st)
            probs += sessioncheck.kept_problems(a + "/" + st, S.REQUIRED[st], rows, lambda st=st: S.score(st, a + "/" + st))
        check("world model: every REQUIRED file kept and the scorer reads no undeclared kept file (sessioncheck kept --call)", not probs, str(probs[:3]))
        p = subprocess.run([sys.executable, os.path.join(KP, "score/score_rd7.py"), "p7-rd", a + "/p7-rd"], capture_output=True, text=True)
        sl = [x for x in p.stdout.splitlines() if x.startswith("SUMMARY:")]
        check("CLI score_rd7.py p7-rd KEPT: detail then exactly one SUMMARY line, exit 0", p.returncode == 0 and len(sl) == 1
              and p.stdout.rstrip().splitlines()[-1].startswith("SUMMARY: H-MOD4 held"), p.stderr[-200:])
        p = subprocess.run([sys.executable, os.path.join(KP, "score/score_rd7.py"), "gate", "p7-rdc", a + "/p7-rdc"], capture_output=True, text=True)
        check("CLI score_rd7.py gate p7-rdc KEPT: exit 0 on the model world", p.returncode == 0, p.stdout)
    if tok == "gatefail":
        p = subprocess.run([sys.executable, os.path.join(KP, "score/score_rd7.py"), "gate", "p7-rdc", a + "/p7-rdc"], capture_output=True, text=True)
        check("CLI score_rd7.py gate p7-rdc KEPT: exit 1 when c-ow fails", p.returncode == 1, p.stdout)

shutil.rmtree(TMP, ignore_errors=True)
print("test_rd7: " + ("all ok" if ok else "FAILURES"))
sys.exit(0 if ok else 1)
