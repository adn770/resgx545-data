"""Readers shared by the R3-pixel scorers (R1-pixgeo's r1lib.py with the R3 additions at the end): kept files of a stage,
predictions, the timelines, STATUS2 reads, the burst of a regtimeline, the loop proof line, the vertex depth words.

Scorers are written before the run and frozen (run/freeze_r3.sh).  numpy is used for scratch scorers only.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True     # the scorers import modules of the data repo: no __pycache__ there (dataset digests)

import collections  # noqa: E402
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
        if c.get("class") == "skipped":
            return "skipped (hypothesis limit of its group or stage)"
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


HELD = ("heldout", "replicate")


def support(entries):
    """'held out: consistent [...], refuted [...]; repeat only: consistent [...], refuted [...]' from (model, set, ok)
    entries (ok True, False, or None = void).  A model counts as held out only on held-out and replicate jobs; jobs of
    set `repeat` (S1 post-hoc fits run again) are tallied apart and never lend held-out support."""
    def tally(sel):
        t = collections.defaultdict(list)
        for m, s, o in entries:
            if s in sel:
                t[m].append(o)
        cons = [f"{m} ({len(r)})" for m, r in t.items() if r and None not in r and all(r)]
        refd = [f"{m} ({sum(1 for x in r if x is False)} of {len(r)})" for m, r in t.items() if False in r]
        void = [m for m, r in t.items() if None in r and False not in r]
        return f"consistent {cons or 'none'}, refuted {refd or 'none'}" + (f", void runs for {void}" if void else "")
    return f"held out: {tally(HELD)}; repeat only: {tally(('repeat',))}"


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


# ---------------------------------------------------------------------------------------------- R3 additions
BG = 0xff203040
IDLE_CG, TICK_CG = 0x20, 0xccfa0           # 0x0008 (CLKGATESTATUS): idle, and the periodic tick's value


def status2(txt):
    """CR_EVENT_STATUS2 (reg 0x0118) from a kept debugfs regs file, or None."""
    m = re.search(r"^reg 0x0118 (0x[0-9a-fA-F]+)", txt or "", re.M)
    return int(m[1], 16) if m else None


def regs_file(k, n, which):
    b = k._gz(f"{n}.{which}.regs.txt.gz")
    return b.decode(errors="replace") if b is not None else None


def parse_o0(txt):
    """The probe's o0 line over the WHOLE output: ('same', value, count, total) for 'o0 0x... (N of N)'; ('mixed', [(value,
    count)...], None, None) for 'o0 mixed ...'; None if there is none."""
    m = re.search(r"o0 (0x[0-9a-f]{8}) \((\d+) of (\d+)\)", txt or "")
    if m:
        return ("same", int(m[1], 16), int(m[2]), int(m[3]))
    m = re.search(r"o0 mixed(.*)$", txt or "", re.M)
    if m:
        vals = [(int(a, 16), int(b)) for a, b in re.findall(r"(0x[0-9a-f]{8}) x(\d+)", m[1])]
        return ("mixed", vals, None, None)
    return None


def burst(txt):
    """The job's burst in a regtimeline output (registers 0x0008, 0x0118, 0x012c): {'B', 't6', 't7', 'stale'} in us from the burst's
    first sample, or None.  The burst is the LONGEST run of samples (up to and including the closing idle sample 0x20) that holds a
    value other than idle and the tick's 0xccfa0 (a fill has one; a triangle job may show a short setup run before it) (E431's reading: closing3/pixel/q082_timelines.py).  t6 / t7: the first sample at or
    after the burst's start with bit 6 / bit 7 of 0x0118 (the latch stays set until the reset, so it may show after the run).
    `stale`: the bit was already set before the burst."""
    m = re.search(r"^timeline: regs (.*?) samples", txt or "", re.M)
    if not m:
        return None
    regs = m[1].split()
    if "0x0008" not in regs or "0x0118" not in regs:
        return None
    i8, i118 = regs.index("0x0008"), regs.index("0x0118")
    rows = []
    for ln in txt.splitlines():
        if ln.startswith("tl "):
            p = ln.split()
            try:
                rows.append((int(p[1]), [int(x, 16) for x in p[2:]]))
            except ValueError:
                return None
    runs_, cur = [], []
    for t, v in rows:
        if v[i8] == IDLE_CG:
            if cur:
                cur.append((t, v))
                runs_.append(cur)
                cur = []
        else:
            cur.append((t, v))
    if cur:
        runs_.append(cur)
    job = [r for r in runs_ if any(v[i8] not in (IDLE_CG, TICK_CG) for _, v in r)]
    if not job:
        return None
    r = max(job, key=lambda run: run[-1][0] - run[0][0])          # the longest: a triangle's setup may show an earlier short one
    t0 = r[0][0]
    after = [(t, v) for t, v in rows if t >= t0]
    stale = any(v[i118] & 0x40 for t, v in rows if t < t0)

    def first(bit):
        return next(((t - t0) / 1000.0 for t, v in after if v[i118] & bit), None)

    return dict(B=(r[-1][0] - t0) / 1000.0, t6=first(0x40), t7=first(0x80), stale=stale)


_PB = None


def _pbdump():
    global _PB
    if _PB is None:
        import pbdump
        _PB = pbdump
    return _PB


def depth_words(param, tadata):
    """The stored depth word of every vertex of the first object ([] if none; None if the dump cannot be decoded), and the
    number of 32-bit words of the TA data and of the parameter buffer: (words, ok)."""
    pb = _pbdump()
    try:
        ws = pb.obj(param) if param else []
        o = pb.first_object(param, tadata) if param and tadata else None
    except Exception:
        return None
    if not ws or o is None:
        return []
    big = 0
    for i, w in enumerate(o["packed"]):
        big |= w << (32 * i)
    nv = len(o["vertices"])
    return [(big >> (80 * v + 48)) & 0xffffffff for v in range(nv)]


def count_word(blob, word):
    """How many aligned 32-bit words of blob equal word (the fallback depth proof when the object does not decode)."""
    if not blob:
        return 0
    n = len(blob) // 4
    return sum(1 for w in struct.unpack("<%dI" % n, blob[:4 * n]) if w == word)
