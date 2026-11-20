# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from the KEPT attempts of round 40 (pinned
in session.toml): row B11's two attempts (sideband 0xc43, crumb3: X, Y, LC's gate, T), row B0's
(0x843: C) and row L's (land: LC's job 1). The base's page, record, snap0 and snap9 are kept as
they were; job 2 (and LC's job 3) is fabricated on them as the tokens say, as fwtask_run.py run
records it (its slots 40-47: the after-read; its slot: M6 and its run id), with job 1's run id
1 and the page's run id the last job's. kernel.log is the base's arm line, the row's class mark,
then the gate's marks owntask-gate-begin and owntask-gate around the base's own gate lines (B11:
its BIF fault line and the recovery, verbatim). Not a test module (no test_ prefix).

Tokens (a set):
  base         b11a (default), b11b (B11's second attempt), b0, land
  job 2, 3     after2=same|diff|rebase|none|high|other (C: same and diff), j2stop (not done:
               the stop dump, no M6), kickfault (with j2stop: BIF_FAULT 0x0440000f in the stop
               dump and snap9), kickother (BIF_FAULT 0x0440000e), heal (job 3's after sa13 =
               pre sa13), noheal, j3stop, prepost (post = pre in the page)
  gate         gfill (the base's gate: B11's fault line, the fill's diff, a devcoredump with its
               words), gexact (both tools exact, no fault line), nodevcd, devcdother (0x0004400f),
               thead (the triangle first, its fault at 0x0155500f), tother (at 0x0440000f), thang
               (`job 7 hung` in the window, no fault), nogatemarks
  controls     pgbad, e0bad, t0stop, j1bad (M4 absent), bif (snap9 BIF_FAULT 0x90004)"""
import gzip
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import make  # noqa: E402
import pins  # noqa: E402

BASES = {"b11a": "data:render/closing-r40-n3e-b11/out/20261120-074024/own/",
         "b11b": "data:render/closing-r40-n3e-b11/out/20261120-084102/own/",
         "b0": "data:render/closing-r40-n3e-b0/out/20261119-230303/own/",
         "land": "data:render/closing-r40-n3e-l/out/20261119-230429/own/"}
FILES = ("c1-a.own_res.json.gz", "c1-a.txt.gz", "c1-a.snap0.regs.gz", "c1-a.snap9.regs.gz",
         "kernel.log")
PINS = [b + f for b in BASES.values() for f in FILES]
M6, FILL = 0x5A5A3306, 0xDEADC0DE
FILL_TXT = "programs asm\njob: ok\ndiff: 2048 of 2048 pixels, first (0, 0) 0xdeadbeef expected 0xff336699\n"
FILL_OK = "programs asm\njob: ok\ndiff: 0 of 2048 pixels\nfill: ok, 64x32\n"
TRI_OK = "tri: render context\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok\n"
TRI_BAD = "tri: render context\njob: faulted, context lost (Input/output error)\n"
DEVCD = ("==== devcd1 ====\n**** sgxfive error state ****\ndetector: bif-fault\nrecovery: ok\n"
         "BIF_INT_STAT: 0x%08x\nBIF_FAULT: 0x%08x\n**** end ****\n")


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def base_of(w):
    return next((b for b in BASES if b in w), "b0" if "b0" in w else "b11a")


def regs_edit(t, tim=None, bif=None):
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t


def build(root, stage, tokens):
    """root/STAGE/ under `tokens`; returns that directory."""
    w = set(tokens)
    b = BASES[base_of(w)]
    d = os.path.join(root, stage)
    os.makedirs(d, exist_ok=True)
    (row,) = K.table(KP, stage)
    n = row["name"]
    a = json.loads(row["args"])
    jobs = a if isinstance(a, list) else [a]
    page = json.loads(pins.blob(b + "c1-a.own_res.json.gz"))
    page = list(page["page"] if isinstance(page, dict) else page)
    run = json.loads(pins.blob(b + "c1-a.txt.gz"))
    rec1 = dict(run["records"][0], job=dict(jobs[0], n=1, runid=1))
    snap0 = pins.blob(b + "c1-a.snap0.regs.gz").decode()
    snap9 = pins.blob(b + "c1-a.snap9.regs.gz").decode()
    pre, post = page[128:160], page[160:192]
    if "prepost" in w:
        page[160:192] = post = list(pre)
    if "pgbad" in w:
        page[0] = 0
    if "e0bad" in w:
        page[0x44] = 0
    if "j1bad" in w:
        page[0x50] = FILL
    page[0x45] = page[0x51] = 1
    afters = {"same": pre, "rebase": post, "none": pre, "high": pre[:12] + post[12:],
              "diff": pre[:1] + [0x04400000] + pre[2:], "other": [0x77] * 32}
    a2 = next((afters[t.split("=")[1]] for t in w if t.startswith("after2=")), post)
    recs, stop, stopi = [rec1], None, None
    for k, j in enumerate(jobs[1:], 2):
        if k == 2 and "j2stop" in w or k == 3 and "j3stop" in w:
            recs.append({"done": False, "ms": 200.0, "slot": [FILL] * 4, "echo": page[5],
                         "cmd_after": 6, "overlap": 0, "job": dict(j, n=6, runid=k),
                         "slots": {str(s): [FILL] * 4 for s in j["slots"]}})
            stop, stopi = f"no done within 200 ms (job {k - 1})", k - 1
            break
        after = list(a2 if k == 2 else post)
        if k == 3 and "heal" in w:
            after[13] = pre[13]
        if k == 3 and "noheal" in w:
            after[13] = post[13] if post[13] != pre[13] else pre[13] + 1
        recs.append({"done": True, "ms": 2.0, "slot": [M6, k, FILL, FILL], "echo": k,
                     "cmd_after": 0, "overlap": 0, "job": dict(j, n=6, runid=k),
                     "slots": {str(s): after[4 * i:4 * i + 4] for i, s in enumerate(j["slots"])},
                     "ticks": 3}
                    | ({"slept": {"ms": j["sleep_ms"], "ticks": 1990}} if "sleep_ms" in j else {}))
        page[224:256] = after
        page[0x58:0x5A] = [M6, k]
        page[2], page[3], page[5] = 2, k, k
    run = {"name": n, "records": recs, "stop": stop, "n_jobs": len(jobs), "ran": len(recs)}
    bif9 = 0x0440000F if "kickfault" in w else 0x0440000E if "kickother" in w else \
        0x90004 if "bif" in w else None
    if stop:
        run["alive_at_stop"] = {"advancing": True, "ticks": [1, 2, 3]}
        gz(os.path.join(d, f"{n}.stop{stopi}-own_res.json"), json.dumps(page))
        gz(os.path.join(d, f"{n}.stop{stopi}-regs.txt"), regs_edit(snap9, bif=bif9 or 0))
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": page}))
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    gz(os.path.join(d, n + ".snap0.regs"), regs_edit(snap0, tim=0 if "t0stop" in w else None))
    gz(os.path.join(d, n + ".snap9.regs"), regs_edit(snap9, bif=bif9))
    klog = pins.blob(b + "kernel.log").decode().splitlines()
    armln = next((ln for ln in klog if "own task armed:" in ln), "")
    b11 = pins.blob(BASES["b11b" if "b11b" in w else "b11a"] + "kernel.log").decode().splitlines()
    at = next(i for i, ln in enumerate(b11) if "BIF fault" in ln)
    fault = [ln for ln in b11[at:] if "BIF fault" in ln or "SGX reset:" in ln
             or "SGX boot:" in ln][:5]          # B11's gate lines: the fault and the recovery
    order = make.STAGES[make.STEP][[s[0] for s in make.STAGES[make.STEP]].index(stage)][5]
    first, second = order.split(",")
    texts = {"fill": FILL_OK, "tri": TRI_OK}
    window = []
    if "thead" in w or "tother" in w:
        word = 0x0155500F if "thead" in w else 0x0440000F
        window = [f"Nov 21 10:00:01 cedar kernel: gma500 0000:00:02.0: [drm] *ERROR* sgxfive: "
                  f"BIF fault 0x10400 at {word:#x} (PD 0x0) stalls job 9, recovering"] + fault[1:]
        texts["tri"] = TRI_BAD
    elif "thang" in w:
        window = ["Nov 21 10:00:01 cedar kernel: gma500 0000:00:02.0: [drm] job 7 hung"]
        texts["tri"] = TRI_BAD
    elif "gfill" in w:
        window = fault
        texts["fill"] = FILL_TXT
    ok = "gexact" in w or not window
    klines = [armln, f"Nov 21 10:00:00 cedar unknown: resgx545 r41 class {n} ok 1-1"]
    if "nogatemarks" not in w:
        klines += [f"Nov 21 10:00:00 cedar unknown: resgx545 r41 owntask-gate-begin {n} {order} "
                   "1-1"] + window + [f"Nov 21 10:00:02 cedar unknown: resgx545 r41 owntask-gate "
                                      f"{n} 1-1"]
    open(os.path.join(d, "kernel.log"), "w").write("\n".join(klines) + "\n")
    devcd = "devcd: none pending\n"
    if window and "nodevcd" not in w and "thang" not in w:
        word = 0x0004400F if "devcdother" in w else \
            0x0155500F if "thead" in w else 0x0440000F if "tother" in w else 0x0004300F
        devcd = DEVCD % (0x10400 if ("thead" in w or "tother" in w) else 0xD0400, word)
    gz(os.path.join(d, n + ".gate.json"), json.dumps({"ok": ok, "order": order}))
    gz(os.path.join(d, f"{n}.gate-{first}.txt"), texts[first])
    gz(os.path.join(d, f"{n}.gate-{second}.txt"), texts[second])
    gz(os.path.join(d, n + ".devcd-pre.txt"), "devcd: none pending\n")
    gz(os.path.join(d, n + ".devcd.txt"), devcd)
    rc, cls = (1, "fail") if stop else (0, "ok")
    cases = ["\t".join(K.COLUMNS), "\t".join([n, stage, row["set"], row["risk"], "-", "owntask",
                                              row["args"], str(rc), cls, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d
