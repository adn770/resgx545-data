# r14-bif fold notes (builder; this file is frozen, post-run notes go to fold/)

- Record: E1046 (refill, Q108's stale-data clause). Draft with
  `tools/records/new_record.py --session DIR`; cite E945, E946, E964, E965 (the PTE knob and its
  kernel line), E1029 (the form and the kept zb-c-id / zb-c-off stores), E467 (test never: the
  store holds the load).
- Read the controls first: rf-c-plain (2ok, 4096 and 4096), rf-c-depth (both stores zb-c-id), then
  rf-c-unread (store 2 V: the refill reaches a load through a CC mapping). If rf-c-unread fails,
  the refill rows say nothing about staleness (the write path or --depth-ctl-next is in question).
- Each row's READING line gives both stores' classes, `depth #2` changed (0 on a refill row: the
  host's V stayed in the buffer through render 2) and the PTE line. A `mixed` class is a partial
  stale read: name its tiles (512 dwords a tile, E465) post hoc and say [post hoc].
- Q108's line: append a narrowing for the stale-data clause only (other folds edit Q108's
  neighbours' files, not this one). With H-CC-COHERENT and H-NC-COHERENT held, the clause becomes
  "no stale read on a depth load, either flag state"; what stays: WRITEONLY / EDMPROTECT on a
  texture read, either flag on a depth load, the TA's writes and the EDM's buffers.
- Replay: build the `pte-refill` table (README) and widen sgx-pipe `bif::pte_access` with a ZLS
  load access, test first (`tests/pte_table.rs`), or refuse it with the reason. Delete any
  `.pytest_cache` and `__pycache__` before publishing; publish `lead/build_tool14.sh` under
  `render/closing-r14-bif/lead/` (the recipe path session.toml binds).
