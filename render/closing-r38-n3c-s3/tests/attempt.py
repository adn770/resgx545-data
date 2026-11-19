# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of stage own (one row, c1-a) for tests/test_score.py, the
way the kit's runner keeps it: c1-a.txt (fwtask_run.py run's JSON, the record with ticks),
c1-a.own_res.json.gz ({"page": [...]}, the page dump after the job), c1-a.snap0.regs.gz,
c1-a.snap9.regs.gz, after a stop c1-a.stop0-own_res.json.gz (a plain list) and
c1-a.stop0-regs.txt.gz, after an ok end c1-a.gate.json.gz; cases.tsv, void.tsv, readings.tsv, and
the stage's kernel.log with the arm's line (pds= and pdsat= as STEP's arm; the address a
stand-in).
The registers are E1148's kept snapshots (r36-n3, pinned in session.toml), with 0x0acc and 0x0c08
replaced as the tokens say. Not a test module (no test_ prefix).

Tokens (a set):
  how far the task got  issuer (entry 0 stored slot 1 and cleared cmd, nothing past the emit),
                        past (+ X0), e1 (+ S1), done (everything, state 2: the job ends ok)
  T (snap9, stop dump)  trun (E1148's running reads), t0 (0), t200 (0x200), t3 (0x005a3305),
                        tother (0x00001234), tunequal (0x200, then 0x005a3305)
  ticks                 ticksN (the record's ticks, default 1 after a stop, 31 after done)
  alive                 alive (the record's alive_at_stop.advancing true after a stop; else
                        false, r37's stops)
  controls              e0bad (slot 1 marker absent), pgbad (page dword 0 not ours), t0stop
                        (snap0's 0x0acc stopped), bif (BIF_FAULT 0x90004 in snap9)
  landing               pa (pa0 = V0, pa2 = V2 after done; else 0 and 0)"""
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

E1148 = "data:render/closing-r36-n3/out/20261118-152130/own/e1-a."
MAGIC, FILL = 0x4E574F53, 0xDEADC0DE
M1, X0, M4, S1, T3 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x005A3305
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)       # E1148's snap0 TA3DCtl dwords 0-3
TREADS = {"trun": (0x0105B86C, 0x010527E7), "t0": (0, 0), "t200": (0x200, 0x200),
          "t3": (T3, T3), "tother": (0x1234, 0x1234), "tunequal": (0x200, T3)}


def regs(which, tim=None, bif=None):
    t = pins.blob(E1148 + which).decode()
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t.encode()


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def build(root, tokens):
    """root/own/ under `tokens`; returns that directory."""
    w = set(tokens)
    d = os.path.join(root, "own")
    os.makedirs(d, exist_ok=True)
    (r,) = K.table(KP, "own")
    n, job = r["name"], json.loads(r["args"])
    page = [0] * 1024
    page[0] = 0 if "pgbad" in w else MAGIC
    page[0x44:0x48] = [FILL] * 4                              # the runner's initfill of slot 1
    for k, vals in job["params"].items():
        page[int(k):int(k) + len(vals)] = vals
    page[1], page[2], page[3] = 1, 0, 1                       # cmd, state, run id
    depth = ("issuer", "past", "e1", "done")
    got = max((depth.index(t) for t in w if t in depth), default=-1)
    if got >= 0:
        page[0x44:0x46] = [0 if "e0bad" in w else M1, 1]
        page[1] = 0
    if got >= 1:
        page[0x46] = X0
    if got >= 2:
        page[0x54] = S1
    done = got == 3
    if done:
        page[0x48:0x4C] = [V[0], 7, V[2], 0] if "pa" in w else [0, 7, 0, 0]
        page[0x4C:0x50] = list(V)
        page[0x50:0x52] = [M4, 1]
        page[2], page[5] = 2, 1
    tk = next((int(t[5:]) for t in w if re.fullmatch(r"ticks[0-9]+", t)), 31 if done else 1)
    t9, ts = next((TREADS[t] for t in w if t in TREADS), TREADS["trun"])
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": page}))
    gz(os.path.join(d, n + ".snap0.regs"), regs("snap0.regs.gz", tim=0 if "t0stop" in w else None))
    gz(os.path.join(d, n + ".snap9.regs"), regs("snap9.regs.gz", tim=t9,
                                                 bif=0x90004 if "bif" in w else None))
    win = 31.0 if done else 230.0
    rec = {"done": done, "ms": 1.0 if done else 200.0, "slot": page[0x44:0x48],
           "echo": page[5], "cmd_after": page[1], "overlap": 0, "job": dict(job, n=1, runid=1),
           "ticks": tk, "ticks_expected": win * 0.997, "window_ms": win}
    run = {"name": n, "records": [rec], "stop": None if done else "no done within 200 ms (job 0)",
           "n_jobs": 1, "ran": 1}
    if not done:
        run["alive_at_stop"] = {"advancing": "alive" in w, "ticks": [tk, tk + 1 if "alive" in w
                                                                     else tk, tk]}
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    words = dict(x.split("=") for x in make.ARM.split() if x.startswith(("pds=", "pdsat=")))
    addr = 0x30005100 if words.get("pdsat") == "fw14" else 0x30022000
    open(os.path.join(d, "kernel.log"), "w").write(
        "Nov 19 12:00:00 cedar kernel: gma500 0000:00:02.0: [drm] sgxfive: own task armed: slots "
        f"0x1, trc 0 (0: stock), exit 0x1974 (0: unknown), emit image {addr:#x} (0: none) "
        f"pds={words.get('pds', 'v1')} pdsat={words.get('pdsat', 'own')} (debugfs own_arm)\n")
    if done:
        gz(os.path.join(d, n + ".gate.json"), json.dumps({"ok": True}))
    else:
        gz(os.path.join(d, n + ".stop0-own_res.json"), json.dumps(page))
        gz(os.path.join(d, n + ".stop0-regs.txt"), regs("stop0-regs.txt.gz", tim=ts))
    rc, cls = (0, "ok") if done else (1, "fail")
    cases = ["\t".join(K.COLUMNS), "\t".join([n, "own", r["set"], r["risk"], "-", "owntask",
                                              r["args"], str(rc), cls, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d
