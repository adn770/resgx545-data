# r20-own preflight (the lead, before staging)

1. The laptop (travel cable, runbook section 3) runs module srcversion E0CC40275493F8AEAD8180B,
   loaded = installed (the kit's preflight checks it and the debugfs files `render_keep`,
   `render_pb_pages`, `render_final_pb_pages`, `render_kept`, `render_words`, `buf09`, `kpoke`).
   On the fallback module B60AB0B4 this session does not run.
2. `~/sgxfive-test-t18b` sha256 58e7985504d0d3311155d94627da8b8473335d9a843f5610e44731864315b21e,
   `~/sgxfive-test-t10` 9bedc2d6... (health) and `~/regtimeline` 079f6359... (as r19-dpm ran it)
   are on the laptop (the stage checks all three); regtimeline runs under `sudo -n`.
3. The knobs at their defaults before the first job: render_keep N, render_pb_pages 0x422,
   render_final_pb_pages 0.
4. Free space: at least 300 MiB on `~`.
5. `bash tests/run_all.sh` passes on the frozen tree (it verifies the freeze).
