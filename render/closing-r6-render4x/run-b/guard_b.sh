#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_b.sh [DIR] [SET]: set B's guard (sets/B.env SET_GUARD): set A's run/guard_k.sh with set B's one more debugfs write, the
# render_tail_room knob (dbg_write of 0 or 0xNNN000 in 0x1000 to 0x100000, the room_set forms, the exit trap's write of 0, the table
# knob room:0xNNN000) and the preflight's file list with render_tail_room.  Default SET B.  Set A's header follows.
# guard_k.sh [DIR] [SET]: static check of everything that runs in r6-render4x's freeze set SET (A, the default) against the forbidden
# list: the driver scripts and the set's runner directory (run/*.sh, run/k.env) and the set's tables only (a later set brings its own
# guard, sets/B.env SET_GUARD).  Run before staging.  (This is the session's own static check; the repo's clean-room guard is run
# separately, never by this session.)  From r5-render4x's guard (R4-G's, itself R4-A's), with round 6's rules:
#   laptop files only under ~/scratch: no /tmp, no bare mktemp (the one form `mktemp -d "$HOME/scratch/tmp/r6x.XXXXXX"`), no ~/r5x-
#   or other session's directory; `rm` ONLY in the three frozen forms (rm_work's, under the runner's own mktemp directory; the exit
#   trap's and the early trap's, of the mktemp directory itself); a free-space check before each job; kpoke only READ (the preflight
#   list, the read after a job and its keep); in the tables --kpoke-render only `2:par:11=0xVVVVVVVV` on a `-n 2 --geometry 1` row and
#   --cmd only 1=0x40000000, 0x80000000 or 0xc0000000.  From round 5:
#   no reboot / shutdown / boot-loader / kernel build or install / push-gma500 / any compile; no trc_hazard; no clock-gate register;
#   no kreg, no kregnow, no kicker, no kpoke in a script except the preflight's existence list; no firmware-task str, no /dev/mem write,
#   no git, no delete, no wait loop, no `| tail` or `|| true`, no `set -f`, no `sed -n` slice of the kernel log (the slice is by the
#   marker), EVERY debugfs access through `sudo -n`; the ONLY debugfs writes are dbg_write of `reset 1`, `render_rgn_arrays 0|1`,
#   `render_pb_pages 0x23..0x422` and `hold_recovery Y|N` (Y only by the held flow), every one bounded; render_param and render_tadata
#   only read.
#   Tables: knobs from the allowed list only; no regtimeline; --poke only cmd: words; --regs only 0x0700-0x072c; --kpoke*, --kreg*,
#   --ctx2, --fault, --depth, --words ... never.
# Exit 0 clean, 1 with the matching lines.
cd "${1:-$(dirname "$0")/..}" || exit 1
GSET=${2:-B}
[ -f "sets/$GSET.env" ] || { echo "no sets/$GSET.env"; exit 1; }
. "sets/$GSET.env"
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|(^|[^a-z])cc |gcc|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|kregnow|kicker|kpoke|own_code|own_arm|own_res|/dev/mem|rm -|git |\| *tail|\|\| *true'
BADT='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make |build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|deploy-tool|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg|kicker|own_code|own_arm|own_res|/dev/mem|kpoke-job|kpoke-render2|--kpoke |(^|[^a-z])/tmp'
# the three lines that may remove anything: rm_work's (under the mktemp directory only), the exit trap's and the early trap's
RM_OK='^[0-9]+:[[:space:]]*("\$WROOT"/\?\*\) rm -rf -- "\$1" ;;|case "\$WROOT" in "\$HOME"/scratch/tmp/r6x\.\?\?\?\?\?\?\) rm -rf -- "\$WROOT" ;; esac|trap '"'"'case "\$WROOT" in "\$HOME"/scratch/tmp/r6x\.\?\?\?\?\?\?\) rm -rf -- "\$WROOT" ;; esac'"'"' EXIT)[[:space:]]*$'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
NOGLOB='(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f'
DBG='\$D/|"\$D"|\$\{D\}|/sys/kernel/debug'
# the one line that may name kpoke: the preflight's existence list
KPOKE_OK='^[0-9]+:[[:space:]]*(for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke render_tail_room; do|dbg_cat kpoke > "\$JW/\$name.kpoke" 2>&1|keep "\$name" "\$JW/\$name.kpoke" ".kpoke.txt")[[:space:]]*$'
st=0
# set B: the drivers set A shares with it (never set A's laptop runner, run/lib_k.sh and run/run_stage.sh) and set B's runner directory
RUNF=$(ls run/k.sh run/stage_k.sh run/freeze_k.sh run/lib_check.sh "$SET_RUNDIR"/*.sh "$SET_RUNDIR"/k.env 2>/dev/null | sort -u)
SCRIPTS=$(echo "$RUNF" | grep '\.sh$' | grep -v 'guard_k.sh$' | grep -v 'guard_b.sh$')
LIBK=$SET_RUNDIR/lib_k.sh
RSTAGE=$SET_RUNDIR/run_stage.sh
code() { grep -nE "$1" "$2" | grep -vE '^[0-9]+:[[:space:]]*#'; }
for f in $RUNF $SET_TABLES; do
	[ -f "$f" ] || continue
	case "$f" in */guard_k.sh|*/guard_b.sh) continue ;; esac
	B=$BAD; case "$f" in tables/*) B=$BADT ;; esac
	if code "$B" "$f" | grep -vE "$KPOKE_OK" | grep -vE "$RM_OK" | grep -vE '^[0-9]+:[[:space:]]*(# |dbg_write\(\) \{ # NAME)'; then echo "FORBIDDEN in $f"; st=1; fi
	if code "$LOOP" "$f"; then echo "WAIT LOOP in $f"; st=1; fi
	if code "$NOGLOB" "$f"; then echo "set -f in $f (it disables the globs that keep the dumps)"; st=1; fi
	if code "$DBG" "$f" | grep -v 'sudo -n' | grep -vE '^[0-9]+:[[:space:]]*(D=\$SGXFIVE_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)[[:space:]]*$'; then
		echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1
	fi
done
# the kernel log is sliced by the case marker only: no line-count slice (sed -n N, head, tail) of a kernel log on the laptop
for f in $LIBK $RSTAGE; do
	if code '(sed -n [0-9]|head -n? *[0-9]|tail -n? *[0-9]).*(dmesg|kmsg|KMSG)|(dmesg|kmsg|KMSG).*(sed -n [0-9]|head |tail )' "$f"; then echo "a line-count slice of the kernel log in $f"; st=1; fi
done
# laptop files: no /tmp, no ~/r5x- (or any other session's) directory, mktemp only in its one form, rm only in its three
for f in $RUNF; do
	case "$f" in */guard_k.sh|*/guard_b.sh) continue ;; esac
	if code '(^|[^a-z])/tmp|TMPDIR|r5x|r4g|r5e|r5p|r5d|~/r6x|HOME/r6x' "$f"; then echo "a path outside ~/scratch/r6x and ~/scratch/tmp in $f"; st=1; fi
	if code 'mktemp' "$f" | grep -vE '^[0-9]+:WROOT=\$\(mktemp -d "\$HOME/scratch/tmp/r6x\.XXXXXX"\) \|\| \{ echo "mktemp under \$HOME/scratch/tmp failed"; exit 1; \}$'; then echo "a mktemp that is not the one form in $f"; st=1; fi
	if code '(^|[^a-z_])rm( |$)' "$f" | grep -vE "$RM_OK"; then echo "an rm that is not one of the three frozen forms in $f"; st=1; fi
