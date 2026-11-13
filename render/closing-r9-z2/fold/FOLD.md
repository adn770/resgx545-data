# r9-z2 fold (post-run, not frozen)

- Attempt 20261113-082522, 10 jobs, rc 0 (run.log, stage.log: the lead's driver logs).
- `fold/look.py` (standard library, post hoc) reads the kept dumps: `fold/look.out`.
- Ramp b (viewport z offset -0.25, a depth from -0.75 to -0.25 as modelled): format 0 stored 0.0 at
  every pixel; formats 1 and 2 stored 0 at every dword, with bit 19 and without (byte-identical
  dumps). The four frozen rivals collapse onto 0 there, as README.md's fold caveat said.
- Ramp a (offset +0.25): format 0 stored 0.00059 to 0.2994 along x at y = 0 (0.6 t, t = x / 512,
  post hoc), never 0 or negative: not the modelled -0.25 to +0.25; what the poke of state-block
  word 10 did to the depth is not shown. Its integer rows follow min(floor(z * 2^24), 0xffffff)
  (and >> 8 in E490's layout) at every dword, bit 19 or not (byte-identical), and miss
  round(z * 0xffffff), the rivals' encoding, at 8803 of 32768 dwords: E977's floor rule.
- `lead/build_tool9.sh` is the k1build recipe byte for byte (frozen): its header still names r9-k1
  and its last line prints `data:render/closing-r9-k1/...`; the recipe this session binds is this
  copy, `data:render/closing-r9-z2/lead/build_tool9.sh` (FROZEN.commits' built line).
