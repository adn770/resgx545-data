# SPDX-License-Identifier: MIT
"""tests/kept.py: kept stage directories for the scorer's tests, laid out as kit/run_stage.sh keeps
them (cases.tsv and void.tsv with kitscore.COLUMNS, readings.tsv, NAME.txt.gz and every file of the
job's work directory as NAME.FILE.gz):

  world()                        mock/world.py as a module
  answer(row, tokens, tmp)       the world's answer to a row, its dbg: knobs in a fake debugfs
  from_world(stage, root, tokens)   every row of tables/STAGE.txt answered by the world
  write_row(d, stage, row, out, rc, files)   one kept row from given text and files
  git_show(repo, path)           a pinned file's bytes at session.toml's commit"""
import gzip
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402

REPOS = {"resgx545": "/Users/jtorra/src/resgx545", "data": "/Users/jtorra/src/resgx545-data"}
CONF = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))


def world():
    spec = importlib.util.spec_from_file_location("k1_world", os.path.join(KP, "mock/world.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git_show(repo, path):
    return subprocess.run(["git", "-C", REPOS[repo], "show",
                           "%s:%s" % (CONF["freeze"][repo], path)], check=True,
                          capture_output=True, timeout=60).stdout


def answer(w, row, tokens, tmp):
    knobs = os.path.join(tmp, "dbg")
    os.makedirs(knobs, exist_ok=True)
    vals = {k: d["default"] for k, d in CONF["knobs"].items()}
    vals.update(dict(k[4:].split("=", 1) for k in row["knobs"] if k.startswith("dbg:")))
    for k, v in vals.items():
        open(os.path.join(knobs, k), "w").write(v + "\n")
    work = os.path.join(tmp, "w")
    os.makedirs(work, exist_ok=True)
    argv = shlex.split(row["args"].replace("$W", work).replace("$S", KP))
    old = os.environ.get("FAKE_DBGREAL")
    os.environ["FAKE_DBGREAL"] = knobs
    try:
        a = w.answer(row["tool"], argv, set(tokens))
    finally:
        if old is None:
            del os.environ["FAKE_DBGREAL"]
        else:
            os.environ["FAKE_DBGREAL"] = old
    files = {os.path.basename(p): (d if isinstance(d, bytes) else d.encode())
             for p, d in (a.get("files") or {}).items()}
    return a.get("rc", 0), a.get("out", ""), files


def reading(name, out):
    """run/hooks.sh's hook_reading, in Python (tests/test_twin.py holds the two equal)."""
    r = {}
    m = re.search(r"^job: ([a-z]*)", out, re.M)
    if m:
        r["job"] = m[1]
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]*)", out, re.M)
    if m:
        r["hash"] = m[1]
    m = re.search(r"^diff: (\d+) of ", out, re.M)
    if m:
        r["diff"] = m[1]
    m = re.search(r"; (\d+) layer texels in place, ", out, re.M)
    if m:
        r["inplace"] = m[1]
    if len(re.findall(r"^bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y$", out, re.M)) == 1:
        r["layer"] = "Y"
    n = len(re.findall(r"^probe [A-Za-z0-9_.-]*: row \d+:", out, re.M))
    if n:
        r["rows"] = str(n)
    return r


def _gz(path, data):
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(data)


def header(d):
    os.makedirs(d, exist_ok=True)
    for t in ("cases.tsv", "void.tsv"):
        p = os.path.join(d, t)
        if not os.path.exists(p):
            open(p, "w").write("\t".join(K.COLUMNS) + "\n")
    p = os.path.join(d, "readings.tsv")
    if not os.path.exists(p):
        open(p, "w").write("name\treads\treading\n")


def write_row(d, stage, row, out, rc, files, cls=None):
    header(d)
    n = row["name"]
    _gz(os.path.join(d, n + ".txt.gz"), out.encode())
    for f, data in files.items():
        _gz(os.path.join(d, "%s.%s.gz" % (n, f)), data)
    if cls is None:
        cls = "ok" if rc == 0 or (rc == 1 and "expectdiff" in row["knobs"] and
                                  re.search(r"^job: ok$", out, re.M) and
                                  re.search(r"^diff:", out, re.M)) else "fail"
    with open(os.path.join(d, "cases.tsv"), "a") as f:
        f.write("\t".join([n, stage, row["set"], row["risk"], " ".join(row["knobs"]), row["tool"],
                           row["args"], str(rc), cls, "-", "-", "999999"]) + "\n")
    if row["set"] == "control" and cls == "ok":
        r = reading(n, out)
        with open(os.path.join(d, "readings.tsv"), "a") as f:
            f.write("%s\t%s\t%s\n" % (n, " ".join(row["reads"]),
                                      " ".join("%s=%s" % kv for kv in r.items())))


def from_world(stage, root, tokens=("model",), w=None):
    w = w or world()
    d = os.path.join(root, stage)
    header(d)
    for row in K.table(KP, stage):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, files = answer(w, row, tokens, tmp)
        write_row(d, stage, row, out, rc, files)
    return d
