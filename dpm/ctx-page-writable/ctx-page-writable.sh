# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q067: debugfs alias_ctx_rw is set before each tri below (it clears itself when the render context
# is created); 64x64 renders on contexts for 64x64.
#   A  no poke, three runs: the image and the context's page as the EDM leaves it
#   B  PB flags bit 0 (--kpoke-render 1:pb:0=0x1) with the kernel's table, three runs
#   C  B with the descriptor's page-table base (pb:4) pointed at 16 scratch pages the tool maps and
#      fills with 0 at a fixed address (--scratch 16 --scratch-at), three runs: the dwords the builder
#      changed, page by page, are the tool's report
#   D  C with the table base at +0x1000, +0x2000 into the scratch (so that the store offset's
#      scale shows against the first word)
#   E  no alias_ctx_rw, B and C once each (the faults of E362 again)
# The page table's first and last entries are printed from each dump. Each case's render_param dump (the kernel's PB pages, page table and scratch block) is compared
# with case A's by cmp -l (the count of bytes that differ). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
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
for i in 1 2 3; do case_run A$i Y; done
for i in 1 2 3; do case_run B$i Y --kpoke-render 1:pb:0=0x1; done
for i in 1 2 3; do
	case_run C$i Y --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
		--kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC"
done
for off in 0x1000 0x2000; do
	a=$(printf '0x%x' $(( SC + off )))
	case_run "D$off" Y --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
		--kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$a"
done
case_run E-B N --kpoke-render 1:pb:0=0x1
case_run E-C N --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
	--kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
