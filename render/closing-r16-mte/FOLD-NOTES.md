# r16-mte fold notes (the builder, for the fold after the run)

- Record: **E1060** only (Q116). Unit mte. Method: this session's rows (README.md), t10 a581c06,
  module B60AB0B4; draft with `tools/records/new_record.py --session DIR`.
- Read `out/ATT/rclip/score-rclip.txt`: the `READING rclip` lines (combinations left; form,
  outside, enable) and `RETIRE rclip`. A retirement is proposed only on `RETIRE rclip: yes` with
  both controls PASS (R16-6 a); a FAILED frozen row is not explained away post hoc (DECISIONS-R16).
- If H-FLIP holds and H-TILECLIP fails: E348's "from the bottom" then means the target's last
  row in our frame; say so in E1060 and check whether E348 needs an appended correction (its
  [CAP] claim is about the closed driver's GL rows, which may stand as written).
- If the gate stopped (hook_check on g-clear-64): its kept image alone decides between H-EXCL,
  H-PIXEL and the rest on that row; Q116 narrows only.
- Q116's "clears": a full-target object with E348's clear clip and the background object [infer]
  (R16-6 a); "what it does beyond a scissor": whole tiles only, if H-TILECLIP (or another tile
  form) holds; the mask-fill reading of E340 stays the closed driver's.
- Replay: add a region clip to sgx-pipe `mte.rs` test first (presence 0xdfc3, words 6-7), a
  `crates/sgx-pipe/tests/` test replaying the `rclip` table, then `closing_tables.py texture
  --replayed ...`. sgx-sim: check whether it refuses presence bit 7 and keep it refusing until
  modelled (SIM_UNMODELLED).
- Delete `.pytest_cache` and `__pycache__` before publishing; `debug/` is not published.
