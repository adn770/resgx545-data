# SPDX-License-Identifier: MIT
"""r25-csc's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against round 24's plan 2.2: E037's copies as r23-pk ran them, with set
0's words BT.601 or zeros; E568's fy-F-p0 programs byte for byte as r23-pk's; t22's options); the
mock's conversion against E1097's kept fills; the scorer on r23-pk's kept files (the fills hold
H-FILLLOAD's conversion, c-copy-none fails the zeros copy's control) and on every world's
outputs (each model holds in its own world and fails in the other's; a failed control makes its
half cannot tell, not the other half); the hooks' reader against the scorer's."""
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
R23 = "data:render/closing-r23-pk/"
COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def table():
    return [dict(zip(("name", "set", "risk", "knobs", "tool", "args"), ln.split("|", 5)))
            for ln in open(os.path.join(KP, "tables", "csc.txt")).read().splitlines()
            if ln and not ln.startswith("#")]


def argv(r):
    return shlex.split(r["args"].replace("$S", "/s").replace("$W", "/w"))


def kept(name):
    return pins.blob(R23 + f"out/20261115-202948/q181/{name}.txt.gz").decode()


def test_generator_current_and_pinned():
    assert subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"]).returncode == 0
    MK.build()
    pins.blob(R23 + "tables/q181.txt")
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stage_rows_and_order():
    assert list(CFG["stages"]) == ["csc"] and CFG["stages"]["csc"].get("on_stop") is None
    head = open(os.path.join(KP, "tables", "csc.txt")).read().splitlines()[:2]
    assert head == ["#stage csc", "#limit 0"]
    names = [r["name"] for r in table()]
    assert names == [f"y{f}-{s}" for f in (28, 29)
                     for s in ("zc", "a", "b", "c", "bc", "d", "e", "f")]
    assert len(names) == 16
    for r in table():
        assert r["risk"] == "safe" and r["tool"] == "t22", r
    sets = {r["name"].split("-")[1]: r["set"] for r in table()}
    assert sets == {"zc": "control", "a": "control", "b": "fit", "c": "fit", "bc": "control",
                    "d": "control", "e": "heldout", "f": "heldout"}
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    assert CFG["host_key_alias"] == "cedar" and CFG["prefix"] == "r25c"
    assert CFG["tools"]["t22"]["source"].startswith("3c68e8de6bdfeecd37b97e2d6095fef932e0e6d9:")
    assert CFG["tools"]["t22"]["sha256"] == open(os.path.join(KP, "lead/TOOL22.built")).read().split()[0]


def test_rows_repeat_e037_and_r23pk():
    old = {r.split("|")[0]: r.split("|", 5)[5] for r in pins.blob(R23 + "tables/q181.txt").decode()
           .splitlines() if r and not r.startswith("#")}
    for r in table():
        n, a = r["name"], argv(r)
        f, s = n.split("-")
        if s == "bc":
            assert r["args"] == old["c-copy-csc"] and r["knobs"] == "expectdiff reads:hash"
        elif s == "zc":
            assert a[:7] == shlex.split(old["c-copy-csc"])[:7]
            assert a[7:] == ["--poke", "xfer:17^=0x1"] + [x for i in range(18, 23)
                                                          for x in ("--poke", f"xfer:{i}=0")]
            assert r["knobs"] == "expectdiff reads:hash"
        else:
            poke = {"b": "csc", "e": "zeros"}.get(s)
            ref = shlex.split(old[f"fy-{f[1:]}-p0-csc"].replace("$S", "/s"))
            want = ref[:5] + (ref[5:-1] if poke == "csc" else
                              argv({"args": "x " + MK.ZEROS})[1:] if poke else []) + \
                [f"/s/bins/{n}.bin"]
            assert a == want, n
            assert r["knobs"] == ("reads:o0" if r["set"] == "control" else "-")
            assert open(os.path.join(KP, "bins", n + ".bin"), "rb").read() == \
                pins.blob(R23 + f"bins/fy-{f[1:]}-p0-csc.bin")


def test_mock_conversion_is_e1097s():
    for f in (28, 29):
        out = "\n".join(WO.pixel_rows("x", f, "conv")) + "\n"
        assert SC.pixsha(out) == SC.pixsha(kept(f"fy-{f}-p0-csc")) == MK.conv_sha(f)
        assert SC.pixsha("\n".join(WO.pixel_rows("x", f, "black")) + "\n") == MK.BLACK_SHA


