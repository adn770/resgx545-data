#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the R1-events scorers (score/score_r1.py) on synthetic records (every hypothesis of Q290, Q082 and
Q033 as a model that builds the records it would leave, every void and cannot-tell state) and on past-run fixtures (S2's
e1c kick jobs and e1j tri64, fill and partial pages, the E746 and E747 data; E431's event-fine output for Q082's control).
Run with the scratch venv:  PYTHONDONTWRITEBYTECODE=1 ../../closing/pixel-faults/.venv/bin/python tests/test_scorer.py
Exit 0 when every check holds.  Nothing here touches the laptop."""
import gzip
import json
import pathlib
import re
import struct
import sys
import tempfile

sys.dont_write_bytecode = True
R1 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R1 / "score"))
sys.path.insert(0, str(R1 / "gen"))
import score_r1 as S  # noqa: E402
import r1layout as L  # noqa: E402

FAIL = []
DATA = pathlib.Path.home() / "src/resgx545-data"
S2OUT = pathlib.Path.home() / "src/scratch/resgx545/closing/s2/out"


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


# ---- builders ------------------------------------------------------------------------------------------------------
def blank():
    p = [0] * L.PAGE_DWORDS
    p[0] = L.MAGIC
    return p


def put(p, slot, e):
    base = L.RING_BASE[slot]
    for j in range(L.RUNGS[slot]):
        o = base + L.RUNG * j
        if p[o] == 0:
            p[o:o + 5] = [1, *e]
            return
    p[L.DROP + slot] += 1


def tick(K, stamp):
    return (2, K << 24, L.PA2_CONST, stamp)


def kickw(K, stamp):
    return (0, (K << 24) | 0x100, 0x01000000 | 5000, stamp)


def jobw(bit, K, stamp):
    return (0, (K << 24) | (1 << bit), 0x01000000 | 7000, stamp)


BASE = 0x10000000


def ring_rec(name, sset, page, **kw):
    r = {"name": name, "set": sset, "op": "k", "class": "ok", "rc": 0, "trigger_rc": 0, "note": "", "run": "RUN",
         "page": page, "page2": list(page), "window_stamp": BASE - 1000, "tool_rc": 0, "fatal": [], "log_bad": []}
    r.update(kw)
    return r


def write_stage(d, stage, recs, exit_code=0, extra_files=None):
    d = pathlib.Path(d)
    d.mkdir(parents=True, exist_ok=True)
    names = [r["name"] for r in recs]
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": "RUN", "exit": exit_code, "why": "", "jobs_run": names}))
    for r in recs:
        (d / f"{r['name']}.json").write_text(json.dumps(r))
    for n, txt in (extra_files or {}).items():
        with gzip.open(d / f"{n}.tool.txt.gz", "wb") as g:
            g.write(txt.encode())
    return d


def rows_of(Sg, quantity=None, case=None):
    return [r for r in Sg.t.rows if (quantity is None or r[1] == quantity) and (case is None or r[0] == case)]


def run_stage(stage, recs, extra=None, fn=None):
    with tempfile.TemporaryDirectory() as tmp:
        d = write_stage(tmp, stage, recs, extra_files=extra)
        Sg = S.Stage(stage, d)
        out = (fn or S.SCORERS[stage])(Sg)
        return Sg, out


# ---- Q290: every hypothesis as a model -----------------------------------------------------------------------------
def k_model(model, drop_k5=False):
    """The records the 15 jobs of table k leave under model kw (H-KW = H-HWC), sat (H-SAT) or fw2 (the byte is 2)."""
    recs = []
    t = S.load_table("k")
    for j in t["jobs"]:
        n, base = j["name"], j["name"].split("-")[0]
        p = blank()
        calls = {"std": 2, "nomisc": 1, "extra2": 4}[j["arm_variant"]]
        cmds = calls
        kk = lambda c: 2 if model == "fw2" else (min(c, 255) if model == "sat" else c % 256)  # noqa: E731
        kw = {"ident_after_arm": calls, "arm_calls": calls}
        if base in ("k0", "k1", "k2", "k3"):
            for i in range(8):
                put(p, 0, tick(kk(cmds), BASE + 25000 * i))
            kw["ccbctl_after"] = [cmds % 256, 0]
        elif base == "k4":
            put(p, 0, tick(kk(cmds), BASE))
            put(p, 0, kickw(kk(cmds), BASE + 9000))
            cmds += 1
            for i in range(1, 15):
                put(p, 0, tick(kk(cmds), BASE + 25000 * i))
            kw["ccbctl_after"] = [cmds % 256, 0]
        elif base == "k5":
            cmds += 254
            ks = []
            for i in range(4):
                put(p, 0, kickw(kk(cmds), BASE + 4000 * i))
                cmds += 1
            for i in range(1, 6):
                put(p, 0, tick(kk(cmds), BASE + 20000 + 25000 * i))
            kw["ccbctl_after"] = [cmds % 256, 0]
            kw["ident_total"] = 2 + 254 + 4
            if drop_k5:
                kw["kick_errors"] = [{"ms": 500, "errno": 110}]
        elif base == "k6":
            K = cmds
            put(p, 0, jobw(8, K, BASE))
            K += 1
            put(p, 1 if False else 3, jobw(4, K, BASE + 900))
            put(p, 0, jobw(8, K, BASE + 400000))
            kw["ccbctl_after"] = [(K + 1) % 256, 0]
        recs.append(ring_rec(n, j["set"], p, **kw, **({"class": "kick-timeout"} if kw.get("kick_errors") else {})))
    return recs


def test_k():
    for model in ("kw", "sat", "fw2"):
        Sg, (ok, why, summ) = run_stage("k", k_model(model))
        r = lambda q, c=None: rows_of(Sg, q, c)  # noqa: E731
        if model == "kw":
            check(all(x[4] is True for x in r("K_ticks")), "k, H-KW: every K_ticks row held (k0, k0-r2, k1, k2 x2, k3 x2)")
            check(all(x[4] is True for x in r("ccbctl0")) and all(x[4] is True for x in r("ident_after_arm")),
                  "k, H-KW: ccbctl[0] and the kernel-log GETMISCINFO count held in every job")
            check([x[4] for x in r("K_kicks")] == [True, True] and [x[4] for x in r("K_ticks_after", "k5")] == [True],
                  "k, H-KW: the 254 kicks wrap the byte: kick entries 0, 1, 2, 3 and ticks 4 (k5, k5-r2)")
            alt = [x for x in r("K_kicks_alt")]
            check(all(x[4] is False for x in alt), "k, H-KW: the H-SAT alternative reads FALSE on the wrapped byte")
            check(all(x[4] is True for x in r("K_step_rule")) and all(x[4] is True for x in r("nontick_entries")),
                  "k, H-KW: the E747 step rule (+1 after each (0,8) entry only) and E746's single kick entry held")
            check("controls held" in summ and "fit:" in summ and "held out:" in summ,
                  "k: the summary tallies fit rows and held-out rows apart and says the controls held")
            ho = [x for x in Sg.t.rows if x[3] == "held out"]
            ft = [x for x in Sg.t.rows if x[3] == "fit"]
            check(ho and ft and not ({id(x) for x in ho} & {id(x) for x in ft}), f"k: {len(ft)} fit rows and {len(ho)} held-out rows kept apart")
        elif model == "sat":
            check(all(x[4] is False for x in r("K_kicks")) and all(x[4] is True for x in r("K_kicks_alt")),
                  "k, H-SAT: the byte stays at 255: H-KW refuted on the kicks, the H-SAT alternative reads TRUE")
        else:
            check(all(x[4] is False for x in r("K_ticks", "k2")) and all(x[4] is True for x in r("K_ticks_alt", "k2")),
                  "k, H-FW: a byte that is 2 whatever the host sent refutes K = 1 on k2 and fits the alternative")
    Sg, (ok, why, summ) = run_stage("k", k_model("kw", drop_k5=True))
    check(all(x[4] is None for x in rows_of(Sg, "K_kicks")) and all(x[4] is None for x in rows_of(Sg, "ccbctl0", "k5")),
          "k: a kick that timed out in k5 is cannot tell (no verdict on the wrap)")
    # void and cannot-tell states
    recs = k_model("kw")
    recs[0]["class"] = "tickstop"
    recs[1]["page2"][L.RING_BASE[0] + 6] ^= 1
    del recs[2]["page"]
    Sg, (ok, why, summ) = run_stage("k", recs)
    check("NODATA (class tickstop)" in "\n".join(Sg.lines) and "window 0 did not take" in "\n".join(Sg.lines)
          and "no page" in "\n".join(Sg.lines), "k: a class that is not a result, a ring that changed after the close and no page are void")
    check(all(x[4] is None for x in rows_of(Sg, "K_ticks", "k0")), "k: a void job's rows count as cannot tell, never as a pass")
    recs = k_model("kw")
    recs[3]["ident_after_arm"] = 2           # k2 (nomisc): the kernel log shows 2 answers but the runner made 1 call
    Sg, (ok, why, summ) = run_stage("k", recs)
    check(rows_of(Sg, "K_ticks", "k2")[0][4] is None and "cannot tell" in summ,
          "k: a variant that is not shown (kernel-log count != the arm path's calls) is cannot tell")
    recs = k_model("kw")
    p = recs[0]["page"]
    for i in range(0, 8):
        o = L.RING_BASE[0] + 8 * i
        p[o + 4] = (BASE - 5000 - 25000 * (8 - i)) & 0xFFFFFFFF      # entries older than the window's own stamp
    recs[0]["page2"] = list(p)
    Sg, (ok, why, summ) = run_stage("k", recs)
    check(rows_of(Sg, "K_ticks", "k0")[0][4] is None, "k: entries before the window's own CR_TIMER stamp are dropped (no ticks left: cannot tell)")
    recs = k_model("kw")
    recs[0]["page"][L.DROP] = 3
    recs[0]["page2"] = list(recs[0]["page"])
    Sg, _ = run_stage("k", recs)
    check(rows_of(Sg, "K_ticks", "k0")[0][4] is None, "k: a full ring (drops) is cannot tell")
    Sg, (ok, why, summ) = run_stage("k", k_model("kw")[:3] + [])
    check("NODATA (no record kept)" in "\n".join(Sg.lines), "k: a job with no record is void")


def test_k_past():
    for name, K in (("kick", 2), ("kick-r2", 3), ("kick-r3", 4)):
        r = json.loads((S2OUT / "e1c" / f"{name}.json").read_text())
        ev = S.merged(S.ring(r["page"]))
        kx = [e for e in ev if S.e_kick(e)]
        after = [e for e in ev if S.e_tick(e) and S.rel(e[4], kx[0][4]) > 0]
        check(len(kx) == 1 and L.count_of(kx[0][2]) == K and {L.count_of(e[2]) for e in after} == {K + 1},
              f"past run (S2 e1c {name}, E746): the kick entry carries K = {K} (the value before its bump) and the ticks after K + 1")
    # the frozen k4 rows (K = 2, +1) on the first kick job, which is the arm's first command after the miscinfo (K = 2)
    r = json.loads((S2OUT / "e1c" / "kick.json").read_text())
    rec = ring_rec("k4", "fit", r["page"], page2=r["page2"], ident_after_arm=2, arm_calls=2, ccbctl_after=[3, 0], window_stamp=None)
    Sg, out = run_stage("k", [rec])
    got = {x[1]: x[4] for x in rows_of(Sg, None, "k4")}
    # S2's 20 ms window filled the 16 rungs (9 drops): "exactly one non-tick entry" is then cannot tell, by design
    check(got.get("K_kick") is True and got.get("K_ticks_after") is True and got.get("ccbctl0") is True
          and got.get("nontick_entries") is None,
          "past run (S2 e1c kick) through score_k: the frozen k4 rows K = 2 and +1 held; the ring that dropped is cannot tell "
          "for the single-entry row")
    # E746's K stepping across the three kicks (2, 3, 4) in job order is the arm/kick fit of the frozen rows
    check(True, "past run: E746's K = 2, 3, 4 on the three kicks is the fit the k4 rows are labelled with")


# ---- Q033 ------------------------------------------------------------------------------------------------------------
def d0_records(model_ok=True):
    t = S.load_table("d0")
    recs = []
    for j in t["jobs"]:
        p = blank()
        K = 2
        if j["name"].startswith("d0-tri64"):
            for i, (slot, bit) in enumerate(S.E747_TRI64):
                put(p, slot, jobw(bit, K, BASE + 1000 * i))
                if bit == 8:
                    K += 1
        else:
            for r_ in range(2):
                for slot, bit in ((0, 8), (2, 21), (2, 10), (3, 4), (3, 22), (1, 9), (3, 4), (3, 22)):
                    put(p, slot, jobw(bit, K, BASE + 100000 * r_ + 1000 * len(p)))
                    if bit == 8:
                        K += 1
            for i in range(5):
                put(p, 0, jobw(8, K, BASE + 900000 + 1000 * i))
                K += 1
        rr = ring_rec(j["name"], j["set"], p, op="ringtool", tool_rc=0, trigger_rc=0, tool_out="diff: 0 of 4096")
        if j["knobs"]:
            rr["knobs_readback"] = {k: v for k, v in j["knobs"].items()}
        recs.append(rr)
    return recs


def test_d0():
    Sg, (ok, why, summ) = run_stage("d0", d0_records())
    check(ok is True and "controls held" in summ, "d0: E747's tri 64x64 (9 entries), the partial render's slot-2 bits 21 and 10 and dispatch 100% open the gate")
    check(all(x[4] is True for x in Sg.t.rows if x[3] != "alt"), f"d0: every frozen row held ({len(Sg.t.rows)} rows)")
    recs = d0_records()
    put(recs[0]["page"], 0, jobw(19, 5, BASE + 5000000))               # a bit-19 entry in the control: E747 says none
    recs[0]["page2"] = list(recs[0]["page"])
    Sg, (ok, why, summ) = run_stage("d0", recs)
    check(ok is not True and rows_of(Sg, "bit19_entries", "d0-tri64")[0][4] is False, "d0: a bit-19 entry in D0 closes the gate and reads FAILED")
    recs = d0_records()
    recs[2]["page"][L.RING_BASE[2]:L.RING_BASE[2] + 8 * L.RUNGS[2]] = [0] * (8 * L.RUNGS[2])   # slot 2 silent: no overflow path
    recs[2]["page2"] = list(recs[2]["page"])
    Sg, (ok, why, summ) = run_stage("d0", recs)
    check(ok is not True, "d0: a partial render that logs no slot-2 entries closes the gate")
    recs = d0_records()
    recs[0]["page"][L.DROP + 3] = 1
    recs[0]["page2"] = list(recs[0]["page"])
    Sg, (ok, why, summ) = run_stage("d0", recs)
    check(ok is not True and rows_of(Sg, "entries", "d0-tri64")[0][4] is None, "d0: a ring that dropped an entry is cannot tell (and no gate)")
    recs = d0_records()
    recs[1]["class"] = "trigfail"
    Sg, (ok, why, summ) = run_stage("d0", recs)
    check(ok is not True and "NODATA" in "\n".join(Sg.lines), "d0: a void control closes the gate")
    recs = d0_records()
    recs[0]["knobs_readback"] = {}
    recs[2]["knobs_readback"] = {"render_pb_pages": "0x00000422"}
    Sg, (ok, why, summ) = run_stage("d0", recs)
    check(ok is not True and "knob render_pb_pages read back" in "\n".join(Sg.lines), "d0: a knob that read back wrong is void")


def d0_past():
    """S2's e1j pages (E747) through the R1 reader: 8 rungs in slot 3 there, 12 here, zeros past slot 3's old end."""
    out = {}
    for name in ("tri64", "fill", "partial"):
        r = json.loads((S2OUT / "e1j" / f"{name}.json").read_text())
        out[name] = r
        ev = S.merged(S.ring(r["page"]))
        out[name + "-ev"] = ev
    return out


def test_d_past():
    f = d0_past()
    ev = f["tri64-ev"]
    check(S.seq_of(ev) == S.E747_TRI64 and S.dispatch_ok(ev), "past run (S2 e1j tri64, E747): the 9 entries in E747's order, dispatch 100%")
    ev = f["fill-ev"]
    check([x for x in S.seq_of(ev)][:3] == [(0, 8), (3, 4), (0, 8)], "past run (S2 e1j fill): 0:8, 3:4, 0:8 (the end-of-render witness)")
    ev = f["partial-ev"]
    check({S.e_bit(e) for e in ev if e[0] == 2} == {21, 10} and not any(e[2] & (1 << 19) for e in ev),
          "past run (S2 e1j partial, E747): slot 2 bits 21 and 10, no bit 19")
    # the same page read as a D0 record
    rec = ring_rec("d0-tri64", "fit", f["tri64"]["page"], page2=f["tri64"]["page2"], op="ringtool", tool_out="diff: 0 of 4096", window_stamp=None)
    Sg, _ = run_stage("d0", [rec], fn=S.score_d0)
    check(rows_of(Sg, "entries", "d0-tri64")[0][4] is True, "past run: score_d0 holds E747's tri64 row on S2's own page")


def d1_timeline(pb, bit_seq, nparts, knob=None, regs=S.__dict__.get("RT", "0x012c,0x0118,0x0624,0x0658,0x0724")):
    cols = regs.split(",")
    start = 300_000_000
    rows = [(100_000, {"0x0624": 0x400})]
    t = start + 1_000_000
    kv = knob if knob is not None else pb - 0x22                  # S1b: 0x0624 = P - 0x22 (0x422 gives 0x400)
    rows.append((t, {"0x0624": kv, "0x0724": 0x10}))
    t += 100000
    for bit in bit_seq:
        if bit == 21:
            rows.append((t, {"0x0624": kv, "0x0724": 0x10, "0x0658": 1}))
            t += 5000
            rows.append((t, {"0x0624": kv, "0x0724": 0x10, "0x0658": 0}))
        rows.append((t, {"0x0624": kv, "0x0724": 0x10, "0x012c": 0x20000000 | (1 << (22 - bit))}))
        t += 1000
        rows.append((t, {"0x0624": kv, "0x0724": 0x10}))
        t += 50000
    txt = [f"timeline: regs {' '.join(cols)} samples 1000 seconds 0 start {start} end {start + 500_000_000} rc 0"]
    for tt, v in rows:
        d = {"0x012c": 0x20000000, "0x0118": 0x400, "0x0624": 0x400, "0x0658": 0, "0x0724": 0}
        d.update(v)
        txt.append("tl " + str(tt) + " " + " ".join(f"{d[c]:08x}" for c in cols))
    return "\n".join(txt) + "\n"


def d1_records(model, drop_slot0=False):
    """model raise: bit 19 in raise jobs only; thresh: in every job that reaches thr0; never: none."""
    t = S.load_table("d1")
    recs, extra = [], {}
    for j in t["jobs"]:
        pb = int(j["pb"], 16)
        nparts = {0x320: 3, 0x3a0: 2, 0x422: 0}[pb]
        raised = pb == 0x320
        p = blank()
        K = 2
        seq = [(0, 8)]
        bits = [8]
        for _ in range(nparts):
            for slot, bit in ((2, 21), (2, 10), (3, 4), (3, 22), (1, 9), (3, 4), (3, 22)):
                seq.append((slot, bit))
                bits.append(bit)
        b19 = (model == "thresh" and nparts) or (model == "raise" and raised)
        if b19:
            seq.append((0, 19))
            bits.append(19)
        seq += [(0, 8)] * 5
        bits += [8] * 5
        for i, (slot, bit) in enumerate(seq):
            put(p, slot, jobw(bit, K, BASE + 1000 * i))
            if bit == 8:
                K += 1
        if drop_slot0:
            p[L.DROP + 0] = 2
        b = [0] * 59
        if raised:
            b[38] = 0x20
        rr = ring_rec(j["name"], j["set"], p, op="ringtool", tool_rc=3 if nparts else 0, trigger_rc=3 if nparts else 0,
                      tool_out="scene overflowed" if nparts else "ok", knobs_readback={"render_pb_pages": j["pb"]} if j["knobs"] else {},
                      buf09=b)
        recs.append(rr)
        extra[j["name"]] = d1_timeline(pb, bits, nparts)
    return recs, extra


def test_d1():
    for model, want in (("raise", "H-RAISE favoured"), ("thresh", "H-THRESH favoured"), ("never", "H-NEVER")):
        recs, extra = d1_records(model)
        Sg, (ok, why, summ) = run_stage("d1", recs, extra)
        check(want in summ, f"d1, {model}: the summary reads '{want}' ({summ[:90]})")
        if model == "raise":
            d5 = rows_of(Sg, "D5_bit3_pulses")
            check(all(x[4] is True for x in d5), "d1, raise: D5 held in every job (status bit-3 pulses = the ring's bit-19 entries, in order)")
            check(all(x[4] is True for x in rows_of(Sg, "bit19_entries") if x[2].startswith("H-RAISE")),
                  "d1, raise: every H-RAISE row held (>= 1 in D2, none in D3 and D4)")
            alt = rows_of(Sg, "bit19_entries_alt")
            check(alt and all(x[4] is False for x in alt), "d1, raise: the H-THRESH alternative on D3 reads FALSE (the TA reached thr0 and no bit 19 came)")
        if model == "thresh":
            check(any(x[4] is False for x in rows_of(Sg, "bit19_entries") if x[0].startswith("d3")),
                  "d1, thresh: bit 19 in D3 refutes H-RAISE there")
        if model == "never":
            check(any(x[4] is False for x in rows_of(Sg, "bit19_entries") if x[0].startswith("d2")), "d1, never: no bit 19 in D2 refutes H-RAISE")
    recs, extra = d1_records("raise", drop_slot0=True)
    Sg, (ok, why, summ) = run_stage("d1", recs, extra)
    check(all(x[4] is None for x in rows_of(Sg, "bit19_entries") if x[0].startswith("d3")),
          "d1: slot 0 full is cannot tell for 'none' (D3), never a pass")
    recs, extra = d1_records("raise")
    for r in recs:
        if r["name"].startswith("d2"):
            r["buf09"][38] = 0
    Sg, (ok, why, summ) = run_stage("d1", recs, extra)
    check("cannot tell" in summ and all(x[4] is None for x in rows_of(Sg, "bit19_entries") if x[0].startswith("d2")),
          "d1: a raise that does not reproduce in D2 is cannot tell (H-RAISE is not tested)")
    recs, extra = d1_records("raise")
    extra[recs[0]["name"]] = d1_timeline(0x320, [8], 0, knob=0x400)
    Sg, (ok, why, summ) = run_stage("d1", recs, extra)
    check("knob did not land" in "\n".join(Sg.lines), "d1: the job's own 0x0624 (not the previous job's) is the knob proof: a wrong value is void")
    recs, extra = d1_records("raise")
    del extra[recs[1]["name"]]
    Sg, (ok, why, summ) = run_stage("d1", recs, extra)
    check("no timeline" in "\n".join(Sg.lines), "d1: no timeline kept is void")
    recs, extra = d1_records("raise")
    recs[3]["knobs_readback"] = {"render_pb_pages": "0x00000422"}
    Sg, _ = run_stage("d1", recs, extra)
    check("read back" in "\n".join(Sg.lines), "d1: a render_pb_pages read-back that is not the written value is void")


# ---- Q082 --------------------------------------------------------------------------------------------------------------
def t_model(model):
    """The records the 56 jobs of table t leave under model t_iter, t_instr or t_time (as tests/fake_tool.py's)."""
    def latch(kind, iters, shape):
        body = {"b8": 8, "b16": 16, "b4": 4, "ld8": 8}[kind]
        side = 0 if shape == "fill" else int(shape[3:])
        if model == "t_iter":
            return iters >= 55
        if model == "t_instr":
            return iters * body >= 440
        f = {0: 1.0, 256: 1.0, 128: 1.3, 32: 2.0, 8: 6.0}[side]
        if kind == "ld8":
            f = 0.6 if side == 8 else 1.0
        return iters * body / f >= 440
    recs = []
    for j in S.load_table("t")["jobs"]:
        n = j["name"]
        if j["op"] == "hold_fault":
            recs.append({"name": n, "set": j["set"], "op": "hold_fault", "class": "ok", "rc": 0, "run": "RUN", "status2_pre": 0x400,
                         "snap1_status2": 0x480, "snap2_status2": 0x480, "status2_post": 0x400, "tool_rc": 1})
            continue
        if j["kind"] == "vtx":
            out = "probe vtx-stock: tri 64x64\nprobe vtx-stock: o0 mixed 0xff00ff00 x1062 0xff203040 x3034\n"
            recs.append({"name": n, "set": j["set"], "op": "probe", "class": "ok", "rc": 0, "run": "RUN", "status2_pre": 0x400,
                         "status2_post": 0x400, "tool_rc": 0, "tool_out": out})
            continue
        post = 0x440 if latch(j["kind"], j["iters"], j["shape"]) else 0x400
        if j["shape"] == "fill":
            body = {"b8": 8, "b16": 16, "b4": 4, "ld8": 8}[j["kind"]]
            out = f"probe x: job time: {20 + j['iters'] * body * 3} us\nprobe x: o0 0x00000000 (2048 of 2048)\n"
        else:
            side = int(j["shape"][3:])
            out = f"probe x: o0 mixed 0xff203040 x{side * side - 30} 0x00000000 x30\n"
        recs.append({"name": n, "set": j["set"], "op": "probe", "class": "ok", "rc": 0, "run": "RUN", "status2_pre": 0x400,
                     "status2_post": post, "tool_rc": 0, "tool_out": out})
    return recs


def test_t():
    for model in ("t_iter", "t_instr", "t_time"):
        Sg, (ok, why, summ) = run_stage("t", t_model(model))
        v = Sg.verdicts
        if model == "t_instr":
            check(v["T0"] is True and v["T1"] == (True, False) and v["T2"] == (True, False) and v["T3"] == (False, True)
                  and v["T4"] == (False, True), f"t, H-INSTR: T0 held; H-TIME/H-INSTR hold on T1 and T2, H-ITER refuted; T3 flat; T4 flat {v['T1'], v['T2'], v['T3'], v['T4']}")
        elif model == "t_iter":
            check(v["T0"] is True and v["T1"] == (False, True) and v["T2"] == (False, True) and v["T3"] == (False, True)
                  and v["T4"] == (False, True), f"t, H-ITER: bit 6 at 55 iterations whatever the body: T1, T2 refute the instruction model {v['T1'], v['T2'], v['T3'], v['T4']}")
        else:
            check(v["T0"] is True and v["T1"] == (True, False) and v["T2"] == (True, False) and v["T3"] == (True, False)
                  and v["T4"] == (True, False), f"t, H-TIME: occupancy (T3) and latency (T4) rows hold H-TIME and refute the flat models {v['T3'], v['T4']}")
        check("held out:" in summ and "control:" in summ, f"t, {model}: the tally keeps held-out and control rows apart")
    Sg, (ok, why, summ) = run_stage("t", t_model("t_instr"))
    check(rows_of(Sg, "status2", "t6-hang")[0][4] is True and rows_of(Sg, "status2", "t6-vtx0")[0][4] is True,
          "t: the TA controls (0x400 with no loop, 0x480 on the held fault) held")
    recs = t_model("t_instr")
    for r in recs:
        if r["name"].startswith("t0-b8-56"):
            r["status2_post"] = 0x400                    # the control fails: bit 6 not set at 56
    Sg, (ok, why, summ) = run_stage("t", recs)
    check(Sg.verdicts["T0"] is False and "a control failed" in summ, "t: T0's control failing (56 reads 0x400) is stated: the ladders are cannot tell")
    recs = t_model("t_instr")
    recs[0]["status2_pre"] = 0x440
    Sg, _ = run_stage("t", recs)
    check("NODATA (the job's own pre read" in "\n".join(Sg.lines), "t: a job whose own pre read is not 0x400 is void (the previous job's latch is not its own)")
    recs = t_model("t_instr")
    for r in recs:
        if r["name"] == "t2-b4-110":
            r["tool_out"] = "probe x: job time: 500 us\n"
    Sg, _ = run_stage("t", recs)
    check("t2-b4-110: NODATA (no o0 = 0" in "\n".join(Sg.lines), "t: no o0 = 0 line is void (the loop did not end)")
    recs = t_model("t_instr")
    for r in recs:
        if r["name"] == "t3-s8-440":
            r["class"] = "trigfail"
    Sg, _ = run_stage("t", recs)
    check(Sg.verdicts["T3"] == (None, None) and "t3-s8-440" in Sg.verdicts["voids"], "t: a void ladder point leaves T3 cannot tell")
    recs = t_model("t_instr")
    for r in recs:
        if r["name"].startswith("t1-b16-"):
            r["tool_out"] = r["tool_out"].replace(re.search(r"job time: (\d+) us", r["tool_out"])[0], "job time: 500 us")
    Sg, (ok, why, summ) = run_stage("t", recs)
    check("DOES NOT GROW" in "\n".join(Sg.lines) and "a control failed" in summ, "t: a fill ladder whose job time does not grow with the iterations fails the knob proof")
    recs = t_model("t_instr")
    for r in recs:
        if r["name"] == "t6-hang":
            r["snap1_status2"] = 0x400
    Sg, _ = run_stage("t", recs)
    check(rows_of(Sg, "status2", "t6-hang")[0][4] is False, "t: the held TA fault reading 0x400 is FAILED (control)")
    # E431's own data through the scorer's threshold logic (past-run fixture)
    for sub, fix in (("event-fine", lambda i: 48 + i), ):
        txt = (DATA / "platform" / sub / "output.txt").read_text()
        runs = {}
        for m in re.finditer(r"== case(\d+)-order(\d+):.*?\n(?:.*\n)*?status2: (0x[0-9a-f]+)\n(?:.*\n)*?status2: (0x[0-9a-f]+)\n", txt):
            pass
        blocks = re.split(r"^== ", txt, flags=re.M)[1:]
        for b in blocks:
            m = re.match(r"case(\d+)-order(\d+):", b)
            st = re.findall(r"^status2: (0x[0-9a-f]+)", b, re.M)
            if m and len(st) >= 2:
                runs.setdefault(int(m[2]), {})[int(m[1])] = (int(st[0], 16), int(st[1], 16))
        ok_all = []
        for order, lad in runs.items():
            ladder = {i: bool(post & 0x40) for i, (pre, post) in lad.items()}
            fs = S.first_set(ladder)
            ok_all.append(all(pre == 0x400 for pre, _ in lad.values()) and fs[0] in (54, 55) and not ladder[53] and ladder[55] and ladder[56])
        check(len(runs) == 3 and all(ok_all), f"past run (E431 {sub}, 3 runs of 48..56): every job's own pre read is 0x400, 53 clear, 55 and 56 set: "
              f"the T0 control reads as E431 did ({sorted(runs)})")
    txt = (DATA / "platform" / "event-steps" / "output.txt").read_text()
    pairs = {}
    for b in re.split(r"^== ", txt, flags=re.M)[1:]:
        m = re.match(r"case(\d+)-order(\d+):", b)
        st = re.findall(r"^status2: (0x[0-9a-f]+)", b, re.M)
        if m and len(st) >= 2:
            pairs[(int(m[2]), 16 + 8 * int(m[1]))] = int(st[1], 16)
    ok_steps = all((v & 0x40) == (0x40 if it >= 56 else 0) for (o, it), v in pairs.items())
    check(len(pairs) >= 40 and ok_steps, f"past run (E431 event-steps, {len(pairs)} jobs of 16..136 by 8): bit 6 clear to 48, set from 56 as the ladder logic reads it")


def test_misc():
    check(S.parse_o0("probe x: o0 0x00000000 (2048 of 2048)") == ("fill", 2048), "parse_o0: the fill line")
    check(S.parse_o0("probe x: o0 mixed 0xff203040 x46 0x00000000 x18") == ("tri", 18), "parse_o0: the triangle line counts the o0 = 0 pixels")
    check(S.parse_o0("probe x: o0 0x00000037 (2048 of 2048)") == ("other", 0), "parse_o0: a fill that did not reach 0 is not o0 = 0")
    check(S.first_set({53: False, 56: True, 80: True}) == (56, 53, True) and S.first_set({53: False, 56: True, 80: False})[2] is False,
          "first_set: bracket and monotonicity")
    check(S.linear_ok([1, 2, 3, 4], [10, 20, 30, 40]) is True and S.linear_ok([1, 2, 3, 4], [40, 30, 20, 10]) is False
          and S.linear_ok([1, 2], [1, 2]) is None, "linear_ok: grows, shrinks, too few points")
    check(S.lcs([1, 2, 3, 4], [1, 3, 4]) == 3, "lcs")
    s = S.Stage("k", "/nonexistent")
    check(s.stage_note().startswith("no stage.json"), "a missing stage.json is a note, not a crash")
    with tempfile.TemporaryDirectory() as tmp:
        d = write_stage(tmp, "k", [ring_rec("k0", "fit", blank())])
        (d / "k0.json").write_text(json.dumps({"name": "k0", "run": "OTHER"}))
        check(S.record(d, "k0") is None, "a record of another run of the stage is not read (nothing is ever deleted)")


def main():
    for fn in (test_misc, test_k, test_k_past, test_d0, test_d_past, test_d1, test_t):
        print(f"--- {fn.__name__}")
        try:
            fn()
        except Exception as e:           # a test that crashes is a failure, not a skip
            import traceback
            traceback.print_exc()
            check(False, f"{fn.__name__} raised {e!r}")
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
