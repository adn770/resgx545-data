# SPDX-License-Identifier: MIT
"""r25-q123's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against rank-round24.md 2.3: E492's programs byte for byte, E1098's
c-lapc and heap base byte for byte, the four new placements and the drawn targets); the step
choice (only 0x80000 fits the ten old links among multiples of 8; every rival predicts another
link at every new placement); the programs (every landing a model allows is mapped and names
itself); the scorer on kept records it must hold on (E492's 0x300008 outputs, E1098's c-lapc) and
must fail on (E492's 0x2ff000 output against a new placement, E1098's b16-ba against a drawn
target); the hooks' reader against the scorer's on a t22-form output; the world's strictness."""
import os
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
import q123 as Q  # noqa: E402
import score as SC  # noqa: E402
import world as WO  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PY = sys.executable
R23 = "data:render/closing-r23-pk/out/20261115-202948/q123/"


def table(stage):
    return [dict(zip(("name", "set", "risk", "knobs", "tool", "args"), ln.split("|", 5)))
            for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines()
            if ln and not ln.startswith("#")]


def argv(r):
    return shlex.split(r["args"].replace("$S", "/s").replace("$W", "/w"))


def preds(stage):
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s, _ = ln.split("\t")
        out.setdefault((c, q), {})[m] = v
    return out


def bin_(name):
    return open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def test_generator_current_and_pinned():
    assert subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"]).returncode == 0
    MK.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(MK.ORDER) == ["q123s", "q123w"]
    n = {s: len(table(s)) for s in MK.ORDER}
    assert n == {"q123s": 10, "q123w": 11}, n
    for s in MK.ORDER:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        assert CFG["stages"][s]["on_stop"] == "end" and not CFG["stages"][s].get("gate")
        rows = table(s)
        sets = [r["set"] for r in rows]
        assert sets == sorted(sets, key=lambda x: x != "control")      # controls first
        for r in rows:
            assert r["risk"] == "safe" and r["tool"] == "t22", r
    assert SC.GATES == {}
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    assert CFG["tools"]["t22"]["source"].startswith("3c68e8de6bdfeecd37b97e2d6095fef932e0e6d9:")
    assert CFG["tools"]["t22"]["sha256"].startswith("9b62d315")
    assert CFG["host_key_alias"] == "cedar" and CFG["prefix"] == "r25q"


def test_step_choice_is_frozen_and_discriminating():
    assert Q.multiples_fitting_all() == [0x80000]
    assert {k: Q.fits(u) for k, u in Q.rivals().items() if u} == \
        {"H-STEP20000": 5, "H-STEP40000": 7, "H-STEP100000": 5}
    assert Q.fits(Q.STEP) == 10
    want = {0x0C3010: 0x8604, 0x2CA7F8: 0x9501, 0x3D0100: 0xA022, 0x1C8008: 0x9003}
    for off, ln in want.items():
        m = Q.step_models(off)
        assert m["H-STEP80000"] == ln
        assert sorted(k for k, v in m.items() if v == ln) == ["H-STEP80000"], hex(off)
    assert Q.link(0x0C3010, 0x40000) == 0x0604 and Q.link(0x0C3010, 0x100000) == 0x18604
    # E492's own hypotheses for its 0x80000 step agree with the links OLD carries
    t = tomllib.loads(pins.blob("resgx545:probes/usse/place-more.toml").decode())
    for p in t["probe"]:
        pl = p.get("place", {})
        if pl.get("source") in ("p25_link_read.s", "p25_link_jump.s"):
            (v,) = {x for x in next(iter(p["hypotheses"].values()))}
            assert Q.OLD[pl["offset"]] == v, p["name"]


