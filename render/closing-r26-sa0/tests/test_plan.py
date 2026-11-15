# SPDX-License-Identifier: MIT
"""r26-sa0's offline tests: the generator is current and session.toml pins every input it reads;
the argv twin (every row against round 26's plan 2.2 and E1061: c-e521 is E1061's u-ctl-e521
program byte for byte, the sa0 rows share E1061's pairs or eight new ones, the writer quads and the
branch lengths); the scorer replayed on E1061's kept readbacks it must hold on (u-ctl-e521 as the
control, u-i0 as H-ZX 8 of 8, u-sa0 as H-MIX) and must fail on (sign-extended values, a dword
changed outside the eight, no readout); the hooks' reader against the scorer's; the mock is as
strict as the tool and its worlds print what they say."""
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
OUT = "data:usse/closing-r16-usse/out/20261114-092913/uadd/"
COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def table(stage):
    return [dict(zip(("name", "set", "risk", "knobs", "tool", "args"), ln.split("|", 5)))
            for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines()
            if ln and not ln.startswith("#")]


def argv(r):
    return shlex.split(r["args"].replace("$S", "/s").replace("$W", "/w"))


def test_generator_current_and_pinned():
    assert subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"]).returncode == 0
    MK.build()
    for n in ("u-ctl-e521", "u-i0", "u-sa0"):
        pins.blob(OUT + n + ".txt.gz")
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    assert CFG["files"]["laptop"] == ["bins/*.bin"]


def test_stages_counts_and_tool():
    assert list(CFG["stages"]) == list(MK.ORDER) == ["uc", "us"]
    assert {s: len(table(s)) for s in MK.ORDER} == {"uc": 2, "us": 6}
    assert CFG["stages"]["us"]["gate"] and CFG["stages"]["uc"]["on_stop"] == "end"
    assert SC.GATES == {"us": "uc"}
    for s in MK.ORDER:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in table(s):
            assert r["risk"] == "safe" and r["tool"] == "t24", r
            assert argv(r)[:4] == ["probe", "--coords", "--temps", "32"]
            assert r["set"] == ("control" if s == "uc" else "heldout")
            assert (r["knobs"] == "reads:scratch") == (s == "uc")
            assert SC.producible(r) == {"scratch"}
    assert CFG["health_tool"] == "t10" and CFG["srcversion"] == "E0CC40275493F8AEAD8180B"
    t = CFG["tools"]["t24"]
    assert t["sha256"] == "fd15fce4ca75b3868fd42b7e5d639ae8a3096fc895543e25a707bac9fb5db040"
    assert t["source"] == "134103452432f328eac27ec148499cc3149cf83b:" \
        "userspace/libsgxfive/tools/sgxfive-test.c"
    built = open(os.path.join(KP, "lead", "TOOL24.built")).read().split()
    assert built[0] == t["sha256"] and built[2] + ":" + built[3] == t["source"]
    for bad in CFG["forbid_options"]:
        assert all(bad not in r["args"] for s in MK.ORDER for r in table(s))


def test_programs_are_the_plans():
    e1061 = subprocess.run(["git", "-C", pins.DATA, "show", pins.COMMIT["data"] + ":usse/"
                            "closing-r16-usse/bins/u-ctl-e521.bin"], capture_output=True).stdout
    assert open(os.path.join(KP, "bins", "c-e521.bin"), "rb").read() == e1061 and e1061
    assert MK.E1061_PAIRS == list(zip(
        [0x8000, 0x8001, 0xABCD, 0xFFFF, 0x7FFF, 0xFFFF8000, 0x1234FEDC, 0xFFFFFFFF],
        [0x8000, 0x7FFF0000, 1, 0xFFFFFFFF, 0x8001, 0x12345678, 0x80000000, 0x10000]))
    new = MK.new_pairs()
    assert new == MK.new_pairs() and len(new) == 8
    assert all(0x8000 <= a & 0xFFFF for a, _ in new)
    assert all(MK.zx(a, b) != MK.sx(a, b) for a, b in new)
    vals = [MK.zx(a, b) for a, b in new]
    assert len(set(vals)) == 8 and not set(vals) & {MK.zx(a, b) for a, b in MK.E1061_PAIRS}
    for r in table("uc") + table("us"):
        n = r["name"]
        t = MK.program(n)
        b = open(os.path.join(KP, "bins", n + ".bin"), "rb").read()
        assert b == MK.asm(t)
        ins = [x for x in t.splitlines() if x and not x.startswith(";")]
        assert len(b) // 8 == len(ins)          # one 64-bit word each
        pairs, writer, dst = MK.ROWS[n]
        assert dst == ("sa0" if n.startswith("s-") else "r10")
        assert sum(x.startswith("iaddu32.testtaz.chan0 " + dst) for x in ins) == 8
        assert ("sa0" in " ".join(ins).replace("iaddu32.testtaz.chan0 sa0", "")) == (dst == "sa0")
        if writer is None:
            assert not any("br" in x.split()[0] for x in ins)
            continue
        i = next(k for k, x in enumerate(ins) if x.startswith("!p0 br"))
        m = int(ins[i].split("#")[1])
        assert ins[i - 1] == "xor.testtaz.chan0 !c0, p0, r7, r9"
        assert ins[i - 2] == "mov.skipinv r9, #0x%08X" % writer
        assert ins[i + m] == "idf drc0, bif"        # br #m lands on the join (m - 1 skipped)
        assert ins[i + m - 1].startswith("stad")
        assert writer in (0, (30 << 16) | 62)     # a top-left lane (E513): even x, even y
        assert writer % 2 == 0 and (writer >> 16) % 2 == 0
    assert {MK.ROWS[n][1] for n in MK.STAGES["us"]} == {0, (30 << 16) | 62}
    assert open(os.path.join(KP, "bins", "s-00-a.bin"), "rb").read() == \
        open(os.path.join(KP, "bins", "s-00-b.bin"), "rb").read()
    assert open(os.path.join(KP, "bins", "s-new-a.bin"), "rb").read() == \
        open(os.path.join(KP, "bins", "s-new-b.bin"), "rb").read()


