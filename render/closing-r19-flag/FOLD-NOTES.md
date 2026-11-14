# r19-flag fold notes (builder, before the run)

- Record: E1086 (Q045, the load clause: does a load task read the state page's lists?). Draft its
  method with `tools/records/new_record.py --session DIR`; appended corrections only.
- Read first: the stop (if any), then `score.py fl out/ATT/fl` (CONTROL, READING and ROW lines).
  fl-ctl is also E1078's second reading of the final's 0x0624 = N - 0x22 (cite, do not restate).
- H-NOLOAD on both rows (same image, ok): Q045's load clause reads "no load task read the junk
  lists" with the final not overflowing (E631's blind spot closed); with ld (E1079, zero fill) and
  ldb (E1080) the lead decides the retire (R19-6) and moves clause (c) to Q191.
- A fault or hang: the kept dmesg line (`BIF fault S at A`, or `job N hung, recovering`) gives the
  word and address; the fault page against the TA data and parameter heap pages tells which walk
  read the junk (page numbers past the page table, plan S4). Check the health after it (the kit's
  strict health) and that `SGX recovery failed` is absent from every kept file.
- H-LOAD-CORRUPT: the diff line and the final hash against fl-ctl's; the final's TA data
  (`NAME.tri.tadata.bin`) page 6 against the ramp (which dwords the final changed).
- Kept files per row (suffixes after `NAME.`): txt, err, dmesg, snap0/snap9.regs, tri.1.*.bin
  (after the kick, before the fill), tri.2.*.bin, tri.*.bin, words.N.txt, ta3d.N.bin.
- Replay vectors: refused (README.md), no table, nothing pinned.
- Kit needs (report, do not change shared tools): `outdir_opts` makes only the parent of a
  directory-valued option, so a `--dump-render DIR` below `$W` cannot be made by the runner.
