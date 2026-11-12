#!/usr/bin/env python3
"""test_q086.py (run with PY; exit 0/1): stage q086 of r7-rp.
 1. argv-twin against plan rows typed by hand (plan 3.7), 2. the real t4 mock accepts every row and writes its kpokes,
 3. the scorer replays E886's kept 10 rows under their real names (H-COV 9 of 9, H-ANY fails; doctored R fails; renamed: cannot tell),
 4. every control on a doctored input fails; refuse_unreadable passes (and refuses an unreadable control),
 5. the world: the frozen verdict for `model`, the rival verdict for each rival word, the stops."""
import gzip
import os
import re
import shlex
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import g_q086 as G  # noqa: E402
import realmock  # noqa: E402
import score_q086 as S  # noqa: E402
import scorekit  # noqa: E402
import world_q086 as W  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
bad = n = 0
TMP = tempfile.mkdtemp(prefix="q086.", dir=os.path.join(KP, "debug"))
HDR = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


G.write(KP)
ROWS = []
for ln in open(os.path.join(KP, "tables", "q086.txt")).read().splitlines():
    if ln and not ln.startswith("#"):
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        ROWS.append(dict(name=name, set=sset, knobs=knobs.split(), tool=tool, args=args, argv=shlex.split(args)))
hdr = [ln for ln in open(os.path.join(KP, "tables", "q086.txt")) if ln.startswith("#")]
check(hdr[0].strip() == "#stage q086" and hdr[1].strip() == "#limit 6", "table header: #stage q086, #limit 6")
check(not any(l.startswith("#need") for l in hdr), "no staged program needed")


def opt(a, k, cast=str):
    return cast(a[a.index(k) + 1]) if k in a else None


def kps(a):
    return sorted(opts(a, "--kpoke-render"))


def opts(a, k):
    return [a[i + 1] for i, t in enumerate(a) if t == k]


# ---- 1. twin: typed by hand from plan 3.7 (name, w, h, kind, kpokes)
U2K = ["1:ta:143=0x01806006", "1:ta:144=0x01806006", "1:ta:146=0x24"]
FXK = ["1:ta:143=0x00802002", "1:ta:144=0x00802002", "1:ta:146=0x4"]
PLAN = [("q086-1024x768-R", 1024, 768, [], "expectdiff strict"),
        ("q086-320x160-U2", 320, 160, U2K, "expectdiff strict hypo:u:1"),
        ("q086-320x160-FX", 320, 160, FXK, "expectdiff strict expectfault hypo:fx:1"),
        ("q086-448x160-R", 448, 160, [], "expectdiff strict"), ("q086-448x160-U2", 448, 160, U2K, "expectdiff strict hypo:cov:4"),
        ("q086-320x224-R", 320, 224, [], "expectdiff strict"), ("q086-320x224-U2", 320, 224, U2K, "expectdiff strict hypo:cov:4"),
        ("q086-416x192-R", 416, 192, [], "expectdiff strict"), ("q086-416x192-U2", 416, 192, U2K, "expectdiff strict hypo:cov:4"),
        ("q086-384x208-R", 384, 208, [], "expectdiff strict"), ("q086-384x208-U2", 384, 208, U2K, "expectdiff strict hypo:cov:4")]
check([r["name"] for r in ROWS] == [p[0] for p in PLAN], "11 rows in the plan's order (bridges, then R then poked per size)")
FOURX = ["--aa4", "--tri-full", "--keep-going", "--pixels", "cmd:1=0xe0000000", "cmd:10=0xeaa26e26", "cmd:13=0x80000002", "cmd:16=0xeaa26e26"]
for r, (name, w, h, kp, knobs) in zip(ROWS, PLAN):
    a = r["argv"]
    check(a[0] == "tri" and r["tool"] == "t4" and (opt(a, "--width", int), opt(a, "--height", int)) == (w, h)
          and (opt(a, "--max-width", int), opt(a, "--max-height", int)) == (w, h) and sorted(kp) == kps(a)
          and all(t in a for t in FOURX) and opt(a, "--wait-ms") == "20000" and len(opts(a, "--poke")) == 4
          and " ".join(r["knobs"]) == knobs and not any(t.startswith("--depth") for t in a),
          "twin %s: %d x %d on its own 4x context, kpokes %s, knobs %s" % (name, w, h, " ".join(kp) or "none", knobs))