def test_scorer_on_r23pk_kept():
    rows = {r["name"]: r for r in table()}
    t = kept("fy-28-p0-csc")
    assert SC.echo_state(rows["y28-b"]["args"], t)[0] is True
    assert SC.echo_state(rows["y28-e"]["args"], t)[0] is False      # BT.601 echo, zeros poke
    assert SC.echo_state(rows["y28-c"]["args"], t)[0] is False      # an unpoked row: no echo
    assert SC.copy_hash(kept("c-copy-none")) == MK.E037_CSC != MK.E037_BLACK   # zc would FAIL
    assert SC.copy_hash(kept("c-copy-csc")) == MK.E037_CSC


def run_world(world, tmp):
    d = os.path.join(tmp, world)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    lines = ["\t".join(COLS)]
    for r in table():
        a = WO.answer("t22", argv(r), world)
        assert a.get("rc", 0) in (0, 1), (world, r["name"], a)
        open(os.path.join(d, r["name"] + ".txt"), "w").write(a["out"])
        lines.append("\t".join([r["name"], "csc", r["set"], r["risk"], r["knobs"], r["tool"],
                                r["args"], str(a.get("rc", 0)), "ok", "-", "-", "1"]))
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("name\n")
    controls, per, _ = SC.verdicts("csc", d)
    return controls, per


def heads(world, tmp):
    controls, per = run_world(world, tmp)
    return controls, {ln.split(": ", 2)[2] for ln in SC.summary("csc", controls, per)}


def test_worlds_score_as_frozen(tmp_path):
    tmp = str(tmp_path)
    c, h = heads("model", tmp)
    assert all(c.values()) and len(c) == 8
    assert "H-FILLLOAD (fit) (4 of 4 rows decided)" in h
    assert "H-FILLLOAD (heldout) (4 of 4 rows decided)" in h
    assert any(x.startswith("H-FILLIGNORE (fit) is not supported") for x in h)
    c, h = heads("ignore", tmp)
    assert all(c.values())
    assert "H-FILLIGNORE (fit) (4 of 4 rows decided)" in h
    assert "H-FILLIGNORE (heldout) (4 of 4 rows decided)" in h
    assert any(x.startswith("H-FILLLOAD (heldout) is not supported") for x in h)
    c, h = heads("clears", tmp)          # d reads black: the held-out half cannot tell
    assert c["y28-d"] is False and c["y28-zc"] and c["y28-a"]
    assert all("controls FAILED" in x for x in h if "(heldout)" in x)
    assert all("controls FAILED" not in x for x in h if "(fit)" in x)
    c, h = heads("copynoop", tmp)        # the zeros copy reads BT.601: the fit half cannot tell
    assert c["y28-zc"] is False and c["y28-a"] is None and c["y28-bc"] and c["y28-d"]
    assert all("controls FAILED" in x for x in h if "(fit)" in x)
    assert "H-FILLLOAD (heldout) (4 of 4 rows decided)" in h


def test_hooks_read_as_the_scorer():
    out = ("probe y28-b: poked xfer:17 0x00000000 -> 0x00000001\n"
           "probe y28-b: o0 0xff000000 (2048 of 2048)\n")
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="probe --poke xfer:17^=0x1 /s/b.bin"; '
          'knobs="-"; hook_reading x; echo "check:[$(hook_check x)]"')
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert r.stdout.split() == ["echo=1/1", "o0=0xff000000", "check:[]"], r.stdout
    sh2 = sh.replace("--poke xfer:17^=0x1 ", "--poke xfer:17^=0x1 --poke xfer:18=0 ")
    r = subprocess.run(["bash", "-c", sh2], capture_output=True, text=True)
    assert "echoed 1 of its 2 pokes" in r.stdout
    open(os.path.join(d, "x.out"), "w").write("target: 64x32 hash 0xd3522437a14b6325\n")
    sh3 = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="copy --every-value"; hook_reading x; '
           'echo "check:[$(hook_check x)]"')
    r = subprocess.run(["bash", "-c", sh3], capture_output=True, text=True)
    assert r.stdout.split() == ["hash=0xd3522437a14b6325", "check:[]"], r.stdout
    shutil.rmtree(d)


def test_world_is_strict():
    assert WO.answer("t22", ["probe", "--bogus", "/s/y28-a.bin"], "model")["rc"] == 2
    assert WO.answer("t22", ["probe", "--poke", "bg:1=0", "/s/y28-a.bin"], "model")["rc"] == 2
    assert WO.answer("t22", ["probe", "--pixels", "/s/other.bin"], "model")["rc"] == 2
    assert WO.answer("t22", ["copy", "--poke", "bg:1=0", "--every-value"], "model")["rc"] == 2
    assert WO.answer("t22", ["tri", "--width", "64"], "model")["rc"] == 2
