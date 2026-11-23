# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from the KEPT stages of round 42 (pinned
in session.toml): G1's m (row M: mark with 0xc43, post sa1 = M1 and sa13 = M13, job 2 a kick
read served, the gate's fill fault at M13's page) and G3's lv (landv: post sa1 0x04400000, job 2
never served, its K5 pre already 0x0440000f, the runner's stop). The base's page, job 1's record,
snap0, snap9 and kernel.log are copied as they were kept, the row renamed to the stage's (NAME =
STAGE1-a); the tokens then edit what the session's predictions read, as fwtask_run.py run and the
kit keep it. A planting stage (w or w2) is built beside a v or f stage unless `noplant`. Not a
test module (no test_ prefix).

Tokens (a set):
  W (w, w2)  base m, job 1 alone, snap9 BIF_FAULT 0, the disarm's record (owntask.reset.json)
             with BIF_FAULT 0; wfault (snap9 BIF_FAULT 0x005d300f), resetfault (the disarm's
             BIF_FAULT 0x005d300f), noreset (no disarm record), nosa1 (post sa1 0x04400000)
  V          base lv (sa1 0x04400000, job 2 not done, its K5 at 0x0440000f); keep (post sa1 = M1
             and job 2's K5 at M1's page: the prediction), v1 (sa1 0x32005000), other (sa1
             0x12345000), early13 (job 2's K5 at M13's page), early0 (at page 0), serve (job 2
             done, its after = post, K5 0, snap9 0)
  F          base m; job 1's post sa1 0x04000010 (EVT4) unless keep (M1), evt22 (0x04400000);
             job 2 kick-only (not done, cmd_after 0, m's kick reply, K5 pre 0, mid and post at
             M13's page) unless kickok (mid and post 0), replyerr (its reply failed); job 3 not
             done, its reply failed, the stop, no gate unless serve (m's job 2 as job 3: done,
             after = post, m's gate files and lines)
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

D = "data:render/closing-r42-n3g-"
BASES = {"m": (D + "g1/out/20261122-160857/m/", "m1-a"),
         "lv": (D + "g3/out/20261122-163956/lv/", "lv1-a")}
ROW = (".own_res.json.gz", ".txt.gz", ".snap0.regs.gz", ".snap9.regs.gz")
GATE = (".gate.json.gz", ".gate-fill.txt.gz", ".gate-tri.txt.gz", ".devcd-pre.txt.gz",
        ".devcd.txt.gz")
STOP = (".stop1-own_res.json.gz", ".stop1-regs.txt.gz")
FILES = {"m": [BASES["m"][1] + f for f in ROW + GATE] + ["kernel.log"],
         "lv": [BASES["lv"][1] + f for f in ROW + STOP] + ["kernel.log"]}
PINS = [BASES[b][0] + f for b in BASES for f in FILES[b]]
M6, FILL, MK13, MK1 = 0x5A5A3306, 0xDEADC0DE, 0x005D3000, 0x005D1000
FAULT = [0x000D0400, MK13 | 0xF]


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
                klog=pins.blob(src + "kernel.log").decode().replace(bn, n),
                gate={f: pins.blob(src + bn + f).decode() for f in GATE} if b == "m" else None)


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
    if x["gate"]:
        for f, body in x["gate"].items():
            gz(os.path.join(d, n + f[:-3]), body)
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


def build_w(root, stage, w, row, jobs):
    x = load("m", row["name"])
    x["recs"] = x["recs"][:1]
    x["gate"] = None
    x["klog"] = strip_gate(x["klog"])
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "wfault" in w else 0)
    if "nosa1" in w:
        x["page"][161] = 0x04400000
    controls(w, x)
    reset = None if "noreset" in w else {
        "ok": True, "own_arm": "off", "health": {"ok": "resetfault" not in w, "bif_int_stat": 0,
                                                 "bif_fault": MK13 | 0xF if "resetfault" in w
                                                 else 0, "event_status2": 0x400}}
    return write(root, stage, row, jobs, x, reset=reset)


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
    if "noplant" not in w:
        pw = make.PLANT[stage]
        (prow,) = K.table(KP, pw)
        build_w(root, pw, {"nosa1"} if "wfail" in w else set(), prow, [jobs[0]])
    ok = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                   "bif_fault": 0, "event_status2": 0x400}}
    if m == "V":
        x = load("lv", row["name"])
        sa1 = {"keep": MK1, "v1": 0x32005000, "other": 0x12345000}
        word = next((v for k, v in sa1.items() if k in w), None)
        if word is not None:
            x["page"][161] = word
        r2 = x["recs"][1]
        r2["job"] = dict(jobs[1], runid=2)
        f = {"early13": MK13 | 0xF, "early0": 0xF}
        fw = next((v for k, v in f.items() if k in w), (x["page"][161] & ~0xFFF) | 0xF)
        r2["bif"] = {"pre": [0xD0400, fw], "post": [0xD0400, fw]}
        x["recs"] = x["recs"][:2]
        controls(w, x)
        if "serve" in w:
            post = x["page"][160:192]
            x["recs"][1] = dict(r2, done=True, cmd_after=0, slot=[M6, 2, FILL, FILL],
                                slots=after_slots(r2["job"], post),
                                bif={"pre": [0x80000, 0], "post": [0x80000, 0]})
            x["page"][224:256] = post
            x["snap9"] = regs_edit(x["snap9"], bif=0)
            return write(root, stage, row, jobs, x, reset=ok)
        x["snap9"] = regs_edit(x["snap9"], bif=fw)
        return write(root, stage, row, jobs, x, stop="no done within 200 ms (job 1); firmware "
                     "hung: the tick stopped", cls="hang")
    # F
    x = load("m", row["name"])
    m2 = x["recs"][1]
    sa1 = {"keep": MK1, "evt22": 0x04400000}
    x["page"][161] = next((v for k, v in sa1.items() if k in w), 0x04000010)
    kick = m2["kick"] if "replyerr" not in w else {
        "kind": "miscinfo", "reply": {"error": "[Errno 110] Connection timed out"}}
    mid = [0, 0] if "kickok" in w else list(FAULT)
    r2 = {"done": False, "ms": 50.0, "slot": x["page"][0x40:0x44], "echo": 1, "cmd_after": 0,
          "overlap": 0, "job": {"n": 0, "params": {}, "runid": 2, "timeout_ms": 50,
                                       "kick": "miscinfo", "expect": "notdone"},
          "k0": {"cmd": 0, "ms": 0.5, "slot": x["page"][0x40:0x44], "tick": 2100},
          "kick": kick, "bif": {"pre": [0x80000, 0], "mid": mid, "post": list(mid)},
          "H": m2["H"], "restored": True}
    controls(w, x)
    if "serve" in w:
        r3 = dict(m2, job=dict(m2["job"], runid=3), slot=[M6, 3, FILL, FILL],
                  slots=after_slots(m2["job"], x["page"][160:192]))
        x["recs"] = [x["recs"][0], r2, r3]
        x["page"][0x58:0x5A] = [M6, 3]
        x["page"][3] = x["page"][5] = 3
        return write(root, stage, row, jobs, x)
    r3 = {"done": False, "ms": 200.0, "slot": [FILL] * 4, "echo": 1, "cmd_after": 6, "overlap": 0,
          "job": dict(m2["job"], runid=3),
          "kick": {"kind": "miscinfo", "reply": {"error": "[Errno 110] Connection timed out"}},
          "bif": {"pre": list(FAULT), "mid": list(FAULT), "post": list(FAULT)},
          "slots": {str(s): [FILL] * 4 for s in m2["job"]["slots"]}}
    x["recs"] = [x["recs"][0], r2, r3]
    x["gate"] = None
    x["klog"] = strip_gate(x["klog"])
    x["page"][1], x["page"][2], x["page"][3] = 6, 0, 3
    x["page"][0x58:0x5C] = [FILL] * 4
    return write(root, stage, row, jobs, x, stop="no done within 200 ms (job 2)")
