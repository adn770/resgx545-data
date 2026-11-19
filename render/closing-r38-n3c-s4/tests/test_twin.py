# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3c/design.md §2.2 and §4, the lead's
brief for round 38's rebuild rows) and the session build rules: stage own flagged, on_stop "end",
owntask emitsb armed as the STEP says (M: `pds=crumb3 pdsat=fw14`, H: `pds=halt`, P: `pds=crumb
pdsat=fw14`, W: `pds=crumb3`), #limit 0, one owntask row c1-a: command 1, the 0xdeadc0de fill of
slots 2-5 (sixteen dwords from 72), timeout 200 ms, ticks; stage post flagged after it, the health
pair's bare argv on t30 as two controls."""
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
NAME, PREFIX = {"M": ("r38-n3c-s3", "r38c"), "H": ("r38-n3c-s4", "r38d"),
                "P": ("r38-n3c-s5", "r38e"), "W": ("r38-n3c-s6", "r38f")}[STEP]
ARM = {"M": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14", "H": "slots=0x1 entry=0 pds=halt",
       "P": "slots=0x1 entry=0 pds=crumb pdsat=fw14", "W": "slots=0x1 entry=0 pds=crumb3"}[STEP]


def test_env():
    assert CFG["name"] == NAME and CFG["prefix"] == PREFIX
    # the r38-kernel module is not built: a placeholder that never matches until the lead writes
    # the built module's srcversion and freezes again
    assert CFG["srcversion"] == "UNBUILT-r38-kernel-e1cf9d2b43ab"
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    assert CFG["freeze"]["resgx545"].startswith("94a7de5")
    assert CFG["freeze"]["data"].startswith("5fa307500")
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


def test_the_frozen_kit_takes_the_arm_and_the_kernel_s_image_is_the_step_s():
    """The kit at the frozen commit lints this arm (r38's words), and the image the arm names is
    one of sgx_own_pds.h's at the fork pin of that commit, with the design's control word."""
    src = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                          ":tools/closing/kit/session.py"], capture_output=True, check=True,
                         text=True).stdout
    assert "pds=(crumb|halt|crumb3))?(?: pdsat=(fw14))?" in src
    gv = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                         ":tools/fwtask/gen_verify.py"], capture_output=True, check=True,
                        text=True).stdout
    assert '"crumb3": 3' in gv and '"halt": 2' in gv


def test_the_predictions_are_the_design_s_table():
    p = K.predictions(KP, "own")["c1-a"]
    if STEP == "H":
        assert p["alive"] == {"H-STOP": "false", "H-ALIVE": "true"}
        assert p["ticks"] == {"H-STOP": "9-11", "H-ALIVE": ">=150"}
        assert "T" not in p
    else:
        s = STEP
        assert p["T"] == {f"{s}-NEVER": "running", f"{s}-T1": "0x00000000",
                          f"{s}-T2": "0x00000200", f"{s}-T3": "0x005a3305",
                          f"{s}-E1": "0x005a3305", f"{s}-DONE": "0x005a3305"}
        assert p["res:0x54"] == {f"{s}-NEVER": "fill", f"{s}-T1": "fill", f"{s}-T2": "fill",
                                 f"{s}-T3": "fill", f"{s}-E1": "0x5a5a3304",
                                 f"{s}-DONE": "0x5a5a3304"}
        assert p["res:0x50"][f"{s}-DONE"] == "0x5a5a3302"
        assert p["res:0x2"][f"{s}-DONE"] == "0x2"
        assert p["ticks"] == {f"{s}-NEVER": "9-11"}
    ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
    assert ctl == {"res:0x0": "0x4e574f53", "res:0x44": "0x5a5a3301", "res:0x45": "@runid",
                   "res:0x1": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0"}
