#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_f.sh [DIR]: r7-faults' own static check of everything that runs (run/*.sh, run/f.env, tables/*.txt) against the forbidden
# list.  Run before staging and by tests/run_all.sh.  (The session's own check; the repo's clean-room guard is never run by it.)  From
# r6-held's guard_h.sh, for this session's files:
#   no reboot / shutdown / boot loader / kernel build or install / push-gma500 / compile; no trc_hazard; no clock-gate register; no
#   kreg, kicker, kpoke, bif_flush write, own task, /dev/mem, git; no wait loop, no `| tail`, no `|| true`, no `set -f`; EVERY debugfs
#   access through `sudo -n`; the ONLY debugfs writes are dbg_write of `reset 1`, `render_rgn_arrays 0|1`, `hold_recovery Y|N`, and
#   clr_write's one kregnow form `0x0c00^=0x10` (written in one place, bounded; clr_write called exactly four times in run_f.sh, the
#   gate pair and the cell pair, and once by the exit trap); never `peek`, `bif_flush`, `render_tail_room`, `render_pb_pages`; hold Y
#   exactly once (the held flow); kernel-log markers appended; every laptop timeout with -k; laptop files under ~/scratch only (no
#   /tmp, no TMPDIR, the one mktemp form, `rm` in its three frozen forms, the ledger and the kept directory the only files
#   appended); a free-space check before each job; the kernel log sliced by marker; ssh/scp bounded.  Tables: knobs from the allowed
#   list; --poke only cmd: words; no --kpoke*, --kreg*, --aa4, --fault ...; rows start with `tri `, `probe --temps 32 --pixels
#   "$S/NAME.bin"` (one program a row, staged and frozen) or `-` (the gate row).
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
st=0
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|kicker|kpoke|own_code|own_arm|own_res|/dev/mem|git |\| *tail|\|\| *true'
RM_OK='^[0-9]+:[[:space:]]*("\$WROOT"/\?\*\) rm -rf -- "\$1" ;;|case "\$WROOT" in "\$HOME"/scratch/tmp/r7f\.\?\?\?\?\?\?\) rm -rf -- "\$WROOT" ;; esac|trap '"'"'case "\$WROOT" in "\$HOME"/scratch/tmp/r7f\.\?\?\?\?\?\?\) rm -rf -- "\$WROOT" ;; esac'"'"' EXIT)[[:space:]]*$'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
LAP="run/lib_f.sh run/run_f.sh run/f.env"
MAC="run/f.sh run/stage_f.sh run/lib_check.sh"
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in $LAP $MAC; do
	if code "$BAD" "$f" | grep -vE "$RM_OK" | grep -vE '^[0-9]+:[[:space:]]*(# |dbg_write\(\) \{ # NAME)' | grep -vE 'bounded\(\) \{ local s=\$1; shift; perl -e'; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f"; st=1; fi
done
for f in $LAP; do
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
	if code 'python|perl' "$f"; then echo "python or perl in a laptop file $f"; st=1; fi
	if code '(^|[^a-z])/tmp|TMPDIR|r6h|r5x|r4g|r5e|~/r7f|HOME/r7f|FAKE_|(^|[^A-Z_])PY([^A-Z_]|$)' "$f"; then echo "a path outside ~/scratch/r7f and ~/scratch/tmp, or a Mac/mock variable, in $f"; st=1; fi
	if code 'mktemp' "$f" | grep -vE '^[0-9]+:WROOT=\$\(mktemp -d "\$HOME/scratch/tmp/r7f\.XXXXXX"\) \|\| \{ echo "mktemp under \$HOME/scratch/tmp failed"; exit 1; \}$'; then echo "a mktemp that is not the one form in $f"; st=1; fi
	if code '(^|[^a-z_])rm( |$)' "$f" | grep -vE "$RM_OK"; then echo "an rm that is not one of the three frozen forms in $f"; st=1; fi
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
	if code 'bif_flush' "$f" | grep -vE 'for f in reset hold_recovery regs render_pb_pages alias_skip render_rgn_arrays render_tail_room peek bif_flush kregnow; do'; then
		echo "bif_flush outside the preflight's presence check in $f"; st=1
	fi
