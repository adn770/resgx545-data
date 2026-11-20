# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3e/design.md §3.2-§3.3, the user's
decisions A-E of 2026-11-19) and the session build rules: stage own flagged, on_stop "end", the
owntask armed as the row says (`slots=0x1 entry=0 pds=crumb3|land pdsat=fw14 form=<form>`, blob
emitsb14d or emitsb_<form>), #limit 0, one owntask row c1-a: command 1, the 0xdeadc0de fill of
slots 2-5 (sixteen dwords from 72) and of dwords 128-223, timeout 200 ms, ticks, no kick; stage
post flagged after it, the health pair's bare argv on t30 as two controls. The module is the
r40-kernel one (fork 423b436e7f80), not built yet: srcversion is the placeholder until the lead
writes the built module's; its own_arm takes the arm with the blob (its generated headers: the
form's word, the land image)."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import make  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
LINUX = os.environ.get("RESGX545_LINUX", "/Volumes/linux/linux-sgx")
FORK = "423b436e7f80"                   # r40-kernel's tip (red r40-red 1be09fd22de0)
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
TO, TP = K.table(KP, "own"), K.table(KP, "post")
STEP = score.STEP
NAME, PREFIX = f"r40-n3e-{STEP.lower()}", f"r40{STEP.lower()}"
FORMS = {"B0": "fw14", "L": "fw14", "B1": "sb003", "B2": "sb841", "B3": "sb842", "B4": "sb840",
         "B5": "sb043", "B6": "sb803", "B7": "sb001", "B8": "sb002", "B9": "sb040",
         "B10": "sb800", "B11": "sbc43"}
FORM = FORMS[STEP]
ARM = f"slots=0x1 entry=0 pds={'land' if STEP == 'L' else 'crumb3'} pdsat=fw14 form={FORM}"
BLOB = "emitsb14d" if FORM == "fw14" else f"emitsb_{FORM}"
SRCV = "83FBFD860D4E0D4CE691F48"     # the r40-kernel module (cachix, 2026-11-19)


def fork(path):
    r = subprocess.run(["git", "-C", LINUX, "show", f"{FORK}:{SGXFIVE}/{path}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"fork {FORK} in {LINUX} (RESGX545_LINUX): {r.stderr}"
    return r.stdout


def test_env():
    assert CFG["name"] == NAME and CFG["prefix"] == PREFIX
    assert CFG["srcversion"] == SRCV
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["tools"]["t30"]["source"].startswith("42c4de7855d6")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "555d8eb",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r40-n3e (r40-d0 merged), not main
    assert CFG["freeze"]["data"].startswith("9fce0b993")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == ["own", "post"]
    assert st["own"]["class"] == "flagged" and st["own"]["on_stop"] == "end"
    assert st["own"]["owntask"] == {"blob": BLOB, "arm": ARM}
    assert make.ARM == ARM and make.BLOB == BLOB
    assert st["post"]["class"] == "flagged" and "owntask" not in st["post"]
    for s in ("own", "post"):
        assert "#limit 0" in open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()


def test_the_one_own_row():
    assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in TO] == [
        ("c1-a", "fit", "owntask", ["-"], "flagged")]
    j = json.loads(TO[0]["args"])
    assert j == {"cmd": 1, "params": {"72": [0xDEADC0DE] * 16, "128": [0xDEADC0DE] * 96},
                 "timeout_ms": 200, "ticks": True}


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


def test_the_frozen_kit_takes_the_arm():
    """The kit at the frozen commit lints this arm; the image it names is one of the generator's
    with #14's three rows."""
    src = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                          ":tools/closing/kit/session.py"], capture_output=True, check=True,
                         text=True).stdout
    ns = {"re": re}
    exec(src[src.index("OWNTASK_FORMS = ("):src.index("OWNTASK_TRC_MAX")], ns)
    assert FORM in ns["OWNTASK_FORMS"]
    assert ns["OWNTASK_ARM"].fullmatch(ARM), ns["OWNTASK_ARM"].pattern
    gv = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                         ":tools/fwtask/gen_verify.py"], capture_output=True, check=True,
                        text=True).stdout
    assert ('"land": 3' if STEP == "L" else '"crumb3": 3') in gv
    run = subprocess.run(["git", "-C", MAIN, "show", CFG["freeze"]["resgx545"] +
                          ":tools/closing/kit/run_stage.sh"], capture_output=True, check=True,
                         text=True).stdout
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert re.fullmatch(sh, ARM), sh


