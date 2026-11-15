# r25-csc preflight (the lead, before staging)

1. Module E0CC40275493F8AEAD8180B loaded and installed (the kit checks both). Travel cable:
   `SGX_TARGET_HOST=jtorra@10.42.0.2`, HostKeyAlias cedar (session.toml).
2. `~/sgxfive-test-t22` sha256 9b62d31539564b0ca9e949aa1b44e325455b485a985fdfa65976684888d219ee
   (lead/TOOL22.built), `~/sgxfive-test-t10` 9bedc2d6... (the kit's stage checks both).
3. `~/scratch/r25c/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again.
5. Kit on resgx545 7f214e5, data 40050d0ac (pins: r23-pk's fy-28/29-p0 bins, its kept fills and
   copies, its q181 table, the t22 and t10 recipes).
6. Run it as its own stage, not between other sessions' YUV jobs: the first row's copy sets the
   state, so an earlier session's load does not matter, but a re-stage reruns from y28-zc.
