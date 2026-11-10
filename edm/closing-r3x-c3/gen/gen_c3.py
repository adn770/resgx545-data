#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_c3.py: write everything C3 runs from, in this directory's parent (closing3/r3x-c3/).

C3 is laptop session L3b of the question-closing pass, round 3 (companion C3 of closing3/rank-round3.md: Q158 and Q124's
residual; decision R3-R1 a in plans/resgx545-question-closing.md).  It is a copy of the framework of closing2/r3-events (kernel-log
markers, kept-output scorer, preflight with the srcversion check, mock) with ONE stage and ONE task:

  c3   13 jobs: S0 (the start state as found), N x3 (writer, reader at the next event, 1200 ms, reader), F x3 (writer, reader,
       one client fill, reader), L x3 (writer, reader, firmware reload with no reset, reader), R x3 (writer, reader, debugfs reset
       and reload, reader).  Every job reads first (rd0), writes (the writer arms the reader of the next event: rdA), perturbs, and
       reads again (rdB).  start.s writes sa63 (the only sa register our task may write, R2-1 b) and r20, r21, i0, i1 and p0..p3.

  asm/start.s, bins/start.blob     the task (the landed verifier accepts it);  tables/c3.json  the job table;
  predictions/c3.tsv               the frozen predictions (case quantity value model set)

