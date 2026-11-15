# r25-sa64 preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both). Travel cable:
   `SGX_TARGET_HOST=jtorra@10.42.0.2`, HostKeyAlias cedar (session.toml).
2. `~/sgxfive-test-t24` sha256 fd15fce4ca75b3868fd42b7e5d639ae8a3096fc895543e25a707bac9fb5db040
   (lead/TOOL24.built, built from resgx545 1341034 by lead/build_tool24_laptop.sh),
   `~/sgxfive-test-t10` 9bedc2d6... (the kit's stage checks both).
3. `~/scratch/r25s/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 1341034, data 40050d0ac (pins: E391's 40 programs and raw output, E125's case
   0, attribute-room and douta tables, douta_words.s, E1096's kept pk and q019 outputs, t10's
   recipe).
6. The recipe's `data:render/closing-r25-sa64/lead/...` path exists once the fold publishes this
   session (as r23-pk's t22 recipe did).
