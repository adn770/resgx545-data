# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q048, the control of E445: the long loops with no write to debugfs kregnow. After a debugfs
# reset and one second, each of the floating-point and integer long loops (12500000 iterations,
# about 0.44 s) runs three times under regtimeline (SGXFIVE_REGTIMELINE, default ~/regtimeline) over
# CR_CLKGATESTATUS (0x0008) and CR_CLKGATECTL2 (0x0004), 50 ms before the job, as in E445's busy
# runs but with nothing written; a job that does not finish within 20 s is killed. Then the
# floating-point loop once plainly (the tool alone). kregnow is only read. The probe binaries are
# those staged for usse-clockgate2. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
for f in usse-clockgate2-fmadlong__0 usse-clockgate2-intlong__0; do
	[ -f "$B/$f.bin" ] || { echo "no $B/$f.bin: stage usse-clockgate2 first"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## loaded module"; sudo -n cat /sys/module/gma500_gfx/srcversion
echo "## tool"; sha256sum "$T"
KEEP="^(job|diff|tri|probe|fill|copy|timeline|tl )|failed"
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu' EXIT
rdk() { sudo -n cat "$D/kregnow" | awk -v r="$1" '$1 == r { print $2 }'; }
rdreg() { sudo -n cat "$D/regs" | awk -v r="$1" '$1 == "reg" && $2 == r { print $3 }'; }
for loop in fmad int; do
	for i in 1 2 3; do
		reset_gpu
		echo "== $loop-long-nowrite-$i: ctl2 $(rdk 0x0004), nothing written"
		echo "-- $loop: regtimeline 0 0.05 -- $T probe $B/usse-clockgate2-${loop}long__0.bin"
		sudo -n timeout -s KILL 20 "$RT" 0 0.05 "0x0008,0x0004" -- "$T" probe "$B/usse-clockgate2-${loop}long__0.bin" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "render context"
		echo "after: ctl2 $(rdk 0x0004) status $(rdreg 0x0008)"
	done
done
reset_gpu
echo "== fmad-long-plain: the tool alone, nothing written"
sudo -n timeout -s KILL 20 "$T" probe "$B/usse-clockgate2-fmadlong__0.bin" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "render context"
echo "after: ctl2 $(rdk 0x0004) status $(rdreg 0x0008)"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
