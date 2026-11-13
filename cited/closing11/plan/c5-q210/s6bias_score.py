#!/usr/bin/env python3
"""Score the frozen s6bias_rule.py. Reader: copied from resgx545-data/render/closing-r10-dpm/
score/read.py (imported by path); replay R/S from closing-r10-dpm/gen/r9_tables.json."""
import csv, glob, gzip, json, os, re, sys
D = "/Users/jtorra/src/resgx545-data/render"
sys.path.insert(0, D + "/closing-r10-dpm/score")
import read as RD
T = json.load(open(D + "/closing-r10-dpm/gen/r9_tables.json"))["models"]
# extra replay values (same replay, E874): r8-ldpm ol7_tables.json models and r7-dpm
# sibling-src/b/q210_targets.out ("WxH U 0x..: S2 0x.. B .. A ..; S3 0x.. ...")
EXTRA = {}
for k, m in json.load(open(D + "/closing-r8-ldpm/gen/ol7_tables.json"))["models"].items():
    EXTRA[k] = {int(a): int(b, 16) for a, b in m["S"].items()}
for ln in open(D + "/closing-r7-dpm/sibling-src/b/q210_targets.out"):
    wh = ln.split()[0]
    EXTRA.setdefault(wh, {}).update({int(a): int(b, 16) for a, b in re.findall(r"S(\d+) (0x[0-9a-f]+)", ln)})
for k, m in T.items():           # consistency check of the sources on the 13
    for a, b in m["S"].items():
        assert EXTRA.get(k, {}).get(int(a), int(b, 16)) == int(b, 16), (k, a)
BIASED = {(4096, 1024), (4096, 1536), (3584, 1024), (2048, 512), (2048, 2304)}
HELD = {(1280, 1280), (1536, 1536), (1792, 1792), (2048, 2048), (2304, 1792), (2304, 2304),
        (2560, 2048), (4096, 2048)}
FIT_SESS = ("closing-r10-dpm",)         # E1009's own rows
FIT_NAMES = re.compile(r"^(w-cal-c(1604|1606|1404|0802)|m6b-.*c0809.*)")  # E962 calibrations (see NOTE)
def rule(w, h): return "B" if (w * 1.0 / h > 2 or w < h) else "H"
rows = []
for cs in sorted(glob.glob(D + "/closing-r*-*dpm/out/**/cases.tsv", recursive=True)):
    sess = cs.split("/render/")[1].split("/")[0]
    att = os.path.relpath(os.path.dirname(cs), D + "/" + sess + "/out")
    with open(cs) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            a = r.get("args", "")
            mw, mh = re.search(r"--width (\d+)", a), re.search(r"--height (\d+)", a)
            if not (mw and mh): continue
            w, h = int(mw.group(1)), int(mh.group(1))
            mv = re.search(r"--vertices (\d+)", a)
            prog = re.findall(r"(\S+\.bin)", a)
            std = "--vtx-coords" not in a and "--slot" not in a
            variant = f"v{mv.group(1) if mv else '-'}:{os.path.basename(prog[-1]) if prog else '-'}"
            if "--tri" not in a: variant += ":notri"
            p = os.path.join(os.path.dirname(cs), r["name"] + ".txt.gz")
            if not os.path.exists(p): continue
            try:
                rd = RD.reading(gzip.open(p, "rt", errors="replace").read())
            except Exception as e:
                rd = dict(void="exc " + repr(e))
            rows.append(dict(std=std, sess=sess, att=att, name=r["name"], w=w, h=h, variant=variant, rd=rd,
                             set=r.get("set", "")))
def rr(w, h):
    m = T.get(f"{w}x{h}")
    if m is not None: return {int(k): int(v, 16) for k, v in m["S"].items()}
    return EXTRA.get(f"{w}x{h}")
out = {"calib": [], "cell": [], "void": [], "noR": [], "nostep": []}
for x in rows:
    S = rr(x["w"], x["h"]); rd = x["rd"]
    if rd.get("void"): out["void"].append(x); continue
    if S is None: out["noR"].append(x); continue
    if 6 not in rd["steps"]: out["nostep"].append(x); continue
    x["lo"] = {k: rd["iv"][k][0] - S[k] for k in (2, 3, 6) if k in rd["iv"]}
    x["hi6"] = rd["iv"][6][1] - S[6]
    x["lo6abs"] = rd["iv"][6][0]
    out["cell" if rd["nparts"] else "calib"].append(x)