done
[ "$(grep -hcE 'rm -rf -- ' run/lib_f.sh run/run_f.sh | paste -sd+ - | bc)" = 3 ] || { echo "not exactly three rm lines"; st=1; }
# appends: the kept directory, the work directories, the ledger; nothing else under $HOME is written
if grep -hnE '>> *"' run/lib_f.sh run/run_f.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE '>> "\$(KEEP|JW|LEDGER)/|>> "\$LEDGER"'; then echo "an append outside KEEP, JW or the ledger"; st=1; fi
grep -q '^LEDGER=\$HOME/scratch/r7f/run/minus110.ledger$' run/lib_f.sh || { echo "the ledger is not ~/scratch/r7f/run/minus110.ledger"; st=1; }
# the kernel log is sliced by marker only
if code '(sed -n [0-9]|head -n? *[0-9]|tail -n? *[0-9]).*(dmesg|kmsg|KMSG)|(dmesg|kmsg|KMSG).*(sed -n [0-9]|head |tail )' run/lib_f.sh; then echo "a line-count slice of the kernel log"; st=1; fi
grep -q 'slice_since "resgx545 case $name $RUN"' run/run_f.sh || { echo "the job slice is not by its case marker"; st=1; }
grep -q 'slice_since "resgx545 case $nm.$st $RUN"' run/run_f.sh || { echo "the step slice is not by its case marker"; st=1; }
grep -q 'slice_since "resgx545 r7f row $nm $RUN"' run/lib_f.sh || { echo "the row slice is not by its row marker"; st=1; }
grep -q '^	space_ok || { echo "## STOP: less than $MIN_FREE_MB MiB free on ~ before $name ($(free_kb) KiB)"; exit 21; }$' run/run_f.sh || { echo "no free-space check before each job"; st=1; }
[ "$(sed -n 's/^MIN_FREE_MB=${MIN_FREE_MB:-\([0-9]*\)}$/\1/p' run/f.env)" -ge 200 ] 2>/dev/null || { echo "MIN_FREE_MB missing or below HACKING's 200"; st=1; }
[ "$(sed -n 's/^BUDGET_110=${BUDGET_110:-\([0-9]*\)}$/\1/p' run/f.env)" = 16 ] || { echo "BUDGET_110 is not decision 3 (a)'s 16"; st=1; }
grep -q '^	rm_work "$JW"$' run/run_f.sh || { echo "a job's work directory is not removed after it is kept"; st=1; }
# every debugfs write goes through dbg_write (tee "$D/$1") or clr_write (tee "$D/kregnow")
if grep -hnE '(tee|>>?)[^|]*"\$D/' run/lib_f.sh run/run_f.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|tee "\$D/kregnow"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is not dbg_write or clr_write"; st=1
fi
awk '/^dbg_write\(\)/ {f=1} f && /case "\$1 \$2" in/ {c=1} f && c && /^\t"/ {print} /^}/ {f=0; c=0}' run/lib_f.sh \
	| grep -vxF $'\t"reset 1"|"render_rgn_arrays 0"|"render_rgn_arrays 1"|"hold_recovery Y"|"hold_recovery N") ;;' && { echo "dbg_write allows more than its forms"; st=1; }
if grep -hnE 'dbg_write [a-z_]+' run/lib_f.sh run/run_f.sh | grep -vE '^[0-9]+:[[:space:]]*#' \
	| grep -vE 'dbg_write reset 1( |;|$)|dbg_write render_rgn_arrays 0( |;|$)|dbg_write hold_recovery N( |;|$)|dbg_write render_rgn_arrays "\$1"; rgn_is "\$1"; \}|dbg_write hold_recovery "\$1"; dbg_cat hold_recovery; \}|dbg_write\(\)|dbg_write: '; then
	echo "dbg_write of a file or value that is not allowed"; st=1
