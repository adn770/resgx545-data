#!/usr/bin/env python3
"""r6-held part H scorer (Q003's replay clause on the new kernel), written and frozen before the run.  Each command prints its rows
and ends with SUMMARY lines.

  score_h.py s0 OUTDIR             the controls (n0: bif_flush refused with nothing held; c1: the health triangle)
  score_h.py q OUTDIR [ROOT...]    the cells (s0's controls read from the first ROOT that has s0; default: OUTDIR's parent)
  score_h.py gate q ROOT...        exit 0 if s0's controls passed, 1 if not (the driver skips q cleanly)
  score_h.py verdict ROOT...       the session's SUMMARY lines

Hypotheses and rows: gen/hgen.py's docstring and predictions/{s0,q}.tsv (case, quantity, value, model, set, source).  The verdict rules
are scorekit's (score/scorekit.py, byte for byte resgx545 main's tools/closing/scorekit.py): any control that is not PASS shuts the
gate of the rows that depend on it (a cell's rows depend on s0's controls and on the cell's own H-JOB controls; a fill cell's list
rows on its H-FILL control; a flushed cell's K2 rows on its H-KEEP controls and on a0's replay, the control that a replay happens on
this kernel at all); a void job is cannot tell, never a pass.  Refuses to score unless run/freeze_h.sh verify passes (SCORE_NOFREEZE=1
only in the offline tests' replays, which never print a SUMMARY to a session).
"""
import gzip
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import scorekit as K  # noqa: E402

STEPS_T = ("t1", "t2", "t3")
FLUSH_RE = re.compile(r"bif_flush: BIF_CTRL 0x([0-9a-f]+) -> 0x([0-9a-f]+), BIF_INT_STAT 0x([0-9a-f]+) BIF_FAULT 0x([0-9a-f]+)"
                      r" MEM_REQ_STAT 0x([0-9a-f]+)")
FAULT_RE = re.compile(r"BIF fault 0x([0-9a-f]+) at 0x([0-9a-f]+)")
STATE = {True: "held", False: "FAILED", None: "cannot tell"}


# ---- reading -------------------------------------------------------------------------------------------------------------------
def read_text(p):
    log = os.environ.get("SCORE_READLOG")
    if log:
        with open(log, "a") as f:
            f.write("%s\t%s\n" % ("ok" if os.path.exists(p) else "MISSING", p))
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", errors="replace") if p.endswith(".gz") else open(p, errors="replace") as f:
        t = f.read()
    return t if t else None


def read_cases(outdir):
    p = os.path.join(outdir, "cases.tsv")
    if not os.path.exists(p):
        return None
    lines = open(p).read().splitlines()
    head = lines[0].split("\t") if lines else []
    rows = {}
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) == len(head):
            rows[f[0]] = dict(zip(head, f))
    return rows


def load_predictions(name, kp=KP):
    out = []
    for ln in open(os.path.join(kp, "predictions", name)).read().splitlines()[1:]:
        if ln.strip():
            case, q, val, model, sset, src = ln.split("\t")
            out.append(dict(case=case, q=q, want=val, model=model, set=sset, src=src))
    return out


def reg(text, off):
    m = re.search(r"^reg 0x%04x (0x[0-9a-f]+)$" % off, text or "", re.M)
    return m.group(1) if m else None


def faults(text):
    return [(int(a, 16), int(b, 16)) for a, b in FAULT_RE.findall(text or "")]


def hexw(v):
    return None if v is None else "0x%08x" % v


