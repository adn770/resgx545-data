#!/usr/bin/env python3
"""The scorers of the Q082 stages q4-v, q4-f and q4-t (score/score_v.py, score_f.py, score_t.py and score_r4.py's gate) on synthetic kept
directories built from the stages' own tables (tests/worlds.py): a world where each hypothesis is true (it is consistent, the rivals are
REFUTED where they differ), a world where a bridge control fails (every held-out row cannot tell, gate exit 1), a missing control (gate
exit 2), a void job (a failed loop proof, a missing dump, STATUS2 not 0x400 before), the ladder with no point on one side, the stock
rows' H-STALL / H-PHASE and their L >= 125 us condition, and the loop mark / size void rules.  The real-record readings of the timeline
rules are in tests/test_tl.py.  Prints ok / FAIL; exit 1 on any FAIL."""
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R4 / "score"), str(R4 / "tests"), str(R4 / "gen")]
import r4const as C  # noqa: E402
import r4loops as LP  # noqa: E402
import score_f as SF  # noqa: E402
import score_r4 as S  # noqa: E402
import score_t as ST  # noqa: E402
import score_v as SV  # noqa: E402
import worlds as W  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R4 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5))))
    return rows


def run(stage, d):
    return S.run_stage(stage, d)


def summ(text):
    return [x for x in text.splitlines() if x.startswith("SUMMARY:")][-1]


# ------------------------------------------------------------------------------------------------------------------ q4-v
_orig_dw = SV.L.depth_words
SV.L.depth_words = lambda p, t: [struct.unpack("<II", p[:8])[0]] * struct.unpack("<II", p[:8])[1]


def v_world(follow=True, stock="stall", i1760_bit=True, drop=None, bad_depth=None, stock_L=2000.0, ctl_bit_ctl0=False, scale=1.0, pre_bad=None, fixed_thr=1000):
    jobs = []
    for r in table("q4-v"):
        name = r["name"]
        g, N, V = SV.parse(name)
        if name == drop:
            continue
        kind = {"b12v": "b12v", "b2v": "b2v", "v24": "b8v", "ctl": "b8v", "ctl0": "b8v"}.get(g)
        if g == "stock":
            Lv = stock_L
            bit = stock == "phase"
        elif g == "ctl0":
            Lv, bit = 0.0, ctl_bit_ctl0
        else:
            nv = 24 if g == "v24" else 3
            Lv = C.v_model_L(kind, nv, N) * scale if N > 1 else 4.7
            bit = (Lv >= 129.5) if follow else (N >= fixed_thr)
            if name == "v-i1760":
                bit = i1760_bit
        depth = C.BASE_DEPTH + N + (1 if bad_depth == name else 0)
        nvx = 3
        job = dict(name=name, set=r["set"], out="probe x: o0 mixed 0xff203040 x2998 0xff00ff00 x1098\n" + W.timeline_ta(Lv, 125.0 if bit else None),
                   pre=0x480 if pre_bad == name else 0x400, post=0x400 | (0x80 if bit else 0))
        if g != "stock":
            job["dumps"] = {"param.bin": struct.pack("<II", depth, nvx) + b"p", "tadata.bin": b"t"}
        jobs.append(job)
    return W.stage("q4-v", jobs)


t, res = run("q4-v", v_world())
s = summ(t)
check("q4-v world TA-rule: every control passes, the ladder rows hold, H-STALL on the stock rows; " + s[:150],
      res["gate"].ok and "bit 7 follows the TA clock run L" in s and res["held"].failed == 0 and res["held"].held >= 10 and "H-STALL in 3 of 3" in s)
check("q4-v: the FIT points (controls of the table) are tallied apart and hold", res["fit"].failed == 0 and res["fit"].held >= 5, str(res["fit"]))
check("q4-v: the latch window (bit 7 118..138 us after the run began) holds in the set jobs", res["latch"].failed == 0 and res["latch"].held >= 5, str(res["latch"]))
t, res = run("q4-v", v_world(stock="phase"))
check("q4-v world H-PHASE: the stock rows read H-PHASE in 3 of 3", "H-PHASE in 3 of 3" in summ(t), summ(t)[-120:])
t, res = run("q4-v", v_world(stock_L=60.0))
check("q4-v: a stock row with L below 125 us is void for H-STALL / H-PHASE", "cannot tell (no stock row with L >= 125 us)" in summ(t), summ(t)[-140:])
t, res = run("q4-v", v_world(follow=False))
check("q4-v world 'bit 7 at N >= 1000 whatever L': FAILED rows, the headline is not printed as a claim; " + summ(t)[:140],
      res["held"].failed > 0 and "is not supported" in summ(t))
