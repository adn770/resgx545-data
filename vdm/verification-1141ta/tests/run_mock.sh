#!/bin/bash
# tests/run_mock.sh: every table runs end to end against a fake tool and plain-directory debugfs; checks
# case counts, markers, kept files, the failure path (reset + health) and the three-failures stop.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_TEST_NEW="$P/tests/fake_tool.sh"
export SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg" SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh"
export SGXFIVE_PROBE_BINS="$W/stage" SGXFIVE_PROBE_BINS39="$W/stage" SGXFIVE_PROBE_BINS34="$W/stage" SGXFIVE_PROBE_BINS41="$W/stage"
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TABLE_DIR="$P/run/tables"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset kpoke hold_recovery render_keep render_pb_pages tadata_fill regs buf09 render_param render_tadata render_words; do : > "$W/dbg/$f"; done
fail=0
for t in "$P"/run/tables/*.txt; do
	name=$(basename "$t" .txt)
	for f in $(grep '^#need ' "$t" | cut -d' ' -f2-); do
		g=$(echo "$f" | sed -e "s|\$S41|$W/stage|g" -e "s|\$S34|$W/stage|g" -e "s|\$S39|$W/stage|g" -e "s|\$S|$W/stage|g")
		: > "$g"
	done
	n=$(grep -vc '^#' "$t")
	KEEP="$W/out/$name" bash "$P/run/run_table_ta.sh" "$name" all > "$W/out/$name.log" 2>&1
	got=$(grep -c '^== ' "$W/out/$name.log")
	kept=$(wc -l < "$W/out/$name/raw.sha256" | tr -d ' ')
	[ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && echo "ok   $name: $got of $n cases, $kept kept files" || { echo "FAIL $name: $got of $n cases, kept $kept"; fail=1; }
done
echo "markers: $(grep -c 'resgx545 case' "$W/kmsg")"
# failure path: a hang in one case is followed by a reset and the next case runs
KEEP="$W/out/h" FAKE_HANG="vdm 1^=0x00000a00" bash "$P/run/run_table_ta.sh" vdm-series-a all > "$W/out/h.log" 2>&1
grep -q "failure: reset and health" "$W/out/h.log" && echo "ok   failure path taken" || { echo "FAIL failure path"; fail=1; }
# three failed recoveries stop the script (tool fails even the plain triangle)
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"
SGXFIVE_TEST="$W/badtool.sh" KEEP="$W/out/b" bash "$P/run/run_table_ta.sh" vdm-series-a all > "$W/out/b.log" 2>&1
grep -q "abort: the GPU did not recover three times" "$W/out/b.log" && echo "ok   three failed recoveries stop the script" || { echo "FAIL stop rule"; fail=1; }
echo "work dir (kept for inspection): $W"
exit $fail
