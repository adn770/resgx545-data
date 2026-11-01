# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Hand-run experiments: sgxfive-test (SGXFIVE_TEST, default ~/sgxfive-test) and regtimeline
# (SGXFIVE_REGTIMELINE, default ~/regtimeline) run each case; every output is kept and nothing
# is judged here. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }

own_pb() (
# Render-context flag bit 5: the loaded-PB slots (TA3DCtl dwords 46 and 47) before a render
# context's cleanup and after its RT, RC and PB steps (render_cleanup), for contexts made with
# the bit clear and set (render_ctx_flags); then contexts with the bit set destroyed while a
# long-running one has loaded its own PB since their render.
flags() { echo "$1" | sudo -n tee "$D/render_ctx_flags" >/dev/null; }
one() {
	echo "== flags $1: $(sudo -n "$T" tri 2>&1 | grep '^diff')"
	sudo -n cat "$D/render_cleanup"
}
for f in 0 0x20 0 0x20; do
	flags $f
	one $f
done
flags 0x20
long=$(mktemp)
sudo -n "$T" tri -n 1500 >"$long" 2>&1 &
pid=$!
sleep 1
for i in 1 2 3 4; do one "0x20, beside a long-running context"; done
wait $pid
echo "== the long-running context: $(grep -c '^diff: 0 of' "$long") of 1500 renders exact"
sudo -n cat "$D/render_cleanup"
rm -f "$long"
flags 0
)
echo "#### own-pb"
own_pb
