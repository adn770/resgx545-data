# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3g/design.md §3, the user's decisions
A-F (a) of 2026-11-21) and the session build rules: every stage flagged, on_stop "end", #limit 0,
the owntask armed as the design says (crumb3, mark or landv at pdsat=fw14, the form's after-read
blob), the last stage's gate failure its planned, scored end (on_gate_fail "score"; the controls
c and s none), every gate the fill first; one owntask row a stage: job 1 = B11's command 1 (the
0xdeadc0de fill of slots 2-5 and dwords 128-223, 200 ms, ticks, no kick), then command 6 (dwords
224-255 filled and read as slots 40-47; on a GETMISCINFO kick in C, M, S, Q; on the next tick pass
and after 2000 ms in LV). The module is r42-kernel's (fork ec6511d5de87; srcversion a placeholder
until the lead sets it after the boot): its own_arm takes each arm with its blob's word and image;
the kit at the frozen commit lints every row and arm."""
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
FORK = "ec6511d5de87"                   # r42-kernel, the module this round builds and boots
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV_PLACEHOLDER = f"UNBUILT-r42-kernel-{FORK}"
STEP = make.STEP
FILL = 0xDEADC0DE
A = "slots=0x1 entry=0 pds={} pdsat=fw14 form={}"
# the design's sessions (§3 and the user's order G1, G2, G3)
PLAN = {"G1": [("c", "emitsb14s", A.format("crumb3", "fw14"), None, ("j1", "kick")),
               ("m", "emitsb_sbc43s", A.format("mark", "sbc43"), "score", ("j1", "kick"))],
        "G2": [("s", "emitsb14s", A.format("crumb3", "fw14"), None, ("j1", "kick")),
               ("q", "emitsb_sb402s", A.format("crumb3", "sb402"), "score", ("j1", "kick"))],
        "G3": [("lv", "emitsb_sbc43s", A.format("landv", "sbc43"), "score",
                ("j1", "tick", "sleep"))]}[STEP]
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
    k = STEP[1]
    assert CFG["name"] == f"r42-n3g-g{k}" and CFG["prefix"] == f"r42g{k}"
    assert CFG["host_key_alias"] == "cedar"
    # the placeholder until the lead sets the booted module's srcversion (then refreeze)
    assert CFG["srcversion"] == SRCV_PLACEHOLDER or re.fullmatch(r"[0-9A-F]{23}",
                                                                 CFG["srcversion"])
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "c0e2dc36",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r42-n3g (sb402s, mark, landv, K5), not main
    assert CFG["freeze"]["data"].startswith("5e9c84b22")
    assert not CFG["knobs"] and not CFG["kregs"]


def test_stages():
    st = CFG["stages"]
    assert list(st) == [p[0] for p in PLAN]
    for name, blob, arm, ogf, jobs in PLAN:
        d = st[name]
        assert d["class"] == "flagged" and d["on_stop"] == "end"
        assert d["owntask"] == {"blob": blob, "arm": arm}
        assert d.get("gate_order", "fill,tri") == "fill,tri" and d.get("on_gate_fail") == ogf
        assert "#limit 0" in open(os.path.join(KP, "tables", name + ".txt")).read().splitlines()


def test_the_one_row_a_stage():
    for name, blob, arm, ogf, jobs in PLAN:
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
    import session as S
    for name, blob, arm, ogf, jobs in PLAN:
        assert S.owntask_arm_problem(arm) is None
        job, bad = S.owntask_jobs(K.table(KP, name)[0]["args"], CFG["job_timeout"])
        assert not bad and job
    run = open(os.path.join(KP, "kit/run_stage.sh")).read()
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert all(re.fullmatch(sh, p[2]) for p in PLAN)


def test_the_kernel_takes_each_arm_with_its_blob():
    """r42-kernel's own_arm (fork ec6511d5de87): form=<name> arms a blob whose emit word is
    sgx_own_emit_forms[]'s; pds=crumb3, mark and landv are its images, 3 rows each."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, blob, arm, ogf, jobs in PLAN:
        form = arm.split("form=")[1]
        sb = make.SIDEBAND[form]
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
    c = {"C-SAME": "held", "C-DIFF": "failed", "C-NOKICK": "failed", "C-GATE": "held"}
    want = {"C": c,
            "M": {"M-PA": "held", "M-SA13": "held", "M-SA1": "held", "M-REBASE": "held",
                  "M-FILL": "held", "M-FILL43": "failed", "M-FILLM1": "failed",
                  "M-FILLOK": "failed", "M-NOKICK": "failed"},
            "S": {"S-KEEP": "held", "S-BACK": "failed", "S-OTHER": "printed", **c},
            "Q": {"Q-REBASE": "held", "Q-REP": "held", "Q-FILL": "held", "Q-NONE": "failed",
                  "Q-OTHER": "printed"},
            "LV": {"LV-V": "held", "LV-EARLY0": "failed", "LV-EARLY": "failed",
                   "LV-REBASE": "held", "LV-HEAL": "failed", "LV-FILL": "held if reached",
                   "LV-FILLOK": "failed"}}
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
        assert ctl == {"res:0x0": "0x4e574f53", "j1rec:slot0": "0x5a5a3301",
                       "j1rec:slot1": "@runid1", "j1rec:cmd": "0x0", "snap0:0x0acc": "running",
                       "snap9:0x0c08": "0x0", "j1": "DONE", "j2rec:done": "done",
                       "j2rec:slot0": "0x5a5a3306", "j2rec:slot1": "@runid2"}
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
    if STEP == "G1":
        p = K.predictions(KP, "m")["m1-a"]
        assert p["gate1page"]["M-FILL"] == "cid15 page 0x005d3000"
        assert p["postpa1"]["M-PA"] == p["after2sa13"]["M-SA13"] == "0x005d3000"
        assert p["after2sa1"]["M-SA1"] == "0x005d1000"
    if STEP == "G2":
        p = K.predictions(KP, "s")["s1-a"]
        assert p["postpa1"]["S-KEEP"] == "0x005d3000" and p["postpa1"]["S-BACK"] == "0x00043000"
        assert p["postpa3"]["S-KEEP"] == "0x01555620" and p["postpa15"]["S-KEEP"] == "0x11b5d77a"
