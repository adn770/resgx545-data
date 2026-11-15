# SPDX-License-Identifier: MIT
"""r26-vol's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against round 26's plan 2.1: 5 controls, 19 bits x 2 w values and two
repeats, t24's options); the control programs are E567's kept programs byte for byte and every
bit program is E567's w 0 or w 1.5 program with that one word changed by that one bit; the mock's
control images are E567's kept images; the scorer on E567's kept files (ty0-3d-w0 against
ty0-3d-w15 holds H-NOVOL, against ind-t0b27 fails it; a cube control given the other w's image
FAILS) and on every world's outputs; the hooks' reader against the scorer's."""
import os
import shlex
import shutil
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import make as MK  # noqa: E402
import pins  # noqa: E402
import score as SC  # noqa: E402
import world as WO  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PY = sys.executable
COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
BITS = {"t0": (14, 15, 16, 27, 28, 29, 30), "t3": (8, 9, 10, 11, 12, 15, 18, 20, 21, 22, 27, 28)}


def table(stage):
    return [dict(zip(("name", "set", "risk", "knobs", "tool", "args"), ln.split("|", 5)))
            for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines()
            if ln and not ln.startswith("#")]


def argv(r):
    return shlex.split(r["args"].replace("$S", "/s").replace("$W", "/w"))


def kept(path):
    return pins.blob(MK.KEPT + path).decode()


def binfile(n):
    return open(os.path.join(KP, "bins", n + ".bin"), "rb").read()


def test_generator_current_and_pinned():
    assert subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"]).returncode == 0
    MK.build()
    for p in ("tx-types/bins/tx-types__1", "tx-types/bins/tx-types__4",
              "tx-types-risky/bins/tx-types-risky__4", "tx-types-risky/bins/tx-types-risky__5"):
        pins.blob(MK.RECOMP + p + ".bin")
    kept("tx-types/ind-t0b27.txt.gz")
    kept("tx-types/ind-t0b30.txt.gz")
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]
    assert sorted(os.listdir(os.path.join(KP, "bins"))) == sorted(
        r["name"] + ".bin" for st in ("vc", "vb") for r in table(st))


