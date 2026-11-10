"""Readers shared by the S1 scorers: kept files of a stage, predictions, the timelines, the control block.

Scorers are written before the run and frozen (run/freeze_s1.sh).  numpy is used for scratch scorers only.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import pathlib
import re
import struct
import sys

S1 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545/tools/usse-asm"))


class Kept:
    """The kept files of one stage: NAME.txt.gz (the tool's output), NAME.dmesg.gz, NAME.after.buf09.bin.gz and the
    dumps NAME.<file>.gz; cases.tsv lists the jobs."""

    def __init__(self, d):
        self.d = pathlib.Path(d)
        self.cases = []
        cs = self.d / "cases.tsv"
        if cs.exists():
            lines = cs.read_text().splitlines()
            hdr = lines[0].split("\t")
            self.cases = [dict(zip(hdr, ln.split("\t"))) for ln in lines[1:]]

    def names(self):
        return [c["name"] for c in self.cases]

    def case(self, name):
        return next((c for c in self.cases if c["name"] == name), {})

    def void(self, name, dumps=()):
        """Why a job's result must not be read, or None.  Tested BEFORE any match: a missing or empty output, no recorded
        rc, an rc that is not a result of the tool (2 usage, 124 timeout, 126/127, a signal), or a missing dump."""
        c = self.case(name)
        txt = self.out(name)
        if txt is None:
            return "no output kept"
        if len(txt.strip()) < 20:
            return "empty output"
        rc = c.get("rc", "")
        if rc == "":
            return "no rc recorded"
        if int(rc) in (2, 124, 125, 126, 127) or int(rc) >= 128:
            return f"rc {rc} is not a result of the tool"
        for suf in dumps:
            if self.dump(name, suf) is None:
                return f"dump {suf} missing"
        return None

    def _gz(self, n):
        p = self.d / n
        return gzip.open(p).read() if p.exists() else None

    def out(self, name):
        b = self._gz(f"{name}.txt.gz")
        return b.decode(errors="replace") if b is not None else None

    def dmesg(self, name):
        b = self._gz(f"{name}.dmesg.gz")
        return b.decode(errors="replace") if b is not None else ""

    def buf09(self, name):
        b = self._gz(f"{name}.after.buf09.bin.gz")
        return list(struct.unpack("<59I", b[:236])) if b and len(b) >= 236 else None

    def dump(self, name, suffix):
        """A dump file by its tail, e.g. 'param.bin' (probe: NAME.<prog>.param.bin) or 'tri.1.tadata.bin'."""
        for p in sorted(self.d.glob(f"{name}.*{suffix}.gz")):
            stem = p.name[len(name) + 1:]
            if stem.endswith(suffix + ".gz") and not stem.startswith(("after.", "held.")):
                return gzip.open(p).read()
        return None

    def depth(self, name, render=1):
        return self._gz(f"{name}.depth.{render}.bin.gz")


def load_preds(path=None, stage=None):
    p = pathlib.Path(path) if path else S1 / "predictions" / f"{stage}.tsv"
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for ln in p.read_text().splitlines()[1:]:
        c, q, v, m, st = ln.split("\t")
        out[c][q].append((v, m, st))
    return out


# ---- registers timeline (regtimeline output kept inside NAME.txt) -------------------------------------
def timeline(text):
    m = re.search(r"^timeline: regs (.*?) samples", text or "", re.M)
    if not m:
        return None
    regs = m[1].split()
    rows = [[int(x, 0) if i == 0 else int(x, 16) for i, x in enumerate(ln.split()[1:])]
            for ln in text.splitlines() if ln.startswith("tl ")]
    return regs, rows


def reg_series(tl, reg):
    regs, rows = tl
    i = regs.index(reg) + 1
    return [r[i] for r in rows]


def runs(tl):
    """(status at each partial render's start, peak status of each TA run) from the 0x0658 bit 0 stretches."""
    regs, rows = tl
    ip, ist = regs.index("0x0658") + 1, regs.index("0x0724") + 1
    prs, peaks, cur, inpr = [], [], 0, False
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                prs.append(r[ist] & 0xffff)
                peaks.append(cur)
                cur = 0
                inpr = True
            continue
        inpr = False
        cur = max(cur, r[ist] & 0xffff)
    peaks.append(cur)
    return prs, peaks


def peak_status(tl):
    return max((v & 0xffff) for v in reg_series(tl, "0x0724")) if tl else None


def first_sample(tl, reg):
    s = reg_series(tl, reg)
    return s[0] if s else None


def knob_value(tl, text):
    """The 0x0624 value of THIS job: the first row at or after the header's `start` (the tool's start; sampling begins
    300 ms earlier and shows the previous job's value) whose 0x0724 low half is non-zero.  None if there is none."""
    m = re.search(r"^timeline: .* start (\d+) end", text or "", re.M)
    if not tl or not m:
        return None
    start = int(m[1])
    regs, rows = tl
    i24, i4 = regs.index("0x0624") + 1, regs.index("0x0724") + 1
    for r in rows:
        if r[0] >= start and (r[i4] & 0xffff):
            return r[i24]
    return None


# ---- tool output ------------------------------------------------------------------------------------
def rows_of(text):
    """Pixel rows of 'row N: 0x... ...' or 'probe NAME: row N: hex ...' lines, in order."""
    r = {}
    for ln in (text or "").splitlines():
        m = re.search(r"row (\d+): (.*)$", ln)
        if m:
            r[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [r[i] for i in sorted(r)]


def pixel_sha(rows):
    vals = [f"{v:08x}" for row in rows for v in row]
    return hashlib.sha256(",".join(vals).encode()).hexdigest()


def outcome(text, dmesg=""):
    t = (text or "") + "\n" + dmesg
    if re.search(r"hung", t):
        return "hang"
    if re.search(r"faulted|BIF fault|bif fault", t, re.I):
        return "fault"
    if "scene overflowed" in t:
        return "overflow"
    if text is None:
        return "missing"
    return "ok"


def f32v(b):
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


def table(rows, header):
    w = [max(len(str(x)) for x in col) for col in zip(header, *rows)] if rows else [len(h) for h in header]
    fmt = "  ".join(f"{{:<{x}}}" for x in w)
    return "\n".join([fmt.format(*header)] + [fmt.format(*[str(c) for c in r]) for r in rows])
