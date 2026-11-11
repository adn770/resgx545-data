#!/usr/bin/env python3
"""R4-A scorer (Q285 rerun), written and frozen before the run.  Each command prints its rows and ends with one SUMMARY.

  score_a.py a-pb0 OUTDIR          the three controls of the split flow (PASS / FAIL / NODATA)
  score_a.py a-pb OUTDIR           p2 (a control) and the pokes p3, p4; Q285 against H-OLD and H-FIELD (the controls of a-pb0 are
                                   read from OUTDIR's parent, the attempt directory)
  score_a.py gate a-pb ROOT...     exit 0 if a-pb0's three controls passed, 1 closed (the message names them)
  score_a.py verdict ROOT...       Q285 from the kept stages
(ROOT: an out/ATT directory; with several, each stage is read from the first that has it)

The verdict rules are scorekit's (score/scorekit.py, byte for byte resgx545 tools/closing/scorekit.py at main 6421c1c, last
changed in eb84f54): any control that is not PASS (FAIL, NODATA) shuts the gate of every row; replicates that disagree are mixed,
never held; a void job is cannot tell and never a pass; the headline names how many rows decided, and rows that were read and
matched no hypothesis say so.  Refuses to score unless run/freeze_k.sh verify passes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alib as L  # noqa: E402
import scorekit as K  # noqa: E402

P0 = P1 = None
PB0 = ("pb-d0-te40", "pb-p0-te60", "pb-p1-te40")
P3 = ("pb-p3a-twin", "pb-p3b-twin")
P4 = ("pb-p4a-ffff", "pb-p4b-ffff")


def preds():
    global P0, P1
    P0 = L.load_predictions("a-pb0.tsv")
    P1 = L.load_predictions("a-pb.tsv")


def job(outdir, cases, name):
    """Everything kept for one job; j['void'] lists what makes it no data."""
    j = {"name": name, "void": []}
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
    j["out"] = L.read_text(os.path.join(outdir, name + ".txt.gz"))
    if j["out"] is None:
        j["void"].append("tool output missing or empty")
    j["dmesg"] = L.read_text(os.path.join(outdir, name + ".dmesg.gz")) or ""
    j["armed"] = L.read_text(os.path.join(outdir, name + ".kpoke.txt.gz"))
    j["armed_kept"] = os.path.exists(os.path.join(outdir, name + ".kpoke.txt.gz"))
    j["param"] = L.read_bytes(os.path.join(outdir, name + ".tri.param.bin.gz"))
    j["tadata"] = L.read_bytes(os.path.join(outdir, name + ".tri.tadata.bin.gz"))
    return j


def stage_dir(roots, stage):
    for r in roots:
        if os.path.exists(os.path.join(r, stage, "cases.tsv")):
            return os.path.join(r, stage)
    return os.path.join(roots[0], stage) if roots else stage


def got_of(j):
    o = j["out"]
    return {"rc": str(j.get("rc")), "echo": L.echo(o), "geometry1": L.geometry1(o), "target_hash": L.target_hash(o),
            "diff": L.diff_text(o), "tri2": L.tri_text(o, 2), "renders": L.renders(o),
            "param_sha256": None if j["param"] is None else L.sha256(j["param"]),
            "param_size": None if j["param"] is None else "%d" % len(j["param"]),
            "tadata_sha256": None if j["tadata"] is None else L.sha256(j["tadata"]),
            "tadata_size": None if j["tadata"] is None else "%d" % len(j["tadata"]),
            "par_0_64": L.words(j["param"], 0, 64)}


def ctl(j, P, name, ref_sha=None):
    """A control against its frozen quantities: ("PASS" | "FAIL" | "NODATA", text)."""
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"])
    if j["row"]["class"] != "ok":
        return "FAIL", "class %s rc %s" % (j["row"]["class"], j["row"].get("rc"))
    if j["param"] is None or j["tadata"] is None:
        return "NODATA", "NODATA (no parameter-buffer or TA-data dump)"
    if L.overflowed(j["out"], j["dmesg"]):
        return "NODATA", "NODATA (a parameter-buffer overflow message in the output)"
    got, bad = got_of(j), []
    for (case, q), vals in sorted(P.items()):
        if case != name or q not in got:
            continue
        want = vals[0][0]
        if got[q] != want:
            bad.append("%s %s, frozen %s" % (q, got[q] if q != "par_0_64" else _wdiff(got[q], want), want if q != "par_0_64" else "(dwords)"))
    if ref_sha is not None and got["param_sha256"] != ref_sha:
        bad.append("parameter buffer differs from the dump run's")
    ap = L.kpoke_applied(j["dmesg"])
    if (case_q(P, name, "applied") or "") != ";".join(ap):
        bad.append("kernel log applied %s, frozen %s" % (ap or "nothing", case_q(P, name, "applied") or "nothing"))
    if case_q(P, name, "armed_after") is not None:
        if not j["armed_kept"]:
            return "NODATA", "NODATA (the debugfs kpoke read after the job was not kept)"
        if (j["armed"] or "").strip() != "":
            bad.append("a poke still armed after the job (debugfs kpoke: %s)" % j["armed"].strip().replace("\n", " "))
    return ("FAIL" if bad else "PASS"), ("; ".join(bad) if bad else "as frozen (hash %s, diff %s)" % (got["target_hash"], got["diff"]))


def case_q(P, case, q):
    v = P.get((case, q))
    return None if not v else v[0][0]


def _wdiff(a, b):
    if a is None:
        return "none"
    x, y = a.split(","), b.split(",")
    d = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
    return "differ at dwords %s" % d[:8]


def pb0_stage(outdir):
    cases = L.read_cases(outdir)
    res, lines = {}, []
    d0 = job(outdir, cases, "pb-d0-te40")
    d0sha = None if d0.get("param") is None else L.sha256(d0["param"])
    for n in PB0:
        j = d0 if n == "pb-d0-te40" else job(outdir, cases, n)
        v, t = ctl(j, P0, n, d0sha if n == "pb-p1-te40" else None)
        res[n] = v
        lines.append("%s: %s: %s" % (n, v, t))
    g = K.gate(res)
    s = "a-pb0: controls %s; gate a-pb %s" % (res, "open" if g.ok else "closed")
    return lines, {"verdicts": res, "summary": s, "gate": g}


def gate(stage, roots):
    if stage != "a-pb":
        return 0, "gate %s: no prerequisite" % stage
    d = stage_dir(roots, "a-pb0")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate a-pb: closed: no a-pb0 stage was kept (rerun: run/k.sh --only a-pb0)"
    _, r = pb0_stage(d)
    if not r["gate"].ok:
        return 1, "gate a-pb: closed: a-pb0 controls %s (rerun: run/k.sh --only a-pb0)" % "; ".join(r["gate"].problems)
    return 0, "gate a-pb: open (a-pb0's dump run, p0 and p1 passed)"


def reading(j, P, name):
    """(state, label, text) of a poke row.  p3: True twin, False not twin; p4: True drawn, False empty; None: no reading (void,
    pokes not applied, class not ok, no render-2 line, an overflow) or, for p4, read and matched neither ('other')."""
    if j["void"]:
        return None, "NODATA", "NODATA (%s)" % "; ".join(j["void"])
    if j["row"]["class"] != "ok":
        return None, "class " + j["row"]["class"], "no reading: class %s rc %s (a garbage word may hang the ISP)" % (
            j["row"]["class"], j["row"].get("rc"))
    want = case_q(P, name, "applied").split(";")
    ap = L.kpoke_applied(j["dmesg"])
    if ap != want:
        return None, "NODATA", "NODATA (the kernel log applied %d of the %d pokes: no reading)" % (len([a for a in ap if a in want]), len(want))
    if L.overflowed(j["out"], j["dmesg"]) or L.tool_failed(j["out"]):
        return None, "NODATA", "NODATA (an overflow or tool failure message in the output)"
    t, d = L.tri_counts(j["out"], 2), L.diff_count(j["out"])
    if t is None or d is None:
        return None, "NODATA", "NODATA (no diff or render-2 line)"
    h = L.target_hash(j["out"])
    txt = "diff %d of %d, render 2: %d triangle, %d background, %d other; target hash %s" % (d[0], d[1], t["tri"], t["bg"], t["other"], h)
    if name in P3:
        twin = d == (0, 4096) and t["tri"] == 4096 and t["bg"] == 0 and t["other"] == 0
        rep = case_q(P, name, "target_hash")
        land = case_q(P, name, "par_11_26_in_dump")
        txt += "; twin two-render hash %s %s (reported, not deciding)" % (rep, "equal" if h == rep else "differs")
        txt += "; dump dwords 11-26 %s the poked words" % ("=" if L.words(j["param"], 11, 27) == land else "differ from")
        return twin, ("twin" if twin else "not twin"), txt
    if t["tri"] > 0:
        return True, "drawn", txt + "; dump dword 11 %s" % L.words(j["param"], 11, 12)
    if t["other"] == 0:
        return False, "empty", txt + "; dump dword 11 %s" % L.words(j["param"], 11, 12)
    return None, "other", txt + " (read: 0 triangle with other pixels, matches neither reading)"


def neg(x):
    return None if x is None else not x


def gate_rows(roots, outdir, cases):
    """The four controls of the pokes: a-pb0's three (kept) and p2 (this stage)."""
    d0 = stage_dir(roots, "a-pb0") if roots else None
    ctls, lines = {}, []
    if d0 and os.path.exists(os.path.join(d0, "cases.tsv")):
        _, r0 = pb0_stage(d0)
        ctls.update(r0["verdicts"])
        ref = job(d0, L.read_cases(d0), "pb-d0-te40")
        d0sha = None if ref.get("param") is None else L.sha256(ref["param"])
    else:
        ctls.update({n: "NODATA" for n in PB0})
        d0sha = None
    v, t = ctl(job(outdir, cases, "pb-p2-own11"), P1, "pb-p2-own11", d0sha)
    ctls["pb-p2-own11"] = v
    lines.append("pb-p2-own11: %s: %s" % (v, t))
    return ctls, lines


