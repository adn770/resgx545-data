#!/bin/bash
# SPDX-License-Identifier: MIT
# fake_tool.sh: the mock laptop's ~/sgxfive-test-s1b (R5-events).  A bash front of tests/fake_tool.py so that a job's `fill` reaches the
# simulated EDM within a few milliseconds of its start, as the C tool does on the laptop (a Python start would leave the slot 0 ring full
# of ticks before the fill's kick).  Every call's argv is logged to MOCK_DIR/tool.log under the job of the kernel log's last case marker
# (the argv-twin test reads it); the fill of an armed ring_skip3p leaves fill_start for the mock EDM (tests/mockfw/kmock.py) and waits
# (bounded) for fill_done; anything else is the Python fake's.
job=$(grep ' case ' "${R3_KMSG:-$MOCK_DIR/kmsg}" 2>/dev/null | tail -1 | sed 's/.* case \([^ ]*\) .*/\1/')
arm=""; [ -e "$MOCK_DIR/e3p_armed" ] && arm=" (armed)"
echo "[$job] $(basename "$0") $*$arm" >> "$MOCK_DIR/tool.log"
if [ "$1" = fill ] && [ -e "$MOCK_DIR/e3p_armed" ]; then
	case ",$MOCK_SCENARIO," in *,fill_fail,*|*,tool_fail,*) echo "job: failed (mock)"; exit 1 ;; esac
	# r6-held part P: a slow start (MOCK_TOOL_DELAY s) must not change any outcome (the round 6 brief: no ms start-up timing)
	[ -n "${MOCK_TOOL_DELAY:-}" ] && sleep "$MOCK_TOOL_DELAY"
	echo "[$job] $(pwd -P)" >> "$MOCK_DIR/cwd.log"
	: > "$MOCK_DIR/fill_start"
	n=$(awk -v w="${MOCK_TOOL_WAIT:-2.0}" 'BEGIN { print int(w * 100) }')
	for ((i = 0; i < n; i++)); do
		if [ -e "$MOCK_DIR/fill_done" ]; then printf 'job: ok\njob time: 100 us\ndiff: 0 of 2048 pixels\n'; exit 0; fi
		sleep 0.01
	done
	echo "job: failed (the end of render never came)"
	exit 1
fi
FAKE_TOOL_NOLOG=1 exec "$MOCK_PY" "$(dirname "$0")/fake_tool.py" "$@"
