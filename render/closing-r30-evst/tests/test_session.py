# SPDX-License-Identifier: MIT
"""r30-evst's offline tests: the generator is current; the argv twin (every row a plain 64 x 64
triangle of t10 under regtimeline, only registers the existing timeline tooling reads, E258's
register-timelines set and E547's event-timelines sets, and 0x0b14); the hooks' awk reader equals the scorer's on E547's kept
timelines and on synthetic ones; the hook's stops (hang latch, tick stop, cut, bad draw); the
scorer on the kept records it must hold on (E547's tri64 rows: bit 26 as 0x24000000, 53 to 81 us,
before the render end) and must fail on (E547's tri256n3 row, an edited word)."""
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
TL = "data:platform/event-bits/dumps/event-timelines/tl-"
FORMS = (["tri", "--width", "64", "--height", "64"],
         ["tri", "--width", "64", "--height", "64", "-n", "3"])


def blob(pin):
    assert pin in CFG["freeze"]["pins"], pin
    path = pin.partition(":")[2]
    r = subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"],
                       capture_output=True, timeout=60, check=True)
    return (gzip.decompress(r.stdout) if path.endswith(".gz") else r.stdout).decode()


def e547(name):
    return blob(TL + name + ".txt.gz")


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


def synth(rows, regs="0x0118 0x012c 0x0804 0x0b14", total=1.5, start=500_000_000,
          end=610_000_000, draw=True):
    head = ("tri: render context for targets up to 64x64\njob: ok\n" +
            ("diff: 0 of 4096 pixels\n" if draw else "") + "tri: 1 renders ok\n")
    n = len(regs.split())
    tl = f"timeline: regs {regs} samples {int(total * 1e9 / 1500)} seconds {total:g} start " \
         f"{start} end {end} rc 0\n"
    return head + tl + "".join(f"tl {t} " + " ".join("%08x" % v for v in vals[:n]) + "\n"
                               for t, vals in rows)


def ticking(extra=9, stop=False, latch=False, word26=0x24000000):
    """0x0b14 a count a ms over 1.5 s, `extra` more counts inside the job; one triangle."""
    rows, c = [], 0x0a00
    job = {540_000_000: word26, 540_080_000: 0x20000000, 540_100_000: 0x20040001,
           540_105_000: 0x20000000}
    ev = sorted([(t * 1_000_000 + 7, "tick") for t in range(1500)] +
                [(t, "w") for t in job] +
                [(540_000_000 + 9_000 * k, "x") for k in range(extra)])
    w = 0x20000000
    for t, kind in ev:
        if kind in ("tick", "x"):
            c += 1
        else:
            w = job[t]
        st2 = 0x480 if latch and w == word26 else 0x400
        se = (0 if stop and t > 1_400_000_000 else 0x10000) | (c & 0xffff)
        rows.append((t, [st2, w, 0x1000ffff, se]))
    return synth(rows)


# ---- the generator and the rows ------------------------------------------------------------
def test_generated_current():
    assert MK.main(["make.py", "--check"]) == 0


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["e1", "e5", "e2", "e3", "e4"]
    n = {st: len(SC.K.table(KP, st)) for st in CFG["stages"]}
    assert n == {"e1": 16, "e5": 7, "e2": 12, "e3": 10, "e4": 2}
    assert all(CFG["stages"][s].get("on_stop") == "end" for s in ("e2", "e3", "e4"))
    assert CFG["tools"]["rt"]["wraps"] is True


def test_argv_twin():
    e258 = blob("data:platform/register-timelines/output.txt")
    head = next(ln for ln in e258.splitlines() if ln.startswith("timeline: regs"))
    known = {int(x, 16) for x in head.split()[2:head.split().index("samples")]}
    # and E547's (event-timelines' r7 set, 0x0748 among them)
    for ln in blob("data:platform/event-bits/cases.tsv").splitlines()[1:]:
        f = ln.split("\t")[-1].split()
        if f[:1] == ["regtimeline"]:
            known |= set(SC.regs_of(" ".join(f[1:])))
    for r in table_rows():
        assert r["tool"] == "rt" and r["risk"] == "safe", r["name"]
        assert r["knobs"] in (["-"], [w for w in r["knobs"] if w.startswith("reads:")]), r
        a = shlex.split(r["args"].replace("$HOME", "/h"))
        i = a.index("--")
        assert a[i + 1] == "/h/sgxfive-test-t10" and a[i + 2:] in FORMS, r["name"]
        total, lead = float(a[0]), float(a[1])
        assert 0 <= lead <= 5.5 and (total == 0 or total > lead), r["name"]
        regs = set(SC.regs_of(r["args"]))
        assert 0x012c in regs
        # only registers the existing register-timeline tooling reads, and CR_USE0_SERV_EVENT
        # (which every kit job's regs snapshot reads, E009)
        assert regs - {0x0b14} <= known, (r["name"], sorted(hex(x) for x in regs - known))
        if r["set"] == "control":
            assert set(r["reads"]) <= SC.producible(r), r["name"]


