#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_k.sh [DIR]: static check of everything that runs in R3K-regress against the forbidden list.  Run before staging.  (This is
# the session's own static check; the clean-room guard of the repo is never run here.)  Stricter than R3K-pixel's:
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / any compile; no trc_hazard; no clock-gate
#   register; no kreg, no kregnow, no kpoke (not even a table's --kpoke-render, not even in a script), no kicker, no firmware-task
#   str (own_code, own_arm, own_res), no /dev/mem write, no git, no delete, no wait loop, no `| tail` or `|| true` that could
#   hide a status, no `set -f`, EVERY debugfs access through `sudo -n`; the ONLY debugfs write is dbg_write of `reset`; no
#   hold_recovery or render_rgn_arrays write; no held job, bif row, idle row, rgn knob or hypothesis group in a table; no
#   --fault, no --poke other than cmd: words, --geometry only 1 to 3, no --kreg/--kpoke-*/--ctx2/--share-pb/--depth/--late/
#   --low/--place/--words/--regs/--dump-each in a table (--move is a userspace triangle offset and allowed).
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|kregnow|kpoke|own_code|own_arm|own_res|/dev/mem|rm -|git |\| *tail|\|\| *true'
BADT='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg|kicker|own_code|own_arm|own_res|/dev/mem'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in run/*.sh run/k.env tables/*.txt; do
	[ -f "$f" ] || continue
	case "$f" in run/guard_k.sh) continue ;; esac
	B=$BAD; case "$f" in tables/*) B=$BADT ;; esac
	# (the preflight's list of debugfs files that must exist names kregnow, kpoke and kicker: only that line is excepted, and
	# it only tests for existence)
	if code "$B" "$f" | grep -vE '^[0-9]+:[[:space:]]*for f in reset hold_recovery regs render_param .* kregnow kpoke kicker; do'; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f (it disables the globs that keep the dumps)"; st=1; fi
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# every write to a debugfs path goes through dbg_write (tee "$D/$1"): no other tee/redirect into $D
if grep -hnE '(tee|>>?)[^|]*"\$D/' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is not dbg_write"; st=1
fi
# dbg_write names: reset only; dbg_write itself allows exactly reset
if grep -hnE 'dbg_write [a-z_]+' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'dbg_write reset( |$)|dbg_write\(\)|dbg_write: |"\$1"|dbg_write "\$1"'; then
	echo "dbg_write of a file that is not reset"; st=1
fi
awk '/^dbg_write\(\)/ {f=1} f && /case "\$1" in/ {c=1} f && c && /^\t[a-z_|]+\) / {print} /^}/ {f=0; c=0}' run/lib_k.sh | grep -vE '^\treset\) ;;$' | grep -vE '^\t\*\)' && { echo "dbg_write allows a name other than reset"; st=1; }
# every timeout on the laptop also kills (-k): a job that ignores TERM must not outlive its bound
for f in run/lib_k.sh run/run_stage.sh; do
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# the runner ignores SIGPIPE and SIGHUP (a dropped ssh must not stop a stage half way)
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
# the runner checks the srcversion (installed = loaded = the expected build), reads the knobs before every job and keeps the
# markers by appending (tee -a: O_WRONLY|O_APPEND)
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_k.sh || { echo "run/lib_k.sh does not compare the module srcversion"; st=1; }
grep -q 'SRCV_EXPECT' run/lib_k.sh || { echo "run/lib_k.sh does not check the expected module build"; st=1; }
grep -q 'knobs_ok ||' run/run_stage.sh || { echo "run/run_stage.sh does not read the knobs before a job"; st=1; }
grep -q 'sudo -n tee -a "\$KMSG"' run/lib_k.sh || { echo "run/lib_k.sh does not append its kernel-log markers (tee -a)"; st=1; }
if grep -nE 'tee "\$KMSG"|tee /dev/kmsg|> *"?\$KMSG|> */dev/kmsg' run/*.sh | grep -v guard_k.sh | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#'; then echo "a kernel-log write that is not an append"; st=1; fi
# every ssh and scp of the Mac side is time-bounded (bounded SECONDS ...)
for f in run/k.sh run/stage_k.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables
if grep -nE -- '--kreg|--kpoke|--ctx2|--share-pb|--depth|xfer_ro|--late|--low|--place|--words|--regs|--dump-each|--fault|--hold|--bif' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
if grep -nE -- '--geometry' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#' | grep -vE -- '--geometry [123]( |$)'; then echo "a --geometry other than 1 to 3"; st=1; fi
for t in tables/*.txt; do
	[ -f "$t" ] || continue
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] != "expectdiff" && k[i] != "stophang") bad = 1; if ($5 != "-") bad = 1 } END { exit !bad }' "$t"; then
		echo "$t: a knob (held, bif, idle, rgn, hypo, noreset, ...) or an rt that this session does not allow"; st=1
	fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 ~ /^tri / && $4 !~ /expectdiff/' "$t" | grep -q .; then echo "$t: a tri row without expectdiff"; st=1; fi
done
exit $st
