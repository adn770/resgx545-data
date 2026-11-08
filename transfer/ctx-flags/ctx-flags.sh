# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q004: what the flag bits 1 and 4 and the priority of a transfer context's HW context do. The
# kernel poke th:W=V (a word of the HW context, applied at the submission of the next transfer
# job, a dummy too) sets the flags (word 0) or the priority (word 1) before a job of a new
# context: dummy -n 1 and a fill (64x64 at (0,0), colour 0xff112233, the destination otherwise
# the sentinel), each with the GPU reset before and the kernel log lines after. Cases: no poke;
# flags 0x2 (bit 1), 0x10 (bit 4), 0x12; priority 1, 2 and 3; a two-job dummy chain whose first
# job has the flags 0x10 and whose second clears them (th:0=0), submitted after the first; two
# runs of each. A job that does not complete in 4 s is reported by the tool as such. The tool
# cannot read the flags back. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1119}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.19) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
KEEP="^(dummy|fill|job|diff)|sgxfive-test:"
case_run() { # NAME ARGS...
	name=$1; shift
	echo "== $name: $*"
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	sudo -n timeout 120 "$T" "$@" > "$W/out" 2>&1 </dev/null
	rc=$?
	grep -E "$KEEP" "$W/out" | cut -c1-170
	echo "rc $rc"
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "kpoke|hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -8
}
for i in 1 2; do
	case_run "dummy-control-$i" dummy -n 1 --wait-ms 4000
	case_run "dummy-flags-0x2-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:0=0x2
	case_run "dummy-flags-0x10-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:0=0x10
	case_run "dummy-flags-0x12-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:0=0x12
	case_run "dummy-flags-0x10-then-clear-$i" dummy -n 2 --wait-ms 8000 --kpoke-job 1:th:0=0x10 \
		--kpoke-job 2:th:0=0
	case_run "dummy-priority-1-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:1=1
	case_run "dummy-priority-2-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:1=2
	case_run "dummy-priority-3-$i" dummy -n 1 --wait-ms 4000 --kpoke-job 1:th:1=3
	case_run "fill-control-$i" fill --width 64 --height 64 --colour 0xff112233
	case_run "fill-flags-0x2-$i" fill --width 64 --height 64 --colour 0xff112233 --kpoke-job 1:th:0=0x2
	case_run "fill-flags-0x10-$i" fill --width 64 --height 64 --colour 0xff112233 --kpoke-job 1:th:0=0x10
	case_run "fill-priority-1-$i" fill --width 64 --height 64 --colour 0xff112233 --kpoke-job 1:th:1=1
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff|^fill"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
