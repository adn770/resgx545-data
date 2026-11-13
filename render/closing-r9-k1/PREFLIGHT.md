# r9-k1 preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (loaded = installed); debugfs has
   `render_bg_layer` (reads N) and `render_bg_src` (reads 0x00000000): the runner refuses to start
   otherwise (knobs at their defaults, session.toml `debugfs`).
2. t9 is staged at `~/sgxfive-test-t9` with sha256
   7a28be3952fb310170e861da0622d890a2e215cb761d6f21bc9321223e1b40ce (the stage step checks it);
   t4 at `~/sgxfive-test-rgn4` (e6951558...).
3. No earlier session of the sitting left a kpoke armed or either knob on (r9-k1 is the only one
   that writes them).
4. `bash tests/run_all.sh` passes on the frozen tree (RUN_ALL PASSED, verify included).
5. Then `python3 kit/session.py stage .` and `python3 kit/session.py run .`.
