#!/bin/bash
# stage_1141ta.sh: copy stage-bins/*.bin to the laptop's ~/sgxprobes-stage-1141ta (mkdir only, no delete), then print
# their sha256 there. The programs were built offline by gen/gen_p1141ta.py and probes/ta-eot.toml (usse-asm of
# ~/src/resgx545, read only). The other programs the tables name ($S, $S34, $S39) are already on the laptop from
# earlier phases; run_table_ta.sh refuses to start a table whose '#need' files are missing.
cd "$(dirname "$0")" || exit 1
LAP="ssh -o HostKeyAlias=cedar -o BatchMode=yes -o ConnectTimeout=10 jtorra@10.42.0.2"
$LAP 'mkdir -p ~/sgxprobes-stage-1141ta'
COPYFILE_DISABLE=1 tar cf - -C stage-bins . | $LAP 'tar xf - -C ~/sgxprobes-stage-1141ta'
$LAP 'cd ~/sgxprobes-stage-1141ta && sha256sum *.bin'
