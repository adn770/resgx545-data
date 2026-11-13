# SPDX-License-Identifier: MIT
"""r8-ldpm: the generator is current, session.toml declares what the tables use, the rows are the
plan's (161 jobs, safe class, the argv twin of R7-dpm's repeated rows), the OL7 copies are the
leftovers' frozen files, and the program binaries are the pinned or re-assembled ones."""
import hashlib
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tomllib

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "kit"), str(KP / "mock")]
import plan as PL  # noqa: E402
import kitscore as K  # noqa: E402
import world as WD  # noqa: E402

TREE = pathlib.Path.home() / "src/resgx545"
DATA = pathlib.Path.home() / "src/resgx545-data"
LEFT = KP.parent / "leftovers"
CFG = tomllib.loads((KP / "session.toml").read_text())
R7 = DATA / "render/closing-r7-dpm/out"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def test_generator_current():
    assert subprocess.run([sys.executable, str(KP / "gen/plan.py"), "--check"]).returncode == 0


def test_job_counts_and_order():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES)
    assert {s: len(T[s]) for s in T} == {"a0": 6, "sp": 20, "m6": 69, "v": 14, "f9": 18, "k": 25, "u": 9}
    assert sum(len(v) for v in T.values()) == 161


def test_safe_class_only():
    for st in PL.STAGES:
        txt = (KP / "tables" / f"{st}.txt").read_text()
        assert "#limit 0" in txt
        for r in K.table(str(KP), st):
            assert r["risk"] == "safe"
            assert "expectfault" not in r["knobs"]
            assert not re.search(r"--kpoke|--fault|--poke", r["args"])


def test_session_toml_declares_the_tables():
    T = PL.tables()
    assert CFG["extra_knobs"] == PL.extra_knobs(T)
    assert CFG["knobs"]["render_pb_pages"]["values"] == PL.knob_values(T)
    assert CFG["knobs"]["render_pb_pages"]["default"] == "0x422"
    assert CFG["tools"]["rt"]["wraps"] is True


def test_every_row_runs_t4_under_regtimeline_with_r5_registers():
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            a = shlex.split(r["args"])
            assert r["tool"] == "rt" and a[:5] == ["0", "0.3", PL.RT, "--", "$HOME/sgxfive-test-rgn4"]
            assert sum(k.startswith("dbg:render_pb_pages=") for k in r["knobs"]) == 1


def test_argv_twin_of_r7_rows():
    """a0's rows, v's control and u's control run R7-dpm's commands (paths aside)."""
    import csv
    want = {"a0-cal-2048": ("a1/s-a0", "a0-cal-2048"), "a0-cal-2048f": ("a1/s-a0", "a0-cal-2048f"),
            "a0-c4-b5": ("a1/s-a0", "a0-c4-b5"), "a0-c4-b6": ("a1/s-a0", "a0-c4-b6"),
            "a0-t-s3m6": ("a1/s-a0", "a0-t-s3m6"), "a0-qf-0xa2": ("a1/s-a0", "a0-qf-0xa2"),
            "v-c4": ("a1/s-v", "v-cal-c4"), "u-c-s22": ("a1/s-b", "b-cal-s22"),
            "m6-c-0x1c2": ("a1/s-m", "m-r6-0x1c2"), "m6-c-0x1c3": ("a1/s-m", "m-r6-0x1c3"),
            "sp-c-0xe8": ("b1/s-k", "k-b3"), "sp-c-0xe9": ("b1/s-k", "k-s4p1")}
    rows = {r["name"]: r for st in PL.STAGES for r in K.table(str(KP), st)}
    norm = lambda a: re.sub(r'"\$W/(dump|words)"', '"$W"', a.replace('"$S/p1139-green.bin"', '"$S/bins/p1139-green.bin"'))  # noqa: E731
    for mine, (stg, theirs) in want.items():
        r7 = {x["name"]: x for x in csv.DictReader(open(R7 / stg / "cases.tsv"), delimiter="\t")}[theirs]
        cmd = rows[mine]["args"].split(" -- ", 1)[1].split(" ", 1)[1]
        r7a = norm(r7["args"])
        if mine == "u-c-s22":                    # R7's dumped calibration: the dump left out here
            r7a = r7a.replace(' --dump-render "$W"', "")
        assert cmd == r7a, mine
        P = next(k for k in rows[mine]["knobs"] if k.startswith("dbg:")).split("=")[1]
        assert int(P, 16) == int(r7["P"], 16), mine


