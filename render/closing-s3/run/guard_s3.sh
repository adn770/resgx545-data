#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_s3.sh [DIR]: static check of everything that runs in S3 against the forbidden list.  Run before staging.
#   no reboot / shutdown / GRUB / kernel build or install / push-gma500 / any compile; no trc_hazard; no
#   clock-gate register; no kreg, kregnow, kpoke of ours; no /dev/mem write; no firmware-task str (own_code,
#   own_arm, own_res); no git; no delete; no wait loop; no `| tail` or `|| true` that could hide a status;
#   and EVERY debugfs access through `sudo -n` (debugfs is root only: a bare `[ -e "$D/x" ]` or an
#   unprivileged glob stopped S1's first sessions).
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|kregnow|kreg|kpoke|own_code|own_arm|own_res|(^|[;&|[:space:]])git |(^|[;&|[:space:]])rm |rmdir|unlink|>[[:space:]]*/dev/mem|of=/dev/mem|\| *tail|\|\| *true|\|\| *:'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in run/*.sh run/s3.env tables/*.txt; do
	[ -f "$f" ] || continue
	case "$f" in run/guard_s3.sh) continue ;; esac
	if code "$BAD" "$f"; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	# a debugfs path on a code line without sudo -n: an unprivileged access
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# every timeout on the laptop also kills (-k): a job that ignores TERM must not outlive its bound
for f in run/lib_s3.sh run/run_stage.sh; do
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# the runner ignores SIGPIPE and SIGHUP (a dropped ssh must not stop a stage half way)
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
# every ssh and scp of the Mac side is time-bounded (bounded SECONDS ...)
for f in run/s3.sh run/stage_s3.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables may only use tool options that write nothing but the job's own command words
if grep -nE -- '--kreg|--kpoke|kpoke-render|--kpoke-job|--ctx2|--share-pb|--depth|--geometry|xfer_ro' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
exit $st
