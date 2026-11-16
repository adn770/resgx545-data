# r29-flag2 preflight (the lead, before staging)

1. Flagged: 4 planned recovered hangs (approved, DECISIONS-R29), `#limit`s 5; no fault planned.
2. Module E0CC40275493F8AEAD8180B loaded = installed; travel cable, HostKeyAlias cedar. r29-flag's
   f2 ended in a failed strict health (rc 5); check a t10 `tri` and `fill` draw before staging.
3. `~/sgxfive-test-t10` (9bedc2d6...) and `~/sgxfive-test-t22` (9b62d315...) on the laptop.
4. `~/scratch/r29g` free; at least 300 MB free on `~`.
5. Order: s0, h1, h2. About 10 minutes, 13 at most. Do not reboot on any stop; report it.
6. After the run: `python3 score/score.py q010 out/ATT` (README.md "Q010's rule here").
