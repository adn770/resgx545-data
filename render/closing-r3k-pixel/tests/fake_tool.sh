#!/bin/bash
# fake sgxfive-test for tests/run_mock.sh.  The health triangle (`tri` alone) prints the exact diff unless FAKE_HEALTH_BAD.
# Any other job takes the first rule of FAKE_RULES ("PATTERN|OUTCOME" lines; PATTERN a fixed string of the arguments) that
# matches, else the frozen defaults (the four-array layout is the rule: a tri job faults if four arrays of the target do not
# fit the layout the knob render_rgn_arrays made; a split-flow job follows FAKE_PB (old | field | bothempty | mixed)):
#   ok                       the job completes
#   diff                     completes with 5 wrong pixels, rc 1;  nodiff  rc 1 with no diff line
#   fault:WORD:ADDR:STATUS2  a BIF fault: held (debugfs hold_recovery Y) it latches in the fake GPU state and the kernel's
#                            hold message is logged; else the kernel's own recovery is logged
#   hang                     no fault, the job does not finish
#   timeout                  exits 124 (a freeze);  fatal  logs a soft lockup;  overflow  the scene overflows (rc 1)
P=${FAKE_P:-$(cd "$(dirname "$0")/.." && pwd)}
echo "$*" >> "${FAKE_LOG:-/dev/null}"
if [ "$*" = tri ]; then
	[ -n "${FAKE_HEALTH_BAD:-}" ] && { echo "job: failed: job faulted, context lost (Input/output error)"; exit 1; }
	echo "diff: 0 of 4096 pixels"; exit 0
fi
outcome=default
rules=${FAKE_RULES:-}
args=" $* "
IFS=$'\n'
for r in $rules; do
	[ -z "$r" ] && continue
	pat=${r%%|*}
	case "$args" in *"$pat"*) outcome=${r#*|}; break ;; esac
done
unset IFS
w=64; h=64; mw=""; mh=""; dump=""; te=0; cmd=$1; prev=""; n=1; geometry=0; fault=0; pokes=()
for a in "$@"; do
	case "$prev" in
	--width) w=$a ;; --height) h=$a ;; --max-width) mw=$a ;; --max-height) mh=$a ;; -n) n=$a ;; --geometry) geometry=$a ;;
	--dump-render) dump=$a ;;
	--poke) case "$a" in cmd:1=*) te=${a#cmd:1=} ;; esac ;;
	--kpoke-render) pokes+=("${a#2:par:}") ;;
	esac
	[ "$a" = "--fault" ] && fault=1
	prev=$a
done
mw=${mw:-$w}; mh=${mh:-$h}
hold=$(cat "$FAKE_DIR/hold")
knob=$(( $(cat "$FAKE_DBGREAL/render_rgn_arrays") ))
[ "$cmd" = tri ] && echo "tri: render context for targets up to ${mw}x${mh}"
# the default outcome of each job kind
if [ "$outcome" = default ]; then
	outcome=ok
	if [ "$cmd" = probe ]; then outcome="fault:0x90002:0x3e017001:0x440"
	elif [ "$fault" = 1 ]; then outcome="fault:0x90008:0x3e000001:0x480"
	elif [ "$geometry" = 0 ] && [ $((te)) -eq $((0xe0000000)) ]; then
		fv=$("${PY:?}" "$P/tests/fake_k.py" fits "$w" "$h" "$mw" "$mh" "$knob")
		case "$fv" in fault*) pg=${fv#fault }; outcome="fault:0x90004:$(printf '0x%x' $(( pg * 4096 + 0x62 ))):0x480" ;; esac
	fi
fi
case "$outcome" in
timeout) exit 124 ;;
fatal) echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "$KMSG"; echo "job: ok"; exit 0 ;;
overflow) echo "job: failed: scene overflowed the parameter buffer, context kept (x)"; exit 1 ;;
fault:*)
	IFS=: read -r _ word addr st2 <<EOF
