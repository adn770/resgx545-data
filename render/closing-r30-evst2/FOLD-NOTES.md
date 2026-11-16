# r30-evst2 fold notes

- Records reserved: E1117 (e2-e4: CR_CACHE_CTRL at the kick, CR_USE0_SERV_EVENT across a served
  triangle, bit 26's width against the registers sampled), E1118 (e1, e5: the held-out repeat of
  E1115's models and H-ONCE/H-EACH). Checked 2026-11-16: main 24e4a36 ends at E1116;
  closing29/r30-pde names no record yet, so it may claim E1117 too: the lead settles it.
- sgx-sim: if H-SE-EVENTS holds, hw.rs's E009 count may move by a measured count a served
  triangle only where the events of a triangle are the fwsim run's; if H-CC-KICK holds, the
  0x012c refusal after a kick can name the lead. The loop's read value stays refused unless a
  frozen row gives it. Test first.
- Delete `debug/`, `.pytest_cache` and `__pycache__` before the fold publishes.
