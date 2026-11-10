#!/usr/bin/env python3
"""The S3 scorers on synthetic stage directories (every control's failure, void data, each verdict) and
their readers on landed data (E728's TA data dumps, S1's kept registers, E729's kernel log, the layout).

  PY tests/test_scorers.py        (PY: the pixel-faults venv; needs a current freeze)
Nothing is deleted: the synthetic directories go to one new mktemp directory, printed at the end.
"""
import gzip
import os
import shutil
import struct
import subprocess
import sys
import tempfile

S3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(S3, "score"))
import s3lib as L  # noqa: E402
import score_s3 as S  # noqa: E402

HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, "src/resgx545-data/texture/p1141/out-hw/p1141tex-dumps")
S1OUT = os.path.join(HOME, "src/scratch/resgx545/closing/s1/out/p-d")
ROOT = tempfile.mkdtemp(prefix="s3-scorer-tests-")
HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"
IDLE = (0x20000000, 0x400, 0x80000, 0)
failed = []
nok = 0


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


def tadata(w, h, mw, mh, slots, size=0):
    t, m = L.layout(w, h), L.layout(mw, mh)
    b = bytearray(size or m["size"])
    for k in range(slots):
        off = m["rgn"] + k * t["rgn_size"]
        for i in range(64):
            if off + 4 * i + 4 <= len(b):
                struct.pack_into("<I", b, off + 4 * i, 0x10000000 | (k << 8) | i)
    return bytes(b)


