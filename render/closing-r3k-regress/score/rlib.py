"""rlib: what one kept job shows, the same function for the OLD records (gen/extract_old.py) and for the new run (score_rg.py).

observe(out_text, rc, tadata, param) -> {quantity: text}.  Only lines that exist in the output yield a quantity; a quantity
the old record has and the new run lacks is a mismatch (the scorer says "missing").  Every line is searched in the WHOLE output.
"""
import hashlib
import re


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def dwords_hex(param, a, b):
    if param is None or len(param) < 4 * b:
        return None
    return ",".join("%08x" % int.from_bytes(param[4 * i:4 * i + 4], "little") for i in range(a, b))


def observe(out, rc, tadata=None, param=None):
    q = {}
    out = out or ""
    if rc is not None:
        q["rc"] = str(rc)
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", out, re.M)
    if m:
        q["echo"] = m.group(1)
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", out, re.M)
    if m:
        q["target_hash"] = m.group(1)
    m = re.search(r"^diff: (\d+) of (\d+) pixels(?:, first \((\d+), (\d+)\) (0x[0-9a-f]+) expected (0x[0-9a-f]+))?", out, re.M)
    if m:
        q["diff"] = "%s of %s" % (m.group(1), m.group(2))
        if m.group(3) is not None:
            q["diff_first"] = "(%s, %s) %s expected %s" % m.group(3, 4, 5, 6)
    last = None
    for m in re.finditer(r"^tri \d+x\d+ #(\d+): (\d+) triangle, (\d+) background, (\d+) other; wrong (\d+) inside, (\d+) outside, "
                         r"(\d+) at edges", out, re.M):
        last = m
    if last:
        q["tri_last"] = "#%s: %s triangle, %s background, %s other; wrong %s inside, %s outside, %s at edges" % last.groups()
    g = re.findall(r"^tri \d+x\d+ #(\d+): geometry only, the scene left open", out, re.M)
    if g:
        q["geometry_only"] = ",".join(g)
    m = re.search(r"^tri: (\d+(?: of \d+)?) renders? ok", out, re.M)
    if m:
        q["renders_ok"] = m.group(1)
    m = re.search(r"^probe \S+: o0 (.+?)\s*$", out, re.M)
    if m:
        q["probe_o0"] = m.group(1)
    m = re.search(r"^probe \S+: tri (.+?)\s*$", out, re.M)
    if m:
        q["probe_tri"] = m.group(1)
    m = re.search(r"^probe \S+: triangle (.+?)\s*$", out, re.M)
    if m:
        q["probe_triangle"] = m.group(1)
    if tadata is not None:
        q["tadata_sha256"] = _sha(tadata)
        q["tadata_size"] = hex(len(tadata))
    if param is not None:
        q["param_sha256"] = _sha(param)
        q["stream_0_2"] = dwords_hex(param, 0, 3) or "-"
        q["par_11_26"] = dwords_hex(param, 11, 27) or "-"
    return q


def has_fault_text(*texts):
    return any(re.search(r"BIF fault|faulted|hung|timed out waiting", t or "") for t in texts)
