#!/usr/bin/env python3
"""Generator tests of R3K-regress: counts, order, labels, that every command is its record's command (minus the options this session
drops), that every prediction is the record's value (re-extracted from the records), the forbidden options, and that regenerating
changes nothing.  Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import rgen as G  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("ok   %s" % name)
    else:
        fails += 1
        print("FAIL %s %s" % (name, detail))


def rows(st):
    return [ln.split("|", 5) for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines() if ln and not ln.startswith("#")]


def preds(st):
    return [ln.split("\t") for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]]


check("stages.txt order: rg-ctl, rg-pb", open(os.path.join(KP, "stages.txt")).read().split() == ["rg-ctl", "rg-pb"])
ctl, pb = rows("rg-ctl"), rows("rg-pb")
check("jobs: 23 + 13 = 36 (under the ~45 of the brief)", (len(ctl), len(pb)) == (23, 13), (len(ctl), len(pb)))
check("every row has 6 fields, a unique name, risk safe, rt -", all(len(r) == 6 and r[2] == "safe" and r[4] == "-" for r in ctl + pb)
      and len({r[0] for r in ctl + pb}) == 36)
check("labels: rg-ctl 2 control (dd-p1 and green 16x16, which K0 already reproduced on the new module) + 21 heldout",
      sorted(r[0] for r in ctl if r[1] == "control") == ["ctl-dd-p1", "ctl-green-16x16"] and sum(r[1] == "heldout" for r in ctl) == 21)
check("labels: rg-pb 2 control (E728's own TE 0x20 and 0xe0), replicates for the second and third runs",
      [r[0] for r in pb if r[1] == "control"] == ["pb-e20-m2-64", "pb-ee0-m2-64"]
      and sorted(r[0] for r in pb if r[1] == "replicate") == ["pb-e40-m2-64b", "pb-e40-m2-64c", "pb-n40-b", "pb-n40-c"])
check("every tri row has expectdiff and --keep-going; probe rows have neither a fault knob nor expectdiff",
      all(("expectdiff" in r[3] and "--keep-going" in r[5]) if r[5].startswith("tri ") else ("expectdiff" not in r[3]) for r in ctl + pb))
check("knobs are only expectdiff or stophang; no held, bif, idle, rgn, hypo, noreset anywhere",
      all(set(r[3].split()) <= {"expectdiff", "stophang"} for r in ctl + pb))
allcmd = "\n".join(r[5] for r in ctl + pb)
check("no forbidden option in any command (kreg, kpoke, fault, ctx2, share-pb, depth, regs, words, dump-each, hold, bif)",
      not re.search(r"--kreg|--kpoke|--fault|--ctx2|--share-pb|--depth|--regs|--words|--dump-each|--hold|--bif|kregnow|kicker", allcmd))
check("--poke only cmd: words; --geometry only 1 to 3", not re.search(r"--poke [^c]", allcmd) and not re.search(r"--geometry (?![123]( |$))", allcmd))
check("rg-pb: E728's shapes first (9 single-render rows), K2's shape (-n 2 --geometry 1, 4 rows) last",
      [("-n 2 --geometry 1" in r[5]) for r in pb] == [False] * 9 + [True] * 4)
check("rg-pb: no row has -n or --geometry in an E728-shape command", all("-n " not in r[5] and "--geometry" not in r[5] for r in pb[:9]))
# the commands are their records' commands (minus --pixels --regs --dump-each --words, which this session drops)
def norm(c):
    c = re.sub(r"--regs \S+|--pixels|--words \S+|--dump-each", "", c)
    c = re.sub(r"--dump-render \S+", "--dump-render D", c)
    return " ".join(c.replace("@D@", "D").replace('"$W/dump"', "D").split())


def rec_args(d, name):
    head = None
    for ln in open(os.path.join(d, "cases.tsv")).read().splitlines():
        f = ln.split("\t")
        if head is None:
            head = f
            continue
        if f[0] == name:
            return f[head.index("args")] if "args" in head else f[head.index("options")]
    raise KeyError(name)


bad = []
for case, sset, cmd, d, srcn, dump, rec in G.CTL:
    a = rec_args(d, srcn)
    if d == G.SRC_Q:
        a = a.replace("$S/pix_green.bin", "$S/pix_green.bin")
    if norm(a).replace("--dump-render D", "").strip() != norm(cmd).replace("--dump-render D", "").strip() and not (srcn.startswith("t-ctl") or srcn.startswith("dd")):
        bad.append((case, norm(a), norm(cmd)))
    if srcn.startswith("t-ctl") and norm(a) != norm(cmd):
        bad.append((case, norm(a), norm(cmd)))
    if srcn.startswith("dd") and norm(a) != norm(cmd):
        bad.append((case, norm(a), norm(cmd)))
check("every rg-ctl command is its record's command (g-u1 without --dump-render/--words/--regs; q-t, g-dd, r2-a-safe as recorded)", not bad, bad[:2])
bad = [(c, norm(rec_args(G.SRC_E, srcn)), norm(G.pb_cmd_e(sz, te, md))[4:]) for c, s, sz, te, md, srcn, rc in G.PB_E
       if norm(rec_args(G.SRC_E, srcn)) != norm(G.pb_cmd_e(sz, te, md))[4:]]
check("every E728-shape row is E728's command (p1141 msaa-b-te29 cases.tsv) minus --pixels and --regs", not bad, bad[:1])
k2 = open(os.path.join(G.K2, "cases.tsv")).read().splitlines()
k2a = {ln.split("\t")[0]: ln.split("\t")[6] for ln in k2[1:]}
check("every -n 2 row is K2's k-pb0 command (cases.tsv of the kept stage)",
      all(norm(k2a[k]) == norm(G.pb_cmd_n(te)) for _, _, te, k in G.PB_N), {k: k2a[k][:60] for _, _, _, k in G.PB_N})
# predictions
P = {}
for st in ("rg-ctl", "rg-pb"):
    for case, q, v, m, s, src in preds(st):
        P.setdefault(case, {}).setdefault(m, {})[q] = (v, s, src)
names = [r[0] for r in ctl + pb]
check("every row has frozen predictions and a source (record and kept file)", all(n in P and all(x[2] for mm in P[n].values() for x in mm.values()) for n in names))
check("rg-ctl rows have the single model OLD; E728-shape rows H-OLD; -n 2 rows H-NEW with H-OLD as the alternative",
      all(set(P[r[0]]) == {"OLD"} for r in ctl) and all(set(P[r[0]]) == {"H-OLD"} for r in pb[:9]) and all(set(P[r[0]]) == {"H-NEW", "H-OLD"} for r in pb[9:]))
check("the set of each prediction is its row's set", all(x[1] == next(r[1] for r in ctl + pb if r[0] == n) for n in names for mm in P[n].values() for x in mm.values()))
check("source citations name the E-record or K2 and the kept file", all(("E7" in x[2] or "E8" in x[2] or "K2" in x[2]) for n in names for mm in P[n].values() for x in mm.values()))
g = lambda c, m, q: P[c][m][q][0]
check("known values: E728's TE 0x40 64x64 hash 0xfc5ff15e0434a325 / 128x128 0x980f5ef9846c2325 / the TE 0x20 control 0xd0530839d87ea325",
      g("pb-e40-m2-64a", "H-OLD", "target_hash") == "0xfc5ff15e0434a325" and g("pb-e40-m2-128", "H-OLD", "target_hash") == "0x980f5ef9846c2325"
      and g("pb-e20-m2-64", "H-OLD", "target_hash") == "0xd0530839d87ea325")
check("known values: K2's k-pb0 value 0x8ea26cdfee74a325 (TE 0x40), 0xd2bfb75560f4c325 (TE 0x60 twin row); E728 words 0,0x40101 at dwords 11,12",
      g("pb-n40-a", "H-NEW", "target_hash") == "0x8ea26cdfee74a325" and g("pb-n60", "H-NEW", "target_hash") == "0xd2bfb75560f4c325"
      and g("pb-e40-m2-64a", "H-OLD", "par_11_26").startswith("00000000,00040101,"))
check("known values: g-u1 u-ctl-1 hash 0xc9e301d225fe2325, the o0 line of dd-p1 and the 16x16 green fill",
      g("ctl-u-1024-n1", "OLD", "target_hash") == "0xc9e301d225fe2325" and g("ctl-dd-p1", "OLD", "probe_o0") == "mixed 0xff203040 x3622 0xff00ff00 x474"
      and g("ctl-green-16x16", "OLD", "probe_o0") == "0xff00ff00 (256 of 256)")
check("a4 (E763): 28 of 128000 wrong, first (304, 128), echo 544x400, TA data 0xa000", g("ctl-a4-320x400-te20-max544", "OLD", "diff") == "28 of 128000"
      and g("ctl-a4-320x400-te20-max544", "OLD", "echo") == "544x400" and g("ctl-a4-320x400-te20-max544", "OLD", "tadata_size") == "0xa000")
check("the TA data sha256 of E728's three TE 0x40 jobs and K2's -n 2 rows is the same (the TA data does not depend on the shape)",
      g("pb-e40-m2-64a", "H-OLD", "tadata_sha256") == g("pb-n40-a", "H-NEW", "tadata_sha256"))
check("the parameter buffer differs between the shapes (the H-NEW sha is not E728's): the quantity that tells the shape",
      g("pb-e40-m2-64a", "H-OLD", "param_sha256") != g("pb-n40-a", "H-NEW", "param_sha256"))
check("staged programs exist in bins/ and every #need line names one", all(os.path.exists(os.path.join(KP, "bins", os.path.basename(x.split(" ", 1)[1].strip()))) for x in
      open(os.path.join(KP, "tables", "rg-ctl.txt")).read().splitlines() if x.startswith("#need ")))
# regeneration changes nothing, and the extraction from the records is the frozen old_values.tsv
T = tempfile.mkdtemp(prefix="rg-gen-")
cp = os.path.join(T, "kp")
shutil.copytree(KP, cp, ignore=shutil.ignore_patterns("out", "tests", "__pycache__"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
subprocess.run([sys.executable, os.path.join(cp, "gen", "rgen.py")], check=True, capture_output=True, env=env)
same = all(open(os.path.join(KP, f)).read() == open(os.path.join(cp, f)).read() for f in
           ["tables/rg-ctl.txt", "tables/rg-pb.txt", "predictions/rg-ctl.tsv", "predictions/rg-pb.tsv", "TABLES.md", "stages.txt"])
check("regenerating from gen/data/old_values.tsv changes nothing", same)
subprocess.run([sys.executable, os.path.join(cp, "gen", "rgen.py"), "extract"], check=True, capture_output=True, env=env)
check("re-extracting from the records gives the same gen/data/old_values.tsv (every prediction is a record's value)",
      open(os.path.join(KP, "gen", "data", "old_values.tsv")).read() == open(os.path.join(cp, "gen", "data", "old_values.tsv")).read())
print("work dir: %s" % T)
sys.exit(1 if fails else 0)
