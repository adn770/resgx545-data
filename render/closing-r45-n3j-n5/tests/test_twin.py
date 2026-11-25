# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3j/design.md §9, the user's decisions
A=a, B=a, C=a, D=b, E=c, F=a) and the session build rules: every stage flagged, on_stop "end", #limit
0, emitsb_sbc43s armed with form=sbc43 at pdsat=fw14 and the design's image (mark for the plants,
crumbz for the Z stages, landq for q), the keys (plants: own_gate none and end_draws none; Z stages:
begin_draws as the row says, own_gate none; q: begin_draws none); one owntask row a stage: job 1 =
B11's command 1 (the 0xdeadc0de fill of slots 2-5 and dwords 128-223, 200 ms, ticks, no kick), then
q's command 6 on the next tick pass. The module is r45-kernel's (fork b1089172b2e7, srcversion
EC553F41FD8324BB6BF1764, to be booted): its own_arm takes each arm with the blob's word and image;
the kit at the frozen commit (K6-K9, pds=crumbz|landq) lints every row and arm; the README's
firmware-page dwords are the fork header's images."""
import hashlib
import json
import os
import re
import struct
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
FORK = "b1089172b2e7"                   # r45-kernel, the module to boot (round 45)
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV = "EC553F41FD8324BB6BF1764"
STEP = make.STEP
FILL = 0xDEADC0DE
A = "slots=0x1 entry=0 pds={} pdsat=fw14 form={}"
# the design's sessions (§3, §6 and the user's order N1, N2, N3)
W_KEYS = {"own_gate": "none", "end_draws": "none"}


def R(draws):
    return {"begin_draws": draws, "own_gate": "none"}


MARK, CRZ, LANDQ = (A.format(i, "sbc43") for i in ("mark", "crumbz", "landq"))
PLAN = {"N5": [("wj", MARK, W_KEYS, ("j1",)), ("zn", CRZ, R("none"), ("j1",)),
               ("wk", MARK, W_KEYS, ("j1",)), ("zt", CRZ, R("tri"), ("j1",)),
               ("wl", MARK, W_KEYS, ("j1",)), ("zft", CRZ, R("fill,tri"), ("j1",)),
               ("wm", MARK, W_KEYS, ("j1",)), ("zf", CRZ, R("fill"), ("j1",)),
               ("wn", MARK, W_KEYS, ("j1",)), ("zff", CRZ, R("fill,fill"), ("j1",)),
               ("wo", MARK, W_KEYS, ("j1",)), ("ztf", CRZ, R("tri,fill"), ("j1",)),
               ("wp", MARK, W_KEYS, ("j1",)), ("ztt", CRZ, R("tri,tri"), ("j1",))],
        "N6": [("wq", MARK, W_KEYS, ("j1",)),
               ("q", LANDQ, {"begin_draws": "none"}, ("j1", "tick"))]}[STEP]
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
    assert CFG["srcversion"] == SRCV          # SV at the freeze: the r45-kernel module's
    assert SRCV == "EC553F41FD8324BB6BF1764"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "1c8dc10e",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r45-n3j-z (K9, images, pin, kit) on main 1c8dc10e
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
    assert S.OWNTASK_IMAGES[-2:] == ("crumbz", "landq")
    assert "stage_health end" in run and "owntask-nogate" in run
    for name, arm, keys, jobs in PLAN:
        assert S.draws_ok(CFG["stages"][name].get("begin_draws", "fill,tri"))