def stage(name, jobs):
    """jobs: {case: dict(rc, cls, held, out, dmesg, snaps{k: tuple}, tadata)}; returns the directory."""
    d = tempfile.mkdtemp(prefix=name + "-", dir=ROOT)
    rows = [HEAD]
    for case, j in jobs.items():
        rows.append("\t".join([case, name, "x", "x", "x", "x", "x", str(j.get("rc", 0)), j.get("cls", "ok"),
                               "held", "-", "0", j.get("held", "no")]))
        if j.get("out") is not None:
            gz(os.path.join(d, case + ".txt.gz"), j["out"])
        gz(os.path.join(d, case + ".dmesg.gz"), j.get("dmesg", ""))
        for k, t in j.get("snaps", {}).items():
            gz(os.path.join(d, "%s.snap%d.regs.gz" % (case, k)), regs(t))
        if j.get("tadata") is not None:
            gz(os.path.join(d, case + ".tri.tadata.bin.gz"), j["tadata"])
    if jobs is not None:
        open(os.path.join(d, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return d


def tri_out(mw, mh, w, h, wrong=0):
    return ("tri: render context for targets up to %dx%d\njob: ok\ndiff: %d of %d pixels\n" % (mw, mh, wrong, w * h))


def held(fault, out="job: failed: job faulted\n", cls="fault", s0=IDLE, s3=IDLE):
    return {"rc": 1, "cls": cls, "held": "yes", "out": out, "snaps": {0: s0, 1: fault, 2: fault, 3: s3}}


def timeline(rows, start=300000000):
    return "timeline: regs 0x0118 0x012c 0x0c00 0x0c04 0x0c08 samples 9 seconds 0 start %d end 900000000 rc 1\n" % start + \
        "".join("tl %d %08x %08x 00000000 %08x %08x\n" % (t, st2, st, i, f) for t, st, st2, i, f in rows)


def a_safe_jobs(**over):
    j = {
        "a4-ctl-320x400-te20": {"out": tri_out(544, 400, 320, 400), "tadata": tadata(320, 400, 544, 400, 1)},
        "a1-256x160-dump": {"out": tri_out(256, 160, 256, 160), "tadata": tadata(256, 160, 256, 160, 4)},
        "a2-320x128-dump": {"out": tri_out(320, 128, 320, 128), "tadata": tadata(320, 128, 320, 128, 4)},
        "a3-256x160-rep": {"out": tri_out(256, 160, 256, 160), "tadata": tadata(256, 160, 256, 160, 4)},
    }
    for k, v in over.items():
        j[k.replace("_", "-")] = dict(j[k.replace("_", "-")], **v) if v is not None else None
    return {k: v for k, v in j.items() if v is not None}


TA_READ = (0x20000000, 0x480, 0x90008, 0x3e000001)
BG_FETCH = (0x20000000, 0x440, 0xd0400, 0x0001f061)
TEX = (0x20000000, 0x440, 0x90002, 0x3e017001)
XFER = (0x20000000, 0x440, 0x80020, 0x32200001)
TA_WRITE = (0x20000000, 0x480, 0x90004, 0x20008061)
XOUT = "dwords written through the read-only alias: 0\nBIF_INT_STAT 0x80020 BIF_FAULT 0x32200001 bif_faults 0\n"


def e1c_jobs(ta=None, bg=None):
    return {"e1-ta-read": ta or held(TA_READ), "e1-bg-fetch": bg or held(BG_FETCH)}


def e1_jobs(tex=None):
    return {"e1-tex": tex or held(TEX, out="probe x: scratch at 0x3e003000 (64 KiB)\njob: failed\n")}


def xfer_jobs(xfer=None):
    x = held(XFER, out=XOUT)
    x.update(rc=0, held="no")
    return {"e1-xfer-ro": xfer or x}


def a_fault_jobs(a5=None, a6=None):
    return {"a5-320x400-max544": a5 or {"out": tri_out(544, 400, 320, 400), "tadata": tadata(320, 400, 544, 400, 4),
                                        "held": "no", "snaps": {0: IDLE, 1: IDLE, 2: IDLE, 3: IDLE}},
            "a6-320x400-max320": a6 or held(TA_WRITE, out="tri: render context for targets up to 320x400\njob: failed\n")}


def summ(stage_name, d):
    return S.STAGES[stage_name](d)[1]["summary"]


def tree(a=None, c=None, e=None, f=None, x=None):
    root = tempfile.mkdtemp(prefix="tree-", dir=ROOT)
    for st, jobs in (("s3-a-safe", a or a_safe_jobs()), ("s3-e1-ctl", c or e1c_jobs()), ("s3-e1", e or e1_jobs()),
                     ("s3-a-fault", f or a_fault_jobs()), ("s3-xfer", x or xfer_jobs())):
        os.rename(stage(st, jobs), os.path.join(root, st))
    return root


def verdict(root):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        q286, q003 = S.verdict(root)
    return q286, q003


S.preds()
# ---- the passing base ----------------------------------------------------------------------------
check("H4 for what the TA writes" in summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs())), "a-safe: base gives H4 (writes)")
check("method ok" in summ("s3-e1-ctl", stage("s3-e1-ctl", e1c_jobs())), "e1-ctl: base passes")
check(summ("s3-e1", stage("s3-e1", e1_jobs())) == "e1-tex HE", "e1: base gives HE for the texture fault")
check(summ("s3-xfer", stage("s3-xfer", xfer_jobs())) == "e1-xfer-ro HE", "xfer (own last stage): base gives HE")
check("H4 sufficiency" in summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs())), "a-fault: base gives H4 sufficiency")
q286, q003 = verdict(tree())
check(q286.startswith("closed H4") and q003.startswith("HE for every"), "verdict: H4 and HE on the base")
# ---- a4, the control of A: each failure ----------------------------------------------------------
for what, over, key in (
        ("TA data 0x8000 (max-width had no effect)", {"tadata": tadata(320, 400, 320, 400, 1)}, "had no effect"),
        ("echo of another maximum", {"out": tri_out(320, 400, 320, 400)}, "tool echo"),
        ("a wrong image", {"out": tri_out(544, 400, 320, 400, wrong=5)}, "diff 5"),
        ("two arrays at TE 0x20", {"tadata": tadata(320, 400, 544, 400, 2)}, "slots"),
        ("a fault", {"cls": "fault", "rc": 1}, "class fault"),
        ("no output", {"out": None}, "NODATA")):
    s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a4_ctl_320x400_te20=over)))
    check(s.startswith("cannot tell: the a4 control failed") and key in s, "a4 fails on " + what)
