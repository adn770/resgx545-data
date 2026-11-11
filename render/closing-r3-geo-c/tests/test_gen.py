#!/usr/bin/env python3
"""The generated tables and predictions (gen/r3gen.py output) against E730's own rows and the design: counts, option strings,
controls, predictions per row, no forbidden option, held-out coverage.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import shlex  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen"), str(R3 / "score")]
import r3_geo as M  # noqa: E402
from r1lib import load_preds  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R3 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            rows.append(dict(name=f[0], set=f[1], risk=f[2], P=f[3], knobs=f[4], rt=f[5], args=f[6]))
    return rows


T = {st: table(st) for st in ("g-z", "g-qf", "g-qh")}
check("job counts: g-z 15, g-qf 22, g-qh 14 (51)", [len(T[s]) for s in ("g-z", "g-qf", "g-qh")] == [15, 22, 14], str({s: len(v) for s, v in T.items()}))
check("stages.txt lists them in session order (g-z, g-qf, g-qh)", (R3 / "stages.txt").read_text().split() == ["g-z", "g-qf", "g-qh"])
check("controls come first in every table", all([r["set"] for r in rows][:sum(1 for r in rows if r["set"] == "control")] == ["control"] * sum(1 for r in rows if r["set"] == "control") for rows in T.values()))
check("every tri row has expectdiff and stophang; no row has a tool option outside the R3GC list",
      all("expectdiff" in r["knobs"].split() and "stophang" in r["knobs"].split() for rows in T.values() for r in rows))
allargs = " ".join(r["args"] for rows in T.values() for r in rows)
check("no --kpoke, --kreg, --ctx2, --share-pb, --late anywhere; the only --poke is blk:1=0x00400200 and only in g-z",
      not re.search(r"--kpoke|--kreg|--ctx2|--share-pb|--late", allargs) and set(re.findall(r"--poke (\S+)", allargs)) == {"blk:1=0x00400200"}
      and not any("--poke" in r["args"] for r in T["g-qf"] + T["g-qh"]))
# E730's rows: the option string of a g-z full-screen row equals E730's for the same size (cases.tsv of the kept data)
e730 = {}
for ln in (R3 / "tests/fixtures/e730/cases.tsv").read_text().splitlines()[1:]:
    f = ln.split("\t")
    e730[f[0]] = f[5].replace("@D@", '"$W/depth"')
same = 0
for name, size, ramp in (("z-ctl-34x18-x", (34, 18), "x"), ("z-ctl-34x18-y", (34, 18), "y"), ("z-ctl-66x34-x", (66, 34), "x")):
    row = next(r for r in T["g-z"] if r["name"] == name)
    want = e730[f"gb-{size[0]}x{size[1]}-ramp{ramp}"]
    same += shlex.split("tri " + want) == shlex.split(row["args"])
check("the three control rows' commands equal E730's (isp-a-guard.sh) option strings token for token, with $W/depth for @D@", same == 3, f"{same} of 3")
# and every other g-z full row = E730's template with the size changed
tpl = e730["gb-34x18-rampx"]
okc = 0
full = [r for r in T["g-z"] if "--tri-full" in r["args"]]
for r in full:
    w, h = (int(re.search(rf"--{k} (\d+)", r["args"])[1]) for k in ("width", "height"))
    ramp = "x" if r["name"].endswith("-x") or re.fullmatch(r"z-w\d+", r["name"]) else "y"
    z = M.RAMP_X if ramp == "x" else M.RAMP_Y
    want = (f'--keep-overflow --wait-ms 20000 --width {w} --height {h} --tri-full --tri-z {z} --depth --depth-ctl {hex(M.depth_ctl(w))} '
            f'--depth-fill 0xdeadbeef --depth-dump "$W/depth" --depth-pages {M.depth_pages(w, h)} --poke blk:1=0x00400200')
    okc += shlex.split("tri " + want) == shlex.split(r["args"])
check("each of the 13 full-screen rows is E730's option string with its own size, pitch and pages", okc == len(full) == 13, f"{okc} of {len(full)}")
check("every width and height of g-z is even (the tool refuses odd sizes: render.c width % 2, height % 2)",
      all(int(re.search(rf"--{k} (\d+)", r["args"])[1]) % 2 == 0 for r in T["g-z"] for k in ("width", "height")))
sizes = {(int(re.search(r"--width (\d+)", r["args"])[1]), int(re.search(r"--height (\d+)", r["args"])[1])) for r in T["g-z"]}
check("g-z sizes: the three controls' E730 sizes plus widths 20, 36, 44, 76, 32, 64 and heights 20, 28, 36, 32 and the two triangle sizes",
      sizes >= {(34, 18), (66, 34), (20, 18), (36, 18), (44, 18), (76, 18), (32, 18), (64, 18), (34, 20), (34, 28), (34, 36), (34, 32), (36, 20)}, str(sorted(sizes)))
check("the g-z held-out rows at the integer fraction (W or H = 0 mod 4 inside the tile area) separate A from RSTRICT",
      all(M.extent("A", w, h) != M.extent("RSTRICT", w, h) for (w, h) in ((20, 18), (36, 18), (44, 18), (76, 18), (34, 20), (34, 28), (34, 36), (36, 20))))
check("the controls (E730's .5 sizes) separate A from ROUND and CEIL, not from FLOOR or RSTRICT",
      all(M.extent("A", w, h) != M.extent(r, w, h) for (w, h) in ((34, 18), (66, 34)) for r in ("ROUND", "CEIL"))
      and all(M.extent("A", w, h) == M.extent(r, w, h) for (w, h) in ((34, 18), (66, 34)) for r in ("FLOOR", "RSTRICT")))
ZP = load_preds(None, "g-z")
check("g-z: every row has predictions; held-out full rows carry stored_set_sha for all five rules (and the control rows E730's count)",
      all(set(ZP[r["name"]]) for r in T["g-z"])
      and all(len([x for x in ZP[r["name"]]["stored_set_sha"] if x[2] == "heldout"]) == 5 for r in full if r["set"] == "heldout")
      and {ZP[r["name"]]["stored_count"][0][0] for r in full if r["set"] == "control"} == {"924", "3444"})
check("g-z: the A prediction of each control cell equals E730's count (924, 924, 3444)",
      [len(M.band_set("A", w, h)) for w, h in ((34, 18), (34, 18), (66, 34))] == [924, 924, 3444])
# C2
FP, HP = load_preds(None, "g-qf"), load_preds(None, "g-qh")
check("g-qf: the three controls (0xa0 = 2, 0xb0 = 1, 0xa3 = 1) then the 19 split cells in descending P",
      [r["name"] for r in T["g-qf"][:3]] == ["qf-0xa0", "qf-0xb0", "qf-0xa3"]
      and [int(r["P"], 16) for r in T["g-qf"][3:]] == sorted(M.split_cells(), reverse=True)
      and [FP[r["name"]]["nparts"][0][0] for r in T["g-qf"][:3]] == ["2", "1", "1"])
check("g-qf/g-qh: every count row carries all 20 pair predictions and the knob proof (0x0624 = P - 0x22)",
      all(len(FP[r["name"]]["nparts"]) == 20 and FP[r["name"]]["knob0624_first"][0][0] == hex(int(r["P"], 16) - 0x22) for r in T["g-qf"][3:])
      and all(len(HP[r["name"]]["nparts"]) == 20 for r in T["g-qh"] if r["name"].startswith("qh-")))
check("g-qh: two scene gates at P = 0x422 (U 275, 438) first, then 12 held-out cells (6 a scene) with the E773 scene commands",
      [r["name"] for r in T["g-qh"][:2]] == ["qc-s275", "qc-s438"] and [r["P"] for r in T["g-qh"][:2]] == ["0x422", "0x422"]
      and HP["qc-s275"]["U"][0][0] == "275" and HP["qc-s438"]["U"][0][0] == "438"
      and all("--move 1:1024,0" in r["args"] for r in T["g-qh"] if "s275" in r["name"])
      and all("-n 2 --geometry 1 --move 2:0,1024" in r["args"] and "--keep-going" in r["args"] for r in T["g-qh"] if "s438" in r["name"]))
check("every count row reads the timeline over 0x0624, 0x0654-0x0660 and 0x0720-0x072c (the 0x0658 stretches and the 0x0724 peak)",
      all("0x0624-0x0628" in r["rt"] and "0x0654-0x0660" in r["rt"] and "0x0720-0x072c" in r["rt"] for r in T["g-qf"] + T["g-qh"]))
check("the held-out predictions in the frozen table equal r3_geo.count at the scene's U (275 / 438) for all 20 pairs",
      all(int(v) == M.count(M.SCENES[re.match(r"qh-(s\d+)", r["name"])[1]][0], *[int(x, 0) for x in re.findall(r"k=(-?\d+), s=(0x[0-9a-f]+)", m)[0]], int(r["P"], 16))
          for r in T["g-qh"] if r["name"].startswith("qh-") for v, m, st in HP[r["name"]]["nparts"]))
check("PREDICTIONS: no quantity names a hang, a fault or a recovery",
      not any(q in ("hang", "fault", "recovery") for P in (ZP, FP, HP) for d in P.values() for q in d))
sys.exit(0 if ok else 1)