fi
# kregnow: one write (clr_write), one value, one read (the preflight); never another row
[ "$(grep -hcE 'tee "\$D/kregnow"' run/lib_f.sh run/run_f.sh | paste -sd+ - | bc)" = 1 ] || { echo "debugfs kregnow must be written in exactly one place"; st=1; }
grep -qF "printf '%s\n' \"0x0c00^=0x10\" | sudo -n timeout -k 3 \"\$BIF_ANSWER\" tee \"\$D/kregnow\" >/dev/null 2> \"\$JW/kw.err\"" run/lib_f.sh || { echo "clr_write does not write exactly 0x0c00^=0x10, bounded"; st=1; }
if code 'kregnow' run/lib_f.sh | grep -vE 'tee "\$D/kregnow"|mark "kregnow|echo |dbg_cat kregnow > "\$WROOT/kregnow.pre"|kregnow\.pre|for f in reset |0x0c00\^=0x10 rc'; then echo "an unexpected kregnow line in run/lib_f.sh"; st=1; fi
if code 'kregnow' run/run_f.sh | grep -vE 'echo '; then echo "kregnow outside clr_write in run/run_f.sh"; st=1; fi
[ "$(grep -vE '^[[:space:]]*#' run/run_f.sh | grep -oE 'clr_write [^;|&]*' | grep -c .)" = 4 ] && [ "$(grep -cE '^[[:space:]]*clr_write "\$name" (set|clear)' run/run_f.sh)" = 4 ] || { echo "clr_write is not called exactly four times in run_f.sh (the gate pair, the cell pair)"; st=1; }
[ "$(grep -vE '^[[:space:]]*#' run/lib_f.sh | grep -cE 'clr_write [a-z]')" = 1 ] || { echo "clr_write is not called exactly once in lib_f.sh (the exit trap)"; st=1; }
grep -nE '(peek|render_tail_room|render_pb_pages|bif_flush)' run/lib_f.sh run/run_f.sh | grep -E 'tee|dbg_write|>' | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#|echo ' && { echo "peek, render_tail_room, render_pb_pages or bif_flush written"; st=1; }
[ "$(grep -cE 'set_hold Y' run/run_f.sh)" = 1 ] || { echo "set_hold Y is not exactly once in run_f.sh"; st=1; }
grep -nE 'set_hold Y|hold_recovery Y' run/lib_f.sh | grep -vE '^[0-9]+:[[:space:]]*#|"hold_recovery Y"\|' && { echo "hold_recovery Y in lib_f.sh"; st=1; }
if grep -hnE 'rgn_set [^(]' run/run_f.sh | grep -vE 'rgn_set (0|"\$rgn")( |;|$)'; then echo "rgn_set with another value"; st=1; fi
grep -q "^trap '' PIPE HUP\$" run/run_f.sh || { echo "run_f.sh does not ignore PIPE and HUP"; st=1; }
grep -q 'modinfo -F srcversion gma500_gfx' run/lib_f.sh && grep -q 'SRCV_EXPECT' run/lib_f.sh || { echo "no srcversion check"; st=1; }
grep -qE '^SRCV_EXPECT=[0-9A-Z]+$' run/f.env || { echo "f.env does not pin a module srcversion (tests/run_mock.sh checks it is 41E2F5C756F96D20F7109A4)"; st=1; }
for f in render_tail_room peek bif_flush kregnow; do grep -q "for f in .*$f" run/lib_f.sh || { echo "the preflight does not check debugfs $f"; st=1; }; done
for k in 'dbg_write hold_recovery N' 'dbg_write render_rgn_arrays 0'; do grep -q "^	$k\$" run/lib_f.sh || { echo "the exit trap does not run: $k"; st=1; }; done
grep -q 'sudo -n tee -a "\$KMSG"' run/lib_f.sh || { echo "markers are not appended (tee -a)"; st=1; }
if grep -nE 'tee "\$KMSG"|tee /dev/kmsg|> *"?\$KMSG|> */dev/kmsg' run/lib_f.sh run/run_f.sh | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#'; then echo "a kernel-log write that is not an append"; st=1; fi
for f in run/f.sh run/stage_f.sh; do
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables
TB="tables/s0.txt tables/l.txt tables/d.txt tables/m.txt"
if grep -nE -- '--kreg|--kpoke|--ctx2|--share-pb|--depth|xfer_ro|--late|--low|--place|--words|--dump-each|--fault|--hold|--bif|--close|--emit-scene|--stencil|--scratch|--tadata-fill|--aa4|--regs|--cmd|--pds|--use|--coords|--tri |--slot' $TB | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' $TB | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
for t in $TB; do
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|gate|probe|rgn:1|held|clr|long|ctl640|hypo:[a-z0-9]+:[0-9]+|cell:health)$/) bad = 1; if ($5 != "-") bad = 1 } END { exit !bad }' "$t"; then
		echo "$t: a knob or an rt that r7-faults does not allow"; st=1
	fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 !~ /^(tri |probe --temps 32 --pixels "\$S\/[a-z0-9-]+\.bin"$|-$)/' "$t" | grep -q .; then echo "$t: a row that is not tri, the one-program probe or the gate row"; st=1; fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 == "-" && $4 != "gate"' "$t" | grep -q .; then echo "$t: a row without a command that is not the gate row"; st=1; fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 ~ /^probe / && $4 != "probe"' "$t" | grep -q .; then echo "$t: a probe row whose knobs are not exactly probe"; st=1; fi
done
for b in $(sed -n 's#.*"\$S/\([a-z0-9-]*\.bin\)".*#\1#p' $TB); do [ -f "bins/$b" ] || { echo "a table names bins/$b, which does not exist"; st=1; }; done
exit $st
