#!/usr/bin/env python3
"""S3 scorers, written and frozen before the run.  Each prints its rows and ends with one SUMMARY line.

  score_s3.py STAGE OUTDIR            one stage (s3-a-safe, s3-e1-ctl, s3-e1, s3-a-fault, s3-xfer)
  score_s3.py verdict ROOT...         Q286 (pixel A) and Q003 (pixel E1) from all five stages
  score_s3.py gate STAGE ROOT...      exit 0 if the stages STAGE depends on passed their controls
(ROOT: an attempt's out/ATT directory; with several, each stage is read from the first that has it)

Refuses to score unless run/freeze_s3.sh verify passes (frozen predictions, scorers, tables, runner).
Missing or empty data, an rc or class that is not a result, a failed knob proof and a failed control
are NODATA or "cannot tell", never a verdict.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3lib as L  # noqa: E402

PA = PE = None


def preds():
    global PA, PE
    PA = L.load_predictions("s3-a.tsv")
    PE = L.load_predictions("s3-e1.tsv")


def job(outdir, cases, name):
    """Everything kept for one job; j['void'] lists what is missing."""
    j = {"name": name, "void": []}
    row = (cases or {}).get(name)
    if row is None:
        j["void"].append("no cases.tsv row")
        return j
    j["row"] = row
    if row.get("rc", "") == "" or not re.fullmatch(r"-?\d+", row["rc"]):
        j["void"].append("no rc")
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


def diff_of(j):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", j.get("out") or "", re.M)
    return None if not m else "%s of %s" % (m.group(1), m.group(2))


def max_echo(j):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", j.get("out") or "", re.M)
    return m.group(1) if m else None


def slots_of(j, target):
    if j.get("tadata") is None:
        return None, None
    lay = L.layout(*target)
    s, below = L.tadata_slots(j["tadata"], lay["rgn"], lay["rgn_size"])
    return s, below


def written(slots):
    """The number of leading non-empty slots, and whether any slot after them is written."""
    n = 0
    while n < len(slots) and slots[n] > 0:
        n += 1
    return n, any(x > 0 for x in slots[n:])


# ---- held readings (E1) --------------------------------------------------------------------------

def held_reading(j):
    """The held fault as snap 1 shows it, its extra bits against snap 0 and the timeline."""
    s0, s1, s3 = j.get("snap0"), j.get("snap1"), j.get("snap3")
    if s1 is None or s0 is None:
        return None
    r = {"status": s1[L.REG_STATUS], "status2": s1[L.REG_STATUS2], "int_stat": s1[L.REG_INT_STAT],
         "bif_fault": s1.get(L.REG_FAULT), "bif_ctrl": s1.get(L.REG_BIF_CTRL)}
    extra1 = s1[L.REG_STATUS] & ~L.KNOWN_STATUS & ~L.MASK_STATUS & ~s0[L.REG_STATUS]
    extra2 = s1[L.REG_STATUS2] & ~L.KNOWN_STATUS2 & ~s0[L.REG_STATUS2]
    r["extra_snap"] = (extra1, extra2)
    r["stable"] = j.get("snap2") is not None and all(
        j["snap2"].get(k) == s1.get(k) for k in (L.REG_STATUS, L.REG_STATUS2, L.REG_INT_STAT, L.REG_FAULT))
    r["cleared"] = None if s3 is None else not (s3[L.REG_INT_STAT] & L.FAULT_REQ)
    r["after_reset"] = None if s3 is None else (s3[L.REG_INT_STAT], s3.get(L.REG_FAULT))
    r["tl"] = None
    if j.get("tl"):
        w = L.fault_window(j["tl"])
        if w:
            r["tl"] = w
            extra1 |= w["rose_status"] & ~L.KNOWN_STATUS & ~L.MASK_STATUS
            extra2 |= w["rose_status2"] & ~L.KNOWN_STATUS2
    r["extra"] = (extra1, extra2)
    # bits seen only in the timeline (rose at the fault inside the hold window, gone by snap 1)
    r["extra_tl_only"] = (extra1 & ~r["extra_snap"][0], extra2 & ~r["extra_snap"][1])
    return r


def fmt_reading(r):
    t = ""
    if r["tl"]:
        t = "; at the fault (t %.3f ms): rose status %#x status2 %#x" % (
            r["tl"]["t"] / 1e6, r["tl"]["rose_status"], r["tl"]["rose_status2"])
    return ("status %#x status2 %#x int_stat %#x bif_fault %s bif_ctrl %s; stable %s; cleared by the reset %s%s"
            % (r["status"], r["status2"], r["int_stat"], L.hx(r["bif_fault"]), L.hx(r["bif_ctrl"]),
               r["stable"], r["cleared"], t))


def e1_row(j, P, case):
    """Score one held fault against HE / HF.  Returns (ok, text, verdict) with verdict in
    HE, HE-edm, HF, NODATA, NOFAULT."""
    if j["void"]:
        return False, "%s: NODATA (%s)" % (case, "; ".join(j["void"])), "NODATA"
    row = j["row"]
    r = held_reading(j)
    if r is None:
        return False, "%s: NODATA (no snap 0 or snap 1)" % case, "NODATA"
    if row["class"] != "fault":
        return False, "%s: no held fault (class %s, rc %s): %s" % (case, row["class"], row["rc"], fmt_reading(r)), "NOFAULT"
    want_int = int(L.pred(P, case, "int_stat"), 16)
    notes = []
    if r["int_stat"] != want_int:
        notes.append("int_stat %#x, predicted %#x" % (r["int_stat"], want_int))
    try:
        page = int(L.pred(P, case, "fault_page"), 16)
        if r["bif_fault"] is None or (r["bif_fault"] >> 12) != page:
            notes.append("fault page %s, predicted %#x" % (L.hx(None if r["bif_fault"] is None else r["bif_fault"] >> 12), page))
    except KeyError:
        pass
    e1, e2 = r["extra"]
    if e1 or e2:
        verdict = "HF"
        notes.append("extra bits: status %#x status2 %#x (not set before the job, not bits 29 / 10, 7, 6)" % (e1, e2))
    else:
        verdict = "HE"
        he2 = int(L.pred(P, case, "status2", "HE"), 16)
        if r["status2"] != he2:
            alt = [m for v, m, _ in P.get((case, "status2"), []) if m != "HE" and int(v, 16) == r["status2"]]
            if alt:
                verdict = alt[0]
            notes.append("status2 %#x, HE predicted %#x%s" % (r["status2"], he2, " (= %s)" % alt[0] if alt else ""))
        if r["status"] != int(L.pred(P, case, "status", "HE"), 16):
            notes.append("status %#x" % r["status"])
    return (not notes or verdict != "HF"), "%s: %s: %s%s" % (
        case, verdict, fmt_reading(r), ("; " + "; ".join(notes)) if notes else ""), verdict


def control_e444(j, P, case):
    """E444's reading reproduced exactly: class fault, the hold message, the four registers."""
    if j["void"]:
        return False, "%s: NODATA (%s)" % (case, "; ".join(j["void"]))
    r = held_reading(j)
    if r is None:
        return False, "%s: NODATA (no snap 0 or snap 1)" % case
    bad = []
    if j["row"]["class"] != "fault":
        bad.append("class %s" % j["row"]["class"])
    if j["row"].get("held_msg") != "yes":
        bad.append("no hold message (knob proof)")
    for q, k in (("status", "status"), ("status2", "status2"), ("int_stat", "int_stat"), ("bif_fault", "bif_fault")):
        want = int(L.pred(P, case, q), 16)
        if r[k] != want:
            bad.append("%s %s, E444 %#x" % (q, L.hx(r[k]), want))
    if r["extra_snap"] != (0, 0):
        bad.append("extra bits at snap 1 %#x/%#x" % r["extra_snap"])
    if r["cleared"] is not True:
        bad.append("not cleared by the reset")
    note = ""
    if r["extra_tl_only"] != (0, 0):
        note = "; timeline-only bits (reported, not part of the pass rule) status %#x status2 %#x" % r["extra_tl_only"]
    return (not bad), "%s: %s: %s%s%s" % (case, "PASS" if not bad else "FAIL", fmt_reading(r),
                                           ("; " + "; ".join(bad)) if bad else "", note)


