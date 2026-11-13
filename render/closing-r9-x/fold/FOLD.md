# r9-x fold (post-run, not frozen)

- Attempt 20261113-081821, 66 jobs in five stages, rc 0 (run.log, stage.log: the lead's driver
  logs); the frozen scorer's output is out/20261113-081821/score-STAGE.txt.
- t3, post hoc (`fold/t3_post.py`, output `fold/t3_post.out`): on the six bit-14 rows the read
  is the kept reference's dword plus floor(4096 * min(max(u, 0), 1)) at 12288 of 12288 pixels,
  whatever S and W (R-4096, formed after the run; S * S = 4096 in E566's jobs and in the four rows
  where H-U01 held). Needs a held-out row (S * S other than 4096 with W other than 64).
- zst: formats 3 and 5 changed 640 depth dwords a tile, 6 512 and 7 196 (64 x 32) or 229.3 (96 x
  48, not a whole number a tile); no stencil-store dword changed in formats 3 to 7.
- Q121 is not run (README.md, deviation 1): it needs `tri --isp2` with the ZLS stencil buffers, a
  tool change.
