# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3h/design.md §3, the user's decisions
A-E (a) of 2026-11-23) and the session build rules: every stage flagged, on_stop "end", #limit 0,
emitsb_sbc43s armed with form=sbc43 at pdsat=fw14 and the design's image (mark for w and w2,
landv for v, crumb3 for f), the K7 keys (w, w2: own_gate none and end_draws none; v: begin_draws
none; f: begin_draws fill and on_gate_fail score); one owntask row a stage: job 1 = B11's command
1 (the 0xdeadc0de fill of slots 2-5 and dwords 128-223, 200 ms, ticks, no kick), then v's command
6 on the next tick pass, f's kick-only job (K6: cmd 0, a GETMISCINFO kick, expect notdone, 50 ms)
and command 6 on a kick. The module is r42-kernel's (fork ec6511d5de87, srcversion
079DD0D13F231EEAC52FE0F, running on the laptop): its own_arm takes each arm with the blob's word
and image; the kit at the frozen commit (K6, K7) lints every row and arm."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import make  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
LINUX = os.environ.get("RESGX545_LINUX", "/Volumes/linux/linux-sgx")
FORK = "ec6511d5de87"                   # r42-kernel, the module the laptop runs (no rebuild)
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV = "079DD0D13F231EEAC52FE0F"
STEP = make.STEP
FILL = 0xDEADC0DE
A = "slots=0x1 entry=0 pds={} pdsat=fw14 form={}"
# the design's sessions (§3 and the user's order N1, N2)
W_KEYS = {"own_gate": "none", "end_draws": "none"}
PLAN = {"N1": [("w", A.format("mark", "sbc43"), W_KEYS, ("j1",)),
               ("v", A.format("landv", "sbc43"), {"begin_draws": "none"}, ("j1", "tick"))],
        "N2": [("w2", A.format("mark", "sbc43"), W_KEYS, ("j1",)),
               ("f", A.format("crumb3", "sbc43"), {"begin_draws": "fill", "on_gate_fail": "score"},
                ("j1", "kickonly", "kick"))]}[STEP]
BLOB = "emitsb_sbc43s"
J1 = {"cmd": 1, "params": {"72": [FILL] * 16, "128": [FILL] * 96}, "timeout_ms": 200,
      "ticks": True}
J6 = {"cmd": 6, "params": {"224": [FILL] * 32}, "timeout_ms": 200, "ticks": True,
      "slots": list(range(40, 48))}
JOBS = {"j1": J1, "kick": dict(J6, kick="miscinfo"), "tick": J6,
        "kickonly": {"cmd": 0, "kick": "miscinfo", "expect": "notdone", "timeout_ms": 50}}


def git_show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True,
                       text=True)
    assert r.returncode == 0, f"{path} at {rev} in {repo}: {r.stderr}"
    return r.stdout


def test_env():
    k = STEP[1]
    assert CFG["name"] == f"r43-n3h-n{k}" and CFG["prefix"] == f"r43h{k}"
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["srcversion"] == SRCV          # the r42-kernel module the laptop runs
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "1f49335c",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r43-n3h (K6, K7), not main
    assert CFG["freeze"]["data"].startswith("fadfa30ad")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == [p[0] for p in PLAN]
    for name, arm, keys, jobs in PLAN:
        d = st[name]
        assert d["class"] == "flagged" and d["on_stop"] == "end"
        assert d["owntask"] == {"blob": BLOB, "arm": arm}
        assert {k: d[k] for k in ("own_gate", "begin_draws", "end_draws", "on_gate_fail",
                                  "gate_order") if k in d} == keys
        assert "#limit 0" in open(os.path.join(KP, "tables", name + ".txt")).read().splitlines()
    # K7: the first stage keeps its begin draws; the stage without them follows the planting one
    assert "begin_draws" not in st[PLAN[0][0]]


def test_the_one_row_a_stage():
    for name, arm, keys, jobs in PLAN:
        t = K.table(KP, name)
        assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in t] == [
            (f"{name}1-a", "fit", "owntask", ["-"], "flagged")]
        a = json.loads(t[0]["args"])
        want = [JOBS[k] for k in jobs]
        assert a == (want[0] if len(want) == 1 else want)


