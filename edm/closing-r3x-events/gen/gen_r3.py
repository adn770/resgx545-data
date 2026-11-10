#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_r3.py (R3x-events): write everything the session runs from, in this directory's parent (closing3/r3x-events/).

R3x-events is laptop session L3 of the question-closing pass, round 3 (decisions R3-E1 to R3-E9 in plans/resgx545-question-closing.md;
proposal closing3/events/exp-events-r3.md; readings closing3/events/readings/readings-r3.md).  It is a copy of the framework of
closing2/r3-events (kernel-log markers, kept-output gates, scorer layout, mock) with new blobs, rows and scorers.  NOT RUN.  Stages, in
run order (stage f and the Q290 rows are NOT here: they follow the kernel batch):

  h   what a running task looks like: ring_hold.blob byte for byte (S2b), H0 (no hold) and H1 (signature inside a 90 ms hold)
  c   single words that should keep the tick: alias2.s, rows C0-C5 (C1 = A7)
  e   the end of a pass: ring_end.s, rows E0, X1 (slot 2), X20, B3 (B3 = the user's, LAST, reset at once)
  d   E537's word: alias2.s, rows D0-D4 (D3 = A8, LAST; D4 only if D3 kept the tick)

  asm/alias2.s, asm/ring_end.s, asm/ring_hold.s   the task sources; bins/*.blob (the landed verifier accepts them)
  tables/STAGE.json   the job tables;   predictions/STAGE.tsv   the frozen predictions (case quantity value model set)

Run with the scratch venv:  ../../closing/pixel-faults/.venv/bin/python gen/gen_r3.py   (then run/freeze_r3.sh freeze)
"""
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402
import r3blobs as B  # noqa: E402

STAGES = L.STAGES
HOLD_SHA = "fa0f79dbb5864187516febf9c96f6ceea944e5abf6ae69b5acbeb9ac8a0ac168"
N90 = L.n_for_ticks(L.K7_HOLD_TICKS)
SPEC = L.ROW_SPEC


# ---- blobs ---------------------------------------------------------------------------------------------------------------
def build_blobs():
    info = {}
    for name, arm in (("alias2", B.ARM_ALIAS), ("ring_end", B.ARM_RING)):
        text, blob = B.build(name)
        (R3 / "asm" / f"{name}.s").write_text(text)
        (R3 / "bins" / f"{name}.blob").write_bytes(blob)
        info[name] = B.info_of(name, text, blob, arm)
    hold = (R3 / "bins" / "ring_hold.blob").read_bytes()
    assert hashlib.sha256(hold).hexdigest() == HOLD_SHA, "ring_hold.blob is not S2b's"
    hp = B.fwtask.parse_blob(hold)
    src = (R3 / "asm" / "ring_hold.s").read_text()
    info["ring_hold"] = {"insns": len(hp.words), "bytes": len(hold), "patches": len(hp.patches), "entries": hp.entries,
                         "sha256": HOLD_SHA, "arm": B.ARM_RING, "sa_writes": sorted({w for w in B.all_writes(src) if w.startswith("sa")}),
                         "str": 0, "ldr": ["#81"], "note": "byte-identical to closing/s2b/bins/ring_hold.blob"}
    (R3 / "bins" / "blobs.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


# ---- tables --------------------------------------------------------------------------------------------------------------
def label_of(spec, k):
    """control and fit rows keep their label on every rep; a held-out row's first rep is held out, the others replicate."""
    lab = spec["label"]
    return lab if lab in ("control", "fit") or k == 0 else "replicate"


def jobs_of(stage, make):
    jobs = []
    for row in L.ROW_ORDER[stage]:
        spec = SPEC[stage][row]
        for k in range(spec["reps"]):
            j = {"name": L.rep_name(row, k), "set": label_of(spec, k), "row": row, "runid": 0x6400 + 0x100 * STAGES.index(stage) + len(jobs) + 1}
            j.update(make(row, spec, k))
            if spec.get("run_if"):
                j["run_if"] = spec["run_if"]
            elif spec.get("rep_if") and k > 0:
                j["run_if"] = spec["rep_if"]
            jobs.append(j)
    return jobs


def make_h(row, spec, k):
    return {"op": "holdsig", "hold": spec["hold"], "n": N90 if spec["hold"] else 0, "window": 2, "sig_ms": [20, 60], "status_ms": 40,
            "open_ms": 160, "d_reads": 20, "status_reads": 20 if not spec["hold"] else 1}


def make_alias2(row, spec, k):
    cmd = spec["cmd"]
    j = {"op": "alias2", "cmd": cmd, "sa": L.CMD_SA2.get(cmd, []), "w65": spec.get("w65"), "npass": spec.get("npass", 0),
         "marker": 0, "ri": [0, 0, 0, 0], "w63": 0, "w64": 0, "restore63": False, "read_1200": False, "d_reads": 20}
    if cmd == L.CMD_E537:
        e = L.E537
        j.update({"w65": {"lit": e["sa65"]}, "w64": e["sa64"], "w63": e["sa63"], "marker": e["sa63"],
                  "ri": [e["r20"], e["r21"], e["i0"], e["i1"]], "restore63": True})
    return j


def make_e(row, spec, k):
    return {"op": "act", "kind": spec["kind"], "act": spec["act"], "count": spec["count"], "trigger": spec["trigger"], "window": 2,
            "pre_ms": 3, "open_ms": spec["open_ms"], "d_reads": 20}


MAKE = {"h": make_h, "c": make_alias2, "e": make_e, "d": make_alias2}


def table(stage):
    rows_not_run = {"h": [], "c": ["stage f and Q290 rows (after the kernel batch)"],
                    "e": ["stage f (the shared exit itself: after the kernel batch)"], "d": []}[stage]
    return {"stage": stage, "blob": L.BLOB_OF[stage], "arm": L.ARM_OF[stage], "stop_budget": L.STOP_BUDGET[stage],
            "per_job_reset": L.PER_JOB_RESET[stage], "jobs": jobs_of(stage, MAKE[stage]), "needs": L.GATE_OF.get(stage),
            "rows_not_run": rows_not_run}


# ---- predictions ---------------------------------------------------------------------------------------------------------
NOHANDLER = "E155 no handler bit"
BIT19 = "E154 bit 19 posts nothing"
E792 = "E792 A4"


def preds_h(t):
    P = []
    for j in t["jobs"]:
        n, s = j["name"], j["set"]
        if not j["hold"]:
            P += [(n, "idle", "yes", "control (idle EDM)", s), (n, "d0_modal", "yes", "control (D0 one modal value)", s)]
        else:
            P += [(n, "hold_band", "yes", "S2 run 3 knob", "control"),
                  (n, "elements", "all", "H-NOTENDED", s), (n, "elements", "some_differ", "H-REARM", s),
                  (n, "d_vs_d0", "D0 or D0+1", "H-NOTENDED", s)]
    return P


def kept_marks(P, n, s, model, rmw="0", dw14="0"):
    P += [(n, "read_minus_write", rmw, model, s), (n, "dword14", dw14, model, s)]


def preds_c(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "C0":
            for q, v in (("pclink", "0x98"), ("p1", "1"), ("sa64", "2"), ("sa65", "K<<24"), ("sa63", "0")):
                P.append((n, q, v, "E791 A0", s))
            P.append((n, "kept", "yes", "E791 A0", s))
            continue
        model = {"C1": NOHANDLER, "C2": NOHANDLER, "C3": NOHANDLER, "C4": BIT19, "C5": E792}[row]
        P.append((n, "kept", "yes", model, s))
        if row in ("C1", "C2", "C3", "C4"):
            P += [(n, "next_pclink", "0x98", model, s), (n, "next_sa65", "K<<24", model, s)]
        if row == "C1":
            kept_marks(P, n, s, model)
        if row == "C5":
            P += [(n, "pclink", "6", E792, s), (n, "d12_delta", "-50+-8", E792, s), (n, "d_shift", "D0+50+-1", E792, s)]
        P.append((n, "p3_answered", "no", "H-NOTENDED", s))
        P.append((n, "p3_answered", "yes", "H-REARM", s))
    return P


def preds_e(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "E0":
            P += [(n, "entries", "14+-2", "control (R3 b0)", s), (n, "grid", "yes", "control (R3 b0)", s),
                  (n, "acted", "0", "control", s)]
        elif row == "X1":
            P += [(n, "acted", "1", "design", s),
                  (n, "kept", "yes", "H-EXIT", s), (n, "next_gap", "25000+-50", "H-EXIT", s), (n, "flag4_logged", "yes", "H-EXIT", s),
                  (n, "kept", "no", "H-BODY", s), (n, "kept", "yes", "H-TICKONLY", s)]
            kept_marks(P, n, s, "H-BODY")
            P += [(n, "sig_busy", "yes", "H-BODY", s), (n, "p3_answered", "no", "H-NOTENDED", s), (n, "p3_answered", "yes", "H-REARM", s)]
        elif row == "X20":
            P += [(n, "acted", "20", "design", s), (n, "kept", "yes", "H-EXIT", s), (n, "d12_delta", "-20+-8", "H-EXIT", s)]
            P += [(n, "p3_answered", "no", "H-NOTENDED", s), (n, "p3_answered", "yes", "H-REARM", s)]
        else:          # B3: the kick pass's own end; its own kick is the probe (no P3)
            P += [(n, "acted", "1", "design", s),
                  (n, "kept", "no", "H-EXIT", s), (n, "sig_busy", "yes", "H-EXIT", s), (n, "miscinfo_answered", "no", "H-EXIT", s),
                  (n, "read_minus_write", "-1", "H-EXIT", s), (n, "kick_entry", "one, flag 3, nothing after", "H-EXIT", s),
                  (n, "kept", "no", "H-BODY", s), (n, "sig_busy", "yes", "H-BODY", s), (n, "miscinfo_answered", "no", "H-BODY", s),
                  (n, "read_minus_write", "-1", "H-BODY", s), (n, "kick_entry", "one, flag 3, nothing after", "H-BODY", s),
                  (n, "kept", "yes", "H-TICKONLY", s), (n, "grid", "yes", "H-TICKONLY", s),
                  (n, "read_minus_write", "-1", "H-TICKONLY", s), (n, "miscinfo_answered", "no", "H-TICKONLY", s)]
    return P


def preds_d(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "D0":
            for q, v in (("pclink", "0x98"), ("p1", "1"), ("sa64", "2"), ("sa65", "K<<24"), ("sa63", "0")):
                P.append((n, q, v, "E791 A0 (as C0)", s))
            P.append((n, "kept", "yes", "E791 A0 (as C0)", s))
            continue
        if row == "D1":
            P += [(n, "kept", "yes", "H-CCB", s), (n, "kept", "no", "H-HANDLER", s), (n, "kept", "yes", "H-ONCE", s)]
            kept_marks(P, n, s, "H-HANDLER")
        elif row == "D2":
            P += [(n, "kept", "no", "H-CCB", s), (n, "read_minus_write", "1", "H-CCB", s), (n, "dword14", "0xad002600", "H-CCB", s),
                  (n, "sig_busy", "yes", "H-CCB", s), (n, "kept", "yes", "H-HANDLER", s), (n, "kept", "yes", "H-ONCE", s)]
        elif row == "D3":
            P += [(n, "kept", "no", "H-CCB", s), (n, "read_minus_write", "1", "H-CCB", s), (n, "dword14", "0xad002600", "H-CCB", s),
                  (n, "sig_busy", "yes", "H-CCB", s),
                  (n, "kept", "no", "H-HANDLER", s), (n, "dword14", "0", "H-HANDLER", s),
                  (n, "kept", "yes", "H-ONCE", s)]
        else:          # D4
            P += [(n, "kept", "yes", "H-ONCE", s)]
        P += [(n, "p3_answered", "no", "H-NOTENDED", s), (n, "p3_answered", "yes", "H-REARM", s)]
    return P


PREDS = {"h": preds_h, "c": preds_c, "e": preds_e, "d": preds_d}


# ---- writing -------------------------------------------------------------------------------------------------------------
def write_preds(stage, rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R3 / "predictions" / f"{stage}.tsv").write_text("\n".join(out) + "\n")


def tables_md(info, tabs):
    L_ = ["# R3x-events job tables (generated by gen/gen_r3.py; the JSON in tables/ is what runs)", "",
          f"n for the 90-tick hold = ((90 + 0.5) * 25000 - 82) / 1.5 = {N90} (S2b's e4l, hold = 1.5 n + 15 units, about 90.5 ms).", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | str | ldr |", "|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | {', '.join(i['sa_writes']) or 'none'} | "
                  f"{i['str']} | {', '.join(i['ldr']) or 'none'} |")
    L_ += ["", "alias2.s: sa writes by command (the guard compares the assembled code with this): "
           + "; ".join(f"cmd {k} {v or 'none'}" for k, v in sorted(info["alias2"]["cmd_sa"].items(), key=lambda x: int(x[0]))), ""]
    for st in STAGES:
        t = tabs[st]
        L_ += [f"## stage {st}: blob {t['blob']}, needs {t['needs']}, stop budget {t['stop_budget']} (stop number {t['stop_budget'] + 1} ends the stage), "
               f"reset + arm each job: {t['per_job_reset']}" + (f"; not run: {', '.join(t['rows_not_run'])}" if t["rows_not_run"] else ""), ""]
        if st == "h":
            L_ += ["| job | set | row | hold | n | signatures at ms | status reads |", "|---|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['hold']} | {j['n']} | {j['sig_ms']} | {j['status_reads']} |")
        elif st in ("c", "d"):
            L_ += ["| job | set | row | cmd | sa writes | w65 | npass | run if |", "|---|---|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['cmd']} | {', '.join(j['sa']) or 'none'} | {j['w65'] or ''} | "
                          f"{j['npass'] or ''} | {j.get('run_if') or ''} |")
        else:
            L_ += ["| job | set | row | kind | act | count | trigger | open ms | run if |", "|---|---|---|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['kind']} | {j['act']} | {j['count']} | {j['trigger']} | "
                          f"{j['open_ms']} | {j.get('run_if') or ''} |")
        L_.append("")
    (R3 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    info = build_blobs()
    tabs = {st: table(st) for st in STAGES}
    for st in STAGES:
        (R3 / "tables" / f"{st}.json").write_text(json.dumps(tabs[st], indent=1, sort_keys=True) + "\n")
        write_preds(st, PREDS[st](tabs[st]))
    (R3 / "stages.txt").write_text("\n".join(STAGES) + "\n")
    tables_md(info, tabs)
    print("wrote", ", ".join(f"{k}: {v['insns']} insns" for k, v in info.items()), "; tables", ", ".join(STAGES),
          "; jobs", {st: len(tabs[st]["jobs"]) for st in STAGES})


if __name__ == "__main__":
    main()
