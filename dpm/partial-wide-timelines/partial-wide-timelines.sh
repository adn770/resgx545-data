# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q036: the DPM registers 0x0700-0x0750 (regtimeline, read-only, a line at every change) around the
# renders of the triangle and copies of it (probe --tri pixel --vertices N) at 4096x4096 with the
# whole parameter buffer (3, 900 and 1500 vertices, the last two overflow it) and with 0x100 pages
# (300 vertices, which overflow and recover), three runs of each: whether STATUS2's high halves
# (0x0710, 0x071c) and 0x0748's bit 2 change while a scene that fills the global list runs.
# render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
R=$HOME/regtimeline
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}/dpm-partial-wide-timelines-green__0.bin
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
[ -x "$R" ] || { echo "no $R: build tools/campaign's regtimeline for the laptop first"; exit 1; }
[ -f "$B" ] || { echo "no $B: stage the table's probe"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
one() {
	name=$1 pages=$2 n=$3
	pb "$pages"
	echo "== $name: regtimeline 10.0 0.2 0x0700-0x0750 -- probe --tri pixel 4096x4096 vertices $n (pb $pages)"
	sudo -n "$R" 10.0 0.2 0x0700-0x0750 -- "$T" probe --tri pixel --width 4096 --height 4096 \
		--vertices "$n" "$B" 2>&1 | grep -vE "^programs|: scratch at|^probe [^ ]+: tri "
}
for run in 1 2 3; do
	one "pb422-v3-r$run" 0x422 3
	one "pb422-v900-r$run" 0x422 900
	one "pb422-v1500-r$run" 0x422 1500
	one "pb100-v300-r$run" 0x100 300
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
