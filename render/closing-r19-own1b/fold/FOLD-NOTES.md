# r19-own1b fold notes (builder, 2026-11-14)

- The lead's decision after r19-own's attempt 20261114-223625 (own1 stopped at o1-c-a, E1085): own1
  again, with two more 64x64 flag-0xc repeats, on prefix r19o2. At the fold this session's verdict
  replaces E1085 (amend branch r19-fold-own, or a follow-up commit), with E1085's empty copy cited.
- Known tool weakness to list in HACKING.md "Known tool weaknesses" (a fold reports it; the tooling
  agent adds it): t18b's `--kept-copy` reads debugfs render_kept once, right after the early close,
  and gets 0 bytes when the kernel has not parked the context yet ([infer] parked when its last
  reference goes, `sgxfive_ctx_release` at fork 456404fcffe5, which can be after the close ioctl
  returns; E1085's o1-c-a). The fix is a bounded retry on an empty read (or the kernel parking
  before the close returns); until then a session counts an empty copy as cannot tell.
- Score: `python3 score/score.py own1 out/ATT/own1`.
- Post hoc (fold): the 1024x768 owner at P 0x422 (o1-big-a, o1-big-b, identical): after the close
  its control, OTPM and state pages are zero; after the second render its state page holds 11
  list pairs (count << 16 | head, tail) whose counts sum to 18 (U - 1, U 19), the first
  0x00010002, 2, so the "state words" are macrotile lists (E627's format), not a page count of the
  owner; its control page holds 11 words 0x002000xx to 0x002002xx (E631's 5 among them), its OTPM
  page 0x04000417 at dword 16. Neither H-CONST nor H-NONE fits.
