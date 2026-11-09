#!/bin/bash
# freeze-fine2-1138.sh [verify]: freeze (or verify) the confirmation set: predictions-fine2-1138.sha256 and manifest-fine2-1138.sha256.
cd "$(dirname "$0")" || exit 1
FILES="cases-fine2.tsv gen/gen_fine2.py run/run_p1138b.py recompute/fine2_p1138.py recompute/fine_extra_p1138.py recompute/fine_p1138.py predictions-fine2-1138.toml tests/test_fine2.py tool-b/userspace/libsgxfive/tools/sgxfive-test.c tool-b/userspace/libsgxfive/src/render.c"
if [ "${1:-}" = verify ]; then
	shasum -a 256 -c manifest-fine2-1138.sha256 --quiet && [ "$(shasum -a 256 predictions-fine2-1138.toml | cut -d' ' -f1)" = "$(cut -d' ' -f1 predictions-fine2-1138.sha256)" ] && echo "fine files verified" || { echo "FROZEN FILES CHANGED"; exit 1; }
else
	shasum -a 256 predictions-fine2-1138.toml > predictions-fine2-1138.sha256
	for f in $FILES; do shasum -a 256 "$f"; done > manifest-fine2-1138.sha256
	wc -l manifest-fine2-1138.sha256; cat predictions-fine2-1138.sha256
fi
