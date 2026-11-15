# SPDX-License-Identifier: MIT
"""r25-sa64's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against round 24's plan and the records it repeats: E391's 40 programs
and pokes byte for byte with --scratch-show 64, the 16 held-out programs rendered from E391's own
table by the renderer that reproduces E391's 40 byte for byte, E125's case 0); the scorer on kept
records it must hold on (E1096's 40 q019 outputs and its pk rows: H-E391 on sa0-sa31) and must
fail on (E1096's outputs, which print 32 dwords and `32 more changed`: the print premise fails;
E391's raw output without the echo; shifted markers); the hooks' reader against the scorer's."""
import os
import re
import shlex
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
E1096 = "data:render/closing-r23-pk/out/20261115-202948/"


def table(stage):
    return [dict(zip(("name", "set", "risk", "knobs", "tool", "args"), ln.split("|", 5)))
            for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines()
            if ln and not ln.startswith("#")]


def argv(r):
    return shlex.split(r["args"].replace("$S", "/s").replace("$W", "/w"))


def cases(raw):
    """{case index: its text} of a probe.py raw.txt."""
    out, cur = {}, None
    for ln in raw.splitlines():
        m = re.match(r"probe-case \S+__(\d+)$", ln)
        if m:
            cur = int(m[1])
            out[cur] = ""
        elif cur is not None:
            out[cur] += ln + "\n"
    return out


def test_generator_current_and_pinned():
    assert subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"]).returncode == 0
    MK.build()
    for n in [r["name"] for r in table("q019")][:40]:
        pins.blob(E1096 + f"q019/{n}.txt.gz")
    for n in ("pk-e391", "pk-e125"):
        pins.blob(E1096 + f"pk/{n}.txt.gz")
    pins.blob("data:pds/attribute-room/pds-attribute-room-rows/raw.txt")
    pins.blob("data:followup/pds/douta/pds-douta-secattr-rows-4/raw.txt")
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stages_counts_and_tool():
    assert list(CFG["stages"]) == list(MK.ORDER) == ["pk64", "q019"]
    n = {s: len(table(s)) for s in MK.ORDER}
    assert n == {"pk64": 2, "q019": 56}, n
    for s in MK.ORDER:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in table(s):
            assert r["risk"] == "safe" and r["tool"] == "t24", r
            a = argv(r)
            assert a[a.index("--scratch-show") + 1] == "64"
    assert CFG["stages"]["pk64"]["on_stop"] == "end" and CFG["stages"]["q019"]["gate"]
    assert SC.GATES == {"q019": "pk64"}
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    t = CFG["tools"]["t24"]
    assert t["sha256"] == "fd15fce4ca75b3868fd42b7e5d639ae8a3096fc895543e25a707bac9fb5db040"
    assert t["source"] == "134103452432f328eac27ec148499cc3149cf83b:" \
        "userspace/libsgxfive/tools/sgxfive-test.c"
    assert t["source_sha256"] == "df2e8b82d089fe6d91e4a72f46ccfb22127a167a4008a529b398c4dfba14b13b"
    built = open(os.path.join(KP, "lead", "TOOL24.built")).read().split()
    assert built[0] == t["sha256"] and built[2] + ":" + built[3] == t["source"]


def test_q019_is_e391_byte_for_byte_then_held_out():
    d = tomllib.loads(pins.blob(MK.AR_TOML).decode())["probe"][0]
    rows = table("q019")
    for i, r in enumerate(rows):
        a = argv(r)
        assert a[:9] == ["probe", "--temps", "32", "--pds", "36", "--use", "/s/bins/sa64_dump.bin",
                         "--scratch-show", "64"]
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", r["name"])
        run, nrows, lo = int(m[1]), int(m[2]), int(m[3])
        b = open(os.path.join(KP, "bins", r["name"] + ".bin"), "rb").read()
        assert r["set"] == ("fit" if nrows in (0, 1, 4) else "heldout")
        if i < 40:
            assert a[9:11] == ["--poke"] + d["case_set"][i]["pokes"]
            assert b == pins.blob(MK.AR + f"pds-attribute-room-rows__{i}.bin")
            assert d["labels"][i] == f"run {run}: {nrows} rows, attributes {lo}-{lo + 15}"
            assert SC.q019_markers(lo, run, nrows) == d["cases"][i][:16]
            assert MK.ar_case(run, nrows, lo) == d["cases"][i]
            assert MK.render_case(d["cases"][i]) == b      # the renderer is E391's, byte for byte
        else:
            assert nrows in (3, 6)
            assert a[9:11] == ["--poke", f"bg:1=0x{0x30000 | nrows << 18:x}"]
            assert b == MK.render_case(MK.ar_case(run, nrows, lo))
    assert sorted((r["name"]) for r in rows[40:]) == sorted(
        f"q019-{run}-r{x}-a{lo:02d}" for run in (1, 2) for x in (3, 6) for lo in (0, 16, 32, 48))
    assert {(0x30000 | x << 18) for x in (0, 1, 2, 4, 8)} == {0x30000, 0x70000, 0xb0000, 0x130000,
                                                             0x230000}


