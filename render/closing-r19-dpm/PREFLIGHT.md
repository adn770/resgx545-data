# r19-dpm preflight (the lead, before staging)

1. S1 r19-k0 ran on this boot and its k0 controls, f0-same and f0-up passed (R19-1 a); else this
   session is void and is not staged.
2. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both); debugfs
   `render_final_pb_pages`, `tadata_fill`, `render_param`, `render_tadata`, `render_words`
   present (session.toml `debugfs` and `[knobs]`: the preflight checks them).
3. `~/sgxfive-test-t18b` sha256 58e7985504d0d3311155d94627da8b8473335d9a843f5610e44731864315b21e,
   `~/sgxfive-test-t10` 9bedc2d6..., `~/regtimeline` 079f6359... (the kit's stage checks them).
   t18b's recipe is bound as `data:render/closing-r19-k0/lead/build_tool18b.sh` (S1's
   publication); `lead/build_tool18b.sh` here is the same bytes as `closing18/k18/`.
4. `~/scratch/r19d/` absent or empty; at least 300 MiB free on `~` (the 4096x4096 TA data and
   the 1024x768 depth dumps, gzipped by the runner).
5. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
6. Kit on resgx545 50606dc (the replay of `tadata_fill` rows; FOLD-NOTES.md).
