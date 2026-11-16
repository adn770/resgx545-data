# r30-pde

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 42c4de7855d6 (data 2da506767cf6), module
srcversion 7CE8E38EDB97FC5EA4F6C90 (the linux fork's branch r30-kernel, 8bc0877e8603: to be
installed and booted with the user's OK; not loaded when this was built), laptop prefix `r30p`.
**FLAGGED**: a safe reference stage, then four flagged stages of planned faults (the user approved
the full flagged session of closing29/kernel/plan-kernel.md 2.3, N-4 a, 2026-11-16). Records
reserved: **E1117, E1118, E1119**. Question: **Q109** (bif, low; E021, E151).

## Why

Q109 asks whether a page directory entry whose size field (bits 3:1) names 16 KiB to 4 MiB
translates, with which address mask and which table layout, and what the BIF reports for a size
field it does not take. No run has used a code other than 0. The fork's debugfs `vm_pde_addr`,
`vm_pde_size` and `vm_pde_layout` map a VM_MAP of exactly 4 MiB at the address through a PDE of
that code over a naturally aligned region of contiguous pages the driver owns, its table laid out
dense, misalign or ptoff, every 4 KiB but the table page tagged (`0xa0000000 | slab << 24 | page
<< 12 | dword`); debugfs `vm_large` reads the table and the tags back. t30's `copy --src-addr`
reads such a slot and names, by the tags, the region page each 4 KiB came from (`tags:` lines);
`fill --dst-addr` writes it, and `vm_large` names the pages it changed.

## What runs

Every row is t30 (sgxfive-test of main 42c4de7) running one 64-pixel-wide copy or fill at the
tool's default stride of 256 bytes (16 rows a 4 KiB page), aimed at the slot 0x60000000 (debugfs
vm_pde_addr in the rows that set it; a 4 MiB slot of the general heap, >= 0x60000000), with
`--large-copy "$W"` (vm_large kept as NAME.vm_large.txt). Every row's window in the slot lies in
the fork's KUnit safety windows (HACKING.md "Known tool weaknesses": code 0 [0, 16K) and [4M - 8K,
4M); codes 1-4 [S - 8K, S + 8K) and [2S - 8K, 2S + 8K); code 5 [4M - 16K, 4M); codes 6 and 7
[16K, 32K) read only), tests/test_gen.py holds it, with pde.union: under every reading the safety
case checks, each 4 KiB reached is in the region and a written one is never the table page.

| stage | class | rows | jobs | `#limit` | what |
|---|---|---|---|---|---|
| s0 | safe | s0-warm; 4 controls x 2 | 9 | 0 | references (below) |
| f1 | flagged | codes 1-3 dense: copy a (fit), copy b, fill (held out) | 9 | 6 | clause 1, the index |
| f2 | flagged | codes 1-3: misalign copy, ptoff copy (held out) | 6 | 4 | clause 2, mask and offset |
| f45 | flagged | code 4 (1M) as f1 and f2; code 5 (4M) dense a, b, fill | 8 | 6 | the 4 MiB regions |
| f67 | flagged | codes 6, 7: one copy each, then each again | 4 | 4 | clause 3 |

36 jobs, at most 20 planned faults (the `#limit`s, which count the faults and recovered hangs of
`expectfault` rows; no control expects one). In run order:

