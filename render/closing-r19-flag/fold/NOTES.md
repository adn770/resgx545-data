# r19-flag fold notes

- Attempt 20261114-225916 (rc 0, 3 jobs, no fault or hang, no `SGX recovery failed` line).
  `reproduce.out` is the frozen scorer re-run on the kept files: byte for byte the run's own
  `score-fl.txt`. `compare_tadata.py` / `compare_tadata.out`: the junk rows' TA data and parameter
  buffer against fl-ctl's, dump by dump.
- Record E1086 (Q045's load clause). Replay vectors: refused (the partial-render path is
  unmodelled, SIM_UNMODELLED E627, E630, E631), no table.
- The t18b recipe is the one the session cites, `render/closing-r19-k0/lead/build_tool18b.sh`
  (published by r19-k0's fold; a byte copy is in this session's lead/).
