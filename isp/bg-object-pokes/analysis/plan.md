# Phase 11.35: debug-only kernel switches and the three hardware questions that waited for them

Scratch, gitignored, written 2026-11-09 04:3x before the first run. Nothing staged or committed in the
worktree; nothing written under `~/src/resgx545`, `~/src/resgx545-fw`, `tools/rewrite/`, `p1132-overlay` or
`p1134`. Questions read: Q066, Q045, Q076 (landed, `~/src/resgx545/questions`), the section "what ran" of
`p1134/plan.md` (disclosures 8 and 9), the kernel sub-phases 11.17 and 11.19 (kit layout, `forks.toml`).

## 0. The kernel series (scratch clone `p1135/fork` of `p1129/fork`, base 3d9b8bdefe94)

| commit | subject | what it gives |
|---|---|---|
| 46 | drm/gma500: add a kpoke space for a render's background object | `bg:N=V`, `bg:N^=V`: word N (0-16) of the object, at the next render's kick (Q066) |
| 47 | drm/gma500: let debugfs render_keep keep the next closed render ctx | the next render context closed keeps its mappings, slot and memory (Q045) |
| 48 | drm/gma500: add debugfs render_kept to read a kept context's TA data | read the kept context's TA data, the state page included (Q045) |

All three behind `CONFIG_DRM_GMA500_SGXFIVE_DEBUG`; no clock-gate register, no register write path
added or extended (no `kreg`, no `kregnow` change); the own-task verifier untouched. Q076 needs no kernel
change: the client directory is word 2 of the render context's HW context (`SGX_RENDER_CTX_PD`), which
debugfs `render_words` has shown since 11.17 as `ctx:2`; p1134 disclosure 9 (the comparison "was not
possible") was wrong about that: the debugfs `layout` shows the EDM's directory, `render_words` the
client's.

## 1. Declared before any run (declared.tsv, predictions-declared.tsv, hashes.txt)

Sets as in p1134: fit, heldout, control, explore (`?`: no outcome can fail it).

- Q066, script bg-words (161 jobs, 64x64, every pixel printed, `--dump-render` keeps the object as the ISP
  reads it). H66-E: words 0-2 of the object are written by the EDM at the kick (E162), so a poke there is
  lost (image = control, the object's word is the EDM's). H66-N (the null for the six zero words 3-8): the ISP
  does not read them, every flip leaves the image as the control's. H66-V: coordinate bits that move an
  edge by a pixel or more of the vertex words 9-16 change the image; fraction bits and the unused words are
  `?`. A poke is checked in the dump: the word reads what was poked (words 3-16) or does not (0-2).
- Q045, script keep-closed (15 jobs): `tri -n 1 --ctx2 --close-first-early` with the first context's render
  flags flipped by 0x0, 0x4 or 0xc and `render_keep` armed (or not), the first context's state page (page 3
  of a 64x64 context's TA data) optionally filled with a ramp before its render. H45-K: with the closed
  context's mappings and memory kept the second render is exact (E458's fault needed the mapping gone);
  the null H45-F: it still faults. H45-S: the slot step stores the kept owner's DPM state into the kept
  state page (the page then differs from the ramp); H45-N (null): the page equals the ramp.
- Q076, script dirs (15 jobs): the PD word of the newest render context (`render_words ctx:2`) against
  `CR_BIF_DIR_LIST_BASE1..15` (0x0c38..0x0c70 of debugfs `regs`) read 2.5 s into a render, regtimeline on
  0x0c00-0x0c8c beside. H76-D: after a reset the first kick of a VM writes it into list 1 (E360), not
  list 15. H76-L: the k-th process's context since the reset has it in list k. H76-S: two contexts of one
  VM have the same PD, in lists 1 and 2. H76-P: a partial render (1024x768, 0x28 pages) under alias_skip
  masks 0, 0xc0 and 0xdc0 still has it in list 1.

## 2. Outcome rules, recompute, safety

A job completed (`tri: N renders ok`) or failed; a failure is followed by a debugfs reset and the health
triangle (64x64 exact, one retry after 5 s; three failed recoveries abort the script). Raw outputs, dumps
gzipped with raw sha256; `recompute/recompute_p1135.py DIR` reads only the kept files and the declared
tables. Every case has a distinct marker (the poked value, the ramp, the kernel log marker); no case is
scored by a model fitted to it. No register is written by any script (no kreg, no kregnow): so no clock-gate
register. Risky cases last, one script a question: bg-words (the zero words last), keep-closed (the 0xc
cases last), dirs (the partial render last). Reset only through debugfs; no reboot.

## 3. Hashes

hashes.txt (written 2026-11-09 04:31, before the first run): declared.tsv, predictions-declared.tsv, the
three tables, the generator, the run scripts and the recompute. The run scripts and the recompute are
disclosed below if they changed after that.

## 4. Disclosures written before the runs (more at the end)

1. Pilot of the dirs script on the old module (5AD04F33, no new switch; 04:33-04:35, three jobs: d76-one-1,
   d76-ctx2-1, d76-part-0x0-2 with the first form of the script) to see what the tool prints. It showed the
   PD word of the context in list 1 (BASE1) in 3 of 3 jobs and BASE2 empty in the ctx2 job. Those three
   pilot jobs are not data: the real run repeats every case on the installed new module, and H76-D, H76-S
   and H76-P are therefore not blind any more (the pilot ran before the first real job; the declared files
   were written before it).
