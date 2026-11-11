#!/usr/bin/env python3
"""The R3-pixel scorers of Q082 (q-f0, q-f1a / q-f1b, q-t, q-v) on landed data (E431's timelines, E784's kept vertex runs) and on
synthetic worlds where each hypothesis wins and loses: a control failing, void data (loop proof, pre-read, missing dumps), the two
orders disagreeing (edge), a contradiction in one order only (unreplicated), the loop gate and its three exits.  Prints ok / FAIL
lines; exit 1 on any FAIL.   PY tests/test_scorers_r3.py   (the pixel-faults venv)"""
import io
import os
import pathlib
import re
import shutil
import struct
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "score"), str(R3 / "gen"), str(R3 / "tests")]
import r3const as C  # noqa: E402
import r3lib as L  # noqa: E402
import score_f as F  # noqa: E402
import score_r3 as S  # noqa: E402
import score_t as T  # noqa: E402
import score_v as V  # noqa: E402
import worlds as W  # noqa: E402

FX = R3 / "tests/fixtures"
failed, nok = [], 0


def check(cond, what):
    global nok
    if cond:
        nok += 1
        print("ok   " + what)
    else:
        failed.append(what)
        print("FAIL " + what)


def mark(n):
    return 0xC0DE0000 | n


# ---------------------------------------------------------------------------------------------------- E431's timelines
exp = {"52": (520.2, None), "53": (538.1, None), "54": (537.4, 273.3), "55": (555.7, 277.7), "56": (549.7, 287.7)}
bad = []
for n, (B, t6) in exp.items():
    b = L.burst((FX / f"e431/case{n}-order1.txt").read_text())
    if b is None or abs(b["B"] - B) > 0.2 or (b["t6"] is None) != (t6 is None) or (t6 and abs(b["t6"] - t6) > 0.2) or b["stale"]:
        bad.append((n, b))
check(not bad, "burst(): E431's kept timelines (event-fine 52..56, order 1) give B and the time of bit 6 of closing3/pixel/q082_timelines.out "
      "(53 clear, 54 at 273 us, 55 at 278, 56 at 288)")
b = L.burst(W.timeline(600.0, t6=200.0))
check(b and abs(b["B"] - 600) < 0.01 and abs(b["t6"] - 200) < 0.01 and b["t7"] is None, "burst(): a synthetic timeline round-trips B and t6")
b = L.burst(W.timeline(600.0, t6=100.0, t7=450.0))
check(b and abs(b["t7"] - 450) < 0.01, "burst(): t7 (bit 7) is read from the same register")
check(L.burst("probe x: o0 0x1 (2 of 2)\n") is None, "burst(): no timeline is None")
two = W.timeline(800.0, t6=300.0).splitlines()
two.insert(4, "tl 120000 000a0000 00000400 20000000")                       # a short setup run before the job's burst
two.insert(5, "tl 125000 00000020 00000400 20000000")
b = L.burst("\n".join(two) + "\n")
check(b and abs(b["B"] - 800) < 0.01 and abs(b["t6"] - 300) < 0.01, "burst(): with a short setup run before the job's burst the LONGEST run is the job's: " + str(b))
check(L.parse_o0("a\nprobe x: o0 0xc0de0035 (2048 of 2048)\nb")[:3] == ("same", 0xC0DE0035, 2048), "parse_o0 finds the line in the whole output")
check(L.parse_o0("probe x: o0 mixed 0xff203040 x12028 0x00000035 x4356\n")[0] == "mixed", "parse_o0 reads the mixed line")


# ---------------------------------------------------------------------------------------------------- q-f0
def f0_job(name, form, N, bit, proof=True, B=None, t6=None, pre=0x400, cls="ok"):
    m = 0 if form == "abs" else mark(N)
    B = B if B is not None else C.B0 + C.B1 * N
    out = W.o0_line("loop", m if proof else 0xdeadbeef, 2048) + W.timeline(B, t6 if bit else None)
    return dict(name=name, out=out, pre=pre, post=0x400 | (0x40 if bit else 0), cls=cls)


