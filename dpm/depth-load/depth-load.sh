# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q038: tri --width 1024 --height 768 --keep-overflow with the triangle at z 0.5 and depth test
# less (blk:1 = 0x00400200). Cases, two runs of each, the GPU reset before each: (N) no depth
# buffer, pb 0x422, 0x30, 0x28, 0x24 and 0x23; (L) --depth with the buffer filled with 0.25f and
# the control 0x0017100e (the store control with bit 1, the load) on pb 0x422, 0x30, 0x28 and 0x23;
# (O) --depth with 0.25f and the load-only control 0x0011700a on pb 0x422, 0x28 and 0x23. The
# tool's own report gives the dwords of the depth buffer that left the fill and its four most
# frequent values; the triangle's pixels are counted by the tool. render_pb_pages is put back at
# the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1120}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.20) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
trap 'pb 0x422; reset_gpu' EXIT
KEEP="^(job|diff|tri|depth #|tri:)|FAILED|failed|renders ok"
case_run() { # NAME PAGES ARGS...
	name=$1 pages=$2; shift 2
	echo "== $name: pb $pages, tri --width 1024 --height 768 $*"
	reset_gpu
	pb "$pages"
	n=$(sudo -n dmesg | wc -l)
	sudo -n timeout 300 "$T" tri --width 1024 --height 768 --keep-overflow --wait-ms 20000 \
		--poke blk:1=0x00400200 "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "us$" | cut -c1-200
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -6
}
for i in 1 2; do
	for p in 0x422 0x30 0x28 0x24 0x23; do
		case_run "N-pb$p-$i" "$p"
	done
	for p in 0x422 0x30 0x28 0x23; do
		case_run "L-pb$p-$i" "$p" --depth --depth-fill 0x3e800000 --depth-ctl 0x0017100e
	done
	for p in 0x422 0x28 0x23; do
		case_run "O-pb$p-$i" "$p" --depth --depth-fill 0x3e800000 --depth-ctl 0x0011700a
	done
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
