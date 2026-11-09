#!/bin/bash
# freeze1141ta.sh [verify]: freeze (or verify) predictions and every file that defines a case, a run or a score.
# Writes only predictions-declared.sha256 and manifest-1141ta.sha256 here. Nothing leaves this directory.
cd "$(dirname "$0")" || exit 1
FILES="declared.tsv predictions-declared.tsv gen/gen_p1141ta.py gen/gen_ring.py run/lib1141ta.sh run/run_table_ta.sh run-all-1141ta.sh stage_1141ta.sh
recompute/recompute_1141ta.py recompute/q164_fate.py recompute/dpm_raise.py recompute/o4_parity.py recompute/vdm_counter.py recompute/hang_len.py recompute/serv_diff.py
programs/o4-markers.tsv draft/events_ring.s probes/ta-eot.toml tests/run_mock.sh tests/fake_tool.sh tests/test_ring_decode.py
$(ls run/tables/*.txt programs/*.s stage-bins/*.bin probes/templates/*.s 2>/dev/null)"
if [ "${1:-}" = verify ]; then
	shasum -a 256 -c manifest-1141ta.sha256 --quiet && [ "$(shasum -a 256 predictions-declared.tsv | cut -d' ' -f1)" = "$(cut -d' ' -f1 predictions-declared.sha256)" ] && echo "files verified" || { echo "FROZEN FILES CHANGED"; exit 1; }
else
	shasum -a 256 predictions-declared.tsv > predictions-declared.sha256
	for f in $FILES; do shasum -a 256 "$f"; done > manifest-1141ta.sha256
	wc -l < manifest-1141ta.sha256; cat predictions-declared.sha256
fi
