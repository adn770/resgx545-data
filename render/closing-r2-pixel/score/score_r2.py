#!/usr/bin/env python3
"""R2-pixel scorers, written and frozen before the run.  Each prints its rows and ends with one SUMMARY line.

  score_r2.py STAGE OUTDIR          one stage (r2-d-safe, r2-d-fault, r2-a-safe, r2-a-fault, r2-a-slack)
  score_r2.py verdict ROOT...       Q281 (D2) and Q286 (A2, with the slack pair if it ran) from all stages
  score_r2.py gate STAGE ROOT...    exit 0 if the stages STAGE depends on passed their controls; 1 closed (a prerequisite
                                    failed); 3 not needed (r2-a-slack only: a5 already decided)
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

Refuses to score unless run/freeze_r2.sh verify passes.  Missing or empty data, an rc or class that is not a result, a
failed knob proof and a failed control are NODATA or "cannot tell", never a verdict.  Held-out rows, fit/repeat rows and
controls are tallied apart in every SUMMARY.  The tool's messages are searched in the WHOLE output (R1-events: a tail of
4000 characters lost "scene overflowed").
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r2lib as L  # noqa: E402

PD = PA = IM = None


def preds():
    global PD, PA, IM
    PD = L.load_predictions("r2-d.tsv")
    PA = L.load_predictions("r2-a.tsv")
    IM = L.load_images()


def job(outdir, cases, name):
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
    if j["out"] is None:
        j["void"].append("tool output missing or empty")
    j["dmesg"] = L.read_text(os.path.join(outdir, name + ".dmesg.gz")) or ""
    for k in range(5):
        j["snap%d" % k] = L.parse_regs(L.read_text(os.path.join(outdir, "%s.snap%d.regs.gz" % (name, k))))
    if j["snap0"] is not None and j["snap0"][L.REG_INT_STAT] & L.FAULT_REQ:
        j["void"].append("a fault latched before the job (snap 0 CR_BIF_INT_STAT %#x)" % j["snap0"][L.REG_INT_STAT])
    j["tadata"] = L.read_bytes(os.path.join(outdir, name + ".tri.tadata.bin.gz"))
    j["tl"] = L.parse_timeline(j["out"]) if j["out"] else None
    return j


def pv(P, case, q, model=None):
    return L.pred(P, case, q, model)


# =============================================================================================== D2 (Q281)
def d_result(j, case):
    """One probe job reduced to a result dict: status void | ran, outcome, image."""
    if j["void"]:
        return {"status": "void", "why": "; ".join(j["void"])}
    sl = L.scratch_line(j["out"])
    want = pv(PD, case, "scratch_line")
    if sl is None or sl[0] != L.BASE_SCRATCH or "(%d KiB)" % sl[1] != want:
        return {"status": "void", "why": "knob: scratch line %s, wanted base %#x %s" % (
            None if sl is None else "%#x (%d KiB)" % sl, L.BASE_SCRATCH, want)}
    cls, rc = j["row"]["class"], j["rc"]
    if cls == "fault":
        f = L.bif_fault(j["dmesg"], j["out"])
        return {"status": "ran", "outcome": "fault", "fault": f}
    if cls == "hang":
        return {"status": "ran", "outcome": "hang"}
    if cls == "fail":
        return {"status": "ran", "outcome": "fail", "rc": rc}
    if rc == 3 and "failed: no pixel written" in j["out"]:
        return {"status": "ran", "outcome": "rc3 no pixel written"}
    if rc != 0:
        return {"status": "ran", "outcome": "rc%d" % rc}
    px = L.probe_rows(j["out"])
    if len(px) != 2048:
        return {"status": "void", "why": "completed with %d pixels, not 2048" % len(px)}
    return {"status": "ran", "outcome": "complete", "px": px}


def distinct(px):
    d = {}
    for v in px:
        d[v] = d.get(v, 0) + 1
    return ", ".join("%#010x x%d" % kv for kv in sorted(d.items(), key=lambda kv: -kv[1])[:4])


def judge_d(name, r):
    """(verdict, text): verdict in PASS / FAIL / NODATA for controls and repeats, HL / HS / OTHER / NODATA for held-out."""
    if r["status"] == "void":
        return "NODATA", "NODATA (%s)" % r["why"]
    oc = r["outcome"]
    if name == "d-ok-64":
        ok = oc == "complete" and L.pix_hash(r["px"]) == pv(PD, name, "pix_sha256_if_complete")
        return ("PASS" if ok else "FAIL"), "%s: %s" % (oc, "A4 exact" if ok else "not the A4 image")
    if name in ("d-L2e2-19", "d-L2e2-19x"):
        ok = oc == "complete" and r["px"] == IM[name][1]
        what = "byte-identical to S1b's image" if name == "d-L2e2-19" else "S1b's image XOR 1"
        return ("PASS" if ok else "FAIL"), "%s: %s" % (oc, what if ok else "NOT %s (%s)" % (what, distinct(r["px"]) if oc == "complete" else oc))
    if name == "d-L2e2-18x":
        if oc == "complete" and all(v == 0xDEADBEEE for v in r["px"]):
            return "HL", "complete, 0xdeadbeee 2048 of 2048 (HL)"
        if oc == "rc3 no pixel written":
            return "HS", "rc 3 no pixel written (HS)"
        if oc == "complete":
            return "HS", "complete, another image: %s (HS)" % distinct(r["px"])
        return "OTHER", "%s%s" % (oc, " %s" % (r.get("fault"),) if r.get("fault") else "")
    if name == "d-L2e2-18":
        return ("PASS" if oc == "rc3 no pixel written" else "FAIL"), "%s (S1b measured rc 3 no pixel written)" % oc
    if name in ("d-L2e2-17", "d-L2e2-16"):
        w, a = pv(PD, name, "fault_word"), int(pv(PD, name, "fault_addr"), 16)
        f = r.get("fault")
        hit = oc == "fault" and f is not None and f[0] == w and f[1] == a
        if name == "d-L2e2-16":
            return ("PASS" if hit else "FAIL"), "%s %s" % (oc, "" if f is None else "%s at %#x" % f) + ("" if hit else " (E722's fault expected)")
        if hit:
            return "HL", "fault %s at %#x (HL)" % f
        if oc == "complete":
            return "HS", "completes (HS)"
        return "OTHER", "%s %s" % (oc, "" if f is None else "%s at %#x" % f)
    return "NODATA", "unknown row"


def d_rows(outdir, names):
    cases = L.read_cases(outdir)
    res, verd, lines = {}, {}, []
    for n in names:
        r = d_result(job(outdir, cases, n), n)
        v, t = judge_d(n, r)
        res[n], verd[n] = r, v
        lines.append("%s: %s" % (n, t))
    return lines, res, verd


D_SAFE = ["d-ok-64", "d-L2e2-19", "d-L2e2-19x", "d-L2e2-18x", "d-L2e2-18"]
D_FAULT = ["d-L2e2-17", "d-L2e2-16"]
D_SET = {"d-ok-64": "control", "d-L2e2-19": "control", "d-L2e2-19x": "control", "d-L2e2-18x": "heldout",
         "d-L2e2-18": "repeat", "d-L2e2-17": "heldout", "d-L2e2-16": "control"}


def d_tally(verd):
    """held out / repeat / controls apart; a held-out row counts only if its controls allow it (see d_cannot_tell)."""
    ct = d_cannot_tell(verd)
    ho = {n: ("cannot tell (%s)" % ct[n]) if n in ct else v for n, v in verd.items() if D_SET[n] == "heldout"}
    rep = {n: v for n, v in verd.items() if D_SET[n] == "repeat"}
    con = {n: v for n, v in verd.items() if D_SET[n] == "control"}
    return ho, rep, con


def d_cannot_tell(verd):
    """Rows that cannot be read because a control failed: {row: why}."""
    bad = {}
    v = verd.get
    if v("d-ok-64") not in (None, "PASS"):
        for n in verd:
            bad[n] = "d-ok-64 control %s" % v("d-ok-64")
    if v("d-L2e2-19") not in (None, "PASS"):
        for n in ("d-L2e2-19x", "d-L2e2-18x", "d-L2e2-18", "d-L2e2-17"):
            if n in verd:
                bad[n] = "d-L2e2-19 is not byte-identical to S1b's image (%s)" % v("d-L2e2-19")
    if v("d-L2e2-19x") not in (None, "PASS") and "d-L2e2-18x" in verd:
        bad["d-L2e2-18x"] = "the variant control d-L2e2-19x %s" % v("d-L2e2-19x")
    if v("d-L2e2-16") not in (None, "PASS") and "d-L2e2-17" in verd:
        bad["d-L2e2-17"] = "the 16-page control did not fault as E722 (%s)" % v("d-L2e2-16")
    return bad


def d_summary(stage, verd):
    ho, rep, con = d_tally(verd)
    parts = ["held out %s" % (ho or "none"), "repeat (fit, tallied apart) %s" % (rep or "none"), "controls %s" % (con or "none")]
    cannot = [n for n, v in {**ho}.items() if str(v).startswith("cannot tell") or v in ("NODATA", "OTHER")]
    badc = [n for n, v in con.items() if v != "PASS"]
    head = "cannot tell for %s: " % ", ".join(sorted(set(cannot + badc))) if (cannot or badc) else ""
    return "%s%s" % (head, "; ".join(parts))


def d_stage(names):
    def f(outdir):
        lines, res, verd = d_rows(outdir, names)
        return lines, {"verdicts": verd, "res": res, "summary": d_summary("", verd)}
    return f


def q281(roots):
    safe = d_rows(stage_dir(roots, "r2-d-safe"), D_SAFE)
    fault = d_rows(stage_dir(roots, "r2-d-fault"), D_FAULT)
    verd = {**safe[2], **fault[2]}
    ran = {n: v for n, v in verd.items() if v != "NODATA"}
    ho, rep, con = d_tally(verd)
    ct = d_cannot_tell(verd)
    held = [(n, v) for n, v in ho.items()]
    hl = [n for n, v in held if v == "HL"]
    hs = [n for n, v in held if v == "HS"]
    other = [n for n, v in held if v in ("OTHER",)]
    void = [n for n, v in held if v == "NODATA" or str(v).startswith("cannot tell")]
    if "d-ok-64" in ct or verd.get("d-ok-64") != "PASS":
        s = "cannot tell: the d-ok-64 control %s" % verd.get("d-ok-64", "was not run")
    elif verd.get("d-L2e2-19") != "PASS":
        s = "cannot tell: d-L2e2-19 is not byte-identical to S1b's image (%s)" % verd.get("d-L2e2-19", "not run")
    elif hs or other:
        s = "HL REFUTED or incomplete: held-out rows against HL: %s; HL-consistent %s; (HS rows: %s)" % (
            {n: v for n, v in held if n in hs + other}, hl, hs)
    elif hl and not void:
        s = "HL: all %d held-out rows agree (%s); repeat d-L2e2-18 %s; controls %s" % (len(hl), ", ".join(hl), rep, con)
    elif hl:
        s = "HL partly: held-out %s agree, cannot tell for %s (%s)" % (hl, void, {n: ct.get(n) for n in void})
    else:
        s = "cannot tell: no held-out row could be read (%s)" % held
    print("SUMMARY: Q281: %s" % s)
    return s


# =============================================================================================== A2 (Q286)
def diff_of(j):
    m = re.search(r"^diff: (\d+) of (\d+) pixels(?:, first \((\d+), (\d+)\))?", j.get("out") or "", re.M)
    if not m:
        return None, None
    first = None if m.group(3) is None else "(%s, %s)" % (m.group(3), m.group(4))
    return "%s of %s" % (m.group(1), m.group(2)), first


def max_echo(j):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", j.get("out") or "", re.M)
    return m.group(1) if m else None


def slots_of(j, target):
    if j.get("tadata") is None:
        return None, None
    lay = L.layout(*target)
    return L.tadata_slots(j["tadata"], lay["rgn"], lay["rgn_size"])


def written(slots):
    n = 0
    while n < len(slots) and slots[n] > 0:
        n += 1
    return n, any(x > 0 for x in slots[n:])


def held_reading(j):
    s0, s1, s3 = j.get("snap0"), j.get("snap1"), j.get("snap3")
    if s1 is None or s0 is None:
        return None
    r = {"status": s1[L.REG_STATUS], "status2": s1[L.REG_STATUS2], "int_stat": s1[L.REG_INT_STAT],
         "bif_fault": s1.get(L.REG_FAULT), "bif_ctrl": s1.get(L.REG_BIF_CTRL)}
    extra1 = s1[L.REG_STATUS] & ~L.KNOWN_STATUS & ~L.MASK_STATUS & ~s0[L.REG_STATUS]
    extra2 = s1[L.REG_STATUS2] & ~L.KNOWN_STATUS2 & ~s0[L.REG_STATUS2]
    r["stable"] = j.get("snap2") is not None and all(
        j["snap2"].get(k) == s1.get(k) for k in (L.REG_STATUS, L.REG_STATUS2, L.REG_INT_STAT, L.REG_FAULT))
    r["cleared"] = None if s3 is None else not (s3[L.REG_INT_STAT] & L.FAULT_REQ)
    r["tl"] = None
    if j.get("tl"):
        w = L.fault_window(j["tl"])
        if w:
            r["tl"] = w
            extra1 |= w["rose_status"] & ~L.KNOWN_STATUS & ~L.MASK_STATUS
            extra2 |= w["rose_status2"] & ~L.KNOWN_STATUS2
    r["extra"] = (extra1, extra2)
    return r


def fmt_reading(r):
    t = ""
    if r["tl"]:
        t = "; at the fault (t %.3f ms): rose status %#x status2 %#x" % (r["tl"]["t"] / 1e6, r["tl"]["rose_status"], r["tl"]["rose_status2"])
    return ("status %#x status2 %#x int_stat %#x bif_fault %s; stable %s; cleared by the reset %s%s"
            % (r["status"], r["status2"], r["int_stat"], L.hx(r["bif_fault"]), r["stable"], r["cleared"], t))


def e1_row(j, case):
    """A held fault against HE / HF (Q003's TA-write row rides on a6 and sa6): HE, HF, NODATA or NOFAULT."""
    if j["void"]:
        return "NODATA"
    r = held_reading(j)
    if r is None or j["row"]["class"] != "fault":
        return "NOFAULT" if r is not None else "NODATA"
    e1, e2 = r["extra"]
    if e1 or e2:
        return "HF"
    if r["status2"] != int(pv(PA, case, "status2", "HE"), 16) or r["status"] != int(pv(PA, case, "status", "HE"), 16):
        return "HE-other"
    return "HE"


def check_ctl(j, case, target, mx):
    """A TE 0x20 control (a4, sa4): returns (ok, [why]).  Every frozen quantity must hold."""
    if j["void"]:
        return False, ["NODATA: " + "; ".join(j["void"])]
    why = []
    row = j["row"]
    if row["class"] != "ok" or row["rc"] not in ("0", "1"):
        why.append("class %s rc %s" % (row["class"], row["rc"]))
    d, first = diff_of(j)
    if d != pv(PA, case, "diff"):
        why.append("diff %s, E727 model %s" % (d, pv(PA, case, "diff")))
    if first != pv(PA, case, "diff_first"):
        why.append("first diff %s, model %s" % (first, pv(PA, case, "diff_first")))
    if max_echo(j) != pv(PA, case, "max_echo"):
        why.append("knob: tool echo %s" % max_echo(j))
    size = None if j["tadata"] is None else len(j["tadata"])
    if size != int(pv(PA, case, "tadata_size"), 16):
        why.append("knob: TA data %s bytes, wanted %s" % (L.hx(size), pv(PA, case, "tadata_size")))
    else:
        s, below = slots_of(j, target)
        n, later = written(s)
        if n != int(pv(PA, case, "slots_written")) or later or below:
            why.append("slots %s (below rgn: %d non-zero)" % (s, below))
        lay = L.layout(*target)
        if hex(lay["rgn"]) != pv(PA, case, "rgn") or hex(lay["rgn_size"]) != pv(PA, case, "rgn_size"):
            why.append("layout %#x/%#x is not the frozen one" % (lay["rgn"], lay["rgn_size"]))
    return not why, why


A_TARGETS = {"a1-256x160-dump": (256, 160), "a2-320x128-dump": (320, 128)}


def a_safe(outdir):
    cases = L.read_cases(outdir)
    lines, res = [], {}
    a4 = job(outdir, cases, "a4-ctl-320x400-te20")
    ok4, why4 = check_ctl(a4, a4["name"], (320, 400), "544x400")
    res["a4"] = ok4
    lines.append("a4 control: %s%s" % ("PASS" if ok4 else "FAIL", (": " + "; ".join(why4)) if why4 else ""))
    slot4 = {}
    for name, tgt in A_TARGETS.items():
        j = job(outdir, cases, name)
        why = list(j["void"])
        if not why:
            if j["row"]["class"] != "ok" or j["row"]["rc"] != "0":
                why.append("class %s rc %s" % (j["row"]["class"], j["row"]["rc"]))
            if diff_of(j)[0] != pv(PA, name, "diff"):
                why.append("diff %s" % diff_of(j)[0])
            if j["tadata"] is None or len(j["tadata"]) != int(pv(PA, name, "tadata_size"), 16):
                why.append("TA data %s bytes" % (None if j["tadata"] is None else hex(len(j["tadata"]))))
        if why:
            lines.append("%s: NODATA (%s)" % (name, "; ".join(why)))
            slot4[name] = None
            continue
        s, below = slots_of(j, tgt)
        n, later = written(s)
        if n < int(pv(PA, name, "min_slots_written")):
            lines.append("%s: NODATA (knob: only %d arrays written, the 4x setting did not take: %s)" % (name, n, s))
            slot4[name] = None
            continue
        lay = L.layout(*tgt)
        if later:
            slot4[name] = "gap"
        elif s[4] == 0:
            slot4[name] = "zero"
        elif L.array_like(j["tadata"], lay["rgn"], lay["rgn_size"], 4):
            slot4[name] = "written"
        else:
            slot4[name] = "not-array"
        lines.append("%s: non-zero dwords per 0x%x slot from 0x%x: %s; below rgn %d; slot 4 %s (H4 %s, H5 %s)%s" % (
            name, lay["rgn_size"], lay["rgn"], s, below, slot4[name], pv(PA, name, "slot4", "H4"), pv(PA, name, "slot4", "H5"),
            "; a gap: a slot after the first empty one is written" if later else ""))
    a1, a3 = job(outdir, cases, "a1-256x160-dump"), job(outdir, cases, "a3-256x160-rep")
    if a1.get("tadata") and a3.get("tadata") and not a3["void"]:
        same = L.sha256(a1["tadata"]) == L.sha256(a3["tadata"])
        res["a3"] = same
        lines.append("a3 replicate: TA data sha256 %s a1's (%s)" % ("equals" if same else "DIFFERS from", L.sha256(a3["tadata"])[:16]))
    else:
        res["a3"] = None
        lines.append("a3 replicate: NODATA (a dump missing)")
    res["slot4"] = slot4
    vals = set(slot4.values())
    if not ok4:
        s = "cannot tell: the a4 control failed (%s); do not run r2-a-fault" % "; ".join(why4)
    elif None in vals:
        s = "cannot tell: a1 or a2 void; a4 control PASS"
    elif vals & {"gap", "not-array"}:
        s = "cannot tell: slot 4 is %s (it lies in the ZLS area at these sizes; a fifth array must look like slots 0-3)" % slot4
    elif res["a3"] is not True:
        s = "cannot tell: the replicate a3 does not equal a1 (no closure without a repeatable dump); slot 4 %s" % slot4
    elif vals == {"zero"}:
        s = "a4 control PASS (TA data 0xa000, 28 wrong pixels as E727); slot 4 zero at 256x160 and 320x128: H4 for what the TA writes (f = 4)"
    elif "written" in vals:
        s = "a4 control PASS; slot 4 WRITTEN (%s): H5 (f = 5 arrays written)" % ", ".join(k for k, v in slot4.items() if v == "written")
    else:
        s = "cannot tell"
    res["summary"] = s
    return lines, res


def a_pair(outdir, a5n, a6n, target, mx):
    """Both held jobs of a pair: returns lines, res (a5 outcome, a6 pass, E1 row)."""
    cases = L.read_cases(outdir)
    lines, res = [], {}
    w, h = target
    a6 = job(outdir, cases, a6n)
    why6 = []
    if a6["void"]:
        why6.append("NODATA: " + "; ".join(a6["void"]))
    else:
        r = held_reading(a6)
        if max_echo(a6) != pv(PA, a6n, "max_echo"):
            why6.append("knob: tool echo %s" % max_echo(a6))
        if a6["row"]["class"] == "ok":
            why6.append("COMPLETED: the layout model is wrong, a5 says nothing")
        elif a6["row"]["class"] != "fault" or r is None:
            why6.append("class %s" % a6["row"]["class"])
        else:
            page = None if r["bif_fault"] is None else r["bif_fault"] >> 12
            if r["int_stat"] != int(pv(PA, a6n, "int_stat"), 16):
                why6.append("int_stat %#x" % r["int_stat"])
            want = int(pv(PA, a6n, "fault_page"), 16)
            if page is None or page < want:
                why6.append("fault page %s, before the end of the TA data %#x" % (L.hx(page), want))
            elif page != want:
                lines.append("%s: the fault is past the TA data at page %#x, not its first page %#x (accepted)" % (a6n, page, want))
            if a6["row"].get("held_msg") != "yes":
                why6.append("no hold message")
    res["a6"] = not why6
    lines.append("%s control: %s%s" % (a6n, "PASS" if not why6 else "FAIL", (": " + "; ".join(why6)) if why6 else ""))
    res["e1_a6"] = e1_row(a6, a6n)
    lines.append("E1 TA write row (%s): %s" % (a6n, res["e1_a6"]))
    a5 = job(outdir, cases, a5n)
    why5 = list(a5["void"])
    out5 = None
    if not why5:
        if max_echo(a5) != pv(PA, a5n, "max_echo"):
            why5.append("knob: tool echo %s" % max_echo(a5))
        elif a5["row"]["class"] == "ok":
            size = None if a5["tadata"] is None else len(a5["tadata"])
            d = diff_of(a5)[0]
            if size != int(pv(PA, a5n, "tadata_size", "H4"), 16):
                why5.append("knob: TA data %s bytes, not %s" % (L.hx(size), pv(PA, a5n, "tadata_size", "H4")))
            else:
                s, below = slots_of(a5, target)
                n, later = written(s)
                lines.append("%s: completed, %s, slots %s" % (a5n, d, s))
                if n != int(pv(PA, a5n, "slots_written", "H4")):
                    why5.append("only %d arrays written (4x not active)" % n)
                elif d != pv(PA, a5n, "diff", "H4"):
                    out5 = "complete-wrong-image"
                else:
                    out5 = "H4"
        elif a5["row"]["class"] == "fault":
            r = held_reading(a5)
            page = None if r is None or r["bif_fault"] is None else r["bif_fault"] >> 12
            lines.append("%s: held fault %s at page %s" % (a5n, L.hx(r and r["int_stat"]), L.hx(page)))
            if r and r["int_stat"] == int(pv(PA, a5n, "int_stat", "H5"), 16) and page == int(pv(PA, a5n, "fault_page", "H5"), 16):
                out5 = "H5-or-slack"
            else:
                out5 = "other-fault"
        else:
            why5.append("class %s" % a5["row"]["class"])
    if why5:
        lines.append("%s: NODATA (%s)" % (a5n, "; ".join(why5)))
    res["a5"] = out5
    return lines, res


def a_fault(outdir):
    lines, res = a_pair(outdir, "a5-320x400-max544", "a6-320x400-max320", (320, 400), "544x400")
    if not res["a6"]:
        s = "cannot tell: the a6 control failed"
    elif res["a5"] == "H4":
        s = "a6 PASS; a5 COMPLETES with 4 arrays in 0xa000: four arrays suffice at 320x400 (H4 sufficiency)"
    elif res["a5"] == "H5-or-slack":
        s = "cannot tell: a5 and a6 both fault (H5 or slack; the pre-approved slack pair 288x656 / 544x656 decides: run r2-a-slack)"
    else:
        s = "cannot tell: a5 %s" % (res["a5"] or "void")
    res["summary"] = s + "; E1 TA write: %s" % res["e1_a6"]
    return lines, res


def a_slack(outdir):
    cases = L.read_cases(outdir)
    sa4 = job(outdir, cases, "sa4-ctl-288x656-te20")
    ok4, why4 = check_ctl(sa4, sa4["name"], (288, 656), "544x656")
    lines = ["sa4 control: %s%s" % ("PASS" if ok4 else "FAIL", (": " + "; ".join(why4)) if why4 else "")]
    l2, res = a_pair(outdir, "sa5-288x656-max544", "sa6-288x656-max288", (288, 656), "544x656")
    res["sa4"] = ok4
    if not ok4:
        s = "cannot tell: the sa4 control failed"
    elif not res["a6"]:
        s = "cannot tell: the sa6 control failed"
    elif res["a5"] == "H4":
        s = "sa6 PASS; sa5 COMPLETES with 4 arrays: four arrays suffice (one page of slack); a5's fault at the boundary was the layout"
    elif res["a5"] == "H5-or-slack":
        s = "sa6 PASS; sa5 faults at the page past the 0x11000 TA data: more than four arrays plus a page are needed (H5)"
    else:
        s = "cannot tell: sa5 %s" % (res["a5"] or "void")
    res["summary"] = s + "; E1 TA write: %s" % res["e1_a6"]
    return lines + l2, res


def q286(roots):
    safe = a_safe(stage_dir(roots, "r2-a-safe"))[1]
    fault = a_fault(stage_dir(roots, "r2-a-fault"))[1]
    sd = stage_dir(roots, "r2-a-slack")
    slack = a_slack(sd)[1] if os.path.exists(os.path.join(sd, "cases.tsv")) else None
    s4 = set(safe["slot4"].values())
    if not safe["a4"] or not fault["a6"]:
        q = "cannot tell (a control failed: a4 %s, a6 %s)" % (safe["a4"], fault["a6"])
    elif safe["a3"] is not True or not s4 <= {"zero", "written"}:
        q = "cannot tell (a3 equals a1: %s; slot 4: %s)" % (safe["a3"], safe["slot4"])
    elif "written" in s4 and fault["a5"] == "H4":
        q = "INCONSISTENT: a dump shows a fifth array but a5 completed in four: cannot tell"
    elif "written" in s4:
        q = "closed H5: a fifth array is written (%s)" % sorted(k for k, v in safe["slot4"].items() if v == "written")
    elif s4 == {"zero"} and fault["a5"] == "H4":
        q = "closed H4: four arrays written at three layouts and sufficient at 320x400 (a5)"
    elif s4 == {"zero"} and fault["a5"] in ("H5-or-slack", "other-fault", "complete-wrong-image") and slack is not None:
        if not (slack["sa4"] and slack["a6"]):
            q = "cannot tell (a5 %s; the slack pair's controls failed: sa4 %s sa6 %s)" % (fault["a5"], slack["sa4"], slack["a6"])
        elif slack["a5"] == "H4":
            q = ("H4 holds with slack: slot 4 zero at three layouts, sa5 completes with four arrays; a5 faulted at 0x2000a only "
                 "because 320x400/544x400 is boundary-exact: the kernel layout needs a fix (Q140)")
        elif slack["a5"] == "H5-or-slack":
            q = ("more than four arrays plus a page are needed (sa5 faults) although slot 4 stays zero in the dumps: "
                 "NOT H4; H5 not shown by a dump either: cannot close")
        else:
            q = "cannot tell (a5 %s; sa5 %s)" % (fault["a5"], slack["a5"])
    else:
        q = "cannot tell (slot 4: %s; a5: %s; slack pair %s)" % (sorted(map(str, s4)), fault["a5"], "not run" if slack is None else slack["a5"])
    print("SUMMARY: Q286: %s" % q)
    return q


# =============================================================================================== driver
STAGES = {"r2-d-safe": d_stage(D_SAFE), "r2-d-fault": d_stage(D_FAULT), "r2-a-safe": a_safe, "r2-a-fault": a_fault,
          "r2-a-slack": a_slack}


def run_stage(stage, outdir):
    preds()
    lines, res = STAGES[stage](outdir)
    for ln in lines:
        print(ln)
    print("SUMMARY: %s: %s" % (stage, res["summary"]))
    return res


def stage_dir(roots, st):
    """The stage's directory in the first of the roots that has it (the first root otherwise)."""
    roots = [roots] if isinstance(roots, str) else list(roots)
    for r in roots:
        if os.path.exists(os.path.join(r, st, "cases.tsv")):
            return os.path.join(r, st)
    return os.path.join(roots[0], st)


def verdict(roots):
    preds()
    q281(roots)
    q286(roots)


def gate(stage, roots):
    """0 open; 1 closed: a prerequisite failed (the message says what to rerun); 3 not needed (r2-a-slack)."""
    preds()
    bad, rerun = [], []
    if stage == "r2-d-fault":
        v = d_rows(stage_dir(roots, "r2-d-safe"), ["d-ok-64"])[2]["d-ok-64"]
        if v != "PASS":
            bad.append("d-ok-64 control %s" % v)
            rerun.append("r2-d-safe")
    elif stage in ("r2-a-fault", "r2-a-slack"):
        sd = stage_dir(roots, "r2-a-safe")
        if not a_safe(sd)[1]["a4"]:
            bad.append("a4 control failed or r2-a-safe not run")
            rerun.append("r2-a-safe")
    if stage == "r2-a-slack":
        fd = stage_dir(roots, "r2-a-fault")
        if not os.path.exists(os.path.join(fd, "cases.tsv")):
            bad.append("r2-a-fault not run")
            rerun.append("r2-a-fault")
        else:
            r = a_fault(fd)[1]
            if not r["a6"]:
                bad.append("a6 control failed (the layout model is wrong or the held method broke)")
            elif r["a5"] == "H4":
                print("SUMMARY: gate r2-a-slack: not needed (a5 completed with four arrays: H4)")
                return 3
            elif r["a5"] not in ("H5-or-slack", "other-fault", "complete-wrong-image"):
                bad.append("a5 is void (%s): the slack pair cannot repair a void a5; rerun r2-a-fault" % r["a5"])
                rerun.append("r2-a-fault")
    print("SUMMARY: gate %s: %s" % (stage, "open" if not bad else "CLOSED (" + "; ".join(bad) + (
        "; rerun: run/r2.sh --only " + " ".join(rerun) if rerun else "") + ")"))
    return 0 if not bad else 1


def main(argv):
    ok, msg = L.verify_freeze()
    if not ok:
        print(msg)
        print("SUMMARY: refused: the frozen files changed (run/freeze_r2.sh verify)")
        return 2
    if len(argv) >= 3 and argv[0] == "gate":
        return gate(argv[1], argv[2:])
    if len(argv) >= 2 and argv[0] == "verdict":
        verdict(argv[1:])
        return 0
    if len(argv) == 2 and argv[0] in STAGES:
        run_stage(argv[0], argv[1])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
