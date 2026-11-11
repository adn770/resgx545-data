#!/usr/bin/env python3
"""R3K-pixel scorers (kernel-batch session K2), written and frozen before the run.  Each prints its rows and ends with one SUMMARY.

  score_k.py STAGE OUTDIR          one stage (k-f4, k-pb0, k-pb, k-bif)
  score_k.py verdict ROOT...       Q140 (k-f4), Q285 (k-pb0 + k-pb) and Q003 (k-bif) from the kept stages
  score_k.py gate STAGE ROOT...    exit 0 if the stages STAGE depends on passed their controls (k-pb: k-pb0's three controls),
                                   1 closed (the message names the stage to rerun)
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

Refuses to score unless run/freeze_k.sh verify passes.  Missing or empty data, an rc or class that is not a result, a failed
knob proof (the TA data size of the layout the knob asked for) and a failed control are NODATA or "cannot tell", never a
verdict.  Held-out rows, replicates and controls are tallied apart.  The tool's messages are searched in the WHOLE output (R1-events
lost "scene overflowed" in a 4000-character tail).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
import klib as L  # noqa: E402
import kgen as G  # noqa: E402

PF4 = PPB = PBIF = None
IDLE = 0x80000


def preds():
    global PF4, PPB, PBIF
    PF4 = L.load_predictions("k-f4.tsv")
    PPB = L.load_predictions("k-pb.tsv")
    PBIF = L.load_predictions("k-bif.tsv")


def pv(P, case, q, model=None):
    return L.pred(P, case, q, model)


def job(outdir, cases, name, need_out=True):
    """Everything kept for one job; j['void'] lists what is missing."""
    j = {"name": name, "void": []}
    row = (cases or {}).get(name)
    if row is None:
        j["void"].append("no cases.tsv row (not run)")
        return j
    j["row"] = row
    if row.get("rc", "") == "" or not re.fullmatch(r"-?\d+", row["rc"]):
        j["void"].append("no rc")
    else:
        j["rc"] = int(row["rc"])
        if j["rc"] in (2, 124, 125, 126, 127) or j["rc"] >= 128:
            j["void"].append("rc %d is not a result of the tool" % j["rc"])
    if row.get("class") not in ("ok", "fault", "hang", "fail"):
        j["void"].append("class %r" % row.get("class"))
    j["out"] = L.read_text(os.path.join(outdir, name + ".txt.gz"))
    if j["out"] is None and need_out:
        j["void"].append("tool output missing or empty")
    j["dmesg"] = L.read_text(os.path.join(outdir, name + ".dmesg.gz")) or ""
    for k in list(range(5)) + ["b%d" % i for i in range(6)]:
        j["snap%s" % k] = L.parse_regs(L.read_text(os.path.join(outdir, "%s.snap%s.regs.gz" % (name, k))))
    if j.get("snap0") is not None and j["snap0"][L.REG_INT_STAT] & L.FAULT_REQ:
        j["void"].append("a fault latched before the job (snap 0 CR_BIF_INT_STAT %#x)" % j["snap0"][L.REG_INT_STAT])
    j["tadata"] = L.read_bytes(os.path.join(outdir, name + ".tri.tadata.bin.gz"))
    j["param"] = L.read_bytes(os.path.join(outdir, name + ".tri.param.bin.gz"))
    j["kw"] = L.kw_steps(L.read_text(os.path.join(outdir, name + ".kw.txt.gz")))
    return j


def stage_dir(roots, stage):
    for r in roots:
        if os.path.exists(os.path.join(r, stage, "cases.tsv")):
            return os.path.join(r, stage)
    return os.path.join(roots[0], stage) if roots else stage


def held_fault(j):
    """A held fault as the snapshots show it: {"word": CR_BIF_INT_STAT, "page": CR_BIF_FAULT >> 12, "bif_fault"} or None."""
    s = j.get("snapb0") or j.get("snap1")
    if s is None or not s[L.REG_INT_STAT] & L.FAULT_REQ:
        return None
    f = s.get(L.REG_FAULT, 0)
    return {"word": s[L.REG_INT_STAT], "page": f >> 12, "bif_fault": f}


def echo_of(j):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", j.get("out") or "", re.M)
    return m.group(1) if m else None


def read_complete(j, w, h, mx, my, f):
    """What a completed tri job shows: diff text, TA data size, the number of region-header arrays written (from rgn, spacing the
    target's rgn_size), anything written after them, and non-zero dwords below rgn."""
    d = L.diff_line(j.get("out"))
    r = {"diff": None if d is None else "%d of %d" % d[:2], "echo": echo_of(j), "size": None if j.get("tadata") is None else len(j["tadata"]),
         "slots": None, "later": None, "below": None, "sha": None}
    if j.get("tadata") is not None:
        t, m = L.layout(w, h), L.layout(mx, my, f)
        s, below = L.tadata_slots(j["tadata"], m["rgn"], t["rgn_size"])
        n = 0
        while n < len(s) and s[n] > 0:
            n += 1
        r.update(slots=n, later=any(x > 0 for x in s[n:]), below=below, sha=L.sha256(j["tadata"]))
    return r


# =============================================================================================== k-f4 (Q140)
F4_ROWS = None


def f4_rows():
    global F4_ROWS
    if F4_ROWS is None:
        F4_ROWS = {r[0]: r for r in G.f4_rows()}
    return F4_ROWS


def f4_result(j, name):
    """(verdict, text, extra): PASS/FAIL for controls, AGREES/REFUTED/cannot tell for held-out rows, NODATA."""
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"]), {}
    _, sset, _, _, _, w, h, f = f4_rows()[name]
    cls = j["row"]["class"]
    held = name.startswith("c1")
    ctl = sset == "control"
    if held:
        hf = held_fault(j)
        if cls == "ok":
            return "FAIL", "completed (E729: 288x144 at knob 1 faults 0x90004 at page 0x20006): the knob leaks", {}
        if cls == "fault" and hf and hex(hf["word"]) == pv(PF4, name, "fault_word") and hex(hf["page"]) == pv(PF4, name, "fault_page"):
            return "PASS", "held fault %#x at page %#x (E729)" % (hf["word"], hf["page"]), {}
        return "FAIL", "class %s, fault %s (frozen 0x90004 at 0x20006)" % (cls, hf), {}
    if cls == "fault":
        bf = L.bif_fault(j["dmesg"], j["out"])
        txt = "faulted %s" % ("(no fault line)" if bf is None else "%s at %#x (page %#x)" % (bf[0], bf[1], bf[1] >> 12))
        return ("FAIL" if ctl else "REFUTED"), txt, {"fault": bf}
    if cls == "hang":
        return ("FAIL" if ctl else "REFUTED"), "hung", {}
    if L.overflowed(j["out"], j["dmesg"]):
        return "cannot tell (parameter-buffer overflow: not the layout)", "the scene overflowed the parameter buffer", {}
    r = read_complete(j, w, h, w, h, f)
    if r["size"] is None:
        return "NODATA", "NODATA (no TA data dump)", r
    want = int(pv(PF4, name, "tadata_size"), 16)
    if r["size"] != want:
        if not ctl and r["size"] == int(pv(PF4, name, "tadata_size_if_knob_1"), 16):
            return ("cannot tell (the knob did not apply: TA data %#x is the knob-1 layout, wanted %#x)" % (r["size"], want),
                    "knob: TA data %#x, wanted %#x" % (r["size"], want), r)
        return ("FAIL" if ctl else "cannot tell (TA data %#x, wanted %#x: not the layout asked for)" % (r["size"], want)), \
            "TA data %#x, wanted %#x" % (r["size"], want), r
    bad = []
    if r["diff"] != pv(PF4, name, "diff"):
        bad.append("diff %s, frozen %s" % (r["diff"], pv(PF4, name, "diff")))
    if r["echo"] != pv(PF4, name, "max_echo"):
        bad.append("echo %s" % r["echo"])
    if r["slots"] != int(pv(PF4, name, "slots_written")) or r["later"]:
        bad.append("%s arrays written (later data: %s)" % (r["slots"], r["later"]))
    if r["below"]:
        bad.append("%d non-zero dwords below rgn" % r["below"])
    if bad:
        return ("FAIL" if ctl else "REFUTED"), "; ".join(bad), r
    return ("PASS" if ctl else "AGREES"), "complete, %s wrong, TA data %#x, %d arrays" % (r["diff"].split(" of ")[0], r["size"], r["slots"]), r


def f4_stage(outdir):
    cases = L.read_cases(outdir)
    res, extra, lines = {}, {}, []
    for name in f4_rows():
        r = f4_result(job(outdir, cases, name), name)
        res[name], extra[name] = r[0], r[2]
        lines.append("%s: %s: %s" % (name, r[0], r[1]))
    # c2 against c3: the same layout, so the same TA data and the same image
    c2, c3 = extra.get("c2-64x64-k4"), extra.get("c3-64x64-k1")
    if res.get("c2-64x64-k4") == "PASS" and c3 and c3.get("sha") and c2.get("sha") != c3.get("sha"):
        res["c2-64x64-k4"] = "FAIL"
        lines.append("c2-64x64-k4: FAIL: TA data sha256 differs from c3's (the knob changed a 64x64 layout)")
    # the controls that every held-out reading rests on
    # any control that is not PASS (FAIL, NODATA, or a row that did not run) gates them (post-run fix C2, POSTRUN-FIX.md)
    ctl_bad = [n for n in ("c1-288x144-k1", "c2-64x64-k4", "c3-64x64-k1") if res.get(n) != "PASS"]
    for n in list(res):
        if n.startswith("h") and res[n] in ("AGREES", "REFUTED") and ctl_bad:
            res[n] = "cannot tell (control %s %s)" % (ctl_bad[0], res.get(ctl_bad[0], "not run"))
    ho = [n for n in res if n.startswith("h")]
    agree = [n for n in ho if res[n] == "AGREES"]
    ref = [n for n in ho if res[n] == "REFUTED"]
    ct = [n for n in ho if res[n].startswith("cannot tell")]
    nd = [n for n in ho if res[n] == "NODATA"]
    ctrl = {n: res[n] for n in res if n.startswith("c")}
    if ctl_bad:
        head = "cannot tell for the held-out rows: control %s %s%s; " % (ctl_bad[0], res.get(ctl_bad[0], "not run"),
                                                                         " (the knob leaks: it completed)" if ctl_bad[0].startswith("c1") else "")
    elif any(res[x].startswith("cannot tell (the knob") for x in ct):
        head = "cannot tell for %s: the knob did not apply (the TA data is the knob-1 layout); " % ", ".join(ct)
    else:
        head = ""
    s = "k-f4: %s%d of %d held-out rows complete with 0 wrong pixels and four arrays in the four-array layout%s%s; controls %s" % (
        head, len(agree), len(ho), "; REFUTED %s" % ref if ref else "", "; cannot tell %s" % ct if ct and not head else "", ctrl)
    if nd:
        s += "; NODATA %s" % nd
    return lines, {"verdicts": res, "summary": s}


# =============================================================================================== k-pb0 and k-pb (Q285)
def words_of(j, a, b):
    if j.get("param") is None or len(j["param"]) < 4 * b:
        return None
    return ",".join("%08x" % int(x) for x in L.dwords(j["param"])[a:b])


def tri2_text(j):
    t = L.tri_lines(j.get("out"), 2) or L.tri_lines(j.get("out"))
    return None if t is None else "%d triangle, %d background" % (t["tri"], t["bg"])


def pb_ctl(j, name, own_ref=None):
    """A control of the split flow against its frozen quantities: PASS / FAIL / NODATA and the text."""
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"])
    if j["row"]["class"] != "ok":
        return "FAIL", "class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    if j.get("param") is None:
        return "NODATA", "NODATA (no parameter-buffer dump)"
    bad = []
    d = L.diff_line(j["out"])
    got = {"diff": None if d is None else "%d of %d" % d[:2], "target_hash": L.target_hash(j["out"]), "tri2": tri2_text(j),
           "stream_0_2": words_of(j, 0, 3), "par_11_26": words_of(j, 11, 27)}
    for q, v in got.items():
        if v != pv(PPB, name, q):
            bad.append("%s %s, frozen %s" % (q, v, pv(PPB, name, q)))
    if own_ref is not None and L.sha256(j["param"]) != own_ref:
        bad.append("parameter buffer differs from the dump run's")
    if name == "pb-p2-own11":
        want = G.pb_words()[0]
        w27 = words_of(j, 0, 27)
        if w27 is not None and w27 != ",".join("%08x" % want[i] for i in range(27)):
            bad.append("dwords 0-26 are not E728's own words (the poke of its own value changed the dump)")
        ap = L.kpoke_applied(j["dmesg"])
        if ap != [("par", 11, 0)]:
            bad.append("kernel log applied %s, wanted [par:11=0]" % ap)
    return ("FAIL" if bad else "PASS"), ("; ".join(bad) if bad else "as frozen (%s)" % got["diff"])


def pb0_stage(outdir):
    cases = L.read_cases(outdir)
    res, lines, shas = {}, [], {}
    for r in G.pb0_rows():
        n = r[0]
        j = job(outdir, cases, n)
        shas[n] = None if j.get("param") is None else L.sha256(j["param"])
        ref = shas.get("pb-d0-te40") if n == "pb-p1-te40" else None
        v, t = pb_ctl(j, n, ref)
        res[n] = v
        lines.append("%s: %s: %s" % (n, v, t))
    s = "k-pb0: controls %s" % res
    return lines, {"verdicts": res, "summary": s}


def gate(stage, roots):
    """(code, message): k-pb needs the three controls of k-pb0."""
    if stage != "k-pb":
        return 0, "gate %s: no prerequisite" % stage
    d = stage_dir(roots, "k-pb0")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate k-pb: closed: no k-pb0 stage was kept (rerun: run/k.sh --only k-pb0)"
    lines, res = pb0_stage(d)
    bad = {n: v for n, v in res["verdicts"].items() if v != "PASS"}
    if bad:
        return 1, "gate k-pb: closed: k-pb0 controls %s (rerun: run/k.sh --only k-pb0)" % bad
    return 0, "gate k-pb: open (k-pb0's dump run, p0 and p1 passed)"


def pb_pokes(name):
    cmd = [r for r in G.pb_rows() if r[0] == name][0][4]
    return [(int(m.group(1)), int(m.group(2), 16)) for m in re.finditer(r"--kpoke-render 2:par:(\d+)=(0x[0-9a-f]+)", cmd)]


def pb_stage(outdir, roots=None):
    cases = L.read_cases(outdir)
    res, lines, note = {}, [], {}
    own, twin = G.pb_words()
    d0sha = None
    if roots:
        d0 = stage_dir(roots, "k-pb0")
        jd = job(d0, L.read_cases(d0), "pb-d0-te40")
        d0sha = None if jd.get("param") is None else L.sha256(jd["param"])
    for r in G.pb_rows():
        n = r[0]
        j = job(outdir, cases, n)
        if n == "pb-p2-own11":
            v, t = pb_ctl(j, n, d0sha)
            res[n] = v
            lines.append("%s: %s: %s" % (n, v, t))
            continue
        if j["void"]:
            res[n] = "NODATA"; lines.append("%s: NODATA (%s)" % (n, "; ".join(j["void"]))); continue
        if j["row"]["class"] != "ok":
            res[n] = "OTHER"; lines.append("%s: OTHER: class %s (a garbage word may hang the ISP; rc %s)" % (n, j["row"]["class"], j["row"].get("rc"))); continue
        pokes = pb_pokes(n)
        ap = [(i, v) for sp, i, v in L.kpoke_applied(j["dmesg"]) if sp == "par"]
        if sorted(ap) != sorted(pokes):
            res[n] = "NODATA"
            lines.append("%s: NODATA (the kernel log applied %d of the %d pokes: the poke did not land, no reading)" % (n, len(ap), len(pokes)))
            continue
        d = L.diff_line(j["out"]); t = L.tri_lines(j["out"], 2) or L.tri_lines(j["out"])
        if d is None or t is None:
            res[n] = "NODATA"; lines.append("%s: NODATA (no diff or render line)" % n); continue
        dtxt = "%d of %d" % d[:2]
        twin_like = dtxt == "0 of 4096" and L.target_hash(j["out"]) == G.FULL_HASH and t["tri"] == 4096
        w27 = words_of(j, 11, 27)
        landed = ""
        if n.startswith("pb-p3"):
            res[n] = "twin" if twin_like else "not twin"
            landed = "; dump dwords 11-26 %s the twin's" % ("=" if w27 == ",".join("%08x" % twin[i] for i in range(11, 27)) else "differ from")
        else:
            res[n] = "drawn" if t["tri"] > 0 else "empty"
            landed = "; dump dword 11 %s" % (words_of(j, 11, 12))
        lines.append("%s: %s: diff %s, %d triangle pixels, target hash %s%s" % (n, res[n], dtxt, t["tri"], L.target_hash(j["out"]), landed))

    def cons(names):
        vals = {res.get(x) for x in names if res.get(x) in ("twin", "not twin", "drawn", "empty")}
        return vals.pop() if len(vals) == 1 else ("split" if vals else None)

    p3, p4 = cons(("pb-p3a-twin", "pb-p3b-twin")), cons(("pb-p4a-ffff", "pb-p4b-ffff"))
    # the jobs behind each reading, not "2 of 2" whatever was read (post-run fix C10, POSTRUN-FIX.md)
    n3 = sum(1 for x in ("pb-p3a-twin", "pb-p3b-twin") if res.get(x) == p3)
    n4 = sum(1 for x in ("pb-p4a-ffff", "pb-p4b-ffff") if res.get(x) == p4)
    if res.get("pb-p2-own11") != "PASS":
        q = "cannot tell: the p2 control (a poke of the word's own value) %s" % res.get("pb-p2-own11")
    elif p3 in (None, "split") or p4 in (None, "split"):
        q = "cannot tell: no consistent reading (p3 %s, p4 %s)" % (p3, p4)
    elif p3 == "twin" and p4 == "empty":
        q = ("H-OLD: the 3D reads the stretch in the old layout (p3 the twin's dwords 11-26 give the twin's image in %d of 2 jobs; "
             "p4 a garbage dword 11 draws nothing in %d of 2 jobs)" % (n3, n4))
    elif p3 == "not twin" and p4 == "drawn":
        q = ("H-FIELD: dword 11 is a field the 3D uses (p4 draws pixels in %d of 2 jobs; p3's old-layout words do not give the twin's image "
             "in %d of 2 jobs)" % (n4, n3))
    elif p3 == "not twin" and p4 == "empty":
        q = "cannot tell: p3 and p4 both empty (not the twin's, nothing drawn): the cause is elsewhere; park under Q030"
    else:
        q = "cannot tell: both effects (p3 gives the twin's image and p4 draws): the data do not separate H-OLD from H-FIELD"
    return lines, {"verdicts": res, "q285": q, "summary": "k-pb: p3 %s, p4 %s; Q285: %s" % (p3, p4, q)}


# =============================================================================================== k-bif (Q003)
def bif_state(t):
    return (t[L.REG_INT_STAT], t.get(L.REG_FAULT, 0))


def bif_n0(j):
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"])
    sn = [j.get("snapb%d" % k) for k in range(6)]
    if any(x is None for x in sn) or not j["kw"]:
        return "NODATA", "NODATA (snapshots or the kw file missing)"
    bad = []
    for k in range(1, 5):
        if k not in j["kw"] or j["kw"][k][1] != 0:
            bad.append("write %d status %s" % (k, j["kw"].get(k)))
    lines = L.kregnow_lines(j["dmesg"])
    if len(lines) != 4:
        return "NODATA", "NODATA (%d kregnow log lines, wanted 4)" % len(lines)
    for k, s in enumerate(sn):
        if bif_state(s) != (IDLE, 0):
            bad.append("snap b%d INT_STAT %#x FAULT %#x" % (k, *bif_state(s)))
    for ln in lines:
        if (ln["int_stat"], ln["fault"]) != (IDLE, 0):
            bad.append("log line %#x: INT_STAT %#x FAULT %#x" % (ln["off"], ln["int_stat"], ln["fault"]))
    if sn[4].get(L.REG_BIF_CTRL) != sn[0].get(L.REG_BIF_CTRL):
        bad.append("BIF_CTRL not restored")
    return ("FAIL" if bad else "PASS"), ("; ".join(bad) if bad else "idle: nothing changed after any of the four writes (INT_STAT 0x80000, FAULT 0)")


def bif_row(j, name):
    """(verdict, text, data) of one held-fault row."""
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"]), {}
    if j["row"]["class"] == "ok":
        return "NOFAULT", "the job completed (no fault latched: nothing to clear)", {}
    if j["row"]["class"] != "fault":
        return "NODATA", "class %s" % j["row"]["class"], {}
    sn = [j.get("snapb%d" % k) for k in range(6)]
    if any(x is None for x in sn) or not j["kw"]:
        return "NODATA", "NODATA (snapshots b0-b5 or the kw file missing)", {}
    if any(k not in j["kw"] or j["kw"][k][1] != 0 for k in range(1, 5)):
        return "NODATA", "NODATA (a kregnow write was refused: %s)" % {k: j["kw"].get(k) for k in range(1, 5)}, {}
    lines = L.kregnow_lines(j["dmesg"])
    if len(lines) != 4:
        return "NODATA", "NODATA (%d kregnow log lines, wanted 4)" % len(lines), {}
    s0 = sn[0]
    fw, fp = int(pv(PBIF, name, "fault_word"), 16), int(pv(PBIF, name, "fault_page"), 16)
    if s0[L.REG_INT_STAT] != fw or (s0.get(L.REG_FAULT, 0) >> 12) != fp:
        return "cannot tell (the fault is %#x at page %#x, frozen %#x at %#x)" % (s0[L.REG_INT_STAT], s0.get(L.REG_FAULT, 0) >> 12, fw, fp), \
            "fault word/page not the frozen ones", {}
    st0 = bif_state(s0)
    after = [(ln["int_stat"], ln["fault"]) for ln in lines]
    cleared = lambda s: s == (IDLE, 0)
    unch = lambda s: s == st0
    data = {"after": after, "snap5": bif_state(sn[5]), "rc": j.get("rc")}
    if not unch(after[0]):
        return "cannot tell (the write of the unset bit 0x1 changed the state: %#x/%#x)" % after[0], "control 1 failed", data
    if sn[4].get(L.REG_BIF_CTRL) != s0.get(L.REG_BIF_CTRL):
        return "cannot tell (BIF_CTRL is %#x after the second flip, %#x before)" % (sn[4].get(L.REG_BIF_CTRL, -1), s0.get(L.REG_BIF_CTRL, -1)), \
            "BIF_CTRL not restored", data
    a2, a3, a4 = after[1], after[2], after[3]
    if cleared(a2) and cleared(a3) and cleared(a4):
        v = "H-W1C"
    elif unch(a2) and cleared(a3) and cleared(a4):
        v = "H-CLR"
    elif unch(a2) and unch(a3) and unch(a4):
        v = "H-RST"
    else:
        v = "OTHER"
    return v, "INT_STAT/FAULT after the writes: %s -> %s" % (
        "%#x/%#x" % st0, ", ".join("%#x/%#x" % a for a in after)), data


def bif_stage(outdir):
    cases = L.read_cases(outdir)
    res, lines, data = {}, [], {}
    for r in G.BIF_ROWS:
        n = r[0]
        if n == "n0-idle":
            j = job(outdir, cases, n, need_out=False)
            v, t = bif_n0(j)
            d = {}
        else:
            j = job(outdir, cases, n)
            v, t, d = bif_row(j, n)
            for rl in L.reset_lines(j["dmesg"]):
                lines.append("%s: reset line %s: BIF_INT_STAT %#x BIF_FAULT %#x" % (n, rl["kind"], rl["int_stat"], rl["fault"]))
        res[n], data[n] = v, d
        lines.append("%s: %s: %s" % (n, v, t))
        if d.get("snap5"):
            lines.append("%s: after the 2.5 s watch INT_STAT/FAULT %#x/%#x, tool rc %s (job completes: no; the fault returns: %s)" % (
                n, *d["snap5"], d["rc"], "no" if d["snap5"] == (IDLE, 0) else "it is still latched"))
    reads = {n: v for n, v in res.items() if n != "n0-idle" and v.startswith("H-")}
    hs = sorted(set(reads.values()))
    if res.get("n0-idle") != "PASS":
        q = "cannot tell: the n0 control (the four writes with nothing held) %s" % res.get("n0-idle")
    elif not reads and any(v == "OTHER" for n, v in res.items() if n != "n0-idle"):
        # rows that were read and match none of the three are not "could not be read" (post-run fix C10, POSTRUN-FIX.md)
        other = {n: v for n, v in res.items() if n != "n0-idle" and v == "OTHER"}
        unread = {n: v for n, v in res.items() if n != "n0-idle" and v != "OTHER"}
        q = "none of H-W1C, H-CLR, H-RST: %d of 4 held rows were read and match none of them (%s)%s; n0 PASS" % (
            len(other), other, ("; not read: %s" % unread) if unread else "")
    elif not reads:
        q = "cannot tell: no held row could be read (%s)" % {n: v for n, v in res.items() if n != "n0-idle"}
    elif len(hs) > 1:
        q = "MIXED: the rows disagree: %s" % reads
    else:
        miss = {n: v for n, v in res.items() if n not in reads and n != "n0-idle"}
        q = "%s: %d of 4 held rows agree%s; n0 PASS" % (hs[0], len(reads), ("; not read: %s" % miss) if miss else "")
    return lines, {"verdicts": res, "q003": q, "summary": "k-bif: Q003: %s" % q}


# =============================================================================================== verdict, CLI
def verdict(roots):
    out = []
    for q, st in (("Q140", "k-f4"), ("Q285", "k-pb"), ("Q003", "k-bif")):
        d = stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept %s)" % (q, st))
            continue
        if st == "k-f4":
            _, r = f4_stage(d)
            out.append("SUMMARY: Q140: %s" % r["summary"])
        elif st == "k-pb":
            _, r = pb_stage(d, roots)
            out.append("SUMMARY: Q285: %s" % r["q285"])
        else:
            _, r = bif_stage(d)
            out.append("SUMMARY: Q003: %s" % r["q003"])
    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ok, msg = L.verify_freeze()
    if not ok:
        print("FROZEN FILES CHANGED: refusing to score\n%s" % msg)
        return 3
    preds()
    if argv[1] == "verdict":
        print(verdict(argv[2:]))
        return 0
    if argv[1] == "gate":
        code, m = gate(argv[2], argv[3:])
        print(m)
        return code
    st, outdir = argv[1], argv[2]
    fn = {"k-f4": f4_stage, "k-pb0": pb0_stage, "k-bif": bif_stage}.get(st)
    if st == "k-pb":
        lines, r = pb_stage(outdir, [os.path.dirname(os.path.abspath(outdir))])
    elif fn:
        lines, r = fn(outdir)
    else:
        print("unknown stage %s" % st)
        return 2
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
