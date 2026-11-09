# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# lib1141ta.sh: what every 11.41/ta script shares (sourced, never run). The script sets SCRIPT_NAME first.
# No register is written by any script of this batch: debugfs kreg and kregnow are never used, so no
# clock-gate register (CR_CLKGATECTL2 or any other) and no trc_hazard can be written. Writes: debugfs
# kpoke (cleared after each job), tadata_fill, render_keep, hold_recovery, render_pb_pages (put back),
# reset. Root through sudo -n. SGXFIVE_DEBUGFS points the tool and this library at a debugfs directory
# (the tests use a plain directory with the mock). No recursive delete anywhere.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1140}
T2=${SGXFIVE_TEST_NEW:-$HOME/sgxfive-test-1141ta}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
S39=${SGXFIVE_PROBE_BINS39:-$HOME/sgxprobes-stage-1139}
S34=${SGXFIVE_PROBE_BINS34:-$HOME/sgxprobes-stage-1134}
S41=${SGXFIVE_PROBE_BINS41:-$HOME/sgxprobes-stage-1141ta}
KEEP=${KEEP:-$HOME/p1141ta-dumps/$SCRIPT_NAME}
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
[ -x "$T" ] || { echo "no $T: the newest tool is ~/sgxfive-test-1140 (p1140/deploy1140.sh)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP"
START=$(date +%s)
sha() { sha256sum "$@"; }
preflight() {
	echo "## script $SCRIPT_NAME"; echo "## uname"; uname -r
	echo "## firmware"; sha /lib/firmware/sgx545_ukernel.fw 2>/dev/null || echo "(no firmware file)"
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	echo "## tool"; sha "$T"
	[ -x "$T2" ] && { echo "## tool (changed copy)"; sha "$T2"; }
	echo "## regtimeline"; sha "$RT" 2>/dev/null || echo "(none)"
	echo "## clock"; date
	echo "## clock-gate registers written by this script: none; trc_hazard: not touched"
}
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep "${RESET_WAIT:-3}"; }
kp_clear() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee "$KMSG" >/dev/null 2>&1; }
set_knob() { echo "$2" | sudo -n tee "$D/$1" >/dev/null; }
RUN=$(date +%s)-$$
W=$(mktemp -d)
clean_w() { # no glob in a delete: each file of the work directory and its subdirectories is removed by name
	for f in "$W"/*.out "$W"/*.bin "$W"/*.txt "$W"/dump/* "$W"/words/* "$W"/depth/* "$W"/kept/*; do
		[ -f "$f" ] && rm -f -- "$f"
	done
	return 0
}
cleanup() {
	kp_clear; set_knob hold_recovery N; set_knob render_keep 0
	printf "clear\n" | sudo -n tee "$D/tadata_fill" >/dev/null 2>&1
	[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE"
	reset_gpu; clean_w; rmdir "$W/dump" "$W/words" "$W/depth" "$W/kept" "$W" 2>/dev/null; finish_log
}
trap cleanup EXIT
finish_log() { # journalctl -k holds what the short ring buffer lost; every case has a kmsg marker
	sudo -n journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1 || sudo -n dmesg > "$KEEP/kernel.log" 2>&1
	echo "## kernel log: $(grep -c 'resgx545 case' "$KEEP/kernel.log" | tr -d ' ') case markers kept in $KEEP/kernel.log"
}
keep() { # NAME FILE [SUFFIX]: gzip the whole raw file (mtime 0), print its sizes and raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sum=$(sha "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1${3:-.txt}.gz"
	echo "$1${3:-.txt} $raw $sum" >> "$KEEP/raw.sha256"
	echo "  kept $1${3:-.txt}: $raw bytes raw, raw sha256 $sum"
}
BAD=0
tri_ok() { sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; }
health() { # a plain 64x64 triangle must draw exactly; a reset and two retries; three failures stop
	sleep "${HEALTH_WAIT:-3}"
	if tri_ok; then BAD=0; return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then BAD=0; echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then BAD=0; echo "  health: recovered on the retry"; return 0; fi
	BAD=$((BAD + 1)); echo "  health: the plain triangle does not draw ($BAD of 3 failed recoveries)"
	[ "$BAD" -ge 3 ] && { echo "## abort: the GPU did not recover three times"; exit 1; }
	return 1
}
begin() {
	printf 'name\tscript\tset\trisk\tP\tknobs\trt\targs\n' > "$KEEP/cases.tsv"; : > "$KEEP/raw.sha256"
	preflight; health
}
