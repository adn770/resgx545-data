# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3b/design.md §1.4 and §4, the lead's
brief for round 37) and the session build rules: stage own flagged, on_stop "end", owntask emitsb
armed as the STEP says (A: `slots=0x1 entry=0`, the v1 image; B: `... pds=crumb`), #limit 0, one
owntask row c1-a: command 1, the 0xdeadc0de fill of slots 2-5 (sixteen dwords from 72), timeout
200 ms, ticks; stage post flagged after it, the health pair's bare argv on t30 as two controls."""
import hashlib
import json
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
TO, TP = K.table(KP, "own"), K.table(KP, "post")
STEP = score.STEP
NAME, PREFIX = {"A": ("r37-n3b-a", "r37a"), "B": ("r37-n3b-b", "r37b")}[STEP]
ARM = {"A": "slots=0x1 entry=0", "B": "slots=0x1 entry=0 pds=crumb"}[STEP]


def test_env():
    assert CFG["name"] == NAME and CFG["prefix"] == PREFIX
    # the r37-kernel module is not built: a placeholder that never matches until the lead writes
    # the built module's srcversion and freezes again
    assert CFG["srcversion"] == "UNBUILT-r37-kernel-4f35fc20ffa9"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    assert CFG["freeze"]["resgx545"].startswith("7925c98")
    assert CFG["freeze"]["data"].startswith("fb461acff")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == ["own", "post"]
    assert st["own"]["class"] == "flagged" and st["own"]["on_stop"] == "end"
    assert st["own"]["owntask"] == {"blob": "emitsb", "arm": ARM}
    assert st["post"]["class"] == "flagged" and "owntask" not in st["post"]
    for s in ("own", "post"):
        assert "#limit 0" in open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()


def test_the_one_own_row():
    assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in TO] == [
        ("c1-a", "fit", "owntask", ["-"], "flagged")]
    j = json.loads(TO[0]["args"])
    assert j == {"cmd": 1, "params": {"72": [0xDEADC0DE] * 16}, "timeout_ms": 200, "ticks": True}


def test_post_rows():
    assert [(r["name"], r["set"], r["tool"], r["args"], r["reads"]) for r in TP] == [
        ("p1-tri", "control", "t30", "tri", ("diff",)),
        ("p2-fill", "control", "t30", "fill", ("diff",))]


def test_the_blob_is_the_maps_at_the_frozen_commit():
    m = json.loads(subprocess.run(["git", "-C", MAIN, "show",
                                   CFG["freeze"]["resgx545"] + ":asm/fwtask/fwtask.map"],
                                  capture_output=True, check=True).stdout)
    b = open(os.path.join(KP, "owntask/emitsb.blob"), "rb").read()
    assert hashlib.sha256(b).hexdigest() == m["emitsb"]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == ["emitsb.blob"]


def test_the_predictions_are_the_design_s_table():
    p = K.predictions(KP, "own")["c1-a"]
    if STEP == "A":
        assert p["res:0x46"] == {"A-ISSUER": "fill", "A-PAST": "0x5a5a3303",
                                 "A-E1": "0x5a5a3303", "A-DONE": "0x5a5a3303"}
        assert p["res:0x54"] == {"A-ISSUER": "fill", "A-PAST": "fill", "A-E1": "0x5a5a3304",
                                 "A-DONE": "0x5a5a3304"}
        assert p["ticks"] == {"A-ISSUER": "0-2", "A-PAST": "any", "A-E1": "any",
                              "A-DONE": ">=25"}
        assert "T" not in p
    else:
        assert p["T"] == {"B-1": "running", "B-1p": "0x00000000", "B-2a": "0x00000200",
                          "B-2b": "0x005a3305", "B-3": "0x005a3305", "B-NONE": "0x005a3305"}
        assert p["res:0x54"] == {"B-1": "fill", "B-1p": "fill", "B-2a": "fill", "B-2b": "fill",
                                 "B-3": "0x5a5a3304", "B-NONE": "0x5a5a3304"}
        assert "ticks" not in p
    assert p["res:0x2"][f"{STEP}-DONE" if STEP == "A" else "B-NONE"] == "0x2"
    ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
    assert ctl == {"res:0x0": "0x4e574f53", "res:0x44": "0x5a5a3301", "res:0x45": "@runid",
                   "res:0x1": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0"}
