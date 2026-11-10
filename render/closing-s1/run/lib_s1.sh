# SPDX-License-Identifier: MIT
# lib_s1.sh: what the laptop-side S1 stage runner shares (sourced by run_stage.sh, never run).
#
# Safety rules of this runner (checked by run/guard_s1.sh):
#  - the only debugfs files ever written: render_pb_pages, alias_skip, reset (set_knob has an allow-list)
#    and /dev/kmsg for the markers.  No kreg, no kregnow, no kpoke write of ours, no /dev/mem write, no
#    clock-gate register (CR_CLKGATECTL, CR_CLKGATECTL2) and no trc_hazard written by any script here.
#    (debugfs reset makes the KERNEL run its boot sequence, which writes the clock-gate registers with the
#    firmware's own values: see PREFLIGHT.md.  The established batches reset between jobs; so does this.)
#  - never a reboot, a GRUB change or a kernel build; the tool is a userspace compile (deploy-tool.sh).
#  - no firmware-task `str` (S2 only), no git, no recursive delete.
#  - no polling or wait loop: no while/until anywhere; the only delays are single fixed sleeps after a reset
#    and before a health triangle; each attempt of the health check is written out one after the other.
# Root through sudo -n.  SGXFIVE_DEBUGFS points the runner at a plain directory (tests/run_mock.sh).
set -u
STAGE=${STAGE:?lib_s1.sh: STAGE not set}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-s1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/s1-stage}
KEEP=${KEEP:-$HOME/s1-out/$STAGE}
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
[ -x "$T" ] || { echo "no $T: build it with tools/bringup/deploy-tool.sh s1 (userspace compile only)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP"
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 s1 %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }

set_knob() { # NAME VALUE: the allow-listed debugfs knobs only; echoes the read-back
	case "$1" in
	render_pb_pages|alias_skip) ;;
	*) echo "set_knob: $1 is not allowed in S1"; exit 7 ;;
	esac
	echo "$2" | sudo -n tee "$D/$1" >/dev/null
	sudo -n cat "$D/$1"
}
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep "${RESET_WAIT:-3}"; }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha /lib/firmware/sgx545_ukernel.fw 2>/dev/null || echo "(no firmware file)"
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	for f in reset render_pb_pages alias_skip regs buf09 render_param render_tadata; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (kernel too old for S1)"; exit 1; }
	done
	echo "## tool"; sha "$T"
	echo "## regtimeline"; sha "$RT" 2>/dev/null || { echo "(none: build tools/sweep/regtimeline.c for the laptop)"; [ "${NEED_RT:-1}" = 1 ] && exit 1; }
	echo "## knobs at start"
	PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "render_pb_pages=$PB_RESTORE"
	AS_RESTORE=$(sudo -n cat "$D/alias_skip" 2>/dev/null); echo "alias_skip=$AS_RESTORE"
	echo "## clock"; date
	echo "## S1 safety rules: see the header of lib_s1.sh (allow-listed knobs only)"
}

W=$(mktemp -d)
clean_w() { # no glob in a delete: each file is removed by name
	for f in "$W"/*.out "$W"/*.bin "$W"/*.txt "$W"/dump/* "$W"/words/* "$W"/depth/*; do
		[ -f "$f" ] && rm -f -- "$f"
	done
	return 0
}
FATAL_STOP=0
cleanup() {
	set_knob alias_skip "${AS_RESTORE:-0}" >/dev/null 2>&1
	[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null 2>&1
	[ "$FATAL_STOP" = 1 ] || reset_gpu
	clean_w; rmdir "$W/dump" "$W/words" "$W/depth" "$W" 2>/dev/null; finish_log
}
trap cleanup EXIT
finish_log() {
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
health() { # a plain 64x64 triangle must draw exactly; reset and two more attempts, written out one by one; three failures stop
	sleep "${HEALTH_WAIT:-3}"
	if tri_ok; then return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then echo "  health: recovered on the retry"; return 0; fi
	echo "## abort: the plain triangle does not draw after a reset and a retry (the first failed recovery stops)"
	exit 5
}
begin() {
	printf 'name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\n' > "$KEEP/cases.tsv"; : > "$KEEP/raw.sha256"
	preflight; health </dev/null
}
# kernel log lines after a marker: the slice of one job
slice_since() { sudo -n dmesg 2>/dev/null | awk -v m="$1" 'f{print} index($0,m){f=1}'; }
