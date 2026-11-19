# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds kept attempts for tests/test_score*.py, the way the kit's runner keeps
them. Not a test module (no test_ prefix).

own(root, tokens): stage own (one row, n0): n0.txt (fwtask_run.py run's JSON, the record with
ticks), n0.own_res.json.gz ({"page": [...]}), n0.snap0.regs.gz, n0.snap9.regs.gz, after a stop
n0.stop0-own_res.json.gz (a plain list) and n0.stop0-regs.txt.gz, after an ok end n0.gate.json.gz;
cases.tsv, void.tsv, readings.tsv. The registers are r37 A's kept snapshots (E1149: the same module
and job, pinned in session.toml), with 0x0acc and 0x0c08 replaced as the tokens say.
  done (every store, state 2, the job ends ok), stop (entry 0's slot 1, cmd 0 and X0, no done:
  r37 A's page shape), ticksN (the record's ticks; default 31 after done, 10 after a stop),
  gatebad (the gate's ok false), nox0, e0bad (slot 1 marker absent), pgbad (page dword 0 not
  ours), t0stop (snap0's 0x0acc stopped), bif (BIF_FAULT 0x90004 in snap9)

tim(root, tokens, rows=None): stage tim (one row, th): th.txt (t30's probe text, then regtimeline's
timeline of 0x0acc: `rows` [(t_ns, value)], by default 2000 running samples 3 us apart then
0x00abcde0), th.snap0.regs.gz and th.snap9.regs.gz (r37 A's, 0x0acc replaced), cases.tsv, ...
  snap9run (snap9's 0x0acc running), snap9other (0x00001234), scratchbad (one tim read 0),
  noscratch (no scratch lines), ivlN (TOTAL and samples giving N ns a sample, default 3100)"""
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
import pins  # noqa: E402

E1149 = "data:render/closing-r37-n3b-a/out/20261118-212949/own/c1-a."
MAGIC, FILL = 0x4E574F53, 0xDEADC0DE
M1, X0, M4 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302
TIM = 0x00ABCDE0
T_RUN = (0x0105B86C, 0x010527E7)


def regs(which, tim=None, bif=None):
    t = pins.blob(E1149 + which).decode()
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t.encode()


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def tsvs(d, stage, r, rc, cls):
    cases = ["\t".join(K.COLUMNS), "\t".join([r["name"], stage, r["set"], r["risk"],
                                              " ".join(r["knobs"]), r["tool"], r["args"], str(rc),
                                              cls, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")


def own(root, tokens):
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
    page[1], page[2], page[3] = 0, 0, 1                       # cmd (cleared), state, run id
    page[0x44:0x46] = [0 if "e0bad" in w else M1, 1]
    if "nox0" not in w:
        page[0x46] = X0
    done = "done" in w
    if done:
        page[0x50:0x52] = [M4, 1]
        page[2], page[5] = 2, 1
    tk = next((int(t[5:]) for t in w if re.fullmatch(r"ticks[0-9]+", t)), 31 if done else 10)
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": page}))
    gz(os.path.join(d, n + ".snap0.regs"), regs("snap0.regs.gz", tim=0 if "t0stop" in w else None))
    gz(os.path.join(d, n + ".snap9.regs"), regs("snap9.regs.gz",
                                                 bif=0x90004 if "bif" in w else None))
    win = 31.0 if done else 237.1
    rec = {"done": done, "ms": 1.0 if done else 200.0, "slot": page[0x44:0x48],
           "echo": page[5], "cmd_after": page[1], "overlap": 0, "job": dict(job, n=1, runid=1),
           "ticks": tk, "ticks_expected": win * 0.997, "window_ms": win}
    run = {"name": n, "records": [rec], "stop": None if done else "no done within 200 ms (job 0)",
           "n_jobs": 1, "ran": 1}
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    if done:
        gz(os.path.join(d, n + ".gate.json"), json.dumps({"ok": "gatebad" not in w}))
    else:
        gz(os.path.join(d, n + ".stop0-own_res.json"), json.dumps(page))
        gz(os.path.join(d, n + ".stop0-regs.txt"), regs("stop0-regs.txt.gz"))
    tsvs(d, "own", r, *((0, "ok") if done else (1, "fail")))
    return d


SCRATCH = [TIM, 0, TIM, TIM, TIM, TIM, 0, 0, 0, 0, TIM, TIM, TIM, TIM, 0, 0]


def running_rows(n=2000, step=3000, t0=900):
    return [(t0 + i * step, 0x01000000 | ((0x40000 - 1197 * i) % 400000)) for i in range(n)]


def tim_text(rows, w):
    name = "pds-timer-tim-host__0"
    sc = list(SCRATCH)
    if "scratchbad" in w:
        sc[3] = 0
    out = ["programs asm", f"probe {name}: scratch at 0x3e003000 (64 KiB)",
           f"probe {name}: o0 0x0da7a000 (2048 of 2048)"]
    if "noscratch" not in w:
        out += [f"probe {name}: scratch +0x{4 * i:03x} 0x{v:08x}" for i, v in enumerate(sc)]
    ivl = next((int(t[3:]) for t in w if re.fullmatch(r"ivl[0-9]+", t)), 3100)
    out.append(f"timeline: regs 0x0acc samples {int(0.06e9 / ivl)} seconds 0.06 start 5000600 "
               "end 106000000 rc 0")
    out += [f"tl {t} {v:08x}" for t, v in rows]
    return "\n".join(out) + "\n"


def tim(root, tokens, rows=None):
    w = set(tokens)
    d = os.path.join(root, "tim")
    os.makedirs(d, exist_ok=True)
    (r,) = K.table(KP, "tim")
    n = r["name"]
    if rows is None:
        rows = running_rows() + [(900 + 2000 * 3000, TIM)]
    t9 = T_RUN[0] if "snap9run" in w else 0x1234 if "snap9other" in w else TIM
    gz(os.path.join(d, n + ".txt"), tim_text(rows, w))
    gz(os.path.join(d, n + ".snap0.regs"), regs("snap0.regs.gz"))
    gz(os.path.join(d, n + ".snap9.regs"), regs("snap9.regs.gz", tim=t9))
    tsvs(d, "tim", r, 0, "ok")
    return d