r = tree(a=a_safe_jobs(a4_ctl_320x400_te20={"tadata": tadata(320, 400, 320, 400, 1)}))
check(not S.gate("s3-a-fault", r), "gate s3-a-fault closed when a4 failed")
# ---- a1 / a2 / a3 --------------------------------------------------------------------------------
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump={"tadata": tadata(256, 160, 256, 160, 5)},
                                                     a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 5)})))
check("H5" in s and "a1-256x160-dump" in s, "a1 slot 4 written (array-like, a3 equal) gives H5")
check(verdict(tree(a=a_safe_jobs(a1_256x160_dump={"tadata": tadata(256, 160, 256, 160, 5)},
                                 a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 5)}),
                   f=a_fault_jobs(a5={"out": "tri: render context for targets up to 544x400\n", "cls": "fault", "rc": 1,
                                      "held": "yes", "snaps": {0: IDLE, 1: (0x20000000, 0x480, 0x90004, 0x2000a061),
                                                               2: IDLE, 3: IDLE}})))[0].startswith("closed H5"),
      "verdict: closed H5 from a dump with a fifth array")
check("INCONSISTENT" in verdict(tree(a=a_safe_jobs(a1_256x160_dump={"tadata": tadata(256, 160, 256, 160, 5)},
                                                   a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 5)})))[0],
      "verdict: a fifth array written but a5 completes in four: inconsistent")
# ---- review fix 8: slot 4 lies in the ZLS area at these sizes: it must look like an array, a3 must
# equal a1 for any closure, and a gap (a slot written after an empty one) is not a count


def with_words(blob, off, idx):
    b = bytearray(blob)
    for i in idx:
        struct.pack_into("<I", b, off + 4 * i, 0xabcd0000 | i)
    return bytes(b)


L16 = L.layout(256, 160)
not_array = with_words(tadata(256, 160, 256, 160, 4), L16["rgn"] + 4 * L16["rgn_size"], range(100, 200))
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump={"tadata": not_array},
                                                     a3_256x160_rep={"tadata": not_array})))
check(s.startswith("cannot tell") and "H5" not in s.split("cannot tell")[0], "slot 4 written but not array-like: cannot tell")
gap = with_words(tadata(256, 160, 256, 160, 4), L16["rgn"] + 5 * L16["rgn_size"], range(0, 64))
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump={"tadata": gap}, a3_256x160_rep={"tadata": gap})))
check(s.startswith("cannot tell"), "slot 4 zero but slot 5 written (a gap): cannot tell")
q = verdict(tree(a=a_safe_jobs(a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 3)})))[0]
check(q.startswith("cannot tell"), "verdict: no H4 closure when a3 differs from a1")
q = verdict(tree(a=a_safe_jobs(a1_256x160_dump={"tadata": tadata(256, 160, 256, 160, 5)}),
                 f=a_fault_jobs(a5={"out": "tri: render context for targets up to 544x400\n", "cls": "fault", "rc": 1,
                                    "held": "yes", "snaps": {0: IDLE, 1: (0x20000000, 0x480, 0x90004, 0x2000a061),
                                                             2: IDLE, 3: IDLE}})))[0]
