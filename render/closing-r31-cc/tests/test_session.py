# SPDX-License-Identifier: MIT
"""r31-cc's offline tests: the generator is current; the argv twin (every row a plain 64 x 64
triangle or the default fill of t10 under regtimeline, only registers the existing timeline
tooling reads: E258's register-timelines set and 0x0b14); the hooks' awk reader equals the
scorer's on E1120's kept rows and on synthetic ones; the hook's stops (tick stop, cut, bad draw,
no `fill: ok`); the scorer on the kept records it must hold on (E1120's e2, e3, e4 rows: one
change, the served count 5 to 7 us after it, CR_DMS_CTRL 31 to 49 us after it) and must fail on
(edited and synthetic timelines: a count or a BIF word before the change, no change)."""
import gzip
import os
import shlex
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import make as MK  # noqa: E402
import score as SC  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
R30 = "data:render/closing-r30-evst2/out/20261116-132348/"
TRI = ["tri", "--width", "64", "--height", "64"]
FILL = ["fill"]


def blob(pin):
    assert pin in CFG["freeze"]["pins"], pin
    path = pin.partition(":")[2]
    r = subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"],
                       capture_output=True, timeout=60, check=True)
    return (gzip.decompress(r.stdout) if path.endswith(".gz") else r.stdout).decode()


def kept(name):
    return blob(R30 + name + ".txt.gz")


def table_rows():
    out = []
    for st in CFG["stages"]:
        out += [dict(r, stage=st) for r in SC.K.table(KP, st)]
    return out


def rd_words(text, tmp):
    p = os.path.join(tmp, "x.out")
    open(p, "w").write(text)
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "-", p],
                       capture_output=True, text=True, check=True)
    return dict(ln.split("=", 1) for ln in r.stdout.split())


