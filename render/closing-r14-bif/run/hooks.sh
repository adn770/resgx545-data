# SPDX-License-Identifier: MIT
# run/hooks.sh: r14-bif's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory, $args the row's arguments, $dbgs its dbg: words.
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W        the first `job:` line: ok, rejected or failed
#   renders=R    tri's last line: Nok (`tri: N renders ok`) or KofN (`tri: K of N renders ok`)
#   dep1, dep2   `depth #N: D dwords, C changed, ...`: C (render N's depth buffer against what the
#                host wrote last: its fill, or a --refill's value)
#   dst1, dst2   `depth store #N: D dwords, C changed, ...`: C
hook_reading() {
	local f j n k v
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	n=$(sed -n -e 's/^tri: \([0-9]*\) renders ok$/\1ok/p' \
		-e 's/^tri: \([0-9]*\) of \([0-9]*\) renders ok$/\1of\2/p' "$f" | sed -n '$p')
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ -n "$n" ] && printf 'renders=%s\n' "$n"
	for k in 1 2; do
		v=$(sed -n "s/^depth #$k: [0-9]* dwords, \([0-9]*\) changed.*/\1/p" "$f" | head -n 1)
		[ -n "$v" ] && printf 'dep%s=%s\n' "$k" "$v"
		v=$(sed -n "s/^depth store #$k: [0-9]* dwords, \([0-9]*\) changed.*/\1/p" "$f" | head -n 1)
		[ -n "$v" ] && printf 'dst%s=%s\n' "$k" "$v"
	done
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# 1. Every `job:` line must be `job: ok` (E934: a rejected job still prints a diff line).
# 2. Every --depth row must have its buffers where gen/rf.py places them (depth 0x3e001000, base
#    0x3e000000, store 0x3e015000, 20 pages): the knob's address and the kept dumps assume them.
# 3. A row whose knob sets PTE flags must find the kernel's `vm_map 0x3e001000 +S: PTE flags F`
#    line (else the knob reached no mapping); a row without the knob must not.
# 4. A --refill row must print its `refill: render 2 buf depth value 0x3f400000` line.
hook_check() {
	local f k a v w bad
	f=$JW/$1.out
	k=$JW/$1.dmesg
	grep -q '^job:' "$f" || { echo "$1 read ok without a job line"; return 0; }
	bad=$(grep '^job:' "$f" | grep -v '^job: ok$' | head -n 1)
	[ -z "$bad" ] || { echo "$1 read ok without job: ok ($bad)"; return 0; }
	case " $args " in
	*" --depth "*)
		grep -q '^depth: 0x3e001000 20 pages, .*base 0x3e000000,' "$f" ||
			echo "$1: the depth buffer is not at 0x3e001000 with base 0x3e000000 ($(grep -m 1 '^depth: ' "$f"))"
		grep -q '^depth store: 0x3e015000 20 pages' "$f" ||
			echo "$1: the depth store is not at 0x3e015000 ($(grep -m 1 '^depth store: ' "$f"))" ;;
	esac
	case " $args " in
	*" --refill "*)
		grep -q '^refill: render 2 buf depth value 0x3f400000$' "$f" ||
			echo "$1: no refill line before render 2" ;;
	esac
	a=""; v=""
	for w in $dbgs; do
		case "$w" in
		vm_pte_addr=*) a=${w#vm_pte_addr=} ;;
		vm_pte_flags=*) v=${w#vm_pte_flags=} ;;
		esac
	done
	if [ -n "$a" ] && [ -n "$v" ] && [ "$v" != 0 ]; then
		grep -q "vm_map $a +0x[0-9a-f]*: PTE flags 0x[0-9a-f]*" "$k" ||
			echo "$1: no kernel PTE line for vm_map $a (the knob reached no mapping)"
	elif grep -q 'vm_map 0x[0-9a-f]* +0x[0-9a-f]*: PTE flags' "$k"; then
		echo "$1: a kernel PTE line on a row without the knob ($(grep -m 1 -o 'vm_map .*' "$k"))"
	fi
	return 0
}
# hook_fault NAME: after an expected fault or hang row; no row of this session expects one
hook_fault() { return 0; }
