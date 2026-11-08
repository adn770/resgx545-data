# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q105: sequences of three kinds of step, each a 64x64 tri on a render context for 64x64 with
# debugfs alias_ctx_rw set: Z, the flagged build over a zero-filled scratch table (kernel pokes
# pb:0 = 0x1 then pb:4 = the scratch address, 16 scratch pages of 0); F, an intended fault (the
# scene's stream unmapped, tri --fault); P, the plain triangle. Sequences: Z P Z P Z P (does a Z
# fault only after a fault?), F Z P Z P, F P P Z, Z F Z F P Z. Before each step the GPU is reset
# (the reset runs); the same sequences are then repeated with no reset between the steps
# (norst). After each step the driver's log lines (fault, recovery failed, cleanup failed) and the
# BIF registers 0x0c00-0x0cff of debugfs regs are printed, and for Z the scratch dwords the job
# changed (the tool reports them). Two runs of each sequence. Root through sudo -n.
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
trap 'echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null; reset_gpu' EXIT
KEEP="^(job|diff|tri|scratch)|failed|dword|page"
SC=$(sudo -n "$T" tri --scratch 16 2>&1 | sed -n 's/^scratch: \(0x[0-9a-f]*\) .*/\1/p' | head -n 1)
[ -n "$SC" ] || { echo "no scratch address"; exit 1; }
SC=$(printf '0x%x' $(( SC + 0x100000 )))
echo "scratch address: $SC"
step() { # LABEL KIND RESET
	label=$1 kind=$2 rst=$3
	[ "$rst" = reset ] && reset_gpu
	echo Y | sudo -n tee "$D/alias_ctx_rw" >/dev/null
	n=$(sudo -n dmesg | wc -l)
	echo "== $label ($kind, $rst)"
	case $kind in
	Z) sudo -n "$T" tri --wait-ms 8000 --scratch 16 --scratch-fill 0 --scratch-at "$SC" \
		--kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC" 2>&1 </dev/null ;;
	F) sudo -n "$T" tri --wait-ms 8000 --fault 2>&1 </dev/null ;;
	P) sudo -n "$T" tri --wait-ms 8000 2>&1 </dev/null ;;
	esac | grep -E "$KEEP" | head -n 12
	echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null
	sudo -n dmesg | tail -n +$((n + 1)) > /tmp/q105.$$
	echo "driver: faults $(grep -c 'BIF fault' /tmp/q105.$$) recovery_failed $(grep -c 'recovery failed' /tmp/q105.$$) cleanup_failed $(grep -c 'cleanup failed' /tmp/q105.$$) hung $(grep -c 'hung, recovering' /tmp/q105.$$)"
	grep -E "BIF fault|recovery failed|cleanup failed" /tmp/q105.$$ | sed 's/^\[[ 0-9.]*\] //' | cut -c1-160 | head -n 4
	echo "bif: $(sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 ~ /^0x0c[0-9a-f][0-9a-f]$/ && $3 != "0x00000000" { printf "%s=%s ", $2, $3 }')"
	rm -f /tmp/q105.$$
}
seq_run() { # NAME RESET KINDS...
	name=$1 rst=$2; shift 2
	echo "#### sequence $name ($rst): $*"
	i=0
	for k in "$@"; do
		i=$((i + 1))
		step "$name-$i" "$k" "$rst"
	done
}
for run in 1 2; do
	for rst in reset norst; do
		seq_run "zpzpzp-$run" $rst Z P Z P Z P
		seq_run "fzpzp-$run" $rst F Z P Z P
		seq_run "fppz-$run" $rst F P P Z
		seq_run "zfzfpz-$run" $rst Z F Z F P Z
	done
done
echo "alias_ctx_rw at the end: $(sudo -n cat "$D/alias_ctx_rw")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
