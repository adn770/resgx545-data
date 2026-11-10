# SPDX-License-Identifier: MIT
# bis.awk: the runner's bisect and flip references from a group's observations (one line a job: `THR0_DECIMAL CLASS NAME`, CLASS R raise,
# N none, V void).  Twin of score/dpm3.py (bracket, pick, flip_of; tests/test_awk_reader.py feeds both the same observations).
#   awk -v mode=B|L|F -v off=N -f bis.awk FILE     prints `THR0_DECIMAL` or `SKIP reason`
# lo = the highest raise, hi = the lowest silent cell above it.  B: lo + (hi - lo) / 2 (integer division) unless the bracket is closed
# (hi - lo <= 1), absent, non-monotone (a silent cell below a raise) or holds a void cell (the bisect ends).  L: lo + off.  F: hi + off.
{
	t = $1 + 0; c = $2
	if (c == "R") { if (!haveR || t > lo) lo = t; haveR = 1 }
	else if (c == "N") { N[++nn] = t }
	else if (c == "V") { V[++nv] = t }
}
END {
	if (!haveR) { print "SKIP no raise cell in the group"; exit }
	hi = -1
	for (i = 1; i <= nn; i++) {
		if (N[i] < lo) { print "SKIP not monotone (a silent cell below a raise)"; exit }
		if (N[i] > lo && (hi < 0 || N[i] < hi)) hi = N[i]
	}
	if (mode == "L") { print lo + off; exit }
	if (hi < 0) { print "SKIP no silent cell above the last raise"; exit }
	if (mode == "F") { print hi + off; exit }
	if (hi - lo <= 1) { print "SKIP bracket closed (exact flip)"; exit }
	for (i = 1; i <= nv; i++) if (V[i] > lo && V[i] < hi) { print "SKIP void cell inside the bracket"; exit }
	print lo + int((hi - lo) / 2)
}
