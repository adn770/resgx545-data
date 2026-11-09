#!/bin/bash
# stage1138.sh [DIR]: assemble iter.toml's programs into DIR (default ./stage-bins) with the landed usse-asm and
# pds-asm (read only from ~/src/resgx545), as stage-p1126.sh does. No laptop is used.
set -eu
export PYTHONDONTWRITEBYTECODE=1
P=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$P/stage-bins}
mkdir -p "$OUT"
python3 -B - "$P/iter.toml" "$OUT" <<'PY'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545/tools/usse-asm"))
import probe
table = probe.load(pathlib.Path(sys.argv[1]))
src = pathlib.Path(sys.argv[1]).parent / "templates"
out = pathlib.Path(sys.argv[2])
for p in table:
    probe.build(p, out, src)
probe.build_helpers(table, out, src)
print("staged:", " ".join(sorted(f.name for f in out.glob("*.bin"))))
PY
