# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q008: the luma key's cuts at 119, 120 and 122. E039's sum S = 262 R + 514 G + 100 B + 512 x 33
# (the weights loaded with xfer:29 = 0x02020106 and xfer:30 = 0x00210064, T0 bit 31, xfer:17 bit
# 1), a source row of 64 pixels whose blue channel counts from B (--ramp b=B, red and green the
# row's fixed values, --ramp-base), so that pixel 0 has S = cut x 1024 + k exactly, for the even k
# from -16 to 16 (every weight is even, so odd sums cannot be made), at the low cut (low byte =
# the cut, threshold 128) and at the high cut (low byte 0, threshold byte = the cut); the later
# pixels have S 100 higher a pixel. Each case's 64 pixels read back, twice. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
CASES="
low 119 -16 69 169 0
low 119 -14 18 195 0
low 119 -12 224 90 0
low 119 -10 173 116 0
low 119 -8 122 142 0
low 119 -6 71 168 0
low 119 -4 20 194 0
low 119 -2 226 89 0
low 119 0 175 115 0
low 119 2 124 141 0
low 119 4 73 167 0
low 119 6 22 193 0
low 119 8 228 88 0
low 119 10 177 114 0
low 119 12 126 140 0
low 119 14 75 166 0
low 119 16 24 192 0
low 120 -16 171 119 0
low 120 -14 120 145 0
low 120 -12 69 171 0
low 120 -10 18 197 0
low 120 -8 224 92 0
low 120 -6 173 118 0
low 120 -4 122 144 0
low 120 -2 71 170 0
low 120 0 20 196 0
low 120 2 226 91 0
low 120 4 175 117 0
low 120 6 124 143 0
low 120 8 73 169 0
low 120 10 22 195 0
low 120 12 228 90 0
low 120 14 177 116 0
low 120 16 126 142 0
low 122 -16 118 150 0
low 122 -14 67 176 0
low 122 -12 16 202 0
low 122 -10 222 97 0
low 122 -8 171 123 0
low 122 -6 120 149 0
low 122 -4 69 175 0
low 122 -2 18 201 0
low 122 0 224 96 0
low 122 2 173 122 0
low 122 4 122 148 0
low 122 6 71 174 0
low 122 8 20 200 0
low 122 10 226 95 0
low 122 12 175 121 0
low 122 14 124 147 0
low 122 16 73 173 0
high 119 -16 69 169 0
high 119 -14 18 195 0
high 119 -12 224 90 0
high 119 -10 173 116 0
high 119 -8 122 142 0
high 119 -6 71 168 0
high 119 -4 20 194 0
high 119 -2 226 89 0
high 119 0 175 115 0
high 119 2 124 141 0
high 119 4 73 167 0
high 119 6 22 193 0
high 119 8 228 88 0
high 119 10 177 114 0
high 119 12 126 140 0
high 119 14 75 166 0
high 119 16 24 192 0
high 120 -16 171 119 0
high 120 -14 120 145 0
high 120 -12 69 171 0
high 120 -10 18 197 0
high 120 -8 224 92 0
high 120 -6 173 118 0
high 120 -4 122 144 0
high 120 -2 71 170 0
high 120 0 20 196 0
high 120 2 226 91 0
high 120 4 175 117 0
high 120 6 124 143 0
high 120 8 73 169 0
high 120 10 22 195 0
high 120 12 228 90 0
high 120 14 177 116 0
high 120 16 126 142 0
high 122 -16 118 150 0
high 122 -14 67 176 0
high 122 -12 16 202 0
high 122 -10 222 97 0
high 122 -8 171 123 0
high 122 -6 120 149 0
high 122 -4 69 175 0
high 122 -2 18 201 0
high 122 0 224 96 0
high 122 2 173 122 0
high 122 4 122 148 0
high 122 6 71 174 0
high 122 8 20 200 0
high 122 10 226 95 0
high 122 12 175 121 0
high 122 14 124 147 0
high 122 16 73 173 0
"
for run in 1 2; do
	echo "$CASES" | while read kind cut k r g b; do
		[ -n "$kind" ] || continue
		if [ $kind = low ]; then w2=$(printf 0x%08x $((0xff008000 | cut))); else w2=$(printf 0x%08x $((0xff000000 | cut << 8))); fi
		base=$(printf 0x%08x $((0xff000000 | r << 16 | g << 8)))
		echo "#### run $run $kind cut $cut k $k S $((cut * 1024 + k)) rgb $r $g $b"
		sudo -n timeout 60 "$T" copy --width 64 --height 1 --src-stride 256 --pixels --ramp b=$b --ramp-base $base \
			--poke tex:0^=0x80000000 --poke xfer:17^=0x2 --poke xfer:29=0x02020106 \
			--poke xfer:30=0x00210064 --poke "xfer:31=$w2" 2>&1 </dev/null
		echo "## exit $?"
	done
done
echo "## end"
