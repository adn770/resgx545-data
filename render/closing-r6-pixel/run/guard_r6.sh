#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r6.sh [DIR]: static check of everything that runs in R6-pixel against the forbidden list.  Run before staging.
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / any compile; no trc_hazard; no clock-gate
#   register; no kreg, kregnow; kpoke only as R6-pixel allows it (the tool's `--kpoke rd:9=0|1` on table rows carrying the knob
#   kpoke, the runner's reads of debugfs kpoke and its `dbg_write kpoke clear`); no /dev/mem write; no firmware-task str
#   (own_code, own_arm, own_res); no git; no delete but the two removals of the work directories (rmwork's and the exit's,
#   both behind a path check); no /tmp and no mktemp but `mktemp -d "$R6TMP/r6p.XXXXXX"` (round 6: laptop files under
#   ~/scratch only); no wait loop; no `| tail` or `|| true` that could hide a status; no `set -f` (it stopped dumps from
#   being kept); and EVERY debugfs access through `sudo -n` (debugfs is root only: a bare `[ -e "$D/x" ]` or an
#   unprivileged glob stopped S1's first sessions).
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|kregnow|kreg[^a-z_]|kreg$|own_code|own_arm|own_res|(^|[;&|[:space:]])git |(^|[;&|[:space:]])rm |rmdir|unlink|>[[:space:]]*/dev/mem|of=/dev/mem|\| *tail|\|\| *true|\|\| *:|dbg_write hold_recovery|set_hold|dbg_write render_pb'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
# the only removals: rmwork's `rm -rf -- "$1"` and the exit's `rm -rf -- "$WROOT"`, each on a line with its path check
RMOK='^[0-9]+:[[:space:]]*(rm -rf -- "\$1" \|\| \{ echo "  rmwork: could not remove \$1 \(left in place\)"; return 1; \}|case "\$WROOT" in "\$R6TMP"/r6p\.\*\) rm -rf -- "\$WROOT" ;; esac)$'
# the only kpoke lines of the scripts
KPOK='kpoke_armed|dbg_write kpoke clear|reset:1\|kpoke:clear|NEED_KPOKE|kpoke\) kpk=1|\$kpk|\*kpoke\*\)|--kpoke rd:9=0 |--kpoke rd:9=1 |grep -o -- .--kpoke.|without the knob kpoke|a kpoke other than|more than one --kpoke|kpoke after:|debugfs kpoke|kpoke armed|kpoke=\['
for f in run/*.sh run/r6.env tables/*.txt; do
	[ -f "$f" ] || continue
	case "$f" in run/guard_r6.sh) continue ;; esac
	if code "$BAD" "$f" | grep -vE "$RMOK"; then echo "FORBIDDEN in $f"; st=1; fi
	case "$f" in
	tables/*)
		# a table row may carry --kpoke only as `--kpoke rd:9=0|1`, once, with the knob kpoke
		if grep -vE '^#' "$f" | awk -F'|' 'NF >= 6 && $6 ~ /kpoke/ { n = gsub(/--kpoke rd:9=[01] /, "&", $6); m = gsub(/kpoke/, "&", $6); if (n != 1 || m != 1 || $4 !~ /(^| )kpoke( |$)/) print }' | grep .; then
			echo "a kpoke that is not one --kpoke rd:9=0|1 on a row with the knob kpoke in $f"; st=1
		fi ;;
	*)
		if code 'kpoke' "$f" | grep -vE "$KPOK"; then echo "a kpoke use R6-pixel does not allow in $f"; st=1; fi
		if code '(^|[^a-zA-Z0-9_.])/tmp' "$f"; then echo "/tmp in $f (laptop files under ~/scratch only)"; st=1; fi
		if code 'mktemp' "$f" | grep -v 'mktemp -d "\$R6TMP/r6p.XXXXXX"'; then echo "a mktemp that is not under \$R6TMP in $f"; st=1; fi ;;
	esac
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f (it disables the globs that keep the dumps)"; st=1; fi
	# a debugfs path on a code line without sudo -n: an unprivileged access
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# every timeout on the laptop also kills (-k): a job that ignores TERM must not outlive its bound
for f in run/lib_r6.sh run/run_stage.sh; do
	grep -q 'space_ok' "$f" || { echo "no free-space check in $f"; st=1; }
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# the runner ignores SIGPIPE and SIGHUP (a dropped ssh must not stop a stage half way)
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
# the runner checks the srcversion and walks the table without set -f
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_r6.sh || { echo "run/lib_r6.sh does not compare the module srcversion"; st=1; }
# every ssh and scp of the Mac side is time-bounded (bounded SECONDS ...)
for f in run/r6.sh run/stage_r6.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables may only use tool options that write nothing but the job's own command words (--poke cmd:N= is a render
# command word of the job, as S3's; no kernel word but the kpoke rows above, no register, no PB/DPM knob)
if grep -nE -- '--kreg|kpoke-render|--kpoke-job|--ctx2|--share-pb|--depth|--geometry|xfer_ro|--late|--low|--place' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
# decision R3-P1: an absolute `ba` loop in a --tri slot lands in other code (E770): no table row with a --tri slot may stage
# an `abs` loop program (the abs controls are fills)
if grep -nE -- '--tri .*loop-abs|loop-abs.*--tri ' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "an abs (ba) loop program in a --tri row"; st=1
fi
exit $st
