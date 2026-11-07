# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q048: CR_CLKGATECTL2 is written through debugfs kregnow (the linux fork's commit 36), after a
# debugfs reset that puts it back as the boot leaves it (0x00aaaaaa, every field 2): each of its
# two-bit fields at 0, 1 and 3 in turn, the others as they were, and the unwritten value: the two
# MADD fields first, then the fields at bits 15:14, 17:16, 19:18, 23:22 and 1:0. (An earlier run,
# whose fields went to the one at bits 3:2, froze the laptop until its watchdog reset it, and lost
# its output; each setting is now noted in ~/clockgate2.progress, and synced, before it is written.)
# Per value: the registers read idle, then each of four jobs under regtimeline (SGXFIVE_REGTIMELINE,
# default ~/regtimeline) over CR_CLKGATESTATUS (0x0008) and CR_CLKGATECTL2 (0x0004), 50 ms before
# the job: a fill running the table's floating-point loop (1e7 instructions), the integer loop, a
# texture copy and a plain fill, staged as $SGXFIVE_PROBE_BINS. Each job's lines are kept
# (a job that does not finish within 20 s is killed and the GPU reset). Then both MADD fields at 0, 1
# and 3 written while each loop runs. MADD0 is the field at bits
# 13:12 and MADD1 the one at 21:20. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
for f in usse-clockgate2-fmad__0 usse-clockgate2-int__0 usse-clockgate2-fmadlong__0 usse-clockgate2-intlong__0; do
	[ -f "$B/$f.bin" ] || { echo "no $B/$f.bin: stage the table"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
KEEP="^(job|diff|tri|probe|fill|copy|timeline|tl )|failed"
BASE=0x00aaaaaa
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu' EXIT
rdk() { sudo -n cat "$D/kregnow" | awk -v r="$1" '$1 == r { print $2 }'; }
rdreg() { sudo -n cat "$D/regs" | awk -v r="$1" '$1 == "reg" && $2 == r { print $3 }'; }
job() { # NAME ARGS...
	name=$1; shift
	echo "-- $name: regtimeline 0 0.05 -- $*"
	sudo -n timeout -s KILL 20 "$RT" 0 0.05 "0x0008,0x0004" -- "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "render context"
}
setting() { # LABEL VALUE
	label=$1 value=$2
	reset_gpu
	echo "$(date +%T) $label $value" >> "$HOME/clockgate2.progress"; sync
	echo "== $label: kregnow 0x0004=$value"
	echo "0x0004=$value" | sudo -n tee "$D/kregnow" >/dev/null || { echo "write refused"; return; }
	sleep 0.5
	echo "idle: ctl2 $(rdk 0x0004) status $(rdreg 0x0008) $(rdreg 0x0008) $(rdreg 0x0008)"
	job fmad "$T" probe "$B/usse-clockgate2-fmad__0.bin"
	job int "$T" probe "$B/usse-clockgate2-int__0.bin"
	job copy "$T" copy
	job fill "$T" fill
	echo "after: ctl2 $(rdk 0x0004) status $(rdreg 0x0008)"
}
setting base $BASE
for f in 6 10 7 8 9 11 0; do
	for v in 0 1 3; do
		val=$(printf '0x%08x' $(( (0x00aaaaaa & ~(3 << (2 * f))) | (v << (2 * f)) )))
		setting "field$f-bits$((2 * f + 1)):$((2 * f))-value$v" "$val"
	done
done
# busy: both MADD fields written 0.3 s after the start of the tool, while the long loop (about 0.44 s) runs
for v in 0 1 3; do
	val=$(printf '0x%08x' $(( (0x00aaaaaa & ~(3 << 12) & ~(3 << 20)) | (v << 12) | (v << 20) )))
	for loop in fmad int; do
		reset_gpu
		echo "$(date +%T) busy-$loop-both-madd-value$v $val" >> "$HOME/clockgate2.progress"; sync
		echo "== busy-$loop-both-madd-value$v: kregnow 0x0004=$val 0.3 s in"
		( sleep 0.3; echo "0x0004=$val" | sudo -n tee "$D/kregnow" >/dev/null ) &
		job "$loop" "$T" probe "$B/usse-clockgate2-${loop}long__0.bin"
		wait
		echo "after: ctl2 $(rdk 0x0004) status $(rdreg 0x0008)"
	done
done
echo "## health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
