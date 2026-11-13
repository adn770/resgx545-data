# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept directories it must hold on and must fail on. No
kept record has a stencil test against a loaded stencil (Q121's gap): the outputs are the mock
world's (gen/st1.predict_from under H-DEPTHORD), and the same rows made under H-RASTER. The model
that made a row holds, the others FAIL; a control that draws the wrong count FAILS; a q071 row
whose store differs by one byte from its base row's FAILS H-INERT; a missing row cannot tell."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import st1 as S  # noqa: E402
import world as Wd  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def table():
    return {ln.split("|")[0]: ln.rstrip("\n").split("|", 5)
            for ln in open(os.path.join(KP, "tables/st1.txt")) if ln.strip() and not ln.startswith("#")}


def job(n):
    a = Wd.answer("t10", table()[n][5].replace('"$W"', "/W").split(), {"model"})
    return a["out"], a["files"]["/W/stencil-store.1.bin"]


def kept(d, jobs):
    d.mkdir(parents=True)
    t = table()
    rows = ["\t".join(COLS)]
    for n, (text, sst) in jobs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        (d / f"{n}.stencil-store.1.bin.gz").write_bytes(gzip.compress(sst))
        r = t[n]
        rows.append("\t".join([n, "st1", r[1], r[2], r[3], r[4], "x", "1", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "st1", str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, n):
    return [ln for ln in out.splitlines() if ln.split(" ")[:2] in (["ROW", n + ":"], ["CONTROL", n + ":"])][0]


def test_depthord_world_holds(tmp_path):
    out = score(kept(tmp_path / "k", {n: job(n) for n in S.ROWS}))
    for n in S.CONTROL_DRAWN:
        assert line(out, n).endswith("PASS"), line(out, n)
    for n in S.ROWS:
        if n in S.CONTROL_DRAWN:
            continue
        held = line(out, n).split("held ")[-1]
        assert held.startswith("H-INERT" if n.startswith("q071") else "H-DEPTHORD"), line(out, n)
    assert "SUMMARY: st1: H-DEPTHORD (13 of 13 rows decided)" in out
    assert "SUMMARY: st1: H-INERT (2 of 2 rows decided)" in out
    for m in ("H-RASTER", "H-F2ORD", "H-NOLOAD"):
        assert f"SUMMARY: st1: {m} is not supported" in out


def raster_job(n):
    w, h, fill, mode, m = S.ROWS[n][:5]
    drawn, sst = S.predict_from(w, h, fill, mode, m, "H-RASTER")
    text, store = job(n)
    rows = [f"row {y}: " + " ".join(f"{S.TRI_COLOUR if (x, y) in drawn else 0xff203040:#010x}"
                                    for x in range(w)) for y in range(h)]
    text = "\n".join(ln for ln in text.splitlines() if not ln.startswith("row ")) + "\n" + "\n".join(rows) + "\n"
    store = bytearray(store)
    for o, v in sst.items():
        store[o] = v
    return text, bytes(store)


def test_raster_rows_hold_raster_and_fail_depthord(tmp_path):
    jobs = {n: job(n) for n in S.CONTROL_DRAWN}
    for n in ("st1-b1", "st1-lane1", "st1-e-b0"):
        jobs[n] = raster_job(n)
    out = score(kept(tmp_path / "k", jobs))
    for n in ("st1-b1", "st1-lane1", "st1-e-b0"):
        assert line(out, n).endswith("held H-RASTER"), line(out, n)
    assert "SUMMARY: st1: H-DEPTHORD is not supported: 0 held, 3 FAILED" in out
    assert "q071-b0: H-INERT no image or dump" in out.replace("ROW ", "")


def test_control_and_inert_fail(tmp_path):
    jobs = {n: job(n) for n in S.ROWS}
    t, s = jobs["st1-never"]
    jobs["st1-never"] = (t.replace(" 0 triangle,", " 5 triangle,"), s)
    t, s = jobs["q071-l1"]
    jobs["q071-l1"] = (t, bytes([s[0] ^ 1]) + s[1:])
    out = score(kept(tmp_path / "k", jobs))
    assert line(out, "st1-never").endswith("FAILED")
    assert line(out, "q071-l1").endswith("no frozen model")
    assert "controls FAILED" in out
