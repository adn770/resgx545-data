"""Synthetic kept directories for the scorer tests: the same files the runner keeps (cases.tsv, NAME.txt.gz,
NAME.dmesg.gz, NAME.after.buf09.bin.gz, dumps), with a register timeline the tests control."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import pathlib  # noqa: E402
import struct  # noqa: E402

HDR = "name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\tnote\n"


class Dir:
    def __init__(self, d, stage="x"):
        self.d = pathlib.Path(d)
        self.d.mkdir(parents=True, exist_ok=True)
        self.stage = stage
        self.rows = []

    def job(self, name, out="", rc=0, cls="ok", dmesg="", buf09=None, args="", dumps=None, P="-"):
        (self.d / f"{name}.txt.gz").write_bytes(gzip.compress(out.encode()))
        (self.d / f"{name}.dmesg.gz").write_bytes(gzip.compress(dmesg.encode()))
        if buf09 is not None:
            w = list(buf09) + [0] * (59 - len(buf09))
            (self.d / f"{name}.after.buf09.bin.gz").write_bytes(gzip.compress(struct.pack("<59I", *w)))
        for suf, data in (dumps or {}).items():
            (self.d / f"{name}.{suf}.gz").write_bytes(gzip.compress(data))
        self.rows.append("\t".join((name, self.stage, "heldout", "safe", P, "stophang", "-", args, str(rc), cls, "-")))
        (self.d / "cases.tsv").write_text(HDR + "\n".join(self.rows) + "\n")
        return self


def timeline(regs, rows, start=100):
    """Tool-style text: `timeline: regs ...` and `tl TIME v v v` rows (rows: lists of ints, one per register)."""
    t = ["timeline: regs " + " ".join(regs) + f" samples {len(rows)} seconds 0 start {start} end {start + 10 * len(rows)} rc 0"]
    for i, r in enumerate(rows):
        t.append(f"tl {start + 10 * i} " + " ".join(f"{v:08x}" for v in r))
    return "\n".join(t) + "\n"


def dpm_regs(with_072c):
    base = ["0x0624", "0x0628", "0x0654", "0x0658", "0x065c", "0x0660", "0x0720", "0x0724"]
    return base + (["0x0728", "0x072c"] if with_072c else [])


def dpm_job_text(P_thr0, peaks, partials=0, with_072c=True, count=1, bad_072c=None, extra=""):
    """Timeline of a job at status ceiling P_thr0: run 1 climbs peaks[0] pages (0x0724 low half), then `partials` partial
    renders (0x0658 bit 0 high) each followed by another climb to peaks[i].  0x072c holds (count << 16) | count while the
    TA runs (or bad_072c).  Returns the tool text."""
    regs = dpm_regs(with_072c)
    rows = []

    def row(status, p658):
        r = [P_thr0, 0, 0, p658, 0, 2, 0, (status << 16) | status]
        if with_072c:
            v = bad_072c if bad_072c is not None else ((count << 16) | count if status else 0)
            r += [0, v]
        rows.append(r)
    row(0, 0)
    for run in range(partials + 1):
        for s in range(1, peaks[run] + 1):
            row(s, 0)
        if run < partials:
            row(peaks[run], 1)
            row(peaks[run], 1)
            row(0, 0)
    row(0, 0)
    return extra + timeline(regs, rows)