def test_the_predictions_are_the_design_s_table():
    p = K.predictions(KP, "own")["c1-a"]
    s = STEP
    if s == "L":
        lands = [f"L-{k}" for k in ("SA", "SHIFT", "PA", "ONE", "NONE")]
        assert p["T"] == {m: "running" for m in ["L-NEVER", "L-E1"] + lands}
        assert p["res:0x54"] == dict({"L-NEVER": "fill", "L-E1": "0x5a5a3304"},
                                     **{m: "0x5a5a3304" for m in lands})
        assert p["lland"] == {m: m.split("-")[1] for m in lands}
        for m in lands:
            assert p["res:0x50"][m] == "0x5a5a3302" and p["res:0x2"][m] == "0x2"
        src = open(os.path.join(KP, "predictions/own.tsv")).read().splitlines()
        assert all("[predicted: held]" in ln for ln in src if "\tL-SA\t" in ln)
        assert all("[predicted: failed]" in ln for ln in src
                   if any(f"\t{m}\t" in ln for m in lands[1:]))
    else:
        assert p["T"] == {f"{s}-NEVER": "running", f"{s}-T1": "0x00000000",
                          f"{s}-T2": "0x00000200", f"{s}-T3": "0x005a3305",
                          f"{s}-E1": "0x005a3305", f"{s}-DONE": "0x005a3305"}
        assert p["res:0x54"] == {f"{s}-NEVER": "fill", f"{s}-T1": "fill", f"{s}-T2": "fill",
                                 f"{s}-T3": "fill", f"{s}-E1": "0x5a5a3304",
                                 f"{s}-DONE": "0x5a5a3304"}
        assert p["res:0x50"][f"{s}-DONE"] == "0x5a5a3302" and p["res:0x2"][f"{s}-DONE"] == "0x2"
        assert "land" not in p and "lland" not in p
        # the design's H-DM and H-ALL columns (n3e §3.2-§3.3), frozen in the outcome texts
        want = {"B0": ("RUN", "RUN"), "B1": ("RUN", "NEVER"), "B2": ("NEVER", "NEVER"),
                "B3": ("NEVER", "NEVER"), "B4": ("NEVER", "NEVER"), "B5": ("RUN", "NEVER"),
                "B6": ("RUN", "NEVER"), "B7": ("NEVER", "NEVER"), "B8": ("NEVER", "NEVER"),
                "B9": ("NEVER", "NEVER"), "B10": ("NEVER", "NEVER"), "B11": ("RUN", "-")}[s]
        assert score.ROWS[s][2:] == want
        src = open(os.path.join(KP, "predictions/own.tsv")).read()
        assert f"H-DM predicts {want[0]}" in src
        assert (f"H-ALL predicts {want[1]}" if want[1] != "-" else "H-ALL: no prediction") in src
    assert "ticks_kick" not in p and "ticks" not in p
    ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
    want = {"res:0x0": "0x4e574f53", "res:0x44": "0x5a5a3301", "res:0x45": "@runid",
            "res:0x1": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0"}
    if s == "L":
        want.update({"survey:p0": "true", "survey:p1": "true"})
    assert ctl == want


def test_the_kernel_takes_the_arm_with_the_blob():
    """r40-kernel's own_arm (fork 423b436e7f80): form=<name> arms a blob whose emit word is the one
    sgx_own_emit_forms[] gives that name; pds=land is its land image, U0 its only fill."""
    regs = fork("sgx_own_regs.h")
    sb = make.SIDEBAND
    w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
    assert f'{{ "{FORM}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    assert f"0x{w:016x}ULL, SGX_OWN_EMITPDS }},\t/* emitpds-{FORM} */" in regs
    pds = fork("sgx_own_pds.h")
    if STEP == "L":
        assert "#define SGX_OWN_PDS_LAND_FILLV\t0" in pds
        assert "#define SGX_OWN_PDS_LAND_CTL\t0x01800100" in pds
        body = pds[pds.index("sgx_own_pds_land["):]
        words = [int(x, 16) for x in re.findall(r"^\t(0x[0-9a-f]{8}),", body[:body.index("};")],
                                               re.M)]
        assert words == [0, 0, 0, 0x1800, 0x5A5A3A18, 0x5A5A3A1A, 0x1A00, 0, 0, 0, 0, 0,
                         0x07040606, 0x07042CA6, 0x07000305, 0xAF000000]
    else:
        assert "#define SGX_OWN_PDS_CRUMB3_CTL\t0x01800100" in pds
    c = fork("sgxfive_owntask.c")
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in c
