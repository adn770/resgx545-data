"""klib (from R2-pixel's r2lib): readers and the frozen models of the R3K-pixel scorers (scratch; numpy only where it pays).

Readers: cases.tsv, the kept gz files, debugfs `regs` snapshots, regtimeline output, the kernel log
slice, TA data dumps.  Model: the kernel's TA data layout, transcribed from the linux fork branch
resgx545 (sgx_render.c: sgx_render_layout, sgx_render_tadata_layout; RD_RGNBASE = tadata + td.rgn;
the RT data's array sizes come from the render's own target, sgx_render_rtds_resize).
Every reader returns None for missing or empty data: the scorers call that NODATA, never a result.
"""
import gzip
import hashlib
import os
import re
import subprocess

import numpy as np

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# E729: the TA data heap of a render context starts at 0x20000000 (fault 0x20006062 = page 6 of it)
TADATA_BASE_PAGE = 0x20000
REG_STATUS, REG_STATUS2, REG_BIF_CTRL, REG_INT_STAT, REG_FAULT = 0x012c, 0x0118, 0x0c00, 0x0c04, 0x0c08
FAULT_REQ = 0xffff
# bits an idle GPU or a held fault of E444 shows: CR_EVENT_STATUS bit 29 (TIMER); CR_EVENT_STATUS2
# bit 10 (DCU_INVAL_COMPLETE), 6 (TRIG_3D), 7 (TRIG_TA).  Bit 31 (MASTER_INTERRUPT) needs an enable,
# which K2 never writes: seen set, it is an extra bit too.
KNOWN_STATUS = 1 << 29
KNOWN_STATUS2 = (1 << 10) | (1 << 7) | (1 << 6)
# masked, never counted as a fault's own bit: CR_EVENT_STATUS bit 14 (SW_EVENT, the EDM's own event, which
# the reset's boot raises) and bit 31 (MASTER_INTERRUPT, set with any enabled pending event)
MASK_STATUS = (1 << 14) | (1 << 31)


def _env_default(name, fallback):
    m = re.search(r"^%s=\$\{%s:-([0-9.]+)\}" % (name, name), open(os.path.join(KP, "run", "k.env")).read(), re.M)
    return float(m.group(1)) if m else fallback


# the timeline rows a held reading may use: before snap 2 (HOLD_READ + HOLD_GAP after the launch, in
# regtimeline's clock); the reset, which comes after snap 2, halts the core and raises other bits
HOLD_WINDOW_NS = int((_env_default("HOLD_READ", 2.8) + _env_default("HOLD_GAP", 1.0)) * 1e9)


def rup(a, m):
    return (a + m - 1) // m * m


def layout(w, h, f=1):
    """sgx_render_layout + sgx_render_tadata_layout for a w x h target (or maximum); f = render_rgn_arrays (the kernel's
    `zls = rgn + round_up(f * rgn_size, 4K)`, closing3/kernel/layout_f4.py; f = 1 is the layout of every earlier session)."""
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span, side = max(n * mx, n * my), 1
    while side < span:
        side <<= 1
    blocks = (mx // 4) * (my // 4)
    rgn_size = 0xc0 * blocks * n * n
    tail = 4 * side * side
    control = rup(tail, 4096)
    rgn = control + 3 * 4096
    zls = rgn + rup(f * rgn_size, 4096)
    size = zls + rup(rgn_size, 4096)
    return {"n": n, "rgn_size": rgn_size, "rgn": rgn, "zls": zls, "size": size}


def fault_page_if(f, target, maximum):
    """The first page past the TA data when f arrays of the target's rgn_size do not fit, else None."""
    t, m = layout(*target), layout(*maximum)
    assert t["rgn"] == m["rgn"], "the target's arrays must start at the maximum's rgn"
    end = m["rgn"] + f * t["rgn_size"]
    return None if end <= m["size"] else TADATA_BASE_PAGE + (m["size"] >> 12)


def read_bytes(path):
    if not os.path.exists(path):
        return None
    try:
        with gzip.open(path, "rb") as f:
            b = f.read()
    except (OSError, EOFError):
        return None
    return b if b else None


def read_text(path):
    b = read_bytes(path)
    return None if b is None else b.decode("utf-8", "replace")


def read_cases(outdir):
    p = os.path.join(outdir, "cases.tsv")
    if not os.path.exists(p):
        return None
    lines = open(p).read().splitlines()
    if len(lines) < 1:
        return None
    head = lines[0].split("\t")
    rows = {}
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) != len(head):
            continue
        rows[f[0]] = dict(zip(head, f))
    return rows


