#!/usr/bin/env python3
"""r7-faults scorer (Q003's -110 by fault page and by manipulation, Q111's `lock #0` twice), written and frozen before the run.  Each
command prints its rows and ends with SUMMARY lines.

  score_f.py STAGE OUTDIR [ROOT...]   s0, l, d or m (s0's controls read from the first ROOT that has s0; default OUTDIR's parent)
  score_f.py gate STAGE ROOT...       exit 0 if s0's controls passed, 1 if not (the driver skips the stage cleanly)
  score_f.py premise STAGE OUTDIR     the premise (scorekit.premise_stops): every control of the stage has a reading of every key it
                                      declares, else STOP lines and exit 1 (the driver stops the session)
  score_f.py verdict ROOT...          the session's SUMMARY lines

Hypotheses and rows: gen/fgen.py's docstring and predictions/*.tsv (case, quantity, value, model, set, source).  The verdict rules are
scorekit's (score/scorekit.py, byte for byte resgx545 main's tools/closing/scorekit.py): any control that is not PASS shuts the gate
of the rows that depend on it (every row on s0's controls; a stage's held-out rows on the stage's own controls (l: l0 and l1; d: d0
and d1; m: m0a and m0b) and on their cell's H-JOB controls; an m clr cell's rows also on its M-CLR controls); a void job is cannot
tell, never a pass.  REQUIRED names every file the scorer reads in a kept stage (score/sessioncheck.py kept checks it).  Refuses to
score unless run/freeze_f.sh verify passes (SCORE_NOFREEZE=1 only in the offline tests' replays).
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

STAGES = ("s0", "l", "d", "m")
# the files a kept stage gives the scorer: cases.tsv, and for EVERY row (steps included) its output, its kernel-log slice, its regs
REQUIRED = {st: ("cases.tsv", ".txt", ".dmesg", ".regs") for st in STAGES}
STEPS_T = ("t1", "t2", "t3")
FAULT_RE = re.compile(r"BIF fault 0x([0-9a-f]+) at 0x([0-9a-f]+)")
KREG_RE = re.compile(r"sgxfive: kregnow 0x0c00: 0x([0-9a-f]+) -> 0x([0-9a-f]+), reads 0x([0-9a-f]+), BIF_INT_STAT 0x([0-9a-f]+) "
                     r"BIF_FAULT 0x([0-9a-f]+)")
STATE = {True: "held", False: "FAILED", None: "cannot tell"}
FAMILIES = {"l": ("H-SELF", "H-REFLAG", "H-RECOUNT", "L-REP"), "d": ("H-PAGE", "H-SIZE"), "m": ("H-CLR", "H-TIME", "H-NULL")}
STAGE_CTL = {"l": ("L-CTL",), "d": ("D-CTL",), "m": ("M-CTL",)}


# ---- reading -------------------------------------------------------------------------------------------------------------------
def read_text(p):
    log = os.environ.get("SCORE_READLOG")
    if not os.path.exists(p) and os.path.exists(p + ".gz"):
        p = p + ".gz"
    if log:
        with open(log, "a") as f:
            f.write("%s\t%s\n" % ("ok" if os.path.exists(p) else "MISSING", p))
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", errors="replace") if p.endswith(".gz") else open(p, errors="replace") as f:
        t = f.read()
    return t if t else None


def read_cases(outdir):
    t = read_text(os.path.join(outdir, "cases.tsv"))
    if t is None:
        return None
    lines = t.splitlines()
    head = lines[0].split("\t") if lines else []
    rows = {}
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) == len(head):
            rows[f[0]] = dict(zip(head, f))
    return rows


def load_predictions(st, kp=KP):
    out = []
    for ln in open(os.path.join(kp, "predictions", st + ".tsv")).read().splitlines()[1:]:
        if ln.strip():
            case, q, val, model, sset, src = ln.split("\t")
            out.append(dict(case=case, q=q, want=val, model=model, set=sset, src=src))
    return out


def reg(text, off):
    m = re.search(r"^reg 0x%04x (0x[0-9a-f]+)$" % off, text or "", re.M)
    return m.group(1) if m else None


def hexw(v):
    return None if v is None else "0x%08x" % int(v, 16)


def boots(text):
    """The boots of a slice in order: 'U' (EDM up) or 'T' (no INIT_COMPLETE), as the runner's boots()."""
    out = ""
    for ln in (text or "").splitlines():
        if "SGX boot: EDM up after" in ln:
            out += "U"
        elif "SGX boot: no INIT_COMPLETE" in ln:
            out += "T"
    return out


