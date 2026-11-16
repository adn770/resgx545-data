#!/bin/bash
# SPDX-License-Identifier: MIT
# finish_freeze.sh: the lead's last offline step of r30-pde, on the Mac over the travel cable (the
# laptop booted into module 7CE8E38EDB97FC5EA4F6C90, no GPU session running): build t30 on the
# laptop (lead/build_tool30_laptop.sh), put its sha256 into session.toml's [tools.t30] (the
# placeholder 0 x 64, the only one), keep its built line in lead/TOOL30.built, then
# tests/run_all.sh, the freeze and run_all again. Refuses an existing freeze, a missing
# placeholder or a build that printed no sha256. Logs to debug/ (never frozen).
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
cd "$KP"
[ ! -e FROZEN.sha256 ] || { echo "r30-pde is frozen already: a freeze is never rewritten"; exit 1; }
ZERO=0000000000000000000000000000000000000000000000000000000000000000
[ "$(grep -c "^sha256 = \"$ZERO\"$" session.toml)" = 1 ] || { echo "session.toml has no t30 placeholder"; exit 1; }
mkdir -p debug
bash lead/build_tool30_laptop.sh 2>&1 | tee debug/build_tool30_laptop.log
sha=$(sed -n 's/^sha256 \([0-9a-f]\{64\}\)$/\1/p' debug/build_tool30_laptop.log | tail -n 1)
[ -n "$sha" ] && [ "$sha" != "$ZERO" ] || { echo "the build printed no sha256: nothing changed"; exit 1; }
"$PY" -c 'import sys; p, z, s = sys.argv[1:]; t = open(p).read(); open(p, "w").write(t.replace(f"sha256 = \"{z}\"", f"sha256 = \"{s}\"", 1))' session.toml "$ZERO" "$sha"
sed -n 's/^FROZEN.commits line: //p' debug/build_tool30_laptop.log | tail -n 1 > lead/TOOL30.built
echo "t30 sha256 $sha in session.toml and lead/TOOL30.built"
bash tests/run_all.sh
"$PY" kit/session.py freeze .
bash tests/run_all.sh