def verify_freeze():
    if os.environ.get("SCORE_NOFREEZE") == "1":
        return True, "not verified (SCORE_NOFREEZE=1: an offline replay)"
    r = subprocess.run([os.path.join(KP, "run", "freeze_h.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


# ---- one cell ----------------------------------------------------------------------------------------------------------------
def step(outdir, cases, name, st):
    """(class, first fault word, slice) of one step of a cell, or (None, None, '') when it has no row."""
    row = (cases or {}).get("%s.%s" % (name, st))
    if row is None:
        return None, None, ""
    d = read_text(os.path.join(outdir, "%s.%s.dmesg.gz" % (name, st))) or ""
    o = read_text(os.path.join(outdir, "%s.%s.txt.gz" % (name, st))) or ""
    fl = faults(d) or faults(o)
    return row["class"], (fl[0][1] if fl else None), d


def cell_got(outdir, cases, name, qs=()):
    """What the kept files say of one q cell: {quantity: value or None}, and void reasons.  qs: the frozen quantities of the cell
    (a file is read only when a quantity needs it, so every read of a run's scoring names a file the runner keeps)."""
    g, void = {}, []
    row = (cases or {}).get(name)
    if row is None:
        return g, ["no cases.tsv row (not run)"]
    if row.get("class") not in ("ok", "fault", "hang", "fail"):
        return g, ["class %r" % row.get("class")]
    p = lambda s: os.path.join(outdir, name + s)  # noqa: E731
    s1 = read_text(p(".snap1.regs.gz"))
    if s1 is None:
        void.append("snap 1 missing")
    g["job_class"] = row["class"]
    v = reg(s1, 0x0c04)
    g["job_int"] = None if v is None else "0x%08x" % int(v, 16)
    v = reg(s1, 0x0c08)
    g["job_word"] = None if v is None else "0x%08x" % int(v, 16)
    dm = read_text(p(".dmesg.gz")) or ""
    fl = read_text(p(".flush.txt.gz")) if any(q.startswith("flush") for q in qs) else None
    if fl is not None:
        m = re.match(r"rc (-?\d+)", fl)
        g["flush_rc"] = m.group(1) if m else None
    else:
        g["flush_rc"] = None
    m = FLUSH_RE.search(dm)
    if m:
        g["flush_ctrl_same"] = "yes" if int(m.group(1), 16) == int(m.group(2), 16) else "no"
        g["flush_int"] = "0x%08x" % int(m.group(3), 16)
        g["flush_word"] = "0x%08x" % int(m.group(4), 16)
    else:
        g["flush_ctrl_same"] = g["flush_int"] = g["flush_word"] = None
    # the -110 that follows the held reset: the job's slice ends before the first step's marker
    g["minus110_reset"] = "1" if "recovery failed: -110" in dm else "0" if dm else None
    st_fill = step(outdir, cases, name, "fill") if "fill_class" in qs else (None, None, "")
    g["fill_class"] = st_fill[0]
    tris = [step(outdir, cases, name, s) for s in STEPS_T]
    t1 = tris[0]
    g["first_tri"] = t1[0]
    g["first_word"] = hexw(t1[1]) if t1[0] == "fault" else None
    oks = [i + 1 for i, t in enumerate(tris) if t[0] == "ok"]
    g["passes_within"] = "3" if oks and oks[0] <= 3 else (None if not any(t[0] for t in tris) else "no")
    g["replays"] = sum(1 for t in tris if t[0] == "fault") + (1 if st_fill[0] == "fault" else 0)
    g["minus110_cell"] = int(any("recovery failed: -110" in s for s in [dm, st_fill[2]] + [t[2] for t in tris]))
    g["peek"] = {k: (read_text(p(".peek%s.txt.gz" % k)) or "").strip() for k in ("0", "1", "3")}
    g["step_words"] = ["%s %s%s" % (s, t[0], "" if t[1] is None else " 0x%08x" % t[1]) for s, t in zip(("fill",) + STEPS_T, [st_fill] + tris) if t[0]]
    return g, void


def compare(g, r):
    got = g.get(r["q"])
    if got is None:
        return None, got
    return (str(got) == r["want"]), got


# ---- s0 -----------------------------------------------------------------------------------------------------------------------
def s0_controls(outdir):
    """{'n0:flush_refused': state, ...} and lines."""
    cases = read_cases(outdir)
    P = load_predictions("s0.tsv")
    ctl, lines = {}, []
    for r in P:
        name, q = r["case"], r["q"]
        row = (cases or {}).get(name)
        key = "%s:%s" % (name, q)
        if row is None:
            ctl[key] = "NODATA"
            lines.append("%s: NODATA (not run)" % key)
            continue
        pth = lambda s: os.path.join(outdir, name + s)  # noqa: E731
        if q == "flush_refused":
            t = read_text(pth(".txt.gz")) or ""
            m = re.match(r"rc (\d+)", t)
            got = None if not m else ("busy" if m.group(1) != "0" and re.search("busy", t, re.I) else "not refused")
        elif q == "flush_ctrl_same":
            a, b = reg(read_text(pth(".snap0.regs.gz")), 0x0c00), reg(read_text(pth(".snap1.regs.gz")), 0x0c00)
            dm = read_text(pth(".dmesg.gz")) or ""
            got = None if a is None or b is None else ("yes" if a == b and "bif_flush:" not in dm else "no")
        elif q == "peek_format":
            t = (read_text(pth(".peek0.txt.gz")) or "").strip()
            got = None if not t else ("reg 0x0694" if re.fullmatch(r"reg 0x0694 0x[0-9a-f]{8}", t) else "bad: " + t[:40])
        elif q == "class":
            got = row.get("class")
        else:
            got = None
        st = "NODATA" if got is None else ("PASS" if got == r["want"] else "FAIL")
        ctl[key] = st
        lines.append("%s: %s (got %s, frozen %s)" % (key, st, got, r["want"]))
    return ctl, lines


def find_stage(roots, st):
    for r in roots:
        if os.path.exists(os.path.join(r, st, "cases.tsv")):
            return os.path.join(r, st)
    return None


def s0_stage(outdir):
    ctl, lines = s0_controls(outdir)
    g = K.gate(ctl)
    s = "s0: controls %s" % ("all PASS (%d)" % len(ctl) if g.ok else "NOT passed: " + "; ".join(g.problems))
    return lines, {"summary": [s], "controls": ctl}


def gate(stage, roots):
    d = find_stage(roots, "s0")
    if d is None:
        return 1, "gate %s: closed: no kept s0 in %s" % (stage, " ".join(roots))
    ctl, _ = s0_controls(d)
    g = K.gate(ctl)
    return (0 if g.ok else 1), "gate %s: %s (s0 from %s)" % (stage, "open" if g.ok else "closed: " + "; ".join(g.problems), d)


# ---- q --------------------------------------------------------------------------------------------------------------------------
FAMILIES = ("H-LIST", "H-WORD", "H-FLUSH", "H-PEND", "H-BOOT", "H-LATCH", "H-REPLAY")
CONTROL_MODELS = ("H-JOB", "H-FILL", "H-KEEP", "H-END", "H-REPLAY")


def q_rows(outdir, s0ctl, kp=KP):
    """Every frozen row of q with its raw state (the comparison alone) and its gated state."""
    P = load_predictions("q.tsv", kp)
    cases = read_cases(outdir)
    cells = []
    for r in P:
        if r["case"] not in cells:
            cells.append(r["case"])
    got = {c: cell_got(outdir, cases, c, {r["q"] for r in P if r["case"] == c}) for c in cells}
    rows = []
    for r in P:
        g, void = got[r["case"]]
        raw, val = (None, None) if void else compare(g, r)
        rows.append(dict(r, raw=raw, got=val, void=void))
    # controls per cell
    ctl = {}
    for x in rows:
        if x["set"] == "control":
            ctl.setdefault(x["case"], {})["%s:%s:%s" % (x["case"], x["q"], x["model"])] = \
                "PASS" if x["raw"] is True else "FAIL" if x["raw"] is False else "NODATA"
    a0 = [x["raw"] for x in rows if x["case"].startswith("a0") and x["model"] == "H-REPLAY"]
    replay_ctl = {"a0:replay": "FAIL" if False in a0 else "PASS" if a0 and all(v is True for v in a0) else "NODATA"}
    s0g = dict(("s0:" + k, v) for k, v in s0ctl.items())
    for x in rows:
        c = ctl.get(x["case"], {})
        need = dict(s0g)
        need.update({k: v for k, v in c.items() if ":H-JOB" in k})
        if x["set"] == "control":
            x["gate"] = K.gate(s0g) if s0g else K.Gate(ok=False, problems=["no s0 control"])
            x["state"] = x["raw"]
            continue
        if x["model"] in ("H-LIST", "H-WORD") and "fill" in x["case"]:
            need.update({k: v for k, v in c.items() if ":H-FILL" in k})
        if x["model"] in ("H-FLUSH", "H-PEND", "H-BOOT", "H-LATCH"):
            need.update({k: v for k, v in c.items() if ":H-KEEP" in k})
        if x["model"] in ("H-FLUSH", "H-PEND", "H-BOOT"):
            need.update(replay_ctl)
        x["gate"] = K.gate(need)
        x["state"] = K.gated(x["gate"], x["raw"])
    return rows, got, ctl, replay_ctl


def q_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    d0 = find_stage(roots, "s0")
    s0ctl = s0_controls(d0)[0] if d0 else {}
    rows, got, ctl, replay_ctl = q_rows(outdir, s0ctl)
    lines = []
    for c in dict.fromkeys(x["case"] for x in rows):
        g, void = got[c]
        if void:
            lines.append("%s: cannot tell: %s" % (c, "; ".join(void)))
        else:
            lines.append("%s: job %s %s %s; steps: %s; replays %d; -110 in the cell %d; peek %s" % (
                c, g.get("job_class"), g.get("job_int"), g.get("job_word"), ", ".join(g["step_words"]) or "none",
                g["replays"], g["minus110_cell"], " / ".join("%s=%s" % (k, v or "-") for k, v in g["peek"].items())))
        for x in rows:
            if x["case"] != c:
                continue
            why = "" if x["gate"].ok or x["set"] == "control" else " (gate: %s)" % "; ".join(x["gate"].problems)
            lines.append("  %-14s %-8s %-8s %-10s got %-12s frozen %-12s %s%s" % (
                x["q"], x["model"], x["set"], STATE[x["state"]], x["got"], x["want"], x["src"][:60], why))
    fam = {}
    for m in FAMILIES:
        t = K.tally([x["state"] for x in rows if x["model"] == m and x["set"] != "control"])
        fam[m] = t
    controls = {}
    for c in ctl.values():
        controls.update(c)
    controls.update(replay_ctl)
    controls.update(("s0:" + k, v) for k, v in s0ctl.items())

    def word(t):
        v = t.verdict()
        return "consistent" if v is True else "REFUTED" if v is False else "cannot tell"
    famtxt = "; ".join("%s %s (%s)" % (m, word(fam[m]), fam[m]) for m in FAMILIES)
    list_rows = [x["state"] for x in rows if x["model"] == "H-LIST"]
    flush_rows = [x["state"] for x in rows if x["model"] == "H-FLUSH"]
    ctl_fail = sorted(k for k, v in controls.items() if v == "FAIL")
    q_list = K.headline("H-LIST: the replay goes through the directory list current at the next TA run", controls_for(rows, "H-LIST", s0ctl), list_rows)
    q_flush = K.headline("H-FLUSH: a BIF invalidate while the fault is held drops the pending write (no replay)",
                         controls_for(rows, "H-FLUSH", s0ctl, replay_ctl), flush_rows)
    summary = ["q: %s" % famtxt,
               "Q003 list (q): %s" % q_list,
               "Q003 flush (q): %s" % q_flush,
               "q controls: %d PASS, %d FAIL%s, %d NODATA" % (sum(v == "PASS" for v in controls.values()), len(ctl_fail),
                                                            (" " + str(ctl_fail)) if ctl_fail else "",
                                                            sum(v == "NODATA" for v in controls.values()))]
    return lines, {"summary": summary, "rows": rows, "fam": fam}


def controls_for(rows, model, s0ctl, extra=None):
    """The controls that gate the rows of one model, merged over the cells that ran and hold such rows."""
    out = dict(("s0:" + k, v) for k, v in s0ctl.items())
    out.update(extra or {})
    for x in rows:
        # a cell that did not run (a stop before it) adds no control: its rows are cannot tell and counted as such
        if x["void"] == ["no cases.tsv row (not run)"]:
            continue
        if x["set"] == "control" and any(y["case"] == x["case"] and y["model"] == model for y in rows):
            if x["model"] == "H-JOB" or (x["model"] == "H-FILL" and model in ("H-LIST", "H-WORD")) or \
                    (x["model"] == "H-KEEP" and model in ("H-FLUSH", "H-PEND", "H-BOOT", "H-LATCH")):
                out["%s:%s:%s" % (x["case"], x["q"], x["model"])] = "PASS" if x["raw"] is True else "FAIL" if x["raw"] is False else "NODATA"
    return out


def verdict(roots):
    out = []
    d0 = find_stage(roots, "s0")
    if d0 is None:
        out.append("SUMMARY: session: no kept s0")
    else:
        out += ["SUMMARY: " + s for s in s0_stage(d0)[1]["summary"]]
    dq = find_stage(roots, "q")
    if dq is None:
        out.append("SUMMARY: q: not run (no kept stage q)")
    else:
        out += ["SUMMARY: " + s for s in q_stage(dq, roots)[1]["summary"]]
    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ok, msg = verify_freeze()
    if not ok:
        print("FROZEN FILES CHANGED: refusing to score\n%s" % msg)
        return 3
    if argv[1] == "verdict":
        print(verdict(argv[2:]))
        return 0
    if argv[1] == "gate":
        code, m = gate(argv[2], argv[3:])
        print(m)
        return code
    st, outdir = argv[1], argv[2]
    if st == "s0":
        lines, r = s0_stage(outdir)
    elif st == "q":
        lines, r = q_stage(outdir, argv[3:] or None)
    else:
        print("unknown stage %s" % st)
        return 2
    print("\n".join(lines))
    print("\n".join("SUMMARY: " + s for s in r["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
