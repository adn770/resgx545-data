# r23-dpm preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both); debugfs
   `render_final_pb_pages`, `render_pb_pages`, `render_keep`, `render_param`, `render_tadata`,
   `render_words`, `buf09`, `kpoke`, `render_kept` present (session.toml `debugfs` and `[knobs]`:
   the preflight checks them); `render_bg_layer` reads N (t22b refuses `--bg-pds` with it on).
2. `~/sgxfive-test-t22b` sha256 2ae2800aa8a0c37dea6e36aaf011d3e707b53831d6a16d2c8a859d4d2640c6ac
   (closing22/k22/TOOL22b.built), `~/sgxfive-test-t10` 9bedc2d6..., `~/regtimeline` 079f6359...
   (the kit's stage checks them).
3. `~/scratch/r23d/` absent or empty; at least 300 MiB free on `~` (zn's four 832-page depth dumps
   a row, gzipped by the runner).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 b2b6bc0, data 40abeab5a (the pins: E442's programs, E1089's zm, E1087's own1
   and E1093's zl kept rows and tables, t10's recipe).
6. r23-pk runs first (records E1096 to E1098); this session's records are E1099 to E1101.
