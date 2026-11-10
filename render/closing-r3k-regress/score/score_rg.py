#!/usr/bin/env python3
"""R3K-regress scorer (module-regression session), written and frozen before the run.

  score_rg.py STAGE OUTDIR       one stage (rg-ctl, rg-pb): a line a row and one SUMMARY
  score_rg.py verdict ROOT...    both SUMMARY lines from the kept stages (ROOT: out/ATT; each stage from the first root that has it)
  score_rg.py gate STAGE ROOT... exit 0 if rg-pb may run (rg-ctl kept, every row run, no fault-class event), else 1

A row is scored against the frozen quantities of each model of predictions/STAGE.tsv: every quantity must be equal, a quantity the
new run lacks is a mismatch.  rg-ctl has one model (OLD, the old module's kept value).  rg-pb has H-OLD (E728's values) for the
E728-shape rows and H-NEW (K2's k-pb0 values) for the -n 2 --geometry 1 rows, with E728's hash, diff and dwords as H-OLD there.
Refuses to score unless run/freeze_k.sh verify passes.  Missing or empty data, an rc or class that is not a result, a fault latched
before the job (snap 0) and a tool output that is empty are NODATA, never a verdict.  Held-out, replicate and control rows are
tallied apart.  Everything is searched in the WHOLE tool output.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klib as L  # noqa: E402
import rlib  # noqa: E402

KP = L.KP
PRED = {}


def load_preds(stage):
    """{case: {"set": s, "models": {model: {q: v}}}} from predictions/STAGE.tsv (6 columns)."""
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        if not ln.strip():
            continue
        case, q, v, m, st, src = ln.split("\t")
        e = out.setdefault(case, {"set": st, "models": {}, "source": src})
        e["models"].setdefault(m, {})[q] = v
    return out


def preds():
    for st in ("rg-ctl", "rg-pb"):
        PRED[st] = load_preds(st)


def dump_file(outdir, name, kind):
    """The kept dump of a job (tri.tadata.bin.gz, NAME__0.param.bin.gz ...): the single file NAME.*kind.bin.gz, or None."""
    f = sorted(glob.glob(os.path.join(outdir, "%s.*%s.bin.gz" % (name, kind))))
    return L.read_bytes(f[0]) if len(f) == 1 else None


def job(outdir, cases, name, want_dumps):
    j = {"name": name, "void": []}
    row = (cases or {}).get(name)
    if row is None:
        j["void"].append("no cases.tsv row (not run)")
        return j
    j["row"] = row
    if not re.fullmatch(r"-?\d+", row.get("rc", "")):
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
    s0 = L.parse_regs(L.read_text(os.path.join(outdir, name + ".snap0.regs.gz")))
    if s0 is not None and s0[L.REG_INT_STAT] & L.FAULT_REQ:
        j["void"].append("a fault latched before the job (snap 0 CR_BIF_INT_STAT %#x)" % s0[L.REG_INT_STAT])
    j["tadata"] = dump_file(outdir, name, "tadata") if want_dumps else None
    j["param"] = dump_file(outdir, name, "param") if want_dumps else None
    if want_dumps and (j["tadata"] is None or j["param"] is None):
        j["void"].append("dump missing")
    if not j["void"]:
        j["obs"] = rlib.observe(j["out"], j["rc"], j["tadata"], j["param"])
    return j


def compare(obs, want):
    """[(quantity, got, frozen)] of the differences."""
    return [(q, obs.get(q), v) for q, v in want.items() if obs.get(q) != v]


def show(d):
    s = "; ".join("%s %s, frozen %s" % (q, (g if g is None or len(g) < 60 else g[:57] + "..."), (f if len(f) < 60 else f[:57] + "..."))
                  for q, g, f in d[:4])
    return s + ("; +%d more" % (len(d) - 4) if len(d) > 4 else "")


def wants_dumps(entry):
    return any("tadata_sha256" in m for m in entry["models"].values())


def row_result(outdir, cases, stage, name):
    """(verdict, text, obs): PASS / FAIL / NODATA for one-model rows; the model name (or OTHER) for a row with two models."""
    e = PRED[stage][name]
    j = job(outdir, cases, name, wants_dumps(e))
    if j["void"]:
        return "NODATA", "NODATA (%s)" % "; ".join(j["void"]), None
    cls = j["row"]["class"]
    if cls != "ok" or rlib.has_fault_text(j["out"], j["dmesg"]):
        return "FAULT", "class %s rc %s (a fault-class event)" % (cls, j["row"].get("rc")), j["obs"]
    models = e["models"]
    if len(models) == 1:
        (m, want), = models.items()
        d = compare(j["obs"], want)
        return ("PASS", "as frozen (%s)" % m, j["obs"]) if not d else ("FAIL", show(d), j["obs"])
    matched = [m for m, want in models.items() if not compare(j["obs"], want)]
    if len(matched) == 1:
        return matched[0], "matches %s: %s" % (matched[0], ", ".join("%s %s" % (q, j["obs"].get(q)) for q in ("target_hash", "diff"))), j["obs"]
    first = sorted(models)[0]
    return "OTHER", "matches neither %s: %s" % (" nor ".join(sorted(models)), show(compare(j["obs"], models[first]))), j["obs"]


def stage_rows(stage):
    return list(PRED[stage])


def ctl_stage(outdir):
    cases = L.read_cases(outdir)
    lines, res, why = [], {}, {}
    for n in stage_rows("rg-ctl"):
        v, t, _ = row_result(outdir, cases, "rg-ctl", n)
        res[n], why[n] = v, t
        lines.append("%s [%s]: %s: %s" % (n, PRED["rg-ctl"][n]["set"], v, t))
    tally = {}
    for n, v in res.items():
        tally.setdefault(PRED["rg-ctl"][n]["set"], {}).setdefault(v, []).append(n)
    parts = []
    for s in ("control", "heldout"):
        d = tally.get(s, {})
        parts.append("%s %d PASS of %d" % (s, len(d.get("PASS", [])), sum(len(x) for x in d.values())))
    bad = {n: v for n, v in res.items() if v != "PASS"}
    s = "rg-ctl: %s; %s" % ("; ".join(parts), ("NOT PASS: %s" % bad) if bad else "every row reproduced its old value (no module regression in these classes)")
    return lines, {"verdicts": res, "summary": s}


E_HELD = ("pb-e40-m2-64a", "pb-e40-m2-64b", "pb-e40-m2-64c", "pb-e80-m2-64", "pb-ec0-m2-64", "pb-e40-m0-64", "pb-e40-m2-128")
E_CTL = ("pb-e20-m2-64", "pb-ee0-m2-64")
N_ROWS = ("pb-n40-a", "pb-n40-b", "pb-n40-c", "pb-n60")


def pb_stage(outdir, roots=None):
    cases = L.read_cases(outdir)
    res, obs, lines = {}, {}, []
    for n in stage_rows("rg-pb"):
        v, t, o = row_result(outdir, cases, "rg-pb", n)
        res[n], obs[n] = v, o
        lines.append("%s [%s]: %s: %s" % (n, PRED["rg-pb"][n]["set"], v, t))
    lines += ctl_gate_line(roots)
    e_ok = [n for n in E_HELD if res.get(n) == "PASS"]
    e_nd = [n for n in E_HELD if res.get(n) in ("NODATA", "FAULT")]
    e_bad = [n for n in E_HELD if res.get(n) == "FAIL"]
    c_ok = all(res.get(n) == "PASS" for n in E_CTL)
    n_new = [n for n in N_ROWS[:3] if res.get(n) == "H-NEW"]
    n_nd = [n for n in N_ROWS if res.get(n) in ("NODATA", "FAULT")]
    n40 = [n for n in N_ROWS[:3] if obs.get(n)]
    stable_n = len({obs[n].get("target_hash") for n in n40}) == 1 and len(n40) == 3
    # the three TE 0x40 E728-shape runs against each other
    e40 = [obs[n] for n in E_HELD[:3] if obs.get(n)]
    stable_e = len(e40) == 3 and len({o.get("target_hash") for o in e40}) == 1 and len({o.get("param_sha256") for o in e40}) == 1
    if e_nd or n_nd:
        q = "cannot tell: NODATA or a fault-class event in %s" % (e_nd + n_nd)
    elif len(e_ok) == len(E_HELD) and c_ok and len(n_new) == 3:
        q = ("H-SHAPE: the module did not change E728's image (7 of 7 E728-shape rows reproduce E728's hash, diff, dwords and dump "
             "sha256s, both E728 controls too); k-pb0's value is reproducible (3 of 3 -n 2 --geometry 1 rows give 0x8ea26cdfee74a325) "
             "and belongs to that job shape, not to the module [infer: the shape differs from E728's, the tool prints render 2 in "
             "other colours]")
    elif len(e_ok) == len(E_HELD) and c_ok:
        q = ("E728-shape rows reproduce E728 (no module change there) but k-pb0's value is NOT reproducible in the -n 2 --geometry 1 "
             "rows (%d of 3 as H-NEW; row results %s): the k-pb0 difference is not stable" % (len(n_new), {n: res[n] for n in N_ROWS[:3]}))
    elif e_bad and stable_e and c_ok:
        d = obs[E_HELD[0]]
        q = ("H-MOD: the new module (or the tool: E728 ran ~/sgxfive-test-1138b) changed E728's image: the E728-shape TE 0x40 rows are "
             "stable run to run and give hash %s (E728 0xfc5ff15e0434a325), diff %s; %d of 7 held-out rows differ from E728; the TE 0x20 "
             "and 0xe0 controls reproduce E728; the -n 2 --geometry 1 rows: %d of 3 as H-NEW" % (
                 d.get("target_hash"), d.get("diff"), len(e_bad), len(n_new)))
    elif e_bad and not stable_e:
        q = "not reproducible: the three E728-shape TE 0x40 runs disagree with each other (hash or parameter-buffer sha256)"
    elif e_bad:
        q = ("E728-shape rows differ from E728 (%d of 7: %s) and a control of E728 (TE 0x20/0xe0) failed too %s: the pinned tool or the "
             "module differs from E728's in general, not specific to TE 0x40" % (len(e_bad), e_bad, {n: res[n] for n in E_CTL}))
    else:
        q = "cannot tell: %s" % res
    s = "rg-pb: E728-shape %d of 7 held-out rows as H-OLD, controls %s; -n 2 --geometry 1: %d of 3 as H-NEW, twin row %s; %s" % (
        len(e_ok), {n: res[n] for n in E_CTL}, len(n_new), res.get("pb-n60"), q)
    return lines, {"verdicts": res, "q": q, "summary": s}


def stage_dir(roots, stage):
    for r in roots:
        if os.path.exists(os.path.join(r, stage, "cases.tsv")):
            return os.path.join(r, stage)
    return os.path.join(roots[0], stage) if roots else stage


def ctl_gate_line(roots):
    if not roots:
        return []
    code, msg = gate("rg-pb", roots)
    return ["gate: %s" % msg]


def gate(stage, roots):
    """(code, message): rg-pb needs rg-ctl kept with every row run and no fault-class event (a wrong image does not close it)."""
    if stage != "rg-pb":
        return 0, "gate %s: no prerequisite" % stage
    d = stage_dir(roots, "rg-ctl")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate rg-pb: closed: no rg-ctl stage was kept (rerun: run/k.sh --only rg-ctl)"
    cases = L.read_cases(d) or {}
    want = list(PRED["rg-ctl"])
    miss = [n for n in want if n not in cases]
    bad = [n for n in want if n in cases and cases[n].get("class") != "ok"]
    if miss or bad:
        return 1, "gate rg-pb: closed: rg-ctl rows not run %s, rows with a class other than ok %s (rerun: run/k.sh --only rg-ctl)" % (miss, bad)
    return 0, "gate rg-pb: open (every rg-ctl row ran, class ok; image mismatches are results, not a closed gate)"


def verdict(roots):
    out = []
    for st, fn in (("rg-ctl", ctl_stage), ("rg-pb", None)):
        d = stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept %s)" % (st, st))
            continue
        _, r = ctl_stage(d) if st == "rg-ctl" else pb_stage(d, roots)
        out.append("SUMMARY: %s" % r["summary"])
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
    if st == "rg-ctl":
        lines, r = ctl_stage(outdir)
    elif st == "rg-pb":
        lines, r = pb_stage(outdir, [os.path.dirname(os.path.abspath(outdir))])
    else:
        print("unknown stage %s" % st)
        return 2
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
