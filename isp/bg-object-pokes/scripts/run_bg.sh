#!/bin/bash
# 11.35 bg-words (Q066): one tri job (64x64, every pixel printed) per case with a kernel poke bg:N of the
# render's background object (debugfs kpoke, applied at the kick), the parameter dump kept
# (--dump-render: the object as the ISP reads it, at 0x463000 of tri.N.param.bin). Table
# gen/table-bg-words.txt: control, words 0-2 (the EDM rewrites them), the vertex words 9-16, a control,
# the six zero words 3-8 last, a control. No register is written.
SCRIPT_NAME=bg-words
. "$(dirname "$0")/lib1135.sh"
begin
run_table "$(cat "$(dirname "$0")/gen/table-bg-words.txt")"
health </dev/null || true
echo "## end"
