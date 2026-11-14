# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py and gen/z16.py's models on kept records they must hold on
and must fail on (read at the frozen data commit), and on rows built from one model's prediction.

Kept records: E1050's zp-z125 (H-PASS-TWIN holds with its own store as the twin, H-PASS-OWN fails),
zp-c-467 and zp-f1 (the controls); E1042's zb2-c-base and zb2-b23, E1031's zf-flat-f6 (the
controls; H-B0 and H-INERT20 hold on the twin's own dumps with the twin's drawn count; zb2-b23
holds H23-FIXED and fails H23-BG); E996's zov-64x32-g0 (zo-c-64's owner rule without a load);
E987's zw-0125 (the control; H-LIN holds outside BEND, H-POLYCLIP fails). Every control PASSES on
its kept record and FAILS on a changed byte; rows built from a model's prediction hold it and fail
its rivals; a row not given cannot tell."""
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
import z16 as Z  # noqa: E402

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


def txt(w, h, drawn, depth=0, dst=None, sst=None, pixels=None, extra=""):
    out = [extra] if extra else []
    out.append(f"depth #1: 20480 dwords, {depth} changed, 2 distinct")
    if dst is not None:
        out.append(f"depth store #1: 20480 dwords, {dst} changed, 2 distinct")
    if sst is not None:
        out.append(f"stencil store #1: 18432 dwords, {sst} changed, 2 distinct")
    out.append("job: ok")
    out.append(f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other")
    if pixels is not None:
        out += [f"row {y}: " + " ".join(f"{Z.TRI_COLOUR if (x, y) in pixels else 0xFF203040:#010x}"
                                        for x in range(w)) for y in range(h)]
    return "\n".join(out) + "\n"


def store(pred, n=20480):
    v = [Z.FILL_DEAD] * n
    for i, x in pred.items():
        v[i] = x
    return pack(v)


def sstore(pred, n=18432):
    b = bytearray(struct.pack("<I", Z.FILL_DEAD) * n)
    for i, x in pred.items():
        b[i] = x
    return bytes(b)


DST, DEP, SST = SC.DST, SC.DEP, SC.SST


# ---- zpass2 ------------------------------------------------------------------------------------


def zp_controls():
    return {"zp2-c-467": (txt(256, 128, 16384, dst=1), {DST: Z.kept("zp-c-467.dst")}),
            "zp2-c-z125": (txt(64, 32, 2048, dst=1), {DST: Z.kept("zp-z125.dst")})}


def test_zpass2_on_kept_and_built(tmp_path):
    z125 = Z.kept("zp-z125.dst")
    jobs = zp_controls()
    jobs["zp2-t-z125"] = (txt(64, 32, 2048, dst=1), {DST: z125})        # the plane: zp-z125's own
    # 0.3: a twin of three floats about 0.3, the pass built by H-PASS-TWIN
    tw = [Z.FILL_DEAD] * 20480
    for i in range(2048):
        tw[i] = 0x3E999999 + i % 3
    pred, drawn = Z.pass_predict("z3", "H-PASS-TWIN", tw)
    jobs["zp2-p-z3"] = (txt(64, 32, drawn, dst=1), {DST: store(pred)})
    jobs["zp2-t-z3"] = (txt(64, 32, 2048, dst=1), {DST: pack(tw)})
    # 0.375: one float, the pass built by H-PASS-OWN (EXACT and TWIN hold with a one-float twin)
    pred, drawn = Z.pass_predict("z375", "H-PASS-OWN")
    jobs["zp2-p-z375"] = (txt(64, 32, drawn, dst=1), {DST: store(pred)})
    jobs["zp2-t-z375"] = (txt(64, 32, 2048, dst=1), {DST: store({i: 0x3EC00000 for i in range(2048)})})
    out = score("zpass2", kept_dir(tmp_path / "a", "zpass2", jobs))
    assert line(out, "CONTROL", "zp2-c-467").endswith("PASS")
    assert line(out, "CONTROL", "zp2-c-z125").endswith("PASS")
    assert held(out, "zp2-t-z125") == {"H-PASS-TWIN"}             # E1050's zp-z125: OWN fails
    assert held(out, "zp2-p-z3") == {"H-PASS-TWIN"}
    assert held(out, "zp2-p-z375") == {"H-PASS-TWIN", "H-PASS-OWN", "H-PASS-EXACT"}
    assert "cannot tell" in line(out, "ROW", "zp2-p-z1")
    assert "SUMMARY: zpass2: H-PASS-TWIN (3 of 7 rows decided)" in out
    # a changed byte fails a control
    jobs["zp2-c-z125"] = (jobs["zp2-c-z125"][0], {DST: flip(z125)})
    out = score("zpass2", kept_dir(tmp_path / "b", "zpass2", jobs))
    assert line(out, "CONTROL", "zp2-c-z125").endswith("FAILED")
    assert "SUMMARY: zpass2: H-PASS-TWIN (" not in out


# ---- zbits4 ------------------------------------------------------------------------------------


def twin_job(n, drawn=None, pixels=None):
    tw = Z.ZB4_TWIN[n]
    d = Z.kept_drawn(tw) if drawn is None else drawn
    return (txt(64, 32, d, depth=176, sst=0, pixels=pixels),
            {DEP: Z.kept(tw + ".dep"), SST: Z.kept(tw + ".sst")})


def b23_pixels(n):
    """the pixel set of a kept stencil row's text"""
    return SC.drawn_set(Z.kept(n + ".txt").decode()) if n + ".txt" in Z.KEPT else None