def kept(tmp, stage, outputs):
    d = tmp / stage
    d.mkdir()
    tb = {ln.split("|")[0]: ln.split("|") for ln in open(os.path.join(KP, "tables", stage + ".txt"))
          if ln.strip() and not ln.startswith("#")}
    rows = ["\t".join(COLS)]
    for n, text in outputs.items():
        (d / f"{n}.txt").write_text(text)
        t = tb[n]
        rows.append("\t".join([n, stage, t[1], t[2], t[3], t[4], "x", "0", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d):
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, name):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {name}")][0]


def rename(text, old, new):
    return text.replace(f"probe {old}:", f"probe {new}:")


def probe_out(name, dw, o0=True):
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if o0:
        out.append(f"probe {name}: o0 0xc0de0001 (2048 of 2048)")
    out += [f"probe {name}: scratch +0x{k:03x} 0x{v:08x}" for k, v in sorted(dw.items())]
    return "\n".join(out) + "\n"


def e1061(n):
    return pins.blob(OUT + n + ".txt.gz").decode()


def test_scorer_holds_on_e1061_kept_readbacks(tmp_path):
    c = rename(e1061("u-ctl-e521"), "u-ctl-e521", "c-e521")
    i0 = e1061("u-i0")
    sa0 = e1061("u-sa0")
    out = score("uc", kept(tmp_path, "uc", {"c-e521": c, "c-one-r10": rename(i0, "u-i0",
                                                                           "c-one-r10")}))
    assert "PASS" in line(out, "CONTROL", "c-e521") and "PASS" in line(out, "CONTROL", "c-one-r10")
    # u-i0's pairs are the sa0 rows' pairs: its kept dwords are H-ZX 8 of 8 on s-00-a, not H-SX
    # and not H-MIX (every dword its own pair's)
    ok = rename(i0, "u-i0", "s-00-a")
    mix = rename(sa0, "u-sa0", "s-00-b")
    out = score("us", kept(tmp_path, "us", {"s-00-a": ok, "s-00-b": mix}))
    a, b = line(out, "ROW", "s-00-a"), line(out, "ROW", "s-00-b")
    assert "H-ZX 8/8" in a and a.endswith("held H-ZX") and "H-SX 1/8" in a
    assert "H-ZX 6/8" in b and b.endswith("held H-MIX") and "+0x010=0x8000fedc" in b
    assert "dwords H-ZX (heldout) is not supported: 1 held, 1 FAILED" in out


def test_scorer_fails_where_it_must(tmp_path):
    # E521's kept values, sign-extended in the first dwords: the control fails
    c = rename(e1061("u-ctl-e521"), "u-ctl-e521", "c-e521").replace(
        "scratch +0x004 0x00010000", "scratch +0x004 0xffff0000", 1)
    pairs = MK.E1061_PAIRS
    zxv = {4 * k: MK.zx(a, b) for k, (a, b) in enumerate(pairs)}
    sxv = {4 * k: MK.sx(a, b) for k, (a, b) in enumerate(pairs)}
    d = kept(tmp_path, "uc", {"c-e521": c, "c-one-r10": probe_out("c-one-r10", sxv)})
    out = score("uc", d)
    assert "FAILED" in line(out, "CONTROL", "c-one-r10")
    assert "FAILED" in line(out, "CONTROL", "c-e521") or "scratch +0x004" not in c
    assert subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), "gate", "us",
                           str(tmp_path)], capture_output=True).returncode == 1
    rows = {"s-00-a": probe_out("s-00-a", sxv),
            "s-00-b": probe_out("s-00-b", {**zxv, 0x20: 0x1234}),     # a ninth dword changed
            "s-6331-a": probe_out("s-6331-a", zxv, o0=False),           # no o0: cannot tell
            "s-new-a": probe_out("s-new-a", {})}                        # nothing stored
    (tmp_path / "x").mkdir()
    out = score("us", kept(tmp_path / "x", "us", rows))
    assert line(out, "ROW", "s-00-a").endswith("held H-SX") and "H-ZX 1/8" in line(out, "ROW", "s-00-a")
    assert "changed outside" in line(out, "ROW", "s-00-b")
    assert line(out, "ROW", "s-6331-a").endswith("cannot tell")
    assert line(out, "ROW", "s-new-a").endswith("no frozen model exact")
    assert "not supported" in out


