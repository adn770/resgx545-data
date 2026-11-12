#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_m.sh [DIR]: static check of everything that runs in r6-misc against the forbidden list.  Run before staging (stage_m.sh does).
# (This is the session's own static check; the repo's clean-room guard is run separately, never by this session.)  From round 5's
# r5-render4x guard_k.sh, narrowed to this session (no knob write at all) and with round 6's laptop file rule:
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / deploy-tool / any compile; no trc_hazard; no
#   clock-gate register; no kreg, kregnow, kicker or kpoke in a script except the preflight's existence list; no firmware-task
#   str, no /dev/mem write, no git, no wait loop, no `| tail` or `|| true`, no `set -f`, no line-count slice of the kernel log;
#   EVERY debugfs access through `sudo -n`; the ONLY debugfs write is dbg_write `reset 1`;
#   laptop files: no /tmp anywhere in run/ (work dirs are mktemp -d ~/scratch/tmp/r6m.XXXXXX), the only deletes are drop_work's and
#   the exit trap's `rm -rf --` of the mktemp directory, a free-space check before each job.
#   Tables: tool t4 or t6 only; knobs from the allowed list; rows start with fill or tri; --poke only pds:pixev:12^= (q289),
#   blk:1=0x00400200 (q287) and cmd:1, 10, 13, 16 (q086); --kpoke-render only 1:ta:143, 144, 146; no --kreg, --ctx2, --fault,
#   --hold, --place, --late, --low, --scratch, --words, --regs, --emit-scene, --dump-render.
#   lead/build_tool6.sh never reaches the laptop (no SGX_TARGET_HOST).
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|kregnow|kicker|kpoke|own_code|own_arm|own_res|/dev/mem|git |\| *tail|\|\| *true|(^|[^a-zA-Z0-9_])/tmp'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
KPOKE_OK='^[0-9]+:[[:space:]]*for f in reset regs kpoke hold_recovery render_pb_pages alias_skip render_rgn_arrays; do[[:space:]]*$'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in run/*.sh run/m.env; do
	case "$f" in run/guard_m.sh) continue ;; esac
	if code "$BAD" "$f" | grep -vE "$KPOKE_OK"; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f"; st=1; fi
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
	# a delete only in the two allowed forms (lib_m.sh)
	if code '(^|[^a-z_-])rm ' "$f" | grep -vE 'rm -rf -- "\$1" ;; \*\) echo "  drop_work|"\$HOME/scratch/tmp/\$PREFIX\."\?\?\?\?\?\?\) rm -rf -- "\$WROOT" ;; esac'; then echo "a delete that is not drop_work's or the exit trap's in $f"; st=1; fi
done
for f in run/lib_m.sh run/run_stage.sh; do
	if code '(sed -n [0-9]|head -n? *[0-9]|tail -n? *[0-9]).*(dmesg|kmsg|KMSG)|(dmesg|kmsg|KMSG).*(sed -n [0-9]|head |tail )' "$f"; then echo "a line-count slice of the kernel log in $f"; st=1; fi
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# every write to a debugfs path goes through dbg_write (tee "$D/$1"); dbg_write takes `reset 1` only
if grep -hnE '(tee|>>?)[^|]*"\$D/' run/lib_m.sh run/run_stage.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is not dbg_write"; st=1
fi
if grep -hnE 'dbg_write [a-z_]+' $(ls run/*.sh | grep -v guard_m.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'dbg_write reset 1( |;|$)|dbg_write\(\)|dbg_write: '; then
	echo "dbg_write of a file or value that is not reset 1"; st=1
fi
awk '/^dbg_write\(\)/ {f=1} f && /case "\$1 \$2" in/ {c=1} f && c && /^\t"/ {print} /^}/ {f=0; c=0}' run/lib_m.sh | grep -vxF $'\t"reset 1") ;;' \
	&& { echo "dbg_write allows more than reset 1"; st=1; }
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_m.sh || { echo "run/lib_m.sh does not compare the module srcversion"; st=1; }
grep -q 'SRCV_EXPECT' run/lib_m.sh || { echo "run/lib_m.sh does not check the expected module build"; st=1; }
grep -q 'WROOT=$(mktemp -d "$HOME/scratch/tmp/$PREFIX.XXXXXX")' run/lib_m.sh || { echo "the work directory is not mktemp -d ~/scratch/tmp/PREFIX.XXXXXX"; st=1; }
grep -q '^PREFIX=r6m$' run/m.env || { echo "the laptop prefix is not r6m"; st=1; }
grep -q 'free_ok || { echo "## STOP: $fk KiB free' run/run_stage.sh || { echo "no free-space check before each job"; st=1; }
grep -q 'slice_since "resgx545 case $name $RUN"' run/run_stage.sh || { echo "the kernel log is not sliced by the case marker"; st=1; }
grep -q 'sudo -n tee -a "\$KMSG"' run/lib_m.sh || { echo "run/lib_m.sh does not append its kernel-log markers (tee -a)"; st=1; }
if grep -nE 'tee "\$KMSG"|tee /dev/kmsg|> *"?\$KMSG|> */dev/kmsg' run/*.sh | grep -v guard_m.sh | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#'; then echo "a kernel-log write that is not an append"; st=1; fi
for f in run/m.sh run/stage_m.sh lead/build_tool6.sh; do
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
if code 'SGX_TARGET|sgx-target|10\.42\.0|cedar' lead/build_tool6.sh; then echo "lead/build_tool6.sh names the laptop"; st=1; fi
# the tables
for t in tables/*.txt; do
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|strict|needhash|gateodd|hypo:[a-z0-9]+:[0-9]+)$/) bad = 1; if ($5 != "t4" && $5 != "t6") bad = 1 } END { exit !bad }' "$t"; then
		echo "$t: a knob or a tool that this session does not allow"; st=1
	fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 !~ /^(tri|fill) /' "$t" | grep -q .; then echo "$t: a row that does not start with tri or fill"; st=1; fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 ~ /^tri / && $4 !~ /expectdiff/' "$t" | grep -q .; then echo "$t: a tri row without expectdiff"; st=1; fi
	if grep -nE -- '--kreg|--ctx2|--share-pb|--fault|--hold|--place|--late|--low|--scratch|--words|--regs|--emit-scene|--dump-render|--dump-each|--cmd |--vdm |--blk |trc_hazard|(^|[^a-zA-Z0-9_])/tmp' "$t" | grep -vE '^[0-9]+:#'; then
		echo "FORBIDDEN option in $t"; st=1
	fi
	if grep -v '^#' "$t" | grep -oE -- "--poke '?[^ ']+" | grep -vE -- "^--poke '?(pds:pixev:12\^=0x[0-9a-f]+|blk:1=0x00400200|cmd:(1|10|13|16)=0x[0-9a-f]+)$"; then
		echo "$t: a --poke outside the session's three forms"; st=1
	fi
	if grep -v '^#' "$t" | grep -oE -- '--kpoke-render [^ ]+' | grep -vE -- '^--kpoke-render 1:ta:(143|144|146)=0x[0-9a-f]+$'; then
		echo "$t: a --kpoke-render outside 1:ta:143, 144, 146"; st=1
	fi
done
exit $st
