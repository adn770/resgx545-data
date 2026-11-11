#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r3.sh (R3GC): static check of everything that runs in R3GC against the forbidden list.  Run before staging.
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500; no trc_hazard; no clock-gate register
#   (CLKGATE); no kreg, kregnow, no kpoke of any kind; no /dev/mem write; no firmware-task str (own_code, own_arm, own_res); no git
#   stash / clean / reset; no recursive delete; no wait loop; every line that names the debugfs ($D/, /sys/kernel/debug)
#   runs it through sudo -n (S1: unprivileged access failed on hardware; S1b: `[ -e ]` and globs too).
#   Tables: no --kpoke*, --kreg / --ctx2 / --share-pb / --late; the only --poke is E730's blk:1=0x00400200, in g-z only.
# Exit 0 clean, 1 with the matching lines.
cd "$(dirname "$0")/.." || exit 1
BAD='reboot|shutdown|poweroff|systemctl (reboot|poweroff|kexec)|kexec|grub|update-grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|--kreg|kreg-render|\bkreg\b|own_code|own_arm|own_res|git (stash|clean|reset)|rm -r|rm -fr|rm -rf|>[[:space:]]*/dev/mem|of=/dev/mem|tee[^|]*/kpoke|>[[:space:]]*"?\$D"?/kpoke|SGXFIVE_KPOKE'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
DEBUGFS='\$D"?/|\$\{D\}"?/|/sys/kernel/debug'
st=0
for f in run/lib_r3.sh run/lib_check.sh run/run_stage.sh run/r3.sh run/stage_r3.sh run/freeze_r3.sh tables/*.txt; do
	[ -f "$f" ] || continue
	# comment lines may NAME what is forbidden; code and job lines may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' ; then echo "FORBIDDEN in $f"; st=1; fi
	if grep -nE "$LOOP" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "WAIT LOOP in $f"; st=1; fi
	# debugfs only through sudo -n (code lines; the sudo must be on the same line)
	if grep -nE "$DEBUGFS" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# the tables may only use tool commands and options that write nothing but the job's own words: no kernel poke at all, and the
# only host-side poke is E730's `--poke blk:1=0x00400200` (g-z only)
if grep -vE '^#' tables/*.txt | grep -nE -- '--kpoke|--kreg|--ctx2|--share-pb|--late'; then echo "FORBIDDEN option in a table"; st=1; fi
for f in tables/*.txt; do
	[ -f "$f" ] || continue
	if grep -vE '^#' "$f" | grep -oE -- '--poke +[^ ]+' | awk '{if ($NF != "blk:1=0x00400200") bad=1} END{exit !bad}'; then
		echo "FORBIDDEN option in a table: a poke other than blk:1=0x00400200 ($f)"; st=1
	fi
	if [ "$(basename "$f")" != g-z.txt ] && grep -vE '^#' "$f" | grep -qE -- '--poke'; then
		echo "FORBIDDEN option in a table: a poke outside g-z ($f)"; st=1
	fi
done
exit $st
