#!/usr/bin/env python3
"""Integrity check of the kept dumps: python3 -B verify_p1135.py OUT_FILE DUMP_DIR. Every "kept NAME: N bytes raw,
M gz, raw sha256 X" line of the run's output must match the gz file in DUMP_DIR (decompressed size and sha256)."""
import gzip, hashlib, pathlib, re, sys
out, d = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
ok = bad = missing = 0
for m in re.finditer(r"kept (\S+): (\d+) bytes raw, (\d+) gz, raw sha256 ([0-9a-f]{64})", out.read_text(errors="replace")):
    name, raw, gz, sha = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    p = d / (name + ".gz")
    if not p.exists():
        missing += 1; print("missing", name); continue
    b = gzip.open(p).read()
    if len(b) == raw and hashlib.sha256(b).hexdigest() == sha and p.stat().st_size == gz:
        ok += 1
    else:
        bad += 1; print("MISMATCH", name)
print("kept files: %d ok, %d mismatch, %d missing" % (ok, bad, missing))
sys.exit(1 if bad or missing else 0)