def f0_world(rel_proof=True, abs_flip=False, rel16=(False, 205), rel136=(True, 1290)):
    jobs = []
    spec = [("rel", 53, False), ("rel", 56, True), ("rel", 53, False), ("rel", 56, True), ("abs", 53, False), ("abs", 56, True),
            ("abs", 53, False), ("abs", 56, True), ("rel", 16, False), ("rel", 136, True)]
    seen = {}
    for form, N, bit in spec:
        seen[(form, N)] = seen.get((form, N), 0) + 1
        nm = f"f0-{form}-b8-{N}" + ("b" if seen[(form, N)] == 2 else "")
        if abs_flip and form == "abs":
            bit = not bit
        B = rel16[1] if N == 16 else rel136[1] if N == 136 else None
        jobs.append(f0_job(nm, form, N, bit, proof=rel_proof or form == "abs", B=B, t6=200))
    return jobs


def run(stage, d):
    return S.run_stage(stage, d)[0]


def summ(text):
    return next(x for x in text.splitlines() if x.startswith("SUMMARY:"))


d = W.stage("q-f0", f0_world())
t = run("q-f0", d)
check("OPEN" in summ(t) and "0 misses" in summ(t), "q-f0: a world where the relative loop proves itself and E431's bits hold: gate OPEN, 0 misses; " + summ(t)[:140])
check(F.f0_state(S.L.Kept(d))[0] == "open", "q-f0 state: open")
d = W.stage("q-f0", f0_world(rel_proof=False))
check(F.f0_state(S.L.Kept(d))[0] == "closed" and "CLOSED" in summ(run("q-f0", d)), "q-f0: the relative loop's proof FAILS (o0 not MARK): the gate is CLOSED (a backward br did not loop in a pixel task)")
d = W.stage("q-f0", f0_world(abs_flip=True))
check(F.f0_state(S.L.Kept(d))[0] == "disagree", "q-f0: abs and rel loops disagree on the bit at 53 and 56: state DISAGREE (the session stops)")
jobs = f0_world()
jobs[1]["post"] = 0x400                                    # the rel 56 row did not set: a repeatability problem, not a proof failure
d = W.stage("q-f0", jobs)
check(F.f0_state(S.L.Kept(d))[0] == "edge", "q-f0: rel 56 clear in one of two runs: the bit is not repeatable there (state edge, gate open)")
jobs = f0_world()
jobs[0]["pre"] = 0x440
d = W.stage("q-f0", jobs)
j = F.f0_jobs(S.L.Kept(d))[0]
check(j["void"] and "not 0x400" in j["void"], "q-f0: STATUS2 not 0x400 before the job voids the row: " + str(j["void"]))
check(F.f0_state(S.L.Kept(d))[0] == "closed", "q-f0: a void relative row closes the gate (it did not prove itself)")
jobs = f0_world()
jobs[0]["cls"] = "proof"
d = W.stage("q-f0", jobs)
check(F.f0_state(S.L.Kept(d))[0] == "closed", "q-f0: the runner's class `proof` (rc 17) closes the gate")
d = W.stage("q-f0", [])
check(F.f0_state(S.L.Kept(d))[0] == "closed", "q-f0: nothing ran: closed")
jobs = f0_world(rel16=(False, 900))
d = W.stage("q-f0", jobs)
check("MISS" in run("q-f0", d), "q-f0: a burst of 900 us at N = 16 misses the frozen 204 +- 125")


