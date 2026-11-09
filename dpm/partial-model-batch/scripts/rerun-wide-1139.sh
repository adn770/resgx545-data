#!/bin/bash
# rerun-wide-1139.sh (on the laptop, in ~/p1139): the two cases of tables/wide.txt whose vertex count the tool
# rejected (800 and 850 are not whole triangles: rc 2, usage), under new names with 801 and 849 vertices; the
# same frozen runner and library, a table of two lines made from the frozen ones.
set -eu
H=$HOME/p1139; C=$H/ch/wide-risky-rerun
mkdir -p "$C/tables"; ln -sf "$H/lib1139.sh" "$C/lib1139.sh"; ln -sf "$H/run_table.sh" "$C/run_table.sh"
{ echo "# name|set|risk|P|knobs|rt|args: reruns of wd-hang-800-0x100 and wd-hang-850-0x100 with 801 and 849 vertices"
  grep -E '^wd-hang-(800|850)-0x100\|' "$H/tables/wide.txt" | sed -e 's/^wd-hang-800-0x100/wd-hang-801-0x100-rerun/; s/--vertices 800/--vertices 801/; s/^wd-hang-850-0x100/wd-hang-849-0x100-rerun/; s/--vertices 850/--vertices 849/'
} > "$C/tables/wide.txt"
KEEP=$HOME/p1139-dumps/wide-risky.rerun exec "$C/run_table.sh" wide risky