- **s0** (safe). `s0-warm` first, right after the boot: vm_pde_size 5 maps the slot over a 4 MiB
  region (order 10) while its copy (`--src-addr 0x5ffff000 --height 16`) reads only the page
  before the slot (the source buffer's guard page reaches into the slot, the copy never does);
  the region then sits in the module's pool (up to 12 MiB, kept until the module goes) for every
  later order-10 row. It is `soft`: an -ENOMEM refusal at the map voids it (f45 and f67 are then
  gated off). The controls, twice each: `s0-pcopy` and `s0-pfill` with the knobs off (a plain
  buffer at the slot: exact, vm_large `none`); `s0-kcopy` and `s0-kfill` with vm_pde_size 0 (4 KiB
  entries over the tagged region: the copy's tags `1:0,2:0,3:0,7:0` and the fill across the slot's
  end into the next, 4 KiB-mapped one changing only the trap page `7:0`, 2048 of 4096 pixels not
  written in the buffer, the table intact). These can fail: the decoder, the tags, the read-out
  and the knob path are all in them.
- **f1** codes 1-3 (16K, 64K, 256K), dense table: copy a over large page 0's end into page 1
  (fit), copy b over page 1's end into page 2 and the fill over page 0's end (held out).
- **f2** codes 1-3: the misalign copy (entry k = block k + 4 KiB) and the ptoff copy (the real
  table at + 0x400, named by the PDE's bits 11:4, a decoy naming the blocks rotated at + 0), over
  page 0's end into page 1, held out.
- **f45** the order-10 regions: code 4 (1M) a, b, fill, misalign, ptoff; code 5 (4M) dense: copy a
  [4M - 16K, 4M - 8K) fit, copy b [4M - 8K, 4M) and the fill [4M - 16K, 4M) held out. Rows `soft`
  (an -ENOMEM voids one; two in a row stop the stage and end the session).
- **f67** last: the unnamed codes 6 and 7 (copies only, [16K, 32K)), c6, c7, then c6, c7 again.
  `soft` (order 10).

Deviation from plan-kernel.md 2.3: its f1 (codes 1-5) and f2 (codes 1-4) are split by region
order, so that an order-10 allocation that fails cannot cost the smaller codes: f1 and f2 take
codes 1-3, f45 code 4 and 5, gated on s0-warm's 4 MiB region; its f3 is f67. Its total (35 jobs,
20 planned faults) is now 36 jobs (s0-warm) and the same 20. The plan's pt4k layout is not used.

Time: about 10 to 15 s a job with the reset and snapshots, more after a fault (strict health):
about 10 minutes of jobs, 15 to 20 with staging [infer]. Alarms 900, 900, 600, 900, 600 s.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py)

The readings (gen/pde.py, the fork's `sgx_mmu_large_phys`): H-DENSE (entry va / S, its address
masked to S), H-4K (the size field ignored: entry va / 4 KiB), H-MASK4K (entry va / S, its address
used to 4 KiB), H-SECTION (the PDE names the data, no table), each with or without the table
offset of the PDE's bits 11:4; and H-FAULT (end fault). Each copy's reading is its `tags`, the
region page of each 4 KiB in VA order; each fill's is `changed`, the region pages it changed.

- **Clause 1, each larger size translates** (f1, f45 dense rows): frozen **H-DENSE** for codes
  1-5, against H-4K, H-SECTION and H-FAULT [infer: the CE headers name the sizes, hw_spec section
  4]. Fit: copy a; held out: copy b and the fill. Per code the verdict is `translates`, `faults`,
  `as 4 KiB` or `as a section` when one model held on the code's three rows. Code 5's one block is
  the region, its first page the table page, so H-DENSE and H-SECTION name the same 4 MiB there.
