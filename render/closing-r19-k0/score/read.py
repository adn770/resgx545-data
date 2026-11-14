# SPDX-License-Identifier: MIT
"""read.py: r19-k0's reader of one job (the tool's text with regtimeline's block, and the files the
job wrote, as kept: NAME.txt, NAME.words.K.txt, NAME.ta3d.K.bin, NAME.depth-store.1.bin,
NAME.p1139-green.{param,tadata}.bin, NAME.tri.K.{param,tadata}.bin; plain or gzipped).

From the timeline (score/r10read.py, r10-dpm's reader, byte for byte):
  nparts, knob, sK      partial renders (0x0658 stretches), 0x0624 at the first sample with pages
                        (the knob proof: P - 0x22), the first TA run's page steps S_k
  tl624                 the distinct values of 0x0624 in order of appearance, from the header's start
From the tool's text:
  ovfK                  1 if render K overflowed (`tri WxH #K: overflowed` or, a geometry kick,
                        its `job: failed: scene overflowed`), 0 if it completed
  thrK                  0x0624 of the --regs block printed at snapshot K (after render K)
  jobfail               the first `job: failed:` line that is not an overflow (a hang, a fault)
  drawn, dst            the last render's triangle pixels; the depth store's changed dwords
From the files: pbK (pb:10-13 of words.K.txt), d35/d37/d38 (dwords of ta3d.1.bin), dsha (sha256
of depth-store.1.bin), param/tadata (sha256 of the probe's dumps), dumps ({file: sha256} of the
geometry dumps)."""
from __future__ import annotations

import gzip
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r10read as R10  # noqa: E402

OVF = "scene overflowed the parameter buffer"


def raw(d, name):
    """A kept file's bytes (plain or gzipped), None when absent."""
    p = os.path.join(d, name)
    if os.path.exists(p + ".gz"):
        with gzip.open(p + ".gz", "rb") as f:
            return f.read()
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    return None


def tool_text(text: str) -> dict:
    """The tool's own lines: overflow per render, 0x0624 per snapshot, a failed job, drawn, dst."""
    r = {"ovf": {}, "thr": {}, "jobfail": None, "drawn": None, "dst": None}
    snap = None
    jobs = []
    for ln in text.splitlines():
        m = re.match(r"tri: registers at snapshot (\d+)$", ln)
        if m:
            snap = int(m.group(1))
            continue
        m = re.match(r"reg 0x0624 0x([0-9a-f]{8})$", ln)
        if m and snap is not None and snap not in r["thr"]:   # the snapshot's own block
            r["thr"][snap] = int(m.group(1), 16)
            continue
        if ln.startswith("job: "):
            jobs.append(ln)
            if ln.startswith("job: failed:") and OVF not in ln and r["jobfail"] is None:
                r["jobfail"] = ln[len("job: failed: "):]
            continue
        m = re.match(r"tri \d+x\d+ #(\d+): (overflowed, )?(\d+) triangle", ln)
        if m:
            k = int(m.group(1))
            r["ovf"][k] = int(bool(m.group(2)))
            r["drawn"] = int(m.group(3))
            continue
        m = re.match(r"tri \d+x\d+ #(\d+): geometry only", ln)
        if m:
            r["ovf"][int(m.group(1))] = 0
            continue
        m = re.match(r"depth store #1: \d+ dwords, (\d+) changed", ln)
        if m:
            r["dst"] = int(m.group(1))
    return r


def pb_words(b: bytes | None):
    if b is None:
        return None
    w = {}
    for ln in b.decode(errors="replace").splitlines():
        m = re.match(r"pb:(\d+)=0x([0-9a-f]+)$", ln.strip())
        if m:
            w[int(m.group(1))] = int(m.group(2), 16)
    if not all(k in w for k in (10, 11, 12, 13)):
        return None
    return ",".join(f"0x{w[k]:x}" for k in (10, 11, 12, 13))


def dword(b: bytes | None, i: int):
    if b is None or len(b) < 4 * (i + 1):
        return None
    return int.from_bytes(b[4 * i:4 * i + 4], "little")


def sha(b):
    return None if b is None else hashlib.sha256(b).hexdigest()


ALL = (".txt", ".words.0.txt", ".words.1.txt", ".words.2.txt", ".words.3.txt", ".ta3d.1.bin",
       ".depth-store.1.bin", ".p1139-green.param.bin", ".p1139-green.tadata.bin",
       ".tri.1.param.bin", ".tri.1.tadata.bin", ".tri.2.param.bin", ".tri.2.tadata.bin",
       ".tri.param.bin", ".tri.tadata.bin")


def reading(d: str, name: str, allowed=ALL) -> dict:
    """Every quantity of one kept job from the files of `allowed` (suffixes; the scorer passes its
    stage's REQUIRED ones); a key is absent (or None) when the job did not give it."""
    def get(suf):
        return raw(d, name + suf) if suf in allowed else None
    tb = get(".txt")
    text = tb.decode(errors="replace") if tb is not None else ""
    out = {}
    t = R10.reading(text)
    if not t.get("void"):
        out.update(nparts=t["nparts"], knob=t["knob"], gmax=t["gmax"])
        for k, v in t["S"].items():
            out[f"s{k}"] = v
        regs, rows, start = R10.parse(text)
        seq = []
        for ts, v in rows:
            if ts >= start and 0x624 in v and (not seq or seq[-1] != v[0x624]):
                seq.append(v[0x624])
        out["tl624"] = seq
    tt = tool_text(text)
    for k, v in tt["ovf"].items():
        out[f"ovf{k}"] = v
    for k, v in tt["thr"].items():
        out[f"thr{k}"] = v
    out["jobfail"] = tt["jobfail"]
    out["drawn"], out["dst"] = tt["drawn"], tt["dst"]
    for k in range(0, 4):
        pw = pb_words(get(f".words.{k}.txt"))
        if pw:
            out[f"pb{k}"] = pw
    ta = get(".ta3d.1.bin")
    for i in (35, 37, 38):
        out[f"d{i}"] = dword(ta, i)
    out["dsha"] = sha(get(".depth-store.1.bin"))
    out["param"] = sha(get(".p1139-green.param.bin"))
    out["tadata"] = sha(get(".p1139-green.tadata.bin"))
    dumps = {}
    for suf in ALL:
        if suf.startswith(".tri."):
            s_ = sha(get(suf))
            if s_:
                dumps[suf[1:-4]] = s_
    out["dumps"] = dumps
    return out


def files_of(name: str, allowed=ALL) -> list:
    """The kept names reading() opens for a job (each plain or .gz)."""
    return [name + suf for suf in ALL if suf in allowed]


def words(r: dict) -> dict:
    """The `k=v` words run/hooks.sh prints (its awk twin; tests/test_read.py holds them equal)."""
    out = {}
    for k in ("nparts", "drawn", "dst"):
        if r.get(k) is not None:
            out[k] = str(r[k])
    if r.get("knob") is not None:
        out["knob"] = f"0x{r['knob']:x}"
    for k in (1, 2, 3):
        if r.get(f"ovf{k}") is not None:
            out[f"ovf{k}"] = str(r[f"ovf{k}"])
        if r.get(f"thr{k}") is not None:
            out[f"thr{k}"] = f"0x{r[f'thr{k}']:x}"
    for k in ("dsha", "param", "tadata"):
        if r.get(k):
            out[k] = r[k][:16]
    return out
