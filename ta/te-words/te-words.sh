# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q035, Q085, Q064: the tiling words, the closed driver's two other 3D register values and the TE
# state register around two-render jobs. A) the triangle at 256x256 and 1024x768 with the
# TA command's te_mtile1 (ta:143) and te_mtile2 (ta:144) as the control reads them back (--regs
# 0x0208-0x020c) and each bit flipped, one job each; B) at 64x64, 256x256 and 1024x768 the job
# with CR_ISP_CTL (rd:3) 0xf0000, 0x04c4 (rd:18) 0x2046400 and both, three runs each against
# the control, the job's time kept; C) regtimeline over 0x0630 and 0x0218 while two and three
# renders run at 1024x768, and with the command's te_psg bit 21 (ta:147) set. Each case marks the
# kernel log ("resgx545 case"). Root through sudo -n.
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
echo "## A tiling words"
for geo in "256 256" "1024 768"; do
	set -- $geo; w=$1; h=$2
	G="--width $w --height $h --max-width $w --max-height $h"
	ctl=$(sudo -n "$T" tri $G --regs 0x0208-0x020c 2>&1 </dev/null)
	echo "== ctl-${w}x${h}"; echo "$ctl" | grep -E "$LINES"
	m1=$(echo "$ctl" | awk '$1 == "reg" && $2 == "0x0208" {print $3}')
	m2=$(echo "$ctl" | awk '$1 == "reg" && $2 == "0x020c" {print $3}')
	one "mtile-ctl-${w}x${h}" $G
	for b in $(seq 0 31); do
		one "mtile1-b$b-${w}x${h}" $G --kpoke-render "1:ta:143=$(printf 0x%08x $((m1 ^ (1 << b))))"
	done
	for b in $(seq 0 31); do
		one "mtile2-b$b-${w}x${h}" $G --kpoke-render "1:ta:144=$(printf 0x%08x $((m2 ^ (1 << b))))"
	done
done
echo "## B closed values"
for geo in "64 64" "256 256" "1024 768"; do
	set -- $geo; w=$1; h=$2
	G="--width $w --height $h --max-width $w --max-height $h"
	for r in 1 2 3; do
		one "ctl-${w}x${h}-r$r" $G
		one "isp0f0000-${w}x${h}-r$r" $G --kpoke-render "1:rd:3=0xf0000"
		one "r04c4-${w}x${h}-r$r" $G --kpoke-render "1:rd:18=0x2046400"
		one "both-${w}x${h}-r$r" $G --kpoke-render "1:rd:3=0xf0000" --kpoke-render "1:rd:18=0x2046400"
	done
done
echo "## C slot register"
G="--width 1024 --height 768 --max-width 1024 --max-height 768"
tl() { # NAME ARGS...
	name=$1; shift
	mark "$name"; echo "== $name: regtimeline tri $*"
	sudo -n timeout 120 "$RT" 0 0 0x0630,0x0218 -- "$T" tri $G "$@" 2>&1 </dev/null |
		grep -E "^job|^diff|^timeline|^tl |^tri:"
}
for r in 1 2 3; do
	tl "slot-n1-r$r" -n 1
	tl "slot-n2-r$r" -n 2
	tl "slot-n3-r$r" -n 3
	tl "slot-n2-geometry-r$r" -n 2 --geometry 1
done
for r in 1 2 3; do
	tl "psg21-n2-r$r" -n 2 --kpoke-render "1:ta:147=0x01600000"
done
echo "## end"