e886 = shlex.split([ln.split("|", 5)[5] for ln in open("/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/tables/q086.txt")
                    if ln.startswith("q086-320x160-FX|")][0])
check([r for r in ROWS if r["name"] == "q086-320x160-FX"][0]["argv"] == e886, "twin: the FX bridge is E886's command token for token")
e886u = shlex.split([ln.split("|", 5)[5] for ln in open("/Users/jtorra/src/scratch/resgx545/closing6/r6-misc/tables/q086.txt")
                     if ln.startswith("q086-320x160-U2|")][0])
check([r for r in ROWS if r["name"] == "q086-320x160-U2"][0]["argv"] == e886u, "twin: the U2 bridge is E886's command token for token")

# frozen predictions typed by hand: (grid 12 x 12 vs tiles) per rule, in the plan's table order COV, X, Y, AREA
HAND = {"q086-448x160-U2": "fault fault ok ok", "q086-320x224-U2": "fault ok fault ok",
        "q086-416x192-U2": "fault fault ok fault", "q086-384x208-U2": "fault ok fault fault"}
P = S.load_preds("q086")
for nm, want in HAND.items():
    check(" ".join(P[nm]["class"][m] for m in ("H-COV", "H-X", "H-Y", "H-AREA")) == want and P[nm]["class"]["H-ANY"] == "ok",
          "frozen %s: COV X Y AREA = %s" % (nm, want))
check(all(P["q086-%s-R" % s]["class"][m] == "ok" for s in ("448x160", "320x224", "416x192", "384x208", "1024x768") for m in S.MODELS),
      "frozen: every R control ok under every rule")
check(P["q086-320x160-FX"]["class"]["H-COV"] == "fault" and all(P["q086-320x160-FX"]["class"][m] == "fault" for m in S.MODELS[:4])
      and P["q086-320x160-U2"]["class"]["H-COV"] == "ok", "frozen: FX bridge faults under every rule, U2 bridge ok")
check(P["q086-448x160-U2"]["cover"]["H-COV"] == "12,12 of 14,10" and P["q086-384x208-U2"]["words"]["all"] == "0x01806006,0x01806006,0x24",
      "frozen: U2's words describe 12 x 12 (cover 12,12 of 14,10 at 448 x 160)")
check(not any(r["set"] == "heldout" and "hypo:cov:4" not in r["knobs"] for r in ROWS)
      and not any(k.startswith("hypo") for r in ROWS if r["name"].endswith("-R") for k in r["knobs"]),
      "groups: poked rows hypo:cov:4 (4 faults at most, none skipped), R controls no hypo (a fault there stops, rc 4)")

# ---- 2. the real t4 mock
for r in ROWS:
    rc, out, err, kpl, wd = realmock.run("t4", r["args"])
    want = [k.replace("1:", "") for k in kps(r["argv"])]
    w, h = opt(r["argv"], "--width", int), opt(r["argv"], "--height", int)
    check(rc == 0 and "job: ok" in out and ("diff: 0 of %d pixels" % (w * h)) in out and sorted(kpl) == sorted(want)
          and len(re.findall(r"^row \d+: ", out, re.M)) == h and "targets up to %dx%d" % (w, h) in out,
          "t4 mock %s: parses, completes, %d pixel rows, kpokes written %s" % (r["name"], h, " ".join(want) or "none"))
    shutil.rmtree(wd, ignore_errors=True)

# ---- 3. replay on E886's kept rows, real names
E = DATA + "/render/closing-r6-misc/out/20261112-144153/q086"


def e886_preds():
    Pe = {}
    for ln in open(E + "/cases.tsv").read().splitlines()[1:]:
        c = ln.split("\t")
        nm = c[0]
        w, h = (int(x) for x in re.match(r"q086-(\d+)x(\d+)-", nm).groups())
        kp = {int(i): int(v, 16) for i, v in re.findall(r"1:ta:(\d+)=(0x[0-9a-f]+)", c[6])}
        Pe[nm] = {"set": "control" if nm.endswith("-R") else "heldout", "size": {"all": "%dx%d" % (w, h)}, "cover": {"H-COV": "-"},
                  "class": {m: "ok" if G.completes(m, w, h, kp) else "fault" for m in S.MODELS},
                  "needs": {"all": "-" if nm.endswith("-R") else "q086-1024x768-R"}}
    return Pe


