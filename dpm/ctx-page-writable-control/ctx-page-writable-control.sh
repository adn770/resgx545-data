# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q067, the control of E446: debugfs alias_ctx_rw is set before each tri below; 64x64 renders on
# contexts for 64x64, as in ctx-page-writable.sh.
#   A  no poke, once: the page table as the render leaves it (the reference of the cmp)
#   C  the descriptor's page-table base (pb:4) pointed at 16 scratch pages the tool maps and fills
#      with 0, flag bit 0 set (--kpoke-render 1:pb:0=0x1), once: E446's case C
#   F  C without the flag poke (the flag word as the kernel leaves it), three runs
#   G  C with the flag word set to 0 (--kpoke-render 1:pb:0=0x0), three runs
# The tool's report of the scratch dwords changed is kept, and the page table's first and last
# entries from each dump. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## loaded module"; sudo -n cat /sys/module/gma500_gfx/srcversion
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
KEEP="^(job|diff|tri|scratch|layout|kpoke)|failed|dword|page"
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null; reset_gpu; rm -rf "$W"' EXIT
SC=$(sudo -n "$T" tri --scratch 16 2>&1 | sed -n 's/^scratch: \(0x[0-9a-f]*\) .*/\1/p' | head -n 1)
[ -n "$SC" ] || { echo "no scratch address"; exit 1; }
# 1 MiB above where the heap's allocator put it: clear of the colour buffer it hands out later
SC=$(printf '0x%x' $(( SC + 0x100000 )))
echo "scratch address: $SC"
case_run() { # NAME RW ARGS...
	name=$1 rw=$2; shift 2
	echo "== $name (alias_ctx_rw $rw)"
	reset_gpu
	echo "$rw" | sudo -n tee "$D/alias_ctx_rw" >/dev/null
	n=$(sudo -n dmesg | wc -l)
	mkdir -p "$W/$name"
	sudo -n "$T" tri --wait-ms 8000 --dump-render "$W/$name" "$@" 2>&1 | grep -E "$KEEP" | head -n 120
	echo "kernel: $(sudo -n dmesg | tail -n +$((n + 1)) | grep -iE 'fault|alias|kpoke|recover' | sed 's/^\[[ 0-9.]*\] //' | head -n 4 | tr '\n' ';')"
	echo "bif: int $(sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 == "0x0c04" { print $3 }') fault $(sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 == "0x0c08" { print $3 }')"
	if [ -f "$W/A1/tri.param.bin" ] && [ -f "$W/$name/tri.param.bin" ]; then
		echo "param vs A1: $(cmp -l "$W/A1/tri.param.bin" "$W/$name/tri.param.bin" 2>&1 | wc -l) bytes differ"
		cmp -l "$W/A1/tri.param.bin" "$W/$name/tri.param.bin" 2>&1 | head -n 12 | sed 's/^/  cmp (byte, A1, this, octal): /'
		echo "page table (dump offset 0x422000), entries 0-3 and 1057-1060: $(od -An -tx4 -v -j $((0x422000)) -N 16 "$W/$name/tri.param.bin" | tr -s ' ') / $(od -An -tx4 -v -j $((0x422000 + 4 * 1057)) -N 16 "$W/$name/tri.param.bin" | tr -s ' ')"
	fi
	echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null
}
case_run A1 Y
case_run C1 Y --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
	--kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC"
for i in 1 2 3; do
	case_run F$i Y --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
		--kpoke-render "1:pb:4=$SC"
done
for i in 1 2 3; do
	case_run G$i Y --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
		--kpoke-render 1:pb:0=0x0 --kpoke-render "1:pb:4=$SC"
done
echo "alias_ctx_rw at the end: $(sudo -n cat "$D/alias_ctx_rw")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