# ---- stages --------------------------------------------------------------------------------------

def a_safe(outdir):
    cases = L.read_cases(outdir)
    lines, res = [], {}
    a4 = job(outdir, cases, "a4-ctl-320x400-te20")
    ok4, why4 = True, []
    if a4["void"]:
        ok4, why4 = False, ["NODATA: " + "; ".join(a4["void"])]
    else:
        if a4["row"]["class"] != "ok" or a4["row"]["rc"] != "0":
            ok4 = False; why4.append("class %s rc %s" % (a4["row"]["class"], a4["row"]["rc"]))
        if diff_of(a4) != L.pred(PA, a4["name"], "diff"):
            ok4 = False; why4.append("diff %s" % diff_of(a4))
        if max_echo(a4) != L.pred(PA, a4["name"], "max_echo"):
            ok4 = False; why4.append("knob: tool echo %s" % max_echo(a4))
        size = None if a4["tadata"] is None else len(a4["tadata"])
        if size != int(L.pred(PA, a4["name"], "tadata_size"), 16):
            ok4 = False; why4.append("knob: TA data %s bytes, not 0xa000 (max-width had no effect)" % L.hx(size))
        else:
            s, below = slots_of(a4, (320, 400))
            n, later = written(s)
            if n != int(L.pred(PA, a4["name"], "slots_written")) or later or below:
                ok4 = False; why4.append("slots %s (below rgn: %d non-zero)" % (s, below))
    res["a4"] = ok4
    lines.append("a4 control: %s%s" % ("PASS" if ok4 else "FAIL", (": " + "; ".join(why4)) if why4 else ""))
    slot4 = {}
    for name, tgt in (("a1-256x160-dump", (256, 160)), ("a2-320x128-dump", (320, 128))):
        j = job(outdir, cases, name)
        why = list(j["void"])
        if not why:
            if j["row"]["class"] != "ok" or j["row"]["rc"] != "0":
                why.append("class %s rc %s" % (j["row"]["class"], j["row"]["rc"]))
            if diff_of(j) != L.pred(PA, name, "diff"):
                why.append("diff %s" % diff_of(j))
            if j["tadata"] is None or len(j["tadata"]) != int(L.pred(PA, name, "tadata_size"), 16):
                why.append("TA data %s bytes" % (None if j["tadata"] is None else hex(len(j["tadata"]))))
        if why:
            lines.append("%s: NODATA (%s)" % (name, "; ".join(why)))
            slot4[name] = None
            continue
        s, below = slots_of(j, tgt)
        n, later = written(s)
        if n < int(L.pred(PA, name, "min_slots_written")):
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
            name, lay["rgn_size"], lay["rgn"], s, below, slot4[name],
            L.pred(PA, name, "slot4", "H4"), L.pred(PA, name, "slot4", "H5"),
            "; a gap: a slot after the first empty one is written" if later else ""))
    a1 = job(outdir, cases, "a1-256x160-dump")
    a3 = job(outdir, cases, "a3-256x160-rep")
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
        s = "cannot tell: the a4 control failed (%s); do not run s3-a-fault" % "; ".join(why4)
    elif None in vals:
        s = "cannot tell: a1 or a2 void; a4 control PASS"
    elif vals & {"gap", "not-array"}:
        s = "cannot tell: slot 4 is %s (it lies in the ZLS area at these sizes; a fifth array must look like slots 0-3)" % slot4
    elif res["a3"] is not True:
        s = "cannot tell: the replicate a3 does not equal a1 (no closure without a repeatable dump); slot 4 %s" % slot4
    elif vals == {"zero"}:
        s = "a4 control PASS (TA data 0xa000); slot 4 zero at 256x160 and 320x128: H4 for what the TA writes (f = 4)"
    elif "written" in vals:
        s = "a4 control PASS; slot 4 WRITTEN (%s): H5 (f = 5 arrays written)" % ", ".join(k for k, v in slot4.items() if v == "written")
    else:
        s = "cannot tell"
    if res["a3"] is False:
        s += "; the replicate a3 differs from a1 (dumps not repeatable)"
    res["summary"] = s
    return lines, res


