# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3k/design.md §2, §4 and §10, the
user's decisions A=a, B=b, C=a, D=a, E=a, F=b) and the session build rules: every stage flagged,
on_stop "end", #limit 0, its blob armed at pdsat=fw14 with its form and the design's image (N rows:
emitsb_sbc43s, form=sbc43, mark for the plants, crumbz for ZFF2, land for LFF2, LFF3 and LF3F,
landq for Q2, landr for R and R2, landp for P and P2; B5 and B6: emitsb_sb043s and emitsb_sb803s,
crumb3, form=sb043 and sb803, on_gate_fail score), the keys (plants: own_gate none and end_draws
none; ZFF2: begin_draws fill,fill, own_gate none; land stages: begin_draws as the row says); one
owntask row a stage: job 1 = B11's command 1 (the 0xdeadc0de fill of slots 2-5 and dwords 128-223,
200 ms, ticks, no kick), then the land stages' command 6 on the next tick pass, the B rows' on a
GETMISCINFO kick. The module is r46-kernel's (fork c5094783eb88, its cachix build's srcversion, to
be booted): its own_arm takes each arm with the blob's word and image; the kit at the frozen commit
(K6-K10, pds=landr|landp) lints every row and arm; the README's firmware-page dwords are the fork
header's images."""
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
FORK = "c5094783eb88"                   # r46-kernel, the module to boot (round 46)
SGXFIVE = "drivers/gpu/drm/gma500/sgxfive"
SRCV = "10BBF3BFBD51D559106589F"
STEP = make.STEP
FILL = 0xDEADC0DE
A = "slots=0x1 entry=0 pds={} pdsat=fw14 form={}"
W_KEYS = {"own_gate": "none", "end_draws": "none"}


def L(draws):
    return {"begin_draws": draws}


MARK, CRZ, LAND, LANDQ, LANDR, LANDP = (A.format(i, "sbc43") for i in (
    "mark", "crumbz", "land", "landq", "landr", "landp"))
PLAN = {"B5": [("b5", A.format("crumb3", "sb043"), {"on_gate_fail": "score"}, ("j1", "kick"))],
        "B6": [("b6", A.format("crumb3", "sb803"), {"on_gate_fail": "score"}, ("j1", "kick"))],
        "N1": [("wa", MARK, W_KEYS, ("j1",)),
               ("zff2", CRZ, {"begin_draws": "fill,fill", "own_gate": "none"}, ("j1",)),
               ("wb", MARK, W_KEYS, ("j1",)), ("lff2", LAND, L("fill,fill"), ("j1", "tick"))],
        "N2": [("wc", MARK, W_KEYS, ("j1",)), ("lff3", LAND, L("fill,fill"), ("j1", "tick"))],
        "N3": [("wd", MARK, W_KEYS, ("j1",)), ("lf3f", LAND, L("fill,fill,fill"), ("j1", "tick"))],
        "N4": [("we", MARK, W_KEYS, ("j1",)), ("q2", LANDQ, L("none"), ("j1", "tick"))],
        "N5": [("wf", MARK, W_KEYS, ("j1",)), ("r", LANDR, L("none"), ("j1", "tick"))],
        "N6": [("wg", MARK, W_KEYS, ("j1",)), ("p", LANDP, L("none"), ("j1", "tick"))],
        "N7": [("wh", MARK, W_KEYS, ("j1",)), ("r2", LANDR, L("none"), ("j1", "tick"))],
        "N8": [("wi", MARK, W_KEYS, ("j1",)), ("p2", LANDP, L("none"), ("j1", "tick"))]}[STEP]
BLOB = {"B5": "emitsb_sb043s", "B6": "emitsb_sb803s"}.get(STEP, "emitsb_sbc43s")
J1 = {"cmd": 1, "params": {"72": [FILL] * 16, "128": [FILL] * 96}, "timeout_ms": 200,
      "ticks": True}
J6 = {"cmd": 6, "params": {"224": [FILL] * 32}, "timeout_ms": 200, "ticks": True,
      "slots": list(range(40, 48))}
JK = dict(J6, kick="miscinfo")
JOBS = {"j1": J1, "tick": J6, "kick": JK}
NAMES = {"B5": ("r46-n3k-b5", "r46k5b"), "B6": ("r46-n3k-b6", "r46k6b")}