# ---------------------------------------------------------------------------------------------------- q-f1 worlds
def f1_model(hyp, kind, N, order):
    instr, imae = C.INSTR_PER_ITER[kind], C.IMAE_PER_ITER[kind]
    busy = kind == "ld8" and hyp == "WDbusy"
    wait = 6.0 * N if busy else 0.0                                  # the load wait is 6 us an iteration, the busy part 4.5 us
    B = C.B0 + (4.5 if busy else 1.128 * instr) * N + wait + W.noise((kind, N, order), 15)
    if hyp == "MA":
        bit = imae * N >= 330
    elif hyp == "WD":
        bit = (B - C.B0) / 4 >= C.T_STAR
    elif hyp == "WDbusy":
        bit = (B - C.B0 - wait) / 4 >= C.T_STAR
    else:
        bit = False
    return bit, B


def f1_world(hyp, order, flip=None, voidproof=None, noimae=False):
    jobs = []
    seq = [(k_, n) for k_, ns in C.F_LADDERS.items() for n in ns]
    seq = seq if order == "a" else list(reversed(seq))
    for kind, N in seq:
        bit, B = f1_model(hyp, kind, N, order)
        if flip == (kind, N, order):
            bit = not bit
        name = f"f{order}-{kind}-n{N}"
        ok = voidproof != (kind, N, order)
        out = W.o0_line(name, mark(N) if ok else 0, 2048) + W.timeline(B, 200.0 if bit else None)
        jobs.append(dict(name=name, out=out, pre=0x400, post=0x400 | (0x40 if bit else 0)))
    return jobs


def f1_verdict(hyp, **kw):
    da = W.stage("q-f1a", f1_world(hyp, "a", **kw))
    db = W.stage("q-f1b", f1_world(hyp, "b", **kw))
    a, b = F.f1_collect(S.L.Kept(da)), F.f1_collect(S.L.Kept(db))
    lines, v, unexpl, infos = F.f1_verdict(a, b)
    return lines, v, unexpl, infos, (da, db)


lines, v, unexpl, infos, _ = f1_verdict("MA")
check(v["H-MA"].startswith("HOLDS") and v["H-WD"].startswith("REFUTED") and v["H-BURST"].startswith("REFUTED") and not unexpl,
      "q-f1 world H-MA (bit from multiply-adds >= 330): H-MA HOLDS on every ladder, H-WD and H-BURST REFUTED (b2 / b8n never set); " + str({h: x[:30] for h, x in v.items()}))
lines, v, unexpl, infos, _ = f1_verdict("WD")
check(v["H-WD"].startswith("HOLDS") and v["H-BURST"].startswith("HOLDS") and v["H-MA"].startswith("REFUTED") and not unexpl,
      "q-f1 world H-WD (a tile's time >= 121.8 us): H-WD and H-BURST HOLD (a fill cannot tell them apart), H-MA REFUTED (b2 sets); " + str({h: x[:30] for h, x in v.items()}))
lines, v, unexpl, infos, _ = f1_verdict("WDbusy")
check(v["H-WD"].startswith("REFUTED") and "ld8" in v["H-WD"] and not v["H-WD-busy"].startswith("REFUTED"),
      "q-f1 world H-WD-busy (load wait not counted): H-WD REFUTED on ld8 only, H-WD-busy stands; " + v["H-WD"] + " | " + v["H-WD-busy"][:50])
lines, v, unexpl, infos, _ = f1_verdict("NEVER")
check(unexpl and v["H-MA"].startswith("REFUTED") and v["H-WD"].startswith("REFUTED"),
      "q-f1 world with no ladder ever setting: H-MA and H-WD both REFUTED and the verdict says E769's fit stays unexplained")
# the E769 loop proof failing at one job voids it: no refutation from it
lines, v, unexpl, infos, _ = f1_verdict("MA", voidproof=("b4", 168, "a"))
rows, _ = F.ladder_eval("b4", F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "a", voidproof=("b4", 168, "a"))))), F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "b")))))[0:2]
st168 = next(r for r in rows if r[0] == 168)
check(st168[4] == "one order" and v["H-MA"].startswith("HOLDS"), "q-f1: a failed loop proof voids that job (one order left, flagged); H-MA still HOLDS")
# the two orders disagree at the threshold N: an `edge`, never a refutation
lines, v, unexpl, infos, _ = f1_verdict("MA", flip=("b16", 24, "b"))
rows = F.ladder_eval("b16", F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "a", flip=("b16", 24, "b"))))),
                     F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "b", flip=("b16", 24, "b")))))) [0]
