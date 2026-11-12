#!/usr/bin/env python3
"""r6-render4x stage A scorer, written and frozen before the run.  Each command prints its rows and ends with SUMMARY lines.

  score_r.py STAGE OUTDIR          one stage: s0 a t.  s0 is read where OUTDIR/../gate-STAGE.txt says ("s0 at DIR": the driver writes the
                                   gate file); without one, from OUTDIR's parent
  score_r.py gate STAGE ROOT...    exit 0 if the stage may run: s0's three controls passed (every stage but s0).  Prints where s0 was
                                   found: "s0 at DIR"
  score_r.py verdict ROOT...       the session: H-TPM (a, with the held sets of h1 and h2) and Q293 (t)
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

Hypotheses (frozen with their predictions in predictions/*.tsv; [infer] where the name is ours):
  H-TPM   a: the tail pointers of a 4x job are one dword a tile of the doubled grid at TA-data offset 4 x Z(x, y), y on the even bits
          (E870, a post hoc fit on E869's one dump); a four-array 4x job faults iff the end of its target's entries passes the td.rgn of
          its context's maximum, and a held fault loses exactly the stream offsets lost() names.  Held out on twelve rows: a1, a8, a9,
          a12, a13 (H-TPM complete, the dead size rules fault), a2, a3, a5, a14 (their neighbours: fault), a4 the premise (complete at the
          limit), h1 and h2 (held faults: the lost set compared as sets).  H-TPM's seven other variants and round 5's eleven dead rules
          are printed as a comparison: the verdict names those no decided row contradicts, never as the claim.
  Q293    t: CR_TE_AA 0xc0000000 inserts one zero dword right before the format word of the 11.31 line (dword 9) and point (dword 11),
          the image empty (t5, t6: H-PAD; H-FIELD would be non-zero); a non-zero value poked into the inserted dword of the 0x40
          triangle draws nothing (t7: the 3D reads it as the format word, E829's H-OLD).  t8 (r5's t6, E827's row) is the control.

The verdict rules are scorekit's (score/scorekit.py, byte for byte resgx545 tools/closing/scorekit.py).  The dumps of a row are found by
its verb (gen/rlib.py dump_stem): a row that asked for a dump, completed and has none is a READER-MISS (an error of the reader, never
NODATA).  A held row's lost offsets are read by header POSITION (rlib.lost_offsets).  Refuses to score unless run/freeze_k.sh verify
passes.  Stage B (the new kernel) has its own scorer, added with its own freeze; this file never reads its stages.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import scorekit as K  # noqa: E402

PRED = {}
STAGE_NAMES = ("s0", "a", "t")
S0_CTL = ("s0-1x-1024x768", "s0-4x-288x144", "s0-4x-1024x768")
PARAM_DUMP_BYTES = 0x464 * 4096          # a render_param dump (whatever P was)
FAULT_INT, FAULT_PAGE = 0x0100, 0x10000
A_CTL = "a4-1024x768-max2048x1024"
A_ROWS = ("a1-1024x1280", "a12-992x1280", "a13-512x1536", "a8-1024x1024-max1024x1280", "a9-1024x800-max1024x1280",
          "a2-1024x1296", "a3-1040x1280", "a5-1024x800-max2048x1024", "a14-1024x1536")
A_REP = {"a1-1024x1280": "a1r-1024x1280"}
H_ROWS = ("h1-1024x800-held", "h2-1280x768-held")
H_TWIN = {"h1-1024x800-held": "a9-1024x800-max1024x1280"}   # the completed twin of h1 on a larger maximum (compared, explore)


def preds():
    for st in STAGE_NAMES + ("h",):
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
    """The kept directory of stage `need` (s0) for scoring `stage` in OUTDIR: the gate file's line, else OUTDIR's parent."""
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
            "par_0_64": L.words(pb, 0, 64), "par_0_32": L.words(pb, 0, 32)}


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
    return 0, "gate %s: open (s0's three controls passed)\ns0 at %s" % (stage, d)


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
    """The frozen side quantities of a completed row: scene pages, TA-data size, headers off the rule, non-zero dwords below td.rgn
    (reported, never H-TPM's verdict)."""
    if j["miss"]:
        return j["miss"]
    g = got_of(j)
    w, h, mw, mh = dims(j["row"]["args"])
    hd = L.headers(j["tadata"], w, h, mw, mh)
    nz = L.nonzero_below(j["tadata"], R.lay(mw, mh)["rgn"])
    got = {"pb_used": g["pb_used"], "tadata_size": g["tadata_size"], "hdr_off": None if hd is None else str(len(hd["off"])),
           "nonzero_below_rgn": None if nz is None else str(nz)}
    out = []
    for q in ("pb_used", "tadata_size", "hdr_off", "nonzero_below_rgn"):
        want = L.pred_or(P, n, q)
        out.append("%s %s%s" % (q, got[q], "" if got[q] == want else " (frozen %s: DIFFERS)" % want))
    return "; ".join(out)


def right_pixels(j):
    """A faulting row's pixels drawn right before the fault (explore, plan 1.4): total - wrong of the tool's diff line, or None."""
    d = L.diff_count(j.get("out"))
    return None if d is None else d[1] - d[0]


# ---- a: H-TPM ---------------------------------------------------------------------------------------------------------------------
def lost_cmp(got, want):
    """('set equal' | 'both B, lost only L, predicted only P', equal?)."""
    g, w = set(got), set(want)
    if g == w:
        return "set equal (%d)" % len(g), True
    return "both %d, lost only %d, predicted only %d" % (len(g & w), len(g - w), len(w - g)), False


def held_row(n, j, P, PH):
    """(observation, state, text) of a held row: the fault with E845's word, then the lost set against the frozen one."""
    ob, t = rule_obs(j)
    if ob != "fault":
        st = False if ob == "complete" else None
        return ob, st, "%s (H-TPM: fault)" % t
    w, h, mw, mh = dims(j["row"]["args"])
    ht = j["heldtadata"]
    want = [int(x, 16) for x in L.pred(PH, n, "lost").split(",")]
    got = L.lost_offsets(ht, w, h, mw, mh)
    if got is None:
        return ob, None, "%s; held TA data not read (%s bytes): the lost set cannot tell" % (t, None if ht is None else len(ht))
    txt, eq = lost_cmp(got, want)
    xs = set(R.lost(w, h, mw, mh, yeven=False))
    extra = []
    if not eq and set(got) == xs:
        extra.append("the lost set is the x-even interleave's (%d)" % len(xs))
    if got:
        extra.append("lost from 0x%x to 0x%x, header 0 %s (frozen %s)" % (min(got), max(got), "lost" if min(got) == R.lay(mw, mh)["rgn"] else "intact",
                                                                       L.pred(PH, n, "header0_lost")))
    return ob, eq, "%s; lost offsets (word 1 zero at an in-target header): %s%s" % (t, txt, "; " + "; ".join(extra) if extra else "")


def held_explore(n, j, a_twin=None):
    """Reported, never scored: the word-0 side of the held dump, the held scene pages, a9 against h1 header by header."""
    w, h, mw, mh = dims(j["row"]["args"])
    ht, hp = j["heldtadata"], j["heldparam"]
    rep = L.word0_report(ht, w, h, mw, mh)
    out = ["word 0: %s" % (rep if rep is not None else "not read")]
    if hp is not None and len(hp) >= 4096:
        out.append("held scene pages %d" % M.pages_nonzero(hp))
    if a_twin is not None and a_twin.get("tadata") is not None and rep is not None:
        tw, th, tmw, tmh = dims(a_twin["row"]["args"])
        pa = L.header_positions(w, h, mw, mh)
        pb = L.header_positions(tw, th, tmw, tmh)
        d0 = d1 = 0
        for (oa, *_), (ob_, *_) in zip(pa, pb):
            wa = struct.unpack_from("<2I", ht, oa)
            wb = struct.unpack_from("<2I", a_twin["tadata"], ob_)
            d0 += wa[0] != wb[0]
            d1 += wa[1] != wb[1] and wa[1] != 0
        out.append("against %s header by header: word 0 differs in %d, word 1 differs (not zero) in %d" % (a_twin["name"], d0, d1))
    return "; ".join(out)


def a_stage(outdir, s0dir=None):
    P, PH = PRED["a"], PRED["h"]
    cases = L.read_cases(outdir)
    s0dir = s0dir or where(outdir, "a", "s0")
    ctls = s0_controls(s0dir)
    lines, observed, rows, states = [], [], {}, {}
    js = {}
    # the premise
    j = js[A_CTL] = job(outdir, cases, A_CTL)
    ob, t = rule_obs(j)
    ctls[A_CTL] = {"complete": "PASS", "fault": "FAILED", None: "NODATA"}[ob]
    if ob:
        observed.append(dims(j["row"]["args"]) + (ob,))
    lines.append("%s (control, H-TPM complete at the limit): %s: %s%s" % (A_CTL, ctls[A_CTL], t, "; " + aux(j, P, A_CTL) if ob == "complete" else ""))
    for n in A_ROWS + tuple(A_REP.values()):
        j = js[n] = job(outdir, cases, n)
        ob, t = rule_obs(j)
        states[n] = ob
        if "row" not in j:
            lines.append("%s: %s" % (n, "not run (a1 faulted: the replicate runs only after a completion)" if n in A_REP.values() else t))
            continue
        want = L.pred(P, n, "htpm")
        if ob:
            observed.append(dims(j["row"]["args"]) + (ob,))
        dead = [r for r in R.RULES if L.pred(P, n, "rule:" + r) in ("fault", "complete") and ob and L.pred(P, n, "rule:" + r) != ob]
        extra = ""
        if ob == "complete":
            extra = "; " + aux(j, P, n)
        elif ob == "fault":
            rp = right_pixels(j)
            extra = "; right pixels before the fault %s (explore)" % rp
        word = "cannot tell" if not ob else ("held" if ob == want else "FAILED")
        lines.append("%s: %s (H-TPM %s: %s)%s%s" % (n, t, want, word, extra, "; contradicts the dead " + ", ".join(dead) if dead else ""))
    for n in A_ROWS:
        ob = states.get(n)
        st = None if ob is None else ob == L.pred(P, n, "htpm")
        if n in A_REP:
            r = A_REP[n]
            if r in (cases or {}):
                ob2 = states.get(r)
                st2 = None if ob2 is None else ob2 == L.pred(P, r, "htpm")
                c = K.combine([st, st2])
                st = {"held": True, "refuted": False}.get(c)
                lines.append("%s with its replicate %s: %s" % (n, r, c))
        rows[n] = st
    hs = {}
    for n in H_ROWS:
        j = js[n] = job(outdir, cases, n)
        if "row" not in j:
            rows[n] = None
            lines.append("%s: not run (%s)" % (n, "; ".join(j["void"])))
            continue
        ob, st, t = held_row(n, j, P, PH)
        rows[n] = st
        hs[n] = t
        if ob:
            observed.append(dims(j["row"]["args"]) + (ob,))
        lines.append("%s (held): %s" % (n, t))
        lines.append("%s (explore): %s" % (n, held_explore(n, j, js.get(H_TWIN.get(n)))))
    claim = ("H-TPM: a four-array 4x job faults iff the end of its target's Z-order tail-pointer entries (y on the even bits) passes the "
             "td.rgn of its context's maximum, and a held fault loses exactly the frozen stream offsets (a1, a8, a9, a12, a13 complete where "
             "K-OR and other dead size rules said fault; a2, a3, a5, a14 fault; h1 and h2 set equal)")
    hl = K.headline(claim, ctls, [rows[n] for n in A_ROWS + H_ROWS])
    surv = R.survivors(observed, R.ALL)
    tpm = [v for v in surv if v.startswith("TPM-")]
    dead = [v for v in surv if v in R.RULES]
    sv = "variants of the Z-order rule no decided row contradicts: %s; dead size rules: %s" % (", ".join(tpm) or "none", ", ".join(dead) or "none")
    res = {"controls": ctls, "rows": rows, "observed": observed, "survivors": surv, "htpm": hl, "variants": sv, "held": hs,
           "summary": "a: %s; %s" % (hl, sv)}
    return lines, res


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


T_CTL = "t8-ctl-te40-1array"
T_INS = ("t5-line-tec0", "t6-point-tec0")
T_POKE = "t7-tri-te40-poke11"


def t_ins_row(n, j, P):
    """(state, text) of t5 or t6: the insertion against the frozen baseline head (the kept 11.31 dump) and the image."""
    if j["void"]:
        return None, "cannot tell: " + void_text(j)
    if j["miss"]:
        return None, j["miss"]
    if j["row"]["class"] != "ok":
        return None, "cannot tell: class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    base = [int(x, 16) for x in L.pred(P, n, "base_0_64").split(",")]
    ins = insertion(base, L.dwords(j["param"]))
    img = L.image_word(j["out"])
    if ins is None:
        return False, "read, and matched no hypothesis: the dump is not the baseline's with one dword inserted (dwords 0-63); image %s" % img
    pos, val = ins
    okpos = pos == int(L.pred(P, n, "insert_pos"))
    okimg = img == L.pred(P, n, "image")
    if okpos and "0x%08x" % val == L.pred(P, n, "insert_val") and okimg:
        return True, "H-PAD held: one dword inserted at %d (before the format word), 0x00000000, image %s" % (pos, img)
    if okpos and val != 0:
        return False, "H-FIELD: one dword inserted at %d (before the format word) and it is 0x%08x, not zero; image %s" % (pos, val, img)
    if okpos and not okimg:
        return False, "the zero dword inserted at %d as frozen, but the image is %s (frozen %s)" % (pos, img, L.pred(P, n, "image"))
    return False, "H-PAD FAILED: one dword inserted at %d (frozen %s) with value 0x%08x; image %s" % (pos, L.pred(P, n, "insert_pos"), val, img)


def t_poke_row(n, j, P):
    """(state, text) of t7: the poke landed (the kernel's line, the dump's dword 11), then render 2's counts against E829's p4."""
    if j["void"]:
        return None, "cannot tell: " + void_text(j)
    if j["miss"]:
        return None, j["miss"]
    if j["row"]["class"] != "ok":
        return None, "cannot tell: class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    applied = L.kpoke_applied(j["dmesg"])
    w = L.dwords(j["param"])
    d11, d12 = "0x%08x" % w[11], "0x%08x" % w[12]
    if L.pred(P, n, "kpoke") not in applied or d11 != L.pred(P, n, "dword11"):
        return None, "cannot tell: the poke did not land (kernel lines %s, dword 11 %s, frozen %s)" % (applied or "none", d11, L.pred(P, n, "dword11"))
    t2 = L.tri_counts_text(j["out"], 2)
    want = L.pred(P, n, "tri2")
    if t2 == want and d12 == L.pred(P, n, "dword12"):
        return True, "H-OLD held: dword 11 %s (poked, applied), dword 12 %s, render 2: %s" % (d11, d12, t2)
    return False, "render 2: %s, dword 12 %s (frozen %s, %s): the poked dword is not read as E829 read 0xffffffff" % (t2, d12, want, L.pred(P, n, "dword12"))


def t_stage(outdir, s0dir=None):
    P = PRED["t"]
    cases = L.read_cases(outdir)
    s0dir = s0dir or where(outdir, "t", "s0")
    lines, rows, misses, texts = [], {}, [], {}
    js = {n: job(outdir, cases, n) for n in (T_CTL,) + T_INS + (T_POKE,)}
    v, t = ctl(js[T_CTL], P, T_CTL)
    ctls = {T_CTL: v}
    if js[T_CTL]["miss"]:
        misses.append(T_CTL)
    lines.append("%s: %s: %s" % (T_CTL, v, t))
    ctls.update(s0_controls(s0dir))
    for n in T_INS:
        s, t = t_ins_row(n, js[n], P)
        rows[n], texts[n] = s, t
        if js[n]["miss"]:
            misses.append(n)
        lines.append("%s (held out, 0xc0000000): %s" % (n, t))
    s, t = t_poke_row(T_POKE, js[T_POKE], P)
    rows[T_POKE], texts[T_POKE] = s, t
    if js[T_POKE]["miss"]:
        misses.append(T_POKE)
    lines.append("%s (held out, dword 11 poked): %s" % (T_POKE, t))
    claim = ("Q293: CR_TE_AA 0xc0000000 inserts one zero dword right before the format word of a line and a point and draws nothing, "
             "as 0x40 and 0x80 do; a non-zero value poked into the inserted dword of the triangle draws nothing (read as the format word)")
    q = K.headline(claim, ctls, [rows[n] for n in T_INS + (T_POKE,)])
    field = [n for n in T_INS if rows.get(n) is False and texts[n].startswith("H-FIELD")]
    if field and K.gate(ctls).ok:
        q = "H-FIELD: the inserted dword is non-zero at 0xc0000000 in %s: a field of the object, not padding [infer]; %s" % (", ".join(field), q)
    if misses:
        q = "READER-MISS in %s: the scorer could not find dumps the rows wrote; %s" % (", ".join(misses), q)
    return lines, {"verdicts": rows, "controls": ctls, "q293": q, "misses": misses, "summary": "t: %s" % q}


def score_stage(st, outdir):
    if st == "s0":
        return s0_stage(outdir)
    return {"a": a_stage, "t": t_stage}[st](outdir)


def verdict(roots):
    out = []
    s0d = stage_dir(roots, "s0")
    if not os.path.exists(os.path.join(s0d, "cases.tsv")):
        out.append("SUMMARY: session: not run (no kept stage s0)")
    else:
        out.append("SUMMARY: session: %s" % s0_stage(s0d)[1]["summary"])
    for st in ("a", "t"):
        d = stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (st, st))
            continue
        if st == "a":
            r = a_stage(d, s0d)[1]
            out.append("SUMMARY: H-TPM (a): %s" % r["htpm"])
            for n in H_ROWS:
                if n in r["held"]:
                    out.append("SUMMARY: %s: %s" % (n.split("-")[0], r["held"][n]))
            out.append("SUMMARY: a variants: %s" % r["variants"])
        else:
            out.append("SUMMARY: Q293 (t): %s" % t_stage(d, s0d)[1]["q293"])
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