check(q.startswith("cannot tell"), "verdict: no H5 closure when a3 differs from a1")
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump={"tadata": None})))
check(s.startswith("cannot tell: a1 or a2 void"), "a1 dump missing: void, cannot tell")
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a2_320x128_dump={"tadata": tadata(320, 128, 320, 128, 1)})))
check(s.startswith("cannot tell"), "a2 with one array (4x not active): void, cannot tell")
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a3_256x160_rep={"tadata": tadata(256, 160, 256, 160, 3)})))
check("a3 differs" in s, "a3 replicate differing is reported")
d = stage("s3-a-safe", a_safe_jobs())
os.rename(os.path.join(d, "cases.tsv"), os.path.join(d, "cases.tsv.hidden"))
check(summ("s3-a-safe", d).startswith("cannot tell"), "no cases.tsv: cannot tell")
s = summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump={"rc": ""})))
check(s.startswith("cannot tell"), "an empty rc: void, cannot tell")
# ---- E1 controls ---------------------------------------------------------------------------------
for what, ta, bg in (
        ("status2 0x400 for the TA read", held((0x20000000, 0x400, 0x90008, 0x3e000001)), None),
        ("no hold message", None, dict(held(BG_FETCH), held="no")),
        ("snap 1 missing", dict(held(TA_READ), snaps={0: IDLE}), None),
        ("an extra status bit 18", held((0x20040000, 0x480, 0x90008, 0x3e000001)), None),
        ("the fault not cleared by the reset", held(TA_READ, s3=TA_READ), None),
        ("no fault (completed)", dict(held(IDLE), cls="ok", rc=0), None)):
    d = stage("s3-e1-ctl", e1c_jobs(ta, bg))
    check(summ("s3-e1-ctl", d).startswith("METHOD BROKEN"), "E1 control fails on " + what)
check(not S.gate("s3-e1", tree(c=e1c_jobs(held((0x20000000, 0x400, 0x90008, 0x3e000001))))),
      "gate s3-e1 closed when a control failed")
check(verdict(tree(c=e1c_jobs(held((0x20000000, 0x400, 0x90008, 0x3e000001)))))[1].startswith("cannot tell"),
      "verdict Q003: cannot tell when a control failed")
# ---- E1 held out ---------------------------------------------------------------------------------
TEXOUT = "probe x: scratch at 0x3e003000 (64 KiB)\njob: failed\n"
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=held((0x20000000, 0xc40, 0x90002, 0x3e017001), out=TEXOUT))))
check(s.startswith("e1-tex HF"), "tex: status2 bit 11 at snap 1 gives HF")
check(verdict(tree(e=e1_jobs(tex=held((0x20000000, 0xc40, 0x90002, 0x3e017001), out=TEXOUT))))[1].startswith("HF"),
      "verdict Q003: HF")
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=held((0x20040000, 0x440, 0x90002, 0x3e017001), out=TEXOUT,
                                                  s0=(0x20040000, 0x400, 0x80000, 0)))))
check(s.startswith("e1-tex HE"), "tex: a bit already set before the job (snap 0) is not the fault's")
stale = (0, 0x20040000, 0xc80, 0x90008, 0x3e000001)
idle_row = (1000, 0x20000000, 0x400, 0x80000, 0)
tl_he = timeline([stale, idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                  (400000000, 0x20000000, 0x440, 0x90002, 0x3e017001)])
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=held(TEX, out=TEXOUT + tl_he))))
check(s.startswith("e1-tex HE"), "tex: the first sample (the previous job's, before the start) is ignored")
tl_hf = timeline([stale, idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                  (400000000, 0x20000000, 0x440, 0x90002, 0x3e017001), (400001000, 0x20000000, 0x640, 0x90002, 0x3e017001)])
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=held(TEX, out=TEXOUT + tl_hf))))
check(s.startswith("e1-tex HF"), "tex: a bit that rises at the fault and falls before snap 1 gives HF (timeline)")
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=held(TEX, out="job: failed\n"))))
check(s.startswith("cannot tell for e1-tex"), "tex: no 64 KiB scratch line: void (knob)")
s = summ("s3-e1", stage("s3-e1", e1_jobs(tex=dict(held(TEX, out=TEXOUT), held="no"))))
check(s.startswith("cannot tell for e1-tex"), "tex: a fault that was not held: void (knob)")
x = held((0x20000000, 0x400, 0x80020, 0x32200001), out=XOUT); x.update(rc=0, held="no")
check(summ("s3-xfer", stage("s3-xfer", xfer_jobs(x))) == "e1-xfer-ro HE-edm", "xfer: status2 0x400 is HE-edm")
x = held(IDLE, out=XOUT, cls="ok"); x.update(rc=0, held="no")
check(summ("s3-xfer", stage("s3-xfer", xfer_jobs(x))).startswith("cannot tell for e1-xfer-ro"), "xfer: no fault: cannot tell")
x = held(XFER, out="cat: xfer_ro: No such device\n"); x.update(rc=1, held="no")
check(summ("s3-xfer", stage("s3-xfer", xfer_jobs(x))).startswith("cannot tell for e1-xfer-ro"), "xfer: the check did not run: void")
check(verdict(tree(x={"e1-xfer-ro": dict(held(XFER, out=XOUT), held="no", rc=0)}))[1].startswith("HE for every"),
      "verdict Q003 reads the xfer row from its own stage")
