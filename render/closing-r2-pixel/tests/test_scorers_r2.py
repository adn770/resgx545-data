#!/usr/bin/env python3
"""The R2 scorers on landed data (S1b's kept p-d images, S1's d-L2e2-16 fault, S3's kept a4 run) and on synthetic worlds
(every control's failure, void data, each verdict, held-out vs repeat tallied apart, the slack pair and its gate, the freeze
refusal).  Prints ok / FAIL lines; exit 1 on any FAIL.   PY tests/test_scorers_r2.py   (the pixel-faults venv)"""
import contextlib
import gzip
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R2, "score"))
sys.path.insert(0, os.path.join(R2, "gen"))
import r2lib as L  # noqa: E402
import r2models as M  # noqa: E402
import score_r2 as S  # noqa: E402

FX = os.path.join(R2, "tests", "fixtures")
ROOT = tempfile.mkdtemp(prefix="r2-scorer-tests-")
HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"
IDLE = (0x20000000, 0x400, 0x80000, 0)
failed, nok = [], 0


def check(cond, what):
    global nok
    if cond:
        nok += 1
        print("ok   " + what)
    else:
        failed.append(what)
        print("FAIL " + what)


def gz(path, data):
    with gzip.open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


def regs(t):
    st, st2, i, f = t
    return "sgxfive regs 1\nreg 0x0118 %#010x\nreg 0x012c %#010x\nreg 0x0c00 0x00000000\nreg 0x0c04 %#010x\nreg 0x0c08 %#010x\n" % (
        st2, st, i, f)


def stage(name, jobs):
    """jobs: {case: dict(rc, cls, held, out, dmesg, snaps{k: tuple}, tadata, mode)}; returns the directory."""
    d = tempfile.mkdtemp(prefix=name + "-", dir=ROOT)
    rows = [HEAD]
    for case, j in jobs.items():
        rows.append("\t".join([case, name, "x", "x", "x", "x", "x", str(j.get("rc", 0)), j.get("cls", "ok"),
                               j.get("mode", "plain"), "-", "0", j.get("held", "no")]))
        if j.get("out") is not None:
            gz(os.path.join(d, case + ".txt.gz"), j["out"])
        gz(os.path.join(d, case + ".dmesg.gz"), j.get("dmesg", ""))
        for k, t in j.get("snaps", {}).items():
            gz(os.path.join(d, "%s.snap%d.regs.gz" % (case, k)), regs(t))
        if j.get("tadata") is not None:
            gz(os.path.join(d, case + ".tri.tadata.bin.gz"), j["tadata"])
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return d


def run(stage_name, d):
    S.preds()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = S.run_stage(stage_name, d)
    return res["summary"], buf.getvalue()


def verdict(root):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        S.verdict(root)
    out = buf.getvalue()
    q281 = [x for x in out.splitlines() if "Q281" in x][0]
    q286 = [x for x in out.splitlines() if "Q286" in x][0]
    return q281, q286


# =============================================================================================== D2
def probe_out(name, pages, px=None, extra="", fail=None):
    t = "programs asm\nprobe %s: scratch at 0x3e003000 (%d KiB)\n" % (name, pages * 4) + extra
    if fail:
        return t + "probe %s: failed: %s\n" % (name, fail)
    t += "probe %s: job time: 548 us\n" % name
    for r in range(32):
        t += "probe %s: row %d: %s\n" % (name, r, " ".join("%08x" % v for v in px[r * 64:(r + 1) * 64]))
    return t


L2 = "s1d-tw64x64-l2e2__0"
X1 = "s1d-tw64x64-l2e2-x1__0"
FAULT_DMESG = ("[1.0] gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90002 at 0x3e017001 (PD 0x1830a000) stalls job 8600, recovering\n")


