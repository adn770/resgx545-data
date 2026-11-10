#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_r3.py: write everything R3-events runs from, in this directory's parent (closing2/r3-events/).

R3-events is laptop session R3 of the question-closing pass, round 2 (decisions R2-1, R2-2, R2-3 and R2-17 in
plans/resgx545-question-closing.md; proposal closing2/exp-events.md sections 0 to 2).  It is a copy of the framework of
closing2/r1-events (kernel-log markers, kept-output gates, scorer layout, mock) and closing/s2b (ring_hold, the 90-tick hold).
NOT RUN.  Stages, in run order:

  a    Q152 stage A, rows A0-A6 (alias.s, one entry; A7 and A8 are NOT here)
  b    Q152 stage B, rows B0, B1, B2 (ring_skip.s; B2 only if B1 kept the tick; B3 is NOT here)
  k7   Q290 K7 (ring_hold.blob of S2b, byte for byte, 90-tick hold, window 2; two kicks inside it; LAST, reset after)

  asm/alias.s, asm/ring_skip.s, asm/ring_hold.s   the three task sources; bins/*.blob (the landed verifier accepts them)
  tables/STAGE.json     the job tables;   predictions/STAGE.tsv   the frozen predictions (case quantity value model set)

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

STAGES = ["a", "b", "k7"]
HOLD_SHA = "fa0f79dbb5864187516febf9c96f6ceea944e5abf6ae69b5acbeb9ac8a0ac168"
N90 = L.n_for_ticks(L.K7_HOLD_TICKS)
MODELS_A = {"H-ALIAS": "all the closed task sees passes through sa64 and sa65", "H-63": "sa63 stops it",
            "H-P11": "p0 = p1 = 1 at the tail call with r and i written stops it"}


def marker(name, salt=""):
    """A frozen marker for a job: not 0, not a tick's pa1 (0x02000000), bit 31 set, from the job's name."""
    h = int(hashlib.sha256((salt + name).encode()).hexdigest()[:8], 16) | 0x80000000
    return h if h != 0x02000000 else h ^ 0x10


# ---- blobs ---------------------------------------------------------------------------------------------------------------
def build_blobs():
    info = {}
    for name, arm in (("alias", B.ARM_ALIAS), ("ring_skip", B.ARM_RING)):
        text, blob = B.build("alias" if name == "alias" else "skip")
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


# ---- stage a -------------------------------------------------------------------------------------------------------------
# row -> (command, repeats, label of its rows)
A_ROWS = [("A0", 0, 2), ("A1", L.CMD_A1, 3), ("A2", L.CMD_A2, 3), ("A3", L.CMD_A3, 3), ("A4", L.CMD_A4, 3), ("A5", L.CMD_A5, 3),
          ("A6", L.CMD_A6, 2)]


def rep_name(row, k):
    return row.lower() + ("" if k == 0 else f"-r{k + 1}")


def table_a():
    jobs = []
    for row, cmd, reps in A_ROWS:
        for k in range(reps):
            n = rep_name(row, k)
            j = {"name": n, "set": "control" if row == "A0" else "heldout" if k == 0 else "replicate", "op": "alias", "row": row,
                 "cmd": cmd, "sa": L.CMD_SA.get(cmd, []), "marker": marker(n) if cmd in (L.CMD_A1, L.CMD_A3) else 0,
                 "ri": [marker(n, f"ri{i}") for i in range(4)] if cmd == L.CMD_A6 else [0, 0, 0, 0],
                 "read_1200": row == "A1", "restore63": row == "A1", "runid": 0x6100 + len(jobs) + 1}
            jobs.append(j)
    return {"stage": "a", "blob": "alias", "arm": B.ARM_ALIAS, "stop_budget": 1, "jobs": jobs,
            "needs": None, "rows_not_run": ["A7 (user: sa65 | 1<<23)", "A8 (user: E537's cmd 4 markers)"]}


def preds_a(t):
    P = []

    def add(case, q, v, model, s):
        P.append((case, q, v, model, s))
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "A0":
            for q, v in (("pclink", "0x98"), ("p1", "1"), ("sa64", "2"), ("sa65", "K<<24"), ("sa63", "0")):
                add(n, q, v, "E536/E537 controls", "fit")
            add(n, "kept", "yes", "controls", "fit")
            continue
        kept = {"A1": {"H-ALIAS": "yes", "H-63": "no", "H-P11": "yes"},
                "A2": {"H-ALIAS": "yes", "H-63": "yes", "H-P11": "yes"},
                "A3": {"H-ALIAS": "yes", "H-63": "yes", "H-P11": "yes"},
                "A4": {"H-ALIAS": "yes", "H-63": "yes", "H-P11": "yes"},
                "A5": {"H-ALIAS": "yes", "H-63": "yes", "H-P11": "yes"},
                "A6": {"H-ALIAS": "yes", "H-63": "yes", "H-P11": "no"}}[row]
        for m, v in kept.items():
            add(n, "kept", v, m, s)
        if row == "A1":
            add(n, "marker_persists_1200ms", "yes", "H-ALIAS, H-P11", s)
        if row == "A2":
            add(n, "pclink", "0x98", "H-ALIAS", s)
            add(n, "p1", "1", "H-ALIAS", s)
        if row == "A4":
            add(n, "pclink", "6", "H-ALIAS", s)
            add(n, "p1", "0", "H-ALIAS", s)
            add(n, "d12_delta", "passes-1", "H-ALIAS", s)
        if row == "A5":
            add(n, "pclink", "0x98", "H-ALIAS", s)
            add(n, "p1", "1", "H-ALIAS", s)
    return P


# ---- stage b -------------------------------------------------------------------------------------------------------------
B_ROWS = [("B0", 0, 3, "control"), ("B1", 1, 3, "heldout"), ("B2", 5, 2, "heldout")]


def table_b():
    jobs = []
    for row, skip, reps, lab in B_ROWS:
        for k in range(reps):
            n = rep_name(row, k)
            jobs.append({"name": n, "set": lab if k == 0 else "replicate", "op": "skip", "row": row, "skip": skip, "window": 2,
                         "pre_ms": 3, "open_ms": 20, "runid": 0x6200 + len(jobs) + 1,
                         "run_if": "b1_all_kept" if row == "B2" else None})
    return {"stage": "b", "blob": "ring_skip", "arm": B.ARM_RING, "stop_budget": 1, "jobs": jobs, "needs": "a",
            "rows_not_run": ["B3 (user: skip on a kick pass)"]}


def preds_b(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "B0":
            for q, v in (("kept", "yes"), ("skipped", "0"), ("grid", "yes")):
                P.append((n, q, v, "control (E746, R1 k)", "control" if s == "control" else "replicate"))
            continue
        N = j["skip"]
        P += [(n, "skipped", str(N), "design", s), (n, "kept", "yes", "H-FREE", s), (n, "kept", "no", "H-STOP", s),
              (n, "next_gap", "25000+-50", "H-FREE", s), (n, "d12_delta", f"passes-{N}", "H-FREE", s)]
        if row == "B2":
            P.append((n, "grid_kept", "yes", "H-FREE", s))
    return P


# ---- stage k7 ------------------------------------------------------------------------------------------------------------
def table_k7():
    jobs = [{"name": "k7-ctl", "set": "control", "op": "hold", "row": "K7", "kick": "none", "n": N90, "window": 2, "open_ms": 160,
             "trigger_after_ms": 3, "runid": 0x6301},
            {"name": "k7-one", "set": "replicate", "op": "hold", "row": "K7", "kick": "misc1", "n": N90, "window": 2,
             "open_ms": 160, "trigger_after_ms": 3, "runid": 0x6302}]
    for k in range(3):
        jobs.append({"name": "k7" if k == 0 else f"k7-r{k + 1}", "set": "heldout" if k == 0 else "replicate", "op": "hold",
                     "row": "K7", "kick": "xfer2", "n": N90, "window": 2, "open_ms": 160, "trigger_after_ms": 3,
                     "runid": 0x6303 + k})
    return {"stage": "k7", "blob": "ring_hold", "arm": B.ARM_RING, "stop_budget": 1, "jobs": jobs, "needs": "b", "rows_not_run": []}


def preds_k7(t):
    P = []
    for j in t["jobs"]:
        n, s = j["name"], j["set"]
        if j["kick"] == "none":
            P += [(n, "kick_entries", "0", "S2b ctl90", "fit"), (n, "burst", "4", "S2b e4l, ctl90", "fit"),
                  (n, "hold_band", "yes", "S2 run 3 knob", "fit")]
        elif j["kick"] == "misc1":
            P += [(n, "kick_entries", "1", "S2b kick90 (3 of 3 QUEUED)", "fit"), (n, "ticks_after_K", "K0+1", "E746, S2b kick90", "fit"),
                  (n, "ccbctl0", "K0+1", "E746", "fit"), (n, "hold_band", "yes", "S2 run 3 knob", "fit")]
        else:
            P += [(n, "kick_entries", "2", "H-EACH", s), (n, "kick_K", "K0,K0+1", "H-EACH", s),
                  (n, "ticks_after_K", "K0+2", "H-EACH", s), (n, "ccbctl0", "K0+2", "H-EACH", s), (n, "read_ok", "yes", "H-EACH", s),
                  (n, "kick_entries", "1", "H-MERGE", s), (n, "read_ok", "no", "H-MERGE", s),
                  (n, "hold_band", "yes", "S2 run 3 knob", "control")]
    return P


# ---- writing -------------------------------------------------------------------------------------------------------------
def write_preds(stage, rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R3 / "predictions" / f"{stage}.tsv").write_text("\n".join(out) + "\n")


def tables_md(info, tabs):
    L_ = ["# R3-events job tables (generated by gen/gen_r3.py; the JSON in tables/ is what runs)", "",
          f"n for the 90-tick hold = ((90 + 0.5) * 25000 - 82) / 1.5 = {N90} (S2b's e4l, hold = 1.5 n + 15 units, about 90.5 ms).", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | str | ldr |", "|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | {', '.join(i['sa_writes']) or 'none'} | "
                  f"{i['str']} | {', '.join(i['ldr']) or 'none'} |")
    L_ += ["", "alias.s: sa writes by command (the guard compares the assembled code with this): "
           + "; ".join(f"cmd {k} {v or 'none'}" for k, v in sorted(info["alias"]["cmd_sa"].items(), key=lambda x: int(x[0]))), ""]
    for st in STAGES:
        t = tabs[st]
        L_ += [f"## stage {st}: blob {t['blob']}, needs {t['needs']}, stop budget {t['stop_budget']}"
               + (f"; not run: {', '.join(t['rows_not_run'])}" if t["rows_not_run"] else ""), ""]
        if st == "a":
            L_ += ["| job | set | row | cmd | sa writes | marker | read 1200 ms | restore sa63 |", "|---|---|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['cmd']} | {', '.join(j['sa']) or 'none'} | "
                          f"{j['marker']:#x} | {j['read_1200']} | {j['restore63']} |")
        elif st == "b":
            L_ += ["| job | set | row | skip | pre ms | open ms | run if |", "|---|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['skip']} | {j['pre_ms']} | {j['open_ms']} | {j['run_if'] or ''} |")
        else:
            L_ += ["| job | set | kicks | n | window | open ms |", "|---|---|---|---|---|---|"]
            for j in t["jobs"]:
                L_.append(f"| {j['name']} | {j['set']} | {j['kick']} | {j['n']} | {j['window']} | {j['open_ms']} |")
        L_.append("")
    (R3 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    info = build_blobs()
    tabs = {"a": table_a(), "b": table_b(), "k7": table_k7()}
    preds = {"a": preds_a, "b": preds_b, "k7": preds_k7}
    for st in STAGES:
        (R3 / "tables" / f"{st}.json").write_text(json.dumps(tabs[st], indent=1, sort_keys=True) + "\n")
        write_preds(st, preds[st](tabs[st]))
    (R3 / "stages.txt").write_text("\n".join(STAGES) + "\n")
    tables_md(info, tabs)
    print("wrote", ", ".join(f"{k}: {v['insns']} insns" for k, v in info.items()), "; tables", ", ".join(STAGES))


if __name__ == "__main__":
    main()
