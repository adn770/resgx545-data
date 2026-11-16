# r34-q044 fold notes (the builder's, for the fold when the lead resumes it)

- Records: E1135 (p1 + pw, bit 25 per mode; s0's controls) and E1136 (p2, the low byte and bits
  11:8). Draft each with `tools/records/new_record.py --session DIR`.
- Verdict: `python3 score/score.py retire out/ATT` prints RETIRE or NARROW with reasons and notes
  (the modes reading 0 against a mask, 22 and 34's readings for Q012, mode 14 named from E031).
- Q044 (pbe/Q044-reg-0400-other-pack-modes.md): RETIRE closes clauses (a) and (b) as README.md
  "Retire rule" says; the lead confirms the split. Q012: append 22 and 34's bit-25 reading (on the
  dwords their two references repeat) as a narrowing line of our own clause only.
- If a p1 reference fails H-E031 (the image differs from E031's kept one on 7CE8E38E), E031 needs
  an appended correction for that mode; the bit-25 verdict is unaffected (read against the stage's
  own reference).
- sgx-pipe pbe.rs: `reg0400_known` admits bit 25 and the low bytes / 0xf80 measured in the modes
  pack_of models (7 at field 0, 8, 15, 18, 20, 24, 25, 27, 28) and `pack_pixel`'s inversion for
  them; tests from the kept images (crates/sgx-pipe/tests/pbe_pack_images.rs's form). Mode 4's
  threshold only if the fold models ARGB1555 in pack_of (H-GE/H-GT decided).
- Replay tables: README.md "Replay vectors".
