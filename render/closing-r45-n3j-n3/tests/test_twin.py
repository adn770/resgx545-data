# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3j/design.md §3, the user's decisions
A=a, B=a, C=a, D=b, F=a) and the session build rules: every stage flagged, on_stop "end", #limit 0,
emitsb_sbc43s armed with form=sbc43 at pdsat=fw14 and the design's image (mark for the plants,
crumb3 for the reads, land for lf2, lt and lff), the keys (plants: own_gate none and end_draws none;
reads: begin_draws as the row says, own_gate none; the land stages: begin_draws as the row says);
one owntask row a stage: job 1 = B11's command 1 (the 0xdeadc0de fill of slots 2-5 and dwords
128-223, 200 ms, ticks, no kick), then the land stages' command 6 on the next tick pass. The module
is r42-kernel's (fork ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, running on the laptop): its
own_arm takes each arm with the blob's word and image; the kit at the frozen commit (K6-K9) lints
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
PLAN = {"N1": [("wa", MARK, W_KEYS, ("j1",)), ("ff2", CR3, R("fill,fill"), ("j1",)),
               ("wb", MARK, W_KEYS, ("j1",)), ("t2", CR3, R("tri"), ("j1",)),
               ("wc", MARK, W_KEYS, ("j1",)), ("tf2", CR3, R("tri,fill"), ("j1",)),
               ("wd", MARK, W_KEYS, ("j1",)), ("tt", CR3, R("tri,tri"), ("j1",)),
               ("we", MARK, W_KEYS, ("j1",)), ("f3", CR3, R("fill"), ("j1",)),
               ("f2b", CR3, R("fill"), ("j1",))],
        "N2": [("wg", MARK, W_KEYS, ("j1",)),
               ("lf2", LAND, {"begin_draws": "fill"}, ("j1", "tick"))],
        "N3": [("wh", MARK, W_KEYS, ("j1",)),
               ("lt", LAND, {"begin_draws": "tri"}, ("j1", "tick"))],
        "N4": [("wi", MARK, W_KEYS, ("j1",)),
               ("lff", LAND, {"begin_draws": "fill,fill"}, ("j1", "tick"))]}[STEP]
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
    assert CFG["name"] == f"r45-n3j-n{k}" and CFG["prefix"] == f"r45j{k}"
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["srcversion"] == SRCV          # the r42-kernel module the laptop runs
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "1c8dc10e",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r45-n3j (K9) on main 1c8dc10e, not main
    assert CFG["freeze"]["resgx545"] != subprocess.run(
        ["git", "-C", MAIN, "rev-parse", "1c8dc10e"], capture_output=True, text=True).stdout.strip()
    assert CFG["freeze"]["data"].startswith("ebfeaa775")
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


