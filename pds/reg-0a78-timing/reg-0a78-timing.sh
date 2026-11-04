# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# CR_PDS_REG_0A78's effect on a render's time (Q024), trimmed: six values (0x2c the firmware's,
# 0x01 and 0x20 the two slower ones of E141, 0x00, 0x08, 0x3f), five times each in a fixed
# shuffled order; each a 256x256 triangle rendered six times, every render's own time kept and
# the mean of the last five printed; 0x2c restored after each. Root through sudo -n (debugfs kreg).
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
put() { printf '%s\n' "$1" | sudo -n tee "$D/kreg" >/dev/null; }
t() { sudo -n "$T" tri --width 256 --height 256 -n 6 2>&1 |
	awk '/ us$/ {n++; u[n]=$(NF-1); if (n>1) s+=$(NF-1)} /renders ok/ {ok=1}
		END {printf "%6d us avg of 5 %s |", s/5, ok ? "ok" : "FAIL"; for (i=1;i<=n;i++) printf " %s", u[i]}'; }
k=0
for v in 0x00 0x01 0x2c 0x20 0x01 0x00 0x00 0x3f 0x2c 0x20 0x00 0x2c 0x3f 0x3f 0x08 0x08 0x08 0x08 0x01 0x2c 0x01 0x08 0x2c 0x20 0x01 0x00 0x3f 0x20 0x20 0x3f; do
	k=$((k+1)); put 0x0a78=$v; echo "case $k 0x0a78=$v: $(t)"; put 0x0a78=0x0000002c
done
echo "kreg after: $(sudo -n cat "$D/kreg" | grep -i 0x0a78)"