Pe = e886_preds()
d1 = os.path.join(TMP, "e886")
shutil.copytree(E, d1)
summ, _ = S.score("q086", d1, Pe)
check(summ.startswith("Q086: H-COV held (9 of 9 rows)") and "H-ANY refuted (6 of 9 rows)" in summ and "controls pass 1 of 1" in summ,
      "replay E886: H-COV 9 of 9, H-ANY fails (6 of 9): " + summ[:150])
print("     (E886 under the other rules: %s)" % "; ".join(s for s in summ.split("; ")[0].split(", ")[1:4]))
# doctored R: one wrong pixel (diff line + a pixel word)
d2 = os.path.join(TMP, "e886-wrongdiff")
shutil.copytree(E, d2)
p = d2 + "/q086-1024x768-R.txt.gz"
txt = gzip.open(p, "rt").read().replace("diff: 0 of 786432", "diff: 1 of 786432")
gzip.open(p, "wt").write(txt)
summ, _ = S.score("q086", d2, Pe)
check(summ.startswith("Q086: cannot tell"), "replay: R with a wrong diff line is cannot tell, never a pass: " + summ[:90])
d3 = os.path.join(TMP, "e886-wrongpix")
shutil.copytree(E, d3)
p = d3 + "/q086-1024x768-R.txt.gz"
txt = gzip.open(p, "rt").read().replace("0xff00ff00", "0xff203040", 1)
gzip.open(p, "wt").write(txt)
summ, _ = S.score("q086", d3, Pe)
check(summ.startswith("Q086: cannot tell"), "replay: R with one wrong pixel word (diff line untouched) is cannot tell: " + summ[:90])
d4 = os.path.join(TMP, "e886-renamed")
shutil.copytree(E, d4)
os.rename(d4 + "/q086-1024x768-R.txt.gz", d4 + "/q086-1024-R.txt.gz")
summ, _ = S.score("q086", d4, Pe)
check(summ.startswith("Q086: cannot tell"), "replay: a renamed R file is cannot tell: " + summ[:90])
d5 = os.path.join(TMP, "e886-renamed-u2")
shutil.copytree(E, d5)
os.rename(d5 + "/q086-320x160-U2.txt.gz", d5 + "/q086-320x160-U2x.txt.gz")
summ, _ = S.score("q086", d5, Pe)
check("H-COV held (8 of 8 rows; 1 cannot tell)" in summ, "replay: a renamed held-out file is one cannot tell row, never a pass: " + summ[:90])

# ---- 4. controls, doctored; refuse_unreadable
by = {r["name"]: r["args"] for r in ROWS}
scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), by[c["name"]]) for c in G.controls()}, G.producible)
check(True, "refuse_unreadable passes for %d controls (%s)" % (len(G.controls()), ", ".join(c["name"] for c in G.controls())))
try:
    scorekit.refuse_unreadable({"x": (("diff", "pixels"), by["q086-448x160-R"].replace("--pixels", ""))}, G.producible)
    check(False, "refuse_unreadable refuses a control whose row cannot print the pixels")
except scorekit.ControlReadError:
    check(True, "refuse_unreadable refuses a control whose row cannot print the pixels")
check([c["name"] for c in G.controls()] == ["q086-1024x768-R", "q086-320x160-FX"] + ["q086-%s-R" % s for s in ("448x160", "320x224", "416x192", "384x208")],
      "controls: the five R rows and the FX bridge")


