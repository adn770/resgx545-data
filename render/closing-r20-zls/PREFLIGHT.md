# r20-zls preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both); debugfs
   `render_final_pb_pages`, `render_param`, `render_tadata`, `render_words`, `buf09`, `kpoke`
   present (session.toml `debugfs` and `[knobs]`: the preflight checks them).
2. `~/sgxfive-test-t18b` sha256 58e7985504d0d3311155d94627da8b8473335d9a843f5610e44731864315b21e,
   `~/sgxfive-test-t10` 9bedc2d6..., `~/regtimeline` 079f6359... (the kit's stage checks them).
3. `~/scratch/r20z/` absent or empty; at least 300 MiB free on `~` (zr's three 832-page depth
   dumps a render, gzipped by the runner).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 c0f8c41, data ba3990f01 (the pins: q107_rule.py, r19-dpm's kept dumps).
