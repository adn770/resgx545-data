#!/bin/bash
# fake sgxfive-test for tests/run_mock.sh.  The health triangle (`tri` alone) prints the exact diff unless FAKE_HEALTH_BAD.  A probe job
# plays a world (default: bit 6 of STATUS2 set when the multiply-adds of an instance reach 330; bit 7 when N x body / 8 x vertices / 3 >=
# 1200; a loop that proves itself) and writes the fake STATUS2 and the burst into $FAKE_DIR for the fake sudo and the fake regtimeline.
# FAKE_RULES: "PATTERN|OUTCOME" lines; PATTERN a fixed string of the arguments; the first match wins:
#   ok                   the default world
#   noloop               the loop does not run: o0 is not the MARK (the backward branch did not loop), STATUS2 unchanged
#   fault:WORD:ADDR      a BIF fault (the kernel's recovery is logged), rc 1
#   hang                 "job hung", rc 1;   timeout  exits 124 (a freeze);   fatal  logs a soft lockup
#   st2:HEX              STATUS2 after the job is HEX (e.g. st2:0x440), whatever the world says
#   headmsg              the tool's error line comes FIRST, then 12000 characters of rows (the message must be found in the whole output)
#   nodiff               rc 1, no diff line
P=${FAKE_P:-$(cd "$(dirname "$0")/.." && pwd)}
echo "$*" >> "${FAKE_LOG:-/dev/null}"
if [ "$*" = tri ]; then
	[ -n "${FAKE_HEALTH_BAD:-}" ] && { echo "job: failed: job faulted, context lost (Input/output error)"; exit 1; }
	echo "diff: 0 of 4096 pixels"; exit 0
fi
outcome=ok
args=" $* "
IFS=$'\n'
for r in $(printf '%s\n' "${FAKE_RULES:-}"); do
	[ -z "$r" ] && continue
	pat=${r%%|*}
	case "$args" in *"$pat"*) outcome=${r#*|}; break ;; esac
done
unset IFS
w=64; h=32; full=0; vertices=3; dump=""; prev=""; prog=""
for a in "$@"; do
	case "$prev" in --width) w=$a ;; --height) h=$a ;; --vertices) vertices=$a ;; --dump-render) dump=$a ;; esac
	[ "$a" = --tri-full ] && full=1
	prev=$a
done
tri=0; for a in "$@"; do [ "$a" = --tri ] && tri=1; done
prog=$(basename "${!#}" .bin)
name=$prog
[ "$tri" = 1 ] || { w=64; h=32; }
st2=""; B=600; t6=200; t7=300
case "$outcome" in
timeout) exit 124 ;;
fatal) echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "$KMSG"; echo "job: ok"; exit 0 ;;
fault:*)
	IFS=: read -r _ word addr <<EOF
$outcome
EOF
	echo "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault $word at $addr (PD 0x0) stalls job 7, recovering" >> "$KMSG"
	echo "job: failed: job faulted, context lost (Input/output error)"; exit 1 ;;
hang)
	echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovering" >> "$KMSG"
	echo "job: failed: job hung, context lost (Connection timed out)"; exit 1 ;;
nodiff) echo "something went wrong"; exit 1 ;;
headmsg) echo "probe $name: failed: job hung, context lost (Connection timed out)"
	for i in $(seq 1 200); do echo "probe $name: row $i: 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000"; done
	exit 1 ;;
esac
# the default world
n=0; kind=""
case "$prog" in
loop-rel-*|loop-abs-*) kind=$(echo "$prog" | sed -e 's/^loop-[a-z]*-//' -e 's/-i[0-9]*$//'); n=$(echo "$prog" | sed 's/.*-i//') ;;
vloop-*) kind=$(echo "$prog" | sed -e 's/^vloop-//' -e 's/-i[0-9]*$//'); n=$(echo "$prog" | sed 's/.*-i//') ;;
esac
imae=0; body=8
case "$kind" in b16) imae=14; body=16 ;; b12) imae=10; body=12 ;; b8) imae=6 ;; b4) imae=2; body=4 ;; ld8) imae=4 ;; b2) body=2 ;; b8n) imae=0 ;; b16v) body=16 ;; b4v) body=4 ;; b8v) body=8 ;; esac
bit6=0; bit7=0
case "$prog" in
loop-*) [ $((imae * n)) -ge 330 ] && bit6=1
	B=$(( 60 + 9 * body * n / 8 )) ;;
vloop-*) [ $((n * body * vertices / 24)) -ge 1200 ] && bit7=1
	B=$(( 100 + n * body * vertices / 6 )) ;;
esac
# the proof line
mark=$(printf '0x%08x' $((0xC0DE0000 | n)))
case "$prog" in
loop-abs-*) val=0x00000000 ;;
loop-rel-*) val=$mark ;;
pix_green) val=0xff00ff00 ;;
*) val="" ;;
esac
[ "$outcome" = noloop ] && val=0xdeadbeef
if [ "$tri" = 1 ]; then
	echo "probe $name: tri ${w}x${h} (2 coordinates)"
	[ "$full" = 1 ] && echo "probe $name: triangle (0,0) ($((3 * w)),0) (0,$((3 * h)))"
	case "$prog" in
	loop-rel-*|pix_green)
		if [ "$full" = 1 ]; then echo "probe $name: o0 $val ($((w * h)) of $((w * h)))"; else echo "probe $name: o0 mixed 0xff203040 x$((w * h - 1000)) $val x1000"; fi ;;
	vloop-*|vctl0) echo "probe $name: o0 mixed 0xff203040 x2998 0xff00ff00 x1098" ;;
	*) # Q276 programs: a 64x64 (or 128x128) image of background words, rows printed with --pixels
		echo "probe $name: o0 mixed 0xff203040 x$((w * h - 100)) 0x00000001 x100"
		for y in $(seq 0 $((h - 1))); do printf 'probe %s: row %d:' "$name" "$y"; for x in $(seq 1 $w); do printf ' ff203040'; done; echo; done ;;
	esac
	if [ -n "$dump" ] && [ -d "$dump" ]; then echo param > "$dump/$name.param.bin"; echo tadata > "$dump/$name.tadata.bin"; fi
else
	echo "probe $name: scratch at 0x3e003000 (64 KiB)"
	echo "probe $name: job time: 800 us"
	echo "probe $name: o0 $val (2048 of 2048)"
fi
[ -n "${FAKE_DIR:-}" ] && { echo "$B" > "$FAKE_DIR/last.b"; echo "$t6" > "$FAKE_DIR/last.t6"; echo "$t7" > "$FAKE_DIR/last.t7"; }
new=0x400
[ "$bit6" = 1 ] && new=0x440
[ "$bit7" = 1 ] && new=0x480
[ "$outcome" = noloop ] && new=0x400
case "$outcome" in st2:*) new=${outcome#st2:} ;; esac
[ -n "${FAKE_DIR:-}" ] && echo "$new" > "$FAKE_DIR/s2"
echo "job: ok"
exit 0