def test_pk64_rows_repeat_e1096():
    r = {x["name"]: x for x in table("pk64")}
    assert argv(r["pk-e391"]) == argv(table("q019")[0])[:-1] + ["/s/bins/pk-e391.bin"]
    assert argv(r["pk-e125"])[5:11] == ["--use", "/s/bins/sa_dump.bin", "--scratch-show", "64",
                                        "--poke", "bg:1=0x130000"]
    assert open(os.path.join(KP, "bins/pk-e125.bin"), "rb").read() == \
        pins.blob(MK.DO + "pds-douta-secattr-rows-4__0.bin")
    for x in r.values():
        assert x["set"] == "control" and x["knobs"] == "reads:echo,shown"
        assert SC.producible(x) >= {"echo", "shown"}


def test_scorer_holds_on_e1096_sa0_sa31_and_print_premise_fails():
    for r in table("q019")[:40]:
        t = pins.blob(E1096 + f"q019/{r['name']}.txt.gz").decode()
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", r["name"])
        run, nrows, lo = int(m[1]), int(m[2]), int(m[3])
        mk = SC.q019_markers(lo, run, nrows)
        assert SC.arrive(SC.scratch(t), mk, lo, 32) == ((16 if lo < 32 else 0), 0), r["name"]
        # E1096's echo holds against this row's poke (the same poke)
        assert SC.echo_state(r["args"], t)[0] is True
        # t22 printed 32 and `32 more changed`: not --scratch-show 64, the premise fails
        assert SC.shown(t) == (32, 32) and not SC.show_ok(t)
    for n, want in (("pk-e391", SC.q019_markers(0, 1, 0)),
                    ("pk-e125", [0xA0A00000 + k for k in range(16)])):
        t = pins.blob(E1096 + f"pk/{n}.txt.gz").decode()
        assert SC.arrive(SC.scratch(t), want, 0) == (16, 0)
        assert SC.echo_state(argv_text(n), t)[0] is True
    assert SC.shown(pins.blob(E1096 + "pk/pk-e125.txt.gz").decode()) == (16, 0)


def argv_text(n):
    return {x["name"]: x for x in table("pk64")}[n]["args"]


def test_scorer_fails_on_e391_raw_and_shifted():
    raw = cases(pins.blob("data:pds/attribute-room/pds-attribute-room-rows/raw.txt").decode())
    assert len(raw) == 40
    for i, r in enumerate(table("q019")[:40]):
        assert SC.echo_state(r["args"], raw[i])[0] is False      # no echo in E391's output
    own, _ = SC.arrive(SC.scratch(raw[1]), SC.q019_markers(0, 1, 0), 0)
    assert own == 0


def test_models_differ_on_the_high_sets():
    pred = open(os.path.join(KP, "predictions", "q019.tsv")).read().splitlines()[1:]
    by = {}
    for ln in pred:
        c, q, v, m, st, _ = ln.split("\t")
        by.setdefault(c, {}).setdefault(q, {})[m] = v
    for c, q in by.items():
        lo = int(c[-2:])
        assert q["own"]["H-ALL64"] == "16"
        assert q["own"]["H-NONE"] == ("16" if lo < 32 else "0")
        assert q["own_lo"]["H-E391"] == ("16" if lo < 32 else "0")
        assert q["echo"]["H-ECHO"].startswith("bg:1=0x")


def run_hooks(out, args):
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="{args}"; knobs="reads:echo,shown"; '
          'hook_reading x; echo "check:[$(hook_check x)]"')
    return subprocess.run(["bash", "-c", sh], capture_output=True, text=True).stdout


def test_hooks_read_as_the_scorer():
    args = "probe --scratch-show 64 --poke bg:1=0x30000 /s/b.bin"
    lines = ["probe x: poked bg:1 0x00130000 -> 0x00030000"] + \
        [f"probe x: scratch +0x{4 * i:03x} 0x{i:08x}" for i in range(64)]
    out = "\n".join(lines) + "\n"
    assert run_hooks(out, args).split() == ["echo=1/1", "shown=64/0", "check:[]"]
    assert SC.shown(out) == (64, 0) and SC.show_ok(out)
    capped = "\n".join(lines[:33] + ["probe x: scratch 32 more changed"]) + "\n"
    r = run_hooks(capped, args)
    assert "shown=32/32" in r and "not --scratch-show 64" in r
    assert not SC.show_ok(capped)
    r = run_hooks("\n".join(lines[1:]) + "\n", args)
    assert "echoed 0 of its 1 pokes" in r


def test_world_is_strict_and_prints_64():
    assert WO.answer("t24", ["probe", "--bogus", "/s/x.bin"], "none")["rc"] == 2
    assert WO.answer("t24", ["probe", "--pds", "36", "/s/x.bin"], "none")["rc"] == 2
    for v in ("0", "65", "all", "-1"):
        assert WO.answer("t24", ["probe", "--scratch-show", v, "/s/x.bin"], "none")["rc"] == 2
    assert WO.answer("t24", ["copy", "--every-value"], "none")["rc"] == 2
    for r in table("pk64") + table("q019"):
        a = WO.answer("t24", argv(r), "all64")
        assert a["rc"] == 0 and SC.shown(a["out"]) == ((16, 0) if r["name"] == "pk-e125"
                                                       else (64, 0))