def test_controls_frozen_and_rows_split():
    for st in CFG["stages"]:
        p = SC.K.predictions(KP, st)
        rows = SC.K.table(KP, st)
        assert rows[0]["set"] == "control"
        for r in rows:
            if r["set"] == "control":
                assert set(p[r["name"]]) == set(r["reads"]), r["name"]
        sets = [r["set"] for r in rows if r["set"] != "control"]
        assert sets == sorted(sets), st          # fit rows first, then held out


# ---- the readers --------------------------------------------------------------------------
def test_hooks_twin_on_kept_and_synthetic(tmp_path):
    texts = [e547(n) for n in ("tri64-r2-1", "tri64-r2-2", "tri64-r7-5", "idle-r2-1")]
    texts += [ticking()]
    for t in texts:
        w, a = rd_words(t, str(tmp_path)), SC.analyse(t)
        for k in ("idle", "idle2", "ivl", "cache", "se16"):
            if k in a or k in w:
                assert str(a.get(k)) == w.get(k), (k, a.get(k), w.get(k))
        if a.get("diff") is not None:
            assert int(w["diff"]) == a["diff"]


def test_hook_check_stops(tmp_path):
    t = str(tmp_path)
    assert check(ticking(), t) == ""
    assert "tick stopped" in check(ticking(stop=True), t)
    assert "hang latch" in check(ticking(latch=True), t)
    assert "wrong pixels" in check(ticking().replace("diff: 0 of", "diff: 3 of"), t)
    cut = ticking().replace("tl 2000007 ", "tl 2000007 00000400 ", 1)
    assert "cut" in check(cut, t)
    assert "no regtimeline sample" in check(ticking().split("timeline:")[0], t)
    # E547's kept rows sample no 0x0b14: the check passes them
    assert check(e547("tri64-r2-2"), t) == ""


def test_serv_event_reading():
    a = SC.analyse(ticking(extra=9))
    assert 0.99 <= a["tickrate"] <= 1.01 and a["seextra"] == 9
    a = SC.analyse(ticking(extra=0))
    assert a["seextra"] == 0
    assert a["cache"] == "0x1000ffff" and a["ccchg"] == 0 and a["st2"] == 0


# ---- the scorer on kept records -----------------------------------------------------------
def held(name, q, value):
    return SC.inside(SC.analyse(e547(name)).get(q), value)


def test_scorer_holds_on_e547_tri64():
    for n in ("tri64-r2-2", "tri64-r2-3", "tri64-r2-4", "tri64-r2-5", "tri64-r7-5"):
        assert held(n, "b26word", "0x24000000") is True, n
        assert held(n, "b26width", "40..140") is True, n
        assert held(n, "b26lead", "60..200") is True, n
        assert held(n, "b26clear", "1") is True, n
        assert held(n, "outside", "0") is True, n
        assert held(n, "sub", "0") is True, n
        assert held(n, "st2", "0") is True, n
    for n in ("tri64-r2-1", "tri64-r7-1", "tri64-r7-2", "tri64-r7-3", "tri64-r7-4"):
        a = SC.analyse(e547(n))
        assert a["b26seen"] == 0 and a["b26lead"] is None, n
        assert held(n, "b26word", "0x24000000") is None, n     # not seen: cannot tell
    seen = sum(SC.analyse(e547(f"tri64-r2-{i}"))["b26seen"] for i in range(1, 6))
    assert seen == 4                                            # E547's r2: 4 of 5
    a = SC.analyse(e547("idle-r2-1"))
    assert a["outside"] == 0 and a["bits"] == [] and a["idle"] == "0x20000000"


def test_scorer_fails_where_it_must():
    # E547's tri256n3 row: three bit 26 episodes, two of them 6.5 us, the first 67 ms before
    # a render end: H-WIDE and H-BEFORE's lead fail
    assert held("tri256n3-r7-1", "b26width", "40..140") is False
    assert held("tri256n3-r7-1", "b26lead", "60..200") is False
    assert SC.analyse(e547("tri256n3-r7-1"))["b26n"] == 3
    # an edited word (bit 18 with bit 26): H-ALONE fails
    t = e547("tri64-r2-2").replace(" 24000000", " 24040000", 1)
    assert SC.inside(SC.analyse(t)["b26word"], "0x24000000") is False
    # a word outside the job: H-IDLE fails
    t = synth([(1000, [0x400, 0x20000000]), (100_000_000, [0x400, 0x20004000]),
               (100_010_000, [0x400, 0x20000000])], regs="0x0118 0x012c")
    assert SC.inside(SC.analyse(t)["outside"], "0") is False
    # the tick model: 9 extra counts are not H-SE-TICKS
    assert SC.inside(SC.analyse(ticking(extra=9))["seextra"], "-1..1") is False