def test_the_kernel_takes_each_arm_with_its_blob():
    """r45-kernel's own_arm (fork b1089172b2e7): form=<name> arms a blob whose emit word is
    sgx_own_emit_forms[]'s; pds=mark, crumbz and landq are its images, 3 rows each."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, arm, keys, jobs in PLAN:
        form = arm.split("form=")[1]
        assert form == make.FORM
        sb = make.SIDEBAND
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        assert f'{{ "{form}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    for img, n, fv in (("MARK", 21, 1), ("CRUMBZ", 17, 1), ("LANDQ", 18, 0)):
        assert f"#define SGX_OWN_PDS_{img}_CTL\t0x01800100" in pds
        assert f"#define SGX_OWN_PDS_{img}_WORDS\t{n}" in pds
        assert f"#define SGX_OWN_PDS_{img}_FILLV\t{fv}" in pds
    c = git_show(LINUX, FORK, f"{SGXFIVE}/sgxfive_owntask.c")
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in c
    for img in ("mark", "crumbz", "landq"):
        assert f'"{img}", sgx_own_pds_{img}, SGX_OWN_PDS_{img.upper()}_WORDS' in c


def header_words(img):
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    body = re.search(r"sgx_own_pds_%s\[SGX_OWN_PDS_%s_WORDS\][^=]*= \{(.*?)\n\};" % (
        img, img.upper()), pds, re.S).group(1)
    return [int(x, 16) for x in re.findall(r"0x([0-9a-f]{8}),", body)]


def test_the_readme_s_page_dwords_are_the_fork_header_s_images():
    """Each stage's `Firmware-page bytes per row` line: the header's words, with U0 the blob's and
    V0, V2 the kernel's at the arm (crumbz and mark) as the fill flag says."""
    readme = open(os.path.join(KP, "README.md")).read()
    blob = open(os.path.join(KP, f"owntask/{BLOB}.blob"), "rb").read()
    n, np_, ne, _ = struct.unpack_from("<HHHH", blob, 8)
    entries = struct.unpack_from(f"<{ne}H", blob, 16 + 8 * n + 8 * np_)
    u0 = 8 << 24 | (0x4000 + entries[1]) << 4 | 0xF
    for name, arm, keys, jobs in PLAN:
        img = re.search(r"pds=(\w+)", arm).group(1)
        line = re.search(rf"^- {name}1-a \({img}, (\d+) dwords from 0x100\): (.*?)(?=\n- |\n\n)",
                         readme, re.M | re.S)
        got = line.group(2).split()
        want = header_words(img)
        assert int(line.group(1)) == len(want) == len(got)
        for k, (g, w) in enumerate(zip(got, want)):
            if k == 0:
                assert g == f"0x{u0:08x}", (name, k)
            elif k in (4, 5) and img != "landq":
                assert g in ("V0", "V2") or g.startswith("0x32"), (name, k, g)
            else:
                assert g == f"0x{w:08x}", (name, k, g, w)
    assert header_words("crumbz")[:4] == header_words("crumb3")[:4]
    assert header_words("crumbz")[4:12] == header_words("crumb3")[4:12]
    assert header_words("crumbz")[12:] == [0x07001FE7, 0x07003547, 0x07000305, 0x07003FE7,
                                           0xAF000000]


def tags(stage):
    src = open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]
    got = {}
    for ln in src:
        f = ln.split("\t")
        if f[3] != "CTL":
            got[f[3]] = re.search(r"\[predicted: ([^\]]+)\]", f[5]).group(1)
    return got


