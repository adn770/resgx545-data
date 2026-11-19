# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3d/design.md §3.1 and §3.2, §4 items
1-7, the lead's brief for round 39) and the session build rules: stage own flagged, on_stop "end",
the owntask armed as the STEP says (K: emitsk, `pds=crumb3 pdsat=fw14`, R4's; Z: emitsk14, the
same with `pds2=req form=fw14`), #limit 0, one owntask row c1-a: command 1, the 0xdeadc0de fill of
slots 2-5 (sixteen dwords from 72), timeout 200 ms, ticks, the miscinfo kick; stage post flagged
after it, the health pair's bare argv on t30 as two controls."""
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
NAME, PREFIX = {"K": ("r39-n3d-k", "r39k"), "Z": ("r39-n3d-z", "r39z")}[STEP]
ARM = {"K": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14",
       "Z": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 pds2=req form=fw14"}[STEP]
BLOB = {"K": "emitsk", "Z": "emitsk14"}[STEP]
# K runs on the module the laptop has (r38-kernel); Z on the r39-kernel module, not built yet
SRCV = {"K": "88ADCEB5AD9F055D077A99C"}.get(STEP)


def test_env():
    assert CFG["name"] == NAME and CFG["prefix"] == PREFIX
    if SRCV:
        assert CFG["srcversion"] == SRCV
    else:       # a placeholder that never matches until the lead writes the built srcversion
        assert CFG["srcversion"].startswith("UNBUILT-r39-kernel-")
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    import subprocess as sp
    head = sp.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "53db9b3",
                   CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # on round 39's branch, from main 53db9b3
    assert CFG["freeze"]["data"].startswith("9fce0b993")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == ["own", "post"]
    assert st["own"]["class"] == "flagged" and st["own"]["on_stop"] == "end"
    assert st["own"]["owntask"] == {"blob": BLOB, "arm": ARM}
    assert st["post"]["class"] == "flagged" and "owntask" not in st["post"]
    for s in ("own", "post"):
        assert "#limit 0" in open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()


def test_the_one_own_row():
    assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in TO] == [
        ("c1-a", "fit", "owntask", ["-"], "flagged")]
    j = json.loads(TO[0]["args"])
    assert j == {"cmd": 1, "params": {"72": [0xDEADC0DE] * 16}, "timeout_ms": 200, "ticks": True,
                 "kick": "miscinfo"}


def test_post_rows():
    assert [(r["name"], r["set"], r["tool"], r["args"], r["reads"]) for r in TP] == [
        ("p1-tri", "control", "t30", "tri", ("diff",)),
        ("p2-fill", "control", "t30", "fill", ("diff",))]


def test_the_blob_is_the_maps_at_the_frozen_commit():
    m = json.loads(subprocess.run(["git", "-C", MAIN, "show",
                                   CFG["freeze"]["resgx545"] + ":asm/fwtask/fwtask.map"],
                                  capture_output=True, check=True).stdout)
    b = open(os.path.join(KP, f"owntask/{BLOB}.blob"), "rb").read()
    assert hashlib.sha256(b).hexdigest() == m[BLOB]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == [f"{BLOB}.blob"]


def test_the_frozen_kit_takes_the_arm_and_the_kick():
    """The kit at the frozen commit lints this arm and takes the row's kick; the image the arm
    names is one of sgx_own_pds.h's with #14's control word."""
    import re
    src = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                          ":tools/closing/kit/session.py"], capture_output=True, check=True,
                         text=True).stdout
    m = re.search(r'OWNTASK_ARM = re.compile\((.*?)\)\n', src, re.S)
    pat = "".join(eval(x) for x in re.findall(r'r"[^"]*"', m.group(1)))
    assert re.fullmatch(pat, ARM), pat
    assert 'OWNTASK_KICKS = ("miscinfo",)' in src
    gv = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                         ":tools/fwtask/gen_verify.py"], capture_output=True, check=True,
                        text=True).stdout
    assert '"crumb3": 3' in gv
    run = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                          ":tools/fwtask/fwtask_run.py"], capture_output=True, check=True,
                         text=True).stdout
    assert 'KICKS = ("miscinfo",)' in run and "ticks_from_kick" in run


def test_the_predictions_are_the_design_s_table():
    p = K.predictions(KP, "own")["c1-a"]
    s = STEP
    assert p["T"] == {f"{s}-NEVER": "running", f"{s}-T1": "0x00000000",
                      f"{s}-T2": "0x00000200", f"{s}-T3": "0x005a3305",
                      f"{s}-E1": "0x005a3305", f"{s}-DONE": "0x005a3305"}
    assert p["res:0x54"] == {f"{s}-NEVER": "fill", f"{s}-T1": "fill", f"{s}-T2": "fill",
                             f"{s}-T3": "fill", f"{s}-E1": "0x5a5a3304",
                             f"{s}-DONE": "0x5a5a3304"}
    assert p["res:0x50"][f"{s}-DONE"] == "0x5a5a3302"
    assert p["res:0x2"][f"{s}-DONE"] == "0x2"
    assert p["ticks_kick"] == {f"{s}-NEVER": "8-11"} and "ticks" not in p
    ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
    assert ctl == {"res:0x0": "0x4e574f53", "k0:cmd": "0x1", "k0:slot1": "fill",
                   "res:0x44": "0x5a5a3301", "res:0x45": "@runid", "res:0x1": "0x0",
                   "snap0:0x0acc": "running", "snap9:0x0c08": "0x0"}
