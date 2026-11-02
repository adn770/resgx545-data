# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# CR_DPM_REG_074C bit 8 (E203: a fault at 0x20006011 whatever the other bits) against
# CR_DPM_STATE_BASE1 (0x0674), which the free-list table saw follow the DPM state page of the
# last partial render's context: a partial render on a 1024x768 context (TA data state page at
# 0x20006000), then the 64x64 triangle with TA command word 167 = 0x100 (an intended fault);
# a partial render on a 4096x4096 context (state page 0x20042000), the same 64x64 job again
# (an intended fault, which should move with 0x0674); then 0x100 on a 64x64 target of a
# context for up to 4096x4096, whose TA data covers 0x20042000, run as `probe --tri` with its
# render memory dumped, and the same job without the poke. 0x0674 (debugfs regs, read-only)
# before each poked job, the kernel's log lines after each (the runner's mark: the log is never
# cleared, its line count taken before), and the non-zero dwords of the dumps' TA data pages
# at 0x40000-0x42fff (DPM control, OTPM, state). render_pb_pages is put back at the end. Root
# through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}/dpm-state-base-green__0.bin
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
[ -f "$B" ] || { echo "no $B: stage the table's probe"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
W=$(mktemp -d)
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
base1() {
	echo "regs: $(sudo -n cat "$D/regs" | awk '$1 == "reg" && ($2 == "0x062c" ||
		$2 == "0x0634" || $2 == "0x0674" || $2 == "0x0720")' | tr '\n' ' ')"
}
tri() {
	name=$1 pages=$2; shift 2
	pb "$pages"
	base1
	n=$(sudo -n dmesg | wc -l)
	echo "== $name: tri $* (pb $pages)"
	sudo -n "$T" tri --keep-going "$@" 2>&1 |
		grep -E "^job|^diff|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri"
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "fault|bif|lost|reset" | head -6
}
pages() {
	f=$W/dpm-state-base-green__0.tadata.bin
	for off in 0x40000 0x41000 0x42000; do
		echo "tadata $off: $(sudo -n od -An -tx4 -v -j $((off)) -N 4096 "$f" |
			tr -s ' ' '\n' | awk 'NF { if ($1 != "00000000")
				printf "%#05x=%s ", 4 * (NR - 1), $1 }')"
	done
	sudo -n rm -f "$W"/*.bin
}
probe() {
	name=$1; shift
	pb 0x422
	base1
	n=$(sudo -n dmesg | wc -l)
	echo "== $name: probe --tri pixel 64x64 max 4096x4096 $*"
	sudo -n "$T" probe --tri pixel --max-width 4096 --max-height 4096 --dump-render "$W" \
		"$@" "$B" 2>&1 | grep -vE "^probe [^ ]+: row "
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "fault|bif|lost|reset" | head -6
	base1
	pages
}
tri partial-1024x768 0x30 --width 1024 --height 768
tri reg074c-0x100-a 0x422 -n 1 --kpoke-render "1:ta:167=0x100"
tri partial-4096x4096 0x100 --width 4096 --height 4096
tri reg074c-0x100-b 0x422 -n 1 --kpoke-render "1:ta:167=0x100"
probe max4096-reg074c-0x100 --kpoke "ta:167=0x100"
probe max4096-control
pb 0x422
sudo -n rm -rf "$W"
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
