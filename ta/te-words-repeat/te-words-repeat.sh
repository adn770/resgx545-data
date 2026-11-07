# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q035 again: the flips of te-words.sh that changed the image or faulted, and some that did not,
# three runs each with the registers read back after the job (--regs 0x0208-0x020c), and the
# 256x256 target with the words the rule gives a 512x512 and a 1024x768 target. Each case marks
# the kernel log ("resgx545 case"). Root through sudo -n.
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
G256="--width 256 --height 256 --max-width 256 --max-height 256"
G1024="--width 1024 --height 768 --max-width 1024 --max-height 768"
ctlw() { # GEOMETRY...: the control's words 0x0208 and 0x020c
	sudo -n "$T" tri "$@" --regs 0x0208-0x020c 2>&1 </dev/null | awk '$1 == "reg" {print $3}' | tr '\n' ' '
}
w256=$(ctlw $G256); w1024=$(ctlw $G1024)
w512=$(ctlw --width 512 --height 512 --max-width 512 --max-height 512)
set -- $w256; a256=$1; b256=$2
set -- $w1024; a1024=$1; b1024=$2
set -- $w512; a512=$1; b512=$2
echo "control words: 256x256 $w256 512x512 $w512 1024x768 $w1024"
flip() { # SIZE WORD(143|144) BIT: three runs
	size=$1; word=$2; bit=$3
	if [ "$size" = 256 ]; then G=$G256; a=$a256; b=$b256; else G=$G1024; a=$a1024; b=$b1024; fi
	[ "$word" = 143 ] && v=$a || v=$b
	nv=$(printf 0x%08x $((v ^ (1 << bit))))
	for r in 1 2 3; do
		one "flip$size-ta$word-b$bit-r$r" $G --regs 0x0208-0x020c --kpoke-render "1:ta:$word=$nv"
	done
}
for r in 1 2 3; do one "ctl256-r$r" $G256 --regs 0x0208-0x020c; one "ctl1024-r$r" $G1024 --regs 0x0208-0x020c; done
for b in 8 20 24 31 12 13 15 16; do flip 256 143 $b; done
for b in 0 12 15 16; do flip 256 144 $b; done
for b in 0 1 2 5 8 9 10; do flip 1024 143 $b; done
for b in 0 1 2 8; do flip 1024 144 $b; done
echo "## other words"
for r in 1 2 3; do
	one "w512-on-256-r$r" $G256 --regs 0x0208-0x020c --kpoke-render "1:ta:143=$a512" --kpoke-render "1:ta:144=$b512"
	one "w1024-on-256-r$r" $G256 --regs 0x0208-0x020c --kpoke-render "1:ta:143=$a1024" --kpoke-render "1:ta:144=$b1024"
done
echo "## end"
