#!/usr/bin/env python3
"""r5-render4x scorer, written and frozen before the run.  Each command prints its rows and ends with SUMMARY lines.

  score_r.py STAGE OUTDIR          one stage: s0 t o m l x d.  s0 (and m, for x) are read where OUTDIR/../gate-STAGE.txt says ("s0 at
                                   DIR", "m at DIR": the driver writes the gate file); without one, from OUTDIR's parent
  score_r.py gate STAGE ROOT...    exit 0 if the stage may run: s0's three controls passed (every stage but s0); for x also stage m
                                   held H-TPC.  Prints where s0 (and m) were found: "s0 at DIR" (round 4 scored o and t with s0 NODATA
                                   because s0 sat in the first attempt)
  score_r.py verdict ROOT...       the session: Q293 (t), H-ENOSPC4 (o), H-TPC and the onset rules of Q292 (m, l, x), the held row (d)
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

Hypotheses (frozen with their predictions in predictions/*.tsv; [infer] where the name is ours):
  H-PAD / H-SAME  t: the dword CR_TE_AA bits 31:30 insert is zero and sits right before the object's format word, at 0x80 as at 0x40
           (t3c, t4c held out; t1 to t4 replicate E847).  H-FIELD: it is non-zero.
  H-ENOSPC4 o: a 4x scene that overflows the PB ends in -ENOSPC with no BIF line, as at 1x (E846 post hoc); held out on 640 x 480 and
           512 x 384, one page each side of the need of their kept twins.  The page rule on the default triangle (o1, o2) is the control.
  H-TPC   m, l, x: at 4x the tail-pointer extent of the doubled grid runs over the region headers of the CONTEXT's layout; four variants
           (TPC-d-rgn, TPC-d-state, TPC-rs-rgn, TPC-rb-rgn) against seven size rules (K-W, K-H, K-OR, K-AND, K-TPM, K-P, K-AREA); every
           rule's prediction is computed from the row's argv (gen/rules.py).  A threshold rule is a family and survives while some
           threshold fits.

The verdict rules are scorekit's (score/scorekit.py, byte for byte resgx545 tools/closing/scorekit.py).  The dumps of a row are found by
its verb (gen/rlib.py dump_stem): a row that asked for a dump, completed and has none is a READER-MISS (an error of the reader, never
NODATA).  Refuses to score unless run/freeze_k.sh verify passes.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import scorekit as K  # noqa: E402

PRED = {}
STAGE_NAMES = ("s0", "t", "o", "m", "l", "x", "d")
S0_CTL = ("s0-1x-1024x768", "s0-4x-288x144", "s0-4x-1024x768")
PARAM_DUMP_BYTES = 0x464 * 4096          # a render_param dump (whatever P was)
FAULT_INT, FAULT_PAGE = 0x0100, 0x10000


def preds():
    for st in STAGE_NAMES:
        PRED[st] = L.load_predictions(st + ".tsv")


# ---- one job's kept files -------------------------------------------------------------------------------------------------------
def job(outdir, cases, name):
    """Everything kept for one job, its dumps found by the verb of the argv that RAN (cases.tsv's args); j['void'] lists what makes it
    no data; j['miss'] is set when the row asked for a dump, completed, and the dump is not there (a READER-MISS)."""
    j = {"name": name, "void": [], "miss": None, "param": None, "tadata": None}
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
    dn = L.dump_names(name, row.get("args") or "")
    if dn:
        j["param"] = L.read_bytes(os.path.join(outdir, dn[0]))
        j["tadata"] = L.read_bytes(os.path.join(outdir, dn[1]))
        if row.get("class") == "ok" and (j["param"] is None or j["tadata"] is None):
            j["miss"] = "READER-MISS: the row asked for a dump (%s) and none was found" % dn[0]
    j["heldparam"] = L.read_bytes(p(".heldparam.bin.gz"))
    j["heldtadata"] = L.read_bytes(p(".heldtadata.bin.gz"))
    j["regs"] = {k: L.read_text(p(".snap%s.regs.gz" % k)) for k in ("0", "1", "2", "3", "9")}
    return j


def stage_dir(roots, stage):
    for r in roots:
        if os.path.exists(os.path.join(r, stage, "cases.tsv")):
            return os.path.join(r, stage)
    return os.path.join(roots[0], stage) if roots else stage


def where(outdir, stage, need):
    """The kept directory of stage `need` (s0 or m) for scoring `stage` in OUTDIR: the gate file's line, else OUTDIR's parent."""
    att = os.path.dirname(os.path.abspath(outdir))
    g = os.path.join(att, "gate-%s.txt" % stage)
    if os.path.exists(g):
        m = re.search(r"^%s at (\S+)$" % need, open(g).read(), re.M)
        if m and os.path.exists(os.path.join(m.group(1), "cases.tsv")):
            return m.group(1)
    return os.path.join(att, need)


def got_of(j):
    o = j["out"]
    pb = j["param"]
    return {"rc": str(j.get("rc")), "echo": L.echo(o), "target_hash": L.target_hash(o), "diff": L.diff_text(o),
            "tri1": L.tri_counts_text(o), "renders": L.renders(o),
            "tadata_size": None if j["tadata"] is None else "%d" % len(j["tadata"]),
            "pb_used": None if pb is None or len(pb) != PARAM_DUMP_BYTES else "%d" % M.pages_nonzero(pb),
            "par_0_64": L.words(pb, 0, 64), "par_0_32": L.words(pb, 0, 32), "o0": _o0(o)}


def _o0(text):
    m = re.search(r"o0 (mixed .*|[^\n]*)$", text or "", re.M)
    return m.group(1).strip() if m else None


def fault_info(j):
    """The job's fault: {'int': bits 15:0 of BIF_INT_STAT, 'word', 'page', 'sb', 'cid', 'src'} or None.  The kernel's job fault line
    first (plain jobs), else the held snap 1 registers (a held job)."""
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


def ctl(j, P, name):
    """A control against its frozen quantities (set ctl): ("PASS" | "FAILED" | "NODATA", text).  A READER-MISS is reported as such."""
    if j["void"]:
        return "NODATA", void_text(j)
    if j["miss"]:
        return "NODATA", j["miss"]
    if j["row"]["class"] != "ok":
        return "FAILED", "class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    got, bad, missing = got_of(j), [], []
    for (case, q), vals in sorted(P.items()):
        if case != name or vals[0][2] != "ctl" or q not in got:
            continue
        want = vals[0][0]
        if got[q] is None:
            missing.append(q)
        elif got[q] != want:
            bad.append("%s %s, frozen %s" % (q, _short(got[q]), _short(want)))
    if missing and not bad:
        return "NODATA", "NODATA (nothing read for %s)" % ", ".join(missing)
    return ("FAILED" if bad else "PASS"), ("; ".join(bad) if bad else "as frozen (hash %s, diff %s)" % (got["target_hash"], got["diff"]))


def _short(v):
    return "none" if v is None else (v if len(str(v)) < 60 else str(v)[:56] + "...")


# ---- s0 ---------------------------------------------------------------------------------------------------------------------------
def s0_stage(outdir):
    P = PRED["s0"]
    cases = L.read_cases(outdir)
    res, lines = {}, []
    for n in S0_CTL:
        j = job(outdir, cases, n)
        v, t = ctl(j, P, n)
        res[n] = v
        lines.append("%s: %s: %s" % (n, v, t))
    g = K.gate(res)
    s = "s0: controls %s; later stages %s" % (res, "open" if g.ok else "CLOSED (the session is void)")
    return lines, {"verdicts": res, "gate": g, "summary": s, "dir": outdir}


def s0_controls(sdir):
    if sdir and os.path.exists(os.path.join(sdir, "cases.tsv")):
        return dict(("s0:" + k, v) for k, v in s0_stage(sdir)[1]["verdicts"].items())
    return dict(("s0:" + n, "NODATA") for n in S0_CTL)


def gate(stage, roots):
    if stage == "s0":
        return 0, "gate s0: no prerequisite"
    d = stage_dir(roots, "s0")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate %s: closed: no s0 stage was kept (run: run/k.sh --only s0)" % stage
    _, r = s0_stage(d)
    if not r["gate"].ok:
        return 1, "gate %s: closed: s0 controls %s (the session is void: the lead decides)\ns0 at %s" % (stage, "; ".join(r["gate"].problems), d)
    msg = "gate %s: open (s0's three controls passed)\ns0 at %s" % (stage, d)
    if stage == "x":
        dm = stage_dir(roots, "m")
        if not os.path.exists(os.path.join(dm, "cases.tsv")):
            return 1, "gate x: closed: no stage m was kept (x runs only if m held H-TPC)\ns0 at %s" % d
        _, rm = rule_stage("m", dm, d)
        if rm["htpc"] is not True:
            return 1, "gate x: closed: stage m did not hold H-TPC (%s): x runs only if it did\ns0 at %s\nm at %s" % (rm["htpc_text"], d, dm)
        msg = "gate x: open (s0's three controls passed; stage m held H-TPC)\ns0 at %s\nm at %s" % (d, dm)
    return 0, msg


# ---- outcomes -----------------------------------------------------------------------------------------------------------------------
def outcome(j):
    """complete | overflow | fault (with the info) | hang | other."""
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


# ---- t: Q293 ----------------------------------------------------------------------------------------------------------------------
def insertion(base, new, n=64):
    """(pos, value) if new[:n] is base[:n-1] with ONE dword inserted at pos.  Refuses (raises) when a side is missing: round 4's
    insertion() printed "no single insertion" on no data."""
    if base is None or new is None:
        raise ValueError("insertion(): a side is missing (base %s, new %s): no reading" % ("none" if base is None else "read", "none" if new is None else "read"))
    if len(base) < n or len(new) < n or new[:n] == base[:n]:
        return None
    for p in range(n - 1):
        if new[:p] == base[:p] and new[p + 1:n] == base[p:n - 1]:
            return p, new[p]
    return None


T_ROWS = ("t1-aa4-te40", "t2-aa4-te80", "t3-line-te40", "t4-point-te40", "t3c-line-te80", "t4c-point-te80")
T_BASE = {"t3-line-te40": "t3b-line-base", "t3c-line-te80": "t3b-line-base", "t4-point-te40": "t4b-point-base", "t4c-point-te80": "t4b-point-base"}


def t_row(n, j, jb, P):
    """(state, text) of one t row; j its job, jb its baseline's job (None for t1, t2)."""
    if j["void"]:
        return None, "cannot tell: " + void_text(j)
    if j["miss"]:
        return None, j["miss"]
    if j["row"]["class"] != "ok":
        return None, "cannot tell: class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    if n in ("t1-aa4-te40", "t2-aa4-te80"):
        w = L.dwords(j["param"])
        t1 = L.tri_counts_text(j["out"])
        d11, d12 = "0x%08x" % w[11], "0x%08x" % w[12]
        same = d11 == L.pred(P, n, "dword11") and d12 == L.pred(P, n, "dword12") and t1 == L.pred(P, n, "tri1")
        return same, "%s: dword 11 %s, dword 12 %s, image: %s%s" % ("H-SAME held" if same else "H-SAME FAILED", d11, d12, t1,
                                                                      "" if same else " (frozen 0x00000000, 0x00040101, %s)" % L.pred(P, n, "tri1"))
    if jb is None or jb["void"] or jb["miss"] or jb.get("param") is None:
        return None, "cannot tell: the baseline %s has no reading (%s)" % (T_BASE[n], (jb or {}).get("miss") or ("; ".join((jb or {}).get("void") or ["no dump"])))
    ins = insertion(L.dwords(jb["param"]), L.dwords(j["param"]))
    if ins is None:
        return False, "read, and matched no hypothesis: the dump is not the baseline's with one dword inserted (dwords 0-63)"
    pos, val = ins
    okpos = pos == int(L.pred(P, n, "insert_pos"))
    if okpos and "0x%08x" % val == L.pred(P, n, "insert_val"):
        return True, "H-PAD held: one dword inserted at %d (before the format word) and it is 0x00000000" % pos
    if okpos:
        return False, "H-FIELD: one dword inserted at %d (before the format word) and it is 0x%08x, not zero" % (pos, val)
    return False, "H-PAD FAILED: one dword inserted at %d (frozen %s) with value 0x%08x" % (pos, L.pred(P, n, "insert_pos"), val)


def t_stage(outdir, s0dir=None):
    P = PRED["t"]
    cases = L.read_cases(outdir)
    s0dir = s0dir or where(outdir, "t", "s0")
    lines, ctls, rows, misses, texts = [], {}, {}, [], {}
    names = ("t6-ctl-te40-1array", "t3b-line-base", "t4b-point-base") + T_ROWS
    js = {n: job(outdir, cases, n) for n in names}
    for n in ("t6-ctl-te40-1array", "t3b-line-base", "t4b-point-base"):
        v, t = ctl(js[n], P, n)
        ctls[n] = v
        if js[n]["miss"]:
            misses.append(n)
        lines.append("%s: %s: %s" % (n, v, t))
    ctls.update(s0_controls(s0dir))
    for n in T_ROWS:
        s, t = t_row(n, js[n], js.get(T_BASE.get(n)), P)
        texts[n] = t
        if js[n]["miss"]:
            misses.append(n)
        rows[n] = s
        sset = "held out" if n in ("t3c-line-te80", "t4c-point-te80") else "replicate of E847"
        lines.append("%s (%s): %s" % (n, sset, t))
    claim = ("Q293: the dword CR_TE_AA bits 31:30 insert is zero and sits right before the object's format word: at 0x80 on a line and a "
             "point (held out), at 0x40 and on a four-array context as E847 read them; padding, not a field [infer]")
    q = K.headline(claim, ctls, list(rows.values()))
    field = [n for n in T_ROWS if rows.get(n) is False and texts[n].startswith("H-FIELD")]
    if field and K.gate(ctls).ok:
        q = "H-FIELD: the inserted dword is non-zero in %s: a field of the object, not padding [infer]" % ", ".join(field)
    if misses:
        q = "READER-MISS in %s: the scorer could not find dumps the rows wrote; %s" % (", ".join(misses), q)
    return lines, {"verdicts": rows, "controls": ctls, "q293": q, "misses": misses, "summary": "t: %s" % q}


# ---- o: overflow at 4x ------------------------------------------------------------------------------------------------------------
O_CTL = ("o1-1x-1024x768-p35", "o2-1x-1024x768-p34", "o3-4x-1024x768-pe3")
O_REP = ("o4-4x-1024x768-pe2", "o5-4x-288x144-p23")
O_HELD = ("o6-4x-640x480-p6e", "o7-4x-640x480-p6d", "o8-4x-512x384-p53", "o9-4x-512x384-p52")
O_EXP = ("o10-1xf-1024x768-p53", "o11-1xf-1024x768-p52")


def o_row(case, j, P):
    """(outcome, state, text) of job j scored as r5's case (j may come from another session's directory: the replay)."""
    if j["void"]:
        return None, None, void_text(j)
    oc, fi = outcome(j)
    want = L.pred(P, case, "outcome")
    note = ""
    if oc == "complete":
        g = got_of(j)
        if j["miss"]:
            return oc, None, j["miss"]
        note = "; scene pages %s (frozen need %s)" % (g["pb_used"], L.pred(P, case, "need"))
        want_diff = L.pred_or(P, case, "diff", "0 of %d pixels" % (lambda d: d[0] * d[1])(dims(j["row"]["args"])))
        if g["diff"] != want_diff:
            return oc, False, "completed but %s (0 wrong frozen: %s)" % (g["diff"], want_diff)
    if oc == "fault":
        note = "; BIF_INT_STAT bits 15:0 0x%04x, BIF_FAULT 0x%08x" % (fi["int"], fi["word"]) if fi else "; no fault word read"
    if oc == want:
        return oc, True, "%s as frozen%s" % (oc, note)
    return oc, False, "%s, frozen %s%s" % (oc, want, note)


def o_stage(outdir, s0dir=None):
    P = PRED["o"]
    cases = L.read_cases(outdir)
    s0dir = s0dir or where(outdir, "o", "s0")
    lines, ctls, rows, obs = [], {}, {}, {}
    for n in O_CTL:
        oc, s, t = o_row(n, job(outdir, cases, n), P)
        ctls[n] = "NODATA" if s is None else ("PASS" if s else "FAILED")
        obs[n] = oc
        lines.append("%s (control): %s: %s" % (n, ctls[n], t))
    ctls.update(s0_controls(s0dir))
    for n in O_REP + O_HELD:
        oc, s, t = o_row(n, job(outdir, cases, n), P)
        rows[n] = s
        obs[n] = oc
        lines.append("%s (%s): %s: %s" % (n, "replicate of E846" if n in O_REP else "held out", {True: "held", False: "FAILED", None: "cannot tell"}[s], t))
    exp = []
    for n in O_EXP:
        oc, s, t = o_row(n, job(outdir, cases, n), P)
        obs[n] = oc
        exp.append("%s %s" % (n, oc))
        lines.append("%s (explore, need 49 [model]): %s" % (n, t))
    claim = ("H-ENOSPC4: a 4x scene that overflows the PB ends in -ENOSPC with no BIF line, as at 1x, one page short of its kept twin's "
             "need (o7 640 x 480, o9 512 x 384), and completes with 0 wrong at the need (o6, o8); o4, o5 replicate E846")
    q = K.headline(claim, ctls, [rows[n] for n in O_REP + O_HELD])
    if any(obs.get(n) == "fault" for n in O_REP + O_HELD):
        q += "; REFUTED by a fault in %s" % ", ".join(n for n in O_REP + O_HELD if obs.get(n) == "fault")
    e = "the 1x full pair: %s" % ", ".join(exp)
    if obs.get(O_EXP[0]) == "complete" and obs.get(O_EXP[1]) == "overflow":
        e += " (the need is 49: E846's sentence 'the frozen need 97 is the model of the full triangle' needs an appended correction)"
    return lines, {"verdicts": rows, "controls": ctls, "henospc4": q, "explore": e, "obs": obs, "summary": "o: %s; %s" % (q, e)}


# ---- m, l, x: H-TPC and the size rules --------------------------------------------------------------------------------------------
def dims(args):
    m = re.search(r"--width (\d+) --height (\d+)", args)
    mm = re.search(r"--max-width (\d+) --max-height (\d+)", args)
    w, h = int(m.group(1)), int(m.group(2))
    return (w, h) + ((int(mm.group(1)), int(mm.group(2))) if mm else (w, h))


def rule_obs(j):
    """(observation, text): 'complete' | 'fault' (E845's 3D-side word) decide; anything else does not."""
    if j["void"]:
        return None, void_text(j)
    oc, fi = outcome(j)
    if oc == "fault":
        if fi and fi["int"] == FAULT_INT and fi["page"] == FAULT_PAGE:
            return "fault", "fault, BIF_INT_STAT bits 15:0 0x%04x, BIF_FAULT 0x%08x (page 0x%x: the request base)" % (fi["int"], fi["word"], fi["page"])
        return None, "a fault of another kind (%s): no rule predicts it, it decides nothing (a stop of the stage)" % (
            "int 0x%04x word 0x%08x" % (fi["int"], fi["word"]) if fi else "no fault word read")
    if oc == "complete":
        return "complete", "complete, 0 wrong"
    return None, "%s: no rule predicts it, it decides nothing" % oc


def aux(j, P, n):
    """The frozen side quantities of a completed row: scene pages, TA-data size, headers off the rule (reported, never a rule's verdict)."""
    if j["miss"]:
        return j["miss"]
    g = got_of(j)
    w, h, mw, mh = dims(j["row"]["args"])
    hd = L.headers(j["tadata"], w, h, mw, mh)
    got = {"pb_used": g["pb_used"], "tadata_size": g["tadata_size"], "hdr_off": None if hd is None else str(len(hd["off"]))}
    out = []
    for q in ("pb_used", "tadata_size", "hdr_off"):
        want = L.pred_or(P, n, q)
        out.append("%s %s%s" % (q, got[q], "" if got[q] == want else " (frozen %s: DIFFERS)" % want))
    return "; ".join(out)


RULE_ROWS = {"m": ("m0-1024x768-max2048x2048", "m1-1280x1024-max1280x1040", "m2-1280x1024-max2048x2048", "m3-1280x1024-max2048x1024",
                   "m4-2048x1536-max4096x4096"),
             "l": ("l1-2048x240", "l2-256x1536", "l3-768x2048", "l4-1280x768", "l5-1024x1024"),
             "x": ("x1-1024x512", "x2-1184x768", "x3-1024x800")}


def rule_stage(stage, outdir, s0dir=None):
    """One of m, l, x: every row's observation against every rule; the survivors; for m the H-TPC headline."""
    P = PRED[stage]
    cases = L.read_cases(outdir)
    s0dir = s0dir or where(outdir, stage, "s0")
    ctls = s0_controls(s0dir)
    lines, observed, states = [], [], {}
    for n in RULE_ROWS[stage]:
        j = job(outdir, cases, n)
        ob, t = rule_obs(j)
        args = j["row"]["args"] if "row" in j else None
        if ob and args:
            observed.append(dims(args) + (ob,))
        want = L.pred(P, n, "htpc")
        rr = [r for r in R.RULES if L.pred(P, n, "rule:" + r) in ("fault", "complete") and ob and L.pred(P, n, "rule:" + r) != ob]
        extra = "; " + aux(j, P, n) if ob == "complete" else ""
        lines.append("%s: %s (H-TPC %s)%s%s" % (n, t, want, extra, "; contradicts " + ", ".join(rr) if rr else ""))
        states[n] = ob
    surv = R.survivors(observed)
    res = {"observed": observed, "survivors": surv, "states": states, "controls": ctls, "htpc": None, "htpc_text": "not scored"}
    if stage == "m":
        m0 = states["m0-1024x768-max2048x2048"]
        ctls["m0-1024x768-max2048x2048"] = {"complete": "PASS", "fault": "FAILED", None: "NODATA"}[m0]
        rows = [None if states[n] is None else states[n] == L.pred(P, n, "htpc") for n in RULE_ROWS["m"][1:]]
        claim = ("H-TPC: the same faulting size completes on a context made for a larger maximum when the tail room grows (m1, m2, m4 "
                 "complete with 0 wrong) and faults when only the region buffer grows (m3); every size rule predicted a fault in m1, m2, m4")
        hl = K.headline(claim, ctls, rows)
        m1, m2 = states["m1-1280x1024-max1280x1040"], states["m2-1280x1024-max2048x2048"]
        if m1 and m2 and m1 != m2:
            hl += "; SPLIT: m1 %s, m2 %s: reported as it is, it decides nothing" % (m1, m2)
        res["htpc"] = K.gate(ctls).ok and all(r is True for r in rows)
        res["htpc_text"] = hl
    res["summary"] = "%s: survivors %s of the %d rules over %d decided rows%s" % (stage, surv or "none", len(R.RULES), len(observed),
                                                                                     "; " + res["htpc_text"] if stage == "m" else "")
    return lines, res


# ---- d: the held fault --------------------------------------------------------------------------------------------------------------
def d_stage(outdir, s0dir=None):
    P = PRED["d"]
    n = "d1-1280x1024-held"
    cases = L.read_cases(outdir)
    j = job(outdir, cases, n)
    lines = []
    if j["void"]:
        lines.append("%s: cannot tell: %s" % (n, void_text(j)))
        return lines, {"replicated": None, "dumps": "cannot tell", "summary": "d: cannot tell (%s)" % "; ".join(j["void"])}
    ob, t = rule_obs(j)
    rep = {"fault": True, "complete": False}.get(ob)
    lines.append("%s: %s (frozen: fault with E845's word, every rule)%s" % (n, t, "" if rep is not False else "; A COMPLETION: it voids stages l and m"))
    hp, ht = j["heldparam"], j["heldtadata"]
    if hp is None or ht is None or len(hp) < 4096 or len(ht) < 4096:
        dumps = "held dump not read (%s bytes, %s bytes): the dump lines cannot tell" % (None if hp is None else len(hp), None if ht is None else len(ht))
    else:
        pages = M.pages_nonzero(hp)
        hd = L.headers(ht, 1280, 1024)
        if hd is None:
            dumps = "held TA data too short for the headers (%d bytes)" % len(ht)
        else:
            off = hd["off"]
            hi = max(off) + 12 if off else None
            h0 = hd["base"] in off
            fits = []
            for v in ("d", "rs", "rb"):
                lim = int(L.pred(P, n, "hdr_zero_below_" + v), 16)
                if off and h0 and hi <= lim and (v == "d" or hi > int(L.pred(P, n, "hdr_zero_below_d"), 16)):
                    fits.append(v)
            dumps = ("scene pages %d (H-TPC: %s); %d of %d headers off the rule%s, header 0 %s; extent fits %s" % (
                pages, L.pred(P, n, "held_pages"), len(off), hd["n"], "" if not off else ", from 0x%x to 0x%x" % (min(off), hi), "off" if h0 else "on",
                ", ".join({"d": "d (TPC-d-rgn or TPC-d-state)", "rs": "rs", "rb": "rb"}[f] for f in fits) if fits else "no variant"))
    lines.append("%s: held dumps: %s" % (n, dumps))
    return lines, {"replicated": rep, "dumps": dumps, "summary": "d: %s; %s" % ({True: "E845's fault replicated", False: "COMPLETED: stages l and m are void", None: "cannot tell"}[rep], dumps)}


STAGES = {"s0": None, "t": t_stage, "o": o_stage, "d": d_stage}


def score_stage(st, outdir):
    if st == "s0":
        return s0_stage(outdir)
    if st in RULE_ROWS:
        return rule_stage(st, outdir)
    return STAGES[st](outdir)


def verdict(roots):
    out = []
    s0d = stage_dir(roots, "s0")
    if not os.path.exists(os.path.join(s0d, "cases.tsv")):
        out.append("SUMMARY: session: not run (no kept stage s0)")
    else:
        out.append("SUMMARY: session: %s" % s0_stage(s0d)[1]["summary"])
    obs_all, notes, voided = [], [], False
    for st in ("t", "o", "m", "l", "x", "d"):
        d = stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (st, st))
            continue
        if st in RULE_ROWS:
            _, r = rule_stage(st, d, s0d)
            obs_all += r["observed"]
            if st == "m":
                out.append("SUMMARY: H-TPC (m): %s" % r["htpc_text"])
            out.append("SUMMARY: rules %s's rows alone leave: %s" % (st, r["survivors"] or "none"))
        elif st == "t":
            out.append("SUMMARY: Q293 (t): %s" % t_stage(d, s0d)[1]["q293"])
        elif st == "o":
            r = o_stage(d, s0d)[1]
            out.append("SUMMARY: H-ENOSPC4 (o): %s" % r["henospc4"])
            out.append("SUMMARY: o explore: %s" % r["explore"])
        elif st == "d":
            r = d_stage(d, s0d)[1]
            voided = r["replicated"] is False
            out.append("SUMMARY: d: %s" % r["summary"][3:])
    if obs_all:
        surv = R.survivors(obs_all)
        g = K.gate(s0_controls(s0d))
        if not g.ok:
            q = "cannot tell: controls: " + "; ".join(g.problems)
        elif voided:
            q = "VOID: row d (E845's own cell) completed: stages l and m cannot name a rule"
        elif not surv:
            q = "no frozen rule survives the %d decided rows: Q292's cause is none of the eleven" % len(obs_all)
        else:
            fam = [r for r in surv if r in R.KTHR]
            q = "the rules no decided row contradicts (%d rows of m, l, x): %s%s" % (len(obs_all), ", ".join(surv),
                 "" if len(fam) < 2 else "; the threshold rules %s are not separated by the session's cells" % ", ".join(fam))
        out.append("SUMMARY: Q292 (m, l, x): %s" % q)
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
    if st not in STAGE_NAMES:
        print("unknown stage %s" % st)
        return 2
    lines, r = score_stage(st, outdir)
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
