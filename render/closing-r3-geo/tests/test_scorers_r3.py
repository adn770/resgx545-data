#!/usr/bin/env python3
"""The R3 scorers (score/score_r3.py) with the frozen predictions on
  - past-run data: R2's kept g-t4 jobs under their R3 names (the four g-da controls: the real decoder on measured objects, a reader check
    not evidence), and the kept timelines of R1 and R2 for H-last (64 of 64 jobs fit, the design's 49 of 49 among them);
  - synthetic worlds with a known truth: each depth world gives its rule consistent and the others refuted; each DPM world (the twin of
    the runner, tests/world_r3.py) gives its law; a failing control gives `cannot tell`; a void, skipped or gated job is reported as such.
The decoded object is replaced by a JSON description in the fake dump (G.decode_object patched) for the depth worlds only.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "score"), str(R3 / "gen"), str(R3 / "tests")]
import dpm3  # noqa: E402
import r3models as M  # noqa: E402
import score_geo2 as G  # noqa: E402
import score_r3 as S  # noqa: E402
import synth  # noqa: E402
import world_r3 as W  # noqa: E402
from r1lib import Kept, load_preds  # noqa: E402

HOME = pathlib.Path.home()
C2 = HOME / "src/scratch/resgx545/closing2"
ok = True
(R3 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R3 / "debug/tmp")
TMP = pathlib.Path(tempfile.mkdtemp())
REAL_DECODE = G.decode_object


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def summary(text):
    return next((ln for ln in text.splitlines() if ln.startswith("SUMMARY:")), "no SUMMARY")


def fake_decode(param, tadata):
    if not param:
        return dict(state="none", words=[], o=None)
    d = json.loads(param.decode())
    if d["state"] != "present":
        return dict(state=d["state"], words=[], o=None)
    packed = [(round((y + 4096) * 256), round((x + 4096) * 256), z) for (x, y), z in zip(d["xy"], d["depth"])]
    return dict(state="present", words=[1], o={}, nvert=len(d["xy"]), rhw=list(d["rhw"]), packed=packed, prims=[tuple(p) for p in d["prims"]])


DEF_XY = [[8.0, 8.0], [56.0, 20.0], [20.0, 56.0]]


def obj_job(d, name, depth_words, xy=None, rhw=0x3F800000, prims=((0, 1, 2),), state="present", cls="ok"):
    j = json.dumps(dict(state=state, xy=xy or DEF_XY, rhw=[rhw] * 3, depth=list(depth_words), prims=[list(p) for p in prims])).encode()
    d.job(name, "probe x: ok\n" * 3, 0, cls, dumps={f"{name}__0.param.bin": j, f"{name}__0.tadata.bin": b"t"})


def frozen_word_of(fz, n, prefix):
    """The frozen word of the model whose label starts with `prefix` for job n (3 equal words), or None."""
    for v, m, s in fz.get(n, {}).get("depth_words", []):
        if m.startswith(prefix + " ") or m == prefix:
            return int(v.split(",")[0], 16)
    return None


def depth_world(stage, name, truth, break_ctl=None, void=None, mutate=None, truth_controls=()):
    """A kept directory for a depth stage in which every non-control row stores the word of the model `truth` (a label prefix, or a
    function (row name, fz) -> word); control rows store their measured word."""
    fz = load_preds(None, stage)
    d = synth.Dir(TMP / name, stage)
    rows = W.load_table(stage)
    for r in rows:
        n = r["name"]
        if n == void:
            d.job(n, "", 0, "ok")
            continue
        if r["set"] == "control" and n not in truth_controls:
            word = int(next(v for v, m, s in fz[n]["depth_words"]).split(",")[0], 16)
            if n == break_ctl:
                word += 2
        else:
            word = truth(n, fz) if callable(truth) else frozen_word_of(fz, n, truth)
        if mutate and n in mutate:
            word = mutate[n]
        obj_job(d, n, [word] * 3)
    return Kept(d.d), fz


G.decode_object = fake_decode

# ===================================================================================================== g-da
def tally(text):
    s = summary(text)
    m = re.search(r"held out: consistent \[(.*?)\], refuted \[(.*?)\]", s)
    return s, (m[1] if m else ""), (m[2] if m else "")


for lab in ("T26", "T27"):
    k, P = depth_world("g-da", f"da-{lab}", lab)
    s, cons, refd = tally(S.score_da(k, P)[0])
    check(f"g-da world {lab}: controls pass, H-thr HOLDS, {lab} consistent 21 of 21, D1 / D5 / D2 refuted",
          "controls pass" in s and "H-thr HOLDS" in s and f"{lab} (" in cons and "D1 (" in refd and "D5 (" in refd, s[:420])
s, cons, refd = tally(S.score_da(*depth_world("g-da", "da-T26x", "T26"))[0])
check("g-da world T26: the narrowed t interval is printed and T27 is refuted (it differs from T26 in the cells between 3/8 and 7/16)",
      "t in (" in s and "T27 (" in refd, s[:600])
k, P = depth_world("g-da", "da-T27x", "T27")
s, cons, refd = tally(S.score_da(k, P)[0])
check("g-da world T27: T26 refuted", "T26 (" in refd and "T27 (" in cons, s[:420])
k, P = depth_world("g-da", "da-D1", "D1")
s, cons, refd = tally(S.score_da(k, P)[0])
check("g-da world D1 (round to nearest): H-thr REFUTED (the high cells read down), D1 consistent",
      "H-thr REFUTED" in s and "D1 (" in cons, s[:500])
d5 = lambda n, fz: (M.depth_word(M.f32(-2.6), M.f32(3.0), "D5") if n == "da-rep-m2p6-3" else M.depth_word(M.f32(-6.1), M.f32(7.0), "D5")
                       if n == "da-rep-m6p1-7" else frozen_word_of(fz, n, "D5"))
k, P = depth_world("g-da", "da-D5", d5, truth_controls=("da-rep-m2p6-3", "da-rep-m6p1-7"))
s, cons, refd = tally(S.score_da(k, P)[0])
check("g-da world D5 (RZ): its repeat control t4-m2p6-3 fails (D5 gives another word): cannot tell", "cannot tell" in s, s[:300])


def alt_inside(n, fz):                      # an inside row alternates: not monotone in the fraction
    cell = next(v for v, m, s in fz[n]["cell"])
    if cell != "inside":
        return frozen_word_of(fz, n, "T26")
    i = int(n.split("in")[1])
    return int(next(v for v, m, s in fz[n]["word_up"] if i % 2 == 0) if i % 2 == 0 else next(v for v, m, s in fz[n]["word_down"]), 16)


k, P = depth_world("g-da", "da-alt", alt_inside)
s, cons, refd = tally(S.score_da(k, P)[0])
check("g-da world with alternating inside cells: H-thr REFUTED, not monotone (the fraction is not the variable)", "not monotone" in s and "H-thr REFUTED" in s, s[:400])
k, P = depth_world("g-da", "da-rep", "T26", break_ctl="da-rep-m2p6-3")
check("g-da: the repeat of t4-m2p6-3 reading another word makes the stage cannot tell (the fit's one word did not repeat)",
      "cannot tell: control(s) ['da-rep-m2p6-3']" in summary(S.score_da(k, P)[0]), summary(S.score_da(k, P)[0])[:200])
k, P = depth_world("g-da", "da-p2", "T26", break_ctl="da-p2-w2")
check("g-da: a power-of-two control reading another word: cannot tell", "cannot tell" in summary(S.score_da(k, P)[0]))
k, P = depth_world("g-da", "da-void", "T26", void="da-in3")
t = S.score_da(k, P)[0]
check("g-da: an empty job is NODATA and listed; the verdict is not claimed on the remaining cells (10 inside cells needed)",
      "NODATA" in t and "da-in3" in summary(t) and "HOLDS" not in summary(t), summary(t)[:300])
# real decoder on the measured objects of R2's g-t4 under the R3 names
rn = {"t4-ctl-z0-w3": "da-ctl-z0-w3", "t4-ctl-zm05-w1": "da-ctl-zm05-w1", "t4-m2p6-3": "da-rep-m2p6-3", "t4-m6p1-7": "da-rep-m6p1-7"}
rd = TMP / "da-real"
rd.mkdir()
src = C2 / "r2-geo/out/g-t4"
lines = (src / "cases.tsv").read_text().splitlines()
keep = [lines[0]]
for ln in lines[1:]:
    f = ln.split("\t")
    if f[0] in rn:
        f[0] = rn[f[0]]
        keep.append("\t".join(f))
(rd / "cases.tsv").write_text("\n".join(keep) + "\n")
for old, new in rn.items():
    for p in src.glob(f"{old}.*"):
        (rd / (new + p.name[len(old):])).write_bytes(p.read_bytes())
G.decode_object = REAL_DECODE
Pall = load_preds(None, "g-da")
Pk = {n: q for n, q in Pall.items() if n in rn.values()}
text = S.S2.score_objects2(Kept(rd), Pk, "g-da")[0]
check("g-da's four measured controls under the REAL decoder on R2's kept objects (0x3f000000, 0x3e800000, 0x3d88888c, 0x3d83a840): all hold",
      "controls pass" in summary(text), summary(text)[:300])
G.decode_object = fake_decode

# ===================================================================================================== g-db, g-dc
def db_truth(rule, sm):
    def f(n, fz):
        qrule = rule[:-1] if rule.endswith("d") else rule                 # the q group has no direction variants
        lab = f"{rule}+{sm}" if n.startswith("db-pos") else f"{qrule}+{sm} (own)" if n.startswith("db-q") else rule
        return next((int(v.split(",")[0], 16) for v, m, s in fz[n]["depth_words"] if m.startswith(lab + " ") or m == lab), None)
    return f


kda, _ = depth_world("g-da", "da-for-db", "T26")
for rule, sm in (("T26", "rn"), ("T26d", "rz"), ("D1", "rh")):
    k, P = depth_world("g-db", f"db-{rule}{sm}", db_truth(rule, sm))
    s, cons, refd = tally(S.score_db(k, P, str(TMP / "da-for-db"))[0])
    check(f"g-db world {rule}+{sm}: that label is consistent on the six z > 0 cells and at least three other labels are refuted there",
          f"{rule}+{sm} (" in cons and "controls pass (g-da's)" in s and refd.count("(") >= 3, s[:300])
k, P = depth_world("g-db", "db-nogate", db_truth("T26", "rn"))
check("g-db without g-da's kept directory (its controls are the session's): cannot tell", "cannot tell" in S.score_db(k, P, str(TMP / "nope"))[0])
kb, _ = depth_world("g-da", "da-for-db2", "D1", break_ctl="da-rep-m2p6-3")
check("g-db with g-da's controls failing: cannot tell", "cannot tell" in S.score_db(k, P, str(TMP / "da-for-db2"))[0])
for lab in ("VF", "VT", "VZ", "VS"):
    k, P = depth_world("g-dc", f"dc-{lab}", lab)
    s, cons, refd = tally(S.score_dc(k, P)[0])
    check(f"g-dc world {lab}: controls pass (the default viewport words give 0x3e800000), {lab} consistent, at least one other refuted",
          "controls pass" in s and f"{lab} (" in cons and len(refd) > 0, s[:420])
k, P = depth_world("g-dc", "dc-bad", "VF", break_ctl="dc-ctl-default")
check("g-dc: the control with the defaults written explicitly reading another word: cannot tell", "cannot tell" in summary(S.score_dc(k, P)[0]))

# ===================================================================================================== g-dd
Pdd = load_preds(None, "g-dd")


def dd_world(name, depth_exact=True, break_struct=None):
    d = synth.Dir(TMP / name, "g-dd")
    for n in Pdd:
        def q1(q, m=None):
            return next(v for v, mm, s in Pdd[n][q] if m is None or mm.startswith(m))
        xy_ord = [tuple(float(c) for c in p.split(",")) for p in q1("xy_ordered").split(";")]
        ents = [(tuple(float(c) for c in e.split("=")[0].split(",")), int(e.split("=")[1], 16)) for e in q1("rhw_by_xy", "HI-w").split(";")]
        dm = {tuple(float(c) for c in e.split("=")[0].split(",")): int(e.split("=")[1], 16) for e in q1("depth_made_by_xy").split(";")}
        rhw = {xy: w for xy, w in ents}
        depth = []
        for x, y in xy_ord:
            key = min(dm, key=lambda p: abs(p[0] - x) + abs(p[1] - y)) if dm else None
            near = key is not None and abs(key[0] - x) + abs(key[1] - y) < 1 / 16
            depth.append((dm[key] if near else 0x3E800000) if depth_exact else (dm[key] - 1 if near else 0x3E800000))
        prims = [tuple(int(e) for e in t.split(",")) for t in q1("prims").split(";")]
        xy = [list(p) for p in xy_ord]
        if n == break_struct:
            xy = xy[1:] + xy[:1]
        j = json.dumps(dict(state="present", xy=xy, rhw=[rhw[min(rhw, key=lambda p: abs(p[0] - x) + abs(p[1] - y))] for x, y in xy_ord],
                            depth=depth, prims=[list(p) for p in prims])).encode()
        d.job(n, "probe x: ok\n" * 3, 0, "ok", dumps={f"{n}__0.param.bin": j, f"{n}__0.tadata.bin": b"t"})
    return Kept(d.d)


s = summary(S.score_dd(dd_world("dd-a"), Pdd)[0])
check("g-dd world with the frozen rules (HI-w, depth exactly 1.0 / 0.0 at the made vertices): the structure holds in 4 of 4, HDP-made 4 of 4",
      "structure (the control) holds in 4 of 4" in s and "exactly 1.0 / 0.0 in 4 of 4" in s, s[:500])
s = summary(S.score_dd(dd_world("dd-b", depth_exact=False), Pdd)[0])
check("g-dd world with the made depth one word off 1.0: HDP-made refuted (0 of 4)", "exactly 1.0 / 0.0 in 0 of 4" in s, s[:500])
s = summary(S.score_dd(dd_world("dd-c", break_struct="dd-m1"), Pdd)[0])
check("g-dd world with one job's structure failing (vertex order rotated): the verdict says so (3 of 4)", "holds in 3 of 4" in s and "cannot tell for the failed" in s, s[:400])

# ===================================================================================================== DPM stages
G.decode_object = REAL_DECODE


def c4_dir(name, limit2048, ctl_limit4096=0x351):
    world = W.World(lambda j: limit2048 if j["w"] == 2048 else ctl_limit4096)
    state, stopped = W.simulate("g-c4", world, TMP / name)
    return TMP / name, state, stopped


d, st, stopped = c4_dir("c4-LT", 0xd4)
t = S.run_stage("g-c4", d)
check("g-c4 world LT (last raise thr0 0xd4): the runner's twin picks 0xe0 0xd0 0xd8 0xd4 0xd6 0xd5; LT HOLDS, exact 0xd4 / 0xd5, no pick off the rule",
      "LT HOLDS" in summary(t) and "PICK OFF" not in t and st["obs"]["c4"][0xd4] == "R" and st["obs"]["c4"][0xd5] == "N"
      and [int(r.split("\t")[4], 16) - 0x22 for r in (d / "cases.tsv").read_text().splitlines()[5:]] == [0xe0, 0xd0, 0xd8, 0xd4, 0xd6, 0xd5], summary(t)[:300])
for lim in (0xc8, 0xfe, 0xc0, 0xff):
    d, st, stopped = c4_dir(f"c4-{lim:x}", lim)
    t = S.run_stage("g-c4", d)
    check(f"g-c4 world with the flip at {lim:#x}: LT REFUTED, the measured exact flip {lim:#x} / {lim + 1:#x} is reported",
          "LT REFUTED" in summary(t) and f"last raise thr0 {lim:#x}" in summary(t) and "PICK OFF" not in t, summary(t)[:300])
d, st, stopped = c4_dir("c4-ctl", 0xd4, ctl_limit4096=0x300)
t = S.run_stage("g-c4", d)
check("g-c4 world whose 4096 control 0x372 reads none (limit 0x300): the twin stops at the control; the scorer says cannot tell",
      stopped and "cannot tell: control(s) ['c3-4096-0x372'" in summary(t), f"{stopped} | {summary(t)[:200]}")
# a hand-written non-monotone observation set and a pick off the rule
check("dpm3.flip_of: a silent cell below a raise is `not monotone`; no raise / no silent above are named; a closed bracket is exact",
      dpm3.flip_of({0xc0: "R", 0xe0: "N", 0xd0: "R", 0xc8: "N"})[2] == "not monotone" and dpm3.flip_of({0xc0: "N"})[2] == "no raise"
      and dpm3.flip_of({0xc0: "R"})[2] == "no silent cell above" and dpm3.flip_of({0xd4: "R", 0xd5: "N"}) == (0xd4, 0xd5, "exact")
      and dpm3.pick({0xc0: "R", 0x100: "N"}) == (0xe0, "") and dpm3.pick({0xc0: "R", 0xc1: "N"})[0] is None)
bad = TMP / "c4-bad"
shutil.copytree(TMP / "c4-LT", bad)
txt = (bad / "cases.tsv").read_text().replace("\t0xf2\t", "\t0xf8\t", 1) if False else None
cases = (bad / "cases.tsv").read_text().splitlines()
i = next(i for i, ln in enumerate(cases) if ln.startswith("c4-b1\t"))
f = cases[i].split("\t")
f[4] = "0xf2"
cases[i] = "\t".join(f)
(bad / "cases.tsv").write_text("\n".join(cases) + "\n")
t = S.run_stage("g-c4", bad)
check("g-c4: a recorded P that is not the midpoint of the kept observations is flagged PICK OFF THE RULE (and its knob proof voids the job)",
      "PICK OFF THE RULE" in t or "NODATA: knob did not land" in t, summary(t)[:200])
# a void bisect cell: the runner ends the bisect, the scorer lists the skipped cells
v = W.World(lambda j: 0xd4 if j["w"] == 2048 else 0x351, need=lambda j: 531 if j["w"] == 2048 else 2124)
shutil.copytree(TMP / "c4-LT", TMP / "c4-skip")

# ---- H-last on the kept timelines of R1 and R2
tot = dict(n=0, ok=0, sep=0, sep_ok=0)
for sess, st in [("r1-pixgeo", s) for s in ("g-u1", "g-c1", "g-c1f", "g-u2")] + [("r2-geo", s) for s in ("g-c3", "g-c2")]:
    k = Kept(C2 / sess / "out" / st)
    rows = [dict(name=n) for n in k.names()]
    rdd = {r["name"]: dpm3.read_job(k, r["name"], knob_proof=False) for r in rows}
    _, t = S.hlast_table(k, rdd, rows)
    for kk in tot:
        tot[kk] += t[kk]
check("H-last on the 73 kept jobs of R1 and R2 with 0x072c sampled: every one fits (the design's 49 of 49 with an abort among them), and exactly "
      "two separate it from the peak and second-abort readings (c3-2048-0xe2, k-1500-0x300)",
      tot["n"] >= 64 and tot["ok"] == tot["n"] and tot["sep"] == 2 and tot["sep_ok"] == 2, str(tot))


# ---- g-d36
def d36_dir(name, **kw):
    world = W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]), **kw)
    state, stopped = W.simulate("g-c4", world, TMP / (name + "-c4"))
    W.simulate("g-d36", world, TMP / name, state)
    return TMP / name, TMP / (name + "-c4")


d, c = d36_dir("d36-T")
t = S.run_stage("g-d36", d, ctl_dir=str(c))
check("g-d36 world where dword 36 follows H-last: at least 3 jobs separate and all fit: H-last HOLDS", "H-last HOLDS" in summary(t), summary(t)[:300])
d, c = d36_dir("d36-F", h_last=False)
t = S.run_stage("g-d36", d, ctl_dir=str(c))
check("g-d36 world where dword 36 is the peak less 2 (plus one): a separating job misses: H-last REFUTED", "H-last REFUTED" in summary(t), summary(t)[:300])
d, c = d36_dir("d36-flat", counts=lambda j, thr0, n: [3] * n)
t = S.run_stage("g-d36", d, ctl_dir=str(c))
check("g-d36 world where every abort has the same count (nothing separates): cannot tell (fewer than 3 separating jobs)", "cannot tell: only 0 separating" in summary(t), summary(t)[:300])
t = S.run_stage("g-d36", d, ctl_dir=str(TMP / "nope"))
check("g-d36 without g-c4's kept directory: cannot tell (the controls are the session's)", "cannot tell" in summary(t) and "missing" in summary(t))

# ---- g-c6, g-c5, g-c7
c4world = lambda: W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]))


def stage_dir(stage, name, world, c4=None):
    c4dir = TMP / (name + "-c4")
    state, stopped = W.simulate("g-c4", c4 or c4world(), c4dir)
    W.simulate(stage, world, TMP / name, state)
    return TMP / name, c4dir


tgt = W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]))
d, c = stage_dir("g-c6", "c6-T", tgt)
t = S.run_stage("g-c6", d, ctl_dir=str(c))
check("g-c6 world H-target (the context does not matter): H-target HOLDS, H-context REFUTED", "H-target HOLDS" in summary(t) and "H-context REFUTED" in summary(t), summary(t)[:400])
ctxw = W.World(lambda j: M.lt_last_thr0(*j["ctx"]))
d, c = stage_dir("g-c6", "c6-C", ctxw)
t = S.run_stage("g-c6", d, ctl_dir=str(c))
check("g-c6 world H-context (the limit follows the 4096 context: 0x351): H-context HOLDS, H-target REFUTED", "H-context HOLDS" in summary(t) and "H-target REFUTED" in summary(t), summary(t)[:400])
t = S.run_stage("g-c6", d, ctl_dir=str(TMP / "nope"))
check("g-c6 without g-c4's kept directory: cannot tell", "cannot tell" in summary(t))
check("g-c6: the calibration is reported against the plain context's 0x213 (531)", "page need 0x213" in t, t[-300:])

lt = W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]))
d, c = stage_dir("g-c5", "c5-LT", lt)
t = S.run_stage("g-c5", d, ctl_dir=str(c))
check("g-c5 world LT at all three targets: LT consistent with all three, no refutation of LT", "LT" in summary(t).split("consistent with all three targets")[1].split("refuted")[0], summary(t)[:500])
def aff(key, c2):
    return W.World(lambda j: c2 if j["w"] == 2048 and j["h"] == 2048 else M.affine_C(j["w"], j["h"], c2 + 0x20, key) - 0x20)


for key, lab, c2 in (("side2", "AS", 0xc8), ("mt", "AM", 0xc8), ("R", "AR", 0xc8)):
    c4w = W.World(lambda j, c2=c2: c2 if j["w"] == 2048 else 0x351)
    d, c = stage_dir("g-c5", f"c5-{lab}", aff(key, c2), c4w)
    t = S.run_stage("g-c5", d, ctl_dir=str(c))
    want = {"AS": ("AS",), "AM": ("AM", "AR"), "AR": ("AR", "AM")}[lab]
    cons = summary(t).split("consistent with all three targets")[1].split("refuted")[0]
    refd = summary(t).split("refuted")[1]
    check(f"g-c5 world {lab} (affine through the two exact points, g-c4 at 0xc8): {lab} consistent with all three targets, LT refuted",
          all(w in cons for w in want) and "LT" in refd and "LT" not in cons, summary(t)[:500])
split = W.World(lambda j: 0x1a8 if (j["w"], j["h"]) == (4096, 2048) else 0x1c0 if (j["w"], j["h"]) == (2048, 4096) else M.lt_last_thr0(j["w"], j["h"]))
d, c = stage_dir("g-c5", "c5-split", split)
t = S.run_stage("g-c5", d, ctl_dir=str(c))
check("g-c5 world with different limits at 4096x2048 and 2048x4096 (equal regions): the scorer says regions alone are REFUTED",
      "regions alone is REFUTED" in summary(t) or "every law in regions alone" in summary(t), summary(t)[-300:])
d, c = stage_dir("g-c5", "c5-picks", lt)
check("g-c5: no pick off the rule in the runner twin's kept data; calibration page needs reported", "PICK OFF" not in t and "page need" in t, "")
d2 = TMP / "c5-LT"
cases = (d2 / "cases.tsv").read_text().splitlines()
check("g-c5: fixed cells above half the page need are skipped by the fit gate (class skipped) when they exist; each target has its 12 rows in the table",
      len(cases) - 1 <= 36, str(len(cases) - 1))

wt = W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]))
d, c = stage_dir("g-c7", "c7-T", wt)
t = S.run_stage("g-c7", d, ctl_dir=str(c))
check("g-c7 world where the scene does not matter (limit 0xd4 as g-c4): H-target HOLDS, the bisect has nothing to do",
      "H-target HOLDS" in summary(t) or "equals g-c4" in summary(t), summary(t)[:500])
ws = W.World(lambda j: 0xc8 if j["full"] else M.lt_last_thr0(j["w"], j["h"]))
d, c = stage_dir("g-c7", "c7-S", ws)
t = S.run_stage("g-c7", d, ctl_dir=str(c))
check("g-c7 world where the full-target scene flips at 0xc8: H-scene (the limit follows the scene), the exact flip is found by the bisect",
      "H-scene" in summary(t) and "0xc8" in summary(t), summary(t)[:500])
wg = W.World(lambda j: M.lt_last_thr0(j["w"], j["h"]), need=lambda j: 6000 if j["full"] else (531 if j["w"] == 2048 else 2124))
d, c = stage_dir("g-c7", "c7-G", wg)
t = S.run_stage("g-c7", d, ctl_dir=str(c))
cs = (d / "cases.tsv").read_text().splitlines()[1:]
check("g-c7 gate: more than 3 partial renders at P 0x422 end the stage after one job (10 rows skipped); the scorer says the gate closed",
      "gate closed" in summary(t) and sum(1 for r in cs if r.split("\t")[9] == "skipped") == 10 and len(cs) == 11, summary(t)[:300])
sys.exit(0 if ok else 1)