# design §3.1-§3.6, frozen predictions as written (held, failed, printed)
WANT = {
    "W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
    "FF2": {"FF2-KEEP": "held", "FF2-FILL": "failed", "FF2-TICK": "failed", "FF2-OTHER": "printed",
            "X-QUIET": "held"},
    "T2": {"T2-SAME": "held", "T2-34": "failed", "T2-KEEP": "failed", "T2-OTHER": "printed",
           "X-QUIET": "held"},
    "TF2": {"TF2-SAME": "held", "TF2-FILL": "failed", "TF2-KEEP": "failed",
            "TF2-OTHER": "printed", "X-QUIET": "held"},
    "TT": {"TT-LAST": "held", "TT-FIRST": "failed", "TT-KEEP": "failed", "TT-OTHER": "printed",
           "X-QUIET": "held"},
    "F3": {"F3-KEEP": "held", "F3-TICK": "failed", "F3-FILL": "failed", "F3-OTHER": "printed",
           "X-QUIET": "held"},
    "F2B": {"F2b-SAME": "held", "F2b-TICK": "failed", "F2b-FILL": "failed",
            "F2b-OTHER": "printed", "F2b-QUIET": "held"},
    "LF2": {"LF2-SA1": "held", "LF2-SA0": "held", "LF2-SA2": "held", "LF2-TICK": "failed",
            "LF2-AOTHER": "printed", "LF2-PAGE": "held", "LF2-EARLY0": "held",
            "LF2-EARLY1": "failed", "LF2-SERVE": "failed"},
    "LT": {"LT-SA1": "held", "LT-TRIPLE": "held", "LT-ONE": "failed", "LT-AOTHER": "printed",
           "LT-PAGE": "held", "LT-HIST": "failed", "LT-SERVE": "failed"},
    "LFF": {"LFF-SA1": "held", "LFF-SA0": "held", "LFF-V0": "failed", "LFF-PAGE": "held",
            "LFF-HIST": "failed"},
}
# the words and rules as the design's tables write them (quantity: {outcome: value})
VALUES = {
    "FF2": {"postsa1": {"FF2-KEEP": "0x005d1000", "FF2-FILL": "@any:0x04000010,0x02000010",
                        "FF2-TICK": "@any:tick"}},
    "T2": {"postsa1": {"T2-SAME": "0x02400000", "T2-34": "0x02000010", "T2-KEEP": "0x005d1000"}},
    "TF2": {"postsa1": {"TF2-SAME": "0x02400000", "TF2-FILL": "0x08000010",
                        "TF2-KEEP": "0x005d1000"}},
    "TT": {"postsa1": {"TT-LAST": "@any:0x08400000,0x08000010",
                       "TT-FIRST": "@any:0x02400000,0x02000010", "TT-KEEP": "0x005d1000"}},
    "F3": {"postsa1": {"F3-KEEP": "0x005d1000", "F3-TICK": "0x01000000", "F3-FILL": "0x02000010"}},
    "F2B": {"postsa1": {"F2b-SAME": "0x05400000", "F2b-TICK": "0x01000000",
                        "F2b-FILL": "0x02000010"}},
    "LF2": {"postsa1": {"LF2-SA1": "0x005d1000", "LF2-TICK": "0x01000000"},
            "postsa0": {"LF2-SA0": "0x00000002"}, "sa2shape": {"LF2-SA2": "TIMER"},
            "sa02kind": {"LF2-AOTHER": "@notin:LF"},
            "j2fault": {"LF2-PAGE": "@hsa0", "LF2-EARLY0": "cid15 page 0x00000000",
                        "LF2-EARLY1": "@post1"}},
    "LT": {"postsa1": {"LT-SA1": "0x02400000"},
           "postsa0": {"LT-TRIPLE": "0x00000000", "LT-ONE": "@V0", "LT-HIST": "@V0"},
           "sa2shape": {"LT-TRIPLE": "TIMER"}, "postsa2": {"LT-ONE": "@V2"},
           "sa02kind": {"LT-AOTHER": "@notin:TRIPLE,ONE"},
           "j2fault": {"LT-PAGE": "@hsa0", "LT-HIST": "cid15 page 0x00000000"}},
    "LFF": {"postsa1": {"LFF-SA1": "0x005d1000"},
            "postsa0": {"LFF-SA0": "0x00000002", "LFF-V0": "@V0", "LFF-HIST": "@V0"},
            "j2fault": {"LFF-PAGE": "@hsa0", "LFF-HIST": "cid15 page 0x00000000"}},
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
        assert ("dk" in ctl) == (st[1] != "W") and ctl.get("dk", "ok") == "ok"
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
        for q, vs in VALUES.get(st[1], {}).items():
            for x, v in vs.items():
                assert p[q][x] == v, (st[0], q, x, p[q].get(x))
    if STEP == "N1":
        p = K.predictions(KP, "wa")["wa1-a"]
        assert p["postsa1"]["W-SA1"] == "0x005d1000" and p["postpa1"]["W-SA13"] == "0x005d3000"
        assert K.predictions(KP, "f2b")["f2b1-a"]["snap9:0x0c08"]["F2b-QUIET"] == "0x0"
    else:
        lst = [s[0] for s in make.STAGES[STEP] if s[1] in make.LANDS][0]
        p = K.predictions(KP, lst)[f"{lst}1-a"]
        assert p["j2"][lst.upper() + "-PAGE"] == "notdone"