def git_show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True,
                       text=True)
    assert r.returncode == 0, f"{path} at {rev} in {repo}: {r.stderr}"
    return r.stdout


def test_env():
    name, prefix = NAMES.get(STEP, (f"r46-n3k-n{STEP[1]}", f"r46k{STEP[1]}"))
    assert CFG["name"] == name and CFG["prefix"] == prefix
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["srcversion"] == SRCV          # SV at the freeze: the r46-kernel module's
    assert re.fullmatch(r"[0-9A-F]{23}", SRCV) and SRCV != "EC553F41FD8324BB6BF1764"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "908b7e96",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r46-n3k (images, blobs, pin, K10) on main 908b7e96
    assert CFG["freeze"]["resgx545"] != subprocess.run(
        ["git", "-C", MAIN, "rev-parse", "908b7e96"], capture_output=True, text=True).stdout.strip()
    assert CFG["freeze"]["data"].startswith("72e07b2d6")
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


def test_the_frozen_kit_takes_the_arms_the_rows_and_the_keys():
    import session as S
    for name, arm, keys, jobs in PLAN:
        assert S.owntask_arm_problem(arm) is None
        job, bad = S.owntask_jobs(K.table(KP, name)[0]["args"], CFG["job_timeout"])
        assert not bad and job
    run = open(os.path.join(KP, "kit/run_stage.sh")).read()
    sh = re.search(r"grep -Eqx '(slots=0x[^']*)'", run).group(1)
    assert all(re.fullmatch(sh, p[1]) for p in PLAN)
    assert S.OWNTASK_IMAGES[-2:] == ("landr", "landp")
    assert "stage_health end" in run and "owntask-nogate" in run
    for name, arm, keys, jobs in PLAN:
        assert S.draws_ok(CFG["stages"][name].get("begin_draws", "fill,tri"))


def test_the_kernel_takes_each_arm_with_its_blob():
    """r46-kernel's own_arm (fork c5094783eb88): form=<name> arms a blob whose emit word is
    sgx_own_emit_forms[]'s; pds=mark, crumbz, land, landq, landr, landp and crumb3 are its images,
    3 rows each."""
    regs = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_regs.h")
    for name, arm, keys, jobs in PLAN:
        form = arm.split("form=")[1]
        assert form == make.FORM
        sb = make.SIDEBAND
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        assert f'{{ "{form}", 0x{w:016x}ULL }},\t/* sideband 0x{sb:03x} */' in regs
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    for img, n, fv in (("MARK", 21, 1), ("CRUMBZ", 17, 1), ("LAND", 16, 0), ("LANDQ", 18, 0),
                       ("LANDR", 18, 0), ("LANDP", 18, 1), ("CRUMB3", 19, 1)):
        assert f"#define SGX_OWN_PDS_{img}_CTL\t0x01800100" in pds
        assert f"#define SGX_OWN_PDS_{img}_WORDS\t{n}" in pds
        assert f"#define SGX_OWN_PDS_{img}_FILLV\t{fv}" in pds
    c = git_show(LINUX, FORK, f"{SGXFIVE}/sgxfive_owntask.c")
    assert "if (emit && sgx_own_emit_form(b) != a->form)" in c
    for img in ("mark", "crumbz", "land", "landq", "landr", "landp", "crumb3"):
        assert f'"{img}", sgx_own_pds_{img}, SGX_OWN_PDS_{img.upper()}_WORDS' in c


def header_words(img):
    pds = git_show(LINUX, FORK, f"{SGXFIVE}/sgx_own_pds.h")
    body = re.search(r"sgx_own_pds_%s\[SGX_OWN_PDS_%s_WORDS\][^=]*= \{(.*?)\n\};" % (
        img, img.upper()), pds, re.S).group(1)
    return [int(x, 16) for x in re.findall(r"0x([0-9a-f]{8}),", body)]


FILLV = {"mark": True, "crumbz": True, "crumb3": True, "landp": True, "land": False,
         "landq": False, "landr": False}