done
[ "$(grep -hcE 'rm -rf -- ' $LIBK $RSTAGE | paste -sd+ - | bc)" = 3 ] || { echo "not exactly three rm lines in $LIBK and $RSTAGE"; st=1; }
grep -q '^	space_ok || { echo "## STOP: less than $MIN_FREE_MB MiB free on ~ before $name ($(free_kb) KiB)"; exit 21; }$' "$RSTAGE" || { echo "$RSTAGE does not check the free space before each job"; st=1; }
grep -q '^MIN_FREE_MB=${MIN_FREE_MB:-[0-9][0-9]*}$' "$SET_RUNDIR/k.env" || { echo "$SET_RUNDIR/k.env does not set MIN_FREE_MB"; st=1; }
[ "$(sed -n 's/^MIN_FREE_MB=${MIN_FREE_MB:-\([0-9]*\)}$/\1/p' "$SET_RUNDIR/k.env")" -ge 200 ] 2>/dev/null || { echo "MIN_FREE_MB is below HACKING's 200"; st=1; }
grep -q '^	rm_work "$JW"$' "$RSTAGE" || { echo "$RSTAGE does not remove a job's work directory after it is kept"; st=1; }
# every write to a debugfs path goes through dbg_write (tee "$D/$1"): no other tee/redirect into $D
if grep -hnE '(tee|>>?)[^|]*"\$D/' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'tee "\$D/\$1"|cat "\$D/|2>&1'; then
	echo "a debugfs write that is not dbg_write"; st=1
