# SPDX-License-Identifier: MIT
"""tests/kept.py: kept stage directories for the scorer's tests, laid out as kit/run_stage.sh keeps
them (cases.tsv and void.tsv with kitscore.COLUMNS, readings.tsv, NAME.txt, NAME.<file of $W>):

  from_world(stage, d, world)          every row of tables/STAGE.txt answered by mock/world.py
                                       (a row's dbg: words written into a fake debugfs for t9)
  from_files(stage, d, {name: {suffix: path}})   kept files of a published session under our names
  blob(path)                           a resgx545-data file at the pinned commit (pinned only)
(after r9-lgeo's tests/kept.py)"""
import gzip
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")


def _world():
    import importlib.util
    spec = importlib.util.spec_from_file_location("r10g_world", os.path.join(KP, "mock/world.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _line(t, stage, rc, cls):
    return "\t".join([t["name"], stage, t["set"], t["risk"], " ".join(t["knobs"]), t["tool"], t["args"],
                      str(rc), cls, "-", "-", "1000000"]) + "\n"


def _head(d):
    for f in ("cases.tsv", "void.tsv"):
        with open(os.path.join(d, f), "w") as fh:
            fh.write("\t".join(K.COLUMNS) + "\n")
    with open(os.path.join(d, "readings.tsv"), "w") as fh:
        fh.write("name\treads\treading\n")


def from_world(stage, d, world, only=None):
    W = _world()
    os.makedirs(d, exist_ok=True)
    _head(d)
    dbg = tempfile.mkdtemp(prefix="r10g-dbg.")
    old = os.environ.get("FAKE_DBGREAL")
    os.environ["FAKE_DBGREAL"] = dbg
    try:
        for t in K.table(KP, stage):
            if only and t["name"] not in only:
                continue
            for k in os.listdir(dbg):
                os.remove(os.path.join(dbg, k))
            for w in t["knobs"]:
                if w.startswith("dbg:"):
                    k, v = w[4:].split("=", 1)
                    with open(os.path.join(dbg, k), "w") as fh:
                        fh.write(v + "\n")
            work = os.path.join(d, ".w-" + t["name"])
            os.makedirs(work, exist_ok=True)
            argv = shlex.split(t["args"].replace("$S", KP).replace("$W", work))
            a = W.answer(t["tool"], argv, set(world.split(",")))
            rc, out = a.get("rc", 0), a.get("out", "")
            cls = "ok" if rc == 0 or (rc == 1 and "expectdiff" in t["knobs"] and "\njob: ok" in "\n" + out
                                      and "\ndiff:" in "\n" + out) else "fail"
            with open(os.path.join(d, t["name"] + ".txt"), "w") as fh:
                fh.write(out)
            for p, data in a.get("files", {}).items():
                with open(os.path.join(d, t["name"] + "." + os.path.basename(p)), "wb") as fh:
                    fh.write(data)
            with open(os.path.join(d, "cases.tsv"), "a") as fh:
                fh.write(_line(t, stage, rc, cls))
            shutil.rmtree(work)
    finally:
        shutil.rmtree(dbg)
        if old is None:
            os.environ.pop("FAKE_DBGREAL", None)
        else:
            os.environ["FAKE_DBGREAL"] = old
    return d


def blob(path):
    """A resgx545-data file at session.toml's pinned commit; a file that session.toml [freeze] pins
    does not name is refused (every file a replay reads is pinned)."""
    with open(os.path.join(KP, "session.toml"), "rb") as f:
        fz = tomllib.load(f)["freeze"]
    assert "data:" + path in fz["pins"], "not pinned in session.toml: data:" + path
    return subprocess.run(["git", "-C", DATA, "show", "%s:%s" % (fz["data"], path)], capture_output=True,
                          check=True, timeout=60).stdout


def data(path):
    b = blob(path)
    return gzip.decompress(b) if path.endswith(".gz") else b


def from_files(stage, d, files, rc=0):
    """files: {our row name: {suffix: resgx545-data path (plain or .gz)}}, read at the pinned
    commit; rows not named did not run."""
    os.makedirs(d, exist_ok=True)
    _head(d)
    tab = {t["name"]: t for t in K.table(KP, stage)}
    for name, fs in files.items():
        for suf, p in fs.items():
            with open(os.path.join(d, name + suf), "wb") as fh:
                fh.write(data(p))
        with open(os.path.join(d, "cases.tsv"), "a") as fh:
            fh.write(_line(tab[name], stage, rc, "ok"))
    return d


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def summary(lines, key):
    """The SUMMARY lines that contain key."""
    return [ln for ln in lines if ln.startswith("SUMMARY") and key in ln]
