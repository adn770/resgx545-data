#!/bin/bash
# fake sgxfive-test for tests/run_mock.sh (R5-pixel).  The health triangle (`tri` alone) prints the exact diff unless FAKE_HEALTH_BAD.
# Round 5 rule: the fake answers by the command's ARGV, never by a case name: a `probe --tri pixel` command goes to tests/fake_o4.py
# (the command's shape is checked against R4's C_BASE and the staged program it names runs in sgx-sim: its words make the image), a
# `probe ... --tri vtxuse` command to tests/fake_rw.py (the shape against R4's CMD, the vertex program run in sgx-sim at the tool's
# three vertices: its windows and w make a real-format object dump).  Worlds: FAKE_O4_MODEL, FAKE_RW_RULE (see those files).
# FAKE_RULES: "PATTERN|OUTCOME" lines; PATTERN a fixed string of the arguments; the first match wins:
#   fault:WORD:ADDR      a BIF fault (the kernel's recovery is logged), rc 1
#   hang                 "job hung", rc 1;   timeout  exits 124 (a freeze);   fatal  logs a soft lockup
#   st2:HEX              STATUS2 after the job is HEX
#   headmsg              the tool's error line comes FIRST, then 12000 characters of rows
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
name=$(basename "${!#}" .bin)
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
	for i in $(seq 1 200); do echo "probe $name: row $i: 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000"; done
	exit 1 ;;
esac
case " $* " in
*" --tri pixel "*) python3 "$P/tests/fake_o4.py" "$@"; rc=$?
	dump=""; prev=""; for a in "$@"; do [ "$prev" = --dump-render ] && dump=$a; prev=$a; done
	[ -n "$dump" ] && [ -d "$dump" ] && { echo param > "$dump/$name.param.bin"; echo tadata > "$dump/$name.tadata.bin"; } ;;
*" --tri vtxuse "*) python3 "$P/tests/fake_rw.py" "$@"; rc=$? ;;
*) echo "probe $name: unknown shape"; rc=2 ;;
esac
[ $rc = 0 ] || exit $rc
new=0x400
case "$outcome" in st2:*) new=${outcome#st2:} ;; esac
[ -n "${FAKE_DIR:-}" ] && echo "$new" > "$FAKE_DIR/s2"
echo "job: ok"
exit 0
