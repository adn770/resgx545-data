# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3i/design.md §3, the user's decisions
A-E (a) of 2026-11-23) and the session build rules: every stage flagged, on_stop "end", #limit 0,
emitsb_sbc43s armed with form=sbc43 at pdsat=fw14 and the design's image (mark for the plants,
crumb3 for the reads, land for lm and lf), the keys (plants: own_gate none and end_draws none;
reads: begin_draws as the row says, own_gate none; lm: begin_draws none; lf: begin_draws fill);
one owntask row a stage: job 1 = B11's command 1 (the 0xdeadc0de fill of slots 2-5 and dwords
128-223, 200 ms, ticks, no kick), then lm's and lf's command 6 on the next tick pass. The module is
r42-kernel's (fork ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, running on the laptop): its
own_arm takes each arm with the blob's word and image; the kit at the frozen commit (K6-K8) lints
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
FORK = "ec6511d5de87"                   # r42-kernel, the module the laptop runs (no rebuild)
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV = "079DD0D13F231EEAC52FE0F"
STEP = make.STEP
FILL = 0xDEADC0DE
A = "slots=0x1 entry=0 pds={} pdsat=fw14 form={}"
# the design's sessions (§3, §6 and the user's order N1, N2, N3)
W_KEYS = {"own_gate": "none", "end_draws": "none"}


def R(draws):
    return {"begin_draws": draws, "own_gate": "none"}


MARK, CR3, LAND = (A.format(i, "sbc43") for i in ("mark", "crumb3", "land"))
PLAN = {"N1": [("wa", MARK, W_KEYS, ("j1",)), ("ft", CR3, R("fill,tri"), ("j1",)),
               ("wb", MARK, W_KEYS, ("j1",)), ("ff", CR3, R("fill,fill"), ("j1",)),
               ("wc", MARK, W_KEYS, ("j1",)), ("t", CR3, R("tri"), ("j1",)),
               ("wd", MARK, W_KEYS, ("j1",)), ("tf", CR3, R("tri,fill"), ("j1",)),
               ("f2", CR3, R("fill"), ("j1",))],
        "N2": [("wl", MARK, W_KEYS, ("j1",)),
               ("lm", LAND, {"begin_draws": "none"}, ("j1", "tick"))],
        "N3": [("wf", MARK, W_KEYS, ("j1",)),
               ("lf", LAND, {"begin_draws": "fill"}, ("j1", "tick"))]}[STEP]
BLOB = "emitsb_sbc43s"
J1 = {"cmd": 1, "params": {"72": [FILL] * 16, "128": [FILL] * 96}, "timeout_ms": 200,
      "ticks": True}
J6 = {"cmd": 6, "params": {"224": [FILL] * 32}, "timeout_ms": 200, "ticks": True,
      "slots": list(range(40, 48))}
JOBS = {"j1": J1, "tick": J6}


def git_show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True,
                       text=True)
    assert r.returncode == 0, f"{path} at {rev} in {repo}: {r.stderr}"
    return r.stdout


def test_env():
    k = STEP[1]
    assert CFG["name"] == f"r44-n3i-n{k}" and CFG["prefix"] == f"r44i{k}"
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["srcversion"] == SRCV          # the r42-kernel module the laptop runs
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "9076992b",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r44-n3i (K8) on main 9076992b, not main
    assert CFG["freeze"]["resgx545"] != subprocess.run(
        ["git", "-C", MAIN, "rev-parse", "9076992b"], capture_output=True, text=True).stdout.strip()
    assert CFG["freeze"]["data"].startswith("b3df8fc21")
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
    # K7: the first stage keeps its begin draws; a stage with its own draws follows its plant
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


def test_the_frozen_kit_takes_the_arms_the_rows_and_the_k7_k8_keys():
    import session as S
    for name, arm, keys, jobs in PLAN:
        assert S.owntask_arm_problem(arm) is None
        job, bad = S.owntask_jobs(K.table(KP, name)[0]["args"], CFG["job_timeout"])
        assert not bad and job
    run = open(os.path.join(KP, "kit/run_stage.sh")).read()
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert all(re.fullmatch(sh, p[1]) for p in PLAN)
    assert "stage_health end" in run and "owntask-nogate" in run
    for name, arm, keys, jobs in PLAN:
        assert S.draws_ok(CFG["stages"][name].get("begin_draws", "fill,tri"))


