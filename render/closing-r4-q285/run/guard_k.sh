#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_k.sh [DIR]: static check of everything that runs in R4-A against the forbidden list.  Run before staging.  (This is the
# session's own static check; the repo's clean-room guard is run separately over a copy, counts only.)  From R3K-regress's guard:
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / any compile; no trc_hazard; no clock-gate register;
#   no kreg, no kregnow, no kicker; no kpoke in a script except the preflight's existence list and the read of what is armed after
#   a job (`dbg_cat kpoke`); no firmware-task str, no /dev/mem write, no git, no delete, no wait loop, no `| tail` or `|| true`, no
#   `set -f`, no `sed -n` slice of the kernel log (the slice is by the marker), EVERY debugfs access through `sudo -n`; the ONLY
#   debugfs writes are dbg_write of `reset 1` and `render_rgn_arrays 0|1`; no hold_recovery write.
#   Tables: knobs rgn:1, expectdiff, stophang only; no regtimeline; --poke only cmd: words; --kpoke-render only 2:par:N=0xV (set,
#   render 2, the par space); no --aa4 (the session forces one array), --kreg, --ctx2, --fault, --depth, --words, --regs ...
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|kregnow|kicker|kpoke|own_code|own_arm|own_res|/dev/mem|rm -|git |\| *tail|\|\| *true'
BADT='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg|kicker|own_code|own_arm|own_res|/dev/mem'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
# the two lines that may name kpoke: the preflight's existence list and the read of what is still armed after a job
KPOKE_OK='^[0-9]+:[[:space:]]*(for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke; do|dbg_cat kpoke > "\$JW/\$name.kpoke" 2>&1|keep "\$name" "\$JW/\$name.kpoke" ".kpoke.txt")[[:space:]]*$'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in run/*.sh run/k.env tables/*.txt; do
	[ -f "$f" ] || continue
	case "$f" in run/guard_k.sh) continue ;; esac
	B=$BAD; case "$f" in tables/*) B=$BADT ;; esac
	if code "$B" "$f" | grep -vE "$KPOKE_OK" | grep -vE '^[0-9]+:[[:space:]]*(# |dbg_write\(\) \{ # NAME)'; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f (it disables the globs that keep the dumps)"; st=1; fi
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# the kernel log is sliced by the case marker only: no line-count slice (sed -n N, head, tail) of a kernel log on the laptop
for f in run/lib_k.sh run/run_stage.sh; do
	if code '(sed -n [0-9]|head -n? *[0-9]|tail -n? *[0-9]).*(dmesg|kmsg|KMSG)|(dmesg|kmsg|KMSG).*(sed -n [0-9]|head |tail )' "$f"; then echo "a line-count slice of the kernel log in $f"; st=1; fi
done
# every write to a debugfs path goes through dbg_write (tee "$D/$1"): no other tee/redirect into $D
if grep -hnE '(tee|>>?)[^|]*"\$D/' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is not dbg_write"; st=1
fi
# dbg_write calls: reset 1, render_rgn_arrays 0|1 (literal or "$1" in rgn_set) only
if grep -hnE 'dbg_write [a-z_]+' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' \
	| grep -vE 'dbg_write reset 1( |;|$)|dbg_write render_rgn_arrays [01]( |;|$)|dbg_write render_rgn_arrays "\$1"; rgn_is "\$1"; \}|dbg_write\(\)|dbg_write: '; then
	echo "dbg_write of a file or value that is not allowed"; st=1
fi
# rgn_set is called with 0 or 1 only
if grep -hnE 'rgn_set [^(]' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'rgn_set [01]( |;|$)|rgn_set\(\)'; then
	echo "rgn_set with a value other than 0 or 1"; st=1
fi
# the allow-list inside dbg_write is exactly the three forms
awk '/^dbg_write\(\)/ {f=1} f && /case "\$1 \$2" in/ {c=1} f && c && /^\t"/ {print} /^}/ {f=0; c=0}' run/lib_k.sh \
	| grep -vxF $'\t"reset 1"|"render_rgn_arrays 0"|"render_rgn_arrays 1") ;;' && { echo "dbg_write allows more than reset 1 and render_rgn_arrays 0|1"; st=1; }
# every timeout on the laptop also kills (-k)
for f in run/lib_k.sh run/run_stage.sh; do
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_k.sh || { echo "run/lib_k.sh does not compare the module srcversion"; st=1; }
grep -q 'SRCV_EXPECT' run/lib_k.sh || { echo "run/lib_k.sh does not check the expected module build"; st=1; }
grep -q 'knobs_ok "$want_rgn" ||' run/run_stage.sh || { echo "run/run_stage.sh does not read the knobs before a job"; st=1; }
grep -q '^	dbg_write render_rgn_arrays 0$' run/lib_k.sh || { echo "run/lib_k.sh's exit trap does not put render_rgn_arrays back to 0"; st=1; }
grep -q 'slice_since "resgx545 case $name $RUN"' run/run_stage.sh || { echo "run/run_stage.sh does not slice the kernel log by the case marker"; st=1; }
grep -q 'sudo -n tee -a "\$KMSG"' run/lib_k.sh || { echo "run/lib_k.sh does not append its kernel-log markers (tee -a)"; st=1; }
if grep -nE 'tee "\$KMSG"|tee /dev/kmsg|> *"?\$KMSG|> */dev/kmsg' run/*.sh | grep -v guard_k.sh | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#'; then echo "a kernel-log write that is not an append"; st=1; fi
for f in run/k.sh run/stage_k.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables
if grep -nE -- '--kreg|--ctx2|--share-pb|--depth|xfer_ro|--late|--low|--place|--words|--regs|--dump-each|--fault|--hold|--bif|--aa4|--kpoke-render2' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
if grep -noE -- '--kpoke-render [^ ]+' tables/*.txt | grep -vE '^[^:]*:[0-9]+:--kpoke-render 2:par:[0-9]+=0x[0-9a-f]{8}$'; then
	echo "a --kpoke-render that is not 2:par:N=0xVVVVVVVV"; st=1
fi
if grep -nE -- '--geometry' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#' | grep -vE -- '--geometry 1( |$)'; then echo "a --geometry other than 1"; st=1; fi
for t in tables/*.txt; do
	[ -f "$t" ] || continue
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] != "expectdiff" && k[i] != "stophang" && k[i] != "rgn:1") bad = 1; if ($5 != "-") bad = 1 } END { exit !bad }' "$t"; then
		echo "$t: a knob or an rt that this session does not allow"; st=1
	fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 ~ /^tri / && $4 !~ /expectdiff/' "$t" | grep -q .; then echo "$t: a tri row without expectdiff"; st=1; fi
done
exit $st
