#!/usr/bin/env python3
"""R4-G scorer (r4-render4x), written and frozen before the run.  Each command prints its rows and ends with one SUMMARY.

  score_r.py STAGE OUTDIR          one stage: s0 c p o t h  (the controls of s0 are read from OUTDIR's parent, the attempt directory)
  score_r.py gate STAGE ROOT...    exit 0 if s0's three controls passed (every stage but s0), 1 closed
  score_r.py verdict ROOT...       the session: Q113 (c), Q292 with H-PB (p, o), Q293 (t), Q140 (h)
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

Hypotheses (frozen with their predictions in predictions/*.tsv; [infer] where the name is ours):
  H-PB     p: a 4x full-triangle job uses U4 = 1 + ceil(2 tiles16 / 32) scene pages and the TA data of the layout formula, at every
           size whose need is under the PB's P - 0x22 = 1024 pages; it completes with 0 wrong pixels.
  H-SPM4   o: a 4x scene that overflows the PB faults on the 3D side (BIF_INT_STAT bits 15:0 = 0x0100, BIF_FAULT page 0x10000, SB 1:
           E828 j4's and E511's word) where the same overflow at 1x ends in -ENOSPC without a fault.  The page rule (completes when
           P - 0x22 >= need) is the control o1 to o3 carry.
  H-SAME / H-PAD   t: the inserted dword of CR_TE_AA bits 31:30 with bit 29 clear is zero and sits before the object's format word, and a
           four-array context reads the displaced layout as a one-array one does (image empty).  H-FIELD: it is a non-zero field.
  H-REPLAY h: after a TA write fault the pending region-header write is issued again when the TA next runs: every failing health
           triangle names the failed job's own BIF_FAULT word; a context that maps the page, or a fill, does not fault.
  Q113     c: a pixel of TEXTYPE 2 with smp3d reads the face of the coordinate of largest magnitude and its sign (+x, -x, +y, -y, +z, -z).

The verdict rules are scorekit's (score/scorekit.py, byte for byte resgx545 tools/closing/scorekit.py): any control that is not PASS
(FAIL, NODATA) shuts the gate of every dependent row; replicates that disagree are mixed, never held; a void job is cannot tell and
never a pass; the headline names how many rows decided.  Refuses to score unless run/freeze_k.sh verify passes.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import cubegen as C  # noqa: E402
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import scorekit as K  # noqa: E402

PRED = {}
S0_CTL = ("s0-1x-1024x768", "s0-4x-288x144", "s0-4x-1024x768")
PARAM_DUMP_BYTES = 0x464 * 4096          # a render_param dump taken at render_pb_pages 0x422
BAD_CLASSES = ("fault", "hang", "fail")


def preds():
    for st in ("s0", "c", "p", "o", "t", "h"):
        PRED[st] = L.load_predictions(st + ".tsv")


# ---- one job's kept files -------------------------------------------------------------------------------------------------------
def job(outdir, cases, name):
    """Everything kept for one job; j['void'] lists what makes it no data."""
    j = {"name": name, "void": []}
    row = (cases or {}).get(name)
    if row is None:
        j["void"].append("no cases.tsv row (not run)")
        return j
    j["row"] = row
    if row.get("class") == "skipped":
        j["void"].append("skipped (its condition did not hold)")
        return j
    rc = row.get("rc", "")
    if not rc.lstrip("-").isdigit():
        j["void"].append("no rc")
    else:
        j["rc"] = int(rc)
        if j["rc"] in (2, 124, 125, 126, 127) or j["rc"] >= 128:
            j["void"].append("rc %d is not a result of the tool" % j["rc"])
    if row.get("class") not in ("ok", "fault", "hang", "fail"):
        j["void"].append("class %r" % row.get("class"))
    p = lambda s: os.path.join(outdir, name + s)  # noqa: E731
    j["out"] = L.read_text(p(".txt.gz"))
    if j["out"] is None:
        j["void"].append("tool output missing or empty")
    j["dmesg"] = L.read_text(p(".dmesg.gz")) or ""
    j["param"] = L.read_bytes(p(".tri.param.bin.gz"))
    j["tadata"] = L.read_bytes(p(".tri.tadata.bin.gz"))
    j["heldparam"] = L.read_bytes(p(".heldparam.bin.gz"))
    j["heldtadata"] = L.read_bytes(p(".heldtadata.bin.gz"))
    j["regs"] = {k: L.read_text(p(".snap%s.regs.gz" % k)) for k in ("0", "1", "2", "3", "9", "ctx", "fill", "h1", "h2", "h3", "h4")}
    return j


def stage_dir(roots, stage):
    for r in roots:
        if os.path.exists(os.path.join(r, stage, "cases.tsv")):
            return os.path.join(r, stage)
    return os.path.join(roots[0], stage) if roots else stage


def got_of(j):
    o = j["out"]
    pb = j["param"]
    reg0724 = L.reg(o, 0x0724) or L.reg(j["regs"].get("9"), 0x0724)
    return {"rc": str(j.get("rc")), "echo": L.echo(o), "target_hash": L.target_hash(o), "diff": L.diff_text(o),
            "tri1": L.tri_counts_text(o), "renders": L.renders(o),
            "tadata_size": None if j["tadata"] is None else "%d" % len(j["tadata"]),
            "pb_used": None if pb is None or len(pb) != PARAM_DUMP_BYTES else "%d" % M.pages_nonzero(pb),
            "reg0724": reg0724, "par_0_64": L.words(pb, 0, 64), "par_0_32": L.words(pb, 0, 32)}


def fault_info(j):
    """The job's fault: {'int': bits 15:0 of BIF_INT_STAT, 'word': BIF_FAULT, 'page', 'sb', 'cid', 'src'} or None.  The kernel's job fault
    line first (plain jobs), else the held snap 1 registers (a held job)."""
    fl = L.bif_faults(j.get("dmesg")) or L.bif_faults(j.get("out"))
    if fl:
        stat, word = fl[0]
        d = L.decode_fault(word)
        return {"int": stat & 0xffff, "word": word, "page": d[0], "sb": d[1], "cid": d[2], "src": "kernel log"}
    s1 = j["regs"].get("1")
    if s1:
        v, w = L.reg(s1, 0x0c04), L.reg(s1, 0x0c08)
        if v and w and (int(v, 16) & 0xffff):
            d = L.decode_fault(int(w, 16))
            return {"int": int(v, 16) & 0xffff, "word": int(w, 16), "page": d[0], "sb": d[1], "cid": d[2], "src": "snap 1"}
    return None


def void_text(j):
    return "NODATA (%s)" % "; ".join(j["void"])


def ctl(j, P, name, keys=None):
    """A control against its frozen quantities (set ctl): ("PASS" | "FAIL" | "NODATA", text)."""
    if j["void"]:
        return "NODATA", void_text(j)
    if j["row"]["class"] != "ok":
        return "FAIL", "class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    got, bad, missing = got_of(j), [], []
    for (case, q), vals in sorted(P.items()):
        if case != name or vals[0][2] != "ctl" or q not in got or (keys and q not in keys):
            continue
        want = vals[0][0]
        if got[q] is None:
            missing.append(q)
        elif got[q] != want:
            bad.append("%s %s, frozen %s" % (q, _short(got[q]), _short(want)))
    if missing and not bad:
        return "NODATA", "NODATA (nothing read for %s: the output or a dump is missing)" % ", ".join(missing)
    return ("FAIL" if bad else "PASS"), ("; ".join(bad) if bad else "as frozen (hash %s, diff %s)" % (got["target_hash"], got["diff"]))


def _short(v):
    return "none" if v is None else (v if len(str(v)) < 60 else str(v)[:56] + "...")


def neg(x):
    return None if x is None else not x


# ---- s0 ---------------------------------------------------------------------------------------------------------------------------
def s0_stage(outdir):
    P = PRED["s0"]
    cases = L.read_cases(outdir)
    res, lines, regs_ok = {}, [], []
    for n in S0_CTL:
        j = job(outdir, cases, n)
        v, t = ctl(j, P, n)
        res[n] = v
        extra = ""
        if not j["void"]:
            g = got_of(j)
            pu = L.pred_or(P, n, "pb_used")
            extra = "; pb pages used %s (model %s: %s)" % (g["pb_used"], pu, "equal" if g["pb_used"] == pu else "differs")
            r = L.pred_or(P, n, "reg0724")
            if r:
                regs_ok.append(g["reg0724"] == r)
                extra += "; reg 0x0724 %s (U4 - 1 reading %s: %s)" % (g["reg0724"], r, "equal" if g["reg0724"] == r else "differs")
        lines.append("%s: %s: %s%s" % (n, v, t, extra))
    g = K.gate(res)
    aux = len(regs_ok) == 2 and all(regs_ok)
    s = "s0: controls %s; later stages %s; reg 0x0724 as a reported check %s" % (
        {k: v for k, v in res.items()}, "open" if g.ok else "CLOSED (the session is void)", "usable" if aux else "not usable")
    return lines, {"verdicts": res, "gate": g, "summary": s, "aux_reg": aux}


def gate(stage, roots):
    if stage == "s0":
        return 0, "gate s0: no prerequisite"
    d = stage_dir(roots, "s0")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate %s: closed: no s0 stage was kept (run: run/k.sh --only s0)" % stage
    _, r = s0_stage(d)
    if not r["gate"].ok:
        return 1, "gate %s: closed: s0 controls %s (the session is void: the lead decides)" % (stage, "; ".join(r["gate"].problems))
    return 0, "gate %s: open (s0's three controls passed)" % stage


def s0_gate(roots, outdir):
    d = stage_dir(roots, "s0") if roots else None
    if d and os.path.exists(os.path.join(d, "cases.tsv")):
        _, r = s0_stage(d)
        return r["verdicts"], r["aux_reg"]
    return {n: "NODATA" for n in S0_CTL}, False


# ---- c: Q113's held-out cube row --------------------------------------------------------------------------------------------------
def c_stage(outdir, roots=None):
    P = PRED["c"]
    cases = L.read_cases(outdir)
    lines, rows = [], {}
    # control: E726's cu-xn program again
    j = job(outdir, cases, "c-cu-xn")
    if j["void"]:
        cv, ct = "NODATA", void_text(j)
    else:
        f = C.observed(j["out"])
        if f is None:
            cv, ct = "NODATA", "NODATA (no 2048 pixel rows in the output)"
        else:
            hist = ",".join(str(int((f == i).sum())) for i in range(6))
            vals = [int(x, 16) for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", j["out"], re.M) for x in m.group(2).split()]
            sha = L.sha256(",".join("%08x" % v for v in vals).encode())
            bad = []
            if j["row"]["class"] != "ok" or j.get("rc") != 0:
                bad.append("class %s rc %s" % (j["row"]["class"], j.get("rc")))
            if hist != L.pred(P, "c-cu-xn", "faces_hist"):
                bad.append("faces %s, frozen %s" % (hist, L.pred(P, "c-cu-xn", "faces_hist")))
            if sha != L.pred(P, "c-cu-xn", "pix_sha256"):
                bad.append("the 2048 pixels differ from E726's (sha256 %s)" % sha[:12])
            cv, ct = ("FAIL", "; ".join(bad)) if bad else ("PASS", "face 1 on 2048 of 2048 and E726's pixels, byte for byte")
    lines.append("c-cu-xn: %s: %s" % (cv, ct))
    ctls = {"c-cu-xn": cv}
    for case in ("c-cube-a", "c-cube-b"):
        j = job(outdir, cases, case)
        if j["void"]:
            rows[case] = (None, void_text(j))
            lines.append("%s: %s" % (case, void_text(j)))
            continue
        f = C.observed(j["out"])
        if f is None or j["row"]["class"] != "ok" or j.get("rc") != 0:
            rows[case] = (None, "no reading (class %s rc %s, %s)" % (j["row"]["class"], j.get("rc"), "no pixel rows" if f is None else "pixels read"))
            lines.append("%s: %s" % (case, rows[case][1]))
            continue
        want_hist = L.pred(P, case, "faces_hist")
        hist = ",".join(str(int((f == i).sum())) for i in range(6))
        sha = C.faces_sha256(f) if (f >= 0).all() else None
        if sha == L.pred(P, case, "faces_sha256"):
            rows[case] = (True, "faces %s on 2048 of 2048 pixels, every pixel as the rule says" % hist)
        else:
            # which pixels differ, and how far they are from a tie
            spec = C.HELDOUT[case.replace("c-", "r4g-")]
            pf, gap = C.faces(*spec)
            diff = [i for i in range(2048) if int(f[i]) != int(pf[i])]
            near = min((float(gap[i]) for i in diff), default=0.0)
            unread = int((f < 0).sum())
            rows[case] = (False, "faces %s (frozen %s): %d of 2048 pixels differ (%d are no cube read), the smallest margin among them %.4f"
                          % (hist, want_hist, len(diff), unread, near))
        lines.append("%s: %s" % (case, "held: " + rows[case][1] if rows[case][0] else "REFUTED: " + rows[case][1]))
    states = [rows[c][0] for c in ("c-cube-a", "c-cube-b")]
    claim = ("Q113: TEXTYPE 2 with smp3d reads the face of the coordinate of largest magnitude and its sign on 2 held-out off-axis jobs "
             "(4096 pixels), the cu-xn control again as in E726: the face mapping is no longer post hoc [infer]; Q113 may be retired as answered "
             "(R4-3), its edges and (s, t) are Q284's")
    q = K.headline(claim, ctls, states)
    return lines, {"verdicts": ctls, "rows": rows, "q113": q, "summary": "c: control %s, held-out %s; %s" % (cv, [rows[c][0] for c in rows], q)}


# ---- p: the 4x page need ----------------------------------------------------------------------------------------------------------
def p_row(j, P, name, aux):
    """(state, text): True held, False refuted (a fault, an overflow or a different page count or TA data), None no reading."""
    if j["void"]:
        return None, void_text(j)
    if j["row"]["class"] in ("fault", "hang"):
        fi = fault_info(j)
        return False, "REFUTES H-PB: %s (the page need passes at this size)%s" % (j["row"]["class"], "" if not fi else
            ", BIF_FAULT 0x%08x int 0x%04x" % (fi["word"], fi["int"]))
    if j["row"]["class"] != "ok":
        return None, "class %s rc %s: no reading" % (j["row"]["class"], j.get("rc"))
    if L.overflowed(j["out"], j["dmesg"]) or L.overflow_count(j["out"]):
        return False, "REFUTES H-PB: the scene overflowed the PB (need predicted %s of %d usable)" % (L.pred_or(P, name, "pb_used"), M.usable(M.PB_PAGES))
    got, bad = got_of(j), []
    for q in ("rc", "echo", "diff", "tri1", "renders", "tadata_size", "pb_used"):
        want = L.pred_or(P, name, q)
        if want is not None and got[q] != want:
            bad.append("%s %s, frozen %s" % (q, _short(got[q]), want))
    if got["pb_used"] is None:
        return None, "no parameter dump to count pages in"
    r = L.pred_or(P, name, "reg0724")
    note = ""
    if r is not None and got["reg0724"] is not None:
        note = "; reg 0x0724 %s (U4 - 1 reading %s: %s)%s" % (got["reg0724"], r, "equal" if got["reg0724"] == r else "differs", "" if aux else " [not gating: s0's 4x controls did not reproduce it]")
    return (not bad), ("; ".join(bad) if bad else "pages used %s, TA data %s, 0 wrong" % (got["pb_used"], got["tadata_size"])) + note


def p_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    P = PRED["p"]
    cases = L.read_cases(outdir)
    ctls, aux = s0_gate(roots, outdir)
    lines, rows = [], {}
    names = sorted({c for c, _ in P})
    for n in names:
        s, t = p_row(job(outdir, cases, n), P, n, aux)
        rows[n] = s
        lines.append("%s: %s: %s" % (n, {True: "held", False: "FAILED", None: "cannot tell"}[s], t))
    claim = ("H-PB: a 4x full-triangle job uses 1 + ceil(2 tiles16 / 32) parameter-buffer pages and the layout formula's TA data, completing "
             "with 0 wrong pixels, at 6 held-out sizes up to U4 961 (4096 x 960 and 960 x 4096 included: a width or height limit would fail there)")
    q = K.headline(claim, ctls, list(rows.values()))
    return lines, {"verdicts": rows, "hpb": q, "summary": "p: %s" % q}


# ---- o: overflow at 4x ------------------------------------------------------------------------------------------------------------
def outcome(j):
    """complete | overflow | fault | hang | other, with the fault info."""
    c = j["row"]["class"]
    if c == "fault":
        return "fault", fault_info(j)
    if c == "hang":
        return "hang", None
    if L.overflowed(j["out"], j["dmesg"]) or L.overflow_count(j["out"]):
        return "overflow", None
    if c == "ok" and (L.diff_count(j["out"]) or (None, None))[0] == 0:
        return "complete", None
    return "other", None


def spm4_fault_ok(fi, P, name):
    return (fi is not None and "0x%04x" % fi["int"] == L.pred(P, name, "fault_int") and "0x%05x" % fi["page"] == L.pred(P, name, "fault_page")
            and fi["sb"] == int(L.pred(P, name, "fault_sb")))


def o_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    P = PRED["o"]
    cases = L.read_cases(outdir)
    s0c, _ = s0_gate(roots, outdir)
    lines, obs, fis = [], {}, {}
    names = ["o1-1x-1024x768-p83", "o2-1x-1024x768-p82", "o3-4x-1024x768-pe3", "o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held",
             "o6-4x-288x144-p23-fill7", "o7-4x-4096x1152-p422", "o8-1x-4096x4096-p422"]
    js = {n: job(outdir, cases, n) for n in names}
    ctls = {}
    for n in names[:3]:
        j = js[n]
        want = L.pred(P, n, "outcome")
        if j["void"]:
            ctls[n] = "NODATA"
            lines.append("%s: NODATA: %s" % (n, void_text(j)))
            continue
        oc, fi = outcome(j)
        obs[n], fis[n] = oc, fi
        ok = oc == want
        if ok and want == "complete" and L.pred(P, n, "diff") != L.diff_text(j["out"]):
            ok = False
        ctls[n] = "PASS" if ok else "FAIL"
        lines.append("%s: %s: %s (frozen %s)%s" % (n, ctls[n], oc, want, "" if oc != "fault" or not fi else ", fault word 0x%08x" % fi["word"]))
    # the s0 gate is part of every dependent row
    for k, v in s0c.items():
        ctls["s0:" + k] = v
    rows = {}
    for n in ("o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held", "o7-4x-4096x1152-p422"):
        j = js[n]
        if j["void"]:
            rows[n] = None
            lines.append("%s: cannot tell: %s" % (n, void_text(j)))
            continue
        oc, fi = outcome(j)
        obs[n], fis[n] = oc, fi
        if oc == "fault" and spm4_fault_ok(fi, P, n):
            rows[n] = True
            lines.append("%s: held: faulted with BIF_INT_STAT bits 15:0 0x%04x, BIF_FAULT 0x%08x (page 0x%x, SB %d, CID %d): E828 j4's word" % (n, fi["int"], fi["word"], fi["page"], fi["sb"], fi["cid"]))
        elif oc == "fault":
            rows[n] = False
            lines.append("%s: FAILED: faulted, but with int 0x%04x word 0x%08x (page 0x%x, SB %d), not E828 j4's word" % (n, fi["int"] if fi else 0, fi["word"] if fi else 0, fi["page"] if fi else 0, fi["sb"] if fi else 0))
        else:
            rows[n] = False
            lines.append("%s: FAILED: %s, no fault (the refuting reading: %s)" % (n, oc, "-ENOSPC like 1x" if oc == "overflow" else "the page rule is off at 4x" if oc == "complete" else "see the output"))
    j = js["o6-4x-288x144-p23-fill7"]
    if j["void"]:
        lines.append("o6-4x-288x144-p23-fill7: not run (%s)" % "; ".join(j["void"]))
        o6 = "not run"
    else:
        oc, fi = outcome(j)
        if oc == "fault" and fi:
            o6 = "the fault page %s 0x10000 (page 0x%x, word 0x%08x)" % ("stays" if fi["page"] == 0x10000 else "leaves", fi["page"], fi["word"])
        else:
            o6 = "no fault (%s)" % oc
        lines.append("o6-4x-288x144-p23-fill7: exploratory, frozen either/or: %s" % o6)
    j = js["o8-1x-4096x4096-p422"]
    if j["void"]:
        rows["o8-1x-4096x4096-p422"] = None
        lines.append("o8-1x-4096x4096-p422: cannot tell: %s" % void_text(j))
    else:
        oc, fi = outcome(j)
        obs["o8-1x-4096x4096-p422"] = oc
        rows["o8-1x-4096x4096-p422"] = oc == "overflow"
        lines.append("o8-1x-4096x4096-p422: %s: %s%s" % ("held" if oc == "overflow" else "FAILED", oc,
                     "" if oc == "overflow" else (" (j4 is not about 4x: the same triangle at 1x faults)" if oc == "fault" else " (the 1x need model is off)")))
    claim = ("H-SPM4: a 4x scene that overflows the PB faults on the 3D side with E828 j4's word (o4, o5, o7), where the same overflow at 1x ends "
             "in -ENOSPC without a fault (o2, o8); the page rule holds at 1x and 4x (o1, o3)")
    q = K.headline(claim, ctls, list(rows.values()))
    # Q292's narrowed form, by cases
    fault3 = [rows.get(n) for n in ("o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held", "o7-4x-4096x1152-p422")]
    gate_ok = K.gate(ctls).ok
    if not gate_ok:
        q292 = "cannot tell: controls: " + "; ".join(K.gate(ctls).problems)
    elif all(r is True for r in fault3) and rows.get("o8-1x-4096x4096-p422") is True:
        q292 = ("an overflowing 4x scene faults (o4, o5, o7: BIF_INT_STAT 0x90100, page 0x10000, SB 1) and the same triangle at 1x does not "
                "(o2, o8): j4's fault is the overflow at 4x; the fork has no partial renders [infer]; the rest is a kernel question, no "
                "kernel work now (decision 7a)")
    elif obs.get("o4-4x-1024x768-pe2") == "overflow" and obs.get("o5-4x-288x144-p23-held") == "overflow":
        q292 = "an overflow at 4x ends in -ENOSPC like 1x (o4, o5): j4's fault is about the size, not the overflow; o7 and o8 say which side"
    else:
        q292 = "mixed: o4 %s, o5 %s, o7 %s, o8 %s" % (obs.get("o4-4x-1024x768-pe2"), obs.get("o5-4x-288x144-p23-held"),
                                                       obs.get("o7-4x-4096x1152-p422"), obs.get("o8-1x-4096x4096-p422"))
    return lines, {"verdicts": rows, "controls": ctls, "hspm4": q, "q292": q292, "o6": o6, "summary": "o: %s; Q292: %s" % (q, q292)}


# ---- t: Q293 ----------------------------------------------------------------------------------------------------------------------
def insertion(base, new, n=64):
    """(pos, value) if new[:n] is base[:n-1] with ONE dword inserted at pos; None otherwise.  The first position that fits (an inserted zero
    next to a zero dword of the baseline fits at the first of them; the rows' baselines have a non-zero dword before the format word)."""
    if base is None or new is None or len(base) < n or len(new) < n:
        return None
    if new[:n] == base[:n]:         # equal heads: no insertion (a zero inserted into a run of zeros would otherwise "fit" at its end)
        return None
    for p in range(n - 1):
        if new[:p] == base[:p] and new[p + 1:n] == base[p:n - 1]:
            return p, new[p]
    return None


def t_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    P = PRED["t"]
    cases = L.read_cases(outdir)
    s0c, _ = s0_gate(roots, outdir)
    lines, ctls, rows = [], {}, {}
    js = {n: job(outdir, cases, n) for n in ("t1-aa4-te40", "t2-aa4-te80", "t3b-line-base", "t3-line-te40", "t4b-point-base", "t4-point-te40", "t6-ctl-te40-1array")}
    for n in ("t6-ctl-te40-1array", "t3b-line-base", "t4b-point-base"):
        v, t = ctl(js[n], P, n)
        ctls[n] = v
        lines.append("%s: %s: %s" % (n, v, t))
    for k, v in s0c.items():
        ctls["s0:" + k] = v
    for n in ("t1-aa4-te40", "t2-aa4-te80"):
        j = js[n]
        if j["void"]:
            rows[n] = None
            lines.append("%s: cannot tell: %s" % (n, void_text(j)))
            continue
        w = L.dwords(j["param"]) if j["param"] else None
        t1 = L.tri_counts_text(j["out"])
        if w is None or t1 is None or j["row"]["class"] != "ok":
            rows[n] = None
            lines.append("%s: cannot tell: no parameter dump or no render line (class %s)" % (n, j["row"]["class"]))
            continue
        d11, d12 = "0x%08x" % w[11], "0x%08x" % w[12]
        same = d11 == L.pred(P, n, "dword11") and d12 == L.pred(P, n, "dword12") and t1 == L.pred(P, n, "tri1")
        rows[n] = same
        why = "dword 11 %s, dword 12 %s, image: %s" % (d11, d12, t1)
        if not same:
            why += " (frozen: 0x00000000, 0x00040101, %s)" % L.pred(P, n, "tri1")
            if d11 == "0x00000000" and d12 == "0x00040101" and t1 != L.pred(P, n, "tri1"):
                why += ": the displaced layout is as E728's but the 3D drew (H-4X-READS)"
        lines.append("%s: %s: %s" % (n, "H-SAME held" if same else "H-SAME FAILED", why))
    pad = {}
    for nb, nt in (("t3b-line-base", "t3-line-te40"), ("t4b-point-base", "t4-point-te40")):
        j, jb = js[nt], js[nb]
        if j["void"]:
            rows[nt] = None
            lines.append("%s: cannot tell: %s" % (nt, void_text(j)))
            continue
        ins = insertion(L.dwords(jb["param"]) if jb.get("param") else None, L.dwords(j["param"]) if j["param"] else None)
        if ins is None:
            rows[nt] = None
            lines.append("%s: cannot tell: the dump is not the baseline's with one dword inserted (no single insertion in dwords 0-63)" % nt)
            continue
        pos, val = ins
        pad[nt] = (pos, val)
        okpos = pos == int(L.pred(P, nt, "insert_pos"))
        if okpos and "0x%08x" % val == L.pred(P, nt, "insert_val"):
            rows[nt] = True
            lines.append("%s: H-PAD held: one dword inserted at %d (before the format word) and it is 0x00000000" % (nt, pos))
        elif okpos:
            rows[nt] = False
            lines.append("%s: H-FIELD: one dword inserted at %d (before the format word) and it is 0x%08x, not zero" % (nt, pos, val))
        else:
            rows[nt] = False
            lines.append("%s: H-PAD FAILED: one dword inserted at %d (frozen %s) with value 0x%08x" % (nt, pos, L.pred(P, nt, "insert_pos"), val))
    claim = ("Q293: the dword CR_TE_AA bits 31:30 insert is zero in 4 of 4 jobs (a triangle on a four-array context at 0x40 and 0x80, a line and "
             "a point object at 0x40) and sits before the object's format word: padding, not a field; a four-array context reads the displaced "
             "layout as a one-array one does [infer]; two objects in one render: one inserted dword each, already in E825/E829 (pb-n40)")
    q = K.headline(claim, ctls, [rows.get(n) for n in ("t1-aa4-te40", "t2-aa4-te80", "t3-line-te40", "t4-point-te40")])
    field = [n for n in ("t3-line-te40", "t4-point-te40") if n in pad and rows.get(n) is False and pad[n][1] != 0]
    if field and K.gate(ctls).ok:
        q = "H-FIELD: the inserted dword is non-zero in %s (%s): a field of the object, not padding [infer]" % (
            ", ".join(field), ", ".join("0x%08x" % pad[n][1] for n in field))
    return lines, {"verdicts": rows, "controls": ctls, "q293": q, "summary": "t: %s" % q}


# ---- h: Q140, the health replay ---------------------------------------------------------------------------------------------------
def step_fault(cases, outdir, name, step):
    """(class, fault word or None, kernel-log slice) of one step of a cell; class None if the step has no row."""
    row = (cases or {}).get("%s.%s" % (name, step))
    if row is None:
        return None, None, ""
    d = L.read_text(os.path.join(outdir, "%s.%s.dmesg.gz" % (name, step))) or ""
    o = L.read_text(os.path.join(outdir, "%s.%s.txt.gz" % (name, step))) or ""
    fl = L.bif_faults(d) or L.bif_faults(o)
    return row["class"], (fl[0][1] if fl else None), d


def minus110(slice_):
    """(requestor bit 2 set, SB, a PARAMETERS page, CID) of the register dump before an 'SGX recovery failed: -110' line, or None."""
    if "recovery failed: -110" not in (slice_ or ""):
        return None
    m = re.findall(r"reg 0xc04 = 0x([0-9a-f]+)\n.*?reg 0xc08 = 0x([0-9a-f]+)", slice_, re.S)
    if not m:
        return ("-110, no register dump",)
    stat, word = int(m[-1][0], 16), int(m[-1][1], 16)
    pg, sb, cid = L.decode_fault(word)
    return (bool(stat & 4), sb, (word >> 28) == 1, cid, word)


def h_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    P = PRED["h"]
    cases = L.read_cases(outdir)
    s0c, _ = s0_gate(roots, outdir)
    ctls = dict(("s0:" + k, v) for k, v in s0c.items())
    lines, rows, info = [], {}, {}
    for n in sorted({c for c, _ in P}):
        j = job(outdir, cases, n)
        if j["void"]:
            rows[n] = None
            lines.append("%s: cannot tell: %s" % (n, void_text(j)))
            continue
        fi = fault_info(j)
        want = int(L.pred(P, n, "job_word"), 16)
        if j["row"]["class"] != "fault" or fi is None:
            rows[n] = None
            lines.append("%s: cannot tell: the job did not fault (class %s): nothing to replay" % (n, j["row"]["class"]))
            continue
        jw = fi["word"]
        head = "job faulted: BIF_INT_STAT bits 15:0 0x%04x, BIF_FAULT 0x%08x (frozen 0x%08x: %s)" % (fi["int"], jw, want, "as predicted" if jw == want else "DIFFERENT")
        if jw >> 12 != want >> 12:
            head += " [the fault page is not the one frozen]"
        steps, lns = {}, []
        for st in ("ctx", "fill", "h1", "h2", "h3", "h4"):
            r = step_fault(cases, outdir, n, st)
            if r[0] is not None:
                steps[st] = r
                clk = L.reg(j["regs"].get(st), 0x0008)
                lns.append("%s %s%s clkgate %s" % (st, r[0], "" if r[1] is None else " at 0x%08x" % r[1], clk))
        fails = [(st, steps[st][1]) for st in ("h1", "h2", "h3", "h4") if st in steps and steps[st][0] != "ok"]
        ok_steps = [st for st in ("h1", "h2", "h3", "h4") if st in steps and steps[st][0] == "ok"]
        replays = len(fails)
        for st in steps:
            m = minus110(steps[st][2])
            if m:
                lns.append("%s: -110 shape %s" % (st, m))
        kind = n.split("-")[-1]
        ownend = [st for st, w in fails if w is not None and (w >> 12) == 0x20006 and (jw >> 12) != 0x20006]
        if kind == "health":
            if not fails:
                state, why = None, "no health triangle failed: the replay was not seen (0 replays; K2 had 2, the rgn4 boot 1)"
            elif ownend:
                state, why = False, "REFUTES the replay: %s faulted at 0x20006, the health context's own end" % ",".join(ownend)
            elif all(w == jw for _, w in fails):
                state, why = True, "every failing health triangle reads the job's own word 0x%08x (%d of %d)%s" % (jw, replays, replays, "; page unseen before" if n.startswith("h2") else "")
            else:
                state, why = False, "a failing health triangle reads another word: %s" % ", ".join("%s 0x%08x" % (st, w or 0) for st, w in fails)
        elif kind == "ctx":
            c = steps.get("ctx", (None,))[0]
            state = None if c is None else (c == "ok")
            why = "the 64 x 64 triangle on a context for 1024 x 768: %s" % c
        else:
            c = steps.get("fill", (None,))[0]
            if c != "ok":
                state, why = None, "the fill itself did not pass (%s)" % c
            elif "h1" in steps and steps["h1"][0] != "ok" and steps["h1"][1] == jw:
                state, why = True, "the fill passed and the first health triangle still faulted at 0x%08x" % jw
            elif "h1" in steps and steps["h1"][0] == "ok":
                state, why = False, "the fill passed and the first health triangle passed too: the replay did not wait for the TA"
            else:
                state, why = False, "the fill passed; the first health triangle faulted at another word"
        stopped = "h4" in steps and steps["h4"][0] != "ok"
        rows[n] = state
        info[n] = {"replays": replays, "ok_steps": ok_steps}
        lines.append("%s: %s: %s; %s; steps: %s%s" % (n, {True: "held", False: "FAILED", None: "cannot tell"}[state], head, why, "; ".join(lns),
                     "; the fourth health triangle failed: the stage stopped (rc 17)" if stopped else ""))
    claim = ("H-REPLAY: after a TA write fault the pending region-header write is issued again when the TA next runs: every failing health "
             "triangle names the failed job's own BIF_FAULT word (also at page 0x2000a, never seen in a health fault), a context that maps the "
             "page and a fill do not fault")
    q = K.headline(claim, ctls, list(rows.values()))
    return lines, {"verdicts": rows, "controls": ctls, "q140": q, "info": info, "summary": "h: %s" % q}


STAGES = {"s0": s0_stage, "c": c_stage, "p": p_stage, "o": o_stage, "t": t_stage, "h": h_stage}


def verdict(roots):
    out = []
    names = [("s0", "session"), ("c", "q113"), ("p", "hpb"), ("o", "q292"), ("t", "q293"), ("h", "q140")]
    for st, key in names:
        d = stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (key, st))
            continue
        fn = STAGES[st]
        _, r = fn(d) if st == "s0" else fn(d, roots)
        if st == "s0":
            out.append("SUMMARY: session: %s" % r["summary"])
        elif st == "o":
            out.append("SUMMARY: Q292 (o): %s" % r["q292"])
            out.append("SUMMARY: H-SPM4 (o): %s" % r["hspm4"])
        elif st == "p":
            out.append("SUMMARY: H-PB (p): %s" % r["hpb"])
        else:
            out.append("SUMMARY: %s (%s): %s" % (key.upper(), st, r[key]))
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
    if st not in STAGES:
        print("unknown stage %s" % st)
        return 2
    lines, r = STAGES[st](outdir) if st == "s0" else STAGES[st](outdir, None)
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
