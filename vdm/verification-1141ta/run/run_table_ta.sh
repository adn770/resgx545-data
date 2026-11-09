#!/bin/bash
# 11.41/ta run_table_ta.sh TABLE [safe|risky|all]: one job a line of tables/TABLE.txt, in the order of the
# file, whole raw output and every dump kept gzipped with its raw sha256 (raw.sha256), a kernel log
# marker per job, cases.tsv beside the dumps. Line: name|set|risk|P|knobs|rt|args
#   P      render_pb_pages for the job ("-": leave as it is); put back at exit
#   knobs  words: keep (render_keep 1, render_kept read after the tool), hold (hold_recovery Y; regs,
#          the control block and the render memory are copied before the reset), noreset (no reset
#          before this job: a job after a job; the default is a reset before every job), fill=PAGE:VALUE
#          [:ramp] (debugfs tadata_fill), new (the changed tool copy $T2, else the newest tool $T)
#   rt     "-", or a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
#   args   the tool's arguments, shell words; $W is the work directory (dump, words, depth in it)
# A failed job (fault, hang, rejected) is followed by a debugfs reset and the health triangle; an
# overflowed one is not a failure. Three failed recoveries stop the script.
TABLE=${1:?table name}
RISK=${2:-safe}
SCRIPT_NAME=$TABLE-$RISK
. "$(dirname "$0")/lib1141ta.sh"
FILE=${TABLE_DIR:-$(dirname "$0")/tables}/$TABLE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
# "#need PATH..." lines of the table: programs that must exist before the first job ($S, $S34, $S39, $S41 expand)
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: stage it first (stage_1141ta.sh)"; exit 1; }
done
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "## render_pb_pages at start: $PB_RESTORE"
begin
njob=0
while IFS='|' read -r name set risk P knobs rt args; do
	[ -z "$name" ] && continue
	case "$name" in '#'*) continue ;; esac
	[ "$RISK" = all ] || [ "$risk" = "$RISK" ] || continue
	use=$T
	case " $knobs " in *" new "*) use=$T2; [ -x "$use" ] || { echo "== $name skipped: no $T2 (the changed tool)"; continue; } ;; esac
	njob=$((njob + 1))
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" "$risk" "$P" "$knobs" "$rt" "$args" >> "$KEEP/cases.tsv"
	echo "== $name set=$set risk=$risk P=$P knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) : ;; *) reset_gpu ;; esac
	[ "$P" != "-" ] && set_knob render_pb_pages "$P"
	mkdir -p "$W/dump" "$W/words" "$W/depth" "$W/kept"; clean_w
	case " $knobs " in *" keep "*) set_knob render_keep 1 ;; esac
	case " $knobs " in *" hold "*) set_knob hold_recovery Y ;; esac
	for k in $knobs; do
		case "$k" in fill=*) f=${k#fill=}; printf '%s\n' "$(echo "$f" | tr ':' ' ')" | sudo -n tee "$D/tadata_fill" >/dev/null ;; esac
	done
	eval "set -- $args"
	echo "  cmd: $use $*"
	mark "$name"
	if [ "$rt" = "-" ]; then
		sudo -n timeout "${JOB_TIMEOUT:-120}" "$use" "$@" > "$W/$name.out" 2>&1 </dev/null
	else
		sudo -n timeout "${JOB_TIMEOUT:-120}" "$RT" 0 0.3 "$rt" -- "$use" "$@" > "$W/$name.out" 2>&1 </dev/null
	fi
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-150)"
	grep -E '^tri [0-9]+x[0-9]+ #[0-9]+:' "$W/$name.out" | cut -c1-150 | head -4
	case " $knobs " in *" hold "*)
		sleep 1
		for f in regs buf09 render_param render_tadata render_words; do
			sudo -n cat "$D/$f" > "$W/held.$f.bin" 2>/dev/null && keep "$name" "$W/held.$f.bin" ".held.$f.bin"
		done ;;
	esac
	keep "$name" "$W/$name.out"
	sudo -n cat "$D/buf09" > "$W/after.buf09.bin" 2>/dev/null && keep "$name" "$W/after.buf09.bin" ".after.buf09.bin"
	sudo -n cat "$D/regs" > "$W/after.regs.txt" 2>/dev/null && keep "$name" "$W/after.regs.txt" ".after.regs.txt"
	case " $knobs " in *" keep "*) sudo -n cat "$D/render_kept" > "$W/kept.bin" 2>/dev/null && keep "$name" "$W/kept.bin" ".kept.bin" ;; esac
	for f in "$W"/dump/* "$W"/words/* "$W"/depth/* "$W"/kept/*; do
		[ -f "$f" ] && keep "$name" "$f" ".$(basename "$f")"
	done
	kp_clear; set_knob render_keep 0; set_knob hold_recovery N
	printf 'clear\n' | sudo -n tee "$D/tadata_fill" >/dev/null 2>&1
	if grep -qE "faulted|hung|rejected|cancelled|FAILED after|Segmentation" "$W/$name.out" || { [ "$rc" -ne 0 ] && ! grep -q "scene overflowed" "$W/$name.out"; }; then
		echo "  failure: reset and health (render_pb_pages back to $PB_RESTORE for the health triangle)"
		[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE"
		reset_gpu; health </dev/null || true
	fi
	clean_w
done < "$FILE"
[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE"
health </dev/null || true
echo "## end: $njob jobs"
