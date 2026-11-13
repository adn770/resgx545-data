# r13-zls fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E1029 (zbase, Q243), E1030 (zbits, Q071), E1031 (zfmt, Q120). Draft with
  `tools/records/new_record.py --session DIR`; cite E058, E465, E467, E977, E995 (zbase), E411,
  E988, E989, E997, E1014 (zbits), E985, E986, E1015 (zfmt).
- zbase: read the controls first (zb-c-id the identity; zb-c-off all 1.0). Then each move's
  READING line gives the offset d the store holds: if no frozen rival holds, fit the base rule
  post hoc from the seven d values (alignment, a mask of rd:12's bits) and say [post hoc].
  zb-m4 is the only base below 16-byte alignment: a fault there stops the stage; the earlier rows
  stand. If H-MOVED holds on all 7, propose retiring Q243 (R13-9: its last open clause).
- zbits: per clause, the model that holds alone names the bit (or the pair). Ramp rows "other"
  (neither E977's nor E997's dump) are a third layout: decode post hoc with
  `render/closing-r10-x/fold/zbits_layout.py`'s forms. Stencil rows: the READING image line tells
  whether the loaded stencil's order moved with the linear bit (1024 drawn, image != zbs-base's).
- zfmt: zf-y48-f0's READING line gives the constant tile rows (the edge tile past 48 may not be
  constant: those groups are undecoded, not failed). zf-flat-f6's undecoded count beyond the 16
  groups is a reading (a whole-tile record would fail F6C).
- Replay tables (README): zbase and zbits into sgx-pipe zls.rs test first; zfmt refused unless
  modelled. Delete any `.pytest_cache` and `__pycache__` before publishing.