fi
# a debugfs read of render_param / render_tadata is a `cat`, bounded, with the output into the job's own directory
if grep -hnE 'render_(param|tadata)' $LIBK $RSTAGE | grep -vE '^[0-9]+:[[:space:]]*#' \
	| grep -vE 'sudo -n timeout -k 5 30 cat "\$D/render_(param|tadata)" > "\$JW/held(param|tadata)\.bin" 2>&1|for f in reset hold_recovery regs render_param render_tadata render_pb_pages|render_param and render_tadata are only READ|#   |dumpheld'; then
	echo "render_param / render_tadata used other than as a bounded read"; st=1
fi
# dbg_write calls: reset 1, render_rgn_arrays 0|1, render_pb_pages 0x422, hold_recovery N (literal), or the function forms
if grep -hnE 'dbg_write [a-z_]+' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' \
	| grep -vE 'dbg_write reset 1( |;|$)|dbg_write render_rgn_arrays [01]( |;|$)|dbg_write render_pb_pages 0x422( |;|$)|dbg_write hold_recovery N( |;|$)|dbg_write render_tail_room 0( |;|$)|dbg_write render_tail_room "\$1"; room_is "\$1"; \}|dbg_write render_rgn_arrays "\$1"; rgn_is "\$1"; \}|dbg_write render_pb_pages "\$1"; pb_is "\$1"; \}|dbg_write hold_recovery "\$1"; dbg_cat hold_recovery; \}|dbg_write\(\)|dbg_write: '; then
	echo "dbg_write of a file or value that is not allowed"; st=1
fi
# set_hold is called with Y or N only; rgn_set with 0, 1 or the row's $rgn; pb_set with 0x422 or the row's $pbv
if grep -hnE 'set_hold [^(]' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'set_hold [YN]\)|set_hold\(\)'; then
	echo "set_hold with a value other than Y or N"; st=1
fi
if grep -hnE 'rgn_set [^(]' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'rgn_set (0|1|"\$rgn")( |;|$)|rgn_set\(\)'; then
	echo "rgn_set with a value other than 0, 1 or the row's"; st=1
fi
if grep -hnE 'room_set [^(]' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'room_set (0|"\$room")( |;|$)|room_set\(\)'; then
	echo "room_set with a value other than 0 or the row's"; st=1
fi
if grep -hnE 'pb_set [^(]' $SCRIPTS | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'pb_set (0x422|"\$pbv")( |;|$)|pb_set\(\)'; then
	echo "pb_set with a value other than 0x422 or the row's"; st=1
fi
# the allow-list inside dbg_write is exactly the forms of lib_k.sh's header
awk '/^dbg_write\(\)/ {f=1} f && /case "\$1 \$2" in/ {c=1} f && c && /^\t"/ {print} /^}/ {f=0; c=0}' $LIBK \
	| grep -vxF -e $'\t"reset 1"|"render_rgn_arrays 0"|"render_rgn_arrays 1"|"hold_recovery Y"|"hold_recovery N") ;;' \
	-e $'\t"render_pb_pages 0x"[0-9a-f][0-9a-f]|"render_pb_pages 0x"[0-9a-f][0-9a-f][0-9a-f])' \
	-e $'\t"render_tail_room 0") ;;' -e $'\t"render_tail_room 0x"[0-9a-f]*000)' && { echo "dbg_write allows more than the seven forms"; st=1; }
# hold_recovery Y is written by the held flow only: one `set_hold Y` in run_stage.sh, none in lib_k.sh
[ "$(grep -cE 'set_hold Y' $RSTAGE)" = 1 ] || { echo "set_hold Y is not exactly once in $RSTAGE"; st=1; }
if grep -nE 'set_hold Y|dbg_write hold_recovery Y' $LIBK | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "hold_recovery Y in $LIBK"; st=1; fi
# every timeout on the laptop also kills (-k)
for f in $LIBK $RSTAGE; do
	if code '(^|[^a-z_])timeout ' "$f" | grep -v 'timeout -k [0-9]'; then echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
grep -q "^trap '' PIPE HUP\$" $RSTAGE || { echo "$RSTAGE does not ignore PIPE and HUP"; st=1; }
grep -q 'modinfo -F srcversion gma500_gfx' $LIBK || { echo "$LIBK does not compare the module srcversion"; st=1; }
grep -q 'SRCV_EXPECT' $LIBK || { echo "$LIBK does not check the expected module build"; st=1; }
grep -q 'knobs_ok "$rgn" "$pbv" "$room" ||' $RSTAGE || { echo "$RSTAGE does not read the knobs before a job"; st=1; }
for k in 'dbg_write hold_recovery N' 'dbg_write render_pb_pages 0x422' 'dbg_write render_rgn_arrays 0' 'dbg_write render_tail_room 0'; do
	grep -q "^	$k\$" $LIBK || { echo "$LIBK's exit trap does not run: $k"; st=1; }
