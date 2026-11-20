# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3f/design.md §3, the user's decisions
A-F (a) of 2026-11-20) and the session build rules: every stage flagged, on_stop "end", #limit 0,
the owntask armed as the design says (crumb3 or land at pdsat=fw14, the form's after-read blob),
the last stage's gate failure its planned, scored end (on_gate_fail "score"; stage c none), row T's
gate the triangle first; one owntask row a stage: job 1 = B11's command 1 (the 0xdeadc0de fill of
slots 2-5 and dwords 128-223, 200 ms, ticks, no kick), then command 6 (dwords 224-255 filled and
read as slots 40-47; on a GETMISCINFO kick in C, X, Y; on the next tick pass and after 2000 ms in
LC). The module is the installed r40-kernel one (srcversion 83FBFD860D4E0D4CE691F48, fork
423b436e7f80): its own_arm takes each arm with its blob's word; the kit at the frozen commit lints
every row and arm."""
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
FORK = "423b436e7f80"                   # r40-kernel, the installed module's fork commit
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV = "83FBFD860D4E0D4CE691F48"
STEP = make.STEP
FILL = 0xDEADC0DE
# the design's sessions (§3.6 and the user's order H1, H2, H3, H4)
PLAN = {"H1": [("c", "emitsb14s", "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14", None, None,
                ("j1", "kick")),
               ("x", "emitsb_sbc43s", "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43", None,
                "score", ("j1", "kick"))],
        "H2": [("y", "emitsb_sb403s", "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sb403", None,
                "score", ("j1", "kick"))],
        "H3": [("lc", "emitsb_sbc43s", "slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43", None,
                "score", ("j1", "tick", "sleep"))],
        "H4": [("t", "emitsb_sbc43s", "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43",
                "tri,fill", "score", ("j1",))]}[STEP]
J1 = {"cmd": 1, "params": {"72": [FILL] * 16, "128": [FILL] * 96}, "timeout_ms": 200,
      "ticks": True}
J6 = {"cmd": 6, "params": {"224": [FILL] * 32}, "timeout_ms": 200, "ticks": True,
      "slots": list(range(40, 48))}
JOBS = {"j1": J1, "kick": dict(J6, kick="miscinfo"), "tick": J6, "sleep": dict(J6, sleep_ms=2000)}


def git_show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True,
                       text=True)
    assert r.returncode == 0, f"{path} at {rev} in {repo}: {r.stderr}"
    return r.stdout


def test_env():
    n = STEP[1]
    assert CFG["name"] == f"r41-n3f-h{n}" and CFG["prefix"] == f"r41h{n}"
    assert CFG["srcversion"] == SRCV and CFG["host_key_alias"] == "cedar"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "e516a7aa",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r41-n3f (the blobs and K1-K4), not main
    assert CFG["freeze"]["data"].startswith("b5b95bff2")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == [p[0] for p in PLAN]
    for name, blob, arm, order, ogf, jobs in PLAN:
        d = st[name]
        assert d["class"] == "flagged" and d["on_stop"] == "end"
        assert d["owntask"] == {"blob": blob, "arm": arm}
        assert d.get("gate_order") == order and d.get("on_gate_fail") == ogf
        assert "#limit 0" in open(os.path.join(KP, "tables", name + ".txt")).read().splitlines()


def test_the_one_row_a_stage():
    for name, blob, arm, order, ogf, jobs in PLAN:
        t = K.table(KP, name)
        assert [(r["name"], r["set"], r["tool"], r["knobs"], r["risk"]) for r in t] == [
            (f"{name}1-a", "fit", "owntask", ["-"], "flagged")]
        a = json.loads(t[0]["args"])
        want = [JOBS[k] for k in jobs]
        assert a == (want[0] if len(want) == 1 else want)


def test_each_blob_is_the_map_s_at_the_frozen_commit():
    m = json.loads(git_show(MAIN, CFG["freeze"]["resgx545"], "asm/fwtask/fwtask.map"))
    blobs = sorted({p[1] for p in PLAN})
    for b in blobs:
        data = open(os.path.join(KP, f"owntask/{b}.blob"), "rb").read()
        assert hashlib.sha256(data).hexdigest() == m[b]["sha256"]
    assert sorted(os.listdir(os.path.join(KP, "owntask"))) == [f"{b}.blob" for b in blobs]


def test_the_frozen_kit_takes_the_arms_and_the_rows():
    sys.path.insert(0, os.path.join(KP, "kit"))
    import session as S
    for name, blob, arm, order, ogf, jobs in PLAN:
        assert S.owntask_arm_problem(arm) is None
        job, bad = S.owntask_jobs(K.table(KP, name)[0]["args"], CFG["job_timeout"])
        assert not bad and job
    run = open(os.path.join(KP, "kit/run_stage.sh")).read()
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert all(re.fullmatch(sh, p[2]) for p in PLAN)
    assert "fill,tri|tri,fill) ;;" in run


def test_the_kernel_takes_each_arm_with_its_blob():
    """r40-kernel's own_arm (fork 423b436e7f80, the installed module): form=<name> arms a blob
    whose emit word is sgx_own_emit_forms[]'s; pds=crumb3 and pds=land are its images."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, blob, arm, order, ogf, jobs in PLAN:
        form = arm.split("form=")[1]
        sb = make.SIDEBAND[form]
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        assert f'{{ "{form}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    assert "#define SGX_OWN_PDS_CRUMB3_CTL\t0x01800100" in pds
    assert "#define SGX_OWN_PDS_LAND_CTL\t0x01800100" in pds
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in \
        git_show(LINUX, FORK, f"{SGXFIVE}/sgxfive_owntask.c")


def test_the_predictions_are_the_design_s_tables():
    want = {"C": {"C-SAME": "held", "C-DIFF": "failed", "C-NOKICK": "failed", "C-GATE": "held"},
            "X": {"X-REBASE": "held", "X-HIGH": "failed", "X-NONE": "failed",
                  "X-OTHER": "failed", "X-KICKFAULT": "failed", "X-NOKICK": "failed",
                  "X-FILL": "held"},
            "Y": {"Y-REBASE": "held", "Y-HIGH": "failed", "Y-NONE": "failed",
                  "Y-OTHER": "failed", "Y-KICKFAULT": "failed", "Y-NOKICK": "failed",
                  "Y-FILL": "held"},
            "LC": {"LC-EARLY": "held", "LC-REBASE": "held if not LC-EARLY", "LC-HEAL": "failed",
                   "LC-FILL": "held if reached", "LC-FILLOK": "failed"},
            "T": {"T-HEAD": "held", "T-OTHER": "failed", "T-HANG": "failed", "T-OK": "failed"}}
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
        assert ctl == {"res:0x0": "0x4e574f53", "res:0x44": "0x5a5a3301", "res:0x45": "@runid1",
                       "res:0x1": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0",
                       "j1": "DONE"}
    if STEP in ("H1", "H2"):
        m = make.STAGES[STEP][-1][1]
        p = K.predictions(KP, make.STAGES[STEP][-1][0])[make.row_name(make.STAGES[STEP][-1][0])]
        assert p["gate1"][f"{m}-FILL"] == "fault 0x000d0400 0x0004300f"
        assert p["devcd"][f"{m}-FILL"] == "0x000d0400 0x0004300f"
    if STEP == "H4":
        p = K.predictions(KP, "t")["t1-a"]
        assert p["gate1page"]["T-HEAD"] == "cid15 page 0x01555000"
