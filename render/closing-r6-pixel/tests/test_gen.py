#!/usr/bin/env python3
"""The generated tables and frozen predictions: stage order and job counts (58 + 8 + 8 + 106 + 22 = 202), the sets, every row with
frozen predictions, and the argv-twin check (round 6 rule, BRIEF-BUILD: R4's o2 slip was a control of another shape): every row's
command, controls included, is its stage's template WRITTEN OUT HERE (not imported from the generator) with only the program name
changed, and the program it names is the one its plan row needs (derived here from the row's name: E709's, R4's and R5's reused
programs for c-e709, c-u, c-all4, p3-pa-k0/k3, rw-k0..k5, d-01, d-02; the replicate the program of its source row; the session's own
program otherwise); p6-s's rows differ from p6-rd's command by exactly the two frozen options; the triangle and size (64 x 64,
--vtx-coords 2), the knobs (stophang s2; p6-s also kpoke) and no regtimeline; the reused programs are the published bytes; the staged
programs listed by #need exist; no forbidden option; the generator is deterministic (a rerun rewrites the same bytes).
Prints ok/FAIL; exit 1."""
import collections
import hashlib
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R6 = pathlib.Path(__file__).resolve().parent.parent
R5P = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
R4P = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r4-pixel")
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    return [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
            for ln in (R6 / "tables" / f"{st}.txt").read_text().splitlines() if ln and not ln.startswith("#")]


STAGES = ["p6-rd", "p6-l3", "g6-rwa", "g6-rw", "p6-s"]
check("stages.txt: p6-rd, p6-l3, g6-rwa, g6-rw, p6-s (S last)", (R6 / "stages.txt").read_text().split() == STAGES)
T = {st: table(st) for st in STAGES}
check("job counts 58, 8, 8, 106, 22 (202)", [len(T[s]) for s in STAGES] == [58, 8, 8, 106, 22], str([len(T[s]) for s in STAGES]))
sets = {st: dict(collections.Counter(r["set"] for r in T[st])) for st in STAGES}
check("sets: p6-rd 14 control 42 heldout 2 replicate; p6-l3 4 + 4; g6-rwa 8 control; g6-rw 104 heldout 2 replicate; p6-s 4 control 18 heldout",
      sets == {"p6-rd": {"control": 14, "heldout": 42, "replicate": 2}, "p6-l3": {"control": 4, "heldout": 4}, "g6-rwa": {"control": 8},
               "g6-rw": {"heldout": 104, "replicate": 2}, "p6-s": {"control": 4, "heldout": 18}}, str(sets))
# the templates, written out (R5's C_BASE and CMD byte for byte)
C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 --blk 4=0x00030001 '
          '--slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" "$S/{prog}.bin"')
C_SETUP = C_BASE.replace("--blk 4=0x00030001", "--blk 4=0x00030001 --blk 1=0x05d00200 --kpoke rd:9=1")
C_RESTORE = C_BASE.replace("--blk 4=0x00030001", "--blk 4=0x00030001 --kpoke rd:9=0")
CMD = ('probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render "$W/dump" '
       '--slot "pixel=$S/pix_green.bin" "$S/{prog}.bin"')
r5t = (R5P / "tables/p5-o4.txt").read_text() + (R5P / "tables/g5-rw.txt").read_text() + (R5P / "tables/g5-rwa.txt").read_text()
check("the templates are R5's (the commands of R5's kept tables)", ("|" + C_BASE.format(prog="r4o-u-x")) in r5t and ("|" + CMD.format(prog="rw-k4")) in r5t)


def plan_row(st, name):
    """(template, program, knobs) a row's plan row needs, from its name alone."""
    base = name[:-4] if name.endswith("-rep") else name
    if st in ("p6-rd", "p6-l3"):
        cfg, ax = base.rsplit("-", 1)
        prog = {"c-e709": f"r4o-e709-{ax}", "c-u": f"r4o-u-{ax}", "c-all4": f"r5o-c-all4-{ax}", "p3-pa-k0": f"r5o-p3-pa-k0-{ax}",
                "p3-pa-k3": f"r5o-p3-pa-k3-{ax}"}.get(cfg, f"r6o-{cfg}-{ax}")
        return C_BASE, prog, "stophang s2"
    if st == "p6-s":
        cfg, ax = base.rsplit("-", 1)
        if cfg == "r-u":
            return C_RESTORE, f"r4o-u-{ax}", "stophang s2 kpoke"
        return C_SETUP, f"r6o-{cfg}-{ax}", "stophang s2 kpoke"
    return CMD, (name[1:] if name.startswith("rl-") else name), "stophang s2"


bad = []
for st in STAGES:
    for r in T[st]:
        tpl, prog, kn = plan_row(st, r["name"])
        if r["args"] != tpl.format(prog=prog) or r["knobs"] != kn or r["rt"] != "-" or r["risk"] != "safe":
            bad.append((st, r["name"], r["args"][-40:], r["knobs"]))
check("argv twin: every row of every stage, controls included, is its plan row's template with only the program changed, the program "
      "its plan row needs, its knobs, no regtimeline", not bad, str(bad[:3]))
check("p6-s's rows differ from p6-rd's command by exactly the two frozen options (setup) or the one restore option",
      C_SETUP.replace(" --blk 1=0x05d00200 --kpoke rd:9=1", "") == C_BASE and C_RESTORE.replace(" --kpoke rd:9=0", "") == C_BASE
      and all(" --kpoke " in r["args"] for r in T["p6-s"]) and not any("kpoke" in r["args"] for st in STAGES[:4] for r in T[st]))
