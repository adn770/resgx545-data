# SPDX-License-Identifier: MIT
"""Synthetic kept directories for the R3-pixel scorer tests: a stage's cases.tsv, the tool outputs (o0 line, rows, regtimeline), the
STATUS2 reads before and after, the vertex dumps.  Worlds where each hypothesis wins and loses are built on top of these."""
import gzip
import hashlib
import os
import struct
import tempfile

HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tnote"
ROOT = tempfile.mkdtemp(prefix="r3-scorer-tests-", dir=os.environ.get("TMPDIR"))


def gz(path, data):
    with gzip.open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


def regs(st2):
    return "sgxfive regs 1\nreg 0x0118 %#010x\nreg 0x012c 0x20000000\nreg 0x0c04 0x00000000\n" % st2


def timeline(B, t6=None, t7=None, st2_base=0x400, noise_us=0.0):
    """regtimeline lines of a job: idle, one tick, the job's burst of B us from t0 = 40 us after the tick's end, bit 6 (7) of 0x0118 at
    t6 (t7) us from the burst's start, closing idle sample; the latch stays set."""
    t0 = 150_000                                    # ns: the burst's first sample
    rows = [(1_000, 0x20, st2_base), (80_000, 0xccfa0, st2_base), (90_000, 0x20, st2_base)]
    st = st2_base
    ev = [(t0, 0xa0000, st)]
    marks = sorted((x, b) for x, b in ((t6, 0x40), (t7, 0x80)) if x is not None)
    for t, b in marks:
        st |= b
        ev.append((t0 + int(t * 1000), 0xa0000, st))
    ev.append((t0 + int(B * 1000), 0x20, st))
    rows += ev
    out = ["timeline: regs 0x0008 0x0118 0x012c samples 5000 seconds 0 start 50000000 end 150000000 rc 0"]
    out += ["tl %d %08x %08x 20000000" % (t, cg, s) for t, cg, s in rows]
    return "\n".join(out) + "\n"


def timeline_ta(L, d7=None, st2_base=0x400, step_ns=4600):
    """regtimeline lines of a vertex-loop job: idle, the tick, then the TA's clocks (0x000ccff8) for L us (a sample every step_ns), then the
    tick value, bit 7 of 0x0118 set d7 us after the run began (None: not set); L = 0: no run."""
    t0 = 150_000
    rows = [(1_000, 0x20, st2_base), (80_000, 0xccfa0, st2_base), (90_000, 0x20, st2_base)]
    st = st2_base
    if L > 0:
        n = max(2, int(round(L * 1000 / step_ns)))
        for i in range(n):
            t = t0 + int(i * L * 1000 / n)
            if d7 is not None and t >= t0 + int(d7 * 1000):
                st = st2_base | 0x80
            rows.append((t, 0xccff8, st))
        t_end = t0 + int(L * 1000)
        if d7 is not None:
            st = st2_base | 0x80
        rows.append((t_end, 0xccfa0, st))
        rows.append((t_end + 20_000, 0x20, st))
    else:
        rows.append((t0, 0x20, st))
    out = ["timeline: regs 0x0008 0x0118 0x012c samples 5000 seconds 0 start 50000000 end 150000000 rc 0"]
    out += ["tl %d %08x %08x 20000000" % (t, cg, s) for t, cg, s in rows]
    return "\n".join(out) + "\n"


def stage(name, jobs):
    """jobs: list of dicts: name, out (text), pre (STATUS2 or None: not kept), post, rc, cls, dumps {suffix: bytes}.  Returns the dir."""
    d = tempfile.mkdtemp(prefix=name + "-", dir=ROOT)
    rows = [HEAD]
    for j in jobs:
        rows.append("\t".join([j["name"], name, j.get("set", "x"), "safe", "x", "x", "x", str(j.get("rc", 0)), j.get("cls", "ok"), "-"]))
        if j.get("out") is not None:
            gz(os.path.join(d, j["name"] + ".txt.gz"), j["out"])
        gz(os.path.join(d, j["name"] + ".dmesg.gz"), "")
        if j.get("pre", 0x400) is not None:
            gz(os.path.join(d, j["name"] + ".pre.regs.txt.gz"), regs(j.get("pre", 0x400)))
        if j.get("post") is not None:
            gz(os.path.join(d, j["name"] + ".after.regs.txt.gz"), regs(j["post"]))
        for suf, data in (j.get("dumps") or {}).items():
            gz(os.path.join(d, j["name"] + "." + j["name"] + "__0." + suf + ".gz"), data)
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return d


def noise(key, amp):
    """A deterministic pseudo-noise in [-amp, amp]."""
    h = int(hashlib.sha256(str(key).encode()).hexdigest()[:8], 16)
    return (h / 0xffffffff * 2 - 1) * amp


def o0_line(name, mark, count, total=None):
    return "probe %s: o0 0x%08x (%d of %d)\n" % (name, mark, count, total or count)