def test_zbits4_on_kept_and_built(tmp_path):
    base_px = SC.drawn_set(__import__("pins").blob("data:" + Z.R14Z + "zbits2/zb2-c-base.txt.gz").decode())
    b23_px = SC.drawn_set(__import__("pins").blob("data:" + Z.R14Z + "zbits2/zb2-b23.txt.gz").decode())
    jobs = {"zb4-c-base": twin_job("zb4-c-base", 1024, base_px),
            "zb4-c-b23": twin_job("zb4-c-b23", 1536, b23_px),
            "zb4-c-f6": twin_job("zb4-c-f6")}
    jobs["zb4-c-f6"] = (txt(64, 32, 2048, depth=176, sst=0), jobs["zb4-c-f6"][1])
    jobs["zb4-b0-st"] = twin_job("zb4-b0-st", 0)                  # the twin's dumps, no colour
    jobs["zb4-b0-f6"] = twin_job("zb4-b0-f6", 1024)               # the twin's dumps, drawn
    jobs["zb4-b0-c16"] = (txt(64, 32, 0, sst=0),                   # nothing stored
                          {DEP: pack([0x3F800000] * 18432), SST: sstore({})})
    jobs["zb4-20-f6"] = twin_job("zb4-20-f6")
    jobs["zb4-20-f7"] = (twin_job("zb4-20-f7")[0], {DEP: flip(Z.kept("zf-7k-3f.dep"), 8),
                                                    SST: Z.kept("zf-7k-3f.sst")})
    # E1042's zb2-b23 read as the background row: COL23, the source not the background
    jobs["zb4-23-bg"] = (txt(64, 32, 1536, sst=1, pixels=b23_px), {DEP: Z.kept("zb2-b23.dep"),
                                                                   SST: Z.kept("zb2-b23.sst")})
    # the mask row built from H23-FIXED; the reference row with one byte moved (H23-REF)
    pred, drawn = Z.b23_predict("zb4-23-msk", "H23-FIXED")
    px = {(x, y) for y in range(32) for x in range(64) if Z.COL23[x % 16] == 0}
    jobs["zb4-23-msk"] = (txt(64, 32, drawn, sst=1, pixels=px), {DEP: Z.kept("zb2-b23.dep"),
                                                                 SST: sstore(pred)})
    pred, drawn = Z.b23_predict("zb4-23-ref", "H23-FIXED")
    s = bytearray(sstore(pred))
    s[Z.st_pos(2, 0)] ^= 0x02
    jobs["zb4-23-ref"] = (txt(64, 32, drawn, sst=1, pixels=b23_px), {DEP: Z.kept("zb2-b23.dep"),
                                                                     SST: bytes(s)})
    for n in Z.OVS_ROWS:
        w, h, g = Z.OVS_ROWS[n]
        pred, drawn = Z.ovs_predict(w, h, g, "H-OVL-PASS" if n == "zo-s-64" else "H-OVL-SKIP")
        jobs[n] = (txt(w, h, drawn, sst=1), {DEP: pack([0x3F800000] * 18432), SST: sstore(pred, 30000)})
    out = score("zbits4", kept_dir(tmp_path / "a", "zbits4", jobs))
    for c in ("zb4-c-base", "zb4-c-b23", "zb4-c-f6"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    assert held(out, "zb4-b0-st") == {"H-B0"}
    assert held(out, "zb4-b0-f6") == set()
    assert held(out, "zb4-b0-c16") == {"H-B0-NOSTORE"}
    assert "cannot tell" in line(out, "ROW", "zb4-b0-f7")
    assert held(out, "zb4-20-f6") == {"H-INERT20"} and held(out, "zb4-20-f7") == set()
    assert held(out, "zb4-23-bg") == {"H23-FIXED", "H23-REF", "H23-MASK"}
    assert held(out, "zb4-23-msk") == {"H23-FIXED", "H23-REF", "H23-BG"}
    assert held(out, "zb4-23-ref") == {"H23-REF"}
    assert held(out, "zo-s-64") == {"H-OVL-PASS"} and held(out, "zo-s-160") == {"H-OVL-SKIP"}
    jobs["zb4-c-b23"] = (jobs["zb4-c-b23"][0], {DEP: Z.kept("zb2-b23.dep"),
                                                SST: flip(Z.kept("zb2-b23.sst"))})
    out = score("zbits4", kept_dir(tmp_path / "b", "zbits4", jobs))
    assert line(out, "CONTROL", "zb4-c-b23").endswith("FAILED")


# ---- zovp --------------------------------------------------------------------------------------


def test_owner_rule_on_e996():
    """zo-c-64's rule (no load: the clear 1.0, the slot the tile visited last) is E996's kept
    zov-64x32-g0 store, dword for dword"""
    full = Z.dwords(Z.kept("zov-64x32-ctl.dep"))
    pred, drawn = Z.ovp_predict(full, 64, 32, 0, 1, "H-OVL-PASS", load=False)
    g0 = Z.dwords(Z.kept("zov-64x32-g0.dep"))
    assert drawn == 2048 and len(pred) == 1536
    assert SC._dict_fit(g0, pred, SC.fill_ok)[0]


def test_zovp_built(tmp_path):
    g0 = Z.dwords(Z.kept("zov-64x32-g0.dep"))
    full = Z.dwords(Z.kept("zov-64x32-ctl.dep"))
    pred, _ = Z.ovp_predict(full, 64, 32, 0, 1, "H-OVL-PASS", load=False)
    jobs = {"zo-c-64": (txt(64, 32, 2048, dst=1536), {DST: store(pred)}),
            "zo-c-f1": (txt(64, 32, 1024, dst=2048), {DST: Z.kept("zp-f1.dst")})}
    assert len(g0) >= 1536
    for n, m in (("zo-p-64", "H-OVL-PASS"), ("zo-p-160", "H-OVL-FIRST")):
        w, h, g, ref, gref = Z.OVP_ROWS[n]
        p, d = Z.ovp_predict(Z.dwords(Z.kept(ref)), w, h, g, gref, m)
        jobs[n] = (txt(w, h, d, dst=1), {DST: store(p)})
    jobs["zo-n1-7fc"] = (txt(64, 32, 0, dst=2048), {DST: store(Z.nan_predict("zo-n1-7fc", "H-NAN-SAT"))})
    jobs["zo-n2-7f8"] = (txt(64, 32, 0, dst=1024), {DST: store(Z.nan_predict("zo-n2-7f8", "H-NAN-LOW"))})
    jobs["zb4-20-d12"] = (txt(64, 32, 0, dst=2048), {DST: Z.kept("zb2-d12.dst")})
    out = score("zovp", kept_dir(tmp_path / "a", "zovp", jobs))
    assert line(out, "CONTROL", "zo-c-64").endswith("PASS")
    assert line(out, "CONTROL", "zo-c-f1").endswith("PASS")
    assert held(out, "zo-p-64") == {"H-OVL-PASS"} and held(out, "zo-p-160") == {"H-OVL-FIRST"}
    assert held(out, "zo-n1-7fc") == {"H-NAN-SAT"} and held(out, "zo-n2-7f8") == {"H-NAN-LOW"}
    assert held(out, "zb4-20-d12") == {"H-INERT20"}
    assert "cannot tell" in line(out, "ROW", "zo-n1-ffc")
    jobs["zo-c-f1"] = (jobs["zo-c-f1"][0], {DST: flip(Z.kept("zp-f1.dst"))})
    out = score("zovp", kept_dir(tmp_path / "b", "zovp", jobs))
    assert line(out, "CONTROL", "zo-c-f1").endswith("FAILED")
    assert "SUMMARY: zovp: H-NAN-SAT: controls FAILED: zo-c-f1: FAILED" in out
    assert "SUMMARY: zovp: H-OVL-PASS is not supported: 1 held, 1 FAILED" in out   # zo-c-64 gates it


# ---- zoff --------------------------------------------------------------------------------------


def zw_dump(model, w, s):
    v = [Z.FILL_DEAD] * 49152
    for y in range(128):
        for x in range(256):
            dr, z = Z.zoff_pixel(model, w, s, x)
            if dr:
                v[Z.store_dword(x, y, 7)] = struct.unpack("<I", struct.pack("<f", z))[0]
    return pack(v)


def test_zoff_on_kept_and_built(tmp_path):
    zw = Z.dwords(Z.kept("zw-0125.dep"))
    assert Z.zoff_fit(zw, "H-LIN", 0.125, 0.5, Z.BEND())[0]
    assert not Z.zoff_fit(zw, "H-LIN", 0.125, 0.5)[0]
    assert not Z.zoff_fit(zw, "H-POLYCLIP", 0.125, 0.5, Z.BEND())[0]
    jobs = {"zw2-c-0125": (txt(256, 128, 32768, depth=32768), {DEP: Z.kept("zw-0125.dep")}),
            "zb4-20-640": (txt(640, 480, 307200, depth=307200), {DEP: Z.kept("zo-640-f0.dep")}),
            "zw2-w3": (txt(256, 128, 32768, depth=1), {DEP: zw_dump("H-LIN", 0.1875, 0.5)}),
            "zw2-w5": (txt(256, 128, 20480, depth=1), {DEP: zw_dump("H-POLYCLIP", 0.3125, 0.5)}),
            "zw2-s25": (txt(256, 128, 32768, depth=1), {DEP: zw_dump("H-LIN-S", 0.25, 0.25)}),
            "zw2-s75": (txt(256, 128, 32768, depth=1), {DEP: zw_dump("H-LIN", 0.25, 0.75)})}
    out = score("zoff", kept_dir(tmp_path / "a", "zoff", jobs))
    assert line(out, "CONTROL", "zw2-c-0125").endswith("PASS")
    assert held(out, "zb4-20-640") == {"H-INERT20"}
    assert held(out, "zw2-w3") == {"H-LIN"} and held(out, "zw2-w5") == {"H-POLYCLIP"}
    assert held(out, "zw2-s25") == {"H-LIN-S", "H-POLYCLIP"} and held(out, "zw2-s75") == {"H-LIN"}
    assert "cannot tell" in line(out, "ROW", "zw2-w0")
    jobs["zw2-c-0125"] = (jobs["zw2-c-0125"][0], {DEP: flip(Z.kept("zw-0125.dep"))})
    out = score("zoff", kept_dir(tmp_path / "b", "zoff", jobs))
    assert line(out, "CONTROL", "zw2-c-0125").endswith("FAILED")