check("every pixel row draws the 64 x 64 triangle with two coordinates (no default triangle: R4's o2 slip)",
      all("--width 64 --height 64 --vtx-coords 2" in r["args"] for st in STAGES for r in T[st]))
check("order p6-rd: controls c-e709 c-u c-all4 c-ow c-rd-0 c-prd-0-k1 -k7, rd-1..7, n-rd-1 n-rd-4 x-rd-4 x-rd-5, prd-3 then prd-4 (k 0 1 2 3 7), rd-4 replicate",
      [r["name"].rsplit("-", 1)[0] for r in T["p6-rd"][:-2:2]] == ["c-e709", "c-u", "c-all4", "c-ow", "c-rd-0", "c-prd-0-k1", "c-prd-0-k7"]
      + [f"rd-{j}" for j in range(1, 8)] + ["n-rd-1", "n-rd-4", "x-rd-4", "x-rd-5"] + [f"prd-{j}-k{k}" for j in (3, 4) for k in (0, 1, 2, 3, 7)]
      and [r["name"] for r in T["p6-rd"][-2:]] == ["rd-4-x-rep", "rd-4-y-rep"])
check("order g6-rw: 72 L (strides 1, 2^8, 2^16, windows a, b), 8 B, 2 replicates, 24 E last",
      [r["name"][:2] for r in T["g6-rw"]] == ["l-"] * 72 + ["b-"] * 8 + ["rl"] * 2 + ["em"] * 12 + ["ep"] * 12
      and [r["name"][2:4] for r in T["g6-rw"][:72:12]] == ["1a", "1b", "8a", "8b", "16"][:5] + ["16"])
# reused programs: the published bytes
same = []
for st in STAGES:
    for r in T[st]:
        prog = re.search(r'"\$S/([\w-]+)\.bin"$', r["args"])[1]
        src = (R5P / "bins" / f"{prog}.bin") if prog.startswith(("r5o-", "rw-k", "d-0")) and st != "g6-rw" else \
            (R4P / "bins" / f"{prog}.bin") if prog.startswith("r4o-u") else None
        if src is not None:
            same.append((prog, (R6 / "bins" / f"{prog}.bin").read_bytes() == src.read_bytes()))
check("reused programs (R4's c-u, R5's c-all4, p3-pa-k0/k3, rw-k0..k5, d-01, d-02) are the published bytes", all(s for _, s in same) and len(same) == 18,
      str([p for p, s in same if not s]))
check("E709's program assembles to R5's bytes", all((R6 / "bins" / f"r4o-e709-{a}.bin").read_bytes() == (R5P / "bins" / f"r4o-e709-{a}.bin").read_bytes() for a in "xy"))
for st in STAGES:
    txt = (R6 / "tables" / f"{st}.txt").read_text()
    need = [n.split("/")[-1] for n in re.findall(r"^#need (\S+)", txt, re.M)]
    used = set(re.findall(r'"\$S/([\w-]+\.bin)"', txt)) | ({"pds_iter_xy.bin", "vtx_coords.bin"} if st.startswith("p6") else {"pix_green.bin"})
    check(f"{st}: every program a row names is listed by #need and staged in bins/", used <= set(need) and all((R6 / "bins" / n).exists() for n in need))
    check(f"{st}: no forbidden option", not re.search(r"--kreg|--poke|--late|--low|--place|--share-pb|--depth|--geometry|--ctx2|kpoke-", txt))
for st in STAGES:
    preds = collections.defaultdict(set)
    for ln in (R6 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        preds[c].add(q)
        assert m, ln
    if st.startswith("p6"):
        miss = [r["name"] for r in T[st] if r["name"].endswith(("-x", "-x-rep")) and not preds[r["name"]] and not r["name"].startswith("c-e709")]
    else:
        miss = [r["name"] for r in T[st] if not {"w_words", "xy_ordered", "rz_words", "nvert"} <= preds[r["name"]]]
    check(f"{st}: every row (the x job of a pair) has frozen predictions with a hypothesis label", not miss, str(miss))
mk = {}
for ln in (R6 / "bins/p6-markers.tsv").read_text().splitlines():
    a, b = ln.split("\t")
    mk[a] = int(b)
xs = sorted(v for n, v in mk.items() if n.endswith("-x"))
check("new markers: unique, 0x181.. below 0x200, the y job's = the x job's + 1, none of R4's or R5's (<= 0x172)",
      len(set(mk.values())) == len(mk) and min(mk.values()) > 0x172 and max(mk.values()) < 0x200
      and all(mk[n[:-1] + "y"] == v + 1 for n, v in mk.items() if n.endswith("-x")), f"{len(mk)} markers {hex(min(mk.values()))}..{hex(max(mk.values()))}")
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R6 / "tables").glob("*")) + sorted((R6 / "predictions").glob("*")) + sorted((R6 / "bins").glob("*"))}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([sys.executable, str(R6 / "gen/r6gen.py")], capture_output=True, text=True, env=env)
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R6 / "tables").glob("*")) + sorted((R6 / "predictions").glob("*")) + sorted((R6 / "bins").glob("*"))}
check("the generator is deterministic: a rerun rewrites the same tables, predictions and programs", r.returncode == 0 and before == after, r.stderr[-200:])
sys.exit(0 if ok else 1)