def test_new_pairs_rows_hold_zx_and_fail_sx(tmp_path):
    new = MK.new_pairs()
    zxv = {4 * k: MK.zx(a, b) for k, (a, b) in enumerate(new)}
    sxv = {4 * k: MK.sx(a, b) for k, (a, b) in enumerate(new)}
    out = score("us", kept(tmp_path, "us", {"s-new-a": probe_out("s-new-a", zxv),
                                            "s-new-6331": probe_out("s-new-6331", sxv)}))
    a, b = line(out, "ROW", "s-new-a"), line(out, "ROW", "s-new-6331")
    assert a.endswith("held H-ZX") and "H-SX 0/8" in a
    assert b.endswith("held H-SX") and "H-ZX 0/8" in b


def run_hooks(out, args, n=1):
    d = os.path.join(KP, "debug", "hooktest")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "x.out"), "w").write(out)
    sh = (f'. "{KP}/run/hooks.sh"; JW="{d}"; args="{args}"; knobs="reads:scratch"; '
          'hook_reading x; for i in $(seq 1 ' + str(n) + '); do echo "check:[$(hook_check x)]"; done')
    return subprocess.run(["bash", "-c", sh], capture_output=True, text=True).stdout


def test_hooks_read_as_the_scorer():
    out = probe_out("x", {4 * k: k for k in range(8)})
    assert run_hooks(out, "probe --coords x").split() == ["scratch=8", "check:[]"]
    assert SC.readback(out, "x")[0] == {4 * k: k for k in range(8)}
    none = probe_out("x", {})
    r = run_hooks(none, "probe --coords x", 1)
    assert "scratch=" not in r and "check:[]" in r        # the first unread row: no stop yet
    # the hook counts in its own shell (a subshell per $(...) here): the stop is the kit's; the
    # message is checked directly
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; JW="{KP}/debug/hooktest"; '
                       'UNREAD=1; hook_check x'], capture_output=True, text=True).stdout
    assert "the second output without its scratch readout" in r


def test_world_is_strict_and_prints_what_it_says():
    f = os.path.join(KP, "bins", "s-00-a.bin")
    assert WO.answer("t24", ["probe", "--bogus", f], "zx")["rc"] == 2
    assert WO.answer("t24", ["probe", "--pds", "36", f], "zx")["rc"] == 2
    assert WO.answer("t24", ["probe", "--poke", "bg:1=0", f], "zx")["rc"] == 2
    assert WO.answer("t24", ["probe", "--coords", "--temps", "0", f], "zx")["rc"] == 2
    assert WO.answer("t24", ["probe", "--coords", "--scratch-show", "65", f], "zx")["rc"] == 2
    assert WO.answer("t24", ["probe", "--coords", f, f], "zx")["rc"] == 2
    assert WO.answer("t24", ["copy", "--every-value"], "zx")["rc"] == 2
    a = WO.answer("t24", ["probe", "--coords", "--temps", "32", f], "zx")
    assert SC.readback(a["out"], "s-00-a")[0] == {4 * k: MK.zx(x, y) for k, (x, y) in
                                                  enumerate(MK.E1061_PAIRS)}
    a = WO.answer("t24", ["probe", "--coords", f], "mix")
    got = SC.readback(a["out"], "s-00-a")[0]
    assert got[0x10] == MK.zx(*MK.E1061_PAIRS[6]) and got[0x14] == MK.zx(*MK.E1061_PAIRS[7])
