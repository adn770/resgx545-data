# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""kitscore.py: what a kit session's scorer reads (tools/closing/kit, HACKING.md "Session kit").
Standard library only; the verdict rules stay in scorekit.py. A scorer imports both from the
session's kit/ (byte copies, pinned by commit in FROZEN.commits).

  table(kp, stage)        the rows of tables/STAGE.txt: dicts name, set, risk, knobs, tool, args,
                          reads (the control's keys)
  predictions(kp, stage)  {case: {quantity: {model: value}}} of predictions/STAGE.tsv
  rows(d, name)           {name: row} of a kept cases.tsv or void.tsv (rc an int)
  text(d, name)           a kept file, plain or gzipped, as text ("" when absent)
  readings(d)             {control: {key: value}} of readings.tsv, the runner's premise readings
  premise(kp, stage, d)   the STOP lines of the premise: every control row of the table must have
                          run and read every key it declares (scorekit.premise_stops)
  controls(kp, stage)     {name: (keys, row)} of the table's control rows, for
                          scorekit.refuse_unreadable
  param_hash(b)           a param buffer dump's stream-bounded sha256 (hex; None for None): the
                          dwords as "%08x\n" lines, a terminate word 0xc0000000 that follows
                          another written 00000000, so each stream ends at its first terminate
                          word and the words past it (stale, r19-k0) are not compared;
                          lib_kit.sh param_hash FILE is its twin (r19-k0b's pmask, E1077)
  completed(row)          a kept row whose job ran to its end: class ok, with rc 0, rc 1 of an
                          `expectdiff` row (the runner took it as a reading only with `job: ok`
                          and a diff line) or the rc of an expected outcome its knobs declare
                          (OUTCOMES, `expect:NAME`)

OUTCOMES: {NAME: (rc, line)} the expected outcomes a row may declare with the knob word
`expect:NAME`: a job that ends with that rc and prints that line is a completed job, not a
failure (kit/run_stage.sh classifies it ok the same way). rc3-overflow: a `probe` DPM cell's
normal end, "scene overflowed the parameter buffer" (R7-dpm's runner took it the same way).
"""
import gzip
import hashlib
import os

import scorekit

OUTCOMES = {"rc3-overflow": (3, "scene overflowed the parameter buffer")}
COLUMNS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
           "fault_word", "free_kb")


def _read(path):
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rb") as f:
            return f.read()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


TERMINATE = 0xC0000000


def param_hash(b):
    """A param buffer dump's sha256 bounded by its streams: lib_kit.sh param_hash's twin."""
    if b is None:
        return None
    h, prev = hashlib.sha256(), False
    for i in range(0, len(b) - len(b) % 4, 4):
        w = int.from_bytes(b[i:i + 4], "little")
        t = w == TERMINATE
        h.update(b"00000000\n" if t and prev else b"%08x\n" % w)
        prev = t
    return h.hexdigest()


def text(d, name):
    b = _read(os.path.join(d, name))
    return "" if b is None else b.decode(errors="replace")


def table(kp, stage):
    out = []
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        words = knobs.split()
        reads = ()
        for w in words:
            if w.startswith("reads:"):
                reads = tuple(w[len("reads:"):].split(","))
        out.append(dict(name=name, set=sset, risk=risk, knobs=words, tool=tool, args=args,
                        reads=reads))
    return out


def predictions(kp, stage):
    out = {}
    lines = open(os.path.join(kp, "predictions", stage + ".tsv")).read().splitlines()
    for ln in lines[1:]:
        if not ln.strip():
            continue
        f = ln.split("\t")
        out.setdefault(f[0], {}).setdefault(f[1], {})[f[3]] = f[2]
    return out


def rows(d, name="cases.tsv"):
    out = {}
    for ln in text(d, name).splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < len(COLUMNS) or not f[0]:
            continue
        r = dict(zip(COLUMNS, f))
        r["rc"] = int(r["rc"])
        out[f[0]] = r
    return out


def readings(d):
    out = {}
    for ln in text(d, "readings.tsv").splitlines()[1:]:
        f = ln.split("\t")
        if f and f[0]:
            r = f[2] if len(f) > 2 else ""
            out[f[0]] = dict(w.split("=", 1) for w in r.split() if "=" in w)
    return out


def controls(kp, stage):
    return {r["name"]: (r["reads"], r) for r in table(kp, stage) if r["set"] == "control"}


def premise(kp, stage, d):
    want = {n: keys for n, (keys, _) in controls(kp, stage).items()}
    return scorekit.premise_stops(want, readings(d))


def completed(row):
    """A kept row (rows()) whose job ran to its end: class ok, and rc 0, rc 1 of an
    `expectdiff` row or the rc of an expected outcome its knobs declare."""
    if row.get("class") != "ok":
        return False
    if row["rc"] == 0:
        return True
    words = row.get("knobs", "")
    words = words.split() if isinstance(words, str) else words
    if row["rc"] == 1 and "expectdiff" in words:
        return True
    return any(w.startswith("expect:") and OUTCOMES.get(w[len("expect:"):], (None,))[0] == row["rc"]
               for w in words)
