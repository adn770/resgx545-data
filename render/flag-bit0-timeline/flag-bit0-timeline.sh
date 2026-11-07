# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q065: the triangle at 64x64 with the render flags' bit 0 flipped (--kpoke-render 1:ta:7^=0x1, as
# E361) with debugfs hold_recovery set, under regtimeline (SGXFIVE_REGTIMELINE, default ~/regtimeline)
# for 3 seconds from 50 ms before the kick over the TE and VDM registers (0x0200-0x0240), the ISP
# (0x0400-0x04fc), the DPM (0x0630, 0x0640-0x0660, 0x0700-0x0760) and the event registers (0x0118,
# 0x012c); the same for the unpoked job (not held); each case three times, a reset after each held
# job. The timeline lines are the changes. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
R="0x0118,0x012c,0x0200-0x0240,0x0400-0x04fc,0x0630,0x0640-0x0660,0x0700-0x0760"
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; }
tl() { # NAME ARGS...
	name=$1; shift
	echo "== $name: regtimeline 0 0.05 -- tri $*"
	sudo -n timeout 60 "$RT" 3 0.05 "$R" -- "$T" tri "$@" 2>&1 </dev/null | grep -E "^job|^diff|^timeline|^tl |^tri:|failed"
}
for r in 1 2 3; do
	hold 0
	tl "control-r$r" --wait-ms 4000
	hold 1
	tl "flag0-held-r$r" --wait-ms 2500 --kpoke-render "1:ta:7^=0x1"
	echo "reset: $(echo 1 | sudo -n tee "$D/reset" >/dev/null; echo $?)"
	hold 0
	sudo -n "$T" tri 2>&1 | grep -E "^diff|renders ok"
done
echo "## end"
