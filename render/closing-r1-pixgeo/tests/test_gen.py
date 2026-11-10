#!/usr/bin/env python3
"""The generated tables and frozen predictions: every row has its frozen prediction with a hypothesis and a label,
labels are consistent with the row's set, no hypothesis rows, tri rows carry expectdiff, 0x072c knobs sit on the right
rows, the stage order and job counts are the session's, the staged programs exist, every program assembles, no table uses
a forbidden option, and the frozen files verify.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R1 = pathlib.Path(__file__).resolve().parent.parent
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R1 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "P", "knobs", "rt", "args"), ln.split("|", 6))))
    return rows


def preds(st):
    out = collections.defaultdict(list)
    for ln in (R1 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R1 / "stages.txt").read_text().split()
check("stage order (R2-17): Q276 C2, then geometry U1, C1, T1, T2, T7, U2, T5, T6",
      stages == ["p-c2", "g-u1", "g-c1", "g-t1", "g-t2", "g-t7", "g-u2", "g-t5", "g-t6"], str(stages))
counts = {st: len(table(st)) for st in stages + ["g-c1f"]}
check("job counts", counts == {"p-c2": 41, "g-u1": 21, "g-c1": 22, "g-t1": 11, "g-t2": 7, "g-t7": 4, "g-u2": 9, "g-t5": 9,
                               "g-t6": 7, "g-c1f": 16}, str(counts))
for st in stages + ["g-c1f"]:
    rows, ps = table(st), preds(st)
    names = [r["name"] for r in rows]
    check(f"{st}: job names unique", len(names) == len(set(names)))
    # the x job of a pair carries the predictions of its configuration; y jobs have none; every other row has some
    has = lambda n: n in ps
    need = [n for n in names if not (st == "p-c2" and n.endswith("-y"))]
    miss = [n for n in need if not has(n)]
    check(f"{st}: every row has a frozen prediction (a y job of a pair is read with its x job)", not miss, str(miss))
    orphan = [n for n in ps if n not in names]
    check(f"{st}: no prediction without a row", not orphan, str(orphan))
    badlab = [(n, p) for n, lst in ps.items() for p in lst if p[3] not in ("control", "heldout", "repeat", "replicate") or not p[2].strip()]
    check(f"{st}: every prediction names a hypothesis and a label", not badlab, str(badlab[:2]))
    setmis = []
    for r in rows:
        labs = {p[3] for p in ps.get(r["name"], []) if p[0] not in ("knob0624_first", "marker", "kicks_open")}
        if labs and r["set"] == "control" and "control" not in labs:
            setmis.append(r["name"])
        if labs and r["set"] == "heldout" and not labs & {"heldout"}:
            setmis.append(r["name"])
    check(f"{st}: a control row has control predictions, a held-out row held-out predictions", not setmis, str(setmis))
    check(f"{st}: controls first", [r["set"] for r in rows] == sorted([r["set"] for r in rows], key=lambda s: s != "control"))
    check(f"{st}: no hypothesis row and no unknown knob", all(not re.search(r"hypo:", r["knobs"]) and
          all(k in ("stophang", "expectdiff", "noreset", "s072c") or k.startswith("trial072c:") for k in r["knobs"].split())
          for r in rows))
    check(f"{st}: every tri row has expectdiff, a multi-render one --keep-going",
          all("expectdiff" in r["knobs"].split() and (" -n " not in r["args"] or re.search(r"-n 1\b", r["args"]) or "--keep-going" in r["args"])
              for r in rows if r["args"].startswith("tri ")))
    check(f"{st}: no poke, kreg or kpoke option", not any(re.search(r"--poke|--kpoke|--kreg|--late|--ctx2", r["args"]) for r in rows))
    for ln in (R1 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln.startswith("#need "):
            f = R1 / "bins" / ln.split("/")[-1]
            if not f.exists():
                check(f"{st}: staged program {f.name}", False)
    # every $S/ file the commands use is in the #need list
    needs = {ln.split("/")[-1].strip() for ln in (R1 / "tables" / f"{st}.txt").read_text().splitlines() if ln.startswith("#need ")}
    used = {m for r in rows for m in re.findall(r'\$S/([A-Za-z0-9_.:-]+?\.bin)', r["args"])}
    check(f"{st}: every program a command names is in the #need list (and so in the freeze)", used <= needs, str(used - needs))
u1 = table("g-u1")
check("g-u1: u-ctl-1 and u-ctl-2a are the 0x072c trial rows (U 19 and 29), first in the table; every other row is s072c",
      u1[0]["name"] == "u-ctl-1" and "trial072c:19" in u1[0]["knobs"] and u1[1]["name"] == "u-ctl-2a"
      and "trial072c:29" in u1[1]["knobs"] and all("s072c" in r["knobs"] for r in u1[2:]) and
      sum("trial072c" in r["knobs"] for r in u1) == 2)
for st in ("g-c1", "g-c1f", "g-u2"):
    check(f"{st}: every DPM row samples 0x072c only through the gate (knob s072c), list 0x0720-0x0724",
          all("s072c" in r["knobs"].split() and "0x0720-0x0724" in r["rt"] for r in table(st)))
check("the T-stages and p-c2 have no timeline and no 0x072c", all(r["rt"] == "-" and "072c" not in r["knobs"]
      for st in ("p-c2", "g-t1", "g-t2", "g-t7", "g-t5", "g-t6") for r in table(st)))
pairs = {r["name"]: r["P"] for r in table("g-u1") if r["name"].startswith("b-")}
check("g-u1 boundary pairs: b-2-m96 at 0x39 / 0x3a, b-m32 at 0x36 / 0x37",
      pairs == {"b-2-m96-lo": "0x39", "b-2-m96-hi": "0x3a", "b-m32-lo": "0x36", "b-m32-hi": "0x37"}, str(pairs))
c1 = {r["name"]: r["P"] for r in table("g-c1")}
check("g-c1: 2 controls, 15 fine cells 0x362..0x37e at 1500 and 5 cells at 1350 (22 jobs)",
      c1["c-1500-0x360"] == "0x360" and c1["c-1500-0x380"] == "0x380" and sum(n.startswith("f-1500-") for n in c1) == 15
      and sorted(n for n in c1 if n.startswith("f-1350-")) == ["f-1350-0x366", "f-1350-0x36e", "f-1350-0x372", "f-1350-0x376", "f-1350-0x37a"])
check("g-c1f: the 16 odd step-1 candidates 0x361..0x37f", [r["P"] for r in table("g-c1f")] == [hex(p) for p in range(0x361, 0x380, 2)])
# the programs assemble and the freeze verifies
r = subprocess.run([str(R1 / "run/freeze_r1.sh"), "verify"], capture_output=True, text=True)
check("the freeze verifies (FROZEN.sha256 and PREDICTIONS.sha256)", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
sys.exit(0 if ok else 1)
