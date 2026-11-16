# SPDX-License-Identifier: MIT
"""tests/test_twin.py (r29-flag2: r29-flag's h1 and h2 byte for byte, after s0's four copies):
the tables against the plan (closing29/plan/rank-round29.md sections 1 and
3; closing29/DECISIONS-R29.md) and the session build rules: s0 is safe (#limit 0, no
expectfault); every flagged stage's #limit counts exactly its expectfault rows that are not
controls (E946) and its last row is one of them; the #limits sum to at most 14 (9 here); the
planned events (rows the frozen hypothesis says fault or hang) are 4 faults and 4 hangs; every
control reads keys its row produces, does not expectfault and has frozen predictions; every
flagged stage is gated and ends the session on its stop; f1's knob addresses are the ones its s0
references read; h2's noreset rows follow a row of their own triple; no option outside the
kit's and the session's rules; no clock-gate, held-reset or firmware-store word."""
import os
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402
import scorekit as SK  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
ORDER = ["s0", "h1", "h2"]
JOBS = {"s0": 4, "h1": 6, "h2": 10}
LIMIT = {"s0": 0, "h1": 2, "h2": 3}
FROZEN = {"h1": "H-B24-HANG", "h2": "H-PREV16"}
R29 = os.path.join(os.path.dirname(KP), "r29-flag")


def limit(stage):
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_stages_gates_and_stops():
    assert list(CFG["stages"]) == ORDER
    assert not CFG["stages"]["s0"].get("gate")
    for st in ORDER[1:]:
        assert CFG["stages"][st].get("gate") is True, st
        assert CFG["stages"][st].get("on_stop") == "end", st
    assert set(score.GATES) == set(ORDER[1:])
    s0 = {r["name"] for r in K.table(KP, "s0")}
    assert {n for v in score.GATES.values() for n in v} == s0


def test_limits_count_the_expectfault_rows_and_cap_at_14():
    for st in ORDER:
        t = K.table(KP, st)
        assert len(t) == JOBS[st], st
        rows = [r["name"] for r in t if "expectfault" in r["knobs"] and r["set"] != "control"]
        assert len(rows) == LIMIT[st] == limit(st), st
        if rows:
            assert rows[-1] == t[-1]["name"], st
    assert sum(LIMIT.values()) == 5 <= 14
    assert sum(JOBS.values()) == 20


def test_planned_faults_and_hangs():
    faults = hangs = 0
    for st, m in FROZEN.items():
        for n, q in K.predictions(KP, st).items():
            end = q.get("end", {}).get(m)
            faults += end == "fault"
            hangs += end == "hang"
    assert (faults, hangs) == (0, 4)
    # every row any frozen model says faults or hangs is expectfault
    for st in ORDER[1:]:
        t = {r["name"]: r for r in K.table(KP, st)}
        for n, q in K.predictions(KP, st).items():
            if any(v in ("fault", "hang") for v in q.get("end", {}).values()):
                assert "expectfault" in t[n]["knobs"], n


def test_controls_can_fail_are_readable_and_never_expect_a_fault():
    for st in ORDER:
        t = K.table(KP, st)
        assert all("expectfault" not in r["knobs"] for r in t if r["set"] == "control"), st
        c = K.controls(KP, st)
        SK.refuse_unreadable(c, score.producible)
        preds = K.predictions(KP, st)
        assert all(preds.get(n) for n in c), st
    s0 = K.table(KP, "s0")
    assert all(r["set"] == "control" and r["risk"] == "safe" for r in s0)
    assert all(r["risk"] == "risky" for st in ORDER[1:] for r in K.table(KP, st) if "expectfault" in r["knobs"])
    # each Q010 hypothesis' reading is reachable among the controls (black and E037's hash)
    p = K.predictions(KP, "s0")
    hashes = {p[n]["hash"]["H-REF"] for n in ("c10-zc", "c10-zn", "c10-bc", "c10-bn")}
    h1 = K.predictions(KP, "h1")["q010-p1"]["hash"]
    assert hashes == {h1["H-KEEP"], h1["H-RECOV-CLR"]}