def test_the_readme_s_page_dwords_are_the_fork_header_s_images():
    """Each stage's `Firmware-page bytes per row` line: the header's words, with U0 the blob's and
    V0, V2 the kernel's at the arm where the fill flag says (mark, crumbz, crumb3, landp)."""
    readme = open(os.path.join(KP, "README.md")).read()
    blob = open(os.path.join(KP, f"owntask/{BLOB}.blob"), "rb").read()
    n, np_, ne, _ = struct.unpack_from("<HHHH", blob, 8)
    entries = struct.unpack_from(f"<{ne}H", blob, 16 + 8 * n + 8 * np_)
    u0 = 8 << 24 | (0x4000 + entries[1]) << 4 | 0xF
    assert u0 == 0x080401EF
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
            elif k in (4, 5) and FILLV[img]:
                assert g in ("V0", "V2"), (name, k, g)
            else:
                assert g == f"0x{w:08x}", (name, k, g, w)
    q, r, v, p = (header_words(i) for i in ("landq", "landr", "landv", "landp"))
    assert [k for k in range(18) if q[k] != r[k]] == [8] and r[8] == 0x04400000
    assert [k for k in range(18) if v[k] != p[k]] == [9, 10] and p[9:11] == [0x005D2000, 0x100]


def tags(stage):
    src = open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]
    got = {}
    for ln in src:
        f = ln.split("\t")
        if f[3] != "CTL":
            got[f[3]] = re.search(r"\[predicted: ([^\]]+)\]", f[5]).group(1)
    return got


def lff(x):
    return {f"{x}-KEEP": "held", f"{x}-FILL2": "failed", f"{x}-FILL1": "failed",
            f"{x}-OTHER": "printed", f"{x}-SA0": "held", f"{x}-TRIPLE": "failed",
            f"{x}-PAGE0": "held", f"{x}-SERVE": "failed"}


def rr(x):
    return {f"{x}-WRITE": "held", f"{x}-LOW": "held", f"{x}-SA0": "failed",
            f"{x}-OTHER": "printed", f"{x}-SERVE": "failed"}


def pp(x):
    return {f"{x}-WRITE": "held", f"{x}-UNMAP": "held", f"{x}-MAPPED": "failed",
            f"{x}-OTHER": "printed"}


def bb(x):
    return {f"{x}-NEVER": "failed", f"{x}-T1": "failed", f"{x}-T2": "failed", f"{x}-T3": "failed",
            f"{x}-E1": "failed", f"{x}-DONE": "held", f"{x}-RUN": "held", f"{x}-HID": "held",
            f"{x}-SAME": "held", f"{x}-REBASE": "failed", f"{x}-AOTHER": "printed",
            f"{x}-NOKICK": "failed", f"{x}-GATE": "held", f"{x}-FILL": "failed",
            f"{x}-QUIET": "held", f"{x}-LAND4": "printed", f"{x}-LANDNONE": "printed"}


# design §4.2-§4.9 and §10.1, frozen predictions as written (held, failed, printed)
WANT = {
    "W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
    "ZFF2": {"ZFF2-KEEP": "held", "ZFF2-FILL2": "failed", "ZFF2-OTHER": "printed",
             "ZFF2-QUIET": "held", "ZFF2-FAULT": "failed"},
    "LFF2": lff("LFF2"), "LFF3": lff("LFF3"),
    "LF3F": {"LF3F-KEEP": "held", "LF3F-SECOND": "failed", "LF3F-LAST": "failed",
             "LF3F-FIRST": "failed", "LF3F-OTHER": "printed", "LF3F-PAGE0": "held",
             "LF3F-SERVE": "failed"},
    "Q2": {"Q2-WRITE": "held", "Q2-SAME": "held", "Q2-SA0": "failed", "Q2-OTHER": "printed",
           "Q2-SERVE": "failed"},
    "R": rr("R"), "R2": rr("R2"), "P": pp("P"), "P2": pp("P2"), "B5": bb("B5"), "B6": bb("B6"),
}
P0, PM1, PQ0, PL4 = ("cid15 page 0x00000000", "cid15 page 0x005d1000", "cid15 page 0x005d2000",
                     "cid15 page 0x04400000")
