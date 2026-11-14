# r19-dpm fold notes (builder, 2026-11-14)

## Kit gap (resolved)

The library-mock replay at 6809cdd gave the tool no debugfs `tadata_fill`, so ld's four zero rows
could not replay. Fixed on main 50606dc (the replay creates the session's declared debugfs files);
kit/ re-scaffolded on 50606dc (only kit/session.py changed), the freeze pins resgx545 50606dc.

## Deviations from the plan (rank-round19 section 3)

- dz and zs run as stages split by the dumps their rows write (dzl, dza, dzc, dzo; zsc, zs): the
  scorer's REQUIRED is per stage and per row, and a dump only geometry rows write cannot be
  required of a -n 1 control (a by-name entry is checked even after a stage stops: 43). dza is
  gated by dzl's controls, zs by zsc's (`gate = true`). Records unchanged (E1081, E1082).

- zs has 7 jobs, not 6: the 0x422 control needs a G 33 twin for q107_rule.py (the plan named only
  the G 1 row); total 42.
- The premise of every geometry row is read from the tool and --regs (render 1 `overflowed`,
  render 2 not, 0x0624 = 0xde after the final), not from 0x0658 stretches alone; rt still runs
  on every row (nparts and peak are read and kept).
- dz-a's E336 word (0x0011700a) replaces the second 0x28 load replicate (dz-a-e336-28).
- dz-c passes `--depth-pages 0x340`: with 784 pages E628's G 33 store spills past the buffer into
  the target's first rows (the 19968 "other" pixels of dl-z05-noload-0x422), which would fail
  the layer control.
- dz-ov reads H-PRLOAD vs H-OWNCLEAR as the share of the partial render's triangle depth (past
  tile row 11) the final's store keeps (>= 0.5 vs <= 0.05), not the nearer-wins test in the
  overlap (that needs both triangles rasterized; the fold may add it from the kept dumps).
- Output files go straight into `$W` (`--dump-render "$W" --words "$W" --depth-dump "$W"`): the
  runner makes only the parent of an `outdir_opts` argument, so `$W/dump` would not exist
  (r19-flag's `--dump-render "$W/dump"` with `outdir_opts` has that problem: the tool cannot open
  `$W/dump/...`; to check before its staging).

## Fold

- Score: `python3 score/score.py STAGE out/ATT/STAGE` per stage; q107_rule.py from the pinned
  blob. Offline extras for the records: E626's walk on the ld param dumps; the dz-ov overlap.