def d_safe_jobs(**over):
    img19, img19x = M.image(19), M.image(19, 1)
    a4 = {r[0]: [int(v, 16) for v in r[3].split(",")] for r in (x.split("\t") for x in open(os.path.join(R2, "gen/data/s1b_p-d-A4.tsv")).read().splitlines()[1:])}
    j = {
        "d-ok-64": {"out": probe_out("s1d-tw128x32-l0e2__0", 64, a4["d-ok-64"])},
        "d-L2e2-19": {"out": probe_out(L2, 19, img19)},
        "d-L2e2-19x": {"out": probe_out(X1, 19, img19x)},
        "d-L2e2-18x": {"out": probe_out(X1, 18, [0xDEADBEEE] * 2048)},
        "d-L2e2-18": {"out": probe_out(L2, 18, fail="no pixel written"), "rc": 3},
    }
    for k, v in over.items():
        k = k.replace("_", "-")
        j[k] = dict(j[k], **v) if v is not None else None
    return {k: v for k, v in j.items() if v is not None}


def d_fault_jobs(**over):
    j = {
        "d-L2e2-17": {"out": probe_out(L2, 17, fail="job faulted, context lost"), "rc": 3, "cls": "fault", "dmesg": FAULT_DMESG},
        "d-L2e2-16": {"out": probe_out(L2, 16, fail="job faulted, context lost"), "rc": 3, "cls": "fault", "dmesg": FAULT_DMESG},
    }
    for k, v in over.items():
        k = k.replace("_", "-")
        j[k] = dict(j[k], **v) if v is not None else None
    return {k: v for k, v in j.items() if v is not None}


S.preds()
# ---- landed data: S1b's kept images, S1's kept fault ---------------------------------------------
fx = {n: L.read_text(os.path.join(FX, "s1b-p-d", n + ".txt.gz")) for n in ("d-ok-64", "d-L2e2-19", "d-L2e2-18", "d-L2e2-20", "d-L2e2-21")}
check(L.probe_rows(fx["d-L2e2-19"]) == M.image(19), "the model reproduces S1b's measured 19-page image (2048 of 2048)")
check(L.probe_rows(fx["d-L2e2-20"]) == M.image(20) and L.probe_rows(fx["d-L2e2-21"]) == M.image(21), "... and the 20- and 21-page images")
check(L.pix_hash(L.probe_rows(fx["d-ok-64"])) == S.pv(S.PD, "d-ok-64", "pix_sha256_if_complete"), "S1b's d-ok-64 image has the frozen A4 hash")
check(L.pix_hash(L.probe_rows(fx["d-L2e2-19"])) == S.pv(S.PD, "d-L2e2-19", "pix_sha256_if_complete"), "S1b's measured 19-page image has the frozen hash (byte for byte)")
real_safe = {"d-ok-64": {"out": fx["d-ok-64"]}, "d-L2e2-19": {"out": fx["d-L2e2-19"]},
             "d-L2e2-18": {"out": fx["d-L2e2-18"], "rc": 3}}
