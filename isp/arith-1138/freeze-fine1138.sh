#!/bin/bash
# freeze-fine1138.sh [verify]: freeze (or verify) the follow-up set: predictions-fine-1138.sha256 and manifest-fine-1138.sha256.
cd "$(dirname "$0")" || exit 1
FILES="cases-fine.tsv gen/gen_fine.py run/run_p1138b.py recompute/fine_p1138.py predictions-fine-1138.toml tests/test_fine.py tool-b/userspace/libsgxfive/tools/sgxfive-test.c tool-b/userspace/libsgxfive/src/render.c tool-b/userspace/libsgxfive/include/sgxfive_render.h tool-b/userspace/libsgxfive/tests/test_render.c tool-b/userspace/libsgxfive/tests/test_cli.py tool-b/userspace/libsgxfive/tests/test_cli_tri_probe.py"
if [ "${1:-}" = verify ]; then
	shasum -a 256 -c manifest-fine-1138.sha256 --quiet && [ "$(shasum -a 256 predictions-fine-1138.toml | cut -d' ' -f1)" = "$(cut -d' ' -f1 predictions-fine-1138.sha256)" ] && echo "fine files verified" || { echo "FROZEN FILES CHANGED"; exit 1; }
else
	shasum -a 256 predictions-fine-1138.toml > predictions-fine-1138.sha256
	for f in $FILES; do shasum -a 256 "$f"; done > manifest-fine-1138.sha256
	wc -l manifest-fine-1138.sha256; cat predictions-fine-1138.sha256
fi
