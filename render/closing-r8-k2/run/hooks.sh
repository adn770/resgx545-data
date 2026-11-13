# SPDX-License-Identifier: MIT
# run/hooks.sh: r8-k2's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and $JW/NAME.dmesg
# are the job's output and kernel-log slice; $dbgs is the row's dbg: words (the runner's).
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W     the tool's `job:` line: ok, rejected, faulted, hung or failed
#   hash=H    `target: WxH hash H`
#   src=A     copy --print-addrs: `copy: source at A, ...`
#   fb=A      tri: `layout: fb A`
#   ro=S      isolation: PASS or FAIL of its `read-only-faults` check
#   rostat=S  isolation: the BIF_INT_STAT of the job's last kernel `BIF fault S at A` line
hook_reading() {
	local f k j h s b r t
	f=$JW/$1.out
	k=$JW/$1.dmesg
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	[ "$j" = failed ] && grep -q '^job: failed: job faulted' "$f" && j=faulted
	[ "$j" = failed ] && grep -q '^job: failed: job hung' "$f" && j=hung
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	s=$(sed -n 's/^copy: source at \(0x[0-9a-f]*\),.*/\1/p' "$f" | head -n 1)
	b=$(sed -n 's/^layout: fb \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	r=$(grep -m 1 -E '^(PASS|FAIL) read-only-faults$' "$f" | cut -d' ' -f1)
	t=$(sed -n 's/.*BIF fault \(0x[0-9a-f]*\) at 0x[0-9a-f]*.*/\1/p' "$k" | sed -n '$p')
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$s" ] && printf 'src=%s\n' "$s"
	[ -n "$b" ] && printf 'fb=%s\n' "$b"
	[ -n "$r" ] && printf 'ro=%s\n' "$r"
	[ -n "$t" ] && printf 'rostat=%s\n' "$t"
	return 0
}
# hook_check NAME: after a job that read ok (rc 0, or rc 1 with a diff line under expectdiff), a
# reason to stop the stage (rc 24), or nothing. Round 8's r8-geo lost 23 rows to a kernel that
# rejected the job while the tool still printed a diff line: here every fill, copy and tri must
# say `job: ok`, and a row whose knob sets flags must find the kernel's `vm_map A +S: PTE flags F`
# line for its address A (else the knob never reached the mapping and the row reads nothing).
hook_check() {
	local f k a v w
	f=$JW/$1.out
	k=$JW/$1.dmesg
	case " $args" in
	" fill"* | " copy"* | " tri"*)
		grep -q '^job: ok$' "$f" || { echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"; return 0; } ;;
	esac
	a=""; v=""
	for w in $dbgs; do
		case "$w" in
		vm_pte_addr=*) a=${w#vm_pte_addr=} ;;
		vm_pte_flags=*) v=${w#vm_pte_flags=} ;;
		esac
	done
	if [ -n "$a" ] && [ -n "$v" ] && [ "$v" != 0 ]; then
		grep -q "vm_map $a +0x[0-9a-f]*: PTE flags 0x[0-9a-f]*" "$k" || echo "$1: no kernel PTE line for vm_map $a (the knob reached no mapping)"
	fi
	return 0
}
