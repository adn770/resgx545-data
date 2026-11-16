# r29-kreg fold notes

Attempt 20261116-061842 (fold/lead-run.log, fold/lead-stage.log): rc 0, 154 jobs, no fault, no
stall, no stop; 0x0a78 read back 0x2c after the run (the lead). s0: 9 of 9 exact, references
median 67164 us. k1: `SUMMARY: k1: controls FAILED: c11: FAILED`, so no frozen verdict. The
scores reproduce byte for byte (fold/reproduce.out).

## c11 (post hoc, after the run; not a frozen rule)

c11 (the 11th 0x2c control, k1 row 91, after b11 = 0x11) read 69190 us, 3.02 percent over s0's
median. Its six renders were 70807 71090 74071 67271 66885 66636 us: renders 2 and 3 ran 6 and
10 percent slow, renders 4-6 at the other controls' level. Not drift: c10 (row 82) and c12 (row
100) read -0.07 and -0.54 percent, the other 15 controls -0.54 to +0.37 percent with no trend
over the run (fold/posthoc.txt). Not a value lingering: the runner read 0x0a78 back as 0x2c
before c11's job (the kit's pre-check and read-back), and b11's own reading was -0.13 percent. A
one-job, two-render spike, the kind E396 saw once (a 0x01 run with renders of 73110 and 74396
us). Two value rows had the same kind of single-render spike: a23 render 6 at 82956 us, b39
render 6 at 74235 us; a04's render 2 at 70515 us (+5 percent). 4 of the 720 renders 2-6.

## Readings (no verdict)

Per value (fold/k1-values.txt, from score-k1.txt): the mean of renders 2-6 against the 16
controls' median 67162 us. 62 of 64 values within 1 percent on both passes (from -0.60 to +0.97
percent); 0x23 +4.77 percent on pass A (its spike) and +0.02 on pass B; 0x39 +0.31 on pass A and
+2.26 on pass B (its spike). No value outside 1 percent on both passes. Post hoc, the median of
renders 2-6 in place of the mean: every value within 0.82 percent on both passes and the 16
controls within -0.59 to +0.36 percent of their median (fold/posthoc.py).

## What it does to Q024

Narrows, does not retire: the frozen control rule failed (a single control spike), and the
many-small-triangles clause was not run (no timed form in t10). A rerun with a frozen robust
reading (median of renders 2-6, or a spike rule) would most likely retire the 256x256 clause
only; the question stays open on the other load, so it is not worth a run on its own.

Session caches (`__pycache__` in tests/, kit/, gen/, score/) and debug/ are left out of the
published copy.
