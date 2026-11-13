# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing13/plan/rank-round13.md sections 2-3,
"F1" to "F3") and the session build rules: each stage's #limit counts exactly its planned rows
(expectfault rows that are not controls, E946's slip designed out) and the last planned row is the
stage's last row (the count never stops a stage with a row left); a control can fail and reads a
key its row produces (scorekit.refuse_unreadable); f1's and f2's controls do not expectfault (a
fault there stops the stage); noreset is never a stage's first row and follows a row that ends ok
or as a recovered hang under the frozen counter (else the runner skips it); one idle:60, on f3's
idle row only; no knob, no kernel poke, no clock-gate option; tools t10 and t10p (one binary)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import f3  # noqa: E402
import kitscore as K  # noqa: E402
import score  # noqa: E402
import scorekit as SK  # noqa: E402

PLANNED = {"f1": 2, "f2": 3, "f3": 8}


def limit(stage):
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_limit_counts_the_planned_rows_only():
    for st, n in PLANNED.items():
        t = K.table(KP, st)
        planned = [r["name"] for r in t if "expectfault" in r["knobs"] and r["set"] != "control"]
        assert len(planned) == n == limit(st), st
        assert planned[-1] == t[-1]["name"], st


def test_controls_can_fail_and_are_readable():
    for st in PLANNED:
        c = K.controls(KP, st)
        assert c, st
        SK.refuse_unreadable(c, score.producible)
        preds = K.predictions(KP, st)
        assert all(preds.get(n) for n in c), st
    for st in ("f1", "f2"):
        assert all("expectfault" not in r["knobs"] for r in K.table(KP, st) if r["set"] == "control")
    t3 = K.table(KP, "f3")
    assert t3[1]["name"] == "f3-c-b" and t3[1]["set"] == "control"
    assert K.predictions(KP, "f3")["f3-c-b"]["end"] == {"M1": "hang"}


def test_noreset_and_idle():
    sim = f3.simulate("M1")
    for st in PLANNED:
        t = K.table(KP, st)
        assert "noreset" not in t[0]["knobs"]
        for i, r in enumerate(t):
            if "noreset" in r["knobs"]:
                assert st == "f3" and sim[t[i - 1]["name"]] in ("ok", "hang"), r["name"]
            idles = [w for w in r["knobs"] if w.startswith("idle:")]
            assert idles == (["idle:60"] if r["name"] == "f3-idle-b" else []), r["name"]
    # every second job of a pair builds on its first: noreset, the first a reset row
    pairs = [("f3-v1c2-p", "f3-v1c2"), ("f3-v1c5-p", "f3-v1c5"), ("f3-shape-a", "f3-shape-b"),
             ("f3-idle-a", "f3-idle-b"), ("f3-fill-m", "f3-fill-b"), ("f3-rst-m", "f3-rst-b"),
             ("f3-hl-a", "f3-hl-b"), ("f3-c-a", "f3-c-b"), ("f3-fill-a", "f3-fill-m")]
    t = {r["name"]: r for r in K.table(KP, "f3")}
    for a, b in pairs:
        assert "noreset" in t[b]["knobs"] and "noreset" not in t[a]["knobs"] or a == "f3-fill-m"
    assert "noreset" not in t["f3-rst-m"]["knobs"] and "noreset" in t["f3-fill-m"]["knobs"]
    assert "after" in t["f3-hl-a"]["knobs"]
    assert sum("after" in r["knobs"] for r in t.values()) == 1


def test_rows_use_only_the_plans_forms():
    for st in PLANNED:
        for r in K.table(KP, st):
            assert not any(w.startswith("dbg:") for w in r["knobs"])
            for o in ("--kpoke", "--kreg", "--clkgate", "--trc-hazard", "--scratch-pages"):
                assert o not in r["args"], (r["name"], o)
            a = r["args"].split()
            if st == "f1":
                assert r["tool"] == "t10p" and a[:5] == ["probe", "--temps", "32", "--coords", "--pixels"]
            elif st == "f2":
                assert r["tool"] == "t10" and "--sideband" in a
                sb = int(a[a.index("--sideband") + 1], 16)
                assert sb == 0x1200 if r["set"] == "control" else sb in (0xA00, 0xA04, 0xA08)
            else:
                assert r["tool"] == "t10"


def test_predicted_counts():
    """f1: 2 planned rows, 1 predicted fault under H-TWX / H-E566 (0 under H-TWIDX, 2 under
    H-FAULTANY); f2: 3 planned faults; f3: 8 planned rows, 5 predicted hangs under M3 plus the
    control's (6 recovered hangs), 4 plus the control's under M1."""
    p1 = K.predictions(KP, "f1")
    assert [n for n in p1 if p1[n]["end"].get("H-TWX") == "fault"] == ["f1-tw32"]
    assert [n for n in p1 if p1[n]["end"].get("H-FAULTANY") == "fault"] == ["f1-tw32", "f1-small"]
    p2 = K.predictions(KP, "f2")
    assert sum(1 for n in p2 if p2[n]["end"].get("H-E383") == "fault") == 3
    m3 = f3.simulate("M3")
    assert sum(v == "hang" for v in m3.values()) == 6
    assert sum(v == "hang" for v in f3.simulate("M1").values()) == 5
