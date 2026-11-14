# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py and gen/z17.py's models on kept records they must hold on
and must fail on (read at the frozen data commit), and on rows built from one model's prediction.

Kept records: E1064's zo-p-160 and zo-s-160 (the replicated controls, byte for byte), E1041's
zo-65-ov (zo2-c-65's first 3584 dwords) with zo-65-f0 and zo-63-f0 (the planes), E1031's
zf-flat-f6 (zb20-c-f6) and E1063's zb4-20-f6 and zb4-20-f7 (the pack rule at the kept size, in
test_gen.py). Every control PASSES on its kept record and FAILS on a changed byte; rows built
from a model's prediction hold it and fail its rivals (every pair parts on the built rows); a row
not given cannot tell; the zb20 rows are built from synthetic twins at the new sizes."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402
import z17 as Z  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def table(stage):
    return {ln.split("|")[0]: ln.rstrip("\n").split("|", 5)
            for ln in open(os.path.join(KP, f"tables/{stage}.txt"))
            if ln.strip() and not ln.startswith("#")}


def kept_dir(d, stage, jobs):
    """jobs: {name: (text, {suffix: bytes})}"""
    d.mkdir(parents=True)
    t = table(stage)
    rows = ["\t".join(COLS)]
    for n, (text, files) in jobs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        for suf, b in files.items():
            (d / f"{n}{suf}.gz").write_bytes(gzip.compress(b))
        r = t[n]
        rows.append("\t".join([n, stage, r[1], r[2], r[3], r[4], "x", "1", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, n):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {n}:")][0]


def held(out, n):
    ln = line(out, "ROW", n)
    return set(ln.rsplit(": held ", 1)[1].split(", ")) if ": held " in ln else set()


def pack(v):
    return struct.pack("<%dI" % len(v), *v)


def flip(x, at=100):
    y = bytearray(x)
    y[at] ^= 1
    return bytes(y)


def txt(w, h, drawn, depth=None, dst=None, sst=None):
    out = []
    if depth is not None:
        out.append(f"depth #1: 20480 dwords, {depth} changed, 2 distinct")
    if dst is not None:
        out.append(f"depth store #1: 20480 dwords, {dst} changed, 2 distinct")
    if sst is not None:
        out.append(f"stencil store #1: 20480 dwords, {sst} changed, 2 distinct")
    out.append("job: ok")
    out.append(f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other")
    return "\n".join(out) + "\n"


def store(pred, n=20480):
    v = [Z.FILL_DEAD] * n
    for i, x in pred.items():
        v[i] = x
    return pack(v)


def sstore(pred, n=20480):
    b = bytearray(struct.pack("<I", Z.FILL_DEAD) * n)
    for i, x in pred.items():
        b[i] = x
    return bytes(b)


DST, DEP, SST = SC.DST, SC.DEP, SC.SST


def kct(key, what):
    return Z.kept_count(key, what)


# ---- zovp2 -------------------------------------------------------------------------------------


def zovp2_controls():
    jobs = {"zo2-c-160": (txt(160, 48, kct("zo-p-160", "drawn"), dst=kct("zo-p-160", "depth store")),
                          {DST: Z.kept("zo-p-160.dst")})}
    for n in Z.OVC_ROWS:
        w, h, g, ref, gref = Z.OVC_ROWS[n]
        pred, drawn = Z.ovp_predict(Z.dwords(Z.kept(ref + ".dep")), w, h, g, gref,
                                    "H-OVL-PASS-EDGE", load=False)
        if n == "zo2-c-65":                                 # the kept zo-65-ov's own dwords
            ov = Z.dwords(Z.kept("zo-65-ov.dep"))
            pred = {i: ov[i] for i in range(3584)}
        jobs[n] = (txt(w, h, drawn, dst=len(pred)), {DST: store(pred)})
    return jobs


def test_zovp2_built_and_controls(tmp_path):
    jobs = zovp2_controls()
    for n, m in (("zo2-p-65", "H-OVL-PASS-EDGE"), ("zo2-p-63", "H-EDGE-SKIP")):
        w, h, g, ref, gref = Z.OVP_ROWS[n]
        p, d = Z.ovp_predict(Z.dwords(Z.kept(ref + ".dep")), w, h, g, gref, m)
        jobs[n] = (txt(w, h, d, dst=len(p)), {DST: store(p)})
    out = score("zovp2", kept_dir(tmp_path / "a", "zovp2", jobs))
    for c in ("zo2-c-160", "zo2-c-65", "zo2-c-63"):
        assert line(out, "CONTROL", c).endswith("PASS"), line(out, "CONTROL", c)
    assert held(out, "zo2-p-65") == {"H-OVL-PASS-EDGE"}
    assert held(out, "zo2-p-63") == {"H-EDGE-SKIP"}
    assert "READING zo2-p-65: dwords off the model" in out
    assert "SUMMARY: zovp2: H-OVL-PASS-EDGE is not supported: 1 held, 1 FAILED" in out
    assert "SUMMARY: zovp2: H-EDGE-SKIP is not supported: 1 held, 1 FAILED" in out
    # every model on a row built by the next: first, the first-visited slot owner
    w, h, g, ref, gref = Z.OVP_ROWS["zo2-p-65"]
    p, d = Z.ovp_predict(Z.dwords(Z.kept(ref + ".dep")), w, h, g, gref, "H-OVL-FIRST")
    jobs["zo2-p-65"] = (txt(w, h, d, dst=len(p)), {DST: store(p)})
    p, d = Z.ovp_predict(Z.dwords(Z.kept("zo-63-f0.dep")), 63, 31, 0, 1, "H-EDGE-EXT")
    jobs["zo2-p-63"] = (txt(63, 31, d, dst=len(p)), {DST: store(p)})
    out = score("zovp2", kept_dir(tmp_path / "b", "zovp2", jobs))
    assert held(out, "zo2-p-65") == {"H-OVL-FIRST"}
    assert held(out, "zo2-p-63") == {"H-EDGE-EXT"}
    # a changed byte fails a control and gates every model
    jobs["zo2-c-160"] = (jobs["zo2-c-160"][0], {DST: flip(Z.kept("zo-p-160.dst"))})
    out = score("zovp2", kept_dir(tmp_path / "c", "zovp2", jobs))
    assert line(out, "CONTROL", "zo2-c-160").endswith("FAILED")
    assert "SUMMARY: zovp2: H-OVL-FIRST: controls FAILED: zo2-c-160: FAILED" in out
    # zo2-c-65 fails when its first dwords differ from E1041's kept store
    jobs["zo2-c-160"] = zovp2_controls()["zo2-c-160"]
    pred = Z.dwords(jobs["zo2-c-65"][1][DST])
    pred[7] ^= 1
    jobs["zo2-c-65"] = (jobs["zo2-c-65"][0], {DST: pack(pred)})
    out = score("zovp2", kept_dir(tmp_path / "d", "zovp2", jobs))
    assert line(out, "CONTROL", "zo2-c-65").endswith("FAILED")
    # a row not given cannot tell
    del jobs["zo2-p-63"]
    out = score("zovp2", kept_dir(tmp_path / "e", "zovp2", jobs))
    assert "cannot tell" in line(out, "ROW", "zo2-p-63")


# ---- zovs2 -------------------------------------------------------------------------------------


def test_zovs2_built_and_controls(tmp_path):
    jobs = {"zo2-c-s160": (txt(160, 48, kct("zo-s-160", "drawn"),
                               sst=kct("zo-s-160", "stencil store")), {SST: Z.kept("zo-s-160.sst")})}
    for n, m in (("zo2-s-65", "H-EDGE-CLIP"), ("zo2-s-63", "H-OVL-PASS-EDGE")):
        w, h, g = Z.OVS_ROWS[n]
        p, d = Z.ovs_predict(w, h, g, m)
        jobs[n] = (txt(w, h, d, sst=1), {SST: sstore(p)})
    out = score("zovs2", kept_dir(tmp_path / "a", "zovs2", jobs))
    assert line(out, "CONTROL", "zo2-c-s160").endswith("PASS")
    assert held(out, "zo2-s-65") == {"H-EDGE-CLIP"} and held(out, "zo2-s-63") == {"H-OVL-PASS-EDGE"}
    assert "READING zo2-s-65: bytes off the model" in out
    jobs["zo2-c-s160"] = (jobs["zo2-c-s160"][0], {SST: flip(Z.kept("zo-s-160.sst"))})
    out = score("zovs2", kept_dir(tmp_path / "b", "zovs2", jobs))
    assert line(out, "CONTROL", "zo2-c-s160").endswith("FAILED")
    assert "controls FAILED" in out


# ---- zb20 --------------------------------------------------------------------------------------


def twin_dump(w, h, g, fmt, n=32768):
    """a synthetic bit-20-set twin: a record per slot at its start (format 6: 44 dwords; format 7:
    two runs of 12 in the first two tiles, none after), every value unique"""
    v = [Z.FILL_DEAD] * n
    for s in range(Z.tiles(w, h)[1] * (g + 1)):
        runs = [(0, 44)] if fmt == 6 else ([(0, 12), (256, 12)] if s < 2 else [])
        for off, k in runs:
            for j in range(k):
                v[512 * s + off + j] = 0x3F000000 + 1000 * s + off + j
    return v


def test_zb20_built_and_controls(tmp_path):
    f6 = Z.kept("zf-flat-f6.dep")
    jobs = {"zb20-c-f6": (txt(64, 32, 2048, depth=176, sst=0),
                          {DEP: f6, SST: Z.kept("zf-flat-f6.sst")})}
    want = {"zb20-b-6-96": "H-PACK-AFTER", "zb20-b-7-96": "H-PACK-SCALE",
            "zb20-b-6-128": "H-PACK2048", "zb20-b-7-128": "H-PACK-AFTER"}
    fills = pack([Z.FILL_DEAD] * 32768)
    for n, (fmt, w, h, g) in Z.ZB20_ROWS.items():
        tw = twin_dump(w, h, g, fmt)
        pred = Z.pack_predict(tw, w, h, g, want[n])
        row = [Z.FILL_DEAD] * 32768
        for i, x in pred.items():
            row[i] = x
        jobs[Z.zb20_twin_of(n)] = (txt(w, h, w * h, depth=1, sst=0), {DEP: pack(tw), SST: fills})
        jobs[n] = (txt(w, h, w * h, depth=1, sst=0), {DEP: pack(row), SST: fills})
    out = score("zb20", kept_dir(tmp_path / "a", "zb20", jobs))
    assert line(out, "CONTROL", "zb20-c-f6").endswith("PASS")
    for n, m in want.items():
        assert held(out, n) == {m}, (n, line(out, "ROW", n))
    assert "READING zb20-t-6-96: drawn 4608; records per slot [44, 44, 44, 44, 44, 44, 44, 44, 44]" in out
    assert "READING zb20-t-7-128: drawn 8192; records per slot [24, 24, 0, 0" in out
    # one dword off, the stencil store not the twin's, a wrong drawn count: each fails its model
    bad = Z.dwords(jobs["zb20-b-6-96"][1][DEP])
    bad[Z.pack_start("H-PACK-AFTER", 96, 48, 2) + 5] ^= 1
    jobs["zb20-b-6-96"] = (jobs["zb20-b-6-96"][0], {DEP: pack(bad), SST: fills})
    jobs["zb20-b-7-96"] = (jobs["zb20-b-7-96"][0], {DEP: jobs["zb20-b-7-96"][1][DEP],
                                                    SST: flip(fills, 8)})
    jobs["zb20-b-6-128"] = (txt(128, 64, 8000, depth=1, sst=0), jobs["zb20-b-6-128"][1])
    out = score("zb20", kept_dir(tmp_path / "b", "zb20", jobs))
    assert held(out, "zb20-b-6-96") == set() and held(out, "zb20-b-7-96") == set()
    assert held(out, "zb20-b-6-128") == set()
    assert held(out, "zb20-b-7-128") == {"H-PACK-AFTER"}
    # the control fails on a changed byte and gates the headline
    jobs["zb20-c-f6"] = (jobs["zb20-c-f6"][0], {DEP: flip(f6), SST: Z.kept("zf-flat-f6.sst")})
    out = score("zb20", kept_dir(tmp_path / "c", "zb20", jobs))
    assert line(out, "CONTROL", "zb20-c-f6").endswith("FAILED")
    assert "SUMMARY: zb20: H-PACK-AFTER: controls FAILED" in out
    # a missing twin cannot tell
    del jobs["zb20-t-7-128"]
    out = score("zb20", kept_dir(tmp_path / "d", "zb20", jobs))
    assert "cannot tell" in line(out, "ROW", "zb20-b-7-128")


def test_zb20_all_models_hold_when_they_agree():
    """at E1063's size the three starts are one: the scorer's rule holds on the kept pair"""
    tw = Z.dwords(Z.kept("zf-flat-f6.dep"))
    dep = Z.dwords(Z.kept("zb4-20-f6.dep"))
    for m in Z.PACK_MODELS:
        fit = SC._dict_fit(dep, Z.pack_predict(tw, 64, 32, 1, m), SC.fill_ok)
        assert fit[0], (m, fit)