t, res = run("q4-v", v_world(i1760_bit=False))
check("q4-v: the i1760 bridge control not reproducing: the gate is shut, every held-out row cannot tell, controls FAILED headline",
      not res["gate"].ok and res["held"].decided == 0 and "controls FAILED" in summ(t), summ(t)[:160])
code, text = S.gate("q4-v", v_world(i1760_bit=False))
check("q4-v: the gate command exits 1 for a FAILED control", code == 1 and "v-i1760" in text, text[:150])
code, text = S.gate("q4-v", v_world(drop="v-i880"))
check("q4-v: the gate command exits 2 for a control that did not run (cannot tell)", code == 2 and "v-i880" in text, text[:150])
code, text = S.gate("q4-v", v_world())
check("q4-v: the gate command exits 0 when the four bridge controls pass", code == 0 and "PASS" in text, text[:100])
t, res = run("q4-v", v_world(bad_depth="v-b12v-n815"))
check("q4-v: a wrong depth word voids that ladder row (loop proof), the other rows stand", "loop proof failed" in t and res["held"].cannot_tell >= 1 and res["held"].held >= 8)
t, res = run("q4-v", v_world(bad_depth="v-n1"))
check("q4-v: a failed loop proof at a control (n1) is `cannot tell` for the gate", not res["gate"].ok and "v-n1" in "; ".join(res["gate"].problems))
t, res = run("q4-v", v_world(pre_bad="v-b2v-n2310"))
check("q4-v: STATUS2 not 0x400 after the reset voids the row", "STATUS2 before the job was 0x480" in t)
t, res = run("q4-v", v_world(ctl_bit_ctl0=True))
check("q4-v: ctl0 with bit 7 set fails its control", not res["gate"].ok and "v-ctl0" in "; ".join(res["gate"].failed))
t, res = run("q4-v", v_world(scale=0.5))
check("q4-v: a ladder whose points are all clear by the rule is flagged NOT INFORMATIVE (no point on one side)", "NOT INFORMATIVE" in t, "")
SV.L.depth_words = _orig_dw


# ------------------------------------------------------------------------------------------------------------------ q4-f
def f_world(hyp, drop=None, bad_proof=None, flip=None):
    jobs = []
    for r in table("q4-f"):
        name = r["name"]
        if name == drop:
            continue
        mk = SF.mark_of(name)
        m0, m1 = re.fullmatch(r"f-ld0-k(\d+)", name), re.fullmatch(r"f-ldo-k(\d+)-m(\d+)", name)
        if name in SF.CONTROLS:
            n, bit = SF.CONTROLS[name]
            B = C.b8_burst(n)
        elif m0:
            i = C.F_LD0.index(int(m0[1]))
            bit = {"S": True}.get(C.F_HYP[hyp]["ld0"][i], False)
            B = 3000.0
        else:
            i = C.F_LDO.index((int(m1[1]), int(m1[2])))
            bit = {"S": True}.get(C.F_HYP[hyp]["ldo"][i], False)
            B = 3000.0
        if name == flip:
            bit = not bit
        out = W.o0_line(name, 0xdeadbeef if bad_proof == name else mk, 2048) + W.timeline(B, 200.0 if bit else None)
        jobs.append(dict(name=name, out=out, pre=0x400, post=0x400 | (0x40 if bit else 0)))
    return W.stage("q4-f", jobs)


verd = {}
for hyp in ("H-YIELD", "H-LOADOFF", "H-SUM"):
    t, res = run("q4-f", f_world(hyp))
    verd[hyp] = res["verdicts"]
    check(f"q4-f world {hyp}: it is consistent and the two rivals are REFUTED; " + summ(t)[:110],
          res["gate"].ok and res["verdicts"][hyp] == "consistent" and all(v == "REFUTED" for h, v in res["verdicts"].items() if h != hyp), str(res["verdicts"]))