def test_the_world_takes_every_row():
    """The strict fake answers every row's argv (no usage): the tool takes every option used."""
    os.environ.setdefault("FAKE_DBGREAL", "/nonexistent")
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            a = shlex.split(r["args"].replace("$HOME", "/h").replace("$W", "/w").replace("$S", str(KP)))
            assert WD.answer("rt", a, {"model"}) is None, r["name"]
            got = WD.answer("t4", a[5:], {"model"})
            assert got is not None and got.get("rc") != 2, (r["name"], got)
    assert WD.answer("t4", ["probe", "--tri", "pixel", "--kpoke", "x", str(KP / "bins/p1139-green.bin")],
                     {"model"})["rc"] == 2


def test_ol7_copies_are_the_frozen_leftovers():
    for f in (KP / "gen/ol7").iterdir():
        if (LEFT / f.name).exists():
            assert sha(f) == sha(LEFT / f.name), f.name
    if (LEFT / "ol7_tables.json").exists():
        assert sha(KP / "gen/ol7_tables.json") == sha(LEFT / "ol7_tables.json")
    frz = (KP / "gen/ol7/FREEZE-ol7c.sha256").read_text()
    assert sha(KP / "gen/ol7_tables.json") in frz
    for f in ("ol7lib.py", "ol7_b_multikick.py", "ol7_c_tables.py"):
        assert f"{sha(KP / 'gen/ol7' / f)}  {f}" in frz


def test_p1139_is_the_pinned_r7_program():
    c = CFG["freeze"]["data"]
    b = subprocess.run(["git", "-C", str(DATA), "show", f"{c}:render/closing-r7-dpm/bins/p1139-green.bin"],
                       capture_output=True).stdout
    assert b == (KP / "bins/p1139-green.bin").read_bytes()


def test_vtx_coord4_is_the_pinned_template():
    c = CFG["freeze"]["resgx545"]
    b = subprocess.run(["git", "-C", str(TREE), "show", f"{c}:probes/tsp/templates/vtx_coord4.s"],
                       capture_output=True).stdout
    assert b == (KP / "asm/vtx_coord4.s").read_bytes()


def test_vertex_programs_assemble_and_write_every_output(tmp_path):
    """usse-asm gives the binaries from asm/ again; sgx-sim runs vtx_coord8 to its emit with o0 to
    o11 written (o4..o11 the extra outputs P3 says the default program leaves unwritten)."""
    asm = TREE / "tools/usse-asm/usse-asm"
    sim = TREE / "target/release/sgx-sim"
    if not asm.exists() or not sim.exists():
        import pytest
        pytest.skip("usse-asm or sgx-sim not built")
    for p in ("vtx_coord4", "vtx_coord8"):
        out = tmp_path / f"{p}.bin"
        subprocess.run([str(asm), "-o", str(out), str(KP / "asm" / f"{p}.s")], check=True)
        assert out.read_bytes() == (KP / "bins" / f"{p}.bin").read_bytes()
    r = subprocess.run([str(sim), "--task", "vertex", "--set", "pa0=0x3f000000", "--set", "pa1=0xbf000000",
                        "--set", "pa2=0x3e000000", "--set", "pa3=0x3f800000", str(KP / "bins/vtx_coord8.bin")],
                       capture_output=True, text=True)
    got = dict(re.findall(r"^(o\d+) = (0x[0-9a-f]+)$", r.stdout, re.M))
    assert {f"o{i}" for i in range(12)} <= set(got)
    assert (got["o4"], got["o5"], got["o6"], got["o7"]) == ("0x3f000000", "0xbf000000", "0x3e800000", "0x3f000000")
    assert (got["o8"], got["o9"], got["o10"], got["o11"]) == ("0x3f000000", "0xbf000000", "0x3f400000", "0x3f800000")
    assert "emit emitvcbvtx" in r.stdout
