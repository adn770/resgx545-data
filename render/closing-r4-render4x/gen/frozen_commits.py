#!/usr/bin/env python3
"""frozen_commits.py: write FROZEN.commits beside this session's FROZEN.sha256 with resgx545's own tools/records/frozen.py
(its commits_for and Finder: the newest commit at or before the date whose blob has the pinned hash), the format HACKING.md
gives.  Refuses to replace an existing file that differs, and to write when a pin has no commit.
  PY gen/frozen_commits.py [DATE]      (DATE default 2026-11-11)
"""
import pathlib
import sys

MAIN = pathlib.Path("/Users/jtorra/src/resgx545")
sys.path.insert(0, str(MAIN / "tools/records"))
import frozen  # noqa: E402

KP = pathlib.Path(__file__).resolve().parent.parent
date = sys.argv[1] if len(sys.argv) > 1 else "2026-11-11"
text, bad = frozen.commits_for(KP, frozen.Finder(MAIN), date)
if bad:
    print("\n".join(bad))
    sys.exit(1)
out = KP / frozen.NAME
if out.exists() and out.read_text() != text:
    print("%s exists and differs: not replaced" % out)
    sys.exit(1)
out.write_text(text)
print("%s: %d pins" % (out, text.count("\n") - frozen.HEADER.count("\n")))