def test_the_kernel_takes_each_arm_with_its_blob():
    """r42-kernel's own_arm (fork ec6511d5de87): form=<name> arms a blob whose emit word is
    sgx_own_emit_forms[]'s; pds=crumb3, mark and land are its images, 3 rows each."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, arm, keys, jobs in PLAN:
        form = arm.split("form=")[1]
        assert form == make.FORM
        sb = make.SIDEBAND
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        assert f'{{ "{form}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    for img, n, fv in (("CRUMB3", 19, 1), ("MARK", 21, 1), ("LAND", 16, 0)):
        assert f"#define SGX_OWN_PDS_{img}_CTL\t0x01800100" in pds
        assert f"#define SGX_OWN_PDS_{img}_WORDS\t{n}" in pds
        assert f"#define SGX_OWN_PDS_{img}_FILLV\t{fv}" in pds
    c = git_show(LINUX, FORK, f"{SGXFIVE}/sgxfive_owntask.c")
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in c
    assert '[SGX_OWN_IMG_MARK] = { "mark"' in c and '[SGX_OWN_IMG_LAND] = { "land"' in c


def tags(stage):
    src = open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]
    got = {}
    for ln in src:
        f = ln.split("\t")
        if f[3] != "CTL":
            got[f[3]] = re.search(r"\[predicted: ([^\]]+)\]", f[5]).group(1)
    return got


# design §3.1-§3.5, frozen predictions as written (held, failed, printed)
WANT = {
    "W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
    "FT": {"FT-SAME": "held", "X-QUIET": "held", "X-KEEP": "failed", "X-OTHER": "printed"},
    "FF": {"FF-N": "held", "FF-LAST": "failed", "FF-K": "failed", "X-QUIET": "held",
           "X-KEEP": "failed", "X-OTHER": "printed"},
    "T": {"T-N": "held", "T-LAST": "failed", "T-K": "failed", "X-QUIET": "held",
          "X-KEEP": "failed", "X-OTHER": "printed"},
    "TF": {"TF-N": "held", "TF-LAST": "failed", "TF-K": "failed", "TF-TRI": "failed",
           "X-QUIET": "held", "X-KEEP": "failed", "X-OTHER": "printed"},
    "F2": {"F2-N": "held", "F2-ACC": "failed", "F2-K": "failed", "F2-PRIOR": "failed",
           "F2-OTHER": "printed", "F2-QUIET": "held"},
    "LM": {"LM-V0": "held", "LM-KEEP": "held", "LM-EARLY1": "held", "LM-EARLY0": "failed",
           "LM-EARLY13": "failed", "LM-SERVE": "failed", "LM-OTHER": "printed"},
    "LF": {"LF-SA1": "held", "LF-EVT": "held", "LF-TICK": "failed", "LF-ONE": "failed",
           "LF-AOTHER": "printed", "LF-EARLY0": "held", "LF-EARLY1": "failed",
           "LF-SERVE": "failed"},
}
# the words and rules as the design's tables write them (quantity: {outcome: value})
VALUES = {
    "FT": {"postsa1": {"FT-SAME": "@any:0x04400000,0x04000010", "X-KEEP": "0x005d1000"}},
    "FF": {"postsa1": {"FF-N": "0x02000000", "FF-LAST": "0x01000000", "FF-K": "0x04000010"}},
    "T": {"postsa1": {"T-N": "@any:0x03400000,0x03000010",
                      "T-LAST": "@any:0x04400000,0x04000010",
                      "T-K": "@any:0x02400000,0x02000010"}},
    "TF": {"postsa1": {"TF-N": "0x04000000", "TF-LAST": "0x01000000", "TF-K": "0x08000010",
                       "TF-TRI": "@any:0x04400000,0x04000010"}},
    "F2": {"postsa1": {"F2-N": "0x01000000", "F2-ACC": "0x09000000", "F2-K": "0x02000010",
                       "F2-PRIOR": "@any:0x04400000,0x04000010"}},
    "LM": {"postsa1": {"LM-KEEP": "0x005d1000"}, "j2fault": {
        "LM-EARLY1": "@post1", "LM-EARLY0": "cid15 page 0x00000000", "LM-EARLY13": "@post13",
        "LM-OTHER": "@other"}, "postsa0": {"LM-V0": "@V0"}, "postsa2": {"LM-V0": "@V2"}},
    "LF": {"postsa1": {"LF-SA1": "0x01000000"}, "sa02kind": {
        "LF-EVT": "EVT", "LF-TICK": "TICK", "LF-ONE": "ONE", "LF-AOTHER": "OTHER"},
        "j2fault": {"LF-EARLY0": "cid15 page 0x00000000", "LF-EARLY1": "@post1"}},
}


def test_the_predictions_are_the_design_s_tables():
    for st in make.STAGES[STEP]:
        assert tags(st[0]) == WANT[st[1]], st
        p = K.predictions(KP, st[0])[f"{st[0]}1-a"]
        ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
        common = {"res:0x0": "0x4e574f53", "j1rec:slot0": "0x5a5a3301", "j1rec:slot1": "@runid1",
                  "j1rec:cmd": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0",
                  "j1": "DONE"}
        assert {q: v for q, v in ctl.items() if q in common} == common
        assert ("dr" in ctl) == (st[1] != "W") and ctl.get("dr", "ok") == "ok"
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
        for q, vs in VALUES.get(st[1], {}).items():
            for x, v in vs.items():
                assert p[q][x] == v, (st[0], q, x, p[q].get(x))
    if STEP == "N1":
        p = K.predictions(KP, "wa")["wa1-a"]
        assert p["postsa1"]["W-SA1"] == "0x005d1000" and p["postpa1"]["W-SA13"] == "0x005d3000"
        assert K.predictions(KP, "f2")["f21-a"]["snap9:0x0c08"]["F2-QUIET"] == "0x0"
    if STEP == "N2":
        p = K.predictions(KP, "lm")["lm1-a"]
        assert p["j2"]["LM-SERVE"] == "done" and p["j2"]["LM-EARLY1"] == "notdone"