- **Clause 2, layout and address bits** (f1, f2, f45): the index is clause 1's H-DENSE against
  H-4K; the mask: frozen **H-MASK-S** (the entry's bits below S ignored) against H-MASK4K; the
  offset: frozen **H-PTOFF-IGN** (bits 11:4 ignored, the table at the PDE's page: the decoy is
  read) against H-PTOFF-USE (H-4K and H-4K-PTOFF, H-SECTION as rivals) [infer: the CE headers' PDE
  address mask 0xfffff000]. Decided when one model held on every such row of every code that
  translates; moot when no code translates and each has its clause 1 reading.
- **Clause 3, a size field the BIF does not take** (f67): frozen **H-FAULT** (a fault with the
  kernel's `BIF fault S at A` line, the same S both times; or a stall the kernel recovers as a
  hang, both times), against H-ALIAS (taken as any size but 16 KiB, or as 4 KiB entries: region
  pages 4-7) and H-ALIAS16 (taken as 16 KiB: pages 0-3, the table page first). The BIF registers
  after the job (CR_BIF_INT_STAT 0x0c04, CR_BIF_FAULT 0x0c08 in the runner's snap9) are kept as a
  reading of every row.
- Controls: s0's eight (H-REF, exact keys, frozen from the fork's functions); each can fail.

`python3 score/score.py q109 out/ATT` prints the clause rule (score.py's docstring): **RETIRE**
when the controls passed, every code 1-5 has a clause 1 verdict, clause 2 is decided or moot and
codes 6 and 7 each a clause 3 verdict; else **NARROW**, naming what stays open.

## What retires

All three clauses can retire in one run: clause 1 per code from f1 and f45; clause 2 from f1, f2
and f45's code 4 (code 5 has no misalign or ptoff region, the fork refuses them); clause 3 from
f67. Q109 narrows instead if order 10 cannot be had (s0-warm voided: f45 and f67 gated off, so 1M,
4M and clause 3 stay open), if a `#limit` ends the session with rows left (codes faulting: up to
6 in f1, so codes 1 and 2 faulting fully leaves code 3 unrun), if a gate closes, or if f67 wedges
the recovery.

## Stops

- s0: any fault or hang (no expectfault: rc 4), a control without its reading (25), a hook_check
  reason (24): the session stops; a closed s0 gate skips every flagged stage.
- Each flagged stage is gated (score.py gate: s0's eight controls passed; f45 and f67 also
  s0-warm's H-WARM; no `SGX recovery failed` kept earlier) and declares `on_stop = "end"`.
- hook_check, after every row that ended ok: `job: ok`, a `diff:` line and vm_large.txt; with the
  knobs off vm_large `none`; with them set the kernel's `PDE size code C layout L` vm_map line,
  vm_large naming the slot, code and layout, **the table page intact**, a copy that changed **no
  page** of the region, a fill that changed at least one and **only pages some reading reaches**
  over its window (gen/allowed.tsv, pde.union): else the GPU wrote where no reading puts it, the
  module is suspect, and the session ends.
- hook_fault, after every planned fault (after the kit's reset and strict health): any `SGX
  recovery failed`; f1, f2, f45 a fault without the kernel's BIF line or a hang (they plan
  faults only); f67 a fault without its BIF line or a hang without its `hung, recovering` line.
- The kit's own: an unexpected fault (4), strict health failing (16), a FATAL kernel line (3), a
  knob not reading back (19), the `#limit` with rows left (24, `## not run (limit)`).

## Tool

t30 is not on the laptop yet. `bash lead/build_tool30_laptop.sh` (the lead, Mac, travel cable)
builds it from main 42c4de7 on the laptop (t24's recipe: bundle, `make CC=gcc
build/sgxfive-test`, `make check` with 0 failures) and prints its sha256 and FROZEN.commits line.
**The freeze waits for it**: session.toml's `[tools.t30] sha256` is the placeholder 0 x 64 until
then. `bash lead/finish_freeze.sh` runs the build, writes the sha256 into session.toml and the
built line into lead/TOOL30.built, then `bash tests/run_all.sh`, the freeze and run_all again
(tests/test_gen.py refuses a freeze of the placeholder). Health stays on t10 (9bedc2d6...).

## Mock worlds

`model`, `alt`, `layout`, `f67hang` (0 everywhere), `faultall` (f1 limit, 24), `nowarm` (f45 and
f67 gated off, 0), `enomem45` (f45 24; the kit reads an all-voided stage's empty cases.tsv as a
file not kept: driver 43), `s0kdiff` (gates closed), `s0fault` (4), `nolarge` (23), `outside`,
`copychg`, `recovfail`, `f1hang` (f1 24), `tablechg` (f2 24), `nobifline` (f67 24). The library
mock replays all 36 rows of t30 with their knobs (none refused). tests/test_score.py replays the
scorer and the hooks on attempts written from the worlds: RETIRE on model, layout, alt and
f67hang; NARROW on s0kdiff, faultall and nowarm; hook_reading equal to score.py's reading.

## Replay vectors

None: closing_tables.py has no kind for an MMU translation, and sgx-sim has no page-size model.
Every stage is **refused** as a table. The fold adds a crates/SIM_UNMODELLED.toml entry for the
PDE size field (or a model, test first, if the readings make one), from the kept vm_large.txt and
the `tags:` lines, which hold everything it needs; the tool source is pinned.

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify once frozen).
  Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Tool and freeze: `bash lead/finish_freeze.sh` (or `bash lead/build_tool30_laptop.sh`, then by
  hand). Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; Q109: `python3 score/score.py q109
  out/ATT`.

No firmware-derived file: nothing here goes to data-private.

Every command is run through its interpreter, never by its mode bits; Python is the repo's own,
`$HOME/src/resgx545/.venv/bin/python`. The driver keeps its own logs, `out/stage.log` and
`out/ATTEMPT/run.log`; tee nothing into this directory's top.