r24 = next(r for r in rows if r[0] == 24)
check(r24[4] == "edge" and v["H-MA"].startswith("HOLDS"), "q-f1: the orders disagree at b16 N = 24: marked edge, H-MA still HOLDS (E431's 54 was 2 of 3)")
# a contradiction in ONE order only is unreplicated, not a refutation
lines, v, unexpl, infos, _ = f1_verdict("MA", flip=("b4", 200, "a"))
rows = F.ladder_eval("b4", F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "a", flip=("b4", 200, "a"))))),
                     F.f1_collect(S.L.Kept(W.stage("x", f1_world("MA", "b", flip=("b4", 200, "a")))))) [0]
r200 = next(r for r in rows if r[0] == 200)
check(r200[4] == "edge", "q-f1: a single flipped order at an N both orders read is an edge (the orders differ)")
da = W.stage("q-f1a", f1_world("MA", "a", flip=("b4", 200, "a")))
lines2, v2, _, _ = F.f1_verdict(F.f1_collect(S.L.Kept(da)), {})
check(v2["H-MA"].startswith("open") or v2["H-MA"].startswith("REFUTED") is False, "q-f1: with one order only no hypothesis is REFUTED by the single-order contradictions (unreplicated: " + v2["H-MA"][:60] + ")")
# time of the latch: the early world's t6 is 200 us: H-EARLY counts every long job, H-END none
ls = "\n".join(lines)
m = re.search(r"(\d+) jobs; t6 in \[120, 340\] us \(H-EARLY\): (\d+); within 15% of B \(H-END\): (\d+)", ls)
check(m and int(m[1]) > 0 and m[1] == m[2] and m[3] == "0", "q-f1: the time of the latch: every long set job has t6 = 200 us (H-EARLY), none at the end (H-END): " + (m[0] if m else ls[-200:]))
# H-WD's N* from the two short points
pts = [(6, C.B0 + 1.128 * 16 * 6), (12, C.B0 + 1.128 * 16 * 12)]
n, band = C.wd_nstar(pts)
check(abs(n - 4 * 121.8 / (1.128 * 16)) < 1.0 and 0.2 < band < 0.4, f"H-WD: N* for b16 from its two short points = {n:.1f} (4 T* / s_body = 27.0), band {band:.2f} (2 sigma of the slope dominates 8%)")
check([C.pred_ma("b16", n_) for n_ in (21, 22, 23, 24, 25)] == ["clear", "clear", "either", "set", "set"]
      and [C.pred_ma("b12", n_) for n_ in (31, 32, 33, 34)] == ["clear", "either", "either", "set"]
      and [C.pred_ma("b4", n_) for n_ in (156, 160, 164, 168)] == ["clear", "either", "either", "set"]
      and [C.pred_ma("ld8", n_) for n_ in (79, 84)] == ["clear", "set"] and C.pred_ma("b2", 16000) == "clear" == C.pred_ma("b8n", 3840),
      "H-MA's frozen cells are the design's table (b16 21,22 clear 23 either 24,25 set; b12; b4; ld8; b2 and b8n never)")
check(C.pred_burst(500) == "clear" and C.pred_burst(536) == C.EITHER and C.pred_burst(600) == "set", "H-BURST: 536 +- 20 us")
# a single order through the stage scorer
text = run("q-f1a", W.stage("q-f1a", f1_world("MA", "a")))
check(summ(text).startswith("SUMMARY: q-f1a: 54 jobs read, 0 void"), "score q-f1a: " + summ(text)[:110])
# a pre-read that is not 0x400 voids the job
jw = f1_world("MA", "a")
jw[3]["pre"] = 0x480
text = run("q-f1a", W.stage("q-f1a", jw))
check("1 void" in summ(text), "score q-f1a: STATUS2 0x480 before a job voids it: " + summ(text)[:90])


