# SPDX-License-Identifier: MIT
"""tests/kept.py: kept stage directories for the scorer's tests, laid out as kit/run_stage.sh keeps
them (cases.tsv and void.tsv with kitscore.COLUMNS, readings.tsv, NAME.txt.gz, NAME.dmesg.gz):

  world()                          mock/world.py as a module
  answer(row, world, knobdir)      the world's answer to a row with its dbg: knobs written into a
                                   fake debugfs directory (as the runner writes them)
  from_world(stage, d, world)      every row of tables/STAGE.txt answered by mock/world.py
  write_row(d, stage, row, out, dmesg, rc)   one kept row from given text
  git_show(repo, rev, path)        a pinned file's bytes at its commit
"""
import gzip
import importlib.util
import os
import re
import shlex
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402

FAULT_RE = re.compile(r"BIF fault|faulted")
HANG_RE = re.compile(r"job [0-9]+ hung|hung|timed out waiting")
RESET_RE = re.compile(r"SGX reset: (after the fault clear )?BIF_FAULT")
KMSG = "gma500 0000:00:02.0: [drm] *ERROR* "
REPOS = {"resgx545": "/Users/jtorra/src/resgx545", "data": "/Users/jtorra/src/resgx545-data"}


def world():
    spec = importlib.util.spec_from_file_location("k2_world", os.path.join(KP, "mock/world.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git_show(repo, rev, path):
    return subprocess.run(["git", "-C", REPOS[repo], "show", f"{rev}:{path}"], check=True,
                          capture_output=True, timeout=60).stdout


def answer(row, w, knobdir):
    vals = {"vm_pte_addr": "0", "vm_pte_flags": "0"}
    for k in row["knobs"]:
        if k.startswith("dbg:"):
            name, v = k[4:].split("=", 1)
            vals[name] = v
    os.makedirs(knobdir, exist_ok=True)
    for name, v in vals.items():
        with open(os.path.join(knobdir, name), "w") as f:
            f.write(v + "\n")
    old = os.environ.get("FAKE_DBGREAL")
    os.environ["FAKE_DBGREAL"] = knobdir
    try:
        return w.answer(row["tool"], shlex.split(row["args"]), set(w_tokens(w, row)))
    finally:
        if old is None:
            del os.environ["FAKE_DBGREAL"]
        else:
            os.environ["FAKE_DBGREAL"] = old


def w_tokens(w, row):
    return row.get("_world", ("model",))


def classify(rc, out, dmesg, knobs):
    text = "\n".join(ln for ln in (out + "\n" + dmesg).splitlines() if not RESET_RE.search(ln))
    if FAULT_RE.search(text):
        return "fault"
    if HANG_RE.search(text):
        return "hang"
    if rc == 0:
        return "ok"
    if "expectdiff" in knobs and rc == 1 and re.search(r"^diff:", out, re.M):
        return "ok"
    return "fail"


def _head(d):
    os.makedirs(d, exist_ok=True)
    for f in ("cases.tsv", "void.tsv"):
        with open(os.path.join(d, f), "w") as fh:
            fh.write("\t".join(K.COLUMNS) + "\n")
    with open(os.path.join(d, "readings.tsv"), "w") as fh:
        fh.write("name\tkeys\treading\n")


def _gz(path, text):
    with gzip.open(path + ".gz", "wb") as f:
        f.write(text.encode())


def reading(out, dmesg):
    """hook_reading's keys, as run/hooks.sh prints them."""
    r = {}
    m = re.search(r"^job: ([a-z]*)", out, re.M)
    if m:
        j = m[1]
        if j == "failed" and re.search(r"^job: failed: job faulted", out, re.M):
            j = "faulted"
        elif j == "failed" and re.search(r"^job: failed: job hung", out, re.M):
            j = "hung"
        r["job"] = j
    for k, rx in (("hash", r"^target: [0-9]*x[0-9]* hash (0x[0-9a-f]*)"),
                  ("src", r"^copy: source at (0x[0-9a-f]*),"), ("fb", r"^layout: fb (0x[0-9a-f]*)"),
                  ("ro", r"^(PASS|FAIL) read-only-faults$")):
        m = re.search(rx, out, re.M)
        if m:
            r[k] = m[1]
    t = re.findall(r"BIF fault (0x[0-9a-f]*) at 0x[0-9a-f]*", dmesg)
    if t:
        r["rostat"] = t[-1]
    return r


def write_row(d, stage, row, out, dmesg, rc, cls=None):
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        _head(d)
    cls = cls or classify(rc, out, dmesg, row["knobs"])
    line = "\t".join([row["name"], stage, row["set"], row["risk"], " ".join(row["knobs"]), row["tool"],
                      row["args"], str(rc), cls, "-", "-", "1000000"]) + "\n"
    with open(os.path.join(d, "cases.tsv"), "a") as f:
        f.write(line)
    _gz(os.path.join(d, row["name"] + ".txt"), out)
    _gz(os.path.join(d, row["name"] + ".dmesg"), dmesg)
    if row["set"] == "control":
        rd = " ".join(f"{k}={v}" for k, v in reading(out, dmesg).items())
        with open(os.path.join(d, "readings.tsv"), "a") as f:
            f.write(f"{row['name']}\t{' '.join(row['reads'])}\t{rd}\n")
    return cls


def from_world(stage, d, tokens=("model",), only=None):
    w = world()
    _head(d)
    for row in K.table(KP, stage):
        if only is not None and row["name"] not in only:
            continue
        row = dict(row, _world=tokens)
        a = answer(row, w, os.path.join(d, ".knobs"))
        dmesg = "".join(KMSG + ln + "\n" for ln in a.get("kmsg", []))
        write_row(d, stage, row, a.get("out", ""), dmesg, a.get("rc", 0))
    return d
