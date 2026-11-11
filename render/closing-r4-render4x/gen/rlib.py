"""rlib.py: what the R4-G generator and scorer read from kept files (standard library only; numpy only in cubegen).  The tool's
lines are searched in the WHOLE output (R1-events lost "scene overflowed" in a 4000-character tail)."""
import gzip
import hashlib
import os
import re
import struct
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
K2 = DATA + "/render/closing-r3k-pixel/out/20261110-193547/k-f4"
RGN4 = DATA + "/render/closing-r3-rgn4/out/rgn4"
REG = DATA + "/render/closing-r3k-regress/out/20261110-222647/rg-pb"
CUBE = DATA + "/texture/p1141/out-hw/p1141tex-dumps/tex-h-cube"
LINE = DATA + "/ta/line-point/dumps/ta-line-point"
POINT = DATA + "/ta/points/dumps/ta-points"


def read_bytes(p):
    if not os.path.exists(p):
        return None
    if p.endswith(".gz"):
        with gzip.open(p, "rb") as f:
            b = f.read()
    else:
        with open(p, "rb") as f:
            b = f.read()
    return b if b else None


def read_text(p):
    b = read_bytes(p)
    return None if b is None else b.decode("utf-8", "replace")


def read_cases(outdir):
    p = os.path.join(outdir, "cases.tsv")
    if not os.path.exists(p):
        return None
    lines = open(p).read().splitlines()
    if not lines:
        return None
    head = lines[0].split("\t")
    rows = {}
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) == len(head):
            rows[f[0]] = dict(zip(head, f))
    return rows


def load_predictions(name, kp=KP):
    out = {}
    for ln in open(os.path.join(kp, "predictions", name)).read().splitlines()[1:]:
        if not ln.strip():
            continue
        case, q, val, model, sset, _src = ln.split("\t")
        out.setdefault((case, q), []).append((val, model, sset))
    return out


def pred(P, case, q, model=None):
    for val, m, _ in P.get((case, q), []):
        if model is None or m == model:
            return val
    raise KeyError((case, q, model))


def pred_or(P, case, q, default=None):
    v = P.get((case, q))
    return default if not v else v[0][0]


def verify_freeze():
    r = subprocess.run([os.path.join(KP, "run", "freeze_k.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def dwords(b):
    n = len(b) // 4
    return list(struct.unpack("<%dI" % n, b[: 4 * n]))


def words(b, a, z):
    if b is None or len(b) < 4 * z:
        return None
    return ",".join("%08x" % x for x in dwords(b[4 * a: 4 * z]))


def target_hash(text):
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", text or "", re.M)
    return m.group(1) if m else None


def diff_text(text):
    m = re.search(r"^diff: (.*)$", text or "", re.M)
    return m.group(1) if m else None


def diff_count(text):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", text or "", re.M)
    return None if not m else (int(m.group(1)), int(m.group(2)))


def tri_text(text, n=1):
    m = None
    for m2 in re.finditer(r"^tri \d+x\d+ #%d: (.*triangle, .*)$" % n, text or "", re.M):
        m = m2
    return m.group(1) if m else None


def tri_counts_text(text, n=1):
    """'N triangle, M background, K other' of render n's result line (the overflow mark and the wrong-pixel counts left out)."""
    t = tri_text(text, n)
    m = t and re.match(r"(?:overflowed, )?(\d+ triangle, \d+ background, \d+ other);", t)
    return m.group(1) if m else None


def tri_overflowed_line(text, n=1):
    t = tri_text(text, n)
    return bool(t and t.startswith("overflowed, "))


def renders(text):
    m = None
    for m2 in re.finditer(r"^tri: ((?:\d+ of )?\d+ renders ok(?:, \d+ overflowed)?)$", text or "", re.M):
        m = m2
    return m.group(1) if m else None


def echo(text):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", text or "", re.M)
    return m.group(1) if m else None


def overflow_count(text):
    m = re.search(r"(\d+) overflowed$", renders(text) or "")
    return int(m.group(1)) if m else 0


def overflowed(*texts):
    return any(re.search(r"scene overflowed|overflowed the parameter buffer|overflowed, ", t or "") for t in texts)


def tool_failed(text):
    return re.search(r"rejected|FAILED after|cancelled|Segmentation|failed:|sgxfive-test: ", text or "") is not None


def reg(text, off):
    """A register of the tool's own `--regs` print ('reg 0x0724 0x000b000b') or of a debugfs regs snapshot: the value, or None."""
    m = re.search(r"^reg 0x%04x (0x[0-9a-f]+)$" % off, text or "", re.M)
    return m.group(1) if m else None


def bif_faults(text):
    """The kernel's job fault lines 'BIF fault 0xSTAT at 0xWORD': [(stat, word)] in order."""
    return [(int(a, 16), int(b, 16)) for a, b in re.findall(r"BIF fault 0x([0-9a-f]+) at 0x([0-9a-f]+)", text or "")]


def decode_fault(word):
    """BIF_FAULT word: (page, SB, CID) (hw_spec 5.5: the page number above bit 12, the sideband 7:4, the context list 3:0)."""
    return (word >> 12, (word >> 4) & 0xf, word & 0xf)
