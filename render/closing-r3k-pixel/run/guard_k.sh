#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_k.sh [DIR]: static check of everything that runs in R3K-pixel against the forbidden list.  Run before staging.  (This is
# the session's own static check; the clean-room guard of the repo is never run here.)
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / any compile; no trc_hazard; no clock-gate
#   register; no kreg (the allow-listed one), no firmware-task str (own_code, own_arm, own_res); no /dev/mem write; no git; no
#   delete; no wait loop; no `| tail` or `|| true` that could hide a status; no `set -f`; EVERY debugfs access through `sudo -n`;
#   and the three exceptions of this session, each pinned:
#     - debugfs kregnow is written in ONE place (bif_write of run/lib_k.sh, bounded by timeout -k), whose allow-list has exactly
#       the two forms 0x0c04=0x... and 0x0c00^=0x10; no table and no other script mentions it;
#     - dbg_write names only reset, hold_recovery and render_rgn_arrays;
#     - a table may use --kpoke-render only as `2:par:INDEX=0xVALUE` in k-pb.txt, and --geometry only as `--geometry 1`;
#       the `bif` knob only in k-bif.txt and the `rgn:` knob only as rgn:1 or rgn:4.
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|kreg([^n]|$)|kpoke|own_code|own_arm|own_res|(^|[;&|[:space:]])git |(^|[;&|[:space:]])rm |rmdir|unlink|>[[:space:]]*/dev/mem|of=/dev/mem|\| *tail|\|\| *true|\|\| *:'
BADT=${BAD/|kpoke|/|}   # a table may name --kpoke-render (checked below: only 2:par:INDEX=0xVALUE in k-pb.txt)
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
st=0
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in run/*.sh run/k.env tables/*.txt; do
	[ -f "$f" ] || continue
	case "$f" in run/guard_k.sh) continue ;; esac
	# (the preflight's list of debugfs files that must exist names kpoke: only that line is excepted)
	B=$BAD; case "$f" in tables/*) B=$BADT ;; esac
	if code "$B" "$f" | grep -vE '^[0-9]+:[[:space:]]*for f in reset hold_recovery regs render_param .* kpoke kicker; do'; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f (it disables the globs that keep the dumps)"; st=1; fi
	# a debugfs path on a code line without sudo -n: an unprivileged access
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# kregnow: one write, in bif_write of lib_k.sh, with the two allowed forms; nowhere else (reads of the file for the preflight excepted)
n=$(grep -hE 'tee "\$D/kregnow"' run/*.sh | grep -vcE '^[[:space:]]*#')
[ "$n" = 1 ] && grep -qE 'tee "\$D/kregnow"' run/lib_k.sh || { echo "debugfs kregnow must be written in exactly one place (bif_write of run/lib_k.sh): $n"; st=1; }
for f in run/*.sh tables/*.txt; do
	case "$f" in run/lib_k.sh|run/guard_k.sh) continue ;; esac
	if code 'kregnow' "$f" | grep -vE 'echo |^[0-9]+:[[:space:]]*#'; then echo "kregnow outside run/lib_k.sh in $f"; st=1; fi
done
if code 'kregnow' run/lib_k.sh | grep -vE 'tee "\$D/kregnow"|mark "kregnow|echo |kregnow\.pre|for f in |bif_write|kregnow\) |kregnow lists'; then echo "an unexpected kregnow line in run/lib_k.sh"; st=1; fi
grep -q '0x0c04=0x\[0-9a-f\]\*)' run/lib_k.sh && grep -q '0x0c00^=0x10)' run/lib_k.sh || { echo "bif_write has lost its two-form allow-list"; st=1; }
if code '^[[:space:]]*\*\)' run/lib_k.sh | grep -n 'bif_write' > /dev/null; then :; fi
# every write to a debugfs path goes through dbg_write (tee "$D/$1") or bif_write (tee "$D/kregnow"): no other tee/redirect into $D
if grep -hnE '(tee|>>?)[^|]*"\$D/' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|tee "\$D/kregnow"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is neither dbg_write nor bif_write"; st=1
fi
# dbg_write names: reset, hold_recovery, render_rgn_arrays only
if grep -hnE 'dbg_write [a-z_]+' $(ls run/*.sh | grep -v guard_k.sh) | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'dbg_write (reset|hold_recovery|render_rgn_arrays)( |$)|dbg_write\(\)|dbg_write: |"\$1"|dbg_write "\$1"'; then
	echo "dbg_write of a file that is not reset, hold_recovery or render_rgn_arrays"; st=1
fi
# every timeout on the laptop also kills (-k): a job that ignores TERM must not outlive its bound
for f in run/lib_k.sh run/run_stage.sh; do
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# the runner ignores SIGPIPE and SIGHUP (a dropped ssh must not stop a stage half way)
grep -q "^trap '' PIPE HUP\$" run/run_stage.sh || { echo "run/run_stage.sh does not ignore PIPE and HUP"; st=1; }
# the runner checks the srcversion (installed = loaded = the expected build) and restores the knob at every exit
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_k.sh || { echo "run/lib_k.sh does not compare the module srcversion"; st=1; }
grep -q 'SRCV_EXPECT' run/lib_k.sh || { echo "run/lib_k.sh does not check the expected module build"; st=1; }
grep -q 'dbg_write render_rgn_arrays 1' run/lib_k.sh || { echo "run/lib_k.sh does not restore render_rgn_arrays in its exit"; st=1; }
# every ssh and scp of the Mac side is time-bounded (bounded SECONDS ...)
for f in run/k.sh run/stage_k.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables: options that write nothing but the job's own command words, plus the three pinned exceptions
if grep -nE -- '--kreg|--kpoke-job|--ctx2|--share-pb|--depth|xfer_ro|--late|--low|--place|--move|--words|--regs' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
if grep -nE -- '--kpoke-render' tables/*.txt | grep -vE '^[^:]*:[0-9]+:#' | grep -vE -- '--kpoke-render 2:par:[0-9]+=0x[0-9a-f]+( |$)'; then echo "a --kpoke-render that is not 2:par:INDEX=0xVALUE"; st=1; fi
for t in tables/*.txt; do
	[ -f "$t" ] || continue
	case "$t" in tables/k-pb.txt) ;; *) if grep -E -- '--kpoke-render' "$t" | grep -vqE '^#'; then echo "$t: --kpoke-render outside k-pb"; st=1; fi ;; esac
	if grep -E -- '--geometry' "$t" | grep -vE '^#' | grep -vqE -- '--geometry 1( |$)'; then echo "$t: a --geometry other than 1"; st=1; fi
	case "$t" in tables/k-pb0.txt|tables/k-pb.txt) ;; *) if grep -E -- '--geometry' "$t" | grep -vqE '^#'; then echo "$t: --geometry outside k-pb0 and k-pb"; st=1; fi ;; esac
	case "$t" in tables/k-bif.txt) ;; *) if awk -F'|' '!/^#/ && NF >= 6 && $4 ~ /(^| )bif( |$)/' "$t" | grep -q .; then echo "$t: the bif knob outside k-bif"; st=1; fi ;; esac
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] ~ /^rgn:/ && k[i] != "rgn:1" && k[i] != "rgn:4") bad = 1 } END { exit !bad }' "$t"; then echo "$t: a rgn knob that is not rgn:1 or rgn:4"; st=1; fi
done
exit $st
