# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from the KEPT stages of round 43 (pinned
in session.toml, resgx545-data b3df8fc21): N1's w (row W: mark, one job, post sa1 = M1 and sa13 =
M13, the disarm's record, no gate), N1's v (landv: post sa0 V0, sa1 M1, sa2 V2, job 2 never served,
its K5 at M1's page, the runner's stop) and N2's f (crumb3 after one fill: job 1's page and
record; its hang and gate are stripped). The base's page, job 1's record, snap0, snap9 and
kernel.log are copied as they were kept, the row renamed to the stage's (NAME = STAGE1-a); the
tokens then edit what the session's predictions read, as fwtask_run.py run and the kit keep it. A
read stage (ft, ff, t, tf, lm, lf) is built beside its plant stage (wa, wb, wc, wd, wl, wf) unless
`noplant`; f2 beside tf unless `notf`. Not a test module (no test_ prefix).

Tokens (a set):
  W (a plant stage)  base w, job 1 alone, snap9 BIF_FAULT 0, the disarm's record
             (owntask.reset.json) with BIF_FAULT 0; wfault (snap9 BIF_FAULT 0x005d300f),
             resetfault (the disarm's BIF_FAULT 0x005d300f), noreset (no disarm record), nosa1
             (post sa1 0x04400000)
  read (ft ff t tf f2)  base f, job 1 alone, snap9 BIF_FAULT 0, the disarm's record, begin draws
             as the stage declares (the health mark at try 1 and each draw kept exact), the end
             draws (fill,tri at try 2, kept); post sa1 the stage's predicted word unless
             sa1=0xWORD; drmark (the begin mark names another list), drretry (a second begin
             mark, try 2), drbad (a kept begin draw not exact), drgone (no begin draw kept),
             rfault (snap9 BIF_FAULT 0x005d300f), notf (f2: no tf beside it), tfretry (f2: tf's
             end health ran twice), tfbad (f2: tf's kept end draw not exact)
  land (lm lf)  base v; job 2 not done, its K5 at post sa1's page (lm: M1's, the prediction) or at
             page 0 (lf: LC's, the prediction); the stage's predicted post sa0-sa2 (lm: V0, M1,
             V2; lf: 0, 0x01000000, 0x0104b95b); sa0=, sa1=, sa2= 0xWORD override them (the K5
             fault follows post sa1's page unless early0, early1, early13, other); serve (job 2
             done, its after = post, K5 0, snap9 0); lf begin draws fill, lm none (drmark etc.
             as above)
  plant      noplant (no planting stage), wfail (the planting stage's sa1 not M1)
  controls   pgbad, e0bad (job 1's record's slot 1 marker 0), e0cmd (its cmd_after 1), t0stop,
             j1bad (M4 absent)"""
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

D = "data:render/closing-r43-n3h-"
A1, A2 = "n1/out/20261123-164401/", "n2/out/20261123-164448/"
BASES = {"w": (D + A1 + "w/", "w1-a"), "v": (D + A1 + "v/", "v1-a"),
         "f": (D + A2 + "f/", "f1-a")}
ROW = (".own_res.json.gz", ".txt.gz", ".snap0.regs.gz", ".snap9.regs.gz")
STOP = (".stop1-own_res.json.gz", ".stop1-regs.txt.gz")
FILES = {"w": [BASES["w"][1] + f for f in ROW] + ["kernel.log", "owntask.reset.json.gz"],
         "v": [BASES["v"][1] + f for f in ROW + STOP] + ["kernel.log", "begin.reghealth1.txt.gz"],
         "f": [BASES["f"][1] + f for f in ROW] + ["kernel.log", "begin.fill1.txt.gz",
                                                  "f1-a.health2.txt.gz"]}
PINS = [BASES[b][0] + f for b in BASES for f in FILES[b]]
M6, FILL, MK13, MK1 = 0x5A5A3306, 0xDEADC0DE, 0x005D3000, 0x005D1000
FAULT = [0x000D0400, MK13 | 0xF]
# a read stage's predicted post sa1 word (the held outcome of design §3.2, §3.3)
WORD = {"ft": 0x04400000, "ff": 0x02000000, "t": 0x03400000, "tf": 0x04000000, "f2": 0x01000000}


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def regs_edit(t, tim=None, bif=None):
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t


def after_slots(job, after):
    return {str(s): after[4 * i:4 * i + 4] for i, s in enumerate(job["slots"])}


def load(b, n):
    src, bn = BASES[b]
    page = json.loads(pins.blob(src + bn + ".own_res.json.gz"))
    page = list(page["page"] if isinstance(page, dict) else page)
    run = json.loads(pins.blob(src + bn + ".txt.gz"))
    return dict(page=page, recs=[dict(x) for x in run["records"]],
                snap0=pins.blob(src + bn + ".snap0.regs.gz").decode(),
                snap9=pins.blob(src + bn + ".snap9.regs.gz").decode(),
                klog=pins.blob(src + "kernel.log").decode().replace(bn, n), extra={})


def strip_gate(klog):
    return "\n".join(ln for ln in klog.splitlines()
                     if "owntask-gate" not in ln and "BIF fault" not in ln) + "\n"


def controls(w, x):
    if "e0bad" in w:
        x["recs"][0]["slot"] = [0, *x["recs"][0]["slot"][1:]]
    if "e0cmd" in w:
        x["recs"][0]["cmd_after"] = 1
    if "pgbad" in w:
        x["page"][0] = 0
    if "j1bad" in w:
        x["page"][0x50] = FILL
    if "t0stop" in w:
        x["snap0"] = regs_edit(x["snap0"], tim=0)


def write(root, stage, row, jobs, x, stop=None, reset=None, cls=None):
    d = os.path.join(root, stage)
    os.makedirs(d, exist_ok=True)
    n = row["name"]
    run = {"name": n, "records": x["recs"], "stop": stop, "n_jobs": len(jobs),
           "ran": len(x["recs"])}
    if stop:
        run["alive_at_stop"] = {"advancing": False, "ticks": [7, 7, 7]}
        gz(os.path.join(d, f"{n}.stop1-own_res.json"), json.dumps(x["page"]))
        gz(os.path.join(d, f"{n}.stop1-regs.txt"), x["snap9"])
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": x["page"]}))
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    gz(os.path.join(d, n + ".snap0.regs"), x["snap0"])
    gz(os.path.join(d, n + ".snap9.regs"), x["snap9"])
    open(os.path.join(d, "kernel.log"), "w").write(x["klog"])
    for f, body in x["extra"].items():
        gz(os.path.join(d, f), body)
    if reset is not None:
        gz(os.path.join(d, "owntask.reset.json"), json.dumps(reset))
    rc, c = (1, cls or "fail") if stop else (0, "ok")
    cases = ["\t".join(K.COLUMNS), "\t".join([n, stage, row["set"], row["risk"], "-", "owntask",
                                              row["args"], str(rc), c, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def plant_stage(stage):
    return next((s for s in make.STAGES[make.STEP] if s[0] == stage), None)


def tok_word(w, key, default):
    t = next((x for x in w if x.startswith(key + "=")), None)
    return default if t is None else int(t.split("=", 1)[1], 16)


def mark_line(klog, phase, try_, draws, run="1795448644-13975"):
    """A kit health mark line as the kernel log keeps it, before the stage's last line."""
    return (f"Nov 23 16:44:12 cedar unknown: resgx545 r44i1 health {phase} try {try_} {draws} "
            f"{run}")


def exact(tool):
    """A kept exact draw: f's begin fill, f's strict-health triangle (round 43, as kept)."""
    name = "begin.fill1.txt.gz" if tool == "fill" else "f1-a.health2.txt.gz"
    return pins.blob(BASES["f"][0] + name).decode()


def draws_files(extra, phase, try_, draws, bad=False):
    """The kept outputs of health `phase` try `try_` for the list `draws` (K8's names)."""
    if draws == "none":
        extra[f"{phase}.reghealth{try_}.txt"] = pins.blob(
            BASES["v"][0] + "begin.reghealth1.txt.gz").decode()
        return
    for i, tool in enumerate(draws.split(","), 1):
        suf = "" if draws == "fill,tri" else f".{i}"
        extra[f"{phase}.{'fill' if tool == 'fill' else 'health'}{try_}{suf}.txt"] = \
            exact(tool).replace("diff: 0 of", "diff: 7 of") if bad else exact(tool)


def set_begin(x, stage, w):
    """The stage's begin health in the kernel log and the kept files: the declared list at try 1;
    drmark, drretry, drbad, drgone edit it."""
    want = make.DRAWS[stage]
    logged = "fill,tri" if "drmark" in w and want != "fill,tri" else want
    if "drmark" in w and want == "fill,tri":
        logged = "fill"
    lines = [ln for ln in x["klog"].splitlines() if " health begin try " not in ln]
    i = next(k for k, ln in enumerate(lines) if "row begin" in ln)
    lines.insert(i + 1, mark_line(x["klog"], "begin", 1, logged))
    if "drretry" in w:
        lines.insert(i + 2, mark_line(x["klog"], "begin", 2, logged))
    x["klog"] = "\n".join(lines) + "\n"
    for k in [k for k in x["extra"] if k.startswith("begin.")]:
        del x["extra"][k]
    if "drgone" not in w:
        draws_files(x["extra"], "begin", 1, want, bad="drbad" in w)


def set_end(x, w, stage):
    """The stage's end draws (the default fill,tri at try 2, kept exact)."""
    lines = x["klog"].splitlines()
    lines.append(mark_line(x["klog"], "end", 2, "fill,tri"))
    if stage == "tf" and "tfretry" in w:
        lines.append(mark_line(x["klog"], "end", 3, "fill,tri"))
    x["klog"] = "\n".join(lines) + "\n"
    draws_files(x["extra"], "end", 2, "fill,tri", bad=stage == "tf" and "tfbad" in w)


def build_w(root, stage, w, row, jobs):
    x = load("w", row["name"])
    x["recs"] = x["recs"][:1]
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "wfault" in w else 0)
    if "nosa1" in w:
        x["page"][161] = 0x04400000
    controls(w, x)
    reset = None if "noreset" in w else {
        "ok": True, "own_arm": "off", "health": {"ok": "resetfault" not in w, "bif_int_stat": 0,
                                                 "bif_fault": MK13 | 0xF if "resetfault" in w
                                                 else 0, "event_status2": 0x400}}
    return write(root, stage, row, jobs, x, reset=reset)


def build_read(root, stage, w, row, jobs):
    x = load("f", row["name"])
    x["recs"] = x["recs"][:1]
    x["klog"] = strip_gate(x["klog"])
    x["page"][161] = tok_word(w, "sa1", WORD[stage])
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "rfault" in w else 0)
    controls(w, x)
    set_begin(x, stage, w)
    set_end(x, w, stage)
    reset = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                      "bif_fault": 0, "event_status2": 0x400}}
    return write(root, stage, row, jobs, x, reset=reset)


