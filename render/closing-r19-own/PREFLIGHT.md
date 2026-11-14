# r19-own preflight (the lead, before staging)

1. The laptop runs module srcversion E0CC40275493F8AEAD8180B, loaded = installed (the kit's
   preflight checks it and the debugfs files `render_keep`, `render_pb_pages`,
   `render_final_pb_pages`, `render_kept`, `render_words`, `buf09`, `kpoke`). On the fallback
   module B60AB0B4 this session does not run: ask the builder for its twin.
2. `~/sgxfive-test-t18b` sha256 58e7985504d0d3311155d94627da8b8473335d9a843f5610e44731864315b21e
   and `~/sgxfive-test-t10` 9bedc2d6... (health) are on the laptop (the stage checks both).
3. The knobs at their defaults before the first job: render_keep N, render_pb_pages 0x422,
   render_final_pb_pages 0 (a session before this one leaves none armed; a reset disarms
   render_keep and the final PB).
4. Free space: at least 300 MiB on `~` (two 2048x1536 contexts' copies are 0x37000 bytes each).
5. `bash tests/run_all.sh` passes on the frozen tree (it verifies the freeze).
