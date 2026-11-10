#!/bin/sh
# fake sgxfive-test: the health triangle prints the exact diff; a job whose arguments contain $FAKE_HANG prints a
# hung job (and a driver line to the fake kernel log); $FAKE_FATAL a lockup line; $FAKE_TIMEOUT exits 124;
# $FAKE_FAULT a faulted job; $FAKE_DIFF prints a reference mismatch with rc 1; $FAKE_NODIFF rc 1 with no diff line;
# the others print ok.  A successful job writes dump files where --dump-render / --depth-dump / --words point
# (the runner must KEEP them).
echo "$*" >> "${FAKE_LOG:-/dev/null}"
case "$*" in
  tri)
    # $FAKE_TRI_FAIL_NTH=N: the Nth plain triangle (health, gate) prints a wrong diff (counted in $FAKE_TRI_COUNT)
    if [ -n "${FAKE_TRI_FAIL_NTH:-}" ]; then
      n=$(cat "$FAKE_TRI_COUNT" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$FAKE_TRI_COUNT"
      if [ "$n" = "$FAKE_TRI_FAIL_NTH" ]; then echo "diff: 5 of 4096 pixels"; exit 1; fi
    fi
    echo "diff: 0 of 4096 pixels"; exit 0 ;;
esac
# $FAKE_KLOG=TEXT: a job prints TEXT into the fake kernel log (the gate's G2: a line in the job's slice)
if [ -n "${FAKE_KLOG:-}" ] && echo "$*" | grep -q -- "${FAKE_KLOG_JOB:-NOMATCH}"; then echo "gma500: [drm] odd message $FAKE_KLOG" >> "${KMSG:-/dev/null}"; fi
# $FAKE_OVERFLOW=PATTERN: such a job prints the overflow class (rc 3, "scene overflowed")
if [ -n "${FAKE_OVERFLOW:-}" ] && echo "$*" | grep -q -- "$FAKE_OVERFLOW"; then echo "probe x: failed: scene overflowed the parameter buffer, context kept (No space left on device)"; exit 3; fi
if [ -n "${FAKE_TIMEOUT:-}" ] && echo "$*" | grep -q -- "$FAKE_TIMEOUT"; then exit 124; fi
if [ -n "${FAKE_FATAL:-}" ] && echo "$*" | grep -q -- "$FAKE_FATAL"; then echo "watchdog: BUG: soft lockup - CPU#0 stuck" >> "${KMSG:-/dev/null}"; echo "job: ok"; exit 0; fi
if [ -n "${FAKE_HANG:-}" ] && echo "$*" | grep -q -- "$FAKE_HANG"; then
  echo "sgxfive: job 7 hung, recovering" >> "${KMSG:-/dev/null}"; echo "probe x: failed: job hung, context lost (Connection timed out)"; exit 1; fi
if [ -n "${FAKE_FAULT:-}" ] && echo "$*" | grep -q -- "$FAKE_FAULT"; then
  echo "probe x: failed: job faulted, context lost (Input/output error)"; exit 1; fi
if [ -n "${FAKE_DIFF:-}" ] && echo "$*" | grep -q -- "$FAKE_DIFF"; then echo "diff: 5 of 786432 pixels"; exit 1; fi
if [ -n "${FAKE_NODIFF:-}" ] && echo "$*" | grep -q -- "$FAKE_NODIFF"; then echo "something went wrong"; exit 1; fi
prev=""
for a in "$@"; do
  case "$prev" in
    --dump-render) echo param > "$a/fake.param.bin"; echo tadata > "$a/fake.tadata.bin" ;;
    --depth-dump) echo depth > "$a/depth.1.bin" ;;
    --words) echo words > "$a/words.0.txt" ;;
  esac
  prev=$a
done
echo "job: ok"; echo "target: 64x64"; exit 0