# ---- 5. the world
def kept(d, world):
    """A kept dir as the runner writes it: group skips, stop rc 19 (FX completed, expectfault), stop on a TA-side fault (rc 18)."""
    os.makedirs(d, exist_ok=True)
    toks = set(world.split(","))
    cases, cnt, skipped, stop = [HDR], {}, set(), None
    for r in ROWS:
        if stop:
            break
        g = [k for k in r["knobs"] if k.startswith("hypo:")]
        grp, gmax = (g[0].split(":")[1], int(g[0].split(":")[2])) if g else ("", 0)
        if grp in skipped:
            continue
        a = shlex.split(r["args"])
        assert W.handles(r["tool"], a)
        o = W.answer(r["tool"], a, toks)
        for suf, t in ((".txt", o["out"]), (".err", o["err"]), (".dmesg", "\n".join(o["kmsg"]))):
            with gzip.open(os.path.join(d, r["name"] + suf + ".gz"), "wb") as f:
                f.write(t.encode())
        cls = "fault" if o["kmsg"] else ("ok" if o["rc"] == 0 or (o["rc"] == 1 and "diff:" in o["out"]) else "fail")
        fi = fw = "-"
        if o["kmsg"]:
            m = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", o["kmsg"][0])
            fi, fw = str(int(m.group(1), 16) & 0xFFFF), m.group(2)
            cnt[grp] = cnt.get(grp, 0) + 1
            if grp and cnt[grp] >= gmax:
                skipped.add(grp)
            if not (fi == "256" and fw.startswith("0x100000")):
                stop = 18
        if "expectfault" in r["knobs"] and cls == "ok":
            stop = 19
        if cls == "fault" and not grp:
            stop = 4
        cases.append("\t".join([r["name"], "q086", r["set"], "risky", " ".join(r["knobs"]), "t4", r["args"], str(o["rc"]), cls, fi, fw, "1"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").writelines(cases)
    return stop


def verdict_of(world):
    d = os.path.join(TMP, "w-" + world.replace(",", "_"))
    stop = kept(d, world)
    summ, _ = S.score("q086", d)
    return summ, stop, d


s, stop, d = verdict_of("model")
check(s.startswith("Q086: H-COV held (4 of 4 rows), H-X refuted (2 of 4 rows), H-Y refuted (2 of 4 rows), H-AREA refuted (2 of 4 rows), "
                   "H-ANY refuted (0 of 4 rows); bridges: 320x160-U2 ok, 320x160-FX fault; controls pass 5 of 5")
      and s.endswith("11 unrun E886 rows not pursued, by design") and stop is None, "world model: " + s)
check(S.main(["x", "gate", "q086", d]) == 0 and S.verdict(os.path.dirname(d))[0].startswith("SUMMARY: Q086: not run"),
      "gate 0; verdict() of an attempt dir without q086 is `not run`")
os.makedirs(os.path.join(TMP, "att"))
shutil.copytree(d, os.path.join(TMP, "att", "q086"))
check(S.verdict(os.path.join(TMP, "att"))[0].startswith("SUMMARY: Q086: H-COV held"), "verdict(att_dir) prints the stage's SUMMARY line")
for word, who in (("hx", "H-X"), ("hy", "H-Y"), ("harea", "H-AREA")):
    s, stop, _ = verdict_of(word)
    held = [m for m in S.MODELS if "%s held" % m in s]
    check(held == [who] and stop is None, "world %s: only %s holds: %s" % (word, who, s[:110]))
s, stop, _ = verdict_of("fxok")
check(stop == 19 and s.startswith("Q086: bridge 320x160-FX completed: E886 depended on the old module"), "world fxok: rc 19, bridge FX named, rows unscored: " + s[:100])
s, stop, _ = verdict_of("tafault")
check(stop == 18 and all("%s refuted" % m in s for m in S.MODELS), "world tafault: rc 18 and every rule refuted (the fault is not 3D side): " + s[:110])
s, stop, _ = verdict_of("ctlfail")
check(s.startswith("Q086: cannot tell") and stop is None, "world ctlfail: R controls with wrong pixels -> cannot tell: " + s[:110])
# a new-size R control that fails gates only its own row
d = os.path.join(TMP, "w-model")
q = os.path.join(TMP, "w-onectl")
shutil.copytree(d, q)
p = q + "/q086-416x192-R.txt.gz"
gzip.open(p, "wt").write(gzip.open(p, "rt").read().replace("diff: 0 of", "diff: 9 of"))
s, _ = S.score("q086", q)
check("H-COV held (3 of 3 rows; 1 cannot tell)" in s and "controls pass 4 of 5" in s, "one failed R control: its row is cannot tell, the others count: " + s[:100])
check(scorekit.missing_files(S.REQUIRED["q086"], d, [r["name"] for r in ROWS]) == [], "every file the scorer reads is kept by the runner's naming")
shutil.rmtree(TMP, ignore_errors=True)
print("%d of %d checks" % (n - bad, n))
sys.exit(1 if bad else 0)