def e1_ctl(outdir):
    cases = L.read_cases(outdir)
    lines, oks = [], []
    for name in ("e1-ta-read", "e1-bg-fetch"):
        ok, txt = control_e444(job(outdir, cases, name), PE, name)
        oks.append(ok)
        lines.append(txt)
    res = {"pass": all(oks)}
    res["summary"] = ("method ok: both controls reproduce E444's held readings" if res["pass"]
                      else "METHOD BROKEN: a control did not reproduce E444 (do not run s3-e1; E1 cannot tell)")
    return lines, res


def e1(outdir):
    cases = L.read_cases(outdir)
    lines, verdicts = [], {}
    tex = job(outdir, cases, "e1-tex")
    if not tex["void"] and L.pred(PE, "e1-tex", "scratch_line") not in (tex["out"] or ""):
        tex["void"].append("knob: no '(64 KiB)' scratch line")
    if not tex["void"] and tex["row"].get("held_msg") != "yes" and tex["row"]["class"] == "fault":
        tex["void"].append("knob: the fault was not held (no hold message)")
    ok, txt, v = e1_row(tex, PE, "e1-tex")
    lines.append(txt); verdicts["e1-tex"] = v
    return e1_summary(lines, verdicts)


def e1_summary(lines, verdicts):
    res = {"verdicts": verdicts}
    res["summary"] = "; ".join("%s %s" % kv for kv in verdicts.items())
    if any(v in ("NODATA", "NOFAULT") for v in verdicts.values()):
        res["summary"] = "cannot tell for " + ", ".join(k for k, v in verdicts.items() if v in ("NODATA", "NOFAULT")) + ": " + res["summary"]
    return lines, res