def parse_regs(text):
    """debugfs regs: {offset: value}; skipped registers left out.  None if no BIF register in it."""
    if not text:
        return None
    out = {}
    for m in re.finditer(r"^reg (0x[0-9a-f]+) (0x[0-9a-f]+)$", text, re.M):
        out[int(m.group(1), 16)] = int(m.group(2), 16)
    return out if REG_INT_STAT in out and REG_STATUS2 in out and REG_STATUS in out else None


def parse_timeline(text):
    """regtimeline: (regs, start_ns, end_ns, rows[(t_ns, {reg: value})]) or None."""
    if not text:
        return None
    m = re.search(r"^timeline: regs ((?:0x[0-9a-f]+ ?)+) samples (\d+) seconds \S+ start (\d+) end (\d+) rc (-?\d+)$",
                  text, re.M)
    if not m:
        return None
    regs = [int(x, 16) for x in m.group(1).split()]
    rows = []
    for t in re.finditer(r"^tl (\d+)((?: [0-9a-f]{8})+)$", text, re.M):
        vals = [int(v, 16) for v in t.group(2).split()]
        if len(vals) == len(regs):
            rows.append((int(t.group(1)), dict(zip(regs, vals))))
    return {"regs": regs, "start": int(m.group(3)), "end": int(m.group(4)), "rows": rows}


def fault_window(tl, until=None):  # (kept from r2lib; K2 reads snapshots, not timelines)
    """The job's own rows (t >= the command's start; the first sample is the previous state) from
    the last row before the first fault row on, up to the row where the fault bits clear, and never at
    or after `until` (default HOLD_WINDOW_NS: the reset comes later and its halt is not the fault's).
    Returns (fault_row, before_row, rose_status, rose_status2) or None when no fault row exists."""
    until = HOLD_WINDOW_NS if until is None else until
    rows = [r for r in tl["rows"] if tl["start"] <= r[0] < until]
    prev = None
    for t, v in tl["rows"]:
        if t < tl["start"]:
            prev = v
    for i, (t, v) in enumerate(rows):
        if v.get(REG_INT_STAT, 0) & FAULT_REQ:
            before = rows[i - 1][1] if i > 0 else prev
            if before is None:
                return None
            rose1 = rose2 = 0
            for t2, v2 in rows[i:]:
                if not v2.get(REG_INT_STAT, 0) & FAULT_REQ:
                    break
                rose1 |= v2[REG_STATUS] & ~before[REG_STATUS]
                rose2 |= v2[REG_STATUS2] & ~before[REG_STATUS2]
            return {"t": t, "row": v, "before": before, "rose_status": rose1, "rose_status2": rose2}
    return None