$outcome
EOF
	[ "$cmd" = probe ] && echo "probe ${!#}: scratch at 0x3e003000 (64 KiB)"
	if [ "$hold" = Y ]; then
		echo "$word $addr $st2 0x20000000" > "$FAKE_DIR/state"
		echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovery held (debugfs hold_recovery)" >> "$KMSG"
	else
		echo "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault $word at $addr (PD 0x0) stalls job 7, recovering" >> "$KMSG"
		echo "gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/$st2" >> "$KMSG"
	fi
	echo "job: failed: job faulted, context lost (Input/output error)"
	[ "$cmd" = tri ] && echo "diff: $((w * h)) of $((w * h)) pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00"
	exit 1 ;;
hang)
	if [ "$hold" = Y ]; then echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovery held (debugfs hold_recovery)" >> "$KMSG"
	else echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovering" >> "$KMSG"; fi
	echo "job: failed: job hung, context lost (Connection timed out)"; exit 1 ;;
nodiff) echo "something went wrong"; exit 1 ;;
esac
# a completing job
if [ "$geometry" != 0 ]; then
	# the split flow (Q285): the pokes land (kernel log), the image follows the hypothesis
	for p in "${pokes[@]+"${pokes[@]}"}"; do
		[ -n "${FAKE_NO_APPLY:-}" ] || echo "gma500 0000:00:02.0: [drm] sgxfive: kpoke par:${p%%=*}=0x$(printf '%08x' $((${p#*=}))) applied" >> "$KMSG"
	done
	if [ "${FAKE_PB_HANG_P4:-}" = 1 ] && echo "$*" | grep -q "par:11=0xffffffff"; then
		echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovering" >> "$KMSG"; echo "job: failed: job hung"; exit 1
	fi
	kind=$("${PY:?}" "$P/tests/fake_k.py" image "${FAKE_PB:-old}" "$te" "${pokes[@]+"${pokes[@]}"}")
	if [ -n "$dump" ]; then
		own=1; [ $((te & 0x20000000)) -ne 0 ] && own=0
		"${PY:?}" "$P/tests/fake_k.py" param x x "$own" "$dump/tri.param.bin" "${pokes[@]+"${pokes[@]}"}"
		echo ta > "$dump/tri.tadata.bin"
	fi
	echo "job: ok"; echo "tri 64x64 #1: geometry only, the scene left open"; echo "job: ok"
	case "$kind" in
	full) echo "target: 64x64 hash 0xd0530839d87ea325"; echo "diff: 0 of 4096 pixels"; echo "tri 64x64 #2: 4096 triangle, 0 background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0"; echo "tri: 1 of 2 renders ok"; exit 0 ;;
	partial) echo "target: 64x64 hash 0x1234567800000001"; echo "diff: 1000 of 4096 pixels, first (3, 3) 0xff203040 expected 0xff00ff00"; echo "tri 64x64 #2: 3096 triangle, 1000 background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0"; echo "tri: 1 of 2 renders ok"; exit 1 ;;
	*) echo "target: 64x64 hash 0xfc5ff15e0434a325"; echo "diff: 3969 of 4096 pixels, first (1, 1) 0xff203040 expected 0xff00ff00"; echo "tri 64x64 #2: 0 triangle, 4096 background, 0 other; wrong 3969 inside, 0 outside, 0 at edges; 3969 if flipped; guard 0"; echo "tri: 1 of 2 renders ok"; exit 1 ;;
	esac
fi
if [ -n "$dump" ]; then
	echo param > "$dump/tri.param.bin"
	"${PY:?}" "$P/tests/fake_k.py" tadata "$w" "$h" "$mw" "$mh" "$knob" "$dump/tri.tadata.bin" || exit 3
fi
echo "job: ok"; echo "target: ${w}x${h}"
[ "$outcome" = diff ] && { echo "diff: 5 of $((w * h)) pixels, first (0, 0) 0xff203040 expected 0xff00ff00"; echo "tri: 0 of 1 renders ok"; exit 1; }
echo "diff: 0 of $((w * h)) pixels"; echo "tri: 1 renders ok"; exit 0