# the words and rules as the design's tables write them (quantity: {outcome: value})
VALUES = {
    "ZFF2": {"zffkind": {"ZFF2-KEEP": "KEEP", "ZFF2-FILL2": "FILL2", "ZFF2-OTHER": "OTHER"}},
    "LFF2": {"postsa1": {"LFF2-KEEP": "0x005d1000", "LFF2-FILL2": "0x04000010",
                         "LFF2-FILL1": "0x02000010",
                         "LFF2-OTHER": "@notany:0x005d1000,0x04000010,0x02000010"},
             "sa02kind": {"LFF2-SA0": "@in:LF", "LFF2-TRIPLE": "@in:TRIPLE"},
             "j2fault": {"LFF2-PAGE0": P0}, "j2": {"LFF2-PAGE0": "notdone", "LFF2-SERVE": "done"}},
    "LF3F": {"postsa1": {"LF3F-KEEP": "0x005d1000", "LF3F-SECOND": "0x04000010",
                         "LF3F-LAST": "0x06000010", "LF3F-FIRST": "0x02000010"},
             "j2fault": {"LF3F-PAGE0": P0}},
    "Q2": {"postsa0": {"Q2-WRITE": "0x005d2000"}, "postsa1": {"Q2-WRITE": "0x005d1000"},
           "j2fault": {"Q2-SAME": PM1, "Q2-SA0": PQ0, "Q2-OTHER": f"@faultnotin:{PQ0},{PM1}"}},
    "R": {"postsa0": {"R-WRITE": "0x04400000"}, "postsa1": {"R-WRITE": "0x005d1000"},
          "j2fault": {"R-LOW": PM1, "R-SA0": PL4, "R-OTHER": f"@faultnotin:{PM1},{PL4}"}},
    "P": {"postsa0": {"P-WRITE": "@V0"}, "postsa1": {"P-WRITE": "0x005d2000"},
          "postsa2": {"P-WRITE": "@V2"},
          "j2fault": {"P-UNMAP": PQ0, "P-MAPPED": f"@notin:{PQ0}", "P-OTHER": f"@faultnotin:{PQ0}"}},
    "B5": {"start": {"B5-DONE": "DONE", "B5-NEVER": "NEVER", "B5-RUN": "@in:T1,T2,T3,E1,DONE"},
           "after2": {"B5-SAME": "@in:PRE,BOTH", "B5-REBASE": "POST"},
           "gate1": {"B5-GATE": "exact", "B5-FILL": "@notin:exact"}},
}
VALUES["LFF3"] = {q: {x.replace("LFF2", "LFF3"): v.replace("LFF2", "LFF3") for x, v in d.items()}
                  for q, d in VALUES["LFF2"].items()}
VALUES["R2"] = {q: {x.replace("R-", "R2-"): v for x, v in d.items()} for q, d in VALUES["R"].items()}
VALUES["P2"] = {q: {x.replace("P-", "P2-"): v for x, v in d.items()} for q, d in VALUES["P"].items()}
VALUES["B6"] = {q: {x.replace("B5", "B6"): v for x, v in d.items()} for q, d in VALUES["B5"].items()}


def test_the_predictions_are_the_design_s_tables():
    for st in make.STAGES[STEP]:
        assert tags(st[0]) == WANT[st[1]], st
        p = K.predictions(KP, st[0])[f"{st[0]}1-a"]
        ctl = {q: mv["CTL"] for q, mv in p.items() if "CTL" in mv}
        common = {"res:0x0": "0x4e574f53", "j1rec:slot0": "0x5a5a3301", "j1rec:slot1": "@runid1",
                  "j1rec:cmd": "0x0", "snap0:0x0acc": "running", "snap9:0x0c08": "0x0",
                  "j1": "DONE"}
        assert {q: v for q, v in ctl.items() if q in common} == common
        scored = st[1] in make.READS + make.FILLS
        assert ("dr" in ctl) == scored and ctl.get("dr", "ok") == "ok"
        assert ("dk" in ctl) == scored and ctl.get("dk", "ok") == "ok"
        assert ("j2rec:done" in ctl) == (st[1] in make.LANDS + make.BROWS)
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
        for q, vs in VALUES.get(st[1], {}).items():
            for x, v in vs.items():
                assert p[q][x] == v, (st[0], q, x, p[q].get(x))
