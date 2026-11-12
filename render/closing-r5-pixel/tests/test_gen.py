#!/usr/bin/env python3
"""The generated tables and frozen predictions: stage order and job counts (58 + 12 + 36 = 106), the sets, every row with frozen
predictions, and the round 5 argv-twin check (BRIEF-BUILD: R4's o2 slip was a control of another shape): every row's command, controls
included, is its stage's template with only the program name changed, and the program it names is the one its plan row needs (derived
here from the row's name, independently of the generator: E709's and R4's reused programs for c-e709, c-u, c-v-a4, rw-k0..k3, rw-07,
rw-10; the session's own program otherwise; the replicate the program of its source row); the triangle and size (64 x 64, --vtx-coords
2), the knobs (stophang s2) and no regtimeline; the staged programs listed by #need exist; no forbidden option; the generator is
deterministic (a rerun rewrites the same bytes).  Prints ok/FAIL; exit 1."""
import collections
import hashlib
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R5 / "gen"), str(R5 / "score")]
import r5_o4  # noqa: E402
import r5_rw  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    return [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
            for ln in (R5 / "tables" / f"{st}.txt").read_text().splitlines() if ln and not ln.startswith("#")]


check("stages.txt: p5-o4, g5-rwa, g5-rw", (R5 / "stages.txt").read_text().split() == ["p5-o4", "g5-rwa", "g5-rw"])
T = {st: table(st) for st in ("p5-o4", "g5-rwa", "g5-rw")}
check("job counts 58, 12, 36 (106; g5-rw's 48 in two tables)", [len(T[s]) for s in T] == [58, 12, 36])
check("g5-rwa: 6 controls then q-15..q-20 (set heldout)", [r["name"] for r in T["g5-rwa"]] == [f"rw-k{i}" for i in range(6)] + [f"q-{i}" for i in range(15, 21)]
      and [r["set"] for r in T["g5-rwa"]] == ["control"] * 6 + ["heldout"] * 6)
check("g5-rw: m-01..m-14, rw-07, rw-10, d-01..d-20", [r["name"] for r in T["g5-rw"]] == [f"m-{i:02d}" for i in range(1, 15)] + ["rw-07", "rw-10"]
      + [f"d-{i:02d}" for i in range(1, 21)] and collections.Counter(r["set"] for r in T["g5-rw"]) == {"heldout": 14, "replicate": 2, "table": 20})


def expect_o4(name):
    base = name[:-4] if name.endswith("-rep") else name
    cfg, ax = base.rsplit("-", 1)
    if cfg == "c-e709":
        return f"r4o-e709-{ax}"
    if cfg == "c-u":
        return f"r4o-u-{ax}"
    if cfg == "c-v-a4":
        return f"r4o-v-a4-{ax}"
    return f"r5o-{cfg}-{ax}"


bad = []
for st, tpl, expect in (("p5-o4", r5_o4.C_BASE, expect_o4), ("g5-rwa", r5_rw.CMD, lambda n: n), ("g5-rw", r5_rw.CMD, lambda n: n)):
    for r in T[st]:
        m = re.fullmatch(re.escape(tpl.format(prog="\x00")).replace("\x00", r"([\w-]+)"), r["args"])
        if not m or m[1] != expect(r["name"]) or r["knobs"] != "stophang s2" or r["rt"] != "-" or r["risk"] != "safe":
            bad.append((st, r["name"], m[1] if m else r["args"][:60]))
check("argv twin: every row of every stage, controls included, is its stage's template (R4's C_BASE / CMD byte for byte) with only "
      "the program changed, the program its plan row needs, knobs `stophang s2`, no regtimeline", not bad, str(bad[:3]))
check("the templates are R4's byte for byte", r5_o4.C_BASE == ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 '
      '--height 64 --vtx-coords 2 --blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" "$S/{prog}.bin"')
      and r5_rw.CMD == ('probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render "$W/dump" '
                        '--slot "pixel=$S/pix_green.bin" "$S/{prog}.bin"'))
r4t = {st: (pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r4-pixel/tables") / f"{st}.txt").read_text() for st in ("p4-o4", "g4-rw")}
check("R4's own tables carry the same command for the reused programs (c-u, c-v-a4, rw-k0..k3, rw-07, rw-10)",
      all(("|" + r["args"]) in r4t["p4-o4"] for r in T["p5-o4"] if r["name"].startswith(("c-u-", "c-v-a4-")))
      and all(("|" + r["args"]) in r4t["g4-rw"] for r in T["g5-rwa"][:4] + T["g5-rw"][14:16]))
for st in T:
    txt = (R5 / "tables" / f"{st}.txt").read_text()
    need = [n.split("/")[-1] for n in re.findall(r"^#need (\S+)", txt, re.M)]
    used = set(re.findall(r'"\$S/([\w-]+\.bin)"', txt)) | ({"pds_iter_xy.bin", "vtx_coords.bin"} if st == "p5-o4" else {"pix_green.bin"})
    check(f"{st}: every program a row names is listed by #need and staged in bins/", used <= set(need) and all((R5 / "bins" / n).exists() for n in need))
    check(f"{st}: no forbidden option", not re.search(r"--kreg|--kpoke|--poke|--late|--low|--place|--share-pb|--depth|--geometry|--ctx2", txt))
for st in T:
    preds = collections.defaultdict(set)
    for ln in (R5 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        preds[c].add(q)
        assert m, ln
    if st == "p5-o4":
        miss = [r["name"] for r in T[st] if r["name"].endswith(("-x", "-x-rep")) and not preds[r["name"]]]
    else:
        miss = [r["name"] for r in T[st] if not {"w_words", "xy_ordered", "rz_words", "nvert"} <= preds[r["name"]]]
    check(f"{st}: every row (the x job of a pair) has frozen predictions with a hypothesis label", not miss, str(miss))
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R5 / "tables").glob("*")) + sorted((R5 / "predictions").glob("*")) + sorted((R5 / "bins").glob("*"))}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([sys.executable, str(R5 / "gen/r5gen.py")], capture_output=True, text=True, env=env)
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R5 / "tables").glob("*")) + sorted((R5 / "predictions").glob("*")) + sorted((R5 / "bins").glob("*"))}
check("the generator is deterministic: a rerun rewrites the same tables, predictions and programs", r.returncode == 0 and before == after, r.stderr[-200:])
sys.exit(0 if ok else 1)