# ---- review fix 1: the timeline window ends before the reset; bits 14 / 31 masked; timeline-only bits
# reported, not part of a control's pass rule
CUT = int((2.8 + 1) * 1e9)
TAOUT = "job: failed\n"
post = [(CUT + 100000000, 0xa0004000, 0x4c0, 0x90008, 0x3e000001), (CUT + 200000000, 0x20000000, 0x400, 0x80000, 0)]
tl_ta = timeline([idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                  (400000000, 0x20000000, 0x480, 0x90008, 0x3e000001)] + post)
check(summ("s3-e1-ctl", stage("s3-e1-ctl", e1c_jobs(held(TA_READ, out=TAOUT + tl_ta)))).startswith("method ok"),
      "control: rows after the hold window (the reset's halt: bits 14, 31, status2 0x4c0) are not counted")
tl_tex_post = timeline([idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                        (400000000, 0x20000000, 0x440, 0x90002, 0x3e017001),
                        (CUT + 1000, 0x20000000, 0xc40, 0x90002, 0x3e017001)])
check(summ("s3-e1", stage("s3-e1", e1_jobs(held(TEX, out=TEXOUT + tl_tex_post)))) == "e1-tex HE",
      "tex: a bit rising after the hold window (at the reset) is not HF")
tl_tex_14 = timeline([idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                      (400000000, 0x80004000 | 0x20000000, 0x440, 0x90002, 0x3e017001)])
check(summ("s3-e1", stage("s3-e1", e1_jobs(held(TEX, out=TEXOUT + tl_tex_14)))) == "e1-tex HE",
      "tex: SW_EVENT (bit 14) and MASTER (bit 31) at the fault are masked")
tl_ta_only = timeline([idle_row, (300500000, 0x20000000, 0x400, 0x80000, 0),
                       (400000000, 0x20000000, 0xc80, 0x90008, 0x3e000001), (500000000, 0x20000000, 0x480, 0x90008, 0x3e000001)])
s = summ("s3-e1-ctl", stage("s3-e1-ctl", e1c_jobs(held(TA_READ, out=TAOUT + tl_ta_only))))
check(s.startswith("method ok"), "control: a timeline-only bit (gone by snap 1) does not fail the control")
d = stage("s3-e1-ctl", e1c_jobs(held(TA_READ, out=TAOUT + tl_ta_only)))
import contextlib as _c, io as _io  # noqa: E402
_b = _io.StringIO()
with _c.redirect_stdout(_b):
    S.run_stage("s3-e1-ctl", d)
check("timeline-only" in _b.getvalue(), "control: the timeline-only bit is reported")
# ---- review fix 3: a fault latched before the job voids it
LATCHED = (0x20000000, 0x480, 0x90008, 0x3e000001)
s = summ("s3-e1", stage("s3-e1", e1_jobs(held(TEX, out=TEXOUT, s0=LATCHED))))
check(s.startswith("cannot tell for e1-tex"), "tex: a fault latched at snap 0 voids the job")
a1l = dict(a_safe_jobs()["a1-256x160-dump"], snaps={0: LATCHED})
check(summ("s3-a-safe", stage("s3-a-safe", a_safe_jobs(a1_256x160_dump=a1l))).startswith("cannot tell"),
      "a1: a fault latched before the job voids it")
check(summ("s3-e1-ctl", stage("s3-e1-ctl", e1c_jobs(held(TA_READ, s0=LATCHED)))).startswith("METHOD BROKEN"),
      "control: a fault latched before the job fails the control")
