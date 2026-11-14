# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing18/plan/rank-round18.md sections 2 and 3;
closing18/DECISIONS-R18.md) and the session build rules: s0 is safe (#limit 0, no expectfault);
every flagged stage's #limit counts exactly its expectfault rows that are not controls (E946) and
its last row is one of them; the #limits sum to 15; the planned faults and hangs (rows a frozen
hypothesis says fault or hang) are 7 and 3; every control reads keys its row produces, does not
expectfault and has frozen predictions; every flagged stage is gated and ends the session on its
stop; f2's knob addresses are the ones its s0 references read; h2's noreset rows follow a row of
their own triple; no option outside the kit's and the session's rules."""
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
ORDER = ["s0", "f1", "f2", "f3", "f4", "h1", "h2"]
JOBS = {"s0": 7, "f1": 2, "f2": 4, "f3": 2, "f4": 2, "h1": 1, "h2": 8}
LIMIT = {"s0": 0, "f1": 2, "f2": 4, "f3": 2, "f4": 2, "h1": 1, "h2": 4}
# the frozen hypotheses whose fault or hang rows are the planned ones
FROZEN = {"f1": "H-PAST-FAULT", "f2": ("H-WO-ALL", "H-EDM-READ"), "f3": "H-KIND", "f4": "H-FAULT-ANY",
          "h1": "H-B24-HANG", "h2": "M1-SHAPE"}


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


def test_limits_count_the_expectfault_rows_and_cap_at_15():
    for st in ORDER:
        t = K.table(KP, st)
        assert len(t) == JOBS[st], st
        rows = [r["name"] for r in t if "expectfault" in r["knobs"] and r["set"] != "control"]
        assert len(rows) == LIMIT[st] == limit(st), st
        if rows:
            assert rows[-1] == t[-1]["name"], st
    assert sum(LIMIT.values()) == 15


def test_planned_faults_and_hangs():
    faults = hangs = 0
    for st, models in FROZEN.items():
        models = (models,) if isinstance(models, str) else models
        p = K.predictions(KP, st)
        for n, q in p.items():
            ends = {q["end"][m] for m in models if m in q.get("end", {})}
            assert len(ends) <= 1, (st, n)
            faults += ends == {"fault"}
            hangs += ends == {"hang"}
    assert (faults, hangs) == (7, 3)


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


def test_f1_rows_are_the_zv_form_at_16_pages():
    t = {r["name"]: r for r in K.table(KP, "f1")}
    s0 = {r["name"]: r for r in K.table(KP, "s0")}
    assert t["q299-g3"]["args"] == s0["zv-c-g3"]["args"].replace("--depth-pages 20", "--depth-pages 16")
    assert t["q299-g5"]["args"] == s0["zv-g5-24"]["args"].replace("--depth-pages 24", "--depth-pages 16")
    assert all(r["tool"] == "t10" for r in t.values())


def test_f2_knobs_are_the_addresses_the_references_read():
    p = K.predictions(KP, "s0")
    depth, scratch = p["rf-c-depth"]["depthat"]["H-REF"], p["f1-ref-a"]["scratchat"]["H-REF"]
    t = K.table(KP, "f2")
    s0 = {r["name"]: r for r in K.table(KP, "s0")}
    assert [r["name"] for r in t] == ["q108-edm-load", "q108-edm-tex", "q108-wo-load", "q108-wo-tex"]
    for r in t:
        k = dict(w[4:].split("=") for w in r["knobs"] if w.startswith("dbg:"))
        assert k["vm_pte_flags"] == ("0x10" if "-edm-" in r["name"] else "0x2")
        load = r["name"].endswith("-load")
        assert k["vm_pte_addr"] == (depth if load else scratch)
        assert r["args"] == s0["rf-c-depth" if load else "f1-ref-a"]["args"]
        assert r["tool"] == "t14"
    for name in ("vm_pte_addr", "vm_pte_flags"):
        assert CFG["knobs"][name]["default"] == "0"


def test_h2_triples():
    t = K.table(KP, "h2")
    names = [r["name"] for r in t]
    assert names == ["h2-c-a", "h2-c-b", "h2-a1", "h2-a2", "h2-a3", "h2-b1", "h2-b2", "h2-b3"]
    for r in t:
        first = r["name"].endswith(("-c-a", "1"))
        assert ("noreset" in r["knobs"]) is not first, r["name"]
        assert r["args"].endswith('--vdm 1^=0x00000800 "$S/bins/p1131-blue__0.bin"')
    assert t[1]["set"] == "control" and "expectfault" not in t[1]["knobs"]
    assert [r["name"] for r in t if "expectfault" in r["knobs"]] == ["h2-a2", "h2-a3", "h2-b2", "h2-b3"]
    a = [r["args"] for r in t]
    assert a[0] == a[1] and a[2] == a[3] == a[4] and a[5] == a[6] == a[7]
    assert "--vertices 24" in a[2] and "--temps 8" in a[2] and "--obj2" not in a[2]
    assert "--vertices 48" in a[5] and "--temps 16" in a[5] and "--obj2 24" in a[5] and "--width 128" in a[5]


def test_no_option_outside_the_rules():
    bad = ("--kreg", "--clkgate", "--trc-hazard", "--fault", "--scratch-at", "--refill", "--kpoke-job")
    for st in ORDER:
        for r in K.table(KP, st):
            a = r["args"].split()
            assert not set(a) & set(bad), r["name"]
            if a[0] == "tri":
                assert all(p.split("=")[0] in ("1:rd:13", "1:ta:143") for p in
                           [a[i + 1] for i, x in enumerate(a) if x == "--kpoke-render"]), r["name"]
            assert "idle:" not in " ".join(r["knobs"])
