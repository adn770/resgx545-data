# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q064: an RT data whose state has bit 8 set. The kernel's debugfs kpoke rtds:19 is dword 13 of the
# RT data (the RT data set's first six words are the set's own), so rtds:19^=0x100 sets the state's
# bit 8 at the first kick, where the firmware reads it into CR_TE_PSG (bit 21). The triangle at
# 64x64 and 1024x768, one and two renders (-n), each of: the control, the TA command's te_psg
# (ta:147) at 0x01600000, the state's bit 8, and both, three runs each; every case with the
# regtimeline of CR_TE_PSG (0x0218) and CR_DPM_STATE_CONTEXT_ID (0x0630), the image's hash and
# difference, and the render memory's (the kernel's render_param and render_tadata copied by
# --dump-render) hashes and the bytes that differ from the control's dump of the same size and
# render count. Each case marks the kernel log ("resgx545 case"). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
RUN=$(date +%s)-$$
W=/tmp/psg-state-$RUN; mkdir -p "$W"
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
LINES="^job|^diff|^target|^tri [0-9x]+ #[0-9]+: [0-9]+ us|^tri:|failed|FAILED|^tl |^timeline"
one() { # NAME ARGS...: regtimeline around one tool run, its lines, the dump's hashes
	name=$1; shift
	mkdir -p "$W/$name"
	mark "$name"
	echo "== $name: tri $*"
	sudo -n timeout 120 "$RT" 0 0.05 0x0218,0x0630 -- "$T" tri --dump-render "$W/$name" "$@" \
		2>&1 </dev/null | grep -E "$LINES"
	for f in tri.param.bin tri.tadata.bin; do
		[ -f "$W/$name/$f" ] && echo "dump $f $(sha256sum < "$W/$name/$f" | cut -c1-16) $(wc -c < "$W/$name/$f") bytes"
	done
}
differ() { # NAME CONTROL: bytes of NAME's dumps that differ from CONTROL's
	for f in tri.param.bin tri.tadata.bin; do
		[ -f "$W/$1/$f" ] && [ -f "$W/$2/$f" ] &&
			echo "diff-vs-$2 $1 $f: $(cmp -l "$W/$1/$f" "$W/$2/$f" 2>/dev/null | wc -l) bytes"
	done
}
for geo in "64 64" "1024 768"; do
	set -- $geo; w=$1; h=$2
	G="--width $w --height $h --max-width $w --max-height $h"
	for n in 1 2; do
		for r in 1 2 3; do
			p="${w}x${h}-n$n-r$r"
			one "ctl-$p" $G -n $n
			one "ta147-$p" $G -n $n --kpoke-render "1:ta:147=0x01600000"
			one "state8-$p" $G -n $n --kpoke-render "1:rtds:19^=0x100"
			one "both-$p" $G -n $n --kpoke-render "1:ta:147=0x01600000" --kpoke-render "1:rtds:19^=0x100"
			for c in ta147 state8 both; do differ "$c-$p" "ctl-$p"; done
		done
	done
done
echo "## end"
rm -rf "$W"
