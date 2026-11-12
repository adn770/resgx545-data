# SPDX-License-Identifier: MIT
"""mockstage.py: a kept stage directory built by running the FROZEN TABLE's own commands through the argv-driven fake tool
(tests/fake_o4.py for the pixel stages, tests/fake_rw.py for g6-rw*), in a world given by environment variables.  The rows are taken
from tables/STAGE.txt as they are: $S is bins/, $W a fresh work directory; the fake answers by argv and program bytes only.  The
outputs and dumps are kept as the runner keeps them (NAME.txt.gz, NAME.NAME.param.bin.gz ...) with a cases.tsv (rc, class ok).
  build(stage, env, only=None) -> directory     (cached per stage and world inside one test process)"""
import concurrent.futures
import gzip
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
R6 = HERE.parent
(R6 / "debug/tmp").mkdir(parents=True, exist_ok=True)
_cache = {}


def rows(stage):
    return [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
            for ln in (R6 / "tables" / f"{stage}.txt").read_text().splitlines() if ln and not ln.startswith("#")]


def run_one(r, env, root):
    w = pathlib.Path(tempfile.mkdtemp(prefix="job-", dir=root))
    (w / "dump").mkdir()
    a = shlex.split(r["args"].replace("$W", str(w)).replace("$S", str(R6 / "bins")))
    fake = HERE / ("fake_rw.py" if "--tri vtxuse" in r["args"] else "fake_o4.py")
    p = subprocess.run([sys.executable, str(fake)] + a, capture_output=True, text=True, env=env)
    return r, p.returncode, p.stdout + p.stderr, w


def build(stage, env=None, only=None):
    key = (stage, tuple(sorted((env or {}).items())), tuple(only or ()))
    if key in _cache:
        return _cache[key]
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env or {}))
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"mock-{stage}-", dir=R6 / "debug/tmp"))
    kept = root / "kept"
    kept.mkdir()
    rs = [r for r in rows(stage) if only is None or r["name"] in only]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda r: run_one(r, e, root), rs))
    lines = ["name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tnote"]
    for r, rc, out, w in res:
        n = r["name"]
        with gzip.open(kept / f"{n}.txt.gz", "wb") as f:
            f.write(out.encode())
        for d in (w / "dump").iterdir():
            with gzip.open(kept / f"{n}.{d.name}.gz", "wb") as f:
                f.write(d.read_bytes())
        lines.append("\t".join([n, stage, r["set"], r["risk"], r["knobs"], r["rt"], r["args"], str(rc), "ok" if rc == 0 else "fail", "-"]))
    (kept / "cases.tsv").write_text("\n".join(lines) + "\n")
    _cache[key] = kept
    return kept
