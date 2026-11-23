# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from the KEPT stages of round 41 (pinned in
session.toml): H1's c (row C: 0x843, crumb3, its job 2 a kick read, the gate exact), H1's x (row
X: 0xc43, crumb3, job 2 served, the fill's fault at sa13's page 0x00043000), H2's y (row Y: 0x403,
V0/V2 in every fourth sa, the same fault) and LC2's lc (land: job 2 posted and never served,
BIF_FAULT 0x0000000f, the runner's stop). The base's page, records, snap0, snap9, gate files and
kernel.log are copied as they were kept, the row renamed to the stage's (NAME = STAGE1-a); the
tokens then edit what the session's predictions read, as fwtask_run.py run and the kit keep it.
Not a test module (no test_ prefix).

Tokens (a set):
  base         c, x, y, lc2 (default: c for C and S, x for M and LV, y for Q)
  words        marked (M's prediction: post sa1 = M1, post sa13 = post pa1 = M13, the fault and the
               devcoredump at M13's page), fill43 (marked, the fault left at 0x00043000), fillm1
               (marked, the fault at M1's page), pakeep (post pa1 = M13: S-KEEP), paother (post
               pa1 0x12345000), landv (post sa0 = V0, sa2 = V2 from snap0), norep (post sa8 moved)
  job 2, 3     after2=same|diff|rebase|none|high|other (rewrites job 2's after-read in its record
               and on the page), j2stop (job 2 posted and never served: its record not done, its
               cmd word 6 left on the page, the stop dump, no gate), job3 (adds LV's job 3, done,
               its after = post), heal (job 3's after sa13 = pre sa13), kickfault (with j2stop:
               BIF_FAULT 0x005d300f in the stop dump and snap9), early0 (with j2stop: 0x0000000f)
  gate         gexact (both tools exact, no fault line, no devcoredump), nogatemarks
  controls     pgbad, e0bad (job 1's record's slot 1 marker 0), e0cmd (its cmd_after 1), t0stop,
               j1bad (M4 absent), j2bad (job 2's record's M6 0), bif (snap9 BIF_FAULT 0x90004),
               snap9ok (snap9 BIF_FAULT 0), bifrec (K5's words in every record)"""
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

D = "data:render/closing-r41-n3f-"
BASES = {"c": (D + "h1/out/20261120-161456/c/", "c1-a"),
         "x": (D + "h1/out/20261120-161456/x/", "x1-a"),
         "y": (D + "h2/out/20261120-161558/y/", "y1-a"),
         "lc2": (D + "lc2/out/20261121-073816/lc/", "lc1-a")}
ROW = (".own_res.json.gz", ".txt.gz", ".snap0.regs.gz", ".snap9.regs.gz")
GATE = (".gate.json.gz", ".gate-fill.txt.gz", ".gate-tri.txt.gz", ".devcd-pre.txt.gz",
        ".devcd.txt.gz")
STOP = (".stop1-own_res.json.gz", ".stop1-regs.txt.gz")
FILES = {b: [n + f for f in ROW + (STOP if b == "lc2" else GATE)] + ["kernel.log"]
         for b, (_, n) in BASES.items()}
PINS = [p + f for b, (p, _) in BASES.items() for f in FILES[b]]
DEFAULT = {"C": "c", "S": "c", "M": "x", "Q": "y", "LV": "x"}
M6, FILL, MK13, MK1 = 0x5A5A3306, 0xDEADC0DE, 0x005D3000, 0x005D1000
FILL_OK = "programs asm\njob: ok\ndiff: 0 of 2048 pixels\nfill: ok, 64x32\n"
TRI_OK = "tri: render context\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok\n"


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def regs_edit(t, tim=None, bif=None):
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t


def ta3d(snap0, i):
    m = re.search(rf"^ta3dctl 0x{4 * i:02x} (0x[0-9a-f]{{8}})$", snap0, re.M)
    return int(m.group(1), 16)


def after_slots(job, after):
    return {str(s): after[4 * i:4 * i + 4] for i, s in enumerate(job["slots"])}


def build(root, stage, tokens):
    """root/STAGE/ under `tokens`; returns that directory."""
    w = set(tokens)
    st = next(s for s in make.STAGES[make.STEP] if s[0] == stage)
    m, order = st[1], st[5]
    b = next((x for x in BASES if x in w), DEFAULT[m])
    src, bn = BASES[b]
    d = os.path.join(root, stage)
    os.makedirs(d, exist_ok=True)
    (row,) = K.table(KP, stage)
    n = row["name"]
    a = json.loads(row["args"])
    jobs = a if isinstance(a, list) else [a]
    page = json.loads(pins.blob(src + bn + ".own_res.json.gz"))
    page = list(page["page"] if isinstance(page, dict) else page)
    run = json.loads(pins.blob(src + bn + ".txt.gz"))
    recs = [dict(x) for x in run["records"]]
    snap0 = pins.blob(src + bn + ".snap0.regs.gz").decode()
    snap9 = pins.blob(src + bn + ".snap9.regs.gz").decode()
    klog = pins.blob(src + "kernel.log").decode().replace(bn, n)
    gate = {f: pins.blob(src + bn + f).decode() for f in GATE} if b != "lc2" else None
    pre = page[128:160]
    bif9 = None
    # the words job 1 left (its post sa and pa)
    if w & {"marked", "fill43", "fillm1"}:
        page[161], page[173], page[193] = MK1, MK13, MK13
    if "pakeep" in w:
        page[193] = MK13
        if page[160:192] != pre:
            page[173] = MK13
    if "paother" in w:
        page[193] = 0x12345000
    if "landv" in w:
        page[160], page[162] = ta3d(snap0, 0), ta3d(snap0, 2)
    if "norep" in w:
        page[168] ^= 0x1000
    post = page[160:192]
    afters = {"same": pre, "rebase": post, "none": pre, "high": pre[:12] + post[12:],
              "diff": pre[:1] + [0x04400000] + pre[2:], "other": [0x77] * 32}
    tok = next((t.split("=")[1] for t in w if t.startswith("after2=")), None)
    a2 = afters[tok] if tok else (post if len(recs) > 1 and m != "C" and m != "S" else None)
    if len(recs) > 1 and recs[1].get("done") and a2 is not None:
        recs[1]["slots"] = after_slots(recs[1]["job"], a2)
        page[224:256] = a2
    if "j2bad" in w and len(recs) > 1:
        recs[1]["slot"] = [0, *recs[1]["slot"][1:]]
    stop = run.get("stop")
    if "j2stop" in w and b != "lc2":
        j = recs[1]["job"]
        recs[1] = {"done": False, "ms": 200.0, "slot": [FILL] * 4, "echo": page[5],
                   "cmd_after": 6, "overlap": 0, "job": j,
                   "slots": {str(s): [FILL] * 4 for s in j["slots"]}}
        recs = recs[:2]
        stop = "no done within 200 ms (job 1)"
        page[0x58:0x5C] = [FILL] * 4
        page[224:256] = [FILL] * 32
        page[1], page[2], page[3] = 6, 0, 2
        gate = None
    if "job3" in w and len(jobs) == 3 and len(recs) == 2 and recs[1].get("done"):
        j = dict(jobs[2], n=6, runid=3)
        a3 = list(post)
        if "heal" in w:
            a3[13] = pre[13]
        recs.append({"done": True, "ms": 2.0, "slot": [M6, 3, FILL, FILL], "echo": 3,
                     "cmd_after": 0, "overlap": 0, "job": j, "slots": after_slots(j, a3),
                     "ticks": 3, "slept": {"ms": 2000, "ticks": 1990}})
        page[224:256] = a3
        page[0x58:0x5A] = [M6, 3]
        page[2], page[3], page[5] = 2, 3, 3
    if "bifrec" in w:
        for k, x in enumerate(recs):
            x["bif"] = {"pre": [0, 0] if k == 0 else [0xD0400, 0x4300F], "post": [0xD0400, 0x4300F]}
    if "e0bad" in w:
        recs[0]["slot"] = [0, *recs[0]["slot"][1:]]
    if "e0cmd" in w:
        recs[0]["cmd_after"] = 1
    if "pgbad" in w:
        page[0] = 0
    if "j1bad" in w:
        page[0x50] = FILL
    if "kickfault" in w:
        bif9 = MK13 | 0xF
    if "early0" in w:
        bif9 = 0xF
    if "bif" in w:
        bif9 = 0x90004
    if "snap9ok" in w:
        bif9 = 0
    # the fault the gate (or the row) read, at the page the tokens say
    fault = {"marked": MK13 | 0xF, "fillm1": MK1 | 0xF}
    word = next((v for k, v in fault.items() if k in w), None)
    if word is not None and gate:
        klog = klog.replace("at 0x4300f", f"at {word:#x}")
        gate[".devcd.txt.gz"] = gate[".devcd.txt.gz"].replace("0x0004300f", f"0x{word:08x}")
        snap9 = snap9.replace("reg 0x0c08 0x0004300f", f"reg 0x0c08 0x{word:08x}")
    if "gexact" in w and gate:
        klog = "\n".join(ln for ln in klog.splitlines() if "BIF fault" not in ln) + "\n"
        gate[".gate-fill.txt.gz"], gate[".gate-tri.txt.gz"] = FILL_OK, TRI_OK
        gate[".devcd.txt.gz"] = "devcd: none pending\n"
    if "nogatemarks" in w:
        klog = "\n".join(ln for ln in klog.splitlines() if "owntask-gate" not in ln) + "\n"
    if gate is None:
        klog = "\n".join(ln for ln in klog.splitlines() if "owntask-gate" not in ln) + "\n"
    run = {"name": n, "records": recs, "stop": stop, "n_jobs": len(jobs), "ran": len(recs)}
    if stop:
        run["alive_at_stop"] = {"advancing": False, "ticks": [7, 7, 7]}
        if b == "lc2":
            sp = pins.blob(src + bn + ".stop1-own_res.json.gz")
            sr = pins.blob(src + bn + ".stop1-regs.txt.gz").decode()
        else:
            sp, sr = json.dumps(page), snap9
        gz(os.path.join(d, f"{n}.stop1-own_res.json"), sp)
        gz(os.path.join(d, f"{n}.stop1-regs.txt"), regs_edit(sr, bif=bif9))
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": page}))
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    gz(os.path.join(d, n + ".snap0.regs"), regs_edit(snap0, tim=0 if "t0stop" in w else None))
    gz(os.path.join(d, n + ".snap9.regs"), regs_edit(snap9, bif=bif9))
    open(os.path.join(d, "kernel.log"), "w").write(klog)
    if gate:
        for f, body in gate.items():
            gz(os.path.join(d, n + f[:-3]), body)
    rc, cls = (1, "fail") if stop else (0, "ok")
    cases = ["\t".join(K.COLUMNS), "\t".join([n, stage, row["set"], row["risk"], "-", "owntask",
                                              row["args"], str(rc), cls, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d
