# SPDX-License-Identifier: MIT
# dpm_read.awk: reads one job's tool output (the regtimeline block: `timeline: regs ...` and `tl TIME v v ...` rows) and prints
#   nparts=N thr0=0xH reach=0|1 valid=0|1 knob=0xH need=N c1=N cN=N
# Rules are R1's (the same as score/dpm3.py, tests/test_awk_reader.py feeds both the same jobs):
#   partial render = rising edge of 0x0658 bit 0; thr0 = 0x0724 low half at the first partial render's start; peaks = the peak
#   low half of each TA run; reach = the second run's peak >= thr0; valid = reach && nparts > 1; knob = the first 0x0624 value at
#   or after the header's `start` whose 0x0724 low half is non-zero; need = the highest peak; cN = the 0x072c low half in the
#   sample just before the last abort's edge (H-last's variable; c1 before the first).  POSIX awk only (no strtonum).
function hex(s,   i, c, v, d) {
	v = 0; s = tolower(s)
	for (i = 1; i <= length(s); i++) { c = substr(s, i, 1); d = index("0123456789abcdef", c) - 1; if (d < 0) break; v = v * 16 + d }
	return v
}
function low(v) { return v % 65536 }
function bit0(v) { return v % 2 }
/^timeline: regs/ {
	nc = 0
	for (i = 3; i <= NF; i++) { if ($i == "samples") break; nc++; name[nc] = $i; if ($i == "0x0624") c24 = nc; if ($i == "0x0658") c58 = nc; if ($i == "0x0724") c724 = nc; if ($i == "0x072c") c72c = nc }
	for (i = 3; i <= NF; i++) if ($i == "start") start = $(i + 1) + 0
	have = 1
	next
}
/^tl / && have {
	t = $2 + 0
	v58 = hex($(2 + c58)); v724 = low(hex($(2 + c724)))
	v24 = hex($(2 + c24))
	c2c = c72c ? low(hex($(2 + c72c))) : 0
	if (!kfound && t >= start && v724 != 0) { kfound = 1; knob = v24 }
	if (bit0(v58)) {
		if (!inpr) {
			nparts++
			if (nparts == 1) thr0 = prev_st
			c_last = prev_c; if (nparts == 1) c_first = prev_c
			npk++; peak[npk] = cur; cur = 0; inpr = 1
			if (nparts == 1) thr0 = v724
		}
		prev_st = v724; prev_c = c2c; next
	}
	inpr = 0
	if (v724 > cur) cur = v724
	prev_st = v724; prev_c = c2c
	next
}
END {
	npk++; peak[npk] = cur
	need = 0; for (i = 1; i <= npk; i++) if (peak[i] > need) need = peak[i]
	reach = (nparts >= 1 && npk > 1 && peak[2] >= thr0) ? 1 : 0
	valid = (reach && nparts > 1) ? 1 : 0
	printf "nparts=%d thr0=0x%x reach=%d valid=%d knob=0x%x need=%d c1=%d cN=%d\n", nparts, thr0, reach, valid, knob, need, c_first, c_last
}