def tadata_slots(blob, rgn, rgn_size):
    """Non-zero dwords per region-header array slot from rgn to the end (the last slot may be short)."""
    a = np.frombuffer(blob[: len(blob) // 4 * 4], dtype="<u4")
    out = []
    off = rgn
    while off < len(blob):
        out.append(int(np.count_nonzero(a[off // 4: min(off + rgn_size, len(blob)) // 4])))
        off += rgn_size
    below = int(np.count_nonzero(a[: rgn // 4]))
    return out, below


def slot_mask(blob, rgn, rgn_size, k):
    a = np.frombuffer(blob[: len(blob) // 4 * 4], dtype="<u4")
    lo = (rgn + k * rgn_size) // 4
    return set(np.nonzero(a[lo: min(lo + rgn_size // 4, len(a))])[0].tolist())


def array_like(blob, rgn, rgn_size, k):
    """Slot k looks like a region-header array: non-empty, its non-zero dwords at positions slot 0 also
    writes (every array of E728's dumps does: the same tiles' headers), and at least as many as the
    sparsest written slot of 1 to 3.  At 256x160 and 320x128 slot 4 lies in the ZLS area (zls 0x5000),
    so a non-zero slot 4 alone is not a fifth array."""
    m0, mk = slot_mask(blob, rgn, rgn_size, 0), slot_mask(blob, rgn, rgn_size, k)
    counts = [len(slot_mask(blob, rgn, rgn_size, i)) for i in (1, 2, 3)]
    counts = [c for c in counts if c]
    return bool(mk) and mk <= m0 and bool(counts) and len(mk) >= min(counts)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def pix_hash(px):
    """The sha256 over the comma-joined 8-digit hex words (S1b's pix_hash; gen/r2models.py has the same function)."""
    return hashlib.sha256(",".join("%08x" % v for v in px).encode()).hexdigest()


def load_predictions(name):
    p = os.path.join(KP, "predictions", name)
    out = {}
    for ln in open(p).read().splitlines()[1:]:
        if not ln.strip():
            continue
        case, q, val, model, sset = ln.split("\t")
        out.setdefault((case, q), []).append((val, model, sset))
    return out


def pred(P, case, q, model=None):
    for val, m, _ in P.get((case, q), []):
        if model is None or m == model:
            return val
    raise KeyError((case, q, model))


def verify_freeze(stage=None):
    """The frozen files (predictions, scorers, tables, runner) must be the ones of the freeze."""
    r = subprocess.run([os.path.join(KP, "run", "freeze_k.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def hx(v):
    return "-" if v is None else "%#x" % v


# ---- the probe's output (D2) ---------------------------------------------------------------------------------
BASE_SCRATCH = 0x3E003000      # the probe's scratch base: another base voids a D2 row
def probe_rows(text):
    """The pixel words of a probe job: every `row N: hex ...` line, in row order (all of them, anywhere in the
    output: the whole text is searched, never a tail)."""
    r = {}
    for ln in (text or "").splitlines():
        m = re.search(r"row (\d+): ((?:[0-9a-f]{8} ?)+)\s*$", ln)
        if m:
            r[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
    return [x for k in sorted(r) for x in r[k]]


def scratch_line(text):
    """(base, KiB) of the probe's `scratch at 0x3e003000 (N KiB)` line, or None."""
    m = re.search(r"scratch at (0x[0-9a-f]+) \((\d+) KiB\)", text or "")
    return None if not m else (int(m.group(1), 16), int(m.group(2)))


def bif_fault(*texts):
    """(word, address) of the first `BIF fault 0x9xxxx at 0x...` line in the texts, or None."""
    for t in texts:
        m = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", t or "", re.I)
        if m:
            return m.group(1).lower(), int(m.group(2), 16)
    return None


def load_images(path=None):
    """predictions/r2-d-images.tsv: {case: (pages, [words])} (frozen model images)."""
    p = path or os.path.join(KP, "predictions", "k-images.tsv")
    out = {}
    for ln in open(p).read().splitlines()[1:]:
        n, lab, pg, px = ln.split("\t")
        out[n] = (int(pg), [int(v, 16) for v in px.split(",")])
    return out


# ---- K2: the new module's kernel-log lines, the tool's split-flow lines, the parameter buffer ------------------------------
def _num(x):
    return int(x, 0)


def kregnow_lines(dmesg):
    """The kernel's `kregnow 0xOFF: OLD -> NEW, reads R, BIF_INT_STAT I BIF_FAULT F` lines (commit 7 of the batch) in log order:
    [{off, old, new, reads, int_stat, fault}].  A write-only row's `kregnow 0xOFF = 0xV (write-only)` line is not matched."""
    out = []
    for m in re.finditer(r"kregnow (0x[0-9a-f]+): (0x[0-9a-f]+) -> (0x[0-9a-f]+), reads (0x[0-9a-f]+), BIF_INT_STAT (0x[0-9a-f]+) "
                         r"BIF_FAULT (0x[0-9a-f]+)", dmesg or ""):
        o, a, b, r, i, f = (_num(x) for x in m.groups())
        out.append({"off": o, "old": a, "new": b, "reads": r, "int_stat": i, "fault": f})
    return out


def reset_lines(dmesg):
    """The reset's two BIF lines of the new module (commit 7): `SGX reset: BIF_FAULT F BIF_INT_STAT I EVENT_STATUS A/B` (after
    the halt, before CLEAR_FAULT) and `SGX reset: after the fault clear BIF_FAULT F BIF_INT_STAT I`.  Returns a list of
    {"kind": "halt"|"clear", "fault", "int_stat"}; the numbers are printed by %#x (0 prints as 0)."""
    out = []
    for ln in (dmesg or "").splitlines():
        m = re.search(r"SGX reset: after the fault clear BIF_FAULT (0x[0-9a-f]+|0) BIF_INT_STAT (0x[0-9a-f]+|0)\b", ln)
        if m:
            out.append({"kind": "clear", "fault": _num(m.group(1)), "int_stat": _num(m.group(2))})
            continue
        m = re.search(r"SGX reset: BIF_FAULT (0x[0-9a-f]+|0) BIF_INT_STAT (0x[0-9a-f]+|0) EVENT_STATUS", ln)
        if m:
            out.append({"kind": "halt", "fault": _num(m.group(1)), "int_stat": _num(m.group(2))})
    return out


def kpoke_applied(dmesg):
    """The `sgxfive: kpoke par:INDEX=0xVALUE applied` lines of the kernel log: [(space, index, value)]."""
    return [(m.group(1), int(m.group(2)), int(m.group(3), 16))
            for m in re.finditer(r"kpoke (\w+):(\d+)=0x([0-9a-f]+) applied", dmesg or "")]


def tri_lines(text, n=None):
    """The tool's per-render result lines `tri WxH #N: T triangle, B background, O other; wrong ...` (the whole output is
    searched; the LAST render N, or render n): {"n", "tri", "bg", "other", "overflowed"} or None."""
    best = None
    for m in re.finditer(r"^tri \d+x\d+ #(\d+): (overflowed, )?(\d+) triangle, (\d+) background, (\d+) other;", text or "", re.M):
        k = int(m.group(1))
        if n is not None and k != n:
            continue
        best = {"n": k, "tri": int(m.group(3)), "bg": int(m.group(4)), "other": int(m.group(5)), "overflowed": bool(m.group(2))}
    return best


def target_hash(text):
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", text or "", re.M)
    return None if not m else m.group(1)


def diff_line(text):
    """(wrong, total, first) of the tool's `diff: N of M pixels[, first (x, y) ...]` line, or None."""
    m = re.search(r"^diff: (\d+) of (\d+) pixels(?:, first \((\d+), (\d+)\))?", text or "", re.M)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), None if m.group(3) is None else "(%s, %s)" % (m.group(3), m.group(4))


def overflowed(*texts):
    """The tool's or the kernel's parameter-buffer overflow message, searched in the whole text."""
    return any(re.search(r"scene overflowed|overflowed the parameter buffer|ENOSPC", t or "") for t in texts)


def dwords(blob):
    return np.frombuffer(blob[: len(blob) // 4 * 4], dtype="<u4")


def kw_steps(text):
    """NAME.kw.txt: {"set": value written back, step: status of its tee} (None if empty)."""
    if not text:
        return None
    out = {}
    for ln in text.splitlines():
        m = re.match(r"set (0x[0-9a-f]+)$", ln)
        if m:
            out["set"] = int(m.group(1), 16)
        m = re.match(r"(\d) (\S+) rc (-?\d+)$", ln)
        if m:
            out[int(m.group(1))] = (m.group(2), int(m.group(3)))
    return out