def pb_stage(outdir, roots=None):
    if roots is None:
        roots = [os.path.dirname(os.path.abspath(outdir))]
    cases = L.read_cases(outdir)
    ctls, lines = gate_rows(roots, outdir, cases)
    res, st, lab = {"pb-p2-own11": ctls["pb-p2-own11"]}, {}, {}
    for n in P3 + P4:
        s, label, t = reading(job(outdir, cases, n), P1, n)
        st[n], lab[n] = s, label
        res[n] = label
        lines.append("%s: %s: %s" % (n, label, t))
    p3 = K.combine([st[n] for n in P3])
    p4 = K.combine([st[n] for n in P4])
    # scorekit's replicate words, named by what each row reads (p3: is it the twin's picture; p4: is anything drawn)
    name3 = {"held": "twin", "refuted": "not twin"}.get(p3, p3)
    name4 = {"held": "drawn", "refuted": "empty"}.get(p4, p4)
    rows_old = [st[P3[0]], st[P3[1]], neg(st[P4[0]]), neg(st[P4[1]])]
    rows_field = [neg(st[P3[0]]), neg(st[P3[1]]), st[P4[0]], st[P4[1]]]
    g = K.gate(ctls)
    others = [n for n in P3 + P4 if lab[n] == "other"]
    void = [n for n in P3 + P4 if st[n] is None and lab[n] != "other"]
    if not g.ok:
        q = K.headline("Q285", ctls, rows_old)
    elif p3 == "held" and p4 == "refuted":
        q = K.headline("H-OLD: the 3D reads render 1's object in the old layout (p3, the twin's dwords 11-26, gives the twin's picture; "
                       "p4, dword 11 = 0xffffffff, draws nothing)", ctls, rows_old)
    elif p3 == "refuted" and p4 == "held":
        q = K.headline("H-FIELD: dword 11 is a field the 3D uses (p4 draws pixels; p3's old-layout words do not give the twin's "
                       "picture)", ctls, rows_field)
    elif p3 == "refuted" and p4 == "refuted":
        q = ("cannot tell: p3 and p4 both read (%d of 4 rows decided) and both empty or not the twin's: the cause is elsewhere; "
             "park under Q030" % K.tally(rows_old).decided)
    elif p3 == "held" and p4 == "held":
        q = ("cannot tell: both effects (p3 gives the twin's picture and p4 draws; %d of 4 rows decided): the data do not separate "
             "H-OLD from H-FIELD" % K.tally(rows_old).decided)
    else:
        why = ["p3 %s" % name3, "p4 %s" % name4]
        if others:
            why.append("%s read and matched no hypothesis" % ", ".join(others))
        if void:
            why.append("no reading in %s" % ", ".join(void))
        q = "cannot tell: %s (%d of 4 rows decided)" % ("; ".join(why), K.tally(rows_old).decided)
    if others and "matched no hypothesis" not in q:
        q += "; %s read and matched no hypothesis" % ", ".join(others)
    return lines, {"verdicts": res, "controls": ctls, "q285": q, "summary": "a-pb: p3 %s, p4 %s; Q285: %s" % (name3, name4, q)}


def verdict(roots):
    d = stage_dir(roots, "a-pb")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return "SUMMARY: Q285: not run (no kept a-pb)"
    _, r = pb_stage(d, roots)
    return "SUMMARY: Q285: %s" % r["q285"]


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
    if st == "a-pb0":
        lines, r = pb0_stage(outdir)
    elif st == "a-pb":
        lines, r = pb_stage(outdir)
    else:
        print("unknown stage %s" % st)
        return 2
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