2. The first form of run_dirs.sh read render_words and regs from the shell 2.5 s into the run; the tool's
   context is gone by then (the process ends after its renders), so the script now uses the tool's own
   `--words DIR` (render_words after each render, the context alive) and `--regs 0x0c34-0x0c74` (a snapshot
   before the first render and after each). run_dirs.sh and recompute_p1135.py changed after hashes.txt was
   written; their new hashes are in hashes-changed.txt. The declared tables did not change.
3. Pilots of bg-words (2 jobs: a control and a poke bg:0 the old module refused, rc 1) and of keep-closed (2 jobs on
   the old module: keep-0 exact, and the nokeep-c case, which faulted at 0x200030c1 with BIF status 0x90004 as E458
   did) ran at 04:34 to 04:43 to see the tool's output; they are not data (old module, no kernel switch).
   recompute_p1135.py's decoders were adapted to that output (the exact test of keep-closed reads "tri: 1 renders
   ok" and the `tri2` line) before the real runs.

## 5. Follow-ups, declared after earlier runs and before their own (hashes-followups.txt)

- bg-words-f1 (8 jobs), declared 05:11 after the first bg-words run (161 images the control's): the whole object at
  once (words 3-16 all 0xffffffff, all 0, word N = 0xa5000000 + N, two jobs each, two controls). H66-Z.
- keep-partial (8 jobs), declared 05:11 after keep-closed: a partial render's state page, a solo first context and a
  first with a second context, flags 0x4 and 0xc. H45-P. Its premise failed (see 6.3).
- keep-pages (6 jobs), declared 05:17 after keep-closed and keep-partial: a ramp in page 1 or page 2 instead of
  page 3. H45-W.

## 6. What ran (written 2026-11-09 05:3x, sections 1 to 5 are as declared and are not edited)

Laptop clock, one run each, in the order dirs 05:00:51-05:02:21 (15 jobs), keep-closed 05:03:26-05:06:08 (15),
bg-words 05:07:18-05:10:11 (161), bg-words-f1 05:12:13-05:12:21 (8), keep-partial ctx2 rows 05:12:58-05:14:17
(4, see 6.3), keep-partial solo rows 05:15:29-05:16:04 (4), keep-pages 05:17:52-05:18:50 (6): 213 job runs on
the module 34729EB82083B1D04B0643E (installed and loaded equal at the start of every script, loaded 04:59:38 from
the series' tip da1eaeaa1247), stock firmware, own_arm off, tool sgxfive-test-1126 (sha256 751f7223...600f82e),
regtimeline 079f6359... (dirs only). No script wrote a register (no kreg, no kregnow). A 64x64 triangle drew
exactly before the first script and after the last (health), no script printed a health failure line, none
retried, none aborted; 2 jobs faulted (the two keep-closed controls without keep: the fault of E458 at 0x200030c1
with BIF status 0x90004, recovered by the script's debugfs reset); no freeze, no watchdog reboot (laptop uptime
1 day 5:49 at the end, the boot of 03:xx the day before).

### 6.1 Disclosures
1. The pilots of section 4 (items 1 and 3) ran on the old module before the real runs.
2. run_dirs.sh and recompute_p1135.py changed after the first hashes (hashes-changed.txt); run_keep2.sh changed after
   its follow-up hash (ONLY filter, --close-trace only with --ctx2: the first form made the four solo rows exit 2, tool
   usage error, no hardware; those four rows were rerun as keep-partial-solo with the fixed script, the four ctx2 rows
   of the first run are keep-partial-ctx2).
3. keep-partial: the tool does not render the second context after an overflowed first render ("tri: closing the second
   context before the first", 0 of 1 renders ok): in the four ctx2 rows the kept context was the second, never
   rendered (kernel log: slot 1), so H45-P is not tested and the four rows are not scored ("not-run"); the solo rows
   read the kept first context. A tool option would be needed (the tool is unchanged).
4. The dmesg lines of the scripts after each case are not scoped to the case (they repeat older faults): the journal of
   the script (kernel.log) is. The "SGX recovery failed: -19 / job N hung, recovery held" lines of the journal since the
   install are the module-load KUnit's (logs/modload-kernel.txt, 14 suites ok, kpoke 32 of 32, NULL device).
5. No positive control exists for "the ISP does not read the words 3-16": every word of the object the ISP reads
   (0 to 2) is rewritten by the EDM after the poke, so a poke that changed the image could not be shown for the
   same memory; the poke reaches the object (read back in the post-job parameter dump), the same pointer, mapping and
   barrier as the kernel's own words.
6. bg-words: H66-V's per-bit predictions (written from the vertex encoding) missed in 34 of 34 scored cases; they
   assumed the vertex words move the rectangle. The explore set (43 cases with `?`) is the cases the model gave no
   prediction for.
7. The kernel wiring (render_spaces w[BG], the close's keep, the reset's release, the debugfs files) was seen failing
   and working only on the hardware; KUnit has the pure parts (red/green in logs/red-green.txt; 48's first run was a
   compile failure only).
