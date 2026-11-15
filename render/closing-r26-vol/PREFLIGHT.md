# r26-vol preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both). Travel cable:
   `SGX_TARGET_HOST=jtorra@10.42.0.2`, HostKeyAlias cedar (session.toml).
2. `~/sgxfive-test-t24` sha256 fd15fce4ca75b3868fd42b7e5d639ae8a3096fc895543e25a707bac9fb5db040
   (lead/TOOL24.built), `~/sgxfive-test-t10` 9bedc2d6... (the kit's stage checks both).
3. `~/scratch/r26v/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 95445c7, data e639458f0 (pins: E567's tx-types tables and template, its four
   kept control programs and six kept images, the t24 and t10 recipes).
6. Run before r26-sa0 in the sitting (the longer session first, rank-round26.md 4).
