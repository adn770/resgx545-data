# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin and the library-mock replay. Every row against the plans
(closing9/seeds/exp-seeds-r9.md section 2, S9-k2, decision S-6 (a); closing9/rank/rank-round9.md
R9c-G, decision X-4 (a)) and against the real tool's source built on libsgxfive's in-process mock
(debug/libmock, TOOLSRC.sha256):

- the plans' rows: xf2 = E946's nine rows token for token, then the three new; tri2 = seven rows;
  bif = 14 rows of E457's form; 33 jobs; the stages in the order xf2, tri2, bif;
- every knob word a value session.toml allows; #limit = the stage's expectfault rows that are
  not controls, plus one (S-6 (a)); every expectfault row that is not a control has `after` or
  takes the kit's strict health for its fault; a knob-free control last in xf2's E946 block,
  tri2 and bif;
- every row's argv through the library mock: never `job: rejected` and never a usage refusal; rc
  0 and `job: ok` where the mock can run the job (tri --depth with its ZLS pokes in a file);
- the addresses: the tool's own --print-addrs, --emit-scene, `layout: fb` and `depth` lines give
  the mappings mock/world.py and gen/make.py name;
- the generator current, the tool source's hash at its commit, the pinned hardware outputs hold
  the control values the predictions freeze, the buffer layout is the pinned one."""
import gzip
import hashlib
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
sys.path.insert(0, os.path.join(KP, "score"))
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402
import make as G  # noqa: E402

CONF = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
DATA = CONF["freeze"]["data"]
LIB = os.path.join(KP, "debug", "libmock", "sgxfive-test")
PLAN = {
    "xf2": ["xf-c-fill", "xf-c-copy", "xf-c-addr", "xf-c-ro", "xf-wo-fill", "xf-cc-copy",
            "xf-edm-fill", "xf-wo-copy", "xf-c-end", "xf-wo-fill-low", "xf-wo-fill-64", "xf-edm-copy"],
    "tri2": ["tri-c", "tri-c-depth", "tri-woedm-fb", "tri-edm-dst", "tri-edm-dld", "tri-wo-dst",
             "tri-c-end"],
    "bif": ["bif-c0", "bif-c9", "bif-1213", "bif-1214", "bif-1314", "bif-12to14", "bif-h32",
            "bif-most", "bif-most-r2", "bif-most-3r", "bif-c-ovf", "bif-most-ovf", "bif-c1",
            "bif-c0-end"],
}
R8K2 = "render/closing-r8-k2/"


def lib(*args, cwd=None):
    env = dict(os.environ, SGXFIVE_KPOKE=os.path.join(cwd or "/nonexistent", "kpoke"))
    if cwd:
        open(env["SGXFIVE_KPOKE"], "w").close()
    return subprocess.run([LIB, "--mock", *args], capture_output=True, text=True, timeout=60, cwd=cwd,
                          env=env)


def rows(stage):
    return K.table(KP, stage)


def dbg(row):
    return dict(k[4:].split("=", 1) for k in row["knobs"] if k.startswith("dbg:"))


def test_rows_are_the_plans():
    assert list(CONF["stages"]) == ["xf2", "tri2", "bif"]
    for s, names in PLAN.items():
        assert [r["name"] for r in rows(s)] == names
    assert sum(len(v) for v in PLAN.values()) == 33
    # E946's nine rows token for token: the same knob words and arguments as r8-k2 ran them
    r8 = KD.git_show("data", DATA, R8K2 + "out/20261113-032428/xf/cases.tsv").decode().splitlines()
    ran = {ln.split("\t")[0]: ln.split("\t") for ln in r8[1:]}
    for r in rows("xf2")[:9]:
        if r["name"] in ran:
            assert ran[r["name"]][4] == " ".join(r["knobs"]) and ran[r["name"]][6] == r["args"], r["name"]
    assert len([n for n in ran if n in PLAN["xf2"]]) == 8        # xf-c-end did not run in E946
    want = {
        "xf-wo-fill-low": ("fill-dst-low", G.WO, "fill --width 64 --height 16 --y 16"),
        "xf-wo-fill-64": ("fill-dst-64", G.WO, "fill --width 64 --height 64"),
        "xf-edm-copy": ("copy-src", G.EDMPROT, "copy --print-addrs"),
        "tri-woedm-fb": ("tri-fb", G.WO | G.EDMPROT, "tri"),
        "tri-edm-dst": ("zst", G.EDMPROT, "tri --depth --depth-store"),
        "tri-edm-dld": ("zbuf", G.EDMPROT, "tri --depth --depth-store"),
        "tri-wo-dst": ("zst", G.WO, "tri --depth --depth-store"),
    }
    got = {r[1]: (r[5], r[6], G.ARGS[r[4]]) for r in G.QROWS if r[2] in ("heldout", "reading")}
    assert got == want
    assert G.pte("copy-src", G.EDMPROT) == 0x14 and G.pte("tri-fb", G.WO | G.EDMPROT) == 0x12
    masks = {r[0]: r[2] for r in G.BROWS}
    assert masks["bif-c9"] == 1 << 9 and masks["bif-c1"] == 1 and masks["bif-c0"] == 0
    for r in G.BROWS:
        if r[1] != "control":
            assert not r[2] & 0x201 and len(G.buffers(r[2])) >= 2, r[0]   # held out: never 0 or 9


def test_knobs_limit_and_order():
    vals = {k: set(d["values"]) for k, d in CONF["knobs"].items()}
    assert {k: d["default"] for k, d in CONF["knobs"].items()} == {
        "vm_pte_flags": "0", "vm_pte_addr": "0", "alias_skip": "0", "render_pb_pages": "0x422"}
    assert all(int(v, 16) & ~0x1A == 0 for v in vals["vm_pte_flags"])     # SGXFIVE_VM_PTE_KNOB
    assert all(int(v, 16) < 1 << 16 for v in vals["alias_skip"])          # ids 0-15 (fork 42)
    for s in PLAN:
        head = [ln for ln in open(os.path.join(KP, "tables", s + ".txt")) if ln.startswith("#limit")]
        ef = [r for r in rows(s) if r["set"] != "control" and "expectfault" in r["knobs"]]
        assert head == [f"#limit {len(ef) + 1}\n"], s                      # S-6 (a), E946's slip
        for r in rows(s):
            for k, v in dbg(r).items():
                assert v in vals[k], (r["name"], k, v)
            if r["set"] != "control":
                assert "expectfault" in r["knobs"] and "after" in r["knobs"], r["name"]
            if s != "bif" and dbg(r).get("vm_pte_flags", "0") != "0":
                assert "expectdiff" in r["knobs"]
        last = rows(s)[8] if s == "xf2" else rows(s)[-1]     # xf2: E946's block ends with xf-c-end
        assert last["set"] == "control" and dbg(last).get("vm_pte_flags", "0") == "0" \
            and dbg(last).get("alias_skip", "0") == "0"
    assert {r["name"] for r in rows("xf2") if r["set"] == "control" and "expectfault" in r["knobs"]} == {"xf-c-ro"}
    assert LIMIT_PLAN == {s: G.LIMIT[s] for s in PLAN}
    # the overflowing scene takes render_pb_pages 0x23, nothing else does
    for r in rows("bif"):
        assert ("--keep-overflow" in r["args"]) == (dbg(r).get("render_pb_pages") == "0x23")


# xf2: 7 expectfault rows (E946's four, the three new) + 1; tri2: 4 + 1; bif: 9 + 1
LIMIT_PLAN = {"xf2": 8, "tri2": 5, "bif": 10}


def test_every_row_runs_on_the_library_mock(tmp_path):
    assert os.path.exists(LIB), "debug/libmock not built (bash tests/run_all.sh)"
    for s in PLAN:
        for r in rows(s):
            a = shlex.split(r["args"])
            d = tmp_path / r["name"]
            d.mkdir()
            pre = ["--mock-pb-pages=0x23"] if dbg(r).get("render_pb_pages") == "0x23" else []
            p = lib(*pre, *a, cwd=str(d))
            assert "rejected" not in p.stdout and "usage" not in p.stderr, (r["name"], p.stdout, p.stderr)
            assert p.returncode == 0, (r["name"], p.returncode, p.stderr)
            if a[0] == "isolation":
                checks = re.findall(r"^(PASS|FAIL) ", p.stdout, re.M)
                assert len(checks) == 9 and set(checks) == {"PASS"}, p.stdout
            elif pre:
                assert "tri: 0 of 2 renders ok, 2 overflowed" in p.stdout, p.stdout
            else:
                assert re.search(r"^job: ok$", p.stdout, re.M), (r["name"], p.stdout)
                assert set(re.findall(r"^diff: (\d+) of", p.stdout, re.M)) == {"0"}, (r["name"], p.stdout)


def test_the_world_is_as_strict_as_the_tool():
    w = KD.world()
    assert w.answer("t4", ["tri", "--frobnicate"], {"model"})["rc"] == 2
    assert w.answer("t4", ["fill", "--print-addrs"], {"model"})["rc"] == 2
    assert w.answer("t4", ["copy", "--width"], {"model"})["rc"] == 2


def test_the_addresses_are_the_tools(tmp_path):
    w = KD.world()
    p = lib("copy", "--print-addrs", cwd=str(tmp_path))
    m = re.search(r"^copy: source at (0x[0-9a-f]+), destination at (0x[0-9a-f]+)$", p.stdout, re.M)
    cm = w.maps(["copy", "--print-addrs"])
    assert (int(m[1], 16), int(m[2], 16)) == (cm[1][0], cm[2][0]) == (G.MAPS["copy-src"][0], cm[2][0])
    assert cm[1][1] == G.MAPS["copy-src"][1] and cm[1][2] is True
    for args, key in (([], "fill-dst"), (["--width", "64", "--height", "16", "--y", "16"], "fill-dst-low"),
                      (["--width", "64", "--height", "64"], "fill-dst-64")):
        scene = tmp_path / f"{key}.json"
        lib("fill", *args, "--emit-scene", str(scene), cwd=str(tmp_path))
        sc = json.loads(scene.read_text())
        fm = w.maps(["fill", *args])
        assert int(sc["target"]["base"], 16) == fm[1][0] == G.MAPS[key][0]
        assert sc["target"]["pages"] * 0x1000 == fm[1][1] == G.MAPS[key][1]
        assert fm[1][4] == G.MAPS[key][4], key          # the page of the last pixel written
    p = lib("tri", cwd=str(tmp_path))
    fb = int(re.search(r"^layout: fb (0x[0-9a-f]+)$", p.stdout, re.M)[1], 16)
    assert fb == w.maps(["tri"])[1][0] == G.MAPS["tri-fb"][0] and w.maps(["tri"])[1][1] == G.MAPS["tri-fb"][1]
    p = lib("tri", "--depth", "--depth-store", cwd=str(tmp_path))
    z = re.search(r"^depth: (0x[0-9a-f]+) (\d+) pages, .*control 0x0017100c$", p.stdout, re.M)
    zs = re.search(r"^depth store: (0x[0-9a-f]+) (\d+) pages", p.stdout, re.M)
    fb = int(re.search(r"^layout: fb (0x[0-9a-f]+)$", p.stdout, re.M)[1], 16)
    dm = w.maps(["tri", "--depth", "--depth-store"])
    assert (int(z[1], 16), int(z[2]) * 0x1000) == dm[1][:2] == G.MAPS["zbuf"][:2]
    assert (int(zs[1], 16), int(zs[2]) * 0x1000) == dm[2][:2] == G.MAPS["zst"][:2]
    assert fb == dm[3][0] == int(G.CTL["tri-depth"]["fb"][0], 16)
    kp = (tmp_path / "kpoke").read_text()            # rd:12 the load base, rd:13 the store's
    assert "rd:11=0x0017100c" in kp and "rd:12=0x1000" in kp and "rd:13=0x15000" in kp
    # the clearing control has the load bit (1) clear: the depth buffer row is a reading
    assert not 0x0017100C & 0x2


def test_the_reference_hashes_of_the_new_fill_sizes(tmp_path):
    import importlib
    S = importlib.import_module("score")
    assert S.__file__ == os.path.join(KP, "score", "score.py")
    for key, args in (("fill-low", G.ARGS["fill-low"]), ("fill-64", G.ARGS["fill-64"])):
        p = lib(*args.split(), cwd=str(tmp_path))
        assert f"hash {S.REF_HASH[key]}" in p.stdout
    p = lib("fill", cwd=str(tmp_path))     # the library mock's fill hash is the laptop's (r7-rp)
    assert f"hash {G.CTL['fill']['hash'][0]}" in p.stdout


def test_generator_is_current():
    assert subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"]).returncode == 0


def test_tool_source_hash_at_its_commit():
    want, spec = open(os.path.join(KP, "TOOLSRC.sha256")).read().split()
    rev, path = spec.split(":", 1)
    assert hashlib.sha256(KD.git_show("resgx545", rev, path)).hexdigest() == want
    t4 = CONF["tools"]["t4"]
    assert t4["source_sha256"] == want and t4["source"] == spec and t4["built_from"] == spec


def test_pinned_hardware_outputs_hold_the_frozen_controls():
    pins = CONF["freeze"]["pins"]
    srcs = {v[1].split(" ")[0] for c in (G.CTL, G.BCTL) for d in c.values() for v in d.values()
            if v[1].startswith("data:")}
    for s in srcs | {G.SRC_LAYOUT}:
        assert s in pins, s

    def text(src):
        b = KD.git_show("data", DATA, src[5:])
        return (gzip.decompress(b) if src.endswith(".gz") else b).decode()
    fill, tri = text(G.SRC_FILL), text(G.SRC_TRI)
    assert f"hash {G.CTL['fill']['hash'][0]}" in fill and "diff: 0 of 2048" in fill
    assert f"hash {G.CTL['tri']['hash'][0]}" in tri and f"layout: fb {G.CTL['tri']['fb'][0]}" in tri
    assert f"hash {G.CTL['copy']['hash'][0]}" in text(G.SRC_COPY)
    jobs = text(G.SRC_RO)
    assert "PASS read-only-faults" in jobs and "BIF fault 0x80020 at 0x3e200002" in jobs
    s1 = text(G.SRC_S1)
    assert "hash 0x99385a04ee01c585" in s1 and f"hash {G.BCTL['plain']['hash2'][0]}" in s1 \
        and "tri: 2 renders ok" in s1
    s1b = text(G.SRC_S1B)
    assert "tri: 0 of 2 renders ok, 2 overflowed" in s1b
    assert re.findall(r"hash (0x[0-9a-f]+)", s1b) == [G.BCTL["ovf"]["hash"][0], G.BCTL["ovf"]["hash2"][0]]
    assert "BIF fault 0x90400 at 0x32004001" in text(G.SRC_E457)
    assert "BIF fault 0x91000 at 0x3000b021" in text(G.SRC_C1)
    lay = json.loads(text(G.SRC_LAYOUT))
    assert [int(lay["addr"][str(i)], 16) for i in range(15)] == G.BUF
    w = KD.world()
    assert w.BUF == G.BUF
