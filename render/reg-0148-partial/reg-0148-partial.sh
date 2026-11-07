# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q043: render details dword 9 (rd:9, CR_REG_0148) at 0 and 1 in a render that overflows the
# parameter buffer into partial renders: the triangle at 1024x768 with 0x24 and 0x30 pages
# (debugfs render_pb_pages, put back at the end), three runs each, the job's lines, its time and
# the DPM registers 0x0700-0x0740 after it. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
RUN=$(date +%s)-$$
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
LINES="^job|^diff|^reg |^target|#1: [0-9]+ us|^tri [0-9x]+ #[0-9]+: [0-9]+ us|^tri:|failed|FAILED|^scratch"
one() { # NAME ARGS...: one tool run, the lines of its result and its exit status
	name=$1; shift
	mark "$name"
	echo "== $name: tri $*"
	out=$(sudo -n timeout 90 "$T" tri "$@" 2>&1 </dev/null); rc=$?
	echo "$out" | grep -E "$LINES"
	echo "rc $rc"
}
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
# run NAME POKES... : the kernel poke words armed, the job with a 16-page scratch buffer (every
# dword 0.25f before the render) and depth test less, its lines, then the poke cleared
run() {
	name=$1; shift
	kp "$@"
	one "$name" --scratch 16 --poke blk:1=0x00400200
	kp
}
trap 'kp' EXIT
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
trap 'kp; pb 0x422' EXIT
G="--width 1024 --height 768 --max-width 1024 --max-height 768"
for r in 1 2 3; do
	for pages in 0x422 0x24 0x30; do
		for v in 0 1; do
			pb $pages
			kp "rd:9=$v"
			one "partial-pb$pages-rd9-$v-r$r" $G --regs 0x0700-0x0740
			kp
		done
	done
done
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "## end"