def test_stages_rows_and_order():
    assert list(CFG["stages"]) == ["vc", "vb"]
    assert CFG["stages"]["vc"].get("on_stop") == "end" and not CFG["stages"]["vc"].get("gate")
    assert CFG["stages"]["vb"].get("gate") is True and SC.GATES == {"vb": "vc"}
    for st in ("vc", "vb"):
        head = open(os.path.join(KP, "tables", st + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {st}", "#limit 0"]
    assert [r["name"] for r in table("vc")] == ["c-w0", "c-w15", "c-cube-w5", "c-cube-w15", "c-w0b"]
    want = []
    for w, ks in BITS.items():
        for k in ks:
            want += [f"vb-{w}b{k}-w0", f"vb-{w}b{k}-w15"] + (
                [f"vb-{w}b{k}-w0r"] if (w, k) in (("t0", 27), ("t0", 30)) else [])
    assert [r["name"] for r in table("vb")] == want and len(want) == 40
    assert len(table("vc")) + len(table("vb")) == 45
    for st, s in (("vc", "control"), ("vb", "heldout")):
        for r in table(st):
            assert r["risk"] == "safe" and r["tool"] == "t24" and r["set"] == s, r
            assert argv(r) == ["probe", "--temps", "32", "--coords", "--pixels",
                               f"/s/bins/{r['name']}.bin"], r
            assert r["knobs"] == ("reads:o0,rows" if s == "control" else "-")
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    assert CFG["host_key_alias"] == "cedar" and CFG["prefix"] == "r26v" and CFG["knobs"] == {}
    built = open(os.path.join(KP, "lead/TOOL24.built")).read().split()
    t = CFG["tools"]["t24"]
    assert t["sha256"] == built[0] and t["source"] == f"{built[2]}:{built[3]}"
    assert t["source_sha256"] == built[4]


def test_controls_are_e567s_programs():
    for n, p in (("c-w0", "tx-types/bins/tx-types__1"), ("c-w15", "tx-types/bins/tx-types__4"),
                 ("c-cube-w5", "tx-types-risky/bins/tx-types-risky__4"),
                 ("c-cube-w15", "tx-types-risky/bins/tx-types-risky__5"),
                 ("c-w0b", "tx-types/bins/tx-types__1")):
        assert binfile(n) == pins.blob(MK.RECOMP + p + ".bin"), n


def test_bit_programs_flip_one_bit():
    for w, ks in BITS.items():
        reg, base = MK.REG[w]
        for k in ks:
            for wv in ("w0", "w15"):
                t = MK.case_text(MK.TYPES, MK.W[wv])
                f = MK.flipped(t, w, k)
                d = [(a, b) for a, b in zip(t.splitlines(), f.splitlines()) if a != b]
                assert d == [(f"mov {reg}, #0x{base:08x}", f"mov {reg}, #0x{base ^ 1 << k:08x}")]
                assert binfile(f"vb-{w}b{k}-{wv}") == MK.assemble(f)
                ctl = binfile("c-w0" if wv == "w0" else "c-w15")
                assert binfile(f"vb-{w}b{k}-{wv}") != ctl and len(binfile(f"vb-{w}b{k}-{wv}")) == len(ctl)
    assert binfile("vb-t0b27-w0r") == binfile("vb-t0b27-w0")
    assert binfile("vb-t0b30-w0r") == binfile("vb-t0b30-w0")


def test_frozen_controls_are_e567s_hashes():
    p = {ln.split("\t")[0]: ln.split("\t")[2] for ln in
         open(os.path.join(KP, "predictions", "vc.tsv")).read().splitlines()[1:]}
    assert p["c-w0"] == p["c-w15"] == p["c-w0b"]
    assert p["c-w0"].startswith("2b49c848")
    assert p["c-cube-w5"].startswith("79970597") and p["c-cube-w15"].startswith("480213ab")


def mockout(name, world):
    return WO.answer("t24", ["probe", "--temps", "32", "--coords", "--pixels", f"/s/bins/{name}.bin"],
                     world)


def test_mock_images_are_e567s():
    for n, (lab, d) in {"c-w0": ("ty0-3d-w0", "tx-types"), "c-w15": ("ty0-3d-w15", "tx-types"),
                        "c-cube-w5": ("rt2-3d-w5", "tx-types-risky"),
                        "c-cube-w15": ("rt2-3d-w15", "tx-types-risky")}.items():
        k = kept(f"{d}/{lab}.txt.gz")
        assert SC.pixsha(mockout(n, {"novol"})["out"]) == SC.pixsha(k) == MK.pixsha(k)
        # the mock's o0 summary is the tool's as kept
        o0 = [ln for ln in k.splitlines() if ": o0 " in ln][0].split(": ", 1)[1]
        assert [ln for ln in mockout(n, {"novol"})["out"].splitlines()
                if ": o0 " in ln][0].split(": ", 1)[1] == o0


def write_dir(d, stage, outs):
    """a kept stage directory: NAME.txt and cases.tsv for each row of outs {name: text}."""
    os.makedirs(d, exist_ok=True)
    lines = ["\t".join(COLS)]
    for r in table(stage):
        if r["name"] not in outs:
            continue
        open(os.path.join(d, r["name"] + ".txt"), "w").write(outs[r["name"]])
        lines.append("\t".join([r["name"], stage, r["set"], r["risk"], r["knobs"], r["tool"],
                                r["args"], "0", "ok", "-", "-", "1"]))
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("name\n")


def test_scorer_on_e567_kept(tmp_path):
    vc = {n: kept(f"{d}/{lab}.txt.gz") for n, d, lab in (
        ("c-w0", "tx-types", "ty0-3d-w0"), ("c-w15", "tx-types", "ty0-3d-w15"),
        ("c-cube-w5", "tx-types-risky", "rt2-3d-w5"), ("c-cube-w15", "tx-types-risky", "rt2-3d-w15"),
        ("c-w0b", "tx-types", "ty0-3d-w0"))}
    write_dir(str(tmp_path / "a" / "vc"), "vc", vc)
    c, _, _ = SC.verdicts("vc", str(tmp_path / "a" / "vc"))
    assert c == {n: True for n in vc}
    bad = dict(vc, **{"c-cube-w15": vc["c-cube-w5"]})          # w that does not act: FAILS
    write_dir(str(tmp_path / "b" / "vc"), "vc", bad)
    assert SC.verdicts("vc", str(tmp_path / "b" / "vc"))[0]["c-cube-w15"] is False
    # a pair from E567's kept files: ty0-3d-w0 against ty0-3d-w15 holds, against ind-t0b27 fails
    w0, w15 = vc["c-w0"], vc["c-w15"]
    ind = kept("tx-types/ind-t0b27.txt.gz")
    outs = {"vb-t3b9-w0": w0, "vb-t3b9-w15": w15, "vb-t3b8-w0": w0, "vb-t3b8-w15": ind,
            "vb-t0b27-w0": w0, "vb-t0b27-w15": w0, "vb-t0b27-w0r": ind}
    write_dir(str(tmp_path / "a" / "vb"), "vb", outs)
    _, per, lines = SC.verdicts("vb", str(tmp_path / "a" / "vb"))
    got = {ln.split()[1]: ln.split()[3].rstrip(";") for ln in lines if ln.startswith("ROW ")}
    assert got["vb-t3b9"] == "held" and got["vb-t3b8"] == "FAILED"
    assert got["vb-t0b27"] == "cannot"                        # the repeat differs
    assert got["vb-t0b14"] == "cannot"                        # not run
    assert "BITS where w acts (H-VOL): t3b8" in lines
    assert SC.main(["score.py", "gate", "vb", str(tmp_path / "a")]) == 0
    assert SC.main(["score.py", "gate", "vb", str(tmp_path / "b")]) == 1
    assert SC.main(["score.py", "gate", "vb", str(tmp_path / "none")]) == 1


def run_world(world, tmp):
    heads = {}
    for st in ("vc", "vb"):
        d = os.path.join(tmp, world, st)
        shutil.rmtree(d, ignore_errors=True)
        outs = {r["name"]: WO.answer("t24", argv(r), {world})["out"] for r in table(st)}
        write_dir(d, st, outs)
        controls, per, lines = SC.verdicts(st, d)
        if st == "vb":
            controls = SC.gate_controls("vb", [os.path.join(tmp, world)])
        heads[st] = (controls, {ln.split(": ", 2)[2] for ln in SC.summary(st, controls, per)}, lines)
    return heads


def test_worlds_score_as_frozen(tmp_path):
    tmp = str(tmp_path)
    h = run_world("novol", tmp)
    assert all(h["vc"][0].values()) and len(h["vc"][0]) == 5
    assert "H-NOVOL (19 of 19 rows decided)" in h["vb"][1]
    h = run_world("vol", tmp)
    assert all(h["vc"][0].values())
    assert any(x.startswith("H-NOVOL is not supported: 18 held, 1 FAILED") for x in h["vb"][1])
    assert "BITS where w acts (H-VOL): t3b9" in h["vb"][2]
    h = run_world("drift", tmp)
    assert "H-NOVOL (18 of 19 rows decided)" in h["vb"][1]
    h = run_world("cubeoff", tmp)
    assert h["vc"][0]["c-cube-w15"] is False
    assert h["vb"][1] and all("controls FAILED" in x for x in h["vb"][1])


def test_hooks_read_as_the_scorer():
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    out = mockout("c-w0", {"novol"})["out"]
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="probe --pixels /s/b.bin"; '
          'knobs="-"; hook_reading x; echo "check:[$(hook_check x)]"')
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert r.stdout.split() == ["o0=mixed", "rows=32", "check:[]"], r.stdout
    assert len(SC.image(out)) == 2048
    open(os.path.join(d, "x.out"), "w").write(mockout("c-w0", {"nopix"})["out"])
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert "printed 0 pixel rows, not 32" in r.stdout
    shutil.rmtree(d)


def test_world_is_strict():
    assert WO.answer("t24", ["probe", "--bogus", "/s/bins/c-w0.bin"], {"novol"})["rc"] == 2
    assert WO.answer("t24", ["probe", "--poke", "bg:1=0", "/s/bins/c-w0.bin"], {"novol"})["rc"] == 2
    assert WO.answer("t24", ["probe", "--pixels", "/s/bins/other.bin"], {"novol"})["rc"] == 2
    assert WO.answer("t24", ["probe", "--temps", "x", "/s/bins/c-w0.bin"], {"novol"})["rc"] == 2
    assert WO.answer("t10", ["probe", "--pixels", "/s/bins/c-w0.bin"], {"novol"})["rc"] == 2
    assert WO.answer("t24", ["tri", "--width", "64"], {"novol"})["rc"] == 2
    assert WO.answer("t24", ["tri"], {"novol"}) is None