# ---- a5 / a6 -------------------------------------------------------------------------------------
A6OUT = "tri: render context for targets up to 320x400\njob: failed\n"
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a6={"out": A6OUT, "cls": "ok", "snaps": {0: IDLE, 1: IDLE, 3: IDLE}})))
check(s.startswith("cannot tell: the a6 control failed") and "COMPLETED" in s, "a6 completes: the layout model is wrong")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a6=held((0x20000000, 0x480, 0x90004, 0x20007061), out=A6OUT))))
check(s.startswith("cannot tell: the a6 control failed"), "a6 faults before the end of the TA data: control fails")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a6=held((0x20000000, 0x480, 0x90004, 0x20009061), out=A6OUT))))
check("H4 sufficiency" in s, "a6 faulting past the first page is accepted (reported)")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a6=held((0x20000000, 0x480, 0x90008, 0x20008061), out=A6OUT))))
check(s.startswith("cannot tell: the a6 control failed"), "a6 with another fault word: control fails")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a6=held(TA_WRITE, out="job: failed\n"))))
check(s.startswith("cannot tell: the a6 control failed") and "knob" in s, "a6 without the 320x400 echo: knob fails")
a5f = {"out": "tri: render context for targets up to 544x400\njob: failed\n", "cls": "fault", "rc": 1, "held": "yes",
       "snaps": {0: IDLE, 1: (0x20000000, 0x480, 0x90004, 0x2000a061), 2: IDLE, 3: IDLE}}
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a5=a5f)))
check(s.startswith("cannot tell: a5 and a6 both fault"), "a5 faults at 0x2000a: H5 or slack, cannot tell")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a5={"out": tri_out(544, 400, 320, 400, wrong=5),
                                                                 "tadata": tadata(320, 400, 544, 400, 4)})))
check(s.startswith("cannot tell: a5 complete-wrong-image"), "a5 completes with a wrong image: cannot tell")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a5={"out": tri_out(544, 400, 320, 400),
                                                                 "tadata": tadata(320, 400, 320, 400, 4)})))
check(s.startswith("cannot tell: a5 void"), "a5 with TA data 0x8000: knob fails, void")
s = summ("s3-a-fault", stage("s3-a-fault", a_fault_jobs(a5={"out": tri_out(544, 400, 320, 400),
                                                                 "tadata": tadata(320, 400, 544, 400, 1)})))
check(s.startswith("cannot tell: a5 void"), "a5 with one array (4x not active): void")
# ---- the frozen predictions agree with the transcribed layout -------------------------------------
check(int(L.pred(S.PA, "a4-ctl-320x400-te20", "tadata_size"), 16) == L.layout(544, 400)["size"], "a4 size = layout(544x400)")
check(int(L.pred(S.PA, "a1-256x160-dump", "tadata_size"), 16) == L.layout(256, 160)["size"], "a1 size = layout(256x160)")
check(L.fault_page_if(4, (320, 400), (544, 400)) is None, "a5: four arrays fit in the 544x400 TA data")
check(int(L.pred(S.PA, "a5-320x400-max544", "fault_page", "H5"), 16) == L.fault_page_if(5, (320, 400), (544, 400)),
      "a5 H5 page = layout")
check(int(L.pred(S.PA, "a6-320x400-max320", "fault_page"), 16) == L.fault_page_if(4, (320, 400), (320, 400)), "a6 page = layout")
for wh, page in (((288, 144), 0x20006), ((256, 288), 0x20006), ((384, 384), 0x20008)):
    check(L.fault_page_if(4, wh, wh) == page and L.fault_page_if(5, wh, wh) == page, "E729 %dx%d faults at %#x for f = 4 and 5" % (wh + (page,)))
for wh in ((256, 160), (320, 128)):
    check(L.fault_page_if(5, wh, wh) is None and L.fault_page_if(6, wh, wh), "E729 %dx%d completes for f <= 5, not 6" % wh)
