# Row D (Q128 follow-up): where crumb3's `douta` writes land (design note, not built)

Status: a note for the lead. Nothing built, frozen or run. Round 40, 2026-11-19.

## What Z already read [HW, printed, not scored]

r39-n3d-z (20261119-153429) read Z-DONE, so entry 1 ran and its LANDING line was printed:
pa0-pa3 = 0x00000000 0x00043000 0x3727c5ac 0x01555620; sa0-sa3 = 0x32004000 0x32005000
0x32002000 0x00000000 = TA3DCtl dwords 0-3 (V0-V3). So crumb3's two `douta` (V0 to attribute 0,
V2 to attribute 2) did **not** land in pa0 or pa2 of the task its `doutu` started. sa0-sa3
equal V0-V3, but they did in every earlier owntask too (the kernel's values), so they say
nothing about the `douta`.

## A row within the installed module (no rebuild, no new risk class)

- Blob: `emitsk14` (or `emitsb14`, whichever S-row runs) whose entry 1 also stores pa4-pa15
  and sa4-sa7 into further result slots (6-9, page dwords 88-103), each store fenced as now,
  before M4. Same emit, word, arm and image as Z: the firmware-page write is Z's.
- The verifier at the pin accepts the reads: `mov rN, paK` and `mov rN, saK` for K up to 31
  classify as `mov-reg` with no refusal (fwtask at r40-s c3f9f67; the C verifier mirrors
  fwtask.FORMS). It still needs the shim run of round 40 with the new blob, as emitsb14 had.
- Readings: the dword(s) equal to V0 (0x32004000) and V2 (0x32002000) among pa0-pa15; table
  D-PA (found at pa k and pa k+2: an attribute offset of k), D-NONE (neither: the `douta` go
  elsewhere or not at all), D-ONE (only one found). Controls as Z. pa1's 0x00043000 is
  printed for the record (not ours).
- Cost: one gen_blobs variant with tests, one shim run, one session (scorer and hooks gain
  the extra slots). About 10 minutes on the laptop.

## Why not built now

Its outcome table is new (the design froze none for the landing), and the three splits come
first: they say what makes the program run at all; D only says where it writes once it does.
Build it after the splits, on whichever pass and word they show suffices.