def test_h1_h2_are_r29_flags_frozen_rows_and_predictions():
    if not os.path.isdir(R29):
        return
    for st in ("h1", "h2"):
        rows = [ln for ln in open(os.path.join(KP, "tables", st + ".txt")) if not ln.startswith("#")]
        old = [ln for ln in open(os.path.join(R29, "tables", st + ".txt")) if not ln.startswith("#")]
        assert rows == old, st
        assert limit(st) == int(open(os.path.join(R29, "tables", st + ".txt")).read().split("#limit ")[1].split()[0])
        assert open(os.path.join(KP, "predictions", st + ".tsv")).read() == \
            open(os.path.join(R29, "predictions", st + ".tsv")).read(), st
    old = {ln.split("|")[0]: ln for ln in open(os.path.join(R29, "tables", "s0.txt")) if not ln.startswith("#")}
    for ln in open(os.path.join(KP, "tables", "s0.txt")):
        if not ln.startswith("#"):
            assert old[ln.split("|")[0]] == ln


def test_q010_copies_and_hangs():
    s0 = {r["name"]: r for r in K.table(KP, "s0")}
    h1 = K.table(KP, "h1")
    h2 = K.table(KP, "h2")
    assert [r["name"] for r in h1] == ["q010-af", "q010-ld2", "q010-pre", "q010-h1", "q010-p1", "q010-h2"]
    assert h2[0]["name"] == "q010-p2"
    noload = s0["c10-zn"]["args"]
    assert "xfer" not in noload and s0["c10-bn"]["args"] == noload
    for r in h1 + h2[:1]:
        if r["name"] in ("q010-af", "q010-pre", "q010-p1", "q010-p2"):
            assert r["args"] == noload and r["tool"] == "t22"
    assert h1[1]["args"] == s0["c10-bc"]["args"]
    assert h1[3]["args"] == h1[5]["args"] and "--vdm 2^=0x01000000" in h1[3]["args"]
    assert "--index-width" not in h1[3]["args"] and h1[3]["tool"] == "t10"


def test_h2_triples():
    t = K.table(KP, "h2")[1:]
    names = [r["name"] for r in t]
    assert names == ["h2-c-a", "h2-c-b", "h2-a3", "h2-b1", "h2-b2", "h2-b3", "h2-c1", "h2-c2", "h2-c3"]
    for i, r in enumerate(t):
        assert ("noreset" in r["knobs"]) is (i % 3 != 0), r["name"]
    assert t[1]["set"] == "control" and "expectfault" not in t[1]["knobs"]
    assert [r["name"] for r in t if "expectfault" in r["knobs"]] == ["h2-a3", "h2-b3", "h2-c3"]
    assert t[0]["args"] == t[1]["args"] and t[0]["args"].endswith('--vdm 1^=0x00000800 "$S/bins/p1131-blue__0.bin"')
    for n in (2, 5, 8):
        assert t[n]["args"].endswith('--vdm 9^=0x00000600 "$S/bins/p1131-blue__0.bin"')
    assert "--vdm 1^=0x00000e00" in t[4]["args"] and "--vdm 1^=0x00000200" in t[7]["args"]
    assert "--vdm" not in t[3]["args"] and "--vdm" not in t[6]["args"]


def test_no_option_outside_the_rules():
    bad = ("--kreg", "--kregnow", "--clkgate", "--trc-hazard", "--fault", "--scratch-at", "--refill",
           "--kpoke-job", "--hold", "--str", "--index-width")
    for st in ORDER:
        for r in K.table(KP, st):
            a = r["args"].split()
            assert not set(a) & set(bad), r["name"]
            kp = [a[i + 1] for i, x in enumerate(a) if x == "--kpoke-render"]
            assert all(p.split("=")[0] in ("1:ta:143", "1:ta:144") for p in kp), r["name"]
            assert "idle:" not in " ".join(r["knobs"])
            assert not any("hold" in w for w in r["knobs"])
