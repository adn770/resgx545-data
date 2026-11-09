#!/bin/sh
# fake sgxfive-test: health triangle prints the exact diff; a job named in $FAKE_HANG (substring of any
# argument) prints a hung job; the others print ok.  Appends its arguments to $FAKE_LOG.
echo "$*" >> "${FAKE_LOG:-/dev/null}"
case "$*" in
  tri) echo "diff: 0 of 4096 pixels"; exit 0 ;;
esac
if [ -n "${FAKE_HANG:-}" ] && echo "$*" | grep -q -- "$FAKE_HANG"; then
  echo "job: failed: job hung, context lost (Connection timed out)"; exit 1
fi
echo "job: ok"; echo "target: 64x64"; exit 0
