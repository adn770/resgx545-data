"""alib.py: what the R4-A generator and scorer read from the kept files (standard library only).  The tool's lines are searched in
the WHOLE output (R1-events lost "scene overflowed" in a 4000-character tail)."""
import gzip
import hashlib
import os
import re
import struct
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_bytes(p):
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rb") as f:
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
    """The text after `diff: ` (the count, the first wrong pixel and its colours), or None."""
    m = re.search(r"^diff: (.*)$", text or "", re.M)
    return m.group(1) if m else None


def diff_count(text):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", text or "", re.M)
    return None if not m else (int(m.group(1)), int(m.group(2)))


def tri_text(text, n):
    """The text after `tri WxH #n: ` of render n's result line (not its timing line), or None."""
    m = None
    for m2 in re.finditer(r"^tri \d+x\d+ #%d: (.*triangle, .*)$" % n, text or "", re.M):
        m = m2
    return m.group(1) if m else None


def tri_counts(text, n):
    t = tri_text(text, n)
    m = t and re.match(r"(overflowed, )?(\d+) triangle, (\d+) background, (\d+) other;", t)
    if not m:
        return None
    return {"tri": int(m.group(2)), "bg": int(m.group(3)), "other": int(m.group(4)), "overflowed": bool(m.group(1))}


def renders(text):
    m = None
    for m2 in re.finditer(r"^tri: ((\d+ of )?\d+ renders ok)$", text or "", re.M):
        m = m2
    return m.group(1) if m else None


def echo(text):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", text or "", re.M)
    return m.group(1) if m else None


def geometry1(text):
    return "yes" if re.search(r"^tri \d+x\d+ #1: geometry only, the scene left open$", text or "", re.M) else "no"


def overflowed(*texts):
    return any(re.search(r"scene overflowed|overflowed the parameter buffer", t or "") for t in texts)


def tool_failed(text):
    """A message of the tool that a job did not run as asked, anywhere in the output."""
    return re.search(r"rejected|FAILED after|cancelled|Segmentation|failed:|sgxfive-test: ", text or "") is not None


def kpoke_applied(dmesg):
    """The kernel's `sgxfive: kpoke SPACE:INDEX=0xVALUE applied` lines: ["par:11=0x00000000", ...] in order."""
    return ["%s:%s=0x%s" % m.groups() for m in re.finditer(r"kpoke (\w+):(\d+)=0x([0-9a-f]{8}) applied", dmesg or "")]