s, txt = run("r2-d-safe", stage("r2-d-safe", real_safe))
check("d-ok-64: complete: A4 exact" in txt and "d-L2e2-19: complete: byte-identical to S1b's image" in txt, "real S1b d-ok-64 and d-L2e2-19 outputs score PASS")
check("d-L2e2-18: rc3 no pixel written (S1b measured" in txt and "d-L2e2-18': 'PASS'" in s, "real S1b d-L2e2-18 (rc 3, no pixel written) scores PASS (a repeat)")
real_f = L.read_text(os.path.join(FX, "s1-p-d", "d-L2e2-16.txt.gz")), L.read_text(os.path.join(FX, "s1-p-d", "d-L2e2-16.dmesg.gz"))
s, txt = run("r2-d-fault", stage("r2-d-fault", {"d-L2e2-16": {"out": real_f[0], "dmesg": real_f[1], "rc": 3, "cls": "fault"}}))
check("d-L2e2-16: fault 0x90002 at 0x3e017001" in txt, "real S1 d-L2e2-16 fault (0x90002 at 0x3e017001) scores PASS")
check("d-L2e2-16': 'PASS'" in s, "  the control passes on the real kernel log")
# ---- the passing base ----------------------------------------------------------------------------
s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs()))
check("held out {'d-L2e2-18x': 'HL'}" in s and "repeat (fit, tallied apart) {'d-L2e2-18': 'PASS'}" in s and "cannot tell" not in s, "d-safe: HL base, held out and repeat tallied apart")
s, txt = run("r2-d-fault", stage("r2-d-fault", d_fault_jobs()))
check("held out {'d-L2e2-17': 'HL'}" in s, "d-fault: 17 pages faults 0x90002 at 0x3e017001 (HL)")
root = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
os.rename(stage("r2-d-safe", d_safe_jobs()), os.path.join(root, "r2-d-safe"))
os.rename(stage("r2-d-fault", d_fault_jobs()), os.path.join(root, "r2-d-fault"))
q281, _ = verdict(root)
check("HL: all 2 held-out rows agree (d-L2e2-18x, d-L2e2-17)" in q281, "Q281 verdict: HL on the base")
# ---- held-out rows against HL ---------------------------------------------------------------------
for what, over, key in (
        ("18x: rc 3 no pixel written", {"d_L2e2_18x": {"out": probe_out(X1, 18, fail="no pixel written"), "rc": 3}}, "d-L2e2-18x': 'HS'"),
        ("18x: sample wrote nothing (0xA0A1A2A2)", {"d_L2e2_18x": {"out": probe_out(X1, 18, [0xA0A1A2A2] * 2048)}}, "d-L2e2-18x': 'HS'"),
        ("18x: another image", {"d_L2e2_18x": {"out": probe_out(X1, 18, [0xDEADBEEE] * 2000 + [1] * 48)}}, "d-L2e2-18x': 'HS'")):
    s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(**over)))
    check(key in s and "cannot tell" not in s.split(";")[0], "18x: " + what + " -> HS")
    r2 = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
    os.rename(stage("r2-d-safe", d_safe_jobs(**over)), os.path.join(r2, "r2-d-safe"))
    os.rename(stage("r2-d-fault", d_fault_jobs()), os.path.join(r2, "r2-d-fault"))
    check("HL REFUTED" in verdict(r2)[0], "  verdict: HL refuted (" + what + ")")
s, txt = run("r2-d-fault", stage("r2-d-fault", d_fault_jobs(d_L2e2_17={"out": probe_out(L2, 17, M.image(19)), "rc": 0, "cls": "ok", "dmesg": ""})))
check("d-L2e2-17': 'HS'" in s, "d-L2e2-17 completing is HS (refutes the layout's end of the coords surface)")
s, txt = run("r2-d-fault", stage("r2-d-fault", d_fault_jobs(d_L2e2_17={"dmesg": FAULT_DMESG.replace("0x3e017001", "0x3e018001")})))
check("d-L2e2-17': 'OTHER'" in s and "cannot tell for d-L2e2-17" in s, "d-L2e2-17 faulting at another address is OTHER (neither HL nor HS)")
# ---- controls: each failure -> cannot tell ---------------------------------------------------------
s, _ = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_ok_64={"out": probe_out("s1d-tw128x32-l0e2__0", 64, [0xD0000000] * 2048)})))
check("cannot tell for" in s and "d-ok-64" in s, "d-ok-64 not the A4 image: cannot tell")
img = M.image(19); img[100] ^= 4
s, _ = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_19={"out": probe_out(L2, 19, img)})))
check("cannot tell for" in s and "d-L2e2-18x" in s and "not byte-identical" in s, "d-L2e2-19 one word different: not byte-identical, 18x cannot tell")
r3 = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
os.rename(stage("r2-d-safe", d_safe_jobs(d_L2e2_19={"out": probe_out(L2, 19, img)})), os.path.join(r3, "r2-d-safe"))
os.rename(stage("r2-d-fault", d_fault_jobs()), os.path.join(r3, "r2-d-fault"))
check(verdict(r3)[0].startswith("SUMMARY: Q281: cannot tell: d-L2e2-19 is not byte-identical"), "Q281 verdict: d-L2e2-19 not byte-identical -> cannot tell")
s, _ = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_19x={"out": probe_out(X1, 19, M.image(19))})))
check("d-L2e2-18x" in s and "variant control d-L2e2-19x FAIL" in s, "the xor control d-L2e2-19x failing makes 18x cannot tell")
s, _ = run("r2-d-fault", stage("r2-d-fault", d_fault_jobs(d_L2e2_16={"out": probe_out(L2, 16, M.image(19)), "rc": 0, "cls": "ok", "dmesg": ""})))
check("d-L2e2-17" in s and "16-page control did not fault" in s and "d-L2e2-16': 'FAIL'" in s, "the 16-page control not faulting makes d-17 cannot tell")
s, _ = run("r2-d-fault", stage("r2-d-fault", d_fault_jobs(d_L2e2_16={"dmesg": FAULT_DMESG.replace("0x90002", "0x90004")})))
check("d-L2e2-16': 'FAIL'" in s, "the 16-page control faulting with another word fails")
# ---- void states -----------------------------------------------------------------------------------
for what, over in (("no output", {"out": None}), ("rc 124", {"rc": 124}), ("empty pixel rows", {"out": "probe x: scratch at 0x3e003000 (76 KiB)\n"}),
                   ("another scratch base", {"out": probe_out(L2, 19, M.image(19)).replace("0x3e003000", "0x3e004000")}),
                   ("another page count", {"out": probe_out(L2, 20, M.image(19))}),
                   ("2047 pixels", {"out": probe_out(L2, 19, M.image(19)).replace("\nprobe %s: row 31:" % L2, "\nXX 31:")})):
    s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_19=over)))
    check("d-L2e2-19: NODATA" in txt and "cannot tell" in s, "void: d-L2e2-19 with " + what)
