"""FROZEN rule file (c5-q210). Do not edit after the freeze; a revised rule is a new file.
Data read before this freeze: E1009 text, r10-dpm fold/brackets.py + brackets.out (its 15 s6rep
bracket rows + control), fold/readall.py (code only), gen/plan.py, gen/r9_tables.json (keys, the
13 target names, one model entry, and a truncated print of 'm6b'/'w'/'repl' prefixes). No kept
run's samples besides those in E1009/brackets.out were read.

Bracket (brackets.py / score/read.py reading): for the TA run's global page step k, samples
around the 0x072c high-half step give (a, b) = 0x0724 high halves; bracket (lo, hi) =
(a, max(a, b-1)). lo = a is the "lower end". R = replay S[6] (gen/r9_tables.json models[WxH].S[6]).
d = lo - R.

H-CLASS  (caller's): BIASED = {4096x1024, 4096x1536, 3584x1024, 2048x512, 2048x2304};
         HELD   = {1280x1280, 1536x1536, 1792x1792, 2048x2048, 2304x1792, 2304x2304, 2560x2048,
                   4096x2048}. Prediction: d == +1 at every run of a BIASED target, d == 0 at
         every run of a HELD target (every run: calibrations and, separately, partial-render
         cell runs). Pass: zero exceptions among held-out runs (all runs not already read by
         E1009/E961/E962; those are fit/known rows, reported separately).
H-LOW0   (rival): d == 0 at every run at every target (no bias).
H-LOWPLUS1 (rival): d == +1 at every run at every target.
H-RULE   (candidate, stated from E1009's 13 targets, so FIT on them; frozen with predictions for
         any target with a replay): bias iff w/h > 2 or w < h (the aspect w:h outside [1:1, 2:1]).
         Predictions: 4096x1024 B, 4096x1536 B, 3584x1024 B, 2048x512 B, 2048x2304 B;
         1280x1280 H, 1536x1536 H, 1792x1792 H, 2048x2048 H, 2304x1792 H, 2304x2304 H,
         2560x2048 H, 4096x2048 H (w/h == 2 exactly is H).
         Rival rules not scored beyond listing: pixel-count threshold (fails: 4096x2048 8.4M is H,
         3584x1024 3.7M is B while 2048x2048 4.2M is H), height > width only.
Refutation: any held-out run with d not in its class prediction refutes H-CLASS for that
target (cannot-tell if the bracket is absent/void). Targets beyond the 13 have no replay R, so
H-RULE cannot be tested on them offline.
S2/S3: also report d for steps 2 and 3 where a replay S exists (descriptive only).
