#!/bin/bash
# fake sgxfive-test-rgn4 for tests/run_mock.sh.  The case is the one named by the last "resgx545 case NAME RUN" marker in $KMSG (the
# runner writes it right before the job), its output, rc, dumps, kernel lines and armed pokes come from the world directory
# $FAKE_WORLD (tests/worlds.py fake DIR WORLD).  The fake kernel's rule of fork a2788bd8: a TE_AA with bit 31 or 30 on a context
# made without --aa4 is refused (-EINVAL) unless render_rgn_arrays reads 1, 2 or 4 ($FAKE_DBGREAL/render_rgn_arrays).
# Health: `fill` and `tri` alone print an exact diff (FAKE_HEALTH_BAD: they fail).
# FAKE_RULES ("PATTERN|OUTCOME" lines, PATTERN a fixed string of the arguments) override the world:
#   fatal  logs a soft lockup;  timeout  exits 124;  hang  logs a hung job;  fault  logs a BIF fault;  nodiff  rc 1, no diff line
#   resetinfo  the world's job, with the kernel's two reset information lines logged during it (not a fault)
echo "$*" >> "${FAKE_LOG:-/dev/null}"
if [ "$*" = tri ] || [ "$*" = fill ]; then
	[ -n "${FAKE_HEALTH_BAD:-}" ] && { echo "job: failed: job faulted, context lost (Input/output error)"; exit 1; }
	[ "$*" = fill ] && { echo "diff: 0 of 2048 pixels"; exit 0; }
	echo "diff: 0 of 4096 pixels"; exit 0
fi
case_name=$(grep -o 'resgx545 case [^ ]*' "$KMSG" | tail -n 1 | cut -d' ' -f3)
WD=${FAKE_WORLD:?}
outcome=world
args=" $* "
IFS=$'\n'
for r in ${FAKE_RULES:-}; do
	[ -z "$r" ] && continue
	case "$args" in *"${r%%|*}"*) outcome=${r#*|}; break ;; esac
done
unset IFS
te=""; dump=""; aa4=0; prev=""; kp=0
for a in "$@"; do
	case "$prev" in --dump-render) dump=$a ;; --poke) case "$a" in cmd:1=*) te=${a#cmd:1=} ;; esac ;; --kpoke-render) kp=1 ;; esac
	[ "$a" = --aa4 ] && aa4=1
	prev=$a
done
echo "tri: render context for targets up to 64x64"
rgn=$(( $(cat "${FAKE_DBGREAL:?}/render_rgn_arrays") ))
if [ -n "$te" ] && [ $(( te & 0xc0000000 )) -ne 0 ] && [ $aa4 = 0 ] && [ $rgn = 0 ]; then
	echo "job: rejected (Invalid argument)"; echo "target: 64x64 hash 0xe4364b426cdce325"
	echo "diff: 4096 of 4096 pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00"; echo "sgxfive-test: render: Invalid argument"
	echo "tri: FAILED after 0 renders"; exit 1
fi
case "$outcome" in
timeout) exit 124 ;;
fatal) echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "$KMSG"; echo "job: ok"; exit 0 ;;
hang) echo "gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovering" >> "$KMSG"; echo "job: failed: job hung, context lost (Connection timed out)"; exit 1 ;;
fault) echo "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20008062 (PD 0x0) stalls job 7, recovering" >> "$KMSG"
	echo "job: failed: job faulted, context lost (Input/output error)"; exit 1 ;;
nodiff) echo "something went wrong"; exit 1 ;;
resetinfo)
	echo "gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x440" >> "$KMSG"
	echo "gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000" >> "$KMSG" ;;
esac
[ -f "$WD/$case_name.out" ] || { echo "fake tool: no world file for case '$case_name'"; exit 1; }
# the pokes are applied (or not) as the world says, and stay armed as the world says (the debugfs kpoke file)
if [ $kp = 1 ]; then cat "$WD/$case_name.kmsg" >> "$KMSG"; cat "$WD/$case_name.armed" > "$FAKE_DBGREAL/kpoke"
else cat "$WD/$case_name.kmsg" >> "$KMSG"; fi
cat "$WD/$case_name.out"
if [ -n "$dump" ] && [ -f "$WD/$case_name.param" ]; then cp "$WD/$case_name.param" "$dump/tri.param.bin"; cp "$WD/$case_name.tadata" "$dump/tri.tadata.bin"; fi
exit "$(cat "$WD/$case_name.rc")"
