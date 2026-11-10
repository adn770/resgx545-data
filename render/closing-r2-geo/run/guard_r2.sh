#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r2.sh (R2): static check of everything that runs in R2 against the forbidden list.  Run before staging.
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500; no trc_hazard; no clock-gate register
#   (CLKGATE); no kreg, kregnow, and no kpoke write of OURS (the only poke of the session is pb:11 = V in the g-c2 table, written
#   by the tool, never by a script); no /dev/mem write; no firmware-task str (own_code, own_arm, own_res); no git
#   stash / clean / reset; no recursive delete; no wait loop; every line that names the debugfs ($D/, /sys/kernel/debug)
#   runs it through sudo -n (S1: unprivileged access failed on hardware; S1b: `[ -e ]` and globs too).
#   Tables: no --kreg / --ctx2 / --share-pb / --late / --poke; a --kpoke / --kpoke-render / --kpoke-job value must be exactly
#   pb:11=0xHEX and only in g-c2 (and every such row needs the kpoke and wd:S knobs).
# Exit 0 clean, 1 with the matching lines.
cd "$(dirname "$0")/.." || exit 1
BAD='reboot|shutdown|poweroff|systemctl (reboot|poweroff|kexec)|kexec|grub|update-grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|--kreg|kreg-render|\bkreg\b|own_code|own_arm|own_res|git (stash|clean|reset)|rm -r|rm -fr|rm -rf|>[[:space:]]*/dev/mem|of=/dev/mem|tee[^|]*/kpoke|>[[:space:]]*"?\$D"?/kpoke|SGXFIVE_KPOKE'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
DEBUGFS='\$D"?/|\$\{D\}"?/|/sys/kernel/debug'
st=0
for f in run/lib_r2.sh run/lib_check.sh run/run_stage.sh run/r2.sh run/stage_r2.sh run/freeze_r2.sh tables/*.txt; do
	[ -f "$f" ] || continue
	# comment lines may NAME what is forbidden; code and job lines may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' ; then echo "FORBIDDEN in $f"; st=1; fi
	if grep -nE "$LOOP" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "WAIT LOOP in $f"; st=1; fi
	# debugfs only through sudo -n (code lines; the sudo must be on the same line)
	if grep -nE "$DEBUGFS" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# the tables may only use tool commands and options that write nothing but the job's own words (and pb:11 in g-c2)
if grep -nE -- '--kreg|--ctx2|--share-pb|--late|--poke' tables/*.txt; then echo "FORBIDDEN option in a table"; st=1; fi
for f in tables/*.txt; do
	[ -f "$f" ] || continue
	if grep -vE '^#' "$f" | grep -qE -- '--kpoke'; then
		[ "$(basename "$f")" = g-c2.txt ] || { echo "FORBIDDEN option in a table: a poke outside g-c2 ($f)"; st=1; }
		# every poke value must be exactly pb:11=0xHEX
		if grep -vE '^#' "$f" | grep -oE -- '--kpoke(-render|-job|2)? +([0-9]+:)?[^ ]+' | awk '{v=$NF; sub(/^[0-9]+:/,"",v); if (v !~ /^pb:11=0x[0-9a-fA-F]+$/) bad=1} END{exit !bad}'; then
			echo "FORBIDDEN option in a table: a poke that is not pb:11 ($f)"; st=1
		fi
	fi
done
exit $st