t, res = run("q4-f", f_world("H-YIELD", flip="f-rel-b8-56"))
check("q4-f: the bridge control at 56 not setting shuts the gate (every verdict cannot tell)", not res["gate"].ok and set(res["verdicts"].values()) == {"cannot tell"}, str(res["verdicts"]))
code, text = S.gate("q4-f", f_world("H-YIELD", flip="f-rel-b8-136"))
check("q4-f: gate exit 1 for a FAILED bridge control", code == 1 and "f-rel-b8-136" in text, text[:120])
code, text = S.gate("q4-f", f_world("H-YIELD", drop="f-ld8-70"))
check("q4-f: gate exit 2 for a missing bridge control (cannot tell)", code == 2, text[:120])
code, text = S.gate("q4-f", f_world("H-YIELD"))
check("q4-f: gate exit 0 when all five bridge controls pass", code == 0, text[:80])
t, res = run("q4-f", f_world("H-YIELD", bad_proof="f-ldo-k70-m1"))
check("q4-f: a failed loop proof at a held-out nested loop voids that row (no hypothesis is tested by it)", "loop proof failed" in t and res["verdicts"]["H-YIELD"] == "consistent")
t, res = run("q4-f", f_world("H-YIELD", flip="f-ld0-k53"))
check("q4-f: a row a hypothesis calls `either` (ld0 at K = 53) is not scored: flipping it leaves H-YIELD consistent",
      res["verdicts"]["H-YIELD"] == "consistent" and res["verdicts"]["H-LOADOFF"] == "REFUTED", str(res["verdicts"]))
t, res = run("q4-f", f_world("H-YIELD", flip="f-ld0-k28"))
check("q4-f: ld0 at K = 28 setting refutes H-YIELD (a wait restarts the timer: 28 iterations stay clear)", res["verdicts"]["H-YIELD"] == "REFUTED", str(res["verdicts"]))
# 53 / 56: the rule (sgx-pipe) refuses the edge, so the control is E804's bracket: a clear 136 contradicting the rule fails the control by the rule too
t, res = run("q4-f", f_world("H-YIELD", flip="f-rel-b8-16"))
check("q4-f: 16 iterations setting contradicts the rule on its tile time and fails the control", not res["gate"].ok and "f-rel-b8-16" in "; ".join(res["gate"].failed))


# ------------------------------------------------------------------------------------------------------------------ q4-t
def t_world(hyp, drop=None, size_bad=None, bad_proof=None, flip=None, t6_off=0.0, green_bit=None):
    jobs = []
    for r in table("q4-t"):
        name = r["name"]
        if name == drop:
            continue
        if (m := ST.GREENR.match(name)):
            w, h = int(m[1]), int(m[2])
            out = W.o0_line(name, 0xff00ff00, w * h)
            bit = green_bit == name
            B, t6 = 150.0, 200.0
        elif (m := ST.N1R.match(name)):
            w, h = int(m[1]), int(m[2])
            bad = size_bad == (w, h)
            out = W.o0_line(name, 0xdeadbeef if bad else LP.mark(1), w * h)
            bit, B, t6 = False, 150.0, 200.0
        elif name in ("t4-fill-n53", "t4-fill-n56"):
            n = int(name[-2:])
            out = W.o0_line(name, LP.mark(n), 2048)
            bit, B, t6 = n == 56, C.b8_burst(n), 200.0
        elif (m := ST.PAR.match(name)):
            out = "probe x: o0 mixed 0xff203040 x3000 0x00000001 x1096\n"
            bit, B, t6 = True, 3000.0, 300.0
        else:
            m = ST.SIZED.match(name)
            w, h, nn = int(m[1]), int(m[2]), int(m[3].rstrip("b"))
            out = W.o0_line(name, 0xdeadbeef if bad_proof == name else LP.mark(nn), w * h)
            if (w, h) in C.T_T6_SIZES and nn in C.T_T6_N:
                bit, t6 = True, C.t6_pred(nn) + t6_off
            else:
                want = C.t_pred(hyp, (w, h), nn)
                bit = want == "set"
                t6 = 250.0
            B = 500.0
        if name == flip:
            bit = not bit
        jobs.append(dict(name=name, out=out + W.timeline(B, t6 if bit else None), pre=0x400, post=0x400 | (0x40 if bit else 0)))
    return W.stage("q4-t", jobs)


