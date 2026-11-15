# SPDX-License-Identifier: MIT
"""r23-pk's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against round 22's plan and the records it repeats: E391's 40 programs
and pokes byte for byte, E125's and E568's, E037's copy, t22's options); the placed programs
(every landing a model allows is mapped and names itself, no lapc program the library mock would
run as its own); the scorer on kept records it must hold on (E391's raw output: H-E391 40 of 40
on its readings; E125's case 0; E568's kept fy outputs: black) and must fail on (E391's readings
shifted; E568's outputs, which carry no echo: the premise fails); the hooks' reader against the
scorer's on a t22-form output."""
import gzip
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
import q123 as Q  # noqa: E402
import score as SC  # noqa: E402
import world as WO  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PY = sys.executable


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
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(MK.ORDER)
    n = {s: len(table(s)) for s in MK.ORDER}
    assert n == {"pk": 4, "q019": 40, "q181": 8, "q123": 7, "q123h": 3}, n
    for s in MK.ORDER:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in table(s):
            assert r["risk"] == "safe" and r["tool"] == "t22", r
    assert CFG["stages"]["pk"]["on_stop"] == "end" and CFG["stages"]["q123"]["on_stop"] == "end"
    assert all(CFG["stages"][s].get("gate") for s in ("q019", "q181", "q123h"))
    assert SC.GATES == {"q019": "pk", "q181": "pk", "q123h": "q123"}
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    assert CFG["tools"]["t22"]["source"].startswith("3c68e8de6bdfeecd37b97e2d6095fef932e0e6d9:")


def test_q019_is_e391_byte_for_byte():
    d = tomllib.loads(pins.blob(MK.AR_TOML).decode())["probe"][0]
    rows = table("q019")
    for i, r in enumerate(rows):
        a = argv(r)
        assert a[:7] == ["probe", "--temps", "32", "--pds", "36", "--use", "/s/bins/sa64_dump.bin"]
        assert a[7:9] == ["--poke"] + d["case_set"][i]["pokes"]
        assert a[9:] == [f"/s/bins/{r['name']}.bin"]
        b = open(os.path.join(KP, "bins", r["name"] + ".bin"), "rb").read()
        assert b == pins.blob(MK.AR + f"pds-attribute-room-rows__{i}.bin")
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", r["name"])
        assert d["labels"][i] == f"run {m[1]}: {int(m[2])} rows, attributes {int(m[3])}-" \
            f"{int(m[3]) + 15}"
        assert r["set"] == ("fit" if int(m[2]) in (0, 1, 4) else "heldout")
        assert SC.q019_markers(int(m[3]), int(m[1]), int(m[2])) == d["cases"][i][:16]
    # --pds 36: douta_words.s's data dwords, as probe.py's pds_data counts them
    p = MK.P._probe(d, "attribute-room.toml")
    tpl = pins.blob("resgx545:probes/pds/templates/douta_words.s").decode()
    assert MK.P._data_dwords(MK.P.render(p, p.cases[0], tpl)) == MK.PDS_N == 36


def test_pk_rows_repeat_their_records():
    r = {x["name"]: x for x in table("pk")}
    assert argv(r["pk-e391"]) == argv(table("q019")[0])[:-1] + ["/s/bins/pk-e391.bin"]
    assert "--poke" not in argv(r["pk-none"])
    assert argv(r["pk-e125"])[5:9] == ["--use", "/s/bins/sa_dump.bin", "--poke", "bg:1=0x130000"]
    assert open(os.path.join(KP, "bins/pk-e125.bin"), "rb").read() == \
        pins.blob(MK.DO + "pds-douta-secattr-rows-4__0.bin")
    # E568's fy-28-p0-csc: tx-formats.sh's job (probe --temps 32 --coords --pixels) and pokes
    tx = pins.blob(MK.YUV_TOML["csc"]).decode()
    pk = tomllib.loads(tx)["probe"][0]["pokes"]
    assert argv(r["pk-e568"]) == ["probe", "--temps", "32", "--coords", "--pixels"] + \
        [a for k in pk for a in ("--poke", k)] + ["/s/bins/pk-e568.bin"]
    for x in r.values():
        assert x["set"] == "control" and x["knobs"] == "reads:echo"


def test_q181_rows():
    rows = {x["name"]: x for x in table("q181")}
    csc = tomllib.loads(pins.blob(MK.YUV_TOML["csc"]).decode())["probe"][0]["pokes"]
    for n, x in rows.items():
        a = argv(x)
        if n.startswith("c-copy"):
            assert a[:3] == ["copy", "--every-value", "--pixels"] and x["set"] == "control"
            assert "expectdiff" in x["knobs"].split() and "reads:hash" in x["knobs"].split()
            continue
        want = [p for k in csc for p in ("--poke", k)] if n.endswith("-csc") else []
        assert a == ["probe", "--temps", "32", "--coords", "--pixels"] + want + [f"/s/bins/{n}.bin"]
        assert open(os.path.join(KP, "bins", n + ".bin"), "rb").read() == \
            open(os.path.join(KP, "bins", n.replace("-nocsc", "-csc") + ".bin"), "rb").read()
    assert rows["c-copy-csc"]["args"].endswith(MK.CSC0)


