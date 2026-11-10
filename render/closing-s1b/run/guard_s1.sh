#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_s1.sh (S1b): static check of everything that runs in S1b against the forbidden list.  Run before staging.
#   no reboot / shutdown / GRUB / kernel build or install / push-gma500; no trc_hazard; no clock-gate register
#   (CLKGATE, CR_CLKGATECTL2); no kreg, kregnow, kpoke writes of ours; no /dev/mem write; no firmware-task str
#   (own_code, own_arm, own_res); no git stash / clean / reset --hard; no recursive delete; no wait loop;
#   every line that names the debugfs ($D/, /sys/kernel/debug) runs it through sudo -n (S1: unprivileged access
#   failed on hardware).
# Exit 0 clean, 1 with the matching lines.
cd "$(dirname "$0")/.." || exit 1
BAD='reboot|shutdown|poweroff|systemctl (reboot|poweroff|kexec)|kexec|grub|update-grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|--kreg|kreg-render|\bkreg\b|own_code|own_arm|own_res|git (stash|clean|reset)|rm -r|rm -fr|rm -rf|>[[:space:]]*/dev/mem|of=/dev/mem'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
DEBUGFS='\$D/|\$\{D\}/|/sys/kernel/debug'
st=0
for f in run/lib_s1.sh run/lib_check.sh run/run_stage.sh run/s1.sh run/stage_s1.sh run/freeze_s1.sh tables/*.txt; do
	[ -f "$f" ] || continue
	# comment lines may NAME what is forbidden; code and job lines may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' ; then echo "FORBIDDEN in $f"; st=1; fi
	if grep -nE "$LOOP" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "WAIT LOOP in $f"; st=1; fi
	# debugfs only through sudo -n (code lines; the sudo must be on the same line)
	if grep -nE "$DEBUGFS" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# the tables may only use tool commands and options that write nothing but the job's own words
if grep -nE 'kpoke-render|--kreg|--kpoke|--ctx2|--share-pb|--late' tables/*.txt; then echo "FORBIDDEN option in a table"; st=1; fi
exit $st