# design §9.3-§9.5, frozen predictions as written (held, failed, printed)
WANT = {
    "W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
    "ZN": {"ZN-SAME": "held", "ZN-OTHER": "failed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZT": {"ZT-SA1": "held", "ZT-TRIPLE": "held", "ZT-ONE": "failed", "ZT-AOTHER": "printed",
           "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZFT": {"ZFT-SA1": "held", "ZFT-TRIPLE": "held", "ZFT-ONE": "failed",
            "ZFT-AOTHER": "printed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZF": {"ZF-SA1": "held", "ZF-TICK1": "failed", "ZF-DRAW": "held", "ZF-PLANT": "failed",
           "ZF-AOTHER": "printed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZFF": {"ZFF-SA1": "held", "ZFF-DRAW": "held", "ZFF-PLANT": "failed",
            "ZFF-AOTHER": "printed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZTF": {"ZTF-SA1": "held", "ZTF-DRAW": "held", "ZTF-TRIPLE": "failed",
            "ZTF-AOTHER": "printed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "ZTT": {"ZTT-LAST": "held", "ZTT-FIRST": "failed", "ZTT-TRIPLE": "held", "ZTT-ONE": "failed",
            "ZTT-AOTHER": "printed", "Z-QUIET": "held", "Z-FAULT": "failed"},
    "Q": {"Q-WRITE": "held", "Q-SA0": "held", "Q-LOW": "failed", "Q-OTHER": "printed",
          "Q-SERVE": "failed"},
}
# the words and rules as the design's tables write them (quantity: {outcome: value})
VALUES = {
    "ZN": {"zn": {"ZN-SAME": "SAME", "ZN-OTHER": "OTHER"}},
    "ZT": {"postsa1": {"ZT-SA1": "0x02400000"}, "sa02kind": {"ZT-TRIPLE": "@in:TRIPLE",
                                                           "ZT-ONE": "@in:ONE",
                                                           "ZT-AOTHER": "@notin:TRIPLE,ONE"}},
    "ZFT": {"postsa1": {"ZFT-SA1": "@any:0x04400000,0x04000010"},
            "sa02kind": {"ZFT-TRIPLE": "@in:TRIPLE", "ZFT-ONE": "@in:ONE",
                         "ZFT-AOTHER": "@notin:TRIPLE,ONE"}},
    "ZF": {"postsa1": {"ZF-SA1": "0x005d1000", "ZF-TICK1": "0x01000000"},
           "sa02kind": {"ZF-DRAW": "@in:LF", "ZF-PLANT": "@in:ONE", "ZF-AOTHER": "@notin:LF,ONE"}},
    "ZFF": {"postsa1": {"ZFF-SA1": "0x005d1000"},
            "sa02kind": {"ZFF-DRAW": "@in:LF", "ZFF-PLANT": "@in:ONE",
                         "ZFF-AOTHER": "@notin:LF,ONE"}},
    "ZTF": {"postsa1": {"ZTF-SA1": "0x02400000"},
            "sa02kind": {"ZTF-DRAW": "@in:LF", "ZTF-TRIPLE": "@in:TRIPLE",
                         "ZTF-AOTHER": "@notin:LF,TRIPLE"}},
    "ZTT": {"postsa1": {"ZTT-LAST": "@any:0x08400000,0x08000010",
                        "ZTT-FIRST": "@any:0x02400000,0x02000010"},
            "sa02kind": {"ZTT-TRIPLE": "@in:TRIPLE", "ZTT-ONE": "@in:ONE",
                         "ZTT-AOTHER": "@notin:TRIPLE,ONE"}},
    "Q": {"j1": {"Q-WRITE": "DONE"}, "postsa0": {"Q-WRITE": "0x005d2000"},
          "postsa1": {"Q-WRITE": "0x005d1000"},
          "j2fault": {"Q-SA0": "cid15 page 0x005d2000", "Q-LOW": "cid15 page 0x005d1000",
                      "Q-OTHER": "@faultnotin:cid15 page 0x005d2000,cid15 page 0x005d1000"},
          "j2": {"Q-SA0": "notdone", "Q-LOW": "notdone", "Q-SERVE": "done"}},
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
        z = st[1] in make.READS
        assert ("dr" in ctl) == z and ctl.get("dr", "ok") == "ok"
        assert ("dk" in ctl) == z and ctl.get("dk", "ok") == "ok"
        assert ("znctl" in ctl) == (z and st[0] != "zn") and ctl.get("znctl", "SAME") == "SAME"
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
        for q, vs in VALUES.get(st[1], {}).items():
            for x, v in vs.items():
                assert p[q][x] == v, (st[0], q, x, p[q].get(x))
    if STEP == "N5":
        p = K.predictions(KP, "wj")["wj1-a"]
        assert p["postsa1"]["W-SA1"] == "0x005d1000" and p["postpa1"]["W-SA13"] == "0x005d3000"
        assert K.predictions(KP, "zn")["zn1-a"]["snap9:0x0c08"]["Z-QUIET"] == "0x0"
    else:
        p = K.predictions(KP, "q")["q1-a"]
        assert p["j2"]["Q-SA0"] == "notdone" and "dr" not in p and "dk" not in p
        assert "begin_draws" not in CFG["stages"]["wq"]      # K7: the session's first stage