s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_18x=None)))
check("d-L2e2-18x: NODATA (no cases.tsv row (not run))" in txt, "void: a row that was not run (skipped group or stop)")
# the tool's message is searched in the whole output, not a truncated tail (R1-events)
big = probe_out(L2, 18, fail="no pixel written") + ("padding line %d\n" % 1) * 1000
s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_18={"out": big})))
check("d-L2e2-18: rc3 no pixel written" in txt, "'no pixel written' found with 6000+ characters after it")
big2 = ("noise\n" * 2000) + probe_out(L2, 19, M.image(19))
s, txt = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs(d_L2e2_19={"out": big2})))
check("d-L2e2-19: complete: byte-identical" in txt, "scratch line and rows found with 12000 characters of noise before them")
# the gate of the D fault stage
rg = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
os.rename(stage("r2-d-safe", d_safe_jobs(d_ok_64={"out": probe_out("s1d-tw128x32-l0e2__0", 64, [0] * 2048)})), os.path.join(rg, "r2-d-safe"))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = S.gate("r2-d-fault", [rg])
check(g == 1 and "rerun: run/r2.sh --only r2-d-safe" in buf.getvalue(), "gate r2-d-fault closed when d-ok-64 failed, names r2-d-safe")
rg2 = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
os.rename(stage("r2-d-safe", d_safe_jobs()), os.path.join(rg2, "r2-d-safe"))
with contextlib.redirect_stdout(io.StringIO()):
    check(S.gate("r2-d-fault", [rg, rg2]) == 1 and S.gate("r2-d-fault", [rg2, rg]) == 0, "gates read the first root that has the stage (a later attempt's rerun wins)")


# =============================================================================================== A2
def tadata(w, h, mw, mh, slots, size=0):
    t, m = L.layout(w, h), L.layout(mw, mh)
    b = bytearray(size or m["size"])
    for k in range(slots):
        off = m["rgn"] + k * t["rgn_size"]
        for i in range(64):
            if off + 4 * i + 4 <= len(b):
                struct.pack_into("<I", b, off + 4 * i, 0x10000000 | (k << 8) | i)
    return bytes(b)


def tri_out(mw, mh, w, h, wrong=0, first="(304, 128)"):
    d = "diff: %d of %d pixels" % (wrong, w * h) + (", first %s 0xff203040 expected 0xff00ff00" % first if wrong else "")
    return "tri: render context for targets up to %dx%d\njob: ok\n%s\n" % (mw, mh, d)


