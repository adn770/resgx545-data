#!/bin/sh
# fake sgxfive-test-rgn4 (R5-dpm mock, from R3-geo's fake_tool.sh): `tri` and `fill` alone are the health jobs (exact; $FAKE_TRI_FAIL_NTH
# makes the Nth plain triangle wrong); a DPM job (probe ... --vertices, or tri --width) is answered by the WORLD from its argv and the knob
# (tests/world_r5.py); $FAKE_HANG / $FAKE_FAULT / $FAKE_FATAL / $FAKE_TIMEOUT patterns force a hang, a fault, a lockup line, rc 124.
echo "$*" >> "${FAKE_LOG:-/dev/null}"
case "$*" in
  fill) echo "diff: 0 of 2048 pixels"; exit 0 ;;
  tri)
    if [ -n "${FAKE_TRI_FAIL_NTH:-}" ]; then
      n=$(cat "$FAKE_TRI_COUNT" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$FAKE_TRI_COUNT"
      if [ "$n" = "$FAKE_TRI_FAIL_NTH" ]; then echo "diff: 5 of 4096 pixels"; exit 1; fi
    fi
    echo "diff: 0 of 4096 pixels"; exit 0 ;;
esac
if [ -n "${FAKE_TIMEOUT:-}" ] && echo "$*" | grep -q -- "$FAKE_TIMEOUT"; then exit 124; fi
if [ -n "${FAKE_FATAL:-}" ] && echo "$*" | grep -q -- "$FAKE_FATAL"; then echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "${KMSG:-/dev/null}"; fi
if [ -n "${FAKE_HANG:-}" ] && [ -n "${FAKE_HANG_P:-}" ] && echo "$*" | grep -q -- "$FAKE_HANG" && [ "$(cat "$SGXFIVE_DEBUGFS/render_pb_pages")" = "$FAKE_HANG_P" ]; then
  echo "sgxfive: job 7 hung, recovering" >> "${KMSG:-/dev/null}"; echo "probe x: failed: job hung, context lost (Connection timed out)"; exit 1; fi
if [ -n "${FAKE_FAULT:-}" ] && echo "$*" | grep -q -- "$FAKE_FAULT"; then echo "probe x: failed: job faulted, context lost (Input/output error)"; exit 1; fi
printf 'sgxfive regs 1\nreg 0x0118 0x00000400\n' > "$SGXFIVE_DEBUGFS/regs"
"${PY:?}" "$(dirname "$0")/world_r5.py" job "$@"; rc=$?
# $FAKE_BIG=PATTERN: such a job prints more than 4 KiB before the timeline (attempt 1's a0-cal-4096 was cut at 4096 bytes)
if [ -n "${FAKE_BIG:-}" ] && echo "$*" | grep -q -- "$FAKE_BIG"; then
  i=0; for i in $(seq 1 80); do echo "probe p1139-green: o$i mixed 0xff203040 x12340124 0xff00ff00 x4437092 (padding line)"; done; fi
# $FAKE_DUMPFAIL=PATTERN: the dump fails as attempt 1's did (after the overflow line)
if [ -n "${FAKE_DUMPFAIL:-}" ] && echo "$*" | grep -q -- "$FAKE_DUMPFAIL"; then echo "probe p1139-green: failed: --dump-render: Input/output error"; fi
prev=""
for a in "$@"; do
  case "$prev" in
    --dump-render) echo param > "$a/p1139-green.param.bin"; echo tadata > "$a/p1139-green.tadata.bin" ;;
    --words) echo words > "$a/words.0.txt" ;;
  esac
  prev=$a
done
exit $rc
