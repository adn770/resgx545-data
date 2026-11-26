# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/n3k/design.md §11.3, §11.4, the
user's decisions G=a, H=a, I=a, J=a, K=a) and the session build rules: every stage flagged, on_stop
"end", #limit 0, emitsb_sbc43s armed at pdsat=fw14 with form=sbc43 and the design's image (mark
for the plants, land for LFK, LTK, LFK2 and LFKP, landr for R and R2, landp for P and P2), the keys
(plants: own_gate none and end_draws none; land stages: begin_draws as the row says); one owntask
row a stage: job 1 = B11's command 1, then the land stages' command 6 on the next tick pass. The
stages are byte for byte their round 45/46 twins but the names (LFK: r45 n2 lf2; LTK: r45 n3 lt;
R, P, R2, P2: N5-N8's). The module is r46-kernel's (fork c5094783eb88): its own_arm takes each arm
with the blob's word and image; the kit at the frozen commit (K6-K11) lints every row and arm; the
README's firmware-page dwords are the fork header's images."""
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


MARK, LAND, LANDR, LANDP = (A.format(i, "sbc43") for i in ("mark", "land", "landr", "landp"))
PLAN = {"N9": [("w9", MARK, W_KEYS, ("j1",)), ("lfk", LAND, L("fill"), ("j1", "tick"))],
        "N10": [("w10", MARK, W_KEYS, ("j1",)), ("ltk", LAND, L("tri"), ("j1", "tick"))],
        "N11": [("w11", MARK, W_KEYS, ("j1",)), ("lfk2", LAND, L("fill"), ("j1", "tick"))],
        "N12": [("w12", MARK, W_KEYS, ("j1",)), ("lfkp", LAND, L("fill"), ("j1", "tick"))],
        "N13": [("w13", MARK, W_KEYS, ("j1",)), ("r", LANDR, L("none"), ("j1", "tick"))],
        "N14": [("w14", MARK, W_KEYS, ("j1",)), ("p", LANDP, L("none"), ("j1", "tick"))],
        "N15": [("w15", MARK, W_KEYS, ("j1",)), ("r2", LANDR, L("none"), ("j1", "tick"))],
        "N16": [("w16", MARK, W_KEYS, ("j1",)), ("p2", LANDP, L("none"), ("j1", "tick"))]}[STEP]
BLOB = "emitsb_sbc43s"
# each stage's twin (design §11.4: "byte for byte but its names and srcversion"): the session dir
# and stage whose table and session.toml stage line are this stage's but the names
C29 = os.path.dirname(KP)                       # the session dirs sit side by side
TWIN = {"lfk": ("r45-n3j-n2", "lf2"), "lfk2": ("r45-n3j-n2", "lf2"),
        "lfkp": ("r45-n3j-n2", "lf2"), "ltk": ("r45-n3j-n3", "lt"), "r": ("r46-n3k-n5", "r"),
        "p": ("r46-n3k-n6", "p"), "r2": ("r46-n3k-n7", "r2"), "p2": ("r46-n3k-n8", "p2")}
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
    name, prefix = f"r46-n3k-n{STEP[1:]}", f"r46k{STEP[1:]}"
    assert CFG["name"] == name and CFG["prefix"] == prefix
    assert CFG["host_key_alias"] == "cedar"
    assert CFG["srcversion"] == SRCV          # SV at the freeze: the r46-kernel module's
    assert re.fullmatch(r"[0-9A-F]{23}", SRCV) and SRCV != "EC553F41FD8324BB6BF1764"
    assert CFG["health_tool"] == "t30" and list(CFG["tools"]) == ["t30"]
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    head = subprocess.run(["git", "-C", MAIN, "merge-base", "--is-ancestor", "eaee04a4",
                           CFG["freeze"]["resgx545"]])
    assert head.returncode == 0          # resgx545 r46-n3k2: r46-n3k eaee04a4 plus K11 (PAD)
    assert CFG["freeze"]["resgx545"] != subprocess.run(
        ["git", "-C", MAIN, "rev-parse", "eaee04a4"], capture_output=True, text=True).stdout.strip()
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


def test_each_land_stage_is_its_twin_byte_for_byte_but_the_names():
    """Design §11.4: LFK, LFK2, LFKP are round 45's LF2 stage, LTK its LT, R, P, R2, P2 N5-N8's:
    the table (names, the N3j/N3k word aside) and the session.toml stage line equal the twin's."""
    for name, arm, keys, jobs in PLAN:
        if name not in TWIN:
            continue
        sess, twin = TWIN[name]
        d = os.path.join(C29, sess)
        if not os.path.isdir(d):
            import pytest
            pytest.skip(f"{d} is not here")
        mine = open(os.path.join(KP, "tables", name + ".txt")).read()
        theirs = open(os.path.join(d, "tables", twin + ".txt")).read()
        norm = (lambda t, n: re.sub(r"N3[jk] row \w+ \(closing29/n3[jk]/design.md\)", "ROW",
                                    t.replace(f"{n}1-a|", "NAME|").replace(f"#stage {n}\n",
                                                                          "#stage NAME\n")
                                    .replace(f"# {n}: ", "# NAME: ")))
        assert norm(mine, name) == norm(theirs, twin), name
        other = tomllib.loads(open(os.path.join(d, "session.toml")).read())["stages"][twin]
        assert CFG["stages"][name] == other, name


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
    import kitscore
    assert callable(kitscore.kc_pad)              # K11 at the frozen commit
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


def lfk(x):
    return {f"{x}-SA": "held", f"{x}-E12": "held", f"{x}-PAGE0": "failed", f"{x}-M1": "held",
            f"{x}-OTHER": "printed", f"{x}-SERVE": "failed"}


def rr(x):
    return {f"{x}-WRITE": "held", f"{x}-LOW": "held", f"{x}-SA0": "failed",
            f"{x}-OTHER": "printed", f"{x}-SERVE": "failed", f"{x}-E12": "held",
            f"{x}-SUM": "failed"}


def pp(x):
    return {f"{x}-WRITE": "held", f"{x}-UNMAP": "held", f"{x}-MAPPED": "failed",
            f"{x}-OTHER": "printed", f"{x}-E12": "held", f"{x}-SUM": "failed"}


# design §4.2, §4.8, §4.9 and §11.4, frozen predictions as written (held, failed, printed)
WANT = {
    "W": {"W-SA1": "held", "W-SA13": "held", "W-QUIET": "held", "W-FAULT": "failed"},
    "LFK": lfk("LFK"), "LFK2": lfk("LFK2"), "LFKP": lfk("LFKP"),
    "LTK": {"LTK-SA": "held", "LTK-E12": "held", "LTK-PAGE0": "failed", "LTK-SA1": "held",
            "LTK-PAST": "failed", "LTK-SERVE": "failed"},
    "R": rr("R"), "R2": rr("R2"), "P": pp("P"), "P2": pp("P2"),
}
P0, PM1, PQ0, PL4, PT = ("cid15 page 0x00000000", "cid15 page 0x005d1000",
                         "cid15 page 0x005d2000", "cid15 page 0x04400000",
                         "cid15 page 0x02400000")
PSR, PSP = "cid15 page 0x36404000", "cid15 page 0x64008000"
# the words and rules as the design's tables write them (quantity: {outcome: value})
VALUES = {
    "LFK": {"postsa1": {"LFK-SA": "0x005d1000"}, "sa02kind": {"LFK-SA": "@in:LF"},
            "postsa12": {"LFK-E12": "@V0"},
            "j2fault": {"LFK-PAGE0": P0, "LFK-M1": PM1, "LFK-OTHER": f"@faultnotin:{P0},{PM1}"},
            "j2": {"LFK-PAGE0": "notdone", "LFK-M1": "notdone", "LFK-SERVE": "done"}},
    "LTK": {"postsa1": {"LTK-SA": "0x02400000"}, "sa02kind": {"LTK-SA": "@in:TRIPLE"},
            "postsa12": {"LTK-E12": "@V0"},
            "j2fault": {"LTK-PAGE0": P0, "LTK-SA1": PT, "LTK-PAST": f"@notin:{P0},{PT}"}},
    "R": {"postsa0": {"R-WRITE": "0x04400000"}, "postsa1": {"R-WRITE": "0x005d1000"},
          "postsa12": {"R-E12": "@V0"},
          "j2fault": {"R-LOW": PM1, "R-SA0": PL4, "R-SUM": PSR,
                      "R-OTHER": f"@faultnotin:{PM1},{PL4},{PSR}"}},
    "P": {"postsa0": {"P-WRITE": "@V0"}, "postsa1": {"P-WRITE": "0x005d2000"},
          "postsa2": {"P-WRITE": "@V2"}, "postsa12": {"P-E12": "@V0"},
          "j2fault": {"P-UNMAP": PQ0, "P-MAPPED": f"@notin:{PQ0}", "P-SUM": PSP,
                      "P-OTHER": f"@faultnotin:{PQ0},{PSP}"}},
}
for _x in ("LFK2", "LFKP"):
    VALUES[_x] = {q: {k.replace("LFK", _x): v for k, v in d.items()}
                  for q, d in VALUES["LFK"].items()}
VALUES["R2"] = {q: {x.replace("R-", "R2-"): v for x, v in d.items()} for q, d in VALUES["R"].items()}
VALUES["P2"] = {q: {x.replace("P-", "P2-"): v for x, v in d.items()} for q, d in VALUES["P"].items()}


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
        assert ("pad" in ctl) == (st[0] == "lfkp") and ctl.get("pad", "ok") == "ok"
        # no control reads the page's cmd word or a later job's slot (the H3 slip, E1176)
        assert not [q for q in ctl if q in ("res:0x1", "res:0x44", "res:0x45")]
        for q, vs in VALUES.get(st[1], {}).items():
            for x, v in vs.items():
                assert p[q][x] == v, (st[0], q, x, p[q].get(x))