tgt = lambda x: (x["w"], x["h"])
THIRTEEN = BIASED | HELD
def pred(t): return 1 if rule(*t) == "B" else 0      # H-RULE (== H-CLASS on the 13)
kept_E1009 = lambda x: x["sess"] == "closing-r10-dpm" or x["name"] in ("w-cal-c1604", "w-cal-c1606", "w-cal-c1404", "w-cal-c0802", "m6b-cal-c0809")
print("jobs with width/height and output:", len(rows), "| void", len(out["void"]), "| no replay R", len(out["noR"]),
      "| no S6 step", len(out["nostep"]))
print("no-R targets:", sorted({(x["w"], x["h"]) for x in out["noR"]}))
def table(kind, sel, title):
    L = [x for x in out[kind] if sel(x)]
    print(f"\n=== {title}: {len(L)} runs")
    print("target     in13 session          attempt      name                  R     bracket6       d6lo d6hi d2lo d3lo pred fit?")
    for x in sorted(L, key=lambda x: (x["w"], x["h"], x["sess"], x["name"])):
        S = rr(x["w"], x["h"]); lo, hi = x["rd"]["iv"][6]
        print(f"{x['w']}x{x['h']:<5d} {'Y' if tgt(x) in THIRTEEN else 'n'}    {x['sess']:16s} {x['att'][:12]:12s} {x['name'][:20]:20s} 0x{S[6]:<4x} [0x{lo:x},0x{hi:x}] {x['lo'][6]:+5d} {x['hi6']:+4d} "
              f"{x['lo'].get(2,'-')!s:>4} {x['lo'].get(3,'-')!s:>4}  {pred(tgt(x)):d}    {'fit' if kept_E1009(x) else 'held'}")
    return L
def tally(L, title):
    print(f"\n--- {title}")
    by = {}
    for x in L: by.setdefault(tgt(x), []).append(x["lo"][6])
    for t, v in sorted(by.items()):
        h = {}
        for d in v: h[d] = h.get(d, 0) + 1
        print(f"  {t[0]}x{t[1]}: {'13:' + ('BIASED' if t in BIASED else 'HELD') if t in THIRTEEN else 'beyond13'} rule={rule(*t)} n={len(v)} d6lo={dict(sorted(h.items()))} match={sum(d == pred(t) for d in v)}/{len(v)}")
    for nm, p in (("H-CLASS (13 targets only)", lambda t, d: d == (1 if t in BIASED else 0)),
                  ("H-LOW0", lambda t, d: d == 0), ("H-LOWPLUS1", lambda t, d: d == 1),
                  ("H-RULE (all with R)", lambda t, d: d == pred(t))):
        sel = [(tgt(x), x["lo"][6]) for x in L if (nm.startswith("H-CLASS") is False or tgt(x) in THIRTEEN)]
        ok = sum(p(t, d) for t, d in sel)
        print(f"  {nm}: held {ok} failed {len(sel) - ok} of {len(sel)} runs")
for kind in ("calib", "cell"):
    A = table(kind, lambda x: True, f"{kind} runs, all workloads")
    tally(A, f"{kind}: ALL workloads (as first scored, before scoping)")
    Bs = table(kind, lambda x: x["std"], f"{kind} runs, standard workload (no --vtx-coords/--slot) [post hoc scoping]") if False else [x for x in A if x["std"]]
    tally(Bs, f"{kind}: STANDARD workload only [post hoc scoping: exceptions in the first pass are --vtx-coords runs]")
    print("non-standard workload runs:", [(x["sess"], x["name"], x["w"], x["h"], x["lo"][6]) for x in A if not x["std"]])
    print("held-out only (not E1009/E961/E962 rows), standard:")
    H = [x for x in Bs if not kept_E1009(x)]
    tally(H, f"{kind}: held-out standard")