for hyp in ("H-SEG", "H-N", "E806-DISC"):
    t, res = run("q4-t", t_world(hyp))
    check(f"q4-t world {hyp}: it is consistent, the rivals that differ are REFUTED; " + summ(t)[:100],
          res["gate"].ok and res["verdicts"][hyp] == "consistent" and any(v == "REFUTED" for h, v in res["verdicts"].items() if h != hyp), str(res["verdicts"]))
t, res = run("q4-t", t_world("H-SEG"))
check("q4-t: the first-piece rows (t6 = 250 + 0.43 N, 250 beyond 290) hold in the H-SEG world", res["t6"].held == 8 and res["t6"].failed == 0, str(res["t6"]))
t, res = run("q4-t", t_world("H-SEG", t6_off=60.0))
check("q4-t: t6 off by 60 us fails the first-piece rows and leaves the bit rule alone", res["t6"].failed == 8 and res["verdicts"]["H-SEG"] == "consistent", str(res["t6"]))
t, res = run("q4-t", t_world("H-SEG", flip="t4-16x16-n72"))
check("q4-t: 16x16 clear at 72 refutes H-SEG (the plan's refutation)", res["verdicts"]["H-SEG"] == "REFUTED")
t, res = run("q4-t", t_world("H-SEG", flip="t4-8x8-n60"))
check("q4-t: 8x8 set at 60 refutes H-SEG", res["verdicts"]["H-SEG"] == "REFUTED")
t, res = run("q4-t", t_world("H-SEG", flip="t4-4x4-n110"))
check("q4-t: 4x4 set at 110 refutes H-SEG", res["verdicts"]["H-SEG"] == "REFUTED")
t, res = run("q4-t", t_world("H-SEG", flip="t4-fill-n56"))
check("q4-t: the fill bridge at 56 not setting shuts the gate", not res["gate"].ok and set(res["verdicts"].values()) == {"cannot tell"})
code, text = S.gate("q4-t", t_world("H-SEG", green_bit="t4-ctl-green-8x8"))
check("q4-t: gate exit 1 when a stock green triangle sets bit 6", code == 1 and "green-8x8" in text, text[:120])
code, text = S.gate("q4-t", t_world("H-SEG", drop="t4-fill-n53"))
check("q4-t: gate exit 2 for a missing bridge row", code == 2, text[:120])
code, text = S.gate("q4-t", t_world("H-SEG"))
check("q4-t: gate exit 0 when the bridge controls pass", code == 0, text[:80])
t, res = run("q4-t", t_world("H-SEG", size_bad=(8, 8)))
check("q4-t: a size whose N = 1 control fails its MARK is void for its rows only (the other sizes still decide)",
      "VOID for its rows" in t and res["verdicts"]["H-SEG"] == "consistent", str(res["verdicts"]))
t, res = run("q4-t", t_world("H-SEG", bad_proof="t4-4x4-n170"))
check("q4-t: a failed proof at one row voids it", "proof failed" in t)
check("q4-t: the exploratory 64x64 rows print a reading with no verdict", "t4-par-64x64-n150" in t and t.count("t4-par-64x64") >= 4)
# ---- verdict over a whole attempt
import shutil  # noqa: E402
root = pathlib.Path(W.ROOT) / "attempt"
root.mkdir()
for st, d in (("q4-v", SV and v_world()), ("q4-f", f_world("H-YIELD")), ("q4-t", t_world("H-SEG"))):
    shutil.copytree(d, root / st)
import io, contextlib  # noqa: E402
buf = io.StringIO()
SV.L.depth_words = lambda p, t: [struct.unpack("<II", p[:8])[0]] * struct.unpack("<II", p[:8])[1]
with contextlib.redirect_stdout(buf):
    rc = S.verdict(str(root))
check("score_r4 verdict prints one line a stage and says which stage did not run", rc == 0 and "q4-v:" in buf.getvalue() and "p4-o4: did not run" in buf.getvalue() and "g4-rw: did not run" in buf.getvalue(), buf.getvalue()[:200])
check("score_r4: a bad stage name is a usage error", S.main(["nonsense", "x"]) == 2)
sys.exit(0 if ok else 1)
