#!/usr/bin/env python3
"""The R2 scorers (score/score_r2.py) with the frozen predictions on
  - past-run data: R1's kept files (the g-t2 z-cut-p control as T3's control, the g-c1 jobs as C3/C2's 4096 controls under their
    R2 names) and S1b's e3i objects (the RZ words of the T4 controls and a held-out-looking row): a reader check, not evidence;
  - synthetic worlds with a known truth: each world must give its hypothesis consistent and the others refuted; a failing
    control must give `cannot tell`; a void, skipped, looping-wrongly or hanging job must be reported as such.
The decoded object is replaced by a JSON description in the fake dump (G.decode_object patched) for the synthetic worlds only.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R2 / "score"), str(R2 / "gen"), str(R2 / "tests")]
import r1models as M1  # noqa: E402
import r2models as M  # noqa: E402
import score_geo2 as G  # noqa: E402
import score_r2 as S  # noqa: E402
import synth  # noqa: E402
from r1lib import Kept, load_preds  # noqa: E402
from rcommon import f32  # noqa: E402

HOME = pathlib.Path.home()
R1OUT = HOME / "src/scratch/resgx545/closing2/r1-pixgeo/out"
S1B = HOME / "src/scratch/resgx545/closing/s1b-v2/out"
ok = True
(R2 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R2 / "debug/tmp")                 # scratch files stay under r2-geo
TMP = pathlib.Path(tempfile.mkdtemp())
REAL_DECODE = G.decode_object


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def summary(text):
    return next((ln for ln in text.splitlines() if ln.startswith("SUMMARY:")), "no SUMMARY")


def table(st):
    out = {}
    for ln in (R2 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            out[f[0]] = dict(set=f[1], P=f[3], knobs=f[4], args=f[6])
    return out


def fake_decode(param, tadata):
    if not param:
        return dict(state="none", words=[], o=None)
    d = json.loads(param.decode())
    if d["state"] != "present":
        return dict(state=d["state"], words=[], o=None)
    packed = [(round((y + 4096) * 256), round((x + 4096) * 256), z) for (x, y), z in zip(d["xy"], d["depth"])]
    return dict(state="present", words=[1], o={}, nvert=len(d["xy"]), rhw=list(d["rhw"]), packed=packed, prims=[tuple(p) for p in d["prims"]])


def obj_job(d, name, xy, rhw, depth, prims, state="present", regs_pre=None, regs_post=None, cls="ok", extra_dumps=None):
    j = json.dumps(dict(state=state, xy=xy, rhw=rhw, depth=depth, prims=prims)).encode()
    dumps = {f"{name}__0.param.bin": j, f"{name}__0.tadata.bin": b"t"}
    for which, v in (("pre", regs_pre), ("after", regs_post)):
        if v is not None:
            dumps[f"{which}.regs.txt"] = f"sgxfive regs 1\nreg 0x0118 0x{v:08x}\n".encode()
    d.job(name, "probe x: ok\n" * 3, 0, cls, dumps=dumps)


def preds_of(st):
    return load_preds(None, st)


# ===================================================================================================== T3
P3 = preds_of("g-t3")
t3rows = table("g-t3")
G.decode_object = fake_decode


def t3_world(name, mode, break_ctl=False, void=None):
    d = synth.Dir(TMP / name, "g-t3")
    # control: z-cut-p as the T2 model predicts it (the stored order, depth words from the prediction)
    p = M1.predict_zclip(2.0, 1.0, "x")
    xy = [list(v) for v in p["xy"]]
    if break_ctl:
        xy = xy[1:] + xy[:1]
    obj_job(d, "z-cut-p", xy, [0x3f800000] * 4, [f32(x) for x in p["depth"]], p["prims"])
    for n, A, B, C, D in (("t3-w-pos", 2, 1, .5, 1.25), ("t3-w-neg", 2, 1, -.5, 1.25), ("t3-nocut", 0, 0, .5, 1.25)):
        if void == n:
            d.job(n, "", 0, "ok")
            continue
        r = M.predict_zwclip(A, B, C, D)
        rh = {"w": r["rhw_w"], "lerp": r["rhw_lerp"], "w+1": [w + (1 if m else 0) for w, m in zip(r["rhw_w"], r["made"])]}[mode]
        dep = [m if m is not None else 0x3e000000 for m in r["depth_made"]]
        if n == "t3-nocut":
            dep = [0x3f000000] * 3
        obj_job(d, n, [list(v) for v in r["xy"]], rh, dep, r["prims"])
    return Kept(d.d)


def tally(text):
    s = summary(text)
    cons = re.search(r"held out: consistent \[(.*?)\], refuted \[(.*?)\]", s)
    return s, (cons[1] if cons else ""), (cons[2] if cons else "")


s, cons, refd = tally(S.score_t3(t3_world("t3a", "w"), P3)[0])
check("T3 world HI-w (made 1/w = RZ of the made w): controls pass; HI-w exact and within 1 ulp consistent, HI-rhw refuted (exact and 1 ulp); "
      "HSH, HZZ, HPR, HDP-made consistent", "controls pass" in s and "HI-w" in cons and "HI-rhw" not in cons and "HI-rhw" in refd
      and all(m in cons for m in ("HSH", "HZZ", "HPR", "HDP-made")), s[:600])
s, cons, refd = tally(S.score_t3(t3_world("t3b", "lerp"), P3)[0])
check("T3 world HI-rhw (made 1/w interpolated): HI-rhw consistent, HI-w refuted", "HI-rhw" in cons and "HI-w (made 1/w" not in cons and "HI-w (made 1/w" in refd, s[:500])
s, cons, refd = tally(S.score_t3(t3_world("t3c", "w+1"), P3)[0])
check("T3 world made 1/w one ulp above HI-w (S1b saw 0x3f800001 on one made vertex): HI-w exact refuted, HI-w within 1 ulp consistent",
      "within 1 ulp" in cons and "HI-w" in cons and "exact word (" in refd and "HI-w (made 1/w = RZ of 1/w_made), exact word (1 of 1)" not in cons, s[:700])
check("T3 on the world with a broken control (z-cut-p stored order rotated): cannot tell", "cannot tell: control(s) ['z-cut-p']" in summary(S.score_t3(t3_world("t3d", "w", break_ctl=True), P3)[0]))
t = S.score_t3(t3_world("t3e", "w", void="t3-w-pos"), P3)[0]
check("T3: an empty job is NODATA and listed, the verdict still reads the other rows", "NODATA" in t and "void jobs ['t3-w-pos']" in summary(t), summary(t)[-200:])
# past-run reader check: R1's measured z-cut-p (the T3 control) under the real decoder
G.decode_object = REAL_DECODE
k = Kept(R1OUT / "g-t2")
tt = S.score_t3(k, {n: q for n, q in P3.items() if n == "z-cut-p"})[0]
check("T3's control on R1's measured g-t2 z-cut-p object (real decode): holds (set, order, prims, depth words)", "controls pass" in summary(tt), summary(tt)[:300])
G.decode_object = fake_decode

# ===================================================================================================== T4
P4 = preds_of("g-t4")
t4rows = table("g-t4")


def t4_world(name, cand_of, ctl_bad=False):
    d = synth.Dir(TMP / name, "g-t4")
    for n, spec in t4rows.items():
        mm = re.search(r'__0\.bin', spec["args"])
        pr = P4[n]
        words = {m.split(" ")[0]: v for q, lst in pr.items() for v, m, s in lst if q == "depth_words"}
        if n.startswith("t4-ctl"):
            w = [v for q, lst in pr.items() for v, m, s in lst if q == "depth_words"][0].split(",")[0]
            if ctl_bad and n == "t4-ctl-z0-w3":
                w = "0x3f000001"
            rhw = M.rhw_words(3.0 if "w3" in n else 1.0)[0]
        else:
            c = cand_of(n)
            w = words[c].split(",")[0]
            W = float(re.search(r"w = ([0-9.]+)", spec.get("role", "") or "x") or [0, 1][0]) if False else None
            rhw = int([v for q, lst in pr.items() for v, m, s in lst if q == "rhw_word" and m.startswith("RZ")][0], 16)
        obj_job(d, n, [list(v) for v in G.DEFAULT_XY], [rhw] * 3, [int(w, 16)] * 3, [(16, 17, 18)])
    return Kept(d.d)


pairs = [n for n in t4rows if not n.startswith("t4-ctl")]
s, cons, refd = tally(S.score_t4(t4_world("t4a", lambda n: "D3"), P4)[0])
check("T4 world D3 (RN of Z/W): controls pass; D3 consistent in 6 of 6 and every other candidate refuted",
      "controls pass" in s and "D3 (" in cons and "D3" not in refd and all(c in refd for c in ("D1", "D5", "D6", "D7")), s[:500])
s, cons, refd = tally(S.score_t4(t4_world("t4b", lambda n: "D1" if n != pairs[-1] else "D3"), P4)[0])
check("T4 world where five pairs follow D1 and the last D3: no candidate is right in 6 of 6 (none of D1..D7 consistent, each refuted)",
      not re.search(r"\bD[1-7] \(", cons) and all(c in refd for c in ("D1", "D2", "D3", "D5", "D6", "D7")), s[:300])
tt = S.score_t4(t4_world("t4c", lambda n: "D3", ctl_bad=True), P4)[0]
check("T4 with the Z = 0, W = 3 control reading a word one ulp off: cannot tell", "cannot tell: control(s) ['t4-ctl-z0-w3']" in summary(tt), summary(tt)[:200])
# S1b's e3i objects (default triangle at w = 3, 7, 0.003): the RZ reciprocal words and default positions the T4 rows predict
G.decode_object = REAL_DECODE
ok_rhw = True
for nm, W in (("e3i-w3", 3.0), ("e3i-w7", 7.0), ("e3i-w0p003", 0.003)):
    kk = Kept(S1B / "g-e3")
    d = G.decode_object(kk.dump(nm, "param.bin"), kk.dump(nm, "tadata.bin"))
    ok_rhw &= set(d["rhw"]) == {M.rhw_words(W)[0]} and G._near(G._xy(d), G.DEFAULT_XY, 2 / 256)
check("T4's rhw_word and position predictions on S1b's measured e3i rows at w = 3, 7, 0.003 (real decode): RZ word and the default triangle", ok_rhw)
G.decode_object = fake_decode

# ===================================================================================================== T5v
P5 = preds_of("g-t5v")
t5rows = table("g-t5v")
BASE = 0x3f200000


def t5_world(name, first_set=None, bad_loop=None, n3_fallthrough=False, hang_at=None, pre_bad=None, nonmono=False, never=False):
    d = synth.Dir(TMP / name, "g-t5v")
    skipping = False
    for n in t5rows:
        N = int(re.fullmatch(r"t5v-(?:i|n)(\d+)", n)[1]) if n != "t5v-ctl0" else 0
        if skipping:
            d.job(n, "", "-", "skipped")
            continue
        if hang_at == n:
            d.job(n, "probe x: failed: job hung, context lost (Connection timed out)\n", 1, "hang")
            skipping = True
            continue
        words = [BASE + N] * 3
        if n == "t5v-n3" and n3_fallthrough:
            words = [BASE + 1] * 3
        if bad_loop == n:
            words = [BASE + N, BASE + N, BASE]
        b7 = first_set is not None and N >= first_set and n.startswith("t5v-i")
        if nonmono and n == "t5v-i110":
            b7 = False
        pre = 0x400 if pre_bad != n else 0x440
        obj_job(d, n, [list(v) for v in G.DEFAULT_XY], [0x3f800000] * 3, words, [(16, 17, 18)], regs_pre=pre, regs_post=0x480 if b7 else 0x400)
        if b7 and not nonmono:
            skipping = True
    return Kept(d.d)


s = summary(S.score_t5v(t5_world("t5a", first_set=55), P5)[0])
check("T5v world: bit 7 first set at 55, the rest skipped by the sweep: controls pass, first set 55, H-ITER / H-INSTR consistent, H-NEVER refuted",
      "first set at N = 55 (last clear 53)" in s and "H-ITER / H-INSTR (set from 55) consistent" in s and "H-NEVER REFUTED" in s
      and "skipped by the sweep stop ['t5v-i110'" in s, s[:500])
s = summary(S.score_t5v(t5_world("t5b", never=True), P5)[0])
check("T5v world: no length sets bit 7 (all 13 jobs run): H-NEVER consistent, H-ITER / H-INSTR REFUTED, bound N = 7040", "never set up to N = 7040" in s and "H-NEVER consistent" in s
      and "REFUTED" in s and "skipped by the sweep stop []" in s, s[:400])
s = summary(S.score_t5v(t5_world("t5c", first_set=220), P5)[0])
check("T5v world: first set at 220: H-ITER / H-INSTR REFUTED, H-TIME consistent", "first set at N = 220 (last clear 110)" in s and "(set from 55) REFUTED" in s and "H-TIME consistent" in s, s[:400])
s = summary(S.score_t5v(t5_world("t5d", n3_fallthrough=True), P5)[0])
check("T5v world: the branch falls through on three iterations (depth word + 1): cannot tell, HLOOP refuted on hardware, no ladder row is a reading",
      "cannot tell" in s and "t5v-n3" in s and "did not loop" in s, s[:300])
t = S.score_t5v(t5_world("t5e", bad_loop="t5v-i110"), P5)[0]
check("T5v world: one vertex did not run the loop on a ladder row (E770's mode): that row is flagged LOOP FAILED and void for the latch",
      "LOOP FAILED" in t and "did NOT run on every vertex in ['t5v-i110']" in t, summary(t)[:200])
s = summary(S.score_t5v(t5_world("t5f", hang_at="t5v-i880"), P5)[0])
check("T5v world: a hang at 880: the verdict says the stage stopped there", "stage stopped at t5v-i880 (hang)" in s, s[:300])
s = summary(S.score_t5v(t5_world("t5g", pre_bad="t5v-n1"), P5)[0])
check("T5v world: STATUS2 not 0x400 after the reset on a control: cannot tell", "cannot tell" in s and "t5v-n1" in s, s[:200])
s = summary(S.score_t5v(t5_world("t5h", first_set=55, nonmono=True), P5)[0])
check("T5v world: bit 7 set at 55 and clear again at 110: not monotone", "not monotone" in s, s[:300])

# ===================================================================================================== C3
G.decode_object = REAL_DECODE
C3P = preds_of("g-c3")
c3t = table("g-c3")


def dpm_world(stage, rows, name, truth, reach_fn=lambda w, h, P, n: True, first_fn=None, with_buf=True):
    d = synth.Dir(TMP / name, stage)
    for n, spec in rows.items():
        P = int(spec["P"], 16)
        mm = re.search(r"--width (\d+) --height (\d+)", spec["args"])
        w, h = (int(mm[1]), int(mm[2])) if mm else (4096, 4096)
        thr0 = (first_fn(n, P) if first_fn else P - 0x22)
        if n.endswith("-cal"):
            txt = synth.dpm_job_text(thr0, [0x1a0], partials=0, count=3)
            d.job(n, txt, 0, "ok", buf09=[0] * 59, args=spec["args"], P=hex(P))
            continue
        r = truth(w, h, P, n)
        reach = reach_fn(w, h, P, n)
        if not reach and "2048" in spec["args"]:
            txt = synth.dpm_job_text(thr0, [0x1a0], partials=0, count=3)          # no first abort: one render
            d.job(n, txt, 0, "ok", buf09=[0] * 59, args=spec["args"], P=hex(P))
            continue
        peaks = [thr0, thr0 + 0x20 if r else thr0, thr0]
        txt = "probe x: failed: scene overflowed\n" + synth.dpm_job_text(thr0, peaks, partials=2, count=3)
        buf = [0] * 59
        buf[36], buf[37], buf[38] = (3 if r else 1), (0x10000 | thr0 if r else 0), (0x20 if r else 0)
        d.job(n, txt, 3, "ok", buf09=buf, args=spec["args"], P=hex(P))
    return Kept(d.d)


C = 0x371
same = lambda w, h, P, n: P - 2 <= C
s = summary(S.score_c3(dpm_world("g-c3", c3t, "c3a", same, reach_fn=lambda w, h, P, n: P - 0x22 <= 0x140), C3P)[0])
check("C3 world A (same C; 2048's scene reaches only for a small threshold): controls pass, 2048x2048: the proposal's cells NODATA, the low ladder all raise: "
      "no flip, H-same consistent as a bound (C >= 0x160)", "controls pass" in s and "2048x2048: 0xa2:R 0xe2:R 0x122:R 0x162:R 0x354:void" in s and "0x354:void" in s and "no flip: all usable cells raise" in s
      and "H-same consistent on 4 of 4" in s and "a bound only" in s, s[:700])
s = summary(S.score_c3(dpm_world("g-c3", c3t, "c3b", same), C3P)[0])
check("C3 world B (same C, the scene reaches at every cell): 2048x2048 flips at 0x372 / 0x374: C in [0x370, 0x372), H-same holds",
      "flip: last raise 0x372, first silent 0x374: C in [0x370, 0x372)" in s and "H-same holds" in s, s[:700])
lower = lambda w, h, P, n: (P - 2 <= C) if w == 4096 else (P - 2 <= 0x2f0)
s = summary(S.score_c3(dpm_world("g-c3", c3t, "c3c", lower), C3P)[0])
check("C3 world C (C = 0x2f0 at 2048): the flip lies between the low ladder and 0x354: C in [0x160, 0x352), H-same REFUTED, the 4096 controls pass",
      "controls pass" in s and "H-same REFUTED" in s and "C in [0x160, 0x352)" in s, s[:600])
higher = lambda w, h, P, n: (P - 2 <= C) if w == 4096 else (P - 2 <= 0x38f)
s = summary(S.score_c3(dpm_world("g-c3", c3t, "c3d", higher), C3P)[0])
check("C3 world D (C = 0x38f at 2048): 0x372 and 0x374 both raise, 0x394 silent: C in [0x392, 0x394)... flip between 0x374 and 0x394, H-same REFUTED",
      "flip: last raise 0x374, first silent 0x394" in s and "H-same REFUTED" in s, s[:600])
s = summary(S.score_c3(dpm_world("g-c3", c3t, "c3e", lambda w, h, P, n: not (n == "c3-4096-0x372") and same(w, h, P, n)), C3P)[0])
check("C3: the 4096 control at 0x372 not raising: cannot tell", "cannot tell: control(s) ['c3-4096-0x372']" in s, s[:200])
# R1's own g-c1 jobs as the C3 controls (same condition, renamed): the real decode of the real timelines and control blocks
import_dir = TMP / "c1real"
import_dir.mkdir()
lines = (R1OUT / "g-c1/cases.tsv").read_text().splitlines()
rows = [lines[0]]
for old, new in (("f-1500-0x372", "c3-4096-0x372"), ("f-1500-0x374", "c3-4096-0x374")):
    for ln in lines[1:]:
        c = ln.split("\t")
        if c[0] == old:
            rows.append("\t".join([new] + c[1:]))
    for f in (R1OUT / "g-c1").glob(f"{old}.*"):
        shutil.copy(f, import_dir / (new + f.name[len(old):]))
(import_dir / "cases.tsv").write_text("\n".join(rows) + "\n")
tt = S.score_c3(Kept(import_dir), C3P)[0]
check("C3's two 4096 controls on R1's measured f-1500-0x372 / 0x374 jobs (real timelines, real control blocks): both usable, raise and none as frozen; "
      "no 2048 job run", "raise per job: c3-4096-0x372:R c3-4096-0x374:-" in tt and "controls pass" in summary(tt) and "no 2048 cell was run" in summary(tt), summary(tt)[:300])

# ===================================================================================================== C2
C2P = preds_of("g-c2")
c2t = table("g-c2")


def c2_truth_abs(n, V):
    return V + 0x20 <= C


def c2_world(name, raiser, landed=lambda n: True, ctl=lambda n, V: V == 0x80):
    d = synth.Dir(TMP / name, "g-c2")
    for n, spec in c2t.items():
        V = int(n.rsplit("-", 1)[1], 16)
        r = ctl(n, V) if n.startswith("k-tri") else raiser(n, V)
        thr0 = V if landed(n) else 0x400
        peaks = [thr0, thr0 + 0x20 if r else thr0, thr0]
        txt = "probe x: failed: scene overflowed\n" + synth.dpm_job_text(thr0, peaks, partials=2, count=3)
        buf = [0] * 59
        buf[36], buf[37], buf[38] = (3 if r else 1), (0x10000 | thr0 if r else 0), (0x20 if r else 0)
        d.job(n, txt, 3, "ok", buf09=buf, args=spec["args"], P="0x422")
    return Kept(d.d)


s = summary(S.score_c2(c2_world("c2a", c2_truth_abs), C2P)[0])
check("C2 world H-abs (raise iff V + 0x20 <= 0x371): controls pass; H-abs consistent in 7 of 7, H-P and H-rel refuted; the flip is 0x351 / 0x352",
      "controls pass" in s and "H-abs (7)" in s.split("consistent")[1].split("refuted")[0] and "H-P" in s.split("refuted")[1] and "H-rel" in s.split("refuted")[1]
      and "raise at 0x351, none at 0x352" in s, s[:600])
s = summary(S.score_c2(c2_world("c2b", lambda n, V: False), C2P)[0])
check("C2 world H-P (no poke raises at P = 0x422): H-P consistent, H-abs and H-rel refuted", "H-P (7)" in s.split("consistent")[1].split("refuted")[0]
      and "H-abs" in s.split("refuted")[1], s[:500])
s = summary(S.score_c2(c2_world("c2c", lambda n, V: True), C2P)[0])
check("C2 world H-rel (every poke raises): H-rel consistent, H-abs and H-P refuted", "H-rel (7)" in s.split("consistent")[1].split("refuted")[0]
      and "H-abs" in s.split("refuted")[1] and "H-P" in s.split("refuted")[1], s[:500])
t = S.score_c2(c2_world("c2d", c2_truth_abs, landed=lambda n: n != "k-1500-0x33e"), C2P)[0]
check("C2: a poke that did not land (first abort at 0x400, not V) is NODATA for that row, not a hit or a miss",
      "the poke did not land: first abort status 0x400" in t and "void runs for ['H-abs']" in summary(t), summary(t)[:300])
s = summary(S.score_c2(c2_world("c2e", c2_truth_abs, ctl=lambda n, V: False), C2P)[0])
check("C2: the E625 control k-tri-0x80 not raising: cannot tell", "cannot tell: control(s) ['k-tri-0x80']" in s, s[:200])
# R1's measured g-c1 jobs read as C2-shaped rows: not applicable (no poke), so the reader check is the first-status knob proof
t = S.score_c2(Kept(import_dir), C2P)[0]
check("C2 on R1's jobs (no poke, other names): nothing scored, no crash", "SUMMARY" in t)
G.decode_object = REAL_DECODE
# ===================================================================================================== void rules and the CLI
kv = synth.Dir(TMP / "void", "g-t5v").job("t5v-ctl0", "", 0, "ok").job("t5v-n1", "x" * 30, 124, "ok")
tv = S.score_t5v(Kept(kv.d), P5)[0]
check("an empty output and an rc 124 are NODATA (never read), and the verdict is cannot tell", tv.count("NODATA") >= 2 and "cannot tell" in summary(tv), summary(tv)[:160])
import subprocess  # noqa: E402
r = subprocess.run([sys.executable, str(R2 / "score/score_r2.py")], capture_output=True, text=True)
check("score_r2.py without arguments prints its usage and exits 2", r.returncode == 2 and "STAGE" in r.stdout)
sys.exit(0 if ok else 1)
