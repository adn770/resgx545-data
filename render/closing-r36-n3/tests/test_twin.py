# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/kernel33/design.md §3, the N3 rows of
closing29/plan/rank-round34.md, the lead's brief for r36-n3) and the session build rules: stage own
flagged, on_stop "end", owntask emitsa armed `slots=0x1 entry=0`, #limit 0, 10 owntask jobs (2
exploration, 8 held out), each one command 1 with the A or B fill of slots 2-4 and nothing else;
stage post flagged after it, the health pair's bare argv on t30 as two controls. The same-value
variant only: no row passes a value the image writes (the kernel builds V0, V2)."""
import hashlib
import json
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
TO, TP = K.table(KP, "own"), K.table(KP, "post")


def test_env():
    assert CFG["srcversion"] == "C01FB3203FDA4FEF01E4891" and CFG["prefix"] == "r36n"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    assert CFG["freeze"]["resgx545"].startswith("b9098a4")
    assert CFG["freeze"]["data"].startswith("6b2938440")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == ["own", "post"]
    assert st["own"]["class"] == "flagged" and st["own"]["on_stop"] == "end"
    assert st["own"]["owntask"] == {"blob": "emitsa", "arm": "slots=0x1 entry=0"}
    assert st["post"]["class"] == "flagged" and "owntask" not in st["post"]
    for s in ("own", "post"):
        assert "#limit 0" in open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()


def test_own_rows():
    assert [r["name"] for r in TO] == ["e1-a", "e2-b"] + [f"h{i}-{'ab'[(i - 1) % 2]}"
                                                          for i in range(1, 9)]
    assert [r["set"] for r in TO] == ["fit"] * 2 + ["heldout"] * 8
    for r in TO:
        assert r["tool"] == "owntask" and r["knobs"] == ["-"] and r["risk"] == "flagged"
        j = json.loads(r["args"])
        fill = {"a": 0xDEADC0DE, "b": 0x0BADF00D}[r["name"][-1]]
        assert j == {"cmd": 1, "params": {"72": [fill] * 12}, "timeout_ms": 200}, j


def test_post_rows():
    assert [(r["name"], r["set"], r["tool"], r["args"], r["reads"]) for r in TP] == [
        ("p1-tri", "control", "t30", "tri", ("diff",)),
        ("p2-fill", "control", "t30", "fill", ("diff",))]


def test_the_blob_is_the_maps_at_the_frozen_commit():
    m = json.loads(subprocess.run(["git", "-C", MAIN, "show",
                                   CFG["freeze"]["resgx545"] + ":asm/fwtask/fwtask.map"],
                                  capture_output=True, check=True).stdout)
    b = open(os.path.join(KP, "owntask/emitsa.blob"), "rb").read()
    assert hashlib.sha256(b).hexdigest() == m["emitsa"]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == ["emitsa.blob"]


def test_every_row_has_predictions_and_the_held_out_split_separates_the_hypotheses():
    p = K.predictions(KP, "own")
    for r in TO:
        q = p[r["name"]]
        assert q["res:0x48"] == {"H-PA": "@V0", "H-SA": "!@V0"}
        assert q["res:0x4a"] == {"H-PA": "@V2", "H-SA": "!@V2"}
        assert q["res:0x50"] == {"H-NONE": "!0x5a5a3302", "CTL": "0x5a5a3302"}
        assert {k for k, mv in q.items() if "CTL" in mv} >= {
            "res:0x44", "res:0x45", "res:0x50", "res:0x51", "res:0x4c", "res:0x4d",
            "res:0x4e", "res:0x4f", "res:0x49", "res:0x4b", "res:0x1", "res:0x2", "res:0x5"}
    lines = open(os.path.join(KP, "predictions/own.tsv")).read().splitlines()[1:]
    sets = {r["name"]: r["set"] for r in TO}
    assert all(ln.split("\t")[4] == sets[ln.split("\t")[0]] for ln in lines)
