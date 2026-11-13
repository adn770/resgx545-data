# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin and the library-mock replay. Every row against the plan
(closing8/rank/rank-round8.md section 3, K2; decisions R8-5, R8-6) and against the real tool's
source built on libsgxfive's in-process mock (debug/libmock, TOOLSRC.sha256):

- the plan's rows: WO on a fill's destination and on the copy's source (RO|WO, R8-6), CACHED on
  the copy's source, EDMPROT on a fill's destination, the triangle's colour target and its vertex
  page; knob-free controls with known hashes and the READONLY fault control; 16 jobs, the
  fault-risky rows after the controls, a knob-free control last in each stage;
- every knob word a value session.toml allows, one flag a row, the address a mapping's first page;
- every row's argv through the library mock: rc 0 and `job: ok` (isolation: every check PASS),
  never `job: rejected` (r8-geo lost 23 rows to that) and never a usage refusal;
- the addresses: the tool's own --print-addrs, `layout: fb` and --emit-scene give the mappings
  mock/world.py and gen/make.py name;
- the generator current, the tool source's hash at its commit, the pinned hardware outputs hold
  the control values the predictions freeze."""
import gzip
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402
import make as G  # noqa: E402

CONF = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
LIB = os.path.join(KP, "debug", "libmock", "sgxfive-test")
PLAN = {
    "xf": ["xf-c-fill", "xf-c-copy", "xf-c-addr", "xf-c-ro", "xf-wo-fill", "xf-cc-copy",
           "xf-edm-fill", "xf-wo-copy", "xf-c-end"],
    "tri": ["tri-c", "tri-wo-fb", "tri-cc-gen", "tri-edm-fb", "tri-edm-gen", "tri-wo-gen",
            "tri-c-end"],
}


def lib(*args, cwd=None):
    return subprocess.run([LIB, "--mock", *args], capture_output=True, text=True, timeout=60, cwd=cwd)


def rows(stage):
    return K.table(KP, stage)


def dbg(row):
    return dict(k[4:].split("=", 1) for k in row["knobs"] if k.startswith("dbg:"))


def test_rows_are_the_plans():
    assert list(CONF["stages"]) == ["xf", "tri"]
    for s, names in PLAN.items():
        assert [r["name"] for r in rows(s)] == names
    assert sum(len(v) for v in PLAN.values()) == 16
    want = {  # (map, flag) of every knob row, the plan's list and decision R8-6's RO|WO row
        "xf-wo-fill": ("fill-dst", G.WO), "xf-cc-copy": ("copy-src", G.CACHED),
        "xf-edm-fill": ("fill-dst", G.EDMPROT), "xf-wo-copy": ("copy-src", G.WO),
        "tri-wo-fb": ("tri-fb", G.WO), "tri-cc-gen": ("tri-gen", G.CACHED),
        "tri-edm-fb": ("tri-fb", G.EDMPROT), "tri-edm-gen": ("tri-gen", G.EDMPROT),
        "tri-wo-gen": ("tri-gen", G.WO),
    }
    got = {r[1]: (r[5], r[6]) for r in G.ROWS if r[2] != "control"}
    assert got == want
    assert G.pte("copy-src", G.WO) == G.RO | G.WO          # RO|WO: a reading row (R8-6)


def test_knobs_and_order():
    vals = {k: set(d["values"]) for k, d in CONF["knobs"].items()}
    assert {k: d["default"] for k, d in CONF["knobs"].items()} == {"vm_pte_flags": "0", "vm_pte_addr": "0"}
    for s in PLAN:
        head = [ln for ln in open(os.path.join(KP, "tables", s + ".txt")) if ln.startswith("#limit")]
        assert head == ["#limit 4\n"]
        rs = rows(s)
        assert rs[-1]["set"] == "control" and not dbg(rs[-1])
        seen_knob = False
        for r in rs:
            d = dbg(r)
            for k, v in d.items():
                assert v in vals[k], (r["name"], k, v)
            if r["set"] == "control":
                assert "expectdiff" not in r["knobs"], r["name"]
                assert ("expectfault" in r["knobs"]) == (r["args"] == "isolation"), r["name"]
                assert not seen_knob or r is rs[-1], "a control after the knob rows: " + r["name"]
                if d:
                    assert d["vm_pte_flags"] == "0"        # the address alone
                continue
            seen_knob = True
            assert {"expectfault", "expectdiff", "after"} <= set(r["knobs"]), r["name"]
            flag = int(d["vm_pte_flags"], 16)
            assert bin(flag).count("1") == 1 and flag & 0x1a == flag
            assert int(d["vm_pte_addr"], 16) in {m[0] for m in G.MAPS.values()}


def test_every_row_runs_on_the_library_mock(tmp_path):
    assert os.path.exists(LIB), "debug/libmock not built (bash tests/run_all.sh)"
    for s in PLAN:
        for r in rows(s):
            a = shlex.split(r["args"])
            p = lib(*a, cwd=str(tmp_path))
            assert "rejected" not in p.stdout and "usage" not in p.stderr, (r["name"], p.stdout, p.stderr)
            assert p.returncode == 0, (r["name"], p.returncode, p.stderr)
            if a[0] == "isolation":
                checks = re.findall(r"^(PASS|FAIL) ", p.stdout, re.M)
                assert len(checks) == 9 and set(checks) == {"PASS"}, p.stdout
            else:
                assert re.search(r"^job: ok$", p.stdout, re.M), (r["name"], p.stdout)
                assert re.search(r"^diff: 0 of \d+ pixels", p.stdout, re.M)


def test_the_world_is_as_strict_as_the_tool(tmp_path):
    w = KD.world()
    assert w.answer("t4", ["tri", "--frobnicate"], {"model"})["rc"] == 2
    assert w.answer("t4", ["fill", "--print-addrs"], {"model"})["rc"] == 2
    assert w.answer("t4", ["copy", "--width"], {"model"})["rc"] == 2


def test_the_addresses_are_the_tools(tmp_path):
    w = KD.world()
    p = lib("copy", "--print-addrs")
    m = re.search(r"^copy: source at (0x[0-9a-f]+), destination at (0x[0-9a-f]+)$", p.stdout, re.M)
    cm = w.maps(["copy", "--print-addrs"])
    assert (int(m[1], 16), int(m[2], 16)) == (cm[1][0], cm[2][0]) == (G.MAPS["copy-src"][0], cm[2][0])
    assert cm[1][1] == G.MAPS["copy-src"][1] and cm[1][2] is True
    p = lib("tri")
    fb = int(re.search(r"^layout: fb (0x[0-9a-f]+)$", p.stdout, re.M)[1], 16)
    tm = w.maps(["tri"])
    assert fb == tm[1][0] == G.MAPS["tri-fb"][0] and tm[1][1] == G.MAPS["tri-fb"][1]
    assert tm[0][:2] == G.MAPS["tri-gen"][:2]
    scene = tmp_path / "fill.json"
    lib("fill", "--emit-scene", str(scene))
    sc = json.loads(scene.read_text())
    fm = w.maps(["fill"])
    assert int(sc["target"]["base"], 16) == fm[1][0] == G.MAPS["fill-dst"][0]
    assert sc["target"]["pages"] * 0x1000 == fm[1][1] == G.MAPS["fill-dst"][1]
    assert int(sc["layout"]["stream_page"], 16) == fm[0][0] == G.MAPS["tri-gen"][0]


def test_generator_is_current():
    assert subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"]).returncode == 0


def test_tool_source_hash_at_its_commit():
    want, spec = open(os.path.join(KP, "TOOLSRC.sha256")).read().split()
    rev, path = spec.split(":", 1)
    import hashlib
    assert hashlib.sha256(KD.git_show("resgx545", rev, path)).hexdigest() == want
    # the laptop's ~/sgxfive-test-rgn4 was built from 4623753, whose libsgxfive and uapi trees are
    # this commit's (r8-lgeo's TOOLSRC.sha256 names the same source sha256)
    tree = subprocess.run(["git", "-C", KD.REPOS["resgx545"], "rev-parse", f"{rev}:userspace/libsgxfive",
                           f"4623753:userspace/libsgxfive"], capture_output=True, text=True).stdout.split()
    assert len(tree) == 2 and tree[0] == tree[1]


def test_pinned_hardware_outputs_hold_the_frozen_controls():
    data = CONF["freeze"]["data"]
    pins = CONF["freeze"]["pins"]
    for p in ("render/closing-r7-rp/out/20261112-205431/p7-rd/begin.fill1.txt.gz",
              "render/closing-r7-rp/out/20261112-205431/p7-rd/begin.health1.txt.gz",
              "texture/copy-addresses/output.txt", "render/client-jobs/output.txt"):
        assert "data:" + p in pins
    fill = gzip.decompress(KD.git_show("data", data, G.SRC_FILL[5:])).decode()
    tri = gzip.decompress(KD.git_show("data", data, G.SRC_TRI[5:])).decode()
    copy = KD.git_show("data", data, G.SRC_COPY[5:]).decode()
    jobs = KD.git_show("data", data, G.SRC_RO[5:]).decode()
    assert f"hash {G.CTL['fill']['hash'][0]}" in fill and "diff: 0 of 2048" in fill
    assert f"hash {G.CTL['tri']['hash'][0]}" in tri and f"layout: fb {G.CTL['tri']['fb'][0]}" in tri
    assert f"hash {G.CTL['copy']['hash'][0]}" in copy
    assert "copy: source at 0x3e002000, destination at 0x3e005000, a counting page before" in copy
    assert "PASS read-only-faults" in jobs and "BIF fault 0x80020 at 0x3e200002" in jobs
