# SPDX-License-Identifier: MIT
# run/hooks.sh: r30-pde's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and .dmesg are the
# job's output and kernel-log slice, $W its work directory (the tool's --large-copy "$W" wrote
# $W/vm_large.txt there, the linux fork's debugfs vm_large after the job); $STAGE, $args, $knobs
# and $class are the runner's, $STAGED the staged tree (gen/allowed.tsv, from gen/make.py).
# score/score.py's reading() is the twin of these keys (tests/test_score.py holds them equal).
#
# hook_reading NAME: a row's reading, `key=value` words:
#   job=W       the first `job:` line's word (ok, failed, rejected)
#   diff=N      the first `diff: N of` line's N (the tool's reference check)
#   large=L     vm_large.txt: `none`, or cCODE.lLAYOUT.oORDER from its addr and region lines
#   table=T     vm_large.txt: `intact` or `CHANGED` (the table page against what was written)
#   changed=C   vm_large.txt: the changed 4 KiB of the region, S:P (slab S page P), sorted, comma
#               separated, or `none`
#   tags=G      copy: per `tags:` line (one a 4 KiB of the source, in VA order) S:P when its first
#               dword is the tag of slab S page P dword 0 and every dword follows it, else x
rd_large() {
	local f=$W/vm_large.txt c l o
	[ -s "$f" ] || return 0
	if [ "$(head -n 1 "$f")" = none ]; then printf 'large=none\n'; return 0; fi
	c=$(sed -n 's/^addr 0x[0-9a-f]* code \([0-9]*\) layout \([0-9]*\) .*/\1/p' "$f" | head -n 1)
	l=$(sed -n 's/^addr 0x[0-9a-f]* code \([0-9]*\) layout \([0-9]*\) .*/\2/p' "$f" | head -n 1)
	o=$(sed -n 's/^region 0x[0-9a-f]* +0x[0-9a-f]* order \([0-9]*\)$/\1/p' "$f" | head -n 1)
	printf 'large=c%s.l%s.o%s\n' "$c" "$l" "$o"
	awk '$1 == "table" { print "table=" $2 }' "$f" | head -n 1
	c=$(sed -n 's/^slab \([0-9]*\) page \([0-9]*\): [0-9]* changed.*/\1:\2/p' "$f" | sort -t: -k1,1n -k2,2n -u | paste -sd, -)
	printf 'changed=%s\n' "${c:-none}"
}
rd_tags() {
	awk '/^tags: va / {
		na = split($0, a, /[ (),\/]+/)
		first = ""; s = ""; p = ""; dw = ""; fo = ""; n = ""
		for (i = 1; i <= na; i++) {
			if (a[i] == "first") first = a[i + 1]
			if (a[i] == "slab") s = a[i + 1]
			if (a[i] == "page") p = a[i + 1]
			if (a[i] == "dword") dw = a[i + 1]
			if (a[i] == "follow") { fo = a[i - 2]; n = a[i - 1] }
		}
		t = (substr(first, 1, 3) == "0xa" && dw == "0" && fo == n) ? s ":" p : "x"
		out = out (out == "" ? "" : ",") t
	} END { if (out != "") print "tags=" out }' "$1"
}
hook_reading() {
	local f=$JW/$1.out v
	v=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'job=%s\n' "$v"
	v=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'diff=%s\n' "$v"
	rd_large
	rd_tags "$f"
	return 0
}
# knob_of NAME: the row's dbg:NAME=V value, or nothing
knob_of() { printf '%s\n' $knobs | sed -n "s/^dbg:$1=//p" | head -n 1; }
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   - `job: ok` and a `diff:` line (expectdiff's rc 1 is a reading only with them; E934), and the
#     tool's vm_large.txt;
#   - knobs off: vm_large reads `none`;
#   - vm_pde_addr set: the kernel's `PDE size code C layout L` vm_map line, vm_large naming the
#     slot, code and layout, the table page intact; a copy changed no page of the region; a fill
#     changed at least one, and only pages some reading of the fork's safety case reaches over its
#     window (gen/allowed.tsv): else the GPU wrote where no reading puts it, and the stage stops
#     (on_stop end: the session ends).
hook_check() {
	local f=$JW/$1.out lg=$W/vm_large.txt c l bad
	grep -q '^job: ok' "$f" || { echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"; return 0; }
	grep -q '^diff: [0-9]* of ' "$f" || { echo "$1 read ok without its diff line"; return 0; }
	[ -s "$lg" ] || { echo "$1 kept no vm_large.txt"; return 0; }
	c=$(knob_of vm_pde_size); l=$(knob_of vm_pde_layout)
	if [ -z "$(knob_of vm_pde_addr)" ]; then
		[ "$(head -n 1 "$lg")" = none ] || echo "$1: vm_large is not none with the knobs off ($(head -n 1 "$lg"))"
		return 0
	fi
	grep -q "PDE size code $c layout $l (debugfs vm_pde_size)" "$JW/$1.dmesg" || { echo "$1: no kernel vm_map line for PDE size code $c layout $l"; return 0; }
	head -n 1 "$lg" | grep -q "^addr 0x60000000 code $c layout $l " || { echo "$1: vm_large is not code $c layout $l at 0x60000000 ($(head -n 1 "$lg"))"; return 0; }
	grep -q '^table intact ' "$lg" || { echo "$1: the table page changed ($(grep -m 1 '^table ' "$lg"))"; return 0; }
	case "$args" in
	copy*)
		grep -q '^pages [0-9]* intact 0 changed$' "$lg" || echo "$1: a copy changed the region ($(grep -m 1 '^pages ' "$lg"))" ;;
	fill*)
		grep -q '^slab [0-9]* page [0-9]*: [0-9]* changed' "$lg" || { echo "$1: a fill that ended ok changed no page of the region"; return 0; }
		bad=$(sed -n 's/^slab \([0-9]*\) page \([0-9]*\): [0-9]* changed.*/\1:\2/p' "$lg" |
			awk -v a=",$(awk -F'\t' -v n="$1" '$1 == n { print $2 }' "$STAGED/gen/allowed.tsv")," 'index(a, "," $0 ",") == 0' | head -n 1)
		[ -z "$bad" ] || echo "$1: page $bad changed, outside every reading's window (gen/allowed.tsv)" ;;
	esac
	return 0
}
# hook_fault NAME: after an expectfault row's fault or hang (its reset and strict health done), a
# reason to stop the stage (rc 24; every flagged stage declares on_stop = end), or nothing:
#   - any `SGX recovery failed` line in the row's kernel slice;
#   - f1, f2, f45 plan faults only: a fault with the kernel's `BIF fault S at A` line;
#   - f67 (the unnamed codes) a fault with that line, or a hang with `job N hung, recovering`.
hook_fault() {
	local k=$JW/$1.dmesg
	grep -q 'SGX recovery failed' "$k" && { echo "$1: SGX recovery failed ($(grep -m 1 'SGX recovery failed' "$k" | sed 's/.*SGX recovery failed/SGX recovery failed/'))"; return 0; }
	case "$STAGE:$class" in
	f1:fault | f2:fault | f45:fault | f67:fault)
		grep -Eq 'BIF fault (0x)?[0-9a-f]+ at (0x)?[0-9a-f]+' "$k" || echo "$1 faulted without a kernel BIF fault line" ;;
	f67:hang)
		grep -Eq 'job [0-9]+ hung, recovering' "$k" || echo "$1 hung without the kernel's hung line" ;;
	*)
		echo "$1 ended $class in stage $STAGE, which plans no such end" ;;
	esac
	return 0
}