def xfer(outdir):
    """The last stage: debugfs xfer_ro (a -ENOENT / -EINVAL / -ENODEV stop here cannot cost a later stage)."""
    cases = L.read_cases(outdir)
    lines, verdicts = [], {}
    xr = job(outdir, cases, "e1-xfer-ro")
    if not xr["void"]:
        m = re.search(r"dwords written through the read-only alias: (\d+)", xr["out"] or "")
        if not m:
            xr["void"].append("no xfer_ro output (the check did not run)")
        elif m.group(1) != L.pred(PE, "e1-xfer-ro", "written"):
            lines.append("e1-xfer-ro: %s dwords written through the read-only alias (NOT PROTECTED)" % m.group(1))
    ok, txt, v = e1_row(xr, PE, "e1-xfer-ro")
    lines.append(txt); verdicts["e1-xfer-ro"] = v
    return e1_summary(lines, verdicts)


def a_fault(outdir):
    cases = L.read_cases(outdir)
    lines, res = [], {}
    a6 = job(outdir, cases, "a6-320x400-max320")
    a6ok, why6 = False, []
    if a6["void"]:
        why6.append("NODATA: " + "; ".join(a6["void"]))
    else:
        r = held_reading(a6)
        if max_echo(a6) != L.pred(PA, a6["name"], "max_echo"):
            why6.append("knob: tool echo %s" % max_echo(a6))
        if a6["row"]["class"] == "ok":
            why6.append("COMPLETED: the layout model is wrong, a5 says nothing")
        elif a6["row"]["class"] != "fault" or r is None:
            why6.append("class %s" % a6["row"]["class"])
        else:
            page = None if r["bif_fault"] is None else r["bif_fault"] >> 12
            if r["int_stat"] != int(L.pred(PA, a6["name"], "int_stat"), 16):
                why6.append("int_stat %#x" % r["int_stat"])
            want = int(L.pred(PA, a6["name"], "fault_page"), 16)
            if page is None or page < want:
                why6.append("fault page %s, before the end of the TA data %#x" % (L.hx(page), want))
            elif page != want:
                lines.append("a6: the fault is past the TA data at page %#x, not its first page %#x (accepted)" % (page, want))
            if a6["row"].get("held_msg") != "yes":
                why6.append("no hold message")
        a6ok = not why6
    res["a6"] = a6ok
    lines.append("a6 control: %s%s" % ("PASS" if a6ok else "FAIL", (": " + "; ".join(why6)) if why6 else ""))
    ok, txt, v = e1_row(a6, PE, "a6-320x400-max320")
    lines.append("E1 TA write row, " + txt)
    res["e1_a6"] = v
    a5 = job(outdir, cases, "a5-320x400-max544")
    why5 = list(a5["void"])
    out5 = None
    if not why5:
        if max_echo(a5) != L.pred(PA, a5["name"], "max_echo"):
            why5.append("knob: tool echo %s" % max_echo(a5))
        elif a5["row"]["class"] == "ok":
            size = None if a5["tadata"] is None else len(a5["tadata"])
            d = diff_of(a5)
            if size != int(L.pred(PA, a5["name"], "tadata_size", "H4"), 16):
                why5.append("knob: TA data %s bytes, not 0xa000" % L.hx(size))
            else:
                s, below = slots_of(a5, (320, 400))
                n, later = written(s)
                lines.append("a5: completed, %s, slots %s" % (d, s))
                if n != int(L.pred(PA, a5["name"], "slots_written", "H4")):
                    why5.append("only %d arrays written (4x not active)" % n)
                elif d != L.pred(PA, a5["name"], "diff", "H4"):
                    out5 = "complete-wrong-image"
                else:
                    out5 = "H4"
        elif a5["row"]["class"] == "fault":
            r = held_reading(a5)
            page = None if r is None or r["bif_fault"] is None else r["bif_fault"] >> 12
            lines.append("a5: held fault %s at page %s" % (L.hx(r and r["int_stat"]), L.hx(page)))
            if r and r["int_stat"] == int(L.pred(PA, a5["name"], "int_stat", "H5"), 16) and \
                    page == int(L.pred(PA, a5["name"], "fault_page", "H5"), 16):
                out5 = "H5-or-slack"
            else:
                out5 = "other-fault"
        else:
            why5.append("class %s" % a5["row"]["class"])
    if why5:
        lines.append("a5: NODATA (%s)" % "; ".join(why5))
    res["a5"] = out5
    if not a6ok:
        s = "cannot tell: the a6 control failed (%s)" % "; ".join(why6)
    elif out5 == "H4":
        s = "a6 PASS; a5 COMPLETES with 4 arrays in 0xa000: four arrays suffice at 320x400 (H4 sufficiency)"
    elif out5 == "H5-or-slack":
        s = "cannot tell: a5 and a6 both fault (H5 or slack; needs a kernel layout with f = 4 at 288x144, Q140)"
    else:
        s = "cannot tell: a5 %s" % (out5 or "void")
    res["summary"] = s + "; E1 TA write: %s" % v
    return lines, res