# ---------------------------------------------------------------------------------------------------- q-t
def t_rows():
    rows = []
    for ln in (R3 / "tables/q-t.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(ln.split("|", 5))
    return rows


def t_world(hyp, ref=56, void_n1=None, bridge_bad=False, pre_bad=None):
    jobs = []
    for name, st, risk, knobs, rt, args in t_rows():
        m = re.search(r"--width (\d+) --height (\d+)", args)
        w, h = int(m[1]), int(m[2])
        bit, N, pr, mk = False, None, w * h, None
        mm = re.search(r"loop-rel-b8-i(\d+)", args)
        if mm:
            N = int(mm[1])
            mk = mark(N)
        if name.startswith("t-ctl-green"):
            out = "probe x: o0 0xff00ff00 (%d of %d)\n" % (w * h, w * h) + W.timeline(300.0)
            jobs.append(dict(name=name, out=out, pre=0x400, post=0x400))
            continue
        if name.startswith("t-par"):
            out = "probe x: o0 mixed 0xff203040 x3000 0x%08x x1096\n" % mk + W.timeline(300.0)
            jobs.append(dict(name=name, out=out, pre=0x400, post=0x400))
            continue
        size = (w, h)
        if name.startswith("t-ctl-n1") or name.startswith("t-bridge"):
            bit = (N >= ref) if name.startswith("t-bridge") else False
            if bridge_bad and name.startswith("t-bridge"):
                bit = False
        elif name.startswith("t-4x4"):
            bit = hyp == "H-INST" and N >= 56
        else:
            allowed = sorted(C.t_allowed(hyp, size, ref, ladder=C.t_ladder(w, h)), key=lambda x: (x is None, x))
            fs = allowed[0]
            bit = fs is not None and N >= fs
        proof_ok = not (void_n1 == size and name.startswith("t-ctl-n1"))
        out = W.o0_line(name, mk if proof_ok else 0, w * h) + W.timeline(400.0, 200.0 if bit else None)
        jobs.append(dict(name=name, out=out, pre=0x480 if pre_bad == name else 0x400, post=0x400 | (0x40 if bit else 0)))
    return jobs


tt = {}
for hyp in ("H-INST", "H-TILE", "H-JOB"):
    d = W.stage("q-t", t_world(hyp))
    tt[hyp] = run("q-t", d)
    s = summ(tt[hyp])
    mine = f"{hyp} holds at"
    others = [h for h in ("H-INST", "H-TILE", "H-JOB") if h != hyp]
    check(mine in s and all(f"{o} REFUTED" in s for o in others),
          f"q-t world {hyp}: only {hyp} holds (the other two are REFUTED at sizes where they differ); " + s[len('SUMMARY: q-t: '):][:150])
check("bridge ok" in summ(tt["H-INST"]), "q-t: the bridge (64x32 at 53 clear, 56 set) is ok in a world with the fill's threshold")
check("bridge FAILED" in summ(run("q-t", W.stage("q-t", t_world("H-INST", bridge_bad=True)))), "q-t: a bridge that does not set at 56 is reported FAILED")
s = summ(run("q-t", W.stage("q-t", t_world("H-JOB", ref=110))))
check("reference N 110" in s and "H-JOB holds" in s, "q-t: a measured 64x32 first set of 110 (the bridge failed) scales every cell: H-JOB still holds; " + s[:110])
s = summ(run("q-t", W.stage("q-t", t_world("H-INST", void_n1=(256, 256)))))
check("(256, 256)" in s and "void sizes [(256, 256)]" in s, "q-t: the N = 1 loop control failing at 256x256 voids that size only: " + s[-110:])
d = W.stage("q-t", t_world("H-TILE", pre_bad="t-8x8-n53"))
text = run("q-t", d)
check("void" in text and "not 0x400" not in summ(text), "q-t: STATUS2 0x480 before a ladder job voids it (not read as a bit)")
# H-WD time of the latch
check("t6 in [120, 340] us in" in tt["H-TILE"], "q-t: the H-WD latch-time line is printed")
# the 4x4 rows
check("4x4 (16 pixels) at N = 56, 220, 880: 56 set, 220 set, 880 set" in tt["H-INST"] and "4x4 (16 pixels) at N = 56, 220, 880: 56 clear" in tt["H-JOB"],
      "q-t: the 4x4 rows are read (H-INST sets from 56, H-JOB clear)")


# ---------------------------------------------------------------------------------------------------- q-v: E784's kept controls
def e784_dir():
    d = pathlib.Path(W.ROOT) / "e784"
    d.mkdir(exist_ok=True)
    for f in (FX / "e784").iterdir():
        shutil.copy(f, d / f.name)
    rows = [W.HEAD] + [f"{n}\tq-v\tx\tsafe\tx\tx\tx\t0\tok\t-" for n in ("v-ctl0", "v-n1", "v-n3", "v-i880", "v-i1760")]
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    return d


d784 = e784_dir()
kk = S.L.Kept(d784)
col = V.collect(kk)
check(all(V.ok(j) for g in col.values() for j in g.values()), "q-v: E784's kept controls (ctl0, n1, n3, i880, i1760) decode with the loop proof 0x3f200000 + N on every vertex (real pbdump decode)")
check(col["ctl"][1760]["bit7"] is True and col["ctl"][880]["bit7"] is False and col["ctl"][3]["bit7"] is False,
      "q-v: E784's STATUS2 reads (i880 clear, i1760 set 0x480) are read through the new reader")
lines, res, info = V.evaluate(col)
check(not info["bad"], "q-v: E784's five controls pass the stage's control rule")
shutil.copy(d784 / "v-n3.v-n3__0.param.bin.gz", d784 / "x.gz")
kk2 = S.L.Kept(d784)
orig = V.L.depth_words
V.L.depth_words = lambda p, t: [C.BASE_DEPTH + 4] * 3                                 # a loop that ran 4 times, not 3: E770's failure mode
col2 = V.collect(kk2)
V.L.depth_words = orig
check(col2["ctl"][3]["proof"] is False, "q-v: a depth word 0x3f200004 where N = 3 FAILS the loop proof (the branch did not run N times)")
lines, res, info = V.evaluate(col2)
check(res is None and info["bad"], "q-v: failed controls give `cannot tell`: " + str(info["bad"])[:80])


# ---------------------------------------------------------------------------------------------------- q-v worlds (depth decode patched)
def v_rows():
    rows = []
    for ln in (R3 / "tables/q-v.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(ln.split("|", 5))
    return rows


def v_world(hyp, n8=1200, skip=True, bad_depth=None, no_ctl=None):
    """bit 7 by the hypothesis' formula of N8* (the narrowing ladder's bracket (n8 - 55, n8]); skipped rows after a set sweep row."""
    jobs, group_set = [], set()
    for name, st, risk, knobs, rt, args in v_rows():
        N = int(re.search(r"-n?i?(\d+)$", name)[1]) if name != "v-ctl0" else 0
        key = {"v-up": "up", "v-dn": "dn"}.get(name[:4], None)
        lad = re.match(r"v-(b16v|b4v|v12|v48)-n", name)
        nv = int(re.search(r"--vertices (\d+)", args)[1]) if "--vertices" in args else 3
        gm = re.search(r"(sweep|watch):(\w+):0x80", knobs)
        if gm and gm[1] == "sweep" and gm[2] in group_set and skip:
            jobs.append(dict(name=name, out="", cls="skipped", rc=0))
            continue
        if name == "v-ctl0" or name in ("v-n1", "v-n3", "v-i880"):
            bit = False
        elif name == "v-i1760":
            bit = True
        elif key:
            bit = N >= n8
        else:
            g = lad[1]
            f = {"INSTR": {"b16v": n8 / 2, "b4v": 2 * n8, "v12": n8, "v48": n8}, "MA": {"b16v": .385 * n8, "b4v": 5 * n8, "v12": n8, "v48": n8},
                 "JOB": {"b16v": n8 / 2, "b4v": 2 * n8, "v12": n8 / 4, "v48": n8 / 16}}[hyp][g]
            bit = N >= f
        if gm and bit:
            group_set.add(gm[2])
        B = 100 + 0.5 * N * (16 if "b16v" in name else 4 if "b4v" in name else 8) * (nv / 3)
        depth = C.BASE_DEPTH + N + (1 if bad_depth == name else 0)
        out = "probe x: o0 mixed 0xff203040 x2998 0xff00ff00 x1098\n" + W.timeline(B, None, 300.0 if bit else None)
        jobs.append(dict(name=name, out=out, pre=0x400, post=0x400 | (0x80 if bit else 0),
                         dumps={"param.bin": struct.pack("<II", depth, nv) + b"p", "tadata.bin": b"t"}))
    return jobs


V.L.depth_words = lambda p, t: [struct.unpack("<II", p[:8])[0]] * struct.unpack("<II", p[:8])[1]
v_res = {}
for hyp in ("INSTR", "MA", "JOB"):
    d = W.stage("q-v", v_world(hyp))
    text = run("q-v", d)
    s = summ(text)
    v_res[hyp] = s
    exp_ok = {"INSTR": {"b16v": "HV-INSTR", "b4v": "HV-INSTR", "v12": "HV-INSTR", "v48": "HV-INSTR"},
              "MA": {"b16v": "HV-MA", "b4v": "HV-MA", "v12": "HV-MA", "v48": "HV-MA"},
              "JOB": {"v12": "HV-JOB", "v48": "HV-JOB"}}[hyp]
    good = all(f"{g} {h} consistent" in s for g, h in exp_ok.items())
    wrong = {"INSTR": ["b16v HV-MA REFUTED", "b4v HV-MA REFUTED"], "MA": ["b16v HV-INSTR REFUTED", "b4v HV-INSTR REFUTED"],
             "JOB": ["v12 HV-INSTR REFUTED", "v48 HV-MA REFUTED"]}[hyp]
    check(good and all(w in s for w in wrong), f"q-v world HV-{hyp}: HV-{hyp} consistent on the ladders it predicts, the rivals REFUTED where they differ; " + s[:200])
check("orders agree" in v_res["INSTR"] and "up (1155, 1210]" in v_res["INSTR"] and "down (1155, 1210]" in v_res["INSTR"],
      "q-v: the narrowing ladder finds the bracket (1155, 1210] (N8* = 1200 on the 55-step ladder) in both orders: " + v_res["INSTR"][:130])
text = run("q-v", W.stage("q-v", v_world("INSTR")))
check("skipped (sweep)" in text, "q-v: rows after a set sweep row are `skipped` and are not read")
text = run("q-v", W.stage("q-v", v_world("INSTR", bad_depth="v-b16v-n478")))
check("loop proof FAILED" in text, "q-v: a wrong depth word voids that row (its bit is not read)")
text = run("q-v", W.stage("q-v", v_world("INSTR", bad_depth="v-n3")))
check("n3" in summ(text) and "cannot tell" in summ(text) and "first backward branch" in summ(text), "q-v: n3's failed proof: `cannot tell`, no ladder row is a reading: " + summ(text)[:100])
jw = v_world("INSTR")
for j in jw:
    if j["name"] == "v-i1760":
        j["post"] = 0x400
text = run("q-v", W.stage("q-v", jw))
check("cannot tell" in summ(text) and "i1760" in summ(text), "q-v: E784's i1760 control not reproducing (bit 7 clear): `cannot tell`")
jw = v_world("INSTR")
for j in jw:
    if j["name"] == "v-up-n990":
        j["pre"] = 0x480
text = run("q-v", W.stage("q-v", jw))
check("STATUS2 before the job was 0x480" in text, "q-v: STATUS2 not 0x400 after the reset voids the row")
V.L.depth_words = orig


# ---------------------------------------------------------------------------------------------------- the gate and the verdict
def mkroot(f0jobs):
    r = pathlib.Path(W.ROOT) / ("root%d" % len(os.listdir(W.ROOT)))
    r.mkdir()
    d = W.stage("q-f0", f0jobs)
    shutil.copytree(d, r / "q-f0")
    return str(r)


import contextlib  # noqa: E402


def gate(roots):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = S.gate("q-f1a", roots)
    return rc, buf.getvalue()


rc, txt = gate([mkroot(f0_world())])
check(rc == 0 and "OPEN" in txt, "gate q-f1a: open when q-f0's relative loop proved itself (exit 0)")
rc, txt = gate([mkroot(f0_world(rel_proof=False))])
check(rc == 1 and "CLOSED" in txt and "--only q-f0" in txt, "gate q-f1a: closed (exit 1) when the relative loop failed its proof, naming the stage to rerun")
rc, txt = gate([mkroot(f0_world(abs_flip=True))])
check(rc == 3, "gate q-f1a: abs and rel disagree: exit 3 (the driver stops for the lead)")
empty = pathlib.Path(W.ROOT) / "rootE"
empty.mkdir()
rc, txt = gate([str(empty)])
check(rc == 1 and "has not run" in txt, "gate q-f1a: closed when q-f0 has not run")
rc, txt = gate([str(empty), mkroot(f0_world())])
check(rc == 0, "gate: an earlier attempt's kept q-f0 opens it (gates come from kept output, newest first)")
check(S.main(["nonsense", "x"]) == 2, "score_r3.py: a bad stage name is a usage error")

# ---------------------------------------------------------------------------------------------------- post-run fixes (POSTRUN-FIX.md, 2026-11-11)
# C1 (the audit's qt_void.py): a void row inside (last clear, first set] must not refute an exact-point hypothesis
fs256 = [a for a in C.t_allowed("H-INST", (256, 256), 56, ladder=C.t_ladder(256, 256)) if a is not None][0]
s = summ(run("q-t", W.stage("q-t", t_world("H-INST", pre_bad=f"t-256x256-n{fs256}"))))
inst = s.split("H-INST ")[1].split(";")[0]
check("256x256" not in inst and "undecided" in inst,
      f"C1: q-t world H-INST with the 256x256 row at N = {fs256} void: H-INST is undecided there, not REFUTED; " + inst)
# C11 (q-f1): a void last point of b2 and b8n is not "not set": the unexplained case needs a usable clear last point
lastb2 = C.F_LADDERS["b2"][-1]
a_ = F.f1_collect(S.L.Kept(W.stage("q-f1a", f1_world("NEVER", "a", voidproof=("b2", lastb2, "a")))))
b_ = F.f1_collect(S.L.Kept(W.stage("q-f1b", f1_world("NEVER", "b", voidproof=("b2", lastb2, "b")))))
check(F.f1_verdict(a_, b_)[2] is False,
      "C11: q-f1 world NEVER with b2's last point void in both orders: not the unexplained case (b2's last point not read)")
check(f1_verdict("NEVER")[2] is True, "C11: ... and with it read clear the unexplained case stands")

print(f"\n{nok} ok, {len(failed)} FAIL")
sys.exit(1 if failed else 0)
