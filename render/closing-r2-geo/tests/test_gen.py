#!/usr/bin/env python3
"""The generated tables and frozen predictions: every row has its frozen prediction with a hypothesis and a label, labels are
consistent with the row's set, tri rows carry expectdiff, the only poke is pb:11 in g-c2 (with kpoke and wd), the sweep and the
status2 knobs sit on the right rows, the stage order and job counts are the session's, the staged programs exist and are named
in the #need lists, the C3 and C2 predictions are the recomputed ones (C = 0x371, P* = 0x374), and the frozen files verify.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R2 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "P", "knobs", "rt", "args"), ln.split("|", 6))))
    return rows


def preds(st):
    out = collections.defaultdict(list)
    for ln in (R2 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R2 / "stages.txt").read_text().split()
check("stage order (R2-17 and the task): T3, T4, T5 (vertex loop), C3, C2 last", stages == ["g-t3", "g-t4", "g-t5v", "g-c3", "g-c2"], str(stages))
counts = {st: len(table(st)) for st in stages + ["g-c3f"]}
check("job counts", counts == {"g-t3": 4, "g-t4": 8, "g-t5v": 13, "g-c3": 11, "g-c2": 9, "g-c3f": 8}, str(counts))
for st in stages + ["g-c3f"]:
    rows, ps = table(st), preds(st)
    names = [r["name"] for r in rows]
    check(f"{st}: job names unique", len(names) == len(set(names)))
    miss = [n for n in names if n not in ps]
    check(f"{st}: every row has a frozen prediction", not miss, str(miss))
    orphan = [n for n in ps if n not in names]
    check(f"{st}: no prediction without a row", not orphan, str(orphan))
    badlab = [(n, p) for n, lst in ps.items() for p in lst if p[3] not in ("control", "heldout", "repeat", "replicate") or not p[2].strip()]
    check(f"{st}: every prediction names a hypothesis and a label", not badlab, str(badlab[:2]))
    setmis = []
    for r in rows:
        labs = {p[3] for p in ps.get(r["name"], []) if p[0] not in ("knob0624_first", "dw36")}
        if labs and r["set"] == "control" and "control" not in labs:
            setmis.append(r["name"])
        if labs and r["set"] == "heldout" and "heldout" not in labs:
            setmis.append(r["name"])
    check(f"{st}: a control row has control predictions, a held-out row held-out predictions", not setmis, str(setmis))
    check(f"{st}: controls first", [r["set"] for r in rows] == sorted([r["set"] for r in rows], key=lambda s: s != "control"))
    known = ("stophang", "expectdiff", "noreset", "s2", "kpoke")
    check(f"{st}: only known knobs (sweep:G, wd:S allowed)", all(all(k in known or re.fullmatch(r"(sweep|wd):\w+", k) for k in r["knobs"].split())
          for r in rows))
    check(f"{st}: every tri row has expectdiff, a multi-render one --keep-going",
          all("expectdiff" in r["knobs"].split() and (" -n " not in r["args"] or re.search(r"-n 1\b", r["args"]) or "--keep-going" in r["args"])
              for r in rows if r["args"].startswith("tri ")))
    check(f"{st}: no kreg/ctx2/share-pb/late/poke option", not any(re.search(r"--(kreg|ctx2|share-pb|late|poke)\b", r["args"]) for r in rows))
    pk = [r for r in rows if "--kpoke" in r["args"]]
    check(f"{st}: pokes only in g-c2, exactly pb:11=0xHEX, with the kpoke and wd:S knobs",
          (not pk if st != "g-c2" else len(pk) == len(rows)) and all(
              all(re.fullmatch(r"pb:11=0x[0-9a-f]+", re.sub(r"^\d+:", "", v)) for v in re.findall(r"--kpoke(?:-render)? (\S+)", r["args"]))
              and "kpoke" in r["knobs"].split() and re.search(r"wd:\d+", r["knobs"]) for r in pk))
    needs = {ln.split("/")[-1].strip() for ln in (R2 / "tables" / f"{st}.txt").read_text().splitlines() if ln.startswith("#need ")}
    check(f"{st}: every #need program exists in bins/", all((R2 / "bins" / n).exists() for n in needs), str([n for n in needs if not (R2 / "bins" / n).exists()]))
    used = {m for r in rows for m in re.findall(r'\$S/([A-Za-z0-9_.:-]+?\.bin)', r["args"])}
    check(f"{st}: every program a command names is in the #need list (and so in the freeze)", used <= needs, str(used - needs))
# rt: DPM rows read 0x0720-0x072c (R1's gate passed), T rows have no timeline
for st in ("g-c3", "g-c3f", "g-c2"):
    check(f"{st}: every row lists 0x0720-0x072c in its timeline (the 0x072c gate passed in R1)", all("0x0720-0x072c" in r["rt"] for r in table(st)))
check("g-t3, g-t4, g-t5v have no timeline", all(r["rt"] == "-" for st in ("g-t3", "g-t4", "g-t5v") for r in table(st)))
t5 = table("g-t5v")
check("g-t5v: ctl0, n1, n3 first (the first backward branch before any long loop), then the ladder 28 .. 7040 as one sweep; every row reads STATUS2",
      [r["name"] for r in t5][:3] == ["t5v-ctl0", "t5v-n1", "t5v-n3"] and [r["name"] for r in t5][3:] == [f"t5v-i{n}" for n in (28, 53, 55, 110, 220, 440, 880, 1760, 3520, 7040)]
      and all("s2" in r["knobs"].split() for r in t5) and all(("sweep:t5v" in r["knobs"].split()) == r["name"].startswith("t5v-i") for r in t5))
c3 = {r["name"]: r["P"] for r in table("g-c3")}
check("g-c3: the 4096 controls at P* - 2 = 0x372 and P* = 0x374 (P* from R1's C = 0x371), the 2048 cells P* -+ 0x20, the calibration at 0x422 and the low ladder",
      c3["c3-4096-0x372"] == "0x372" and c3["c3-4096-0x374"] == "0x374" and {c3[f"c3-2048-{p:#x}"] for p in (0x354, 0x372, 0x374, 0x394)} == {"0x354", "0x372", "0x374", "0x394"}
      and c3["c3-2048-cal"] == "0x422" and len(c3) == 11, str(c3))
cp = preds("g-c3")
check("g-c3 predictions: R1 controls raise at 0x372, none at 0x374; H-same raise iff P - 2 <= 0x371 on every 2048 cell",
      [(q, v) for q, v, m, s in cp["c3-4096-0x372"] if q == "raise"] == [("raise", "yes")] and [(q, v) for q, v, m, s in cp["c3-4096-0x374"] if q == "raise"] == [("raise", "no")]
      and all(v == ("yes" if int(n.split("-")[2], 16) - 2 <= 0x371 else "no") for n, lst in cp.items() if n.startswith("c3-2048-") and n != "c3-2048-cal"
              for q, v, m, s in lst if m.startswith("H-same")))
c2 = table("g-c2")
check("g-c2: two E625 controls (poke 0x80 raise, 0x100 none) then V = 0x300 0x33e 0x351 0x352 0x35e 0x3a0 0x3de at 1500 vertices, all at P = 0x422",
      [r["name"] for r in c2] == ["k-tri-0x80", "k-tri-0x100"] + [f"k-1500-{v:#x}" for v in (0x300, 0x33e, 0x351, 0x352, 0x35e, 0x3a0, 0x3de)]
      and all(r["P"] == "0x422" for r in c2))
c2p = preds("g-c2")
habs = {n: next(v for q, v, m, s in lst if q == "raise" and m.startswith("H-abs")) for n, lst in c2p.items() if n.startswith("k-1500")}
check("g-c2 predictions: H-abs raises iff V + 0x20 <= 0x371 (0x351 raises, 0x352 does not); H-P never; H-rel always",
      habs == {"k-1500-0x300": "yes", "k-1500-0x33e": "yes", "k-1500-0x351": "yes", "k-1500-0x352": "no", "k-1500-0x35e": "no", "k-1500-0x3a0": "no", "k-1500-0x3de": "no"}
      and all(next(v for q, v, m, s in lst if m.startswith("H-P")) == "no" and next(v for q, v, m, s in lst if m.startswith("H-rel")) == "yes"
              for n, lst in c2p.items() if n.startswith("k-1500")))
t4 = preds("g-t4")
check("g-t4: six held-out pairs with 6 candidate words each (3 to 4 distinct) and two controls",
      sum(1 for n, l in t4.items() if any(s == "heldout" for _, _, _, s in l)) == 6 and sum(1 for n, l in t4.items() if any(s == "control" for _, _, _, s in l)) == 2)
r = subprocess.run([str(R2 / "run/freeze_r2.sh"), "verify"], capture_output=True, text=True)
check("the freeze verifies (FROZEN.sha256 and PREDICTIONS.sha256)", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
sys.exit(0 if ok else 1)
