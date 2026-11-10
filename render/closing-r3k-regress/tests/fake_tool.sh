#!/bin/bash
# fake sgxfive-test for tests/run_mock.sh.  The health triangle (`tri` alone) prints the exact diff unless FAKE_HEALTH_BAD.
# Any other job takes the first rule of FAKE_RULES ("PATTERN|OUTCOME" lines; PATTERN a fixed string of the arguments) that matches,
# else it completes:
#   ok       the job completes (rc 0; a -n 2 / --geometry job, rc 1 with a diff line, as the real tool does)
#   diff     completes with 5 wrong pixels, rc 1;  nodiff  rc 1 with no diff line
#   fault:WORD:ADDR:STATUS2   a BIF fault (the kernel's own recovery is logged), rc 1
#   hang     no fault, the job does not finish
#   timeout  exits 124 (a freeze);  fatal  logs a soft lockup;  overflow  the scene overflows (rc 1)
echo "$*" >> "${FAKE_LOG:-/dev/null}"
if [ "$*" = tri ]; then
	[ -n "${FAKE_HEALTH_BAD:-}" ] && { echo "job: failed: job faulted, context lost (Input/output error)"; exit 1; }
	echo "diff: 0 of 4096 pixels"; exit 0
fi
outcome=ok
args=" $* "
IFS=$'\n'
for r in ${FAKE_RULES:-}; do
	[ -z "$r" ] && continue
	case "$args" in *"${r%%|*}"*) outcome=${r#*|}; break ;; esac
done
unset IFS
w=64; h=64; mw=""; mh=""; dump=""; cmd=$1; prev=""; n=1; geometry=0
for a in "$@"; do
	case "$prev" in
	--width) w=$a ;; --height) h=$a ;; --max-width) mw=$a ;; --max-height) mh=$a ;; -n) n=$a ;; --geometry) geometry=$a ;; --dump-render) dump=$a ;;
	esac
	prev=$a
done
mw=${mw:-$w}; mh=${mh:-$h}
[ "$cmd" = tri ] && echo "tri: render context for targets up to ${mw}x${mh}"
case "$outcome" in
timeout) exit 124 ;;
fatal) echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "$KMSG"; echo "job: ok"; exit 0 ;;
overflow) echo "job: failed: scene overflowed the parameter buffer, context kept (x)"; exit 1 ;;
fault:*)
	IFS=: read -r _ word addr st2 <<EOF2
$outcome
EOF2
	echo "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault $word at $addr (PD 0x0) stalls job 7, recovering" >> "$KMSG"
	echo "job: failed: job faulted, context lost (Input/output error)"; exit 1 ;;
hang)
	echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovering" >> "$KMSG"
	echo "job: failed: job hung, context lost (Connection timed out)"; exit 1 ;;
nodiff) echo "something went wrong"; exit 1 ;;
esac
if [ -n "$dump" ]; then
	if [ "$cmd" = probe ]; then b=${!#}; b=${b##*/}; b=${b%.bin}; echo param > "$dump/$b.param.bin"; echo tadata > "$dump/$b.tadata.bin"
	else echo param > "$dump/tri.param.bin"; echo tadata > "$dump/tri.tadata.bin"; fi
fi
if [ "$cmd" = probe ]; then
	echo "probe x: scratch at 0x3e003000 (64 KiB)"; echo "probe x: tri ${w}x${h}, pixel replaced"; echo "probe x: o0 0xff00ff00 ($((w * h)) of $((w * h)))"
	exit 0
fi
echo "job: ok"; echo "target: ${w}x${h} hash 0x0123456789abcde5"
if [ "$outcome" = diff ] || [ "$geometry" != 0 ]; then
	echo "diff: 5 of $((w * h)) pixels, first (0, 0) 0xff203040 expected 0xff00ff00"; echo "tri: 0 of $n renders ok"; exit 1
fi
echo "diff: 0 of $((w * h)) pixels"; echo "tri: $n renders ok"; exit 0
