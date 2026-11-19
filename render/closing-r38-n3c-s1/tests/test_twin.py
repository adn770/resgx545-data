# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3c/design.md §2.1, §2.3 and §4 items
1 and 4; the lead's brief for round 38, session S1) and the session build rules: stage own
flagged, on_stop "end", owntask emitsn armed `slots=0x1 entry=0` (no pds= word), #limit 0, one
owntask row n0 (r37 A's job: command 1, the 0xdeadc0de fill of slots 2-5, timeout 200 ms, ticks);
stage tim flagged after it, one row th: t30's probe of the recorded program and harness (--temps
32 --pds 36 --use) under regtimeline on 0x0acc alone (E1133's t1d shape at TOTAL 0.06); stage post
flagged last, the health pair's bare argv on t30 as two controls."""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
TO, TT, TP = K.table(KP, "own"), K.table(KP, "tim"), K.table(KP, "post")


def test_env():
    assert CFG["name"] == "r38-n3c-s1" and CFG["prefix"] == "r38s"
    assert CFG["srcversion"] == "77917296568EB311B89B0DA"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30", "rt"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    assert CFG["tools"]["rt"]["sha256"].startswith("079f63590ce8") and CFG["tools"]["rt"]["wraps"]
    assert CFG["freeze"]["resgx545"].startswith("2ce7fc7")
    assert CFG["freeze"]["data"].startswith("31ec9b2f2")
    assert not CFG["knobs"] and not CFG["kregs"]
    assert "--pds" not in CFG["forbid_options"] and "--use" not in CFG["forbid_options"]
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == ["own", "tim", "post"]
    assert st["own"]["class"] == "flagged" and st["own"]["on_stop"] == "end"
    assert st["own"]["owntask"] == {"blob": "emitsn", "arm": "slots=0x1 entry=0"}
    for s in ("tim", "post"):
        assert st[s]["class"] == "flagged" and "owntask" not in st[s] and "on_stop" not in st[s]
    for s in st:
        assert "#limit 0" in open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()


def test_the_one_own_row_is_r37_a_s_job():
    assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in TO] == [
        ("n0", "fit", "owntask", ["-"], "flagged")]
    j = json.loads(TO[0]["args"])
    assert j == {"cmd": 1, "params": {"72": [0xDEADC0DE] * 16}, "timeout_ms": 200, "ticks": True}


def test_the_one_tim_row():
    assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in TT] == [
        ("th", "held", "rt", ["-"], "flagged")]
    a = shlex.split(TT[0]["args"])
    assert a[:4] == ["0.06", "0.005", "0x0acc", "--"]
    assert a[4] == "$HOME/sgxfive-test-t30"
    assert a[5:] == ["probe", "--temps", "32", "--pds", "36", "--use", "$S/bins/sa_dump.bin",
                     "$S/bins/pds-timer-tim-host__0.bin"]


def test_post_rows():
    assert [(r["name"], r["set"], r["tool"], r["args"], r["reads"]) for r in TP] == [
        ("p1-tri", "control", "t30", "tri", ("diff",)),
        ("p2-fill", "control", "t30", "fill", ("diff",))]


def test_the_blob_is_the_maps_at_the_frozen_commit():
    m = json.loads(subprocess.run(["git", "-C", MAIN, "show",
                                   CFG["freeze"]["resgx545"] + ":asm/fwtask/fwtask.map"],
                                  capture_output=True, check=True).stdout)
    b = open(os.path.join(KP, "owntask/emitsn.blob"), "rb").read()
    assert hashlib.sha256(b).hexdigest() == m["emitsn"]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == ["emitsn.blob"]


def test_the_predictions_are_the_design_s_tables():
    p = K.predictions(KP, "own")["n0"]
    assert {q: mv for q, mv in p.items() if "CTL" not in mv} == {
        "res:0x46": {"N0-OK": "0x5a5a3303"}, "res:0x50": {"N0-OK": "0x5a5a3302"},
        "res:0x51": {"N0-OK": "@runid"}, "res:0x2": {"N0-OK": "0x2"},
        "ticks": {"N0-OK": ">=25"}, "gate": {"N0-OK": "ok"}, "end": {"N0-STOP": "<25|nodone"}}
    ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
    assert ctl == {"res:0x0": "0x4e574f53", "res:0x44": "0x5a5a3301", "res:0x45": "@runid",
                   "res:0x1": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0"}
    t = K.predictions(KP, "tim")["th"]
    assert t == {"tl": {"V0-HOLDS": "0x00abcde0", "V0-NOT": "running"},
                 "snap9:0x0acc": {"V0-HOLDS": "0x00abcde0", "V0-NOT": "running"},
                 "scratch": {"V0-HOLDS": "0x00abcde0", "V0-NOT": "0x00abcde0"},
                 "ivl": {"CTL": "2500..5000"}, "pre": {"CTL": "running"}}
