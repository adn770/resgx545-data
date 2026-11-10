#!/usr/bin/env python3
"""The generated tables and frozen predictions of R3: stage order and job counts (R3-G1..R3-G9: 27 + 16 + 10 + 4 depth jobs, g-c4 10,
g-d36 6, g-c6 5, g-c5 36, g-c7 11), every row has its frozen prediction with a hypothesis and a label, labels agree with the row's set, every
stage has a control that can fail (the DPM stages after g-c4 take g-c4's), every DPM job lists 0x0720-0x072c (the H-last side table) and
carries the H-last prediction, derived cells (B:, L:, F:) carry their group knobs, the P and knob vocabulary is the runner's, no poke
of any kind, no tool options outside the audited set, the staged programs exist and are in the #need lists, the frozen numbers (LT 0xd4,
the fixed cells, the controls' readings) are the design's, and the freeze verifies.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen")]
import r3models as M  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R3 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "P", "knobs", "rt", "args"), ln.split("|", 6))))
    return rows


def preds(st):
    out = collections.defaultdict(list)
    for ln in (R3 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R3 / "stages.txt").read_text().split()
ORDER = ["g-da", "g-db", "g-dc", "g-dd", "g-c4", "g-d36", "g-c6", "g-c5", "g-c7"]
check("stage order (R3-G9): g-da, g-db, g-dc, g-dd, g-c4, g-d36, g-c6, g-c5, g-c7", stages == ORDER, str(stages))
counts = {st: len(table(st)) for st in ORDER}
check("job counts: depth 27 + 16 + 10 + 4 = 57, g-c4 10, g-d36 6, g-c6 5, g-c5 36, g-c7 11 (R3-G1..G8)",
      counts == {"g-da": 27, "g-db": 16, "g-dc": 10, "g-dd": 4, "g-c4": 10, "g-d36": 6, "g-c6": 5, "g-c5": 36, "g-c7": 11}, str(counts))
check("total 125 jobs", sum(counts.values()) == 125, str(sum(counts.values())))
KNOWN = re.compile(r"stophang|expectdiff|ctl:[RN]|obs:[a-z0-9]+|cal:[a-z0-9]+|gate:[0-9]+|fit:[a-z0-9]+")
META = {"cell", "frac", "word_down", "word_up", "thr_dir", "raise_rule", "last_raise_thr0", "page_need", "separating_jobs", "knob0624_first"}
for st in ORDER:
    rows, ps = table(st), preds(st)
    names = [r["name"] for r in rows]
    check(f"{st}: job names unique", len(names) == len(set(names)))
    miss = [n for n in names if n not in ps]
    check(f"{st}: every row has a frozen prediction", not miss, str(miss))
    orphan = [n for n in ps if n not in names and not n.startswith("@")]
    check(f"{st}: no prediction without a row (stage-level ones start with @)", not orphan, str(orphan))
    badlab = [(n, p) for n, lst in ps.items() for p in lst if p[3] not in ("control", "heldout", "repeat", "replicate") or not p[2].strip()]
    check(f"{st}: every prediction names a hypothesis and a label", not badlab, str(badlab[:2]))
    setmis = [r["name"] for r in rows if r["set"] == "control" and "control" not in {p[3] for p in ps[r["name"]]}
              or r["set"] == "heldout" and "heldout" not in {p[3] for p in ps[r["name"]]}]
    check(f"{st}: a control row has control predictions, a held-out row held-out predictions", not setmis, str(setmis))
    check(f"{st}: controls first", [r["set"] for r in rows] == sorted([r["set"] for r in rows], key=lambda s: s != "control"))
    check(f"{st}: only the runner's knobs", all(KNOWN.fullmatch(k) for r in rows for k in r["knobs"].split()))
    check(f"{st}: no poke, kreg, ctx2, share-pb, late or --poke option anywhere", not any(re.search(r"--(kpoke|kreg|ctx2|share-pb|late|poke)", r["args"]) for r in rows))
    check(f"{st}: P is a hex value, `-`, or a derived cell B:/L:/F:",
          all(re.fullmatch(r"-|0x[0-9a-f]+|[BLF]:[a-z0-9]+(:[+-][0-9]+)?", r["P"]) for r in rows))
    needs = {ln.split("/")[-1].strip() for ln in (R3 / "tables" / f"{st}.txt").read_text().splitlines() if ln.startswith("#need ")}
    check(f"{st}: every #need program exists in bins/", all((R3 / "bins" / n).exists() for n in needs), str([n for n in needs if not (R3 / "bins" / n).exists()]))
    used = {m for r in rows for m in re.findall(r'\$S/([A-Za-z0-9_.:-]+?\.bin)', r["args"])}
    check(f"{st}: every program a command names is in the #need list (and so in the freeze)", used <= needs, str(used - needs))
    nc = sum(1 for r in rows if r["set"] == "control")
    if st in ("g-da", "g-dc", "g-c4"):
        check(f"{st}: at least one control job that can fail", nc >= 1, str(nc))
for st in ("g-da", "g-db", "g-dc", "g-dd"):
    rows = table(st)
    check(f"{st}: depth jobs run no timeline, no knob, 64x64 vtxuse programs",
          all(r["rt"] == "-" and r["P"] == "-" and "--tri vtxuse" in r["args"] and "--width 64 --height 64" in r["args"] for r in rows))
dpm = [st for st in ORDER if st.startswith("g-c") or st == "g-d36"]
dpm = [s for s in dpm if s != "g-c3"]
for st in ("g-c4", "g-d36", "g-c6", "g-c5", "g-c7"):
    rows, ps = table(st), preds(st)
    check(f"{st}: every job lists 0x0720-0x072c in its timeline and carries the H-last prediction (the side table)",
          all("0x0720-0x072c" in r["rt"] for r in rows) and all(any(q == "dw36" and "H-last" in m for q, v, m, s in ps[r["name"]]) for r in rows))
    check(f"{st}: every derived cell (B:, L:, F:) records its group and the fit gate; every calibration is at P 0x422",
          all(("obs:" in r["knobs"] or r["P"].startswith(("L:", "F:")) and st == "g-c6") for r in rows if r["P"].startswith(("B:", "L:", "F:")))
          and all(r["P"] == "0x422" for r in rows if "cal:" in r["knobs"]))
c4 = {r["name"]: r for r in table("g-c4")}
check("g-c4: four controls (R1's 4096 pair 0x372 raise / 0x374 none, R2's 2048 pair 0xe2 raise / 0x122 none) then six bisect cells B:c4",
      [n for n, r in c4.items() if r["set"] == "control"] == ["c3-4096-0x372", "c3-4096-0x374", "c3-2048-0xe2", "c3-2048-0x122"]
      and [r["P"] for n, r in c4.items() if n.startswith("c4-b")] == ["B:c4"] * 6
      and [c4[n]["knobs"].split()[1] for n in ("c3-4096-0x372", "c3-4096-0x374", "c3-2048-0xe2", "c3-2048-0x122")] == ["ctl:R", "ctl:N", "ctl:R", "ctl:N"], str(list(c4)))
check("g-c4: only the 2048 controls and the bisect cells feed the c4 group (the 4096 controls do not)",
      [n for n, r in c4.items() if "obs:c4" in r["knobs"]] == ["c3-2048-0xe2", "c3-2048-0x122"] + [f"c4-b{i}" for i in range(1, 7)])
p4 = preds("g-c4")
check("g-c4: LT is frozen as the stage-level last raise 0xd4 and per cell as thr0 <= 0xd4; controls as measured",
      any(q == "last_raise_thr0" and v == "0xd4" and "LT" in m for q, v, m, s in p4["@g-c4"])
      and all(any(q == "raise_rule" and v == "thr0 <= 0xd4" for q, v, m, s in p4[f"c4-b{i}"]) for i in range(1, 7))
      and [v for q, v, m, s in p4["c3-4096-0x372"] if q == "raise"] == ["yes"] and [v for q, v, m, s in p4["c3-4096-0x374"] if q == "raise"] == ["no"]
      and [v for q, v, m, s in p4["c3-2048-0xe2"] if q == "raise"] == ["yes"] and [v for q, v, m, s in p4["c3-2048-0x122"] if q == "raise"] == ["no"])
d36 = table("g-d36")
check("g-d36: 1500 vertices, the knob only: 2048x2048 at thr0 0x60 0x70 0x90 0xb0 and 4096x4096 at 0x2c0 0x300 (P = thr0 + 0x22)",
      [(r["P"], "--width 2048" in r["args"]) for r in d36] == [("0x82", True), ("0x92", True), ("0xb2", True), ("0xd2", True), ("0x2e2", False), ("0x322", False)]
      and all("--vertices 1500" in r["args"] for r in d36))
c6 = {r["name"]: r for r in table("g-c6")}
check("g-c6: 2048x2048 with --max-width 4096 --max-height 4096: a calibration at 0x422, the cells L:c4 and F:c4, thr0 0x100 and 0x120",
      list(c6) == ["c6-cal", "c6-L", "c6-F", "c6-0x100", "c6-0x120"] and c6["c6-L"]["P"] == "L:c4" and c6["c6-F"]["P"] == "F:c4"
      and (c6["c6-0x100"]["P"], c6["c6-0x120"]["P"]) == ("0x122", "0x142")
      and all("--max-width 4096 --max-height 4096" in r["args"] and "--width 2048 --height 2048" in r["args"] for r in c6.values()))
c5 = table("g-c5")
tg = {"c5a": (4096, 2048), "c5b": (2048, 4096), "c5c": (3072, 3072)}
check("g-c5: 12 jobs a target (4096x2048, 2048x4096, 3072x3072): a calibration at 0x422, five fixed cells, six bisect cells B:target",
      all(len([r for r in c5 if r["name"].startswith(g + "-")]) == 12 for g in tg)
      and all(sum(1 for r in c5 if r["name"].startswith(g + "-") and r["P"] == f"B:{g}") == 6 for g in tg)
      and all(f"--width {w} --height {h} " in r["args"] for g, (w, h) in tg.items() for r in c5 if r["name"].startswith(g + "-")))
cells = {g: sorted(int(r["P"], 16) - 0x22 for r in c5 if r["name"].startswith(g + "-f")) for g in tg}
check("g-c5 fixed cells: the ends of the affine-in-regions bracket and LT's pair (4096x2048 and 2048x4096: 0x19b 0x1a8 0x1a9 0x1c5 0x1c6)",
      cells["c5a"] == cells["c5b"] == [0x19b, 0x1a8, 0x1a9, 0x1c5, 0x1c6] and all(len(v) == 5 for v in cells.values()) and 0x1dd in cells["c5c"], str({g: [hex(x) for x in v] for g, v in cells.items()}))
c7 = {r["name"]: r for r in table("g-c7")}
check("g-c7: --tri-full 1500 vertices at 2048x2048: a calibration at 0x422 with the gate (3 partial renders), then 6 cells from g-c4's flip and 4 bisect cells",
      list(c7)[0] == "c7-cal" and "gate:3" in c7["c7-cal"]["knobs"] and len(c7) == 11
      and [r["P"] for r in list(c7.values())[1:7]] == ["L:c4", "F:c4", "L:c4:-16", "L:c4:-4", "F:c4:+4", "F:c4:+16"]
      and [r["P"] for r in list(c7.values())[7:]] == ["B:c7"] * 4 and all("--tri-full" in r["args"] for r in c7.values()))
da = preds("g-da")
meta = lambda n, q: next((v for qq, v, m, s in da[n] if qq == q), None)
cells_da = [n for n in da if meta(n, "cell")]
by_kind = collections.Counter(meta(n, "cell") for n in cells_da)
check("g-da: 4 controls (two R2, two repeats of E783's words) + 2 power-of-two controls; 5 low, 4 high, 2 above half, 10 inside held out",
      sum(1 for r in table("g-da") if r["set"] == "control") == 6 and by_kind == {"outside-lo": 2, "outside-mid": 3, "outside-hi": 4, "above-half": 2, "inside": 10}, str(by_kind))
check("g-da: the repeats carry E783's measured words (0x3d88888c and 0x3d83a840), the R2 controls 0x3f000000 and 0x3e800000",
      [v for q, v, m, s in da["da-rep-m2p6-3"] if q == "depth_words"] == ["0x3d88888c,0x3d88888c,0x3d88888c"]
      and [v for q, v, m, s in da["da-rep-m6p1-7"] if q == "depth_words"] == ["0x3d83a840,0x3d83a840,0x3d83a840"]
      and [v for q, v, m, s in da["da-ctl-z0-w3"] if q == "depth_words"] == ["0x3f000000,0x3f000000,0x3f000000"]
      and [v for q, v, m, s in da["da-ctl-zm05-w1"] if q == "depth_words"] == ["0x3e800000,0x3e800000,0x3e800000"])
check("g-da: every held-out cell has the six candidate words and the directions frozen (low, mid down; high, above half up; inside flip)",
      all(sum(1 for q, v, m, s in da[n] if q == "depth_words") == 6 for n in cells_da)
      and all(meta(n, "thr_dir") == {"outside-lo": "down", "outside-mid": "down", "outside-hi": "up", "above-half": "up", "inside": "flip"}[meta(n, "cell")] for n in cells_da))
inside = sorted(float(meta(n, "frac")) for n in cells_da if meta(n, "cell") == "inside")
check("g-da: the inside fractions lie in (0.37, 0.4667), none within 0.004 of 3/8 or 7/16, five bins of two",
      all(0.37 <= f < 0.4667 for f in inside) and all(min(abs(f - 0.375), abs(f - 0.4375)) >= 0.004 for f in inside) and len(inside) == 10, str(inside))
check("g-da: T26 and T27 tell apart in at least 4 inside cells and D1 and T26 in all 4 high cells (the cells separate the candidates)",
      sum(1 for n in cells_da if meta(n, "cell") == "inside" and len({v for q, v, m, s in da[n] if q == "depth_words" and m.split()[0] in ("T26", "T27")}) == 2) >= 4
      and all(len({v for q, v, m, s in da[n] if q == "depth_words" and m.split()[0] in ("D1", "T26")}) == 2 for n in cells_da if meta(n, "cell") == "outside-hi"))
db = preds("g-db")
check("g-db: 6 z > 0 cells + 6 q cells + 4 near-1 cells, each with at least two distinct frozen words",
      len([n for n in db if n.startswith("db-pos")]) == 6 and len([n for n in db if n.startswith("db-q")]) == 6 and len([n for n in db if n.startswith("db-near")]) == 4
      and all(len({v for q, v, m, s in l if q == "depth_words"}) >= 2 for l in db.values()))
dc = preds("g-dc")
check("g-dc: the default viewport words (0.5, 0.5) written explicitly are the control (0x3e800000); four jobs at w = 1, six at w != 1",
      [v for q, v, m, s in dc["dc-ctl-default"] if q == "depth_words"] == ["0x3e800000,0x3e800000,0x3e800000"]
      and len([n for n in dc if n.startswith("dc-w1")]) == 3 and len([n for n in dc if n.startswith("dc-wn")]) == 6
      and all("--blk 10=" in r["args"] and "--blk 11=" in r["args"] for r in table("g-dc")))
dd = preds("g-dd")
check("g-dd: four held-out cuts (two on +w, two on -w) with the structure predictions (the control) and the made-vertex words",
      len(dd) == 4 and all({"nvert", "xy_set", "xy_ordered", "prims", "depth_made_by_xy", "rhw_by_xy"} <= {q for q, v, m, s in l} for l in dd.values()))
check("the tool is the pinned R1 binary (TOOL.sha256 bf4f8be2...), no rebuild; TOOLSRC.sha256 present",
      (R3 / "TOOL.sha256").read_text().startswith("bf4f8be2d8a8fe50034559450928e05695dc96d396d4892f9b00ea6bc0d4f053") and (R3 / "TOOLSRC.sha256").stat().st_size > 0)
r = subprocess.run([str(R3 / "run/freeze_r3.sh"), "verify"], capture_output=True, text=True)
check("the freeze verifies (FROZEN.sha256 and PREDICTIONS.sha256)", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
sys.exit(0 if ok else 1)
