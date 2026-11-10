#!/bin/bash
# fake sgxfive-test for tests/run_mock.sh.  The health triangle (`tri` alone) prints the exact diff unless FAKE_HEALTH_BAD.
# Any other job takes the first rule of FAKE_RULES ("PATTERN|OUTCOME" lines; PATTERN a fixed string of the arguments) that
# matches, else the default rules below (the frozen HL / H4 outcomes):
#   ok[:SLOTS[:SIZE]]        a tri job completes; --dump-render gets a TA data dump of the layout's size (or SIZE) with
#                            SLOTS region-header arrays written (default: 4 at TE 0xe0, else 1); at TE 0x20 the diff is
#                            E727's model count (28 at 320x400, 605 at 288x656), rc 1 with a diff line
#   diff                     completes with 5 wrong pixels, rc 1;  nodiff  rc 1 with no diff line
#   fault:WORD:ADDR:STATUS2  a BIF fault: held (debugfs hold_recovery Y) it latches in the fake GPU state and the kernel's
#                            hold message is logged; else the kernel's own recovery is logged
#   hang                     no fault, the job does not finish (held: the hold message; else "hung")
#   timeout                  exits 124 (a freeze);  fatal  logs a soft lockup
# A probe job (`probe ... --scratch-pages N PROGRAM`) follows the frozen layout model (tests/fake_probe.py) unless a rule
# matches: it prints the probe's output, completes, fails with rc 3 `no pixel written`, or faults.
P=${FAKE_P:-$(cd "$(dirname "$0")/.." && pwd)}
force=""
echo "$*" >> "${FAKE_LOG:-/dev/null}"
if [ "$*" = tri ]; then
	[ -n "${FAKE_HEALTH_BAD:-}" ] && { echo "job: failed: job faulted, context lost (Input/output error)"; exit 1; }
	echo "diff: 0 of 4096 pixels"; exit 0
fi
DEFAULT='--max-width 320 --max-height 400 --poke cmd:1=0xe|fault:0x90004:0x20008061:0x480
--max-width 288 --max-height 656 --poke cmd:1=0xe|fault:0x90004:0x2000d061:0x480'
outcome=ok
rules=$(printf '%s\n%s\n' "${FAKE_RULES:-}" "$DEFAULT")
args=" $* "
IFS=$'\n'
for r in $rules; do
	[ -z "$r" ] && continue
	pat=${r%%|*}
	case "$args" in *"$pat"*) outcome=${r#*|}; break ;; esac
done
unset IFS
w=64; h=64; mw=""; mh=""; dump=""; te=0; cmd=$1; prev=""; pages=16
for a in "$@"; do
	case "$prev" in
	--width) w=$a ;; --height) h=$a ;; --max-width) mw=$a ;; --max-height) mh=$a ;;
	--dump-render) dump=$a ;; --scratch-pages) pages=$a ;; --poke) case "$a" in cmd:1=*) te=${a#cmd:1=} ;; esac ;;
	esac
	prev=$a
done
mw=${mw:-$w}; mh=${mh:-$h}
hold=$(cat "$FAKE_DIR/hold")
pstate=""
if [ "$cmd" = probe ]; then
	pstate=$("${PY:?}" "$P/tests/fake_probe.py" mode "$pages" "${!#}")
	force=""; [ "$outcome" = okforce ] && { outcome=ok; force=force; pstate=ok; }
	# the frozen model decides unless a rule did
	if [ "$outcome" = ok ] && [ "$pstate" = fault ]; then
		read -r pw pa <<EOF
$("$PY" "$P/tests/fake_probe.py" fault "$pages" "${!#}")
EOF
		outcome="fault:$pw:$pa:0x440"
	fi
fi
[ "$cmd" = tri ] && echo "tri: render context for targets up to ${mw}x${mh}"
case "$outcome" in
timeout) exit 124 ;;
fatal) echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "$KMSG"; echo "job: ok"; exit 0 ;;
fault:*)
	IFS=: read -r _ word addr st2 <<EOF
$outcome
EOF
	[ "$cmd" = probe ] && echo "probe ${!#}: scratch at 0x3e003000 ($((pages * 4)) KiB)"
	if [ "$hold" = Y ]; then
		echo "$word $addr $st2 0x20000000" > "$FAKE_DIR/state"
		echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovery held (debugfs hold_recovery)" >> "$KMSG"
	else
		echo "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault $word at $addr (PD 0x0) stalls job 7, recovering" >> "$KMSG"
		echo "gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 EVENT_STATUS 0x20000000/$st2" >> "$KMSG"
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
if [ "$cmd" = probe ]; then
	"$PY" "$P/tests/fake_probe.py" out "$pages" "${!#}" $force
	[ "$pstate" = nopix ] && exit 3
	exit 0
fi
slots=""; size=""
case "$outcome" in ok:*) o=${outcome#ok:}; slots=${o%%:*}; case "$o" in *:*) size=${o#*:} ;; esac ;; esac
[ -z "$slots" ] && { [ $((te)) -eq $((0xe0000000)) ] && slots=4 || slots=1; }
if [ -n "$dump" ]; then
	echo param > "$dump/tri.param.bin"
	"${PY:?}" "$P/tests/mk_tadata.py" "$w" "$h" "$mw" "$mh" "$slots" "${size:-0}" "$dump/tri.tadata.bin" || exit 3
fi
echo "job: ok"; echo "target: ${w}x${h}"
nbad=0; first=""
if [ $((te)) -eq $((0x20000000)) ]; then
	case "${w}x${h}" in 320x400) nbad=28; first="(304, 128)" ;; 288x656) nbad=605; first="(272, 208)" ;; esac
fi
[ "$outcome" = diff ] && { nbad=5; first="(0, 0)"; }
if [ "$nbad" -gt 0 ]; then echo "diff: $nbad of $((w * h)) pixels, first $first 0xff203040 expected 0xff00ff00"; echo "tri: 0 of 1 renders ok"; exit 1; fi
echo "diff: 0 of $((w * h)) pixels"; echo "tri: 1 renders ok"; exit 0
