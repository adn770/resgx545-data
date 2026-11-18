# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of r36-n3's stage own for tests/test_score.py, the way
the kit's runner keeps it: per row NAME.txt (fwtask_run.py run's JSON), NAME.own_res.json.gz
({"page": [...]}), NAME.snap0.regs.gz (with the kernel's ta3dctl lines), NAME.gate.json.gz, and
cases.tsv, void.tsv, readings.tsv. The task's stores come from mock/world.py's own_res (the fake
the kit's mock runs) under the world's tokens, plus these test-only tokens:
  split   pa2 is 0 (only pa0 = V0: a split landing)      pa1bad  pa1 = V0 (a stray douta)
  sa1bad  sa1 is 0                                        none    entry 1 never runs: the first
  nosnapv snap0 without ta3dctl lines                             row's job is not done (class
  movedv  the snap0's V0-V3 differ from the fallback              fail), the stage stops there
  short   only the first 6 rows kept (a stop after h4)
Not a test module (no test_ prefix)."""
import gzip
import importlib.util
import json
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock", "world.py"))
world = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(world)
MOVED = (0x32104000, 0x32105000, 0x32102000, 0x00000000)


def snap(v, with_v=True):
    lines = ["sgxfive regs 1", "state loaded 1 live 1 sw_events 0 bif_faults 0",
             "reg 0x0c04 0x00080000", "reg 0x0c08 0x00000000"]
    if with_v:
        lines += [f"ta3dctl 0x{4 * i:02x} 0x{x:08x}" for i, x in enumerate(v)]
    return ("\n".join(lines) + "\nend\n").encode()


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def build(root, tokens=("model",)):
    """root/own/ under the world `tokens`; returns that directory."""
    os.environ["FAKE_DIR"] = os.path.join(root, "fake")
    os.makedirs(os.environ["FAKE_DIR"], exist_ok=True)
    w = set(tokens)
    d = os.path.join(root, "own")
    os.makedirs(d, exist_ok=True)
    v = MOVED if "movedv" in w else world.V
    page = [0] * 1024
    page[0] = 0x4E574F53
    cases = ["\t".join(K.COLUMNS)]
    tab = K.table(KP, "own")
    if "short" in w:
        tab = tab[:6]
    for i, r in enumerate(tab, 1):
        n = r["name"]
        job = json.loads(r["args"])
        for k, vals in job["params"].items():
            page[int(k):int(k) + len(vals)] = vals
        page[0x44:0x48] = [0xDEADC0DE] * 4          # fwtask_run.py's initfill of slot 1
        page[3], page[1], page[2] = i, 1, 0
        got = world.own_res(1, job["params"], w)
        if "none" in w:
            got = {k: x for k, x in got.items() if k < 0x48}
        if "movedv" in w:
            got.update({0x48: MOVED[0], 0x4a: MOVED[2]})
            got.update({0x4c + j: MOVED[j] for j in range(4)})
        if "split" in w:
            got[0x4a] = 0
        if "pa1bad" in w:
            got[0x49] = v[0]
        if "sa1bad" in w:
            got[0x4d] = 0
        for k, x in got.items():
            page[k] = x
        done = "none" not in w
        if done:
            page[2], page[5] = 2, i
        gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": page}))
        gz(os.path.join(d, n + ".snap0.regs"), snap(v, "nosnapv" not in w))
        run = {"name": n, "records": [{"done": done, "slot": page[0x44:0x48], "echo": page[5],
                                        "cmd_after": page[1]}], "stop": None if done else
               "no done within 200 ms (job 0)", "n_jobs": 1, "ran": 1}
        gz(os.path.join(d, n + ".txt"), json.dumps(run))
        rc, cls = (0, "ok") if done else (1, "fail")
        if done:
            gz(os.path.join(d, n + ".gate.json"), json.dumps({"ok": True}))
        cases.append("\t".join([n, "own", r["set"], r["risk"], "-", "owntask", r["args"],
                                str(rc), cls, "-", "-", "1000"]))
        if not done:
            break
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d