def held(fault, out="job: failed: job faulted\n", cls="fault", s0=IDLE, s3=IDLE):
    return {"rc": 1, "cls": cls, "held": "yes", "out": out, "snaps": {0: s0, 1: fault, 2: fault, 3: s3}, "mode": "held"}


def a_safe_jobs(**over):
    j = {
        "a4-ctl-320x400-te20": {"out": tri_out(544, 400, 320, 400, 28), "tadata": tadata(320, 400, 544, 400, 1), "rc": 1},
        "a1-256x160-dump": {"out": tri_out(256, 160, 256, 160), "tadata": tadata(256, 160, 256, 160, 4)},
        "a2-320x128-dump": {"out": tri_out(320, 128, 320, 128), "tadata": tadata(320, 128, 320, 128, 4)},
        "a3-256x160-rep": {"out": tri_out(256, 160, 256, 160), "tadata": tadata(256, 160, 256, 160, 4)},
    }
    for k, v in over.items():
        k = k.replace("_", "-")
        j[k] = dict(j[k], **v) if v is not None else None
    return {k: v for k, v in j.items() if v is not None}


TA_WRITE = (0x20000000, 0x480, 0x90004, 0x20008061)
TA_WRITE_A = (0x20000000, 0x480, 0x90004, 0x2000a061)
TA_WRITE_S = (0x20000000, 0x480, 0x90004, 0x2000d061)
TA_WRITE_S11 = (0x20000000, 0x480, 0x90004, 0x20011061)


def a5_complete(w=320, h=400, mw=544, mh=400):
    return {"out": tri_out(mw, mh, w, h), "tadata": tadata(w, h, mw, mh, 4), "held": "no", "mode": "held", "snaps": {0: IDLE, 1: IDLE, 2: IDLE, 3: IDLE}}


def a_fault_jobs(a5=None, a6=None):
    return {"a5-320x400-max544": a5 or a5_complete(),
            "a6-320x400-max320": a6 or held(TA_WRITE, out="tri: render context for targets up to 320x400\njob: failed\n")}


def slack_jobs(sa4=None, sa5=None, sa6=None):
    return {"sa4-ctl-288x656-te20": sa4 or {"out": tri_out(544, 656, 288, 656, 605, "(272, 208)"), "tadata": tadata(288, 656, 544, 656, 1), "rc": 1},
            "sa5-288x656-max544": sa5 or a5_complete(288, 656, 544, 656),
            "sa6-288x656-max288": sa6 or held(TA_WRITE_S, out="tri: render context for targets up to 288x656\njob: failed\n")}


def a5_fault(word=TA_WRITE_A, mx="544x400"):
    return {"out": "tri: render context for targets up to %s\njob: failed\n" % mx, "cls": "fault", "rc": 1, "held": "yes", "mode": "held",
            "snaps": {0: IDLE, 1: word, 2: word, 3: IDLE}}


def tree(a=None, f=None, k=None, d=True):
    root = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
    for st, jobs in (("r2-d-safe", d_safe_jobs() if d else None), ("r2-d-fault", d_fault_jobs() if d else None),
                     ("r2-a-safe", a or a_safe_jobs()), ("r2-a-fault", f or a_fault_jobs()), ("r2-a-slack", k)):
        if jobs is not None:
            os.rename(stage(st, jobs), os.path.join(root, st))
    return root


S.preds()
# ---- a4 on S3's kept real run ---------------------------------------------------------------------
real = {"out": L.read_text(os.path.join(FX, "s3-a4", "a4-ctl-320x400-te20.txt.gz")), "rc": 1,
        "tadata": L.read_bytes(os.path.join(FX, "s3-a4", "a4-ctl-320x400-te20.tri.tadata.bin.gz"))}
