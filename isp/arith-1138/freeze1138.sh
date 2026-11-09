#!/bin/bash
# freeze1138.sh [verify]: write (or verify) predictions-1138.sha256 and manifest-1138.sha256: the sha256 of
# the predictions and of every file the run and the analysis use. Run before the first job; verify before every run.
cd "$(dirname "$0")" || exit 1
FILES="cases.tsv gen/gen_p1138.py recompute/p1138lib.py recompute/recompute_p1138.py run/run_p1138.py iter.toml deploy1138.sh stage1138.sh plan.md predictions-1138.toml tests/test_p1138lib.py tests/test_recompute.py tests/test_run.py $(ls templates/* stage-bins/*.bin tool/userspace/libsgxfive/tools/sgxfive-test.c tool/userspace/libsgxfive/src/render.c tool/userspace/libsgxfive/include/sgxfive_render.h tool/userspace/libsgxfive/tests/test_render.c tool/userspace/libsgxfive/tests/test_cli.py tool/userspace/libsgxfive/tests/test_cli_tri_probe.py)"
if [ "${1:-}" = verify ]; then
	shasum -a 256 -c manifest-1138.sha256 --quiet && [ "$(shasum -a 256 predictions-1138.toml | cut -d' ' -f1)" = "$(cut -d' ' -f1 predictions-1138.sha256)" ] && echo "frozen files verified" || { echo "FROZEN FILES CHANGED"; exit 1; }
else
	shasum -a 256 predictions-1138.toml > predictions-1138.sha256
	for f in $FILES; do shasum -a 256 "$f"; done > manifest-1138.sha256
	wc -l manifest-1138.sha256; cat predictions-1138.sha256
fi
