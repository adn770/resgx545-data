# SPDX-License-Identifier: MIT
# run/hooks.sh: r9-faults's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and $JW/NAME.dmesg
# are the job's output and kernel-log slice, $JW/dmesg.all the whole log the slice was cut from;
# $dbgs is the row's dbg: words, $args its arguments, $PREFIX and $RUN the runner's.
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W      the first `job:` line: ok, rejected, faulted, hung, overflowed or failed
#   hash=H     the first `target: WxH hash H`;  hash2=H  the second (tri -n 2)
#   src=A      copy --print-addrs: `copy: source at A, ...`
#   fb=A       tri: `layout: fb A`
#   renders=R  tri's last line: Nok (`tri: N renders ok`), KofNovfM (`K of N renders ok, M
#              overflowed`), failedK (`FAILED after K renders`)
#   dstore=N   tri --depth-store: the changed dwords of `depth store #1`
#   ro=S       isolation: PASS or FAIL of its `read-only-faults` check
#   rostat=S   the BIF_INT_STAT of the job's last kernel `BIF fault S at A` line
#   fstat=S fpage=P   the same line's status and page (A with its low 12 bits cleared)
hook_reading() {
	local f k j h h2 s b r t a n d
	f=$JW/$1.out
	k=$JW/$1.dmesg
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	[ "$j" = failed ] && grep -m 1 '^job:' "$f" | grep -q '^job: failed: job faulted' && j=faulted
	[ "$j" = failed ] && grep -m 1 '^job:' "$f" | grep -q '^job: failed: job hung' && j=hung
	[ "$j" = failed ] && grep -m 1 '^job:' "$f" | grep -q '^job: failed: scene overflowed the parameter buffer, context kept' && j=overflowed
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | sed -n 1p)
	h2=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | sed -n 2p)
	s=$(sed -n 's/^copy: source at \(0x[0-9a-f]*\),.*/\1/p' "$f" | head -n 1)
	b=$(sed -n 's/^layout: fb \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	n=$(sed -n -e 's/^tri: \([0-9]*\) renders ok$/\1ok/p' \
		-e 's/^tri: \([0-9]*\) of \([0-9]*\) renders ok, \([0-9]*\) overflowed$/\1of\2ovf\3/p' \
		-e 's/^tri: FAILED after \([0-9]*\) renders*$/failed\1/p' "$f" | sed -n '$p')
	d=$(sed -n 's/^depth store #1: [0-9]* dwords, \([0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	r=$(grep -m 1 -E '^(PASS|FAIL) read-only-faults$' "$f" | cut -d' ' -f1)
	t=$(sed -n 's/.*BIF fault \(0x[0-9a-f]*\) at 0x[0-9a-f]*.*/\1/p' "$k" | sed -n '$p')
	a=$(sed -n 's/.*BIF fault 0x[0-9a-f]* at 0x\([0-9a-f]*\).*/\1/p' "$k" | sed -n '$p')
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$h2" ] && printf 'hash2=%s\n' "$h2"
	[ -n "$s" ] && printf 'src=%s\n' "$s"
	[ -n "$b" ] && printf 'fb=%s\n' "$b"
	[ -n "$n" ] && printf 'renders=%s\n' "$n"
	[ -n "$d" ] && printf 'dstore=%s\n' "$d"
	[ -n "$r" ] && printf 'ro=%s\n' "$r"
	[ -n "$t" ] && printf 'rostat=%s\nfstat=%s\n' "$t" "$t"
	[ -n "$a" ] && printf 'fpage=0x%08x\n' $(( 0x$a & ~0xfff ))
	return 0
}
# hook_check NAME: after a job that read ok (rc 0, or rc 1 with a diff line under expectdiff), a
# reason to stop the stage (rc 24), or nothing.
# 1. Every fill, copy and tri must print at least one `job:` line and every one `job: ok` or, for
#    a scene that overflows by design (bif's --keep-overflow rows), `job: failed: scene overflowed
#    the parameter buffer, context kept` (r8-geo lost 23 rows to `job: rejected` with a diff line).
# 2. A row whose knob sets PTE flags must find the kernel's `vm_map A +S: PTE flags F` line for
#    its address A (else the knob reached no mapping and the row reads nothing).
# 3. Two `SGX recovery failed: -110` lines in the kernel log since this stage began (the plan's
#    stop on two -110 in a row, counted from the stage's `row begin` marker): the recoveries are
#    timing out. A -110 whose next health draw fails stops the stage before this (strict health).
hook_check() {
	local f k a v w bad n
	f=$JW/$1.out
	k=$JW/$1.dmesg
	case " $args" in
	" fill"* | " copy"* | " tri"*)
		grep -q '^job:' "$f" || { echo "$1 read ok without a job line"; return 0; }
		bad=$(grep '^job:' "$f" | grep -v -e '^job: ok$' -e '^job: failed: scene overflowed the parameter buffer, context kept' | head -n 1)
		[ -z "$bad" ] || { echo "$1 read ok without job: ok ($bad)"; return 0; } ;;
	esac
	a=""; v=""
	for w in $dbgs; do
		case "$w" in
		vm_pte_addr=*) a=${w#vm_pte_addr=} ;;
		vm_pte_flags=*) v=${w#vm_pte_flags=} ;;
		esac
	done
	if [ -n "$a" ] && [ -n "$v" ] && [ "$v" != 0 ]; then
		grep -q "vm_map $a +0x[0-9a-f]*: PTE flags 0x[0-9a-f]*" "$k" || { echo "$1: no kernel PTE line for vm_map $a (the knob reached no mapping)"; return 0; }
	fi
	n=$(awk -v m="resgx545 $PREFIX row begin $RUN" 'index($0, m) { c = 0; f = 1; next } f && /SGX recovery failed: -110/ { c++ } END { print c + 0 }' "$JW/dmesg.all")
	[ "$n" -ge 2 ] && echo "$n 'SGX recovery failed: -110' lines since stage $STAGE began (the plan's stop on two -110 in a row)"
	return 0
}
