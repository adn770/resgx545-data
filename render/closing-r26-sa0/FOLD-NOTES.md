# r26-sa0 fold notes (builder)

- Record E1106 only. Own worktrees and branches (r26-fold-sa0, r26-fold-sa0-data).
- Attempt 20261115-224747: both gate controls PASS (c-e521 H-E521 8/8, c-one-r10 H-ZX 8/8), H-ZX
  6 of 6 held-out rows, H-SX 0 of 6, H-MIX 0 of 6. The score files reproduce byte for byte
  (fold/reproduce.out).
- Q126 clause 1 (the extension the test reads) is not observable by E498's measured rules;
  clause 2 (sa0 written by one writer) is decided by E1106: retire (R26-3 a), a separate commit.
- The writer is a 2x2 quad (E513: the branch is decided by the top-left lane), so the plan's
  (63, 31) became the quad with top-left lane (62, 30).
- Replay refused: sgx-sim refuses pa0 reads before a write and has no quad branch.