def build_land(root, stage, w, row, jobs):
    lm = stage == "lm"
    x = load("v", row["name"])
    r2 = x["recs"][1]
    r2["job"] = dict(jobs[1], runid=2)
    x["recs"] = x["recs"][:2]
    pg = x["page"]
    v0, v2 = pg[160], pg[162]               # V0 and V2 as v kept them
    pg[160] = tok_word(w, "sa0", v0 if lm else 0)
    pg[161] = tok_word(w, "sa1", MK1 if lm else 0x01000000)
    if "tick" in w:
        pg[160], pg[162] = 2, 0x01061A70
    elif "one" in w:
        pg[160], pg[162] = v0, v2
    else:
        pg[162] = tok_word(w, "sa2", v2 if lm else 0x0104B95B)
    page = {"early0": 0xF, "early13": MK13 | 0xF, "other": 0x12345000 | 0xF,
            "early1": pg[161] | 0xF}
    fw = next((v for k, v in page.items() if k in w),
              (pg[161] | 0xF) if lm else 0xF)
    r2["bif"] = {"pre": [0xD0400, fw], "post": [0xD0400, fw]}
    controls(w, x)
    if lm:
        set_begin(x, "lm", w)
    else:
        set_begin(x, "lf", w)
    ok = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                   "bif_fault": 0, "event_status2": 0x400}}
    if "serve" in w:
        post = pg[160:192]
        x["recs"][1] = dict(r2, done=True, cmd_after=0, slot=[M6, 2, FILL, FILL],
                            slots=after_slots(r2["job"], post),
                            bif={"pre": [0x80000, 0], "post": [0x80000, 0]})
        pg[224:256] = post
        x["snap9"] = regs_edit(x["snap9"], bif=0)
        return write(root, stage, row, jobs, x, reset=ok)
    x["snap9"] = regs_edit(x["snap9"], bif=fw)
    return write(root, stage, row, jobs, x, stop="no done within 200 ms (job 1); firmware "
                 "hung: the tick stopped", cls="hang")


def build(root, stage, tokens):
    """root/STAGE/ under `tokens` (and its planting stage beside it); returns STAGE's dir."""
    w = set(tokens)
    st = plant_stage(stage)
    m = st[1]
    (row,) = K.table(KP, stage)
    a = json.loads(row["args"])
    jobs = a if isinstance(a, list) else [a]
    if m == "W":
        return build_w(root, stage, w, row, jobs)
    if stage in make.PLANT and "noplant" not in w:
        pw = make.PLANT[stage]
        (prow,) = K.table(KP, pw)
        build_w(root, pw, {"nosa1"} if "wfail" in w else set(), prow, [jobs[0]])
    if stage == "f2" and "notf" not in w:
        (trow,) = K.table(KP, "tf")
        build_read(root, "tf", {t for t in w if t in ("tfretry", "tfbad")}, trow, [jobs[0]])
    if m in make.LANDS:
        return build_land(root, stage, w, row, jobs)
    return build_read(root, stage, w, row, jobs)