Run with the scratch venv:  ../../closing/pixel-faults/.venv/bin/python gen/gen_c3.py   (then run/freeze_c3.sh freeze)
"""
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(HERE))
import c3layout as L  # noqa: E402
import c3blobs as B  # noqa: E402

ORDER = [("s0", "S0", 0), ("n1", "N", 0), ("n2", "N", 1), ("n3", "N", 2), ("f1", "F", 0), ("f2", "F", 1), ("f3", "F", 2),
         ("l1", "L", 0), ("l2", "L", 1), ("l3", "L", 2), ("r1", "R", 0), ("r2", "R", 1), ("r3", "R", 2)]


def marker(name, salt=""):
    """A frozen marker for a job: bit 31 set, not a tick's pa1 (0x02000000), from the job's name."""
    h = int(hashlib.sha256((salt + name).encode()).hexdigest()[:8], 16) | 0x80000000
    return h if h != 0x02000000 else h ^ 0x10


def build_blob():
    text, blob = B.build()
    (R3 / "asm" / "start.s").write_text(text)
    (R3 / "bins" / "start.blob").write_bytes(blob)
    info = {"start": B.info_of("start", text, blob, B.ARM_START)}
    (R3 / "bins" / "blobs.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


def table():
    jobs = []
    for name, row, k in ORDER:
        j = {"name": name, "row": row, "rep": k, "op": "start", "perturb": L.PERTURB[row], "runid": 0x7100 + len(jobs) + 1,
             "set": "control" if row == "S0" else "heldout" if k == 0 else "replicate"}
        if row == "S0":
            j.update({"write": False, "sa63": 0, "ri": [0, 0, 0, 0], "flags": [0, 0, 0, 0]})
        else:
            j.update({"write": True, "sa63": marker(name), "ri": [marker(name, f"ri{i}") for i in range(4)],
                      "flags": list(L.FLAGS[k])})
        jobs.append(j)
    return {"stage": "c3", "blob": "start", "arm": B.ARM_START, "stop_budget": 0, "gap_ms": L.GAP_MS, "jobs": jobs, "needs": None,
            "rows_not_run": ["sa100, sa127, sa20, sa24 writes (R2-1 b: our task writes sa63, sa64, sa65 only; here sa63)"]}


def preds(t):
    P = []

    def add(case, q, v, model, s):
        P.append((case, q, str(v), model, s))

    prev = None
    for j in t["jobs"]:
        n, row, k = j["name"], j["row"], j["rep"]
        if row == "S0":
            for q, v in (("rd0_pclink", "0x98"), ("rd0_p0p1", "11"), ("rd0_p2p3", "00"), ("rd0_sa64", "2"), ("rd0_sa63", "0"),
                         ("rd0_sa20", "0"), ("rd0_sa24", "0")):
                add(n, q, v, "E792 A0, E536/E537 controls", "fit")
            add(n, "kept", "yes", "H-NOSTOP", "fit")
            prev = n
            continue
        rep = "replicate" if k else "heldout"
        add(n, "kept", "yes", "H-NOSTOP", "heldout" if k == 0 else "replicate")
        add(n, "carry", "yes", "E536 (state lasts between reads)", "control")
        add(n, "a_markers", "yes", "E536 next event, E791 A1", "control")
        add(n, "a_pclink", "0x98", "E792 (sa64 not written)", "fit" if k == 0 else "replicate")
        add(n, "a_p0", "1", "E792 (p0 reads 1 whatever the writer left)", "fit" if k == 0 else "replicate")
        add(n, "a_p1", str(j["flags"][1]), "E792 (p1 = the writer's tail)", "fit" if k == 0 else "replicate")
        p2, p3 = j["flags"][2], j["flags"][3]
        add(n, "a_p2p3", f"{p2}{p3}", "H-KEEP (p2, p3 as the writer left them)", "heldout" if k == 0 else "replicate")
        add(n, "a_p2p3", "11", "H-SET (the next entry has p2 = p3 = 1)", "heldout" if k == 0 else "replicate")
        if row == "N":
            fit = "fit" if k == 0 else "replicate"
            add(n, "b_markers", "yes", "E536 (1200 ms)", fit)
            add(n, "b_p0p1", "11", "E536 (1200 ms)", fit)
            add(n, "b_pclink", "0x98", "E536 (1200 ms)", fit)
            add(n, "b_p2p3", f"{p2}{p3}", "E536 (1200 ms, p2 p3 as written)", "fit" if (p2, p3) == (1, 1) else "heldout")
            for r_ in ("sa100", "sa127", "sa20", "sa24"):
                add(n, f"b_{r_}_same", "yes", "E536 (1200 ms)", fit)
        elif row == "F":
            fit = "fit" if k == 0 else "replicate"
            add(n, "b_i_kept", "yes", "E536 (fill)", fit)
            add(n, "b_r_replaced", "yes", "E536 (fill: r20 = 0, r21 a counter)", fit)
            add(n, "b_r20_zero", "yes", "E536 (fill)", fit)
            if k:
                add(n, "b_r21_step", "0x1000", "E536 (+0x1000 a fill)", "heldout")
            add(n, "b_sa63_kept", "yes", "H-KEEP-SA (sa63 survives a fill as sa100 did)", "heldout")
            add(n, "b_p0p1", "11", "E536 (fill)", fit)
            add(n, "b_pclink", "0x98", "E536 (fill)", fit)
            add(n, "b_p2p3", "01", "E536 (fill: p2 p3 = 0 1)", "fit" if k == 0 else "heldout")
            for r_ in ("sa100", "sa127", "sa20", "sa24"):
                add(n, f"b_{r_}_same", "yes", "E536 (fill)", fit)
        else:                                           # L and R: reload with and without a reset
            lab = "heldout" if k == 0 else "replicate"
            for model, i_k, r_k in (("H-KEEP (i and sa survive, r does not: the sketch)", "yes", "no"),
                                    ("H-ALL (r survives too: E537's r21 0x3000 after a reload)", "yes", "yes")):
                add(n, "b_i_kept", i_k, model, lab)
                add(n, "b_r_kept", r_k, model, lab)
                add(n, "b_sa63_kept", "yes", model, lab)
            add(n, "b_p2p3", "00", "E536 controls (after reset and reload: 0 0)", lab)
            add(n, "b_p0p1", "11", "E536 controls", lab)
            add(n, "b_pclink", "0x98", "E536 controls", lab)
            for r_ in ("sa100", "sa127", "sa20", "sa24"):
                add(n, f"b_{r_}_same", "yes", "H-KEEP (sa left as it is)", lab)
            add(n, "b_sa20_sa24_zero", "yes", "E537 (sa20 and sa24 read 0 after a reload)", lab)
    return P


def write_preds(rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R3 / "predictions" / "c3.tsv").write_text("\n".join(out) + "\n")


def tables_md(info, t, P):
    L_ = ["# C3 job table (generated by gen/gen_c3.py; the JSON in tables/ is what runs)", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | str | ldr |", "|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | {', '.join(i['sa_writes']) or 'none'} | "
                  f"{i['str']} | {', '.join(i['ldr']) or 'none'} |")
    L_ += ["", "start.s: sa writes by command: " + "; ".join(f"cmd {k} {v or 'none'}" for k, v in sorted(info["start"]["cmd_sa"].items())),
           "", "| job | row | perturb | flags p0..p3 | sa63 marker | r20 r21 i0 i1 markers | set |", "|---|---|---|---|---|---|---|"]
    for j in t["jobs"]:
        L_.append(f"| {j['name']} | {j['row']} | {j['perturb']} | {''.join(str(f) for f in j['flags'])} | "
                  f"{j['sa63']:#010x} | {' '.join(f'{x:#010x}' for x in j['ri'])} | {j['set']} |")
    L_ += ["", f"{len(P)} frozen predictions in predictions/c3.tsv."]
    (R3 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    for d in ("asm", "bins", "tables", "predictions"):
        (R3 / d).mkdir(exist_ok=True)
    info = build_blob()
    t = table()
    (R3 / "tables" / "c3.json").write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    P = preds(t)
    write_preds(P)
    (R3 / "stages.txt").write_text("c3\n")
    tables_md(info, t, P)
    print(f"blob {info['start']['insns']} insns, {len(t['jobs'])} jobs, {len(P)} predictions")


if __name__ == "__main__":
    main()
