#!/bin/bash
# freeze1140.sh [verify]: freeze (or verify) the sweep: predictions-1140.sha256 and manifest-1140.sha256.
cd "$(dirname "$0")" || exit 1
FILES="cases-1140.tsv gen/gen_p1140.py run/run_p1140.py recompute/model1140.py recompute/recompute_p1140.py predictions-1140.toml tests/test_run_p1140.py tests/test_recompute_p1140.py tool/userspace/libsgxfive/tools/sgxfive-test.c tool/userspace/libsgxfive/src/render.c tool/userspace/libsgxfive/include/sgxfive_render.h tool/userspace/libsgxfive/tests/test_render.c tool/userspace/libsgxfive/tests/test_cli.py"
if [ "${1:-}" = verify ]; then
	shasum -a 256 -c manifest-1140.sha256 --quiet && [ "$(shasum -a 256 predictions-1140.toml | cut -d' ' -f1)" = "$(cut -d' ' -f1 predictions-1140.sha256)" ] && echo "files verified" || { echo "FROZEN FILES CHANGED"; exit 1; }
else
	shasum -a 256 predictions-1140.toml > predictions-1140.sha256
	for f in $FILES; do shasum -a 256 "$f"; done > manifest-1140.sha256
	wc -l manifest-1140.sha256; cat predictions-1140.sha256
fi
