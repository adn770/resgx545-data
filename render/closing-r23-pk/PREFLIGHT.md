# r23-pk preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both). Travel cable:
   `SGX_TARGET_HOST=jtorra@10.42.0.2`, HostKeyAlias cedar (session.toml).
2. `~/sgxfive-test-t22` sha256 9b62d31539564b0ca9e949aa1b44e325455b485a985fdfa65976684888d219ee
   (lead/TOOL22.built), `~/sgxfive-test-t10` 9bedc2d6... (the kit's stage checks both).
3. `~/scratch/r23p/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 b2b6bc0, data 40abeab5a (pins: E391's 40 programs and raw output, E125's case
   0, E568's tables and kept fy outputs, t10's recipe).
6. E037's copy hashes (0xb6067a95fa98de2d, 0xd3522437a14b6325) come from the 2026-11-01 tool; the
   hash line (`target: WxH hash`, sgxfive_hash_dwords) is unchanged since ac5b888. If c-copy-csc
   fails while c-copy-none holds, read the pixels before blaming the hash.