check(len(real["tadata"]) == 0xa000, "S3's kept a4 run: TA data dump is 0xa000 bytes")
s, txt = run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a4_ctl_320x400_te20=real)))
check("a4 control: PASS" in txt, "S3's real a4 output scores PASS against E727's frozen model (28 of 128000, first (304, 128), 1 array, 0xa000)")
# ---- the passing base ------------------------------------------------------------------------------
check("H4 for what the TA writes" in run("r2-a-safe", stage("r2-a-safe", a_safe_jobs()))[0], "a-safe: base gives H4 (writes)")
check("H4 sufficiency" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs()))[0], "a-fault: base gives H4 sufficiency")
check("E1 TA write: HE" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs()))[0], "a6's E1 TA-write row: HE on the base")
_, q286 = verdict(tree())
check("closed H4" in q286, "Q286 verdict: closed H4 on the base")
# ---- a4: each failure -----------------------------------------------------------------------------
for what, over, key in (
        ("TA data 0x8000 (max-width had no effect)", {"tadata": tadata(320, 400, 320, 400, 1)}, "TA data 0x8000"),
        ("echo of another maximum", {"out": tri_out(320, 400, 320, 400, 28)}, "tool echo"),
        ("diff 0 (S3's old prediction)", {"out": tri_out(544, 400, 320, 400, 0)}, "diff 0 of 128000"),
        ("29 wrong pixels", {"out": tri_out(544, 400, 320, 400, 29)}, "diff 29"),
        ("first wrong pixel elsewhere", {"out": tri_out(544, 400, 320, 400, 28, "(300, 128)")}, "first diff (300, 128)"),
        ("two arrays at TE 0x20", {"tadata": tadata(320, 400, 544, 400, 2)}, "slots"),
        ("data below rgn", {"tadata": (lambda b: b[:64] + b"\x01\x00\x00\x00" + b[68:])(tadata(320, 400, 544, 400, 1))}, "below rgn: 1"),
        ("a fault", {"cls": "fault", "rc": 1}, "class fault"),
        ("no output", {"out": None}, "NODATA")):
    s = run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a4_ctl_320x400_te20=over)))[0]
    check(s.startswith("cannot tell: the a4 control failed") and key in s, "a4 fails on " + what)
r = tree(a=a_safe_jobs(a4_ctl_320x400_te20={"tadata": tadata(320, 400, 320, 400, 1)}))
with contextlib.redirect_stdout(io.StringIO()):
    check(S.gate("r2-a-fault", [r]) == 1, "gate r2-a-fault closed when a4 failed")