STAGES = {"s3-a-safe": a_safe, "s3-e1-ctl": e1_ctl, "s3-e1": e1, "s3-a-fault": a_fault, "s3-xfer": xfer}


def run_stage(stage, outdir):
    preds()
    lines, res = STAGES[stage](outdir)
    for ln in lines:
        print(ln)
    print("SUMMARY: %s: %s" % (stage, res["summary"]))
    return res


def stage_dir(roots, st):
    """The stage's directory in the first of the attempt roots that has it (the first root otherwise)."""
    roots = [roots] if isinstance(roots, str) else list(roots)
    for r in roots:
        if os.path.isdir(os.path.join(r, st)):
            return os.path.join(r, st)
    return os.path.join(roots[0], st)


def verdict(roots):
    preds()
    r = {st: STAGES[st](stage_dir(roots, st))[1] for st in STAGES}
    safe, fault = r["s3-a-safe"], r["s3-a-fault"]
    s4 = set(safe["slot4"].values())
    if not safe["a4"] or not fault["a6"]:
        q286 = "cannot tell (a control failed: a4 %s, a6 %s)" % (safe["a4"], fault["a6"])
    elif safe["a3"] is not True or not s4 <= {"zero", "written"}:
        q286 = "cannot tell (a3 equals a1: %s; slot 4: %s)" % (safe["a3"], safe["slot4"])
    elif "written" in s4 and fault["a5"] == "H4":
        q286 = "INCONSISTENT: a dump shows a fifth array but a5 completed in four: cannot tell"
    elif "written" in s4:
        q286 = "closed H5: a fifth array is written (%s)" % sorted(k for k, v in safe["slot4"].items() if v == "written")
    elif s4 == {"zero"} and fault["a5"] == "H4":
        q286 = "closed H4: four arrays written at three layouts and sufficient at 320x400 (a5)"
    else:
        q286 = "cannot tell (slot 4: %s; a5: %s)" % (sorted(map(str, s4)), fault["a5"])
    print("SUMMARY: Q286: %s" % q286)
    if not r["s3-e1-ctl"]["pass"]:
        q003 = "cannot tell: the E444 controls failed"
    else:
        v = dict(r["s3-e1"]["verdicts"], **r["s3-xfer"]["verdicts"], **{"a6 (TA write)": fault["e1_a6"]})
        if any(x == "HF" for x in v.values()):
            q003 = "HF: a fault raised a status bit of its own: %s" % v
        elif all(x in ("HE", "HE-edm") for x in v.values()):
            q003 = "HE for every held kind: no event bit of its own; %s" % v
        else:
            q003 = "partly: %s" % v
    print("SUMMARY: Q003 E1: %s" % q003)
    return q286, q003


def gate(stage, roots):
    preds()
    need = {"s3-e1": ["s3-e1-ctl"], "s3-a-fault": ["s3-a-safe", "s3-e1-ctl"], "s3-xfer": ["s3-e1-ctl"]}.get(stage, [])
    bad = []
    for st in need:
        res = STAGES[st](stage_dir(roots, st))[1]
        if st == "s3-a-safe" and not res["a4"]:
            bad.append("a4 control failed")
        if st == "s3-e1-ctl" and not res["pass"]:
            bad.append("E444 controls failed")
    print("SUMMARY: gate %s: %s" % (stage, "open" if not bad else "CLOSED (" + "; ".join(bad) + ")"))
    return not bad


def main(argv):
    ok, msg = L.verify_freeze()
    if not ok:
        print(msg)
        print("SUMMARY: refused: the frozen files changed (run/freeze_s3.sh verify)")
        return 2
    if len(argv) >= 3 and argv[0] == "gate":
        return 0 if gate(argv[1], argv[2:]) else 1
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
