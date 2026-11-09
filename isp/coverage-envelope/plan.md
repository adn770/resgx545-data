# p1140: widening the envelope of the triangle coverage rule (Q240, Q199)

Scratch, untracked. Method of p1138 (plan.md there), colour images only. H0 = E606/E607's rule. The question:
where does H0 stop holding, on targets and vertices the records refused? Blind: sets, hypotheses, alternatives and
criteria frozen by hash (`freeze1140.sh`, `predictions-1140.toml`, `manifest-1140.sha256`) after a pilot of 6
cases outside every set and before the first main job.

Tool: `tool/` (a copy of p1138's tool-b), by TDD (`tests/test_render.c` test_vertex_words, three tests in
`tests/test_cli.py`): `tri --pixels-rle` (a row a line as runs, short for a 4096 x 4096 target) and the clip words
of the three vertices (`tri: clipN x y z w`, float32 bits, from `sgxfive_tri_vertex_words`, the function the scene
itself uses) printed for every `--tri-v` job, so the input the hardware got is recorded directly. Three stale
expectations of test_render.c (513 for 512, 2^-16 for 2^-17) were fixed. Deployed as `~/sgxfive-test-1140`
(`deploy1140.sh`; binary and source shas in env.toml).

Groups: S1 size (random 1/256 triangles; 3 fit and 7 held-out sizes, non power of two half-sizes, up to 4096 x 4096),
S2 sweeps across the half-grid tie (1/4096 pixel, 1/1024 from 2048 wide), S3 negative coordinates with sub-grid
fractions (edges aimed at pixel centres, kept when the rounding variants disagree), S5 tiny-edge (cross product +-1,
512^2 to 4096^2), S4 far vertices at +-2^k pixels (run last, one job at a time with a health check before each).
Run: `run/run_p1140.py` on the laptop, one process per job, marker in /dev/kmsg, raw output gzipped, three failed
recoveries stop it. Recompute: `recompute/recompute_p1140.py` (numpy, scratch; model in `model1140.py`).

## Result and changes after the freeze

Criteria of predictions-1140.toml: P1, P2, P2b, P3, P4, P4b, P5b, P7, P7b, P8a, P11, P12 passed (12 of 17); P5, P6 (negative
coordinates), P8b (4096^2 edge function not exact), P9 and P10 (far vertices exact to 2^15; first mismatch at k = 16) failed.
Run: pilot 6 jobs, main 1608, far 208 (1822 jobs, 0 flagged, 0 resets); 10 cases of S1 4096 x 4096 (ids 1400416 to 1400425) were not run.
After the freeze (stated, not hidden): recompute/recompute_p1140.py takes several run directories (main, far) so the criteria are
evaluated in one pass (no model or criterion changed; the file no longer matches manifest-1140.sha256, the cases, run script,
model, predictions, tests and tool do); recompute/post_neg_1140.py, post_neg2_1140.py, post_tie_1140.py, post_dist_1140.py and
post_far_power_1140.py are post hoc and not frozen. Nothing was refitted: the failed criteria stay failed.
No registers were written from userspace (no kpoke, no depth): the colour jobs only.