done
grep -q 'slice_since "resgx545 case $name $RUN"' $RSTAGE || { echo "$RSTAGE does not slice the kernel log by the case marker"; st=1; }
grep -q 'sudo -n tee -a "\$KMSG"' $LIBK || { echo "$LIBK does not append its kernel-log markers (tee -a)"; st=1; }
if grep -nE 'tee "\$KMSG"|tee /dev/kmsg|> *"?\$KMSG|> */dev/kmsg' $SCRIPTS | grep -vE '^[^:]*:[0-9]+:[[:space:]]*#'; then echo "a kernel-log write that is not an append"; st=1; fi
for f in run/k.sh run/stage_k.sh; do
	[ -f "$f" ] || continue
	if code '(^|[^a-z_])(ssh|scp) ' "$f" | grep -vE 'bounded "?[0-9$]|echo |SSHO=|SCPO='; then echo "UNBOUNDED ssh/scp in $f"; st=1; fi
done
# the tables
TB=$(for t in $SET_TABLES; do [ -f "$t" ] && echo "$t"; done)
[ -n "$TB" ] || { echo "no table of set $GSET"; st=1; }
if grep -nE -- '--kreg|--ctx2|--share-pb|--depth|xfer_ro|--late|--low|--place|--words|--dump-each|--fault|--hold|--bif|--kpoke-job|--kpoke-render2|--kpoke [^-]|--close|--emit-scene|--stencil|--scratch|--tadata-fill' $TB | grep -vE '^[^:]*:[0-9]+:#'; then
	echo "FORBIDDEN option in a table"; st=1
fi
if grep -nE -- '--poke [^c]' $TB | grep -vE '^[^:]*:[0-9]+:#'; then echo "a --poke that is not a cmd: word"; st=1; fi
if grep -noE -- '--regs [^ ]+' $TB | grep -vE '^[^:]*:[0-9]+:--regs 0x0700-0x072c$'; then echo "a --regs other than 0x0700-0x072c"; st=1; fi
if grep -noE -- '--cmd [^ ]+' $TB | grep -vE '^[^:]*:[0-9]+:--cmd 1=0x(40|80|c0)000000$'; then echo "a --cmd other than 1=0x40000000, 0x80000000, 0xc0000000"; st=1; fi
if grep -noE -- '--kpoke-render [^ ]+' $TB | grep -vE '^[^:]*:[0-9]+:--kpoke-render 2:par:11=0x[0-9a-f]{8}$'; then echo "a --kpoke-render other than 2:par:11=0xVVVVVVVV"; st=1; fi
if grep -hE -- '--kpoke-render' $TB | grep -v -- '-n 2 --geometry 1 '; then echo "a --kpoke-render on a row that is not -n 2 --geometry 1 (the poke must land between the two renders)"; st=1; fi
if grep -nE -- '--aa4 [^- ]' $TB | grep -vE '^[^:]*:[0-9]+:#'; then echo "an --aa4 with a value"; st=1; fi
for t in $TB; do
	[ -f "$t" ] || continue
	if awk -F'|' '!/^#/ && NF >= 6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|rgn:1|held|dumpheld|strict|pb:0x[0-9a-f][0-9a-f][0-9a-f]?|room:0x[0-9a-f]+000|hypo:[a-z0-9]+:[0-9]+)$/) bad = 1; if ($5 != "-") bad = 1 } END { exit !bad }' "$t"; then
		echo "$t: a knob or an rt that this session does not allow"; st=1
	fi
	if awk -F'|' '!/^#/ && NF >= 6 && $6 ~ /^tri / && $4 !~ /expectdiff/' "$t" | grep -q .; then echo "$t: a tri row without expectdiff"; st=1; fi
	# a pb: value lies in 0x23 to 0x422
	for v in $(grep -oE 'pb:0x[0-9a-f]+' "$t" | cut -d: -f2); do
		[ $((v)) -ge $((0x23)) ] && [ $((v)) -le $((0x422)) ] || { echo "$t: pb:$v is outside 0x23 to 0x422"; st=1; }
	done
	# the tool is the only program a row runs: no row starts with anything but tri, probe, fill
	if awk -F'|' '!/^#/ && NF >= 6 && $6 !~ /^(tri|probe|fill) /' "$t" | grep -q .; then echo "$t: a row that does not start with tri, probe or fill"; st=1; fi
done
exit $st
