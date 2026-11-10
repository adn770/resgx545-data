#!/usr/bin/env python3
"""The generated tables and frozen predictions: stage order and job counts, every row has its frozen prediction with a
hypothesis label and a set that matches the row's, held-out / repeat / control rows are the ones the decisions name, faults
are last, every tri row carries expectdiff and --keep-going, every probe row of the safe D stage but d-ok-64 carries
expectnopix, the staged programs exist and are frozen, no table uses a forbidden option, scratch lines match the pages, the
image file matches the prediction hashes, and the frozen files verify.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R2 / "gen"))
sys.path.insert(0, str(R2 / "score"))
import r2lib as L  # noqa: E402
import r2models as M  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R2 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5))))
    return rows


def preds(f):
    out = collections.defaultdict(list)
    for ln in (R2 / "predictions" / f).read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R2 / "stages.txt").read_text().split()
cond = (R2 / "conditional.txt").read_text().split()
check("stage order (R2-7 to R2-9): D2 safe, D2 faults, A2 safe, A2 faults; the slack pair conditional",
      stages == ["r2-d-safe", "r2-d-fault", "r2-a-safe", "r2-a-fault"] and cond == ["r2-a-slack"], f"{stages} {cond}")
T = {st: table(st) for st in stages + cond}
check("job counts", {k: len(v) for k, v in T.items()} == {"r2-d-safe": 5, "r2-d-fault": 2, "r2-a-safe": 4, "r2-a-fault": 2, "r2-a-slack": 3})
check("D2 order: d-ok-64, 19, 19x, 18x, 18, then (faults last) 17, 16",
      [r["name"] for r in T["r2-d-safe"] + T["r2-d-fault"]] == ["d-ok-64", "d-L2e2-19", "d-L2e2-19x", "d-L2e2-18x", "d-L2e2-18", "d-L2e2-17", "d-L2e2-16"])
check("A2 order: a4, a1, a2, a3, then held a5, a6 (last)", [r["name"] for r in T["r2-a-safe"] + T["r2-a-fault"]] ==
      ["a4-ctl-320x400-te20", "a1-256x160-dump", "a2-320x128-dump", "a3-256x160-rep", "a5-320x400-max544", "a6-320x400-max320"])
check("slack order: control, held sa5, held control sa6 last", [r["name"] for r in T["r2-a-slack"]] == ["sa4-ctl-288x656-te20", "sa5-288x656-max544", "sa6-288x656-max288"])
PD, PA = preds("r2-d.tsv"), preds("r2-a.tsv")
sets = {r["name"]: r["set"] for st in T.values() for r in st}
check("D2 sets: ok-64, 19, 19x, 16 control; 18x and 17 held out; 18 repeat (a retrodiction: tallied apart)",
      {k: sets[k] for k in ("d-ok-64", "d-L2e2-19", "d-L2e2-19x", "d-L2e2-18x", "d-L2e2-18", "d-L2e2-17", "d-L2e2-16")} ==
      {"d-ok-64": "control", "d-L2e2-19": "control", "d-L2e2-19x": "control", "d-L2e2-18x": "heldout", "d-L2e2-18": "repeat", "d-L2e2-17": "heldout", "d-L2e2-16": "control"})
check("A2 sets: a4, a6 control; a1, a2, a5 held out; a3 replicate; slack: sa4, sa6 control, sa5 held out",
      [sets[k] for k in ("a4-ctl-320x400-te20", "a1-256x160-dump", "a2-320x128-dump", "a3-256x160-rep", "a5-320x400-max544", "a6-320x400-max320", "sa4-ctl-288x656-te20", "sa5-288x656-max544", "sa6-288x656-max288")] ==
      ["control", "heldout", "heldout", "replicate", "heldout", "control", "control", "heldout", "control"])
for f, P, sts in (("r2-d", PD, ("r2-d-safe", "r2-d-fault")), ("r2-a", PA, ("r2-a-safe", "r2-a-fault", "r2-a-slack"))):
    names = [r["name"] for st in sts for r in T[st]]
    miss = [n for n in names if n not in P]
    check(f"{f}: every row has a frozen prediction", not miss, str(miss))
    check(f"{f}: no prediction without a row", not [n for n in P if n not in names])
    check(f"{f}: every prediction names a hypothesis and a set, and the set is the row's",
          not [(n, p) for n, lst in P.items() for p in lst if p[3] != sets[n] or not p[2].strip()])
    check(f"{f}: no duplicate (case, quantity, hypothesis)", all(len({(q, m) for q, v, m, s in lst}) == len(lst) for lst in P.values()))
allrows = [r for st in T.values() for r in st]
tri = [r for r in allrows if r["args"].startswith("tri ")]
check("every tri row carries expectdiff and --keep-going (a never-control without expectdiff stopped S3's a4)",
      all("expectdiff" in r["knobs"].split() and "--keep-going" in r["args"] for r in tri) and len(tri) == 9, str(len(tri)))
check("every row has stophang or a hypothesis group or is a held row with one", all(re.search(r"stophang|hypo:|expectnopix", r["knobs"]) for r in allrows))
check("D2 safe rows but d-ok-64 carry expectnopix (S1b's d-L2e2-18 rc 3 stopped its stage as a failure)",
      all("expectnopix" in r["knobs"] for r in T["r2-d-safe"] if r["name"] != "d-ok-64") and "expectnopix" not in T["r2-d-safe"][0]["knobs"])
check("the fault rows are hypothesis rows of their own groups (one event each)",
      [r["knobs"] for r in T["r2-d-fault"]] == ["hypo:d17:1", "hypo:d16:1"])
check("a5, a6, sa5, sa6 are held, with regtimeline registers, in the hypothesis group (E1's row rides a6)",
      all(re.search(r"(^| )held( |$)", r["knobs"]) and "hypo:fx:2" in r["knobs"] and r["rt"] == "0x0118,0x012c,0x0c00-0x0c08" for r in T["r2-a-fault"] + T["r2-a-slack"][1:]))
check("no other row is held or runs under regtimeline", all("held" not in r["knobs"] and r["rt"] == "-" for st in ("r2-d-safe", "r2-d-fault", "r2-a-safe") for r in T[st]))
# scratch lines against the pages, programs, images
for r in T["r2-d-safe"] + T["r2-d-fault"]:
    pg = int(re.search(r"--scratch-pages (\d+)", r["args"]).group(1))
    sl = [v for q, v, m, s in PD[r["name"]] if q == "scratch_line"]
    check(f"{r['name']}: the scratch-line knob proof is {pg * 4} KiB", sl == [f"({pg * 4} KiB)"], str(sl))
imgs = L.load_images()
for n, (pg, px) in imgs.items():
    h = [v for q, v, m, s in PD[n] if q == "pix_sha256_if_complete"]
    check(f"{n}: the frozen image hashes to the frozen prediction", h == [M.pix_hash(px)] and len(px) == 2048)
check("the frozen images are the model's (19, 19x, 18x) and S1b's A4 (d-ok-64)",
      imgs["d-L2e2-19"][1] == M.image(19) and imgs["d-L2e2-19x"][1] == M.image(19, 1) and imgs["d-L2e2-18x"][1] == M.image(18, 1) and set(imgs) == {"d-ok-64", "d-L2e2-19", "d-L2e2-19x", "d-L2e2-18x"})
check("d-L2e2-19's frozen hash is the hash S1b's measured 19-page image has (byte for byte)",
      [v for q, v, m, s in PD["d-L2e2-19"] if q == "pix_sha256_if_complete"] == [M.pix_hash(M.image(19))])
for st in T:
    txt = (R2 / "tables" / f"{st}.txt").read_text()
    need = set(re.findall(r"^#need \$S/(\S+)", txt, re.M))
    used = set(re.findall(r'"\$S/(\S+?)"', txt))
    check(f"{st}: #need lists exactly the programs the rows use, and they exist", need == used and all((R2 / "bins" / n).exists() for n in need), f"{need ^ used}")
frozen = {ln.split()[1]: ln.split()[0] for ln in (R2 / "FROZEN.sha256").read_text().splitlines()}
check("every staged program, table, scorer, runner script and generator is in FROZEN.sha256",
      all(f"bins/{n}" in frozen for n in {p.name for p in (R2 / "bins").glob("*.bin")}) and all(f"tables/{st}.txt" in frozen for st in T)
      and all(f in frozen for f in ("score/score_r2.py", "score/r2lib.py", "run/run_stage.sh", "run/lib_r2.sh", "run/r2.env", "run/r2.sh", "run/guard_r2.sh", "gen/r2gen.py", "gen/r2models.py", "predictions/r2-d.tsv", "predictions/r2-a.tsv", "predictions/r2-d-images.tsv", "templates/tx_map_x1.s")))
# E727's frozen quantities and the layout
a4 = {q: v for q, v, m, s in PA["a4-ctl-320x400-te20"]}
check("a4 frozen to E727's model: 28 of 128000, first (304, 128), echo 544x400, TA data 0xa000, one array, rgn 0x4000",
      (a4["diff"], a4["diff_first"], a4["max_echo"], a4["tadata_size"], a4["slots_written"], a4["rgn"]) == ("28 of 128000", "(304, 128)", "544x400", "0xa000", "1", "0x4000"))
sa4 = {q: v for q, v, m, s in PA["sa4-ctl-288x656-te20"]}
check("slack control frozen: 605 of 188928, first (272, 208), TA data 0x11000, rgn 0x7000, rgn_size 0x2400",
      (sa4["diff"], sa4["diff_first"], sa4["tadata_size"], sa4["rgn"], sa4["rgn_size"]) == ("605 of 188928", "(272, 208)", "0x11000", "0x7000", "0x2400"))
h = {(q, m): v for q, v, m, s in PA["a5-320x400-max544"]}
check("a5 frozen: H4 completes (diff 0, 0xa000, 4 slots), H5 held 0x90004 at page 0x2000a, status2 0x480",
      (h[("outcome", "H4")], h[("diff", "H4")], h[("tadata_size", "H4")], h[("slots_written", "H4")], h[("int_stat", "H5")], h[("fault_page", "H5")], h[("status2", "H5")]) == ("complete", "0 of 128000", "0xa000", "4", "0x90004", "0x2000a", "0x480"))
h = {(q, m): v for q, v, m, s in PA["sa5-288x656-max544"]}
check("sa5 frozen: H4 completes (diff 0 of 188928, 0x11000, 4 slots), H5 held 0x90004 at page 0x20011",
      (h[("outcome", "H4")], h[("diff", "H4")], h[("tadata_size", "H4")], h[("fault_page", "H5")]) == ("complete", "0 of 188928", "0x11000", "0x20011"))
h = {(q, m): v for q, v, m, s in PD["d-L2e2-17"]}
check("d-L2e2-17 frozen: HL fault 0x90002 at 0x3e017001, HS completes", (h[("outcome", "HL")], h[("fault_word", "HL")], h[("fault_addr", "HL")], h[("outcome", "HS")]) == ("fault", "0x90002", "0x3e017001", "complete"))
check("d-L2e2-18x frozen: HL complete with 0xdeadbeee everywhere; HS rc 3 or another image",
      [(m, v) for q, v, m, s in PD["d-L2e2-18x"] if q == "outcome"] == [("HL", "complete"), ("HS (rc 3)", "rc3 no pixel written"), ("HS (another image)", "other image")])
# forbidden options, programs assemble (the generator asserted the base programs equal S1b's), freeze
alltext = "\n".join((R2 / "tables" / f"{st}.txt").read_text() for st in T)
check("no table uses a forbidden option (kreg, kpoke, ctx2, share-pb, depth, geometry, xfer_ro, --poke of a non-cmd word)",
      not re.search(r"--kreg|--kpoke|kpoke-render|--ctx2|--share-pb|--depth|--geometry|xfer_ro|--poke [^c]|--late|--low|--place", alltext))
check("no table row names a debugfs knob or a register write", not re.search(r"debugfs|hold_recovery|reset|/dev/mem|clkgate|trc_hazard", "\n".join(l for l in alltext.splitlines() if not l.startswith("#"))))
r = subprocess.run([str(R2 / "run/freeze_r2.sh"), "verify"], capture_output=True, text=True)
check("the freeze verifies (FROZEN.sha256, PREDICTIONS.sha256, nothing added since)", r.returncode == 0, (r.stdout + r.stderr).strip()[:200])
print("ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