def test_q123_programs_land_mapped():
    base = open(os.path.join(KP, "bins/q123-base.bin"), "rb").read()
    assert len(base) == 256 * 8
    for name, stg, st, form, off, kind, n, t in Q.Q123:
        b = open(os.path.join(KP, "bins", name + ".bin"), "rb").read()
        assert len(b) == 8 * n and n <= 8192 and off % 8 == 0 and off >= 0x1000
        assert off + 8 * n <= 0x500000
        q1 = int.from_bytes(b[8:16], "little")
        assert q1 & (0xff << 56 | 3 << 52) != (0xfc << 56 | 1 << 53) or kind == "end", name
        models = Q.q123_models(off, form, kind, n, t, 17 if stg == "q123h" else 16)
        for m, v in models.items():
            k = v & 0xffff
            if v & 0xffff0000 == Q.PAD:
                assert k < n, (name, m)               # a word of the placed program
            else:
                assert v & 0xffff0000 == Q.WPAD and k < 256, (name, m)   # the heap base's
        idx0 = Q.code_index(off, form)
        if kind in ("ba", "lapc"):
            assert f"#0x{idx0 + t:05X}" in open(os.path.join(KP, "bins", name + ".s")).read()
    r = {x["name"]: x for x in table("q123")}
    assert [x["name"] for x in table("q123")][:2] == ["c-run", "c-lapc"]
    for x in table("q123") + table("q123h"):
        a = argv(x)
        assert a[-1] == "/s/bins/q123-base.bin" and "--place-form" in a
        if x["set"] == "control":
            assert x["knobs"].split() == ["reads:o0,placed", "o0:b000024e"]
    assert r["x18-b16"]["args"].count("exe18") == 1
    assert all("exe18" in x["args"] for x in table("q123h"))


def test_scorer_holds_on_e391_and_fails_shifted():
    raw = cases(pins.blob("data:pds/attribute-room/pds-attribute-room-rows/raw.txt").decode())
    assert len(raw) == 40
    for i, r in enumerate(table("q019")):
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", r["name"])
        mk = SC.q019_markers(int(m[3]), int(m[1]), int(m[2]))
        own, stray = SC.arrive(SC.scratch(raw[i]), mk, int(m[3]))
        assert (own, stray) == ((16 if int(m[3]) < 32 else 0), 0), (r["name"], own, stray)
        # E391's output carries no echo: its poke row's premise fails
        assert SC.echo_state(r["args"], raw[i])[0] is False
    # shifted: case 1's scratch against case 0's markers
    own, _ = SC.arrive(SC.scratch(raw[1]), SC.q019_markers(0, 1, 0), 0)
    assert own == 0


def test_scorer_on_e125_and_e568():
    raw = cases(pins.blob("data:followup/pds/douta/pds-douta-secattr-rows-4/raw.txt").decode())
    mk = [int(x, 16) for x in
          MK.markers_value(MK.do_markers(0)[0]).split(",")]
    assert SC.arrive(SC.scratch(raw[0]), mk, 0) == (16, 0)
    decl = MK.yuv_declared()
    for n in ("fy-28-p0-csc", "fy-29-p0-csc", "fy-28-p0-nocsc", "fy-29-p0-nocsc", "fy-28-p1-csc",
              "fy-29-p1-csc"):
        t = pins.blob(f"data:texture/p1132/tx-formats/{n}.txt.gz").decode()
        assert SC.pixsha(t) == MK.BLACK_SHA                 # H-NOLOAD holds on E568
        if n.endswith("-csc"):
            assert SC.pixsha(t) != decl[n]                  # H-LOAD fails on E568
            assert SC.echo_state(" ".join("--poke " + k for k in tomllib.loads(
                pins.blob(MK.YUV_TOML["csc"]).decode())["probe"][0]["pokes"]), t)[0] is False


def test_echo_reader():
    args = "probe --poke bg:1=0x30000 --poke xfer:17^=0x1 /s/x.bin"
    ok = ("probe x: poked bg:1 0x00130000 -> 0x00030000\n"
          "probe x: poked xfer:17 0x00000004 -> 0x00000005\n")
    assert SC.echo_state(args, ok) == (True, "bg:1=0x00030000,xfer:17=0x00000005")
    assert SC.echo_state(args, ok.replace("0x00000005", "0x00000004"))[0] is False
    assert SC.echo_state(args, ok.splitlines()[0] + "\n")[0] is False
    assert SC.echo_state("probe /s/x.bin", "probe x: o0 0x1 (2048 of 2048)\n") == (True, "-")


def test_hooks_read_as_the_scorer():
    out = ("probe q123-base: o0 0xb000024e (2048 of 2048)\n"
           "probe q123-base: placed words read back: 600 of 600 as built, hash 0x1\n"
           "probe q123-base: poked bg:1 0x00130000 -> 0x00030000\n")
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="probe --poke bg:1=0x30000 --place '
          f'0x40000=/s/a.bin /s/b.bin"; knobs="reads:o0,placed o0:b000024e"; '
          'hook_reading x; echo "check:[$(hook_check x)]"')
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
    assert r.stdout.split() == ["echo=1/1", "o0=0xb000024e", "placed=600/600", "check:[]"], r.stdout
    assert SC.o0(out) == 0xB000024E and SC.placed(out) == "600/600"
    sh2 = sh.replace("o0:b000024e", "o0:b0000050")
    r = subprocess.run(["bash", "-c", sh2], capture_output=True, text=True)
    assert "frozen 0xb0000050" in r.stdout
    sh3 = sh.replace("--poke bg:1=0x30000 ", "--poke bg:1=0x30000 --poke xfer:17^=0x1 ")
    r = subprocess.run(["bash", "-c", sh3], capture_output=True, text=True)
    assert "echoed 1 of its 2 pokes" in r.stdout


def test_world_is_strict():
    assert WO.answer("t22", ["probe", "--bogus", "/s/x.bin"], "model")["rc"] == 2
    assert WO.answer("t22", ["probe", "--pds", "36", "/s/x.bin"], "model")["rc"] == 2
    assert WO.answer("t22", ["copy", "--poke", "bg:1=0", "--every-value"], "model")["rc"] == 2
    assert WO.answer("t22", ["tri", "--width", "64"], "model")["rc"] == 2