# ---- readers on landed data ----------------------------------------------------------------------
b = L.read_bytes(os.path.join(DATA, "msaa-b-te29/t29-m2-e0-64x64-ctl.tri.tadata.bin.gz"))
if b:
    s, below = L.tadata_slots(b, 0x4000, 0x300)
    check(s[:4] == [96, 64, 64, 64] and not any(s[4:]) and below == 0, "E728 TE 0xe0 64x64: 96, 64, 64, 64 then zero (%s)" % s[:6])
    check(hasattr(L, "array_like") and all(L.array_like(b, 0x4000, 0x300, k) for k in (1, 2, 3))
          and not L.array_like(b, 0x4000, 0x300, 4), "E728: slots 1-3 pass the array-like rule, the empty slot 4 does not")
for nm in ("t29-m2-c0-128x128", "t29-m2-80-128x128"):
    b = L.read_bytes(os.path.join(DATA, "msaa-b-te29/%s.tri.tadata.bin.gz" % nm))
    if b:
        s, _ = L.tadata_slots(b, 0x4000, 0x300)
        check(hasattr(L, "array_like") and all(L.array_like(b, 0x4000, 0x300, k) for k in range(1, 4) if s[k]),
              "E728 %s: every written slot after slot 0 passes the array-like rule" % nm)
b = L.read_bytes(os.path.join(DATA, "msaa-b-te29/t29-m2-20-64x64-ctl.tri.tadata.bin.gz"))
if b:
    s, below = L.tadata_slots(b, 0x4000, 0x300)
    check(s[0] == 72 and not any(s[1:]), "E728 TE 0x20 64x64: one array of 72 (%s)" % s[:4])
t = L.read_text(os.path.join(S1OUT, "d-L2e2-16.after.regs.txt.gz"))
r = L.parse_regs(t)
check(r is not None and r[L.REG_INT_STAT] == 0x80000, "S1 d-L2e2-16 regs after the recovery: idle 0x80000")
dm = L.read_text(os.path.join(S1OUT, "d-L2e2-16.dmesg.gz")) or ""
check("BIF fault 0x90002 at 0x3e017001" in dm and "EVENT_STATUS 0x20000000/0x440" in dm,
      "S1's texture fault: 0x90002 at 0x3e017001, status2 0x440 at the kernel's reset (the e1-tex prediction)")
j = L.read_text(os.path.join(DATA, "msaa-c-q140/journal-k.txt.gz")) or ""
check("0x20006062 (PD" in j and "0x20008062 (PD" in j, "E729 journal: the first faults at pages 0x20006 and 0x20008")
check(L.parse_regs("") is None and L.parse_timeline("no timeline") is None and L.read_bytes("/nonexistent") is None,
      "readers return None on empty or missing data")
# ---- the scorer refuses when a frozen file changed -------------------------------------------------
cp = tempfile.mkdtemp(prefix="frozen-copy-", dir=ROOT)
for sub in ("run", "score", "tables", "predictions", "bins"):
    shutil.copytree(os.path.join(S3, sub), os.path.join(cp, sub), ignore=shutil.ignore_patterns("__pycache__"))
for f in ("stages.txt", "FROZEN.sha256", "PREDICTIONS.sha256"):
    shutil.copy(os.path.join(S3, f), cp)
r0 = subprocess.run([sys.executable, os.path.join(cp, "score/score_s3.py"), "s3-a-safe", stage("s3-a-safe", a_safe_jobs())],
                    capture_output=True, text=True)
with open(os.path.join(cp, "predictions/s3-a.tsv"), "a") as f:
    f.write("a4-ctl-320x400-te20\tdiff\t1 of 128000\tboth\tcontrol\n")
r1 = subprocess.run([sys.executable, os.path.join(cp, "score/score_s3.py"), "s3-a-safe", stage("s3-a-safe", a_safe_jobs())],
                    capture_output=True, text=True)
check(r0.returncode == 0 and "SUMMARY: s3-a-safe:" in r0.stdout and r1.returncode == 2 and "SUMMARY: refused" in r1.stdout,
      "the scorer runs on the frozen copy and refuses once a prediction changed")
print("%d ok, %d failed; synthetic directories in %s" % (nok, len(failed), ROOT))
sys.exit(1 if failed else 0)
