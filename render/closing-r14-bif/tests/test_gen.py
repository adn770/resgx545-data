# SPDX-License-Identifier: MIT
"""test_gen.py: r14-bif's generated tables are current, every row carries the flags and knob words
its premise needs (E934), the argv twin (mock/world.py) takes every row as t14 would, and the
frozen constants agree with the kept records they come from (E1029's zb-c-id and zb-c-off, E965's
tri-c-depth and its kernel PTE line)."""
import os
import re
import shlex
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "kit", "score", "mock"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import pins  # noqa: E402
import rf as R  # noqa: E402
import world  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
ROWS = K.table(KP, "refill")
R13Z = "data:render/closing-r13-zls/out/20261113-213117/zbase/"
R9F = "data:render/closing-r9-faults/out/20261113-084720/tri2/"


def argv(row):
    return shlex.split(row["args"].replace('"$W"', "/w"))


def opt(a, name):
    return a[a.index(name) + 1] if name in a else None


def test_generated_files_are_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout


def test_rows_and_order():
    assert [r["name"] for r in ROWS] == ["rf-c-plain", "rf-c-depth", "rf-c-unread", "rf-cc-keep",
                                         "rf-cc-refill", "rf-nc-refill"]
    assert all(r["tool"] == "t14" and r["risk"] == "safe" for r in ROWS)
    assert {r["name"] for r in ROWS if r["set"] == "control"} == {"rf-c-plain", "rf-c-depth",
                                                                   "rf-c-unread"}
    head = open(os.path.join(KP, "tables/refill.txt")).read().splitlines()[:2]
    assert head == ["#stage refill", "#limit 0"]
    assert list(CFG["stages"]) == ["refill"]


def test_every_row_has_its_premise_flags():
    for row in ROWS:
        a = argv(row)
        assert a[:3] == ["tri", "-n", "2"], row["name"]
        assert "--depth" in a and "--depth-store" in a and opt(a, "--depth-dump") == "/w"
        if row["name"] == "rf-c-plain":
            continue
        # E1029's form: the store holds the load (test never), every buffer at its address
        for w in ("--keep-going", "--tri-full"):
            assert w in a, (row["name"], w)
        assert opt(a, "--poke") == "blk:1=0x00000200" and opt(a, "--depth-pages") == "20"
        assert opt(a, "--depth-fill") == "index" and opt(a, "--depth-store-fill") == "0x3e800000"
        assert opt(a, "--width") == "64" and opt(a, "--height") == "32"
        assert "expectdiff" in row["knobs"], row["name"]
        refill = opt(a, "--refill")
        assert refill in (None, f"2:depth={R.V:#010x}")
        knob = "dbg:vm_pte_flags=0x8" in row["knobs"]
        assert knob == ("dbg:vm_pte_addr=0x3e001000" in row["knobs"])
        want = {"rf-c-depth": (False, None), "rf-c-unread": (True, True), "rf-cc-keep": (True, None),
                "rf-cc-refill": (True, True), "rf-nc-refill": (False, True)}[row["name"]]
        assert (knob, refill and True) == want, row["name"]
        if row["name"] == "rf-c-unread":
            assert opt(a, "--depth-ctl") == "0x0017100c" and opt(a, "--depth-ctl-next") == "0x0017500e"
        else:
            assert opt(a, "--depth-ctl") == "0x0017500e" and "--depth-ctl-next" not in a


def test_knob_values_are_declared():
    for row in ROWS:
        for w in row["knobs"]:
            if w.startswith("dbg:"):
                k, v = w[4:].split("=")
                assert v in CFG["knobs"][k]["values"], w
    assert CFG["knobs"]["vm_pte_flags"]["default"] == "0"
    assert CFG["outdir_opts"] == ["--depth-dump"]


def test_the_twin_takes_every_row_and_refuses_what_t14_refuses(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_DBGREAL", str(tmp_path))
    for row in ROWS:
        a = argv(row)
        assert world.answer("t14", a, {"model"})["rc"] in (0, 1), row["name"]
    base = argv(ROWS[4])
    bad = [
        base[:-2] + ["--refill", "1:depth=0x3f400000"],      # K below 2
        base[:-2] + ["--refill", "3:depth=0x3f400000"],      # K past -n
        base[:-2] + ["--refill", "2:stencil=0x3f400000"],    # stencil without --stencil
        base[:-2] + ["--refill", "2:zbuf=0x3f400000"],       # no such buffer
        base[:-2] + ["--refill", "2:depth=0x100000000"],     # not 32-bit
        [x for x in base if x != "--depth"],                 # depth options without --depth
        ["tri", "-n", "1"] + base[3:] + ["--depth-ctl-next", "0x0017500e"],
        base + ["--stencil"],
    ]
    for b in bad:
        assert world.answer("t14", b, {"model"}) == world.USAGE, b


def test_the_tool_source_takes_the_refill_option():
    src = pins.blob("resgx545:userspace/libsgxfive/tools/sgxfive-test.c").decode()
    assert '"--refill"' in src and 'printf("refill: render %u buf %s value 0x%08x\\n"' in src
    assert 'zbuf_fill(&z.depth, &o->depth_fill)' in src and '"rd:12=0x%llx"' in src
    assert ".depth_ctl = 0x0017100c" in src


def test_frozen_constants_match_the_kept_records():
    idd = R.dwords(pins.blob(KEPT := R.KEPT["id"]))
    off = R.dwords(pins.blob(R.KEPT["off"]))
    assert KEPT.startswith(R13Z)
    assert R.store_class(idd) == "F" and R.store_class(off) == "clear"
    for n in ("zb-c-id", "zb-c-off"):
        t = pins.blob(R13Z + n + ".txt.gz").decode()
        assert "depth: 0x3e001000 20 pages, fill index, base 0x3e000000," in t
        assert "depth store: 0x3e015000 20 pages, fill 0x3e800000" in t
    assert "control 0x0017500e" in pins.blob(R13Z + "zb-c-id.txt.gz").decode()
    assert "control 0x0017100c" in pins.blob(R13Z + "zb-c-off.txt.gz").decode()
    t = pins.blob(R9F + "tri-c-depth.txt.gz").decode()
    m = re.search(r"^depth store #1: \d+ dwords, (\d+) changed", t, re.M)
    assert int(m.group(1)) == R.PLAIN_CHANGED and "tri: 1 renders ok" in t
    assert "depth store: 0x3e015000 20 pages" in t
    # the kernel's PTE line hook_check and the scorer read (E965's tri-edm-dld)
    k = pins.blob(R9F + "tri-edm-dld.dmesg.gz").decode()
    assert re.search(r"vm_map 0x3e001000 \+0x14000: PTE flags 0x10 \(debugfs vm_pte_flags\)", k)


def test_the_twin_store_is_e1029s_store(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_DBGREAL", str(tmp_path))
    for n, key in (("rf-c-depth", "id"), ("rf-c-unread", "off")):
        a = world.answer("t14", argv(next(r for r in ROWS if r["name"] == n)), {"model"})
        assert a["files"]["/w/depth-store.1.bin"] == pins.blob(R.KEPT[key]), n


def test_every_pin_read_is_frozen():
    test_frozen_constants_match_the_kept_records()
    test_the_tool_source_takes_the_refill_option()
    frozen = set(CFG["freeze"]["pins"])
    assert pins.READ <= frozen, pins.READ - frozen