def boot_word(text):
    b = boots(text)
    return None if not b else ("timeout" if b[0] == "T" else "up")


def dump_clock(text):
    """CR_CLKGATESTATUS of each timed-out boot's dump (explore)."""
    out, dump = [], False
    for ln in (text or "").splitlines():
        if "SGX boot: no INIT_COMPLETE" in ln:
            dump = True
        elif "recovery failed" in ln:
            dump = False
        elif dump and "reg 0x008 = " in ln:
            out.append(ln.split()[-1])
    return out


def verify_freeze():
    if os.environ.get("SCORE_NOFREEZE") == "1":
        return True, "not verified (SCORE_NOFREEZE=1: an offline replay)"
    r = subprocess.run([os.path.join(KP, "run", "freeze_f.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def rfile(outdir, name, suffix):
    return read_text(os.path.join(outdir, name + suffix))


# ---- one row's readings ------------------------------------------------------------------------------------------------------
def got_gate(outdir, name):
    t = rfile(outdir, name, ".txt") or ""
    dm = rfile(outdir, name, ".dmesg")
    rfile(outdir, name, ".regs")
    g = {}
    m = re.search(r"^set rc (\d+)$", t, re.M)
    g["set_rc"] = m.group(1) if m else None
    k = KREG_RE.findall(dm or "")
    g["set_reads"] = "0x" + k[0][2] if len(k) >= 1 else None
    g["set_int"] = "0x" + k[0][3] if len(k) >= 1 else None
    g["back_reads"] = "0x" + k[1][2] if len(k) >= 2 else None
    return g


def got_probe(outdir, name, row):
    t = rfile(outdir, name, ".txt") or ""
    rfile(outdir, name, ".dmesg")
    rfile(outdir, name, ".regs")
    g = {"class": row.get("class")}
    if not re.search(r"^probe \S+: scratch at 0x", t, re.M):
        g["count"] = None
    elif re.search(r"^probe \S+: scratch unchanged$", t, re.M):
        g["count"] = "0"
    else:
        m = re.search(r"^probe \S+: scratch \+0x000 0x([0-9a-f]{8})$", t, re.M)
        g["count"] = None if not m else str(int(m.group(1), 16) - 0xd0000000)
    return g


def got_plain(outdir, name, row):
    for s in (".txt", ".dmesg", ".regs"):
        rfile(outdir, name, s)
    return {"class": row.get("class")}


def step(outdir, cases, name, st):
    """(class, first fault word, slice) of one step of a cell, or (None, None, '') when it has no row."""
    row = (cases or {}).get("%s.%s" % (name, st))
    if row is None:
        return None, None, ""
    d = rfile(outdir, name + "." + st, ".dmesg") or ""
    rfile(outdir, name + "." + st, ".txt")
    rfile(outdir, name + "." + st, ".regs")
    fl = FAULT_RE.findall(d)
    return row["class"], ("0x" + fl[0][1] if fl else None), d


def got_held(outdir, cases, name, row):
    g = {}
    regs = rfile(outdir, name, ".regs")
    dm = rfile(outdir, name, ".dmesg") or ""
    rfile(outdir, name, ".txt")
    g["job_class"] = row["class"]
    g["job_int"] = hexw(reg(regs, 0x0c04))
    g["job_word"] = hexw(reg(regs, 0x0c08))
    v = reg(regs, 0x0724)
    g["dpm_hold"] = None if v is None else "0x%x" % (int(v, 16) & 0xffff)
    g["boot_held"] = boot_word(dm) if row["class"] == "fault" else None
    k = KREG_RE.findall(dm)
    if len(k) >= 1:
        g["clr_hidden"] = "yes" if (int(k[0][3], 16) & 0xffff) == 0 and int(k[0][4], 16) == 0 else "no"
    else:
        g["clr_hidden"] = None
    if len(k) >= 2 and g["job_int"] and g["job_word"]:
        g["clr_back"] = "yes" if int(k[1][3], 16) == int(g["job_int"], 16) and int(k[1][4], 16) == int(g["job_word"], 16) else "no"
    else:
        g["clr_back"] = None
    tris = [step(outdir, cases, name, s) for s in STEPS_T]
    g["first_tri"] = tris[0][0]
    rep = next((t for t in tris if t[0] == "fault"), None)
    g["boot_replay1"] = boot_word(rep[2]) if rep else None
    oks = [i + 1 for i, t in enumerate(tris) if t[0] == "ok"]
    g["passes_within"] = "3" if oks and oks[0] <= 3 else (None if not any(t[0] for t in tris) else "no")
    # explore
    g["_boots"] = boots(dm) + "|" + "|".join(boots(t[2]) for t in tris if t[0])
    g["_replays"] = sum(1 for t in tris if t[0] == "fault")
    g["_words"] = ["%s %s%s" % (s, t[0], "" if t[1] is None else " " + t[1]) for s, t in zip(STEPS_T, tris) if t[0]]
    g["_clock"] = dump_clock(dm) + [c for t in tris for c in dump_clock(t[2])]
    return g


def readings(outdir, st, cases):
    """{case: (got, void)} for every case the predictions of the stage name."""
    P = load_predictions(st)
    out = {}
    for case in dict.fromkeys(r["case"] for r in P):
        row = (cases or {}).get(case)
        if row is None:
            out[case] = ({}, ["no cases.tsv row (not run)"])
            continue
        if row.get("class") not in ("ok", "fault", "hang", "fail"):
            out[case] = ({}, ["class %r" % row.get("class")])
            continue
        mode = row.get("mode")
        if mode == "gate":
            g = got_gate(outdir, case)
        elif mode == "probe":
            g = got_probe(outdir, case, row)
        elif mode == "held":
            g = got_held(outdir, cases, case, row)
        else:
            g = got_plain(outdir, case, row)
        out[case] = (g, [])
    return out


def compare(g, r):
    got = g.get(r["q"])
    if got is None:
        return None, got
    return (str(got) == r["want"]), got


def ctl_state(raw):
    return "PASS" if raw is True else "FAIL" if raw is False else "NODATA"


# ---- s0 and the gate ---------------------------------------------------------------------------------------------------------
def find_stage(roots, st):
    for r in roots:
        if os.path.exists(os.path.join(r, st, "cases.tsv")):
            return os.path.join(r, st)
    return None


def s0_controls(outdir):
    rows, _, _ = stage_rows("s0", outdir, {})
    return {"%s:%s" % (x["case"], x["q"]): ctl_state(x["raw"]) for x in rows}


def gate(stage, roots):
    d = find_stage(roots, "s0")
    if d is None:
        return 1, "gate %s: closed: no kept s0 in %s" % (stage, " ".join(roots))
    g = K.gate(s0_controls(d))
    return (0 if g.ok else 1), "gate %s: %s (s0 from %s)" % (stage, "open" if g.ok else "closed: " + "; ".join(g.problems), d)


# ---- a stage's rows ----------------------------------------------------------------------------------------------------------
def stage_rows(st, outdir, s0ctl):
    P = load_predictions(st)
    cases = read_cases(outdir)
    got = readings(outdir, st, cases)
    rows = []
    for r in P:
        g, void = got[r["case"]]
        raw, val = (None, None) if void else compare(g, r)
        rows.append(dict(r, raw=raw, got=val, void=void))
    s0g = {"s0:" + k: v for k, v in s0ctl.items()}
    # the stage's own controls that ran (a stop before the second M0 cell, the budget's, leaves it out: the cells that ran are
    # gated by the controls that ran); none ran: NODATA, which shuts every held-out row
    stage_ctl = {"%s:%s:%s" % (x["case"], x["q"], x["model"]): ctl_state(x["raw"]) for x in rows
                 if x["set"] == "control" and x["model"] in STAGE_CTL.get(st, ()) and x["void"] != ["no cases.tsv row (not run)"]}
    if st in STAGE_CTL and not stage_ctl:
        stage_ctl = {"%s: no stage control ran" % st: "NODATA"}
    for x in rows:
        if x["set"] == "control":
            x["gate"] = K.gate(s0g) if st != "s0" else K.Gate(ok=True)
            x["state"] = x["raw"]
            continue
        need = dict(s0g)
        need.update(stage_ctl)
        need.update({"%s:%s:%s" % (y["case"], y["q"], y["model"]): ctl_state(y["raw"]) for y in rows
                     if y["case"] == x["case"] and y["set"] == "control" and y["model"] in ("H-JOB", "M-CLR")})
        x["gate"] = K.gate(need)
        x["state"] = K.gated(x["gate"], x["raw"])
    return rows, got, stage_ctl


def stage_score(st, outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    s0ctl = {}
    if st != "s0":
        d0 = find_stage(roots, "s0")
        s0ctl = s0_controls(d0) if d0 else {}
    rows, got, stage_ctl = stage_rows(st, outdir, s0ctl)
    lines = []
    for c in dict.fromkeys(x["case"] for x in rows):
        g, void = got[c]
        if void:
            lines.append("%s: cannot tell: %s" % (c, "; ".join(void)))
        elif "_boots" in g:
            lines.append("%s: job %s %s %s; dpm pages at the hold %s; boots (held reset | steps) %s; steps: %s; replays %d; "
                         "timed-out dumps' CLKGATESTATUS %s" % (c, g.get("job_class"), g.get("job_int"), g.get("job_word"),
                                                                g.get("dpm_hold"), g["_boots"], ", ".join(g["_words"]) or "none",
                                                                g["_replays"], ",".join(g["_clock"]) or "-"))
        else:
            lines.append("%s: %s" % (c, " ".join("%s=%s" % (k, v) for k, v in sorted(g.items()))))
        for x in rows:
            if x["case"] != c:
                continue
            why = "" if x["gate"].ok or x["set"] == "control" else " (gate: %s)" % "; ".join(x["gate"].problems[:3])
            lines.append("  %-14s %-9s %-9s %-11s got %-12s frozen %-12s %s%s" % (
                x["q"], x["model"], x["set"], STATE[x["state"]], x["got"], x["want"], x["src"][:60], why))
    controls = {"%s:%s:%s" % (x["case"], x["q"], x["model"]): ctl_state(x["raw"]) for x in rows if x["set"] == "control"}
    controls.update({"s0:" + k: v for k, v in s0ctl.items()})
    ctl_fail = sorted(k for k, v in controls.items() if v == "FAIL")
    summary = []
    if st == "s0":
        g = K.gate(controls)
        summary.append("s0: controls %s" % ("all PASS (%d)" % len(controls) if g.ok else "NOT passed: " + "; ".join(g.problems)))
    else:
        fam = {m: K.tally([x["state"] for x in rows if x["model"] == m and x["set"] != "control"]) for m in FAMILIES[st]}

        def word(t):
            v = t.verdict()
            return "consistent" if v is True else "REFUTED" if v is False else "cannot tell"
        summary.append("%s: %s" % (st, "; ".join("%s %s (%s)" % (m, word(fam[m]), fam[m]) for m in FAMILIES[st])))
        heads = {"l": [("Q111 lock (l)", "H-SELF", "H-SELF: a second lock #0 of a held mutex blocks its own holder (a pixel program)"),
                       ("Q111 lock (l)", "H-REFLAG", "H-REFLAG: a re-lock passes and one release frees the mutex"),
                       ("Q111 lock (l)", "H-RECOUNT", "H-RECOUNT: a re-lock passes and the locks are counted")],
                 "d": [("Q003 page (d)", "H-PAGE", "H-PAGE: the boot after a held 0x90004 fault times out iff the page is 0x20006 to 0x20008"),
                       ("Q003 page (d)", "H-SIZE", "H-SIZE: it times out iff the size is 288 x 144")],
                 "m": [("Q003 clear (m)", "H-CLR", "H-CLR: CLEAR_FAULT set and cleared while held makes the boot come up"),
                       ("Q003 time (m)", "H-TIME", "H-TIME: a 9 s hold makes the boot come up"),
                       ("Q003 null (m)", "H-NULL", "H-NULL: the boot times out as without the manipulation")]}[st]
        for label, model, claim in heads:
            mrows = [x for x in rows if x["model"] == model and x["set"] != "control"]
            need = {"s0:" + k: v for k, v in s0ctl.items()}
            need.update(stage_ctl)
            for x in mrows:
                if x["void"] != ["no cases.tsv row (not run)"]:
                    need.update({"%s:%s:%s" % (y["case"], y["q"], y["model"]): ctl_state(y["raw"]) for y in rows
                                 if y["case"] == x["case"] and y["set"] == "control" and y["model"] in ("H-JOB", "M-CLR")})
            summary.append("%s: %s" % (label, K.headline(claim, need, [x["state"] for x in mrows])))
        if st in ("d", "m"):
            t110 = sum(boots(rfile(outdir, c, ".dmesg") or "").count("T") for c, (g, v) in got.items() if not v)
            summary.append("%s: timed-out boots after the held resets %d (explore; every boot of the rows: the ledger)" % (st, t110))
    summary.append("%s controls: %d PASS, %d FAIL%s, %d NODATA" % (st, sum(v == "PASS" for v in controls.values()), len(ctl_fail),
                                                                   (" " + str(ctl_fail)) if ctl_fail else "",
                                                                   sum(v == "NODATA" for v in controls.values())))
    return lines, {"summary": summary, "rows": rows}


def files_for(stage, outdir):
    """sessioncheck.py kept --call: the scoring of one kept stage (its reads are audited)."""
    stage_score(stage, outdir, [os.path.dirname(os.path.abspath(outdir))])


# ---- the premise -------------------------------------------------------------------------------------------------------------
def premise(st, outdir):
    """STOP lines: a control of the stage with no reading of a key it declared, or that did not run."""
    P = load_predictions(st)
    cases = read_cases(outdir)
    got = readings(outdir, st, cases)
    decl, read = {}, {}
    for r in P:
        if r["set"] != "control":
            continue
        name = "%s:%s" % (r["case"], r["model"])
        decl[name] = tuple(decl.get(name, ())) + (r["q"],)
        g, void = got[r["case"]]
        if void == ["no cases.tsv row (not run)"]:
            continue
        read.setdefault(name, {})[r["q"]] = g.get(r["q"])
    return K.premise_stops(decl, read)


def verdict(roots):
    out = []
    for st in STAGES:
        d = find_stage(roots, st)
        if d is None:
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (st, st))
            continue
        out += ["SUMMARY: " + s for s in stage_score(st, d, roots)[1]["summary"]]
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
    if argv[1] == "premise":
        stops = premise(argv[2], argv[3])
        print("\n".join(stops) if stops else "premise %s: every control has its readings" % argv[2])
        return 1 if stops else 0
    st, outdir = argv[1], argv[2]
    if st not in STAGES:
        print("unknown stage %s" % st)
        return 2
    lines, r = stage_score(st, outdir, argv[3:] or None)
    print("\n".join(lines))
    print("\n".join("SUMMARY: " + s for s in r["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
