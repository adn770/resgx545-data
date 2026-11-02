# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q038, Q036, Q045: the DPM registers 0x0600-0x0750 sampled by regtimeline (read-only, a line
# at every change) around the triangle at 64x64 and 1024x768 with the whole PB, at 1024x768
# with 0x30 pages (one partial render) and at 4096x4096 with 0x100 and 0x23 pages (one and ten
# partial renders): the free-list status words as the TA takes pages and the 3D frees them,
# and per partial render CR_DPM_ABORT_STATUS_MTILE, CR_DPM_PARTIAL_RENDER and the context
# slot. Last, the 1024x768 triangle with 0x30 pages once more, its pixels read, printing those
# of the bottom tile row (y 752-767) that are neither the triangle's, the background's nor the
# sentinel's colour, with their position (the partial-render table found 14 such pixels in
# one tile of that row in every overflowing job). render_pb_pages is put back at the end.
# Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
R=$HOME/regtimeline
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
[ -x "$R" ] || { echo "no $R: build tools/campaign's regtimeline for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
one() {
	name=$1 pages=$2 total=$3; shift 3
	pb "$pages"
	echo "== $name: regtimeline $total 0.2 0x0600-0x0750 -- tri $* (pb $pages)"
	sudo -n "$R" "$total" 0.2 0x0600-0x0750 -- "$T" tri "$@" 2>&1 |
		grep -vE "^tri: render context|^layout:"
}
one full-64x64 0x422 3.0
one full-1024x768 0x422 3.0 --width 1024 --height 768
one pb30-1024x768 0x30 3.0 --width 1024 --height 768
one pb100-4096x4096 0x100 6.0 --width 4096 --height 4096
one pb23-4096x4096 0x23 6.0 --width 4096 --height 4096
pb 0x30
echo "== other-pixels-1024x768: tri --pixels (pb 0x30), rows 752-767"
sudo -n "$T" tri --width 1024 --height 768 --pixels 2>&1 |
	awk '/^row (75[2-9]|76[0-7]):/ { y = $2; sub(":", "", y)
		for (i = 3; i <= NF; i++) if ($i != "0xff00ff00" && $i != "0xff203040" &&
			$i != "0xdeadbeef") printf "other (%d, %s) %s\n", i - 3, y, $i }
		/^job|^diff/'
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
