# r10-st1 fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E988 (st1, Q121) and E989 (q071 rows, Q071's stencil clause with r10-x's zbits).
  Draft with `tools/records/new_record.py --session DIR`; cite E284, E467, E978, E985.
- Read the three controls first: st1-never drawing anything means the reference or the mode field
  is not as E284 reads it; st1-always short of 2048 means the depth test is not always.
- If no order holds, check H-NOLOAD's image alone (everything drawn) before the store; then fit
  j from the bytes rows post hoc (each pixel's j mod 256 is in the 8 rows' images).
- Lane 1 (x0 = 1, y0 = 0 under H-DEPTHORD) is the plan's open lane: say it from st1-b0/b1 and the
  lane rows. Edge rows: the past-target pixels' stored bytes are a reading.
- Delete any `.pytest_cache` and `__pycache__` before publishing.