def test_each_blob_is_the_map_s_at_the_frozen_commit():
    m = json.loads(git_show(MAIN, CFG["freeze"]["resgx545"], "asm/fwtask/fwtask.map"))
    data = open(os.path.join(KP, f"owntask/{BLOB}.blob"), "rb").read()
    assert hashlib.sha256(data).hexdigest() == m[BLOB]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == [f"{BLOB}.blob"]


def test_the_frozen_kit_takes_the_arms_the_rows_and_the_k7_keys():
    import session as S
    for name, arm, keys, jobs in PLAN:
        assert S.owntask_arm_problem(arm) is None
        job, bad = S.owntask_jobs(K.table(KP, name)[0]["args"], CFG["job_timeout"])
        assert not bad and job
    run = open(os.path.join(KP, "kit/run_stage.sh")).read()
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert all(re.fullmatch(sh, p[1]) for p in PLAN)
    assert "stage_health end" in run and "owntask-nogate" in run
    assert S.OWNTASK_DRAWS == ("fill,tri", "fill", "tri", "none")


def test_the_kernel_takes_each_arm_with_its_blob():
    """r42-kernel's own_arm (fork ec6511d5de87): form=<name> arms a blob whose emit word is
    sgx_own_emit_forms[]'s; pds=crumb3, mark and landv are its images, 3 rows each."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, arm, keys, jobs in PLAN:
        form = arm.split("form=")[1]
        assert form == make.FORM
        sb = make.SIDEBAND
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        assert f'{{ "{form}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    for img, n in (("CRUMB3", 19), ("MARK", 21), ("LANDV", 18)):
        assert f"#define SGX_OWN_PDS_{img}_CTL\t0x01800100" in pds
        assert f"#define SGX_OWN_PDS_{img}_WORDS\t{n}" in pds
        assert f"#define SGX_OWN_PDS_{img}_FILLV\t1" in pds
    c = git_show(LINUX, FORK, f"{SGXFIVE}/sgxfive_owntask.c")
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in c
    assert '[SGX_OWN_IMG_MARK] = { "mark"' in c and '[SGX_OWN_IMG_LANDV] = { "landv"' in c


def test_the_predictions_are_the_design_s_tables():
    want = {"W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
            "V": {"V-KEEP": "held", "V-EVT": "failed", "V-V1": "failed", "V-OTHER": "printed",
                  "V-V": "held", "V-EARLY1": "held", "V-EARLY13": "failed",
                  "V-EARLY0": "failed", "V-SERVE": "failed"},
            "F": {"F-FILL4": "held", "F-KEEP": "failed", "F-OTHER": "printed",
                  "K-QUIET": "held", "K-KICK": "held", "K-KICKOK": "failed", "K-REPLY": "held",
                  "K-STALL": "held", "K-SERVE": "failed", "F-GATE": "held if reached"}}
    for st in make.STAGES[STEP]:
        src = open(os.path.join(KP, "predictions", st[0] + ".tsv")).read().splitlines()[1:]
        got = {}
        for ln in src:
            f = ln.split("\t")
            if f[3] != "CTL":
                got[f[3]] = re.search(r"\[predicted: ([^\]]+)\]", f[5]).group(1)
        assert got == want[st[1]], st
        p = K.predictions(KP, st[0])[f"{st[0]}1-a"]
        ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
        common = {"res:0x0": "0x4e574f53", "j1rec:slot0": "0x5a5a3301", "j1rec:slot1": "@runid1",
                  "j1rec:cmd": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0",
                  "j1": "DONE"}
        assert {q: v for q, v in ctl.items() if q in common} == common
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
    if STEP == "N1":
        p = K.predictions(KP, "w")["w1-a"]
        assert p["postsa1"]["W-SA1"] == "0x005d1000" and p["postpa1"]["W-SA13"] == "0x005d3000"
        p = K.predictions(KP, "v")["v1-a"]
        assert p["j2fault"]["V-EARLY1"] == "@post1" and p["j2fault"]["V-EARLY0"] == \
            "cid15 page 0x00000000"
    if STEP == "N2":
        p = K.predictions(KP, "f")["f1-a"]
        assert p["sa1kind"]["F-FILL4"] == "EVT4" and p["j2kick"]["K-KICK"] == "@post13"