def check(text, tmp, name="x"):
    open(os.path.join(tmp, name + ".out"), "w").write(text)
    r = subprocess.run(["bash", "-c", f'JW="{tmp}"; . "{KP}/run/hooks.sh"; hook_check {name}'],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


REGS5 = (0x012c, 0x0804, 0x0a74, 0x0b14, 0x0c00)


def synth(cc=540_000_000, count_at=6_000, bif_at=None, bif_word=0x8, dms_at=38_000,
          b26=(30_000, 36_000), stop=False, fill=False, change=True, regs=REGS5):
    """One job's text: t10's lines, then a timeline of REGS over 1.5 s from 0, the tool started
    at 0.5 s, ticks every 1002.5 us from 7 us; around the change at `cc` (ns): a served count
    `count_at` ns after it (negative: before), a BIF word over 400 ns at cc + `bif_at`, the DMS
    write and bit 26's episode at the offsets given, the render end 100 us on."""
    ev = {}
    for k in range(1497):
        ev.setdefault(7_000 + k * 1_002_500, []).append(("tick",))
    if change:
        ev.setdefault(cc, []).append(("cc",))
    ev.setdefault(cc + count_at, []).append(("tick",))
    if bif_at is not None:
        ev.setdefault(cc + bif_at, []).append(("bif", bif_word))
        ev.setdefault(cc + bif_at + 400, []).append(("bif", 0))
    ev.setdefault(cc + dms_at, []).append(("dms",))
    ev.setdefault(cc + b26[0], []).append(("w", 0x24000000))
    ev.setdefault(cc + b26[1], []).append(("w", 0x20000000))
    ev.setdefault(cc + 100_000, []).append(("w", 0x20040001))
    ev.setdefault(cc + 105_000, []).append(("w", 0x20000000))
    st = dict(w=0x20000000, cc=0x0000ffff, cnt=0x0a00, bif=0, dms=0x00208200)
    rows = [(0, dict(st))]
    for t in sorted(ev):
        for e in ev[t]:
            if e[0] == "tick":
                st["cnt"] += 1
            elif e[0] == "cc":
                st["cc"] = 0x1000ffff
            elif e[0] == "bif":
                st["bif"] = e[1]
            elif e[0] == "dms":
                st["dms"] = 0x50208200
            else:
                st["w"] = e[1]
        rows.append((t, dict(st)))
    col = {0x012c: "w", 0x0804: "cc", 0x0a74: "dms", 0x0c00: "bif"}

    def word(s, r, t):
        if r == 0x0b14:
            return (0 if stop and t > 1_400_000_000 else 0x10000) | (s["cnt"] & 0xffff)
        return s[col[r]]
    head = ("programs asm\njob: ok\ntarget: 64x32 hash 0xb60c6095080bd325\n"
            "diff: 0 of 2048 pixels\noutside: 0 dwords\nfill: ok, 64x32 at (0, 0), stride 256, "
            "colour 0xff336699\n") if fill else \
        "tri: render context for targets up to 64x64\njob: ok\ndiff: 0 of 4096 pixels\n" \
        "tri: 1 renders ok\n"
    tl = (f"timeline: regs {' '.join('0x%04x' % r for r in regs)} samples 900000 seconds 1.5 "
          f"start 500000000 end 610000000 rc 0\n")
    return head + tl + "".join(f"tl {t} " + " ".join("%08x" % word(s, r, t) for r in regs) + "\n"
                               for t, s in rows)


# ---- the generator and the rows ------------------------------------------------------------
def test_generated_current():
    assert MK.main(["make.py", "--check"]) == 0


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["c1", "c2", "c3", "c4", "c5"]
    n = {st: len(SC.K.table(KP, st)) for st in CFG["stages"]}
    assert n == {"c1": 10, "c2": 12, "c3": 12, "c4": 10, "c5": 8}
    assert all(CFG["stages"][s].get("on_stop") == "end" for s in CFG["stages"])
    assert all("class" not in CFG["stages"][s] for s in CFG["stages"])
    assert CFG["tools"]["rt"]["wraps"] is True
    assert not CFG["knobs"] and not CFG["kregs"]


def test_argv_twin():
    e258 = blob("data:platform/register-timelines/output.txt")
    head = next(ln for ln in e258.splitlines() if ln.startswith("timeline: regs"))
    known = {int(x, 16) for x in head.split()[2:head.split().index("samples")]}
    for ln in blob("data:platform/event-bits/cases.tsv").splitlines()[1:]:
        f = ln.split("\t")[-1].split()
        if f[:1] == ["regtimeline"]:
            known |= set(SC.regs_of(" ".join(f[1:])))
    for r in table_rows():
        assert r["tool"] == "rt" and r["risk"] == "safe", r["name"]
        assert r["knobs"] in (["-"], [w for w in r["knobs"] if w.startswith("reads:")]), r
        a = shlex.split(r["args"].replace("$HOME", "/h"))
        i = a.index("--")
        assert a[i + 1] == "/h/sgxfive-test-t10", r["name"]
        assert a[i + 2:] == (FILL if r["stage"] == "c5" else TRI), r["name"]
        assert a[:2] == ["1.5", "0.5"], r["name"]
        regs = set(SC.regs_of(r["args"]))
        assert 0x0804 in regs
        # only registers the existing register-timeline tooling reads (E258, E547), and
        # CR_USE0_SERV_EVENT (every kit job's regs snapshot reads it, E009, E1120)
        assert regs - {0x0b14} <= known, (r["name"], sorted(hex(x) for x in regs - known))
        if r["set"] == "control":
            assert set(r["reads"]) <= SC.producible(r), r["name"]


def test_controls_frozen_and_rows_split():
    for st in CFG["stages"]:
        p = SC.K.predictions(KP, st)
        rows = SC.K.table(KP, st)
        assert rows[0]["set"] == "control" and rows[-1]["set"] == "control"
        for r in rows:
            if r["set"] == "control":
                assert set(p[r["name"]]) == set(r["reads"]), r["name"]
        assert {r["set"] for r in rows if r["set"] != "control"} == {"held"}, st


def test_the_control_premises_are_the_kits_snapshot_after_the_reset():
    snap = blob(R30 + "e2/e2-c1.snap0.regs.gz").splitlines()
    for reg, want in (("0x0804", "0x0000ffff"), ("0x0c00", "0x00000000"),
                      ("0x0a74", "0x00208200")):
        assert f"reg {reg} {want}" in snap, reg
    for st in CFG["stages"]:
        p = SC.K.predictions(KP, st)[f"{st}-c1"]
        assert list(p["cache"].values()) == ["0x0000ffff"]
        if "bif0" in p:
            assert list(p["bif0"].values()) == ["0x00000000"]
        if "dms0" in p:
            assert list(p["dms0"].values()) == ["0x00208200"]


def test_xfer_premise_the_kept_fill_snapshots():
    for d in ("data:render/closing-r8-k2/out/20261113-032428/xf/xf-c-fill",
              "data:render/closing-r9-faults/out/20261113-084720/xf2/xf-c-fill"):
        assert "reg 0x0804 0x0000ffff" in blob(d + ".snap0.regs.gz").splitlines(), d
        assert "reg 0x0804 0x1000ffff" in blob(d + ".snap9.regs.gz").splitlines(), d
    out = blob("data:render/closing-r8-k2/out/20261113-032428/xf/xf-c-fill.txt.gz")
    assert "job: ok" in out and "diff: 0 of 2048 pixels" in out


# ---- the readers --------------------------------------------------------------------------
def test_hooks_twin_on_kept_and_synthetic(tmp_path):
    texts = [kept(n) for n in ("e2/e2-03", "e2/e2-04", "e3/e3-07", "e4/e4-01")]
    texts += [synth(), synth(fill=True), synth(regs=(0x0804,)), synth(regs=(0x0804, 0x0c00))]
    for t in texts:
        w, a = rd_words(t, str(tmp_path)), SC.analyse(t)
        for k in ("idle", "ivl", "cache", "se16", "bif0", "dms0"):
            if k in a or k in w:
                assert str(a.get(k)) == w.get(k), (k, a.get(k), w.get(k))
        assert int(w["diff"]) == a["diff"]


def test_hook_check_stops(tmp_path):
    t = str(tmp_path)
    assert check(synth(), t) == ""
    assert check(synth(fill=True), t) == ""
    assert "tick stopped" in check(synth(stop=True), t)
    assert "wrong pixels" in check(synth().replace("diff: 0 of", "diff: 3 of"), t)
    assert "fill: ok" in check(synth(fill=True).replace("fill: ok,", "fill: FAIL,"), t)
    cut = synth().replace("tl 7000 ", "tl 7000 00000400 ", 1)
    assert "cut" in check(cut, t)
    assert "no regtimeline sample" in check(synth().split("timeline:")[0] + "tri: 1 renders ok\n",
                                            t)
    assert check(kept("e2/e2-04"), t) == ""


def test_ticks_near():
    lead = [7_000 + k * 1_002_500 for k in range(400)]
    assert SC.ticks_near(lead, 500_000_000, 500_030_000) is False
    p = 7_000 + 500 * 1_002_500
    assert SC.ticks_near(lead, p - 20_000, p - 10_000) is True     # within 15 us of a tick
    assert SC.ticks_near(lead, p + 20_000, p + 50_000) is False
    assert SC.ticks_near(lead[:2], 0, 1) is True                    # no cadence: cannot tell


# ---- the scorer on the kept rows the models were read from (post hoc there) -----------------
def test_the_models_hold_on_e1120s_rows():
    a = SC.analyse(kept("e2/e2-04"))
    assert a["ccn"] == 1 and a["ccword"] == "0x1000ffff" and a["ccback"] == 0
    assert a["cntlag"] == 5.1 and a["cntpre"] == 0 and SC.inside(a["ccstart"], "10..40")
    assert a["cc26"] == 106.6 and a["ccfirst"] == 1
    a = SC.analyse(kept("e2/e2-03"))
    assert a["cntlag"] == 0.0 and a["cntpre"] == 0 and a["cc26"] == 35.0
    assert SC.analyse(kept("e2/e2-01"))["cntpre"] is None     # a tick 40 us before the change
    assert SC.analyse(kept("e2/e2-05"))["cntlag"] is None     # a tick 6.7 us before it
    a = SC.analyse(kept("e3/e3-07"))
    assert a["dmslag"] == 48.3 and a["dms26"] is None          # bit 26 in the same sample
    a = SC.analyse(kept("e3/e3-05"))
    assert SC.inside(a["dmslag"], "20..70") and a["dms26"] == 1
    a = SC.analyse(kept("e4/e4-01"))
    assert a["cntlag"] == 5.4 and SC.inside(a["cc26"], "15..120")
    for n in ("e2/e2-03", "e2/e2-04", "e3/e3-07", "e4/e4-01"):
        assert "biford" not in SC.analyse(kept(n))             # 0x0c00 not sampled in E1120


def test_the_models_fail_where_they_must():
    # a served count 10 us before the change: H-CNT-LAG's cntpre fails, H-CNT-LEAD holds
    a = SC.analyse(synth(count_at=-10_000))
    assert SC.inside(a["cntpre"], "0") is False and SC.inside(a["cntpre"], "1") is True
    # 20 us after it: outside H-CNT-LAG's 0 to 12
    assert SC.inside(SC.analyse(synth(count_at=20_000))["cntlag"], "0..12") is False
    # a BIF word 5 us before the change: "pre" (H-BIF-FIRST); 5 us after: "post"; in the
    # change's own sample only, or none: cannot tell
    assert SC.analyse(synth(bif_at=-5_000))["biford"] == "pre"
    assert SC.analyse(synth(bif_at=5_000))["biford"] == "post"
    assert SC.analyse(synth(bif_at=0))["biford"] is None
    assert SC.analyse(synth(bif_at=0))["bifsame"] == 1
    assert SC.analyse(synth())["biford"] is None
    assert SC.analyse(synth(bif_at=-5_000))["bifwords"] == "0x00000008"
    # no change: H-CC-XFER fails, H-CC-TA holds
    a = SC.analyse(synth(change=False, fill=True))
    assert SC.inside(a["ccn"], "1") is False and SC.inside(a["ccn"], "0") is True
    assert a["cntlag"] is None and a["biford"] is None
    # the DMS write before bit 26: H-WAIT fails; 80 us on: H-DMS fails
    assert SC.inside(SC.analyse(synth(dms_at=20_000))["dms26"], "1") is False
    assert SC.inside(SC.analyse(synth(dms_at=80_000))["dmslag"], "20..70") is False
    # an event bit before the change: H-CCFIRST fails
    a = SC.analyse(synth(b26=(-3_000, 2_000)))
    assert a["ccfirst"] == 0
    # a second change of 0x0804 (back to its reset word): H-CC-ONE fails
    t = synth()
    lines = t.splitlines()
    i = next(k for k, ln in enumerate(lines)
             if ln.startswith("tl ") and int(ln.split()[1]) > 541_000_000)
    p = lines[i].split()
    p[3] = "0000ffff"
    lines[i] = " ".join(p)
    a = SC.analyse("\n".join(lines) + "\n")
    assert SC.inside(a["ccn"], "1") is False or SC.inside(a["ccback"], "0") is False
