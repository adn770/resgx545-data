# SPDX-License-Identifier: MIT
# lib_r3.sh (R3GC): what the laptop-side R3GC stage runner shares (sourced by run_stage.sh, never run).
# Built from R1's lib_r1.sh with its fixes kept (every item below is tested in tests/run_mock.sh).
#
# Safety rules of this runner (checked by run/guard_r3.sh):
#  - the only debugfs files ever written by the runner: render_pb_pages (allow-listed set_knob) and reset (the kernel's own
#    reset, also the stuck-job watchdog), plus /dev/kmsg for the markers.  No kreg, no kregnow, no kpoke at all (no pb:11
#    poke in this session), no /dev/mem write, no clock-gate register and no trc_hazard written by any script here.  The only
#    write of any kind besides those is the TOOL's host-side `--poke blk:1=0x00400200` of the g-z rows (E730's own option: a
#    word of the triangle's state block in the tool's memory, no register).
#  - EVERY debugfs access (read, write, test, glob) goes through sudo -n (S1: an unprivileged read failed; S1b: `[ -e ]` and
#    globs too); run/guard_r3.sh refuses a code line that names the debugfs without sudo.
#  - the debugfs directory is the FIRST of `dri/*/sgx` (the node has three names: dri/0, dri/0000:00:02.0, dri/128): never
#    "exactly one".
#  - never a reboot, a boot-loader change or a kernel build; the tool is R1's binary, nothing is built on the laptop.
#  - no firmware-task `str`, no git, no recursive delete (work files are removed one by one by name).
#  - no polling or wait loop: no while/until anywhere; the only delays are single fixed sleeps after a reset and before a
#    health triangle (and the one background `sleep` of a poke row's watchdog); each attempt of the health check is written out one after the other.
# Root through sudo -n.  SGXFIVE_DEBUGFS points the runner at a plain directory (tests/run_mock.sh).
set -u
STAGE=${STAGE:?lib_r3.sh: STAGE not set}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-r1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/r3gc-stage}
OUTROOT=${OUTROOT:-$HOME/r3gc-out}
KEEP=${KEEP:-$OUTROOT/$STAGE}
TOOL_SHA_FILE=${TOOL_SHA_FILE:-$HOME/r3gc/TOOL.sha256}
WANT_SRCV=${WANT_SRCV:-B21FDA82BD5E5CB5A627E3B}   # E625/E730/E779 ran on this module; any other stops the stage
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
[ -x "$T" ] || { echo "no $T: stage it with run/stage_r3.sh (R1's tool must be in place)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP"
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 r3gc %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }

set_knob() { # NAME VALUE: the allow-listed debugfs knob only; echoes the read-back
	case "$1" in
	render_pb_pages) ;;
	*) echo "set_knob: $1 is not allowed in R2"; exit 7 ;;
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
	[ "$SRCV_LOADED" = "$WANT_SRCV" ] || { echo "the module srcversion is $SRCV_LOADED, the session was built for $WANT_SRCV"; exit 1; }
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (kernel too old for R2)"; exit 1; }
	done
	[ "$NEED_KPOKE" = 1 ] && { sudo -n test -e "$D/kpoke" || { echo "the loaded driver has no debugfs kpoke (g-c2 needs it)"; exit 1; }; }
	echo "## debugfs directory: $D"
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	want=$(cut -d' ' -f1 "$TOOL_SHA_FILE" 2>/dev/null)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "the tool is not the staged one ($got, staged ${want:-none}): run stage_r3.sh"; exit 1; }
	echo "## regtimeline"; sha "$RT" 2>/dev/null || { echo "(none: R1 built ~/regtimeline; it is missing)"; [ "${NEED_RT:-1}" = 1 ] && exit 1; }
	echo "## knobs at start"
	PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "render_pb_pages=$PB_RESTORE"
	[ -n "$PB_RESTORE" ] || { echo "the knob cannot be read (sudo?)"; exit 1; }
	# the markers are the job slices: one must arrive in the kernel log before any job
	mark "preflight $STAGE"
	sudo -n dmesg 2>/dev/null | grep -q "resgx545 r3gc preflight $STAGE $RUN" \
		|| { echo "the kmsg marker did not arrive in dmesg (sudo -n tee $KMSG)"; exit 1; }
	echo "## kmsg marker arrived"
	echo "## clock"; date
	echo "## R3GC safety rules: see the header of lib_r3.sh (allow-listed knob only; no kpoke; the host-side poke blk:1 only in g-z)"
}

W=$(mktemp -d "${TMPDIR:-/tmp}/r3gcw.XXXXXX")
clean_w() { # no glob in a delete: each file is removed by name
	for f in "$W"/*.out "$W"/*.bin "$W"/*.txt "$W"/*.dmesg "$W"/*.wd "$W"/dump/* "$W"/words/* "$W"/depth/*; do
		[ -f "$f" ] && rm -f -- "$f"
	done
	return 0
}
FATAL_STOP=0
cleanup() {
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
	printf 'name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\tnote\n' > "$KEEP/cases.tsv"; : > "$KEEP/raw.sha256"
	preflight; health </dev/null
}
# kernel log lines after a marker: the slice of one job
slice_since() { sudo -n dmesg 2>/dev/null | awk -v m="$1" 'f{print} index($0,m){f=1}'; }
# CR_EVENT_STATUS2 (reg 0x0118) of a debugfs regs file, as a number, or empty
status2_of() { awk '/^reg 0x0118 /{print $3; exit}' "$1" 2>/dev/null; }