def test_q123s_rows_are_e492s_programs():
    e = {"read": pins.blob(MK.E492_READ), "jump": pins.blob(MK.E492_JUMP)}
    assert (len(e["read"]), len(e["jump"])) == (32, 88)
    for kind, b in e.items():
        p = bin_(f"e492-{kind}")
        assert p[:len(b)] == b and len(p) == 8 * Q.SPAN
        # the pads are E1098's pads at the same word (c-lapc's words 7 on)
        assert p[max(len(b), 56):] == bin_("c-lapc")[max(len(b), 56):8 * Q.SPAN]
    rows = table("q123s")
    pr = preds("q123s")
    offs = []
    for r in rows:
        a = argv(r)
        off, prog = a[4].split("=")
        assert a[:4] == ["probe", "--temps", "32", "--place"] and a[5:] == \
            ["--place-form", "cbase", "/s/bins/q123-base.bin"]
        kind = r["name"].split("-")[1]
        assert prog == f"/s/bins/e492-{kind}.bin" and r["name"].endswith(f"{int(off, 0):06x}")
        offs.append(int(off, 0))
        if r["set"] == "control":
            assert int(off, 0) == 0x300008
            assert r["knobs"].split() == ["reads:o0,placed", "o0:00000003"]
            assert pr[(r["name"], "o0")] == {"H-STEP80000": "0x00000003"}
        else:
            assert r["knobs"] == "-" and len(pr[(r["name"], "o0")]) == 5
    assert offs == [0x300008] * 2 + [o for o in Q.NEW for _ in (0, 1)]


def test_q123w_rows_and_draw():
    assert bin_("q123-base") == pins.blob(MK.E1098_BASE) and len(bin_("q123-base")) == 2048
    assert bin_("c-lapc") == pins.blob(MK.E1098_CLAPC) and len(bin_("c-lapc")) == 600 * 8
    d = Q.draw()
    ts = [t for _, t in d]
    assert len(set(ts)) == 10 and 256 in ts and 8191 in ts and all(256 <= t <= 8191 for t in ts)
    assert 590 not in ts and [k for k, _ in d].count("lapc") == 6
    rows = table("q123w")
    assert rows[0]["name"] == "c-lapc" and rows[0]["set"] == "control"
    assert rows[0]["knobs"].split() == ["reads:o0,placed", "o0:b000024e"]
    assert [r["name"] for r in rows[1:]] == [f"w-{k}-{t:04d}" for k, t in d]
    for r in rows:
        a = argv(r)
        assert a[4].startswith("0x40000=/s/bins/") and a[5:7] == ["--place-form", "cbase"]
        assert a[-1] == "/s/bins/q123-base.bin"
    idx0 = Q.WOFF // 8
    for kind, t in d:
        b = bin_(f"w-{kind}-{t:04d}")
        assert len(b) == 8 * 8192 and Q.WOFF + len(b) <= Q.STEP          # in step
        assert f"#0x{idx0 + t:05X}" in open(os.path.join(KP, "bins", f"w-{kind}-{t:04d}.s")).read()
        # the target word is a pad naming itself, same bytes as E1098's pad of that word if any
        m = Q.word_models(t)
        assert m["H-INDEX"] & 0xFFFF == t < 8192 and m["H-WRAP256"] & 0xFFFF < 256
        assert b[8 * 600:8 * 601] != bytes(8)
        if t < 600:
            assert b[8 * t:8 * t + 8] == bin_("c-lapc")[8 * t:8 * t + 8]
        q1 = int.from_bytes(b[8:16], "little")
        assert q1 & (0xff << 56 | 3 << 52) != (0xfc << 56 | 1 << 53)   # no library-mock fill


def _kept(name, text, d):
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + ".txt"), "w").write(text)


def _score(stage, texts, tmp):
    d = str(tmp / stage)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.write("\t".join(SC.K.COLUMNS) + "\n" + "".join(
            f"{n}\t{stage}\t-\tsafe\t-\tt22\tprobe\t0\tok\t-\t-\t1\n" for n in texts))
    open(os.path.join(d, "void.tsv"), "w").write("name\treason\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\treading\n")
    for n, t in texts.items():
        _kept(n, t, d)
    return SC.verdicts(stage, d)


def _e492(name):
    raw = pins.blob(f"data:usse/place-more/{name}/raw.txt").decode()
    first = raw.split("probe-case ")[1]
    return first + f"probe x: placed words read back: {Q.SPAN} of {Q.SPAN} as built, hash 0x1\n"