# ---- a1 / a2 / a3 ----------------------------------------------------------------------------------
five = {"tadata": tadata(256, 160, 256, 160, 5)}
s = run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a1_256x160_dump=five, a3_256x160_rep=five)))[0]
check("H5" in s and "a1-256x160-dump" in s, "a1 slot 4 written (array-like, a3 equal) gives H5")
check(verdict(tree(a=a_safe_jobs(a1_256x160_dump=five, a3_256x160_rep=five), f=a_fault_jobs(a5=a5_fault())))[1].startswith("SUMMARY: Q286: closed H5"), "Q286: closed H5 from a dump with a fifth array")
check("INCONSISTENT" in verdict(tree(a=a_safe_jobs(a1_256x160_dump=five, a3_256x160_rep=five)))[1], "Q286: a fifth array written but a5 completes in four: inconsistent")
check("a3 does not equal a1" in run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 3)})))[0], "a3 differing from a1: cannot tell")
check("a1 or a2 void" in run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a1_256x160_dump={"out": tri_out(256, 160, 256, 160, 3)})))[0], "a1 with a wrong diff is void")
s, txt = run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a2_320x128_dump={"tadata": tadata(320, 128, 320, 128, 3)})))
check("only 3 arrays written" in txt and "a1 or a2 void" in s, "a2 with three arrays: the 4x setting did not take: void")
check("cannot tell: slot 4 is" in run("r2-a-safe", stage("r2-a-safe", a_safe_jobs(a1_256x160_dump={"tadata": (lambda b: (struct.pack_into("<I", b, 0x5000 + 4 * 700, 7), bytes(b))[1])(bytearray(tadata(256, 160, 256, 160, 4)))}, a3_256x160_rep={"tadata": (lambda b: (struct.pack_into("<I", b, 0x5000 + 4 * 700, 7), bytes(b))[1])(bytearray(tadata(256, 160, 256, 160, 4)))})))[0], "a non-array-like slot 4 (ZLS data) is not a fifth array: cannot tell")
# ---- a5 / a6 ----------------------------------------------------------------------------------------
check("a5 COMPLETES" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs()))[0], "a5 completes with 4 arrays: H4")
s = run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a5=a5_fault())))[0]
check("both fault" in s and "run r2-a-slack" in s, "a5 faulting at 0x2000a with a6: cannot tell, the slack pair is next")
check("cannot tell: a5 other-fault" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a5=a5_fault((0x20000000, 0x480, 0x90004, 0x2000b061)))))[0], "a5 faulting at another page: other fault, cannot tell")
check("cannot tell: a5 complete-wrong-image" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a5=dict(a5_complete(), out=tri_out(544, 400, 320, 400, 7)))))[0], "a5 completing with a wrong image: cannot tell")
check("cannot tell: a5 void" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a5={"out": None})))[0], "a5 without output: void")
for what, a6, key in (
        ("completes (the layout model is wrong)", {"out": tri_out(320, 400, 320, 400), "cls": "ok", "rc": 0, "held": "no", "snaps": {0: IDLE, 1: IDLE, 2: IDLE, 3: IDLE}}, "COMPLETED"),
        ("another word", held((0x20000000, 0x480, 0x90008, 0x20008061), out="tri: render context for targets up to 320x400\n"), "int_stat"),
        ("a page below 0x20008", held((0x20000000, 0x480, 0x90004, 0x20007061), out="tri: render context for targets up to 320x400\n"), "before the end"),
        ("no hold message", dict(held(TA_WRITE, out="tri: render context for targets up to 320x400\n"), held="no"), "no hold message"),
        ("a stale fault at snap 0", held(TA_WRITE, out="tri: render context for targets up to 320x400\n", s0=(0x20000000, 0x480, 0x90004, 0x1)), "NODATA")):
    s = run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a6=a6)))[0]
    check(s.startswith("cannot tell: the a6 control failed"), "a6 fails: " + what)
check("accepted" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a6=held((0x20000000, 0x480, 0x90004, 0x2000a061), out="tri: render context for targets up to 320x400\n"))))[1], "a6 faulting later than the first page past the TA data is accepted and reported")
# E1 rows ride on a6: HF when a bit of its own rose
hf = held((0x20000000 | 1 << 18, 0x480, 0x90004, 0x20008061), out="tri: render context for targets up to 320x400\n")
check("E1 TA write: HF" in run("r2-a-fault", stage("r2-a-fault", a_fault_jobs(a6=hf)))[0], "a6: an extra status bit at snap 1 is HF")
# ---- the slack pair and its gate -------------------------------------------------------------------
check("sa5 COMPLETES" in run("r2-a-slack", stage("r2-a-slack", slack_jobs()))[0], "slack: sa5 completes with 4 arrays, controls PASS")
check("sa5 faults at the page past" in run("r2-a-slack", stage("r2-a-slack", slack_jobs(sa5=a5_fault(TA_WRITE_S11, "544x656"))))[0], "slack: sa5 faulting at 0x20011 is H5")
check("sa4 control failed" in run("r2-a-slack", stage("r2-a-slack", slack_jobs(sa4={"out": tri_out(544, 656, 288, 656, 604, "(272, 208)"), "tadata": tadata(288, 656, 544, 656, 1), "rc": 1})))[0], "slack: sa4 with 604 wrong pixels fails")
check("sa6 control failed" in run("r2-a-slack", stage("r2-a-slack", slack_jobs(sa6=held((0x20000000, 0x480, 0x90004, 0x2000c061), out="tri: render context for targets up to 288x656\n"))))[0], "slack: sa6 faulting before 0x2000d fails")
fa = a_fault_jobs(a5=a5_fault())


def gate_rc(root, stg="r2-a-slack"):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = S.gate(stg, [root])
    return rc, buf.getvalue()


