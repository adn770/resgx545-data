# r30-evst fold notes

- Records reserved: E1115 (bit 26 and CR_EVENT_STATUS across plain triangles, e1, e5, e3's
  density), E1116 (0x0118, 0x0804, 0x0b14 across a kick and idle, e2, e4). Checked 2026-11-16:
  main 9cfced4 and every branch and worktree end at E1114; closing29/kernel names none past it.
- Questions: Q111 (bit 26 word, width, order against the render end; the seen rate; bits 6, 9,
  20 under a sample); E009's count across a served kick (sgx-sim hw.rs `on_event` drops it today).
  Edit only our own clauses of Q111.
- sgx-sim: hw.rs gets a landed rule for 0x012c after a CACHE_CTRL write only from what holds here
  (H-ALONE's word; the delay is not measured unless 0x0804 shows the write: refuse it otherwise),
  and for 0x0b14 across events if H-SE-EVENTS or H-SE-TICKS holds. Test first; the test reads
  the kept `.txt` files.
- The fwsim fact in README "Why" came from the lead (main 9cfced4's fwsim run); no trace was
  read. Keep trace content out of the published session.
- Delete `debug/`, `.pytest_cache` and `__pycache__` before the fold publishes.