def test_scorer_on_kept_records(tmp_path):
    # E492's 0x300008 jobs (placed line added: E492's tool had none): the controls pass
    texts = {r["name"]: "" for r in table("q123s")}
    texts["c-read-300008"] = _e492("usse-place-more-read-300008")
    texts["c-jump-300008"] = _e492("usse-place-more-jump-300008")
    # E492's 0x2ff000 job (link 0xfe02) as a new placement's output: every model fails
    texts["s-read-0c3010"] = _e492("usse-place-more-read-2ff000")
    texts = {k: v for k, v in texts.items() if v}
    controls, per_model, lines = _score("q123s", texts, tmp_path)
    assert controls == {"c-read-300008": True, "c-jump-300008": True}, lines
    # (the rows not given are unrun: cannot tell)
    assert all(v[0] is False and set(v[1:]) == {None} for v in per_model.values()), per_model
    # E1098's c-lapc holds; its b16-ba (o0 0xb0000050) against a drawn target fails both
    cl = pins.blob(R23 + "c-lapc.txt.gz").decode()          # pins.blob unpacks a .gz
    bb = pins.blob(R23 + "b16-ba.txt.gz").decode()
    first = table("q123w")[1]["name"]
    controls, per_model, lines = _score("q123w", {"c-lapc": cl, first: bb.replace(
        "600 of 600", "8192 of 8192")}, tmp_path)
    assert controls == {"c-lapc": True}, lines
    assert sorted(per_model) == ["H-INDEX", "H-WRAP256"], lines
    assert all(v[0] is False and set(v[1:]) == {None} for v in per_model.values()), lines
    # the model world's output holds H-INDEX on every drawn row and H-STEP80000 on q123s
    for stage, held in (("q123s", "H-STEP80000"), ("q123w", "H-INDEX")):
        tx = {}
        for r in table(stage):
            out = WO.answer("t22", argv(r), "model")
            assert out["rc"] == 0
            tx[r["name"]] = out["out"]
        controls, per_model, _ = _score(stage, tx, tmp_path / ("m" + stage))
        assert all(controls.values())
        assert all(per_model[held]) and not any(v for m, s in per_model.items() if m != held
                                                for v in s)


def test_hooks_read_as_the_scorer():
    out = ("probe q123-base: o0 0x00000003 (2048 of 2048)\n"
           "probe q123-base: placed words read back: 32 of 32 as built, hash 0x1\n")
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="probe --temps 32 --place '
          f'0x300008=/s/a.bin --place-form cbase /s/b.bin"; knobs="reads:o0,placed o0:00000003"; '
          'hook_reading x; echo "check:[$(hook_check x)]"')
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert r.stdout.split() == ["o0=0x00000003", "placed=32/32", "check:[]"], r.stdout
    assert SC.o0(out) == 3 and SC.placed(out) == "32/32"
    r = subprocess.run(["bash", "-c", sh.replace("o0:00000003", "o0:b000024e")],
                       capture_output=True, text=True)
    assert "frozen 0xb000024e" in r.stdout
    open(os.path.join(d, "x.out"), "w").write(out.replace("32 of 32", "31 of 32"))
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert "not read back as built" in r.stdout


def test_world_is_strict():
    ok = ["probe", "--temps", "32", "--place", "0x300008=/s/bins/e492-read.bin", "--place-form",
          "cbase", "/s/bins/q123-base.bin"]
    assert WO.answer("t22", ok, "model")["rc"] == 0
    assert WO.answer("t22", ok[:3] + ["--bogus"] + ok[3:], "model")["rc"] == 2
    assert WO.answer("t22", ok[:5] + ok[7:], "model")["rc"] == 2           # no --place-form
    bad = list(ok)
    bad[4] = "0x300004=/s/bins/e492-read.bin"
    assert WO.answer("t22", bad, "model")["rc"] == 2                        # not a multiple of 8
    bad[4] = "0x4ff000=/s/bins/w-ba-0256.bin"
    assert WO.answer("t22", bad, "model")["rc"] == 2                        # past the heap
    assert WO.answer("t22", ["copy", "--every-value"], "model")["rc"] == 2
    assert WO.answer("t22", ["tri", "--width", "64"], "model")["rc"] == 2