rc, out = gate_rc(tree(f=fa))
check(rc == 0, "gate r2-a-slack OPEN: a4 PASS, a6 PASS, a5 faulted at 0x2000a")
rc, out = gate_rc(tree())
check(rc == 3 and "not needed" in out, "gate r2-a-slack not needed: a5 completed (exit 3)")
rc, out = gate_rc(tree(f=a_fault_jobs(a5=a5_fault(), a6={"out": tri_out(320, 400, 320, 400), "cls": "ok", "rc": 0, "held": "no", "snaps": {0: IDLE, 1: IDLE, 2: IDLE, 3: IDLE}})))
check(rc == 1 and "a6 control failed" in out, "gate r2-a-slack closed: the a6 control failed")
rc, out = gate_rc(tree(f=a_fault_jobs(a5={"out": None})))
check(rc == 1 and "a5 is void" in out and "rerun: run/r2.sh --only r2-a-fault" in out, "gate r2-a-slack closed: a5 void, names r2-a-fault to rerun")
rc, out = gate_rc(tree(a=a_safe_jobs(a4_ctl_320x400_te20={"tadata": tadata(320, 400, 320, 400, 1)}), f=fa))
check(rc == 1 and "a4 control failed" in out, "gate r2-a-slack closed: the a4 control failed")
rg3 =tempfile.mkdtemp(prefix="tree-", dir=ROOT)
os.rename(stage("r2-a-safe", a_safe_jobs()), os.path.join(rg3, "r2-a-safe"))
rc, out = gate_rc(rg3)
check(rc == 1 and "r2-a-fault not run" in out, "gate r2-a-slack closed: r2-a-fault not run")
# verdicts with the slack pair
_, q = verdict(tree(f=fa, k=slack_jobs()))
check("H4 holds with slack" in q and "Q140" in q, "Q286 verdict: a5 faults, the slack pair completes: H4 holds with slack (kernel layout fix, Q140)")
_, q = verdict(tree(f=fa, k=slack_jobs(sa5=a5_fault(TA_WRITE_S11, "544x656"))))
check("more than four arrays plus a page" in q and "NOT H4" in q, "Q286 verdict: the slack pair faults too: more than four arrays and a page")
_, q = verdict(tree(f=fa, k=slack_jobs(sa4={"out": None})))
check("slack pair's controls failed" in q, "Q286 verdict: a slack control failed: cannot tell")
_, q = verdict(tree(f=fa))
check("slack pair not run" in q and q.count("cannot tell") >= 1, "Q286 verdict: a5 faults and the slack pair was not run: cannot tell")
# ---- sets tallied apart in the printed rows (held out vs repeat vs controls) -------------------------
s, _ = run("r2-d-safe", stage("r2-d-safe", d_safe_jobs()))
check(s.index("held out") < s.index("repeat (fit, tallied apart)") < s.index("controls"), "every D summary lists held out, repeat and controls apart")
# ---- the freeze refusal ---------------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
for d in ("run", "score", "predictions", "tables", "bins", "gen", "templates"):
    shutil.copytree(os.path.join(R2, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("__pycache__"))
for f in ("FROZEN.sha256", "PREDICTIONS.sha256", "stages.txt", "conditional.txt", "TABLES.md"):
    shutil.copy(os.path.join(R2, f), tmp)
sd = stage("r2-a-safe", a_safe_jobs())
r = subprocess.run([sys.executable, os.path.join(tmp, "score", "score_r2.py"), "r2-a-safe", sd], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
check(r.returncode == 0 and "SUMMARY: r2-a-safe" in r.stdout, "the scorer runs on a verified freeze (CLI)")
with open(os.path.join(tmp, "predictions", "r2-a.tsv"), "a") as f:
    f.write("x\ty\tz\tm\tcontrol\n")
r = subprocess.run([sys.executable, os.path.join(tmp, "score", "score_r2.py"), "r2-a-safe", sd], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
check(r.returncode == 2 and "refused" in r.stdout, "the scorer refuses after a prediction changed (exit 2)")
print("%d ok, %d FAIL; synthetic directories: %s" % (nok, len(failed), ROOT))
sys.exit(1 if failed else 0)
