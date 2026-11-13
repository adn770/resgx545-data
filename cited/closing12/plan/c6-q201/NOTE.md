# C6 / Q201: cmd:16 byte 0 as the single-sample point, scored on E064's sweep

Rule SAMPLE0 (`sample0_rule.py`,
sha256 a1980fa58965057c11c9c2950f5cb342ae2050e63082388f71065c5c138c4b73,
frozen in `FREEZE.log`): E606/E660 coverage (exact, 1/256 vertices, top-left ties; ported from
sgx-pipe `Tri::covers`) on the tool's 64x64 triangle (8,8), (56,20), (20,56) pixels
(`sgxfive_tri_default`), with pixel (x, y) sampled at (x + lo/16, y + hi/16), lo = bits 3:0,
hi = bits 7:4 of cmd:16 (x = low nibble decided from E278 "x in bits 3:0, y in bits 7:4" and E339
0x26 = (6, 2) before freezing; 0x88 = centre). Rivals: SWAPPED, FIXED (0.5, 0.5), HALF
((n + 0.5)/16). Pass: all 256 predicted counts equal the observed "N triangle" and the partition
of the 256 values by predicted image equals the partition by observed hash.

Data: `/Users/jtorra/src/resgx545-data/isp/sample-positions/raw.txt` (256 cases, count, hash,
diff). Fit-ish rows: the 31 one-nibble values E064 tabled (other nibble 8). Held out: the 225
two-nibble values and the 27-class hash partition, never fitted by E064. Before the freeze I read
only the baseline and `^=0x1` cases of raw.txt (format), report.txt's head, and tallied the
`diff:` column (all 256 are 0, so it carries no information: it is the tool's own edge-tolerant
check, not a diff against the baseline; not scored beyond that).
No pixel images are kept, so only counts and hash partitions are scored.

Results (`score.out`, rerun: `python -I score.py > score.out`):
- SAMPLE0: counts 256/256 held (one-nibble 31/31, two-nibble 225/225); 27 predicted classes =
  27 observed hash classes, all identical (256/256 values in the right class). PASS.
- SWAPPED: counts 226/256, classes identical 2 of 27, 12/256 values in the right class. Failed.
- FIXED: counts 51/256, one predicted class against 27. Failed.
- HALF: counts 197/256, 0 classes identical (28 predicted classes). Failed (also misses 0x88).

Inference [infer]: the single-sample position source is the pixel plus (lo, hi)/16, x low nibble;
E606's "pixel centre" is byte 0 = 0x88; E502/E1010's x + 0.375, y + 0.125 is byte 0 = 0x26.
Q201's "position source differs from the attribute point" then reads as setup, not hardware.
Caveat: equal hashes were matched to equal predicted images by class, not by pixels; one
triangle, one run. A value whose count or class differs refutes it.

Records: E064, E278, E339, E437, E502, E606, E660 (E904, E1010 per the survey, not re-read).
No landed claim needs correction; E064's "does not say which nibble is x" can get an appended
note that SAMPLE0 fits all 256 counts and the 27-class partition (swapped fails). All files are
publishable (no firmware-derived content).
