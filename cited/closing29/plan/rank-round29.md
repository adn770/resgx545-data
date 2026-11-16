# Round 29 plan: the flagged rows (user present, planned faults and recovered hangs)

Planner, offline, read-only. Inputs: `closing29/BRIEF-COMMON.md` (round 29 section),
`closing27/plan/rank-round27.md` section 4 (the 11 rows), the question files under
`/Users/jtorra/src/resgx545/questions/`, records to E1107 (main c057181), the worked examples
`closing18/r18-flag` and `closing19/b/r19-flag`, the kit header `tools/closing/kit/run_stage.sh`,
the tool source `userspace/libsgxfive/tools/sgxfive-test.c` and `include/sgxfive_tri_probe.h`,
and the kernel fork `/Volumes/linux/linux-sgx` branch resgx545 456404fcffe5 (read only:
`sgxfive.c`, `sgxfive_debug.c`, `sgxfive_sched.c`). Records reserved from **E1108**.

## 0. Summary

- Of the 11 rows, **6 have a decidable flagged outcome** today (Q108, Q139, Q241, Q112, Q010,
  Q163); **5 are dropped** for this round (Q040, Q046, Q036, Q069, Q195; reasons in section 2).
- Only **Q010 can retire**: its one open clause ("what clears the colour-space set between jobs")
  is a fork read plus one reading after a recovered fault and two after recovered hangs. Every
  other kept row narrows a medium or low question that keeps other clauses.
- One session, **r29-flag**: s0 (safe references) then f1 to f4 (faults) then h1, h2 (hangs).
  **Planned: 8 faults and 5 hangs (13 events)**; the `#limit`s cap the events at 14 (8 faults,
  6 hangs). About 39 jobs, **about 22 minutes, 30 at most**. Tools t10, t14, t22 (all on the
  laptop); no tool build, no kernel change, no boot, no clock-gate write, no held reset.
- Two stages (f3, h2) need an offline fit first (O29-1, O29-2); each is built only if its fit
  freezes a form and a rival (R29-2). Without them: 6 faults and 2 hangs.

## 1. The rows, verified against the question files and the last records

Notation: H- frozen hypothesis (predicted first), rivals after; "planned" = the frozen hypothesis
says it faults or hangs; every row any hypothesis says faults or hangs is `expectfault`.

### Q108 (bif, medium; last E1071): the flags together on a read (stage f1, 2 faults, t14)

- Open after E1071: data cached within one render, the flags on the TA's own writes and the EDM's
  buffers, **the flags together on a read**, which unit makes WRITEONLY's last-page access.
- Decidable now: only "together on a read". The fork's `vm_pte_flags` acts on a user `VM_MAP`
  only (`sgxfive_debug.c`, the knob's comment), so the TA's and the EDM's buffers need a kernel
  change (not this round). Decides: narrow (Q108 keeps three clauses).
- Kept data: E965 (both flags on a colour *write* fault as EDMPROTECT alone, 0xa0020 at the first
  page); E1071 (on a *read* WRITEONLY alone faults at the first page, 0x80200 load, 0x80002
  texture; EDMPROTECT alone lets both through).
- Rows (r18-flag f2's forms on t14, knob `vm_pte_flags=0x12`, the fork accepts 0x2|0x8|0x10):
  `q108-both-load` (rf-c-depth's ZLS load, depth buffer 0x3e001000) and `q108-both-tex`
  (f1-ref-a's texture read of the scratch 0x3e003000).
- Frozen: **H-WO-READ** (the read faults as WRITEONLY alone: 0x80200 and 0x80002 at the first
  page, `FAULT_TYPE` 0) [infer: EDMPROTECT never stops a read, E1071]; rivals **H-EDM-TYPE**
  (EDMPROTECT's type takes over as on writes, E965: 0xa0200, 0xa0002) and **H-PASS** (both
  complete with E1046's store and E1047's image). Planned 2 faults (H-PASS: none); `#limit 2`.
- Controls that can fail (s0): rf-c-depth (E1046's store byte for byte), f1-ref-a (E1047's
  image). Risk: low (four such faults in E1071, all recovered at the first try).

### Q139 (ta, medium; last E1074): the page of the TA's empty-axis write (stage f2, 2 faults, t10)

- Open: what places the TA's write at TA data page 0x20008, the stride's relation to the RT
  data, the kind at four macrotiles a side. Decides: narrow (the stride clause stays).
- Kept data (E1073 fold of E509, E1074): 0x90004 pages by case: x-side empty axis 0x20008 at
  256 x 256 (n = 2, module 14D09986) and at 384 x 256 (n = 2, E1074, module B60AB0B4), 0x2000a
  at 640 x 480 (four columns); y-side empty axis 0x20010 at both 256 x 256 and 640 x 480; stride
  256 at 640 x 480 0x2000a. So the page is not the layout's end (E1074's H-PAGE-END failed) and
  differs by axis at one size [post hoc].
- Rows (E1074's form, `--kpoke-render 1:ta:143=V`, `--dump-render "$W"`): `f2-x512`, an x-side
  empty word at 512 x 256 (n = 2: the builder confirms n with sgx-pipe's `ta::macrotile_slots`
  and picks 448 x 256 if 512 is not n = 2), and `f2-y384`, a y-side empty word at 384 x 256.
- Frozen: **H-AXIS-N** (the page is fixed by the axis and n: x-side n = 2 0x20008, y-side 0x20010,
  whatever the size) against **H-SIZE** (the page moves with the TA data's size at the new size:
  the builder writes its value from the size's baseline TA data length, s0) [infer, weak]. The
  kind (0x90004) is E1073's H-KIND again on both rows (a third and fourth held-out word).
  Planned 2 faults; `#limit 2`.
- Controls (s0): f2-ctl-256 (E1048's hash, 24576 bytes TA data) and a new `c-512` baseline (the
  512 x 256 job unpoked: job ok and its TA data length, the reading H-SIZE's page needs).
- Not this round: "the kind at four macrotiles a side". The decisive row is an empty axis at a
  four-column size, and E509's three such 0x90004 faults at 640 x 480 each failed their health
  triangle twice before one drew (E1073; r18-flag README deviation 3): under the kit's strict
  health that is a predicted session stop (16). See R29-4.

### Q241 (isp, low; last E1072): which word gives bit 18's fetch address (stage f3, 2 faults, t10)

- Open: bit 15's 48 pixels, bit 18's fetch, the visibility counter, the offset's units, pass
  types over several triangles, the gate pairs. Decides: narrow (one clause of six).
- Kept data: E1072 (bit 18 alone faults the library triangle and E977's ramp alike, 0xd0400 at
  `BIF_FAULT` 0x1: page 0, `FAULT_REQ` bit 10, `FAULT_TYPE` 5, the requestor of E764's background
  program fetch).
- **O29-1 (offline, before the build):** list the words of E1072's two jobs that could carry the
  address (the state block words of `include/sgxfive_tri_probe.h`'s layout whose address field is
  0, and the render details the 3D kick writes, `--kpoke-render 1:rd:N`) from the tool source and
  E1072's kept outputs; freeze at most two candidates by name and the address scale of each (the
  stream's own address words are `addr >> 4` in bits 27:0, `src/render.c`).
- Rows: `b18-wA`, `b18-wB`, E065's job with `--poke blk:1^=0x00040000` and the candidate set to a
  marker page no mapping holds (the builder checks the layout: a page below 0x10000000).
- Frozen: **H-WORD-k** (the fault page is the marker's) against **H-ZERO** (page 0 whatever the
  word). Planned 2 faults (both hypotheses fault); `#limit 2`.
- Controls (s0): x-ctl (E998's, E977's kept dump and hash) and `c-lib-wA`, `c-lib-wB` (the library
  job with each candidate poked and bit 18 clear: E065's image, or the gate closes: a candidate
  that changes the image is no clean address word). If O29-1 finds no candidate, f3 is not built
  (R29-2).

### Q112 (vdm, medium; last E1075): where bit 25's 0xd0008 address comes from (stage f4, 2 faults)

- Open: what bit 24's hang waits on, the fault word 0xd0008, any field that makes the TA read
  wider indices. Decides: narrow (0xd0008 only).
- Kept data: E737 (bit 25 faults 0xd0008 at 0x1, 4 of 4), E756 (the same over a 32-bit list).
  `BIF_FAULT` 0x1 is page 0 through list 1; `FAULT_REQ` bit 3 is the TA's stream read (hw_spec
  5.5, 0x80008/0x90008). The index list (`src/render.c`): word 2 header, word 3 base, **word 4 =
  0xf0000000** (VDM_INDEX2, address bits 27:0 all zero), word 5 0x003fffff, words 6 and 7 the
  vertex task. Word 4 is the only list word whose low 28 bits are 0 [infer: the address bit 25
  makes the TA read].
- Rows (E737's form on t10, `probe --tri pixel --vertices 15 --copy-depth --pixels`,
  `--vdm 2^=0x02000000`): `d8-w4a` with `--vdm 4=0xf0a5a000`, `d8-w4b` with `--vdm 4=0xf05a5000`
  (bits 27:24 kept 0: they are Q042's).
- Frozen: **H-W4-S4** (word 4's bits 27:0 shifted by 4: pages 0x0a5a0 and 0x05a50), **H-W4-S0**
  (unshifted: pages 0x00a5a and 0x005a5), **H-ZERO** (page 0 both). Both rows fault under every
  hypothesis: planned 2; `#limit 2`. The fold checks the markers are unmapped from the layout.
- Control (s0): `c-ix-w4`, E414's job with word 4 = 0xf0a5a000 and bit 25 clear: E414's object
  (ix-c's o0 line); a changed image closes f4's gate.
- Not decidable here: what bit 24's hang waits on (no frozen form; a hung job's registers are read
  only after the recovery's reboot, E1034's kept dmesg). Bit 24's hang is reused as Q010's hang.

### Q010 (texture, low; last E399, with E1097 and E1103): what clears the set (f1 + h1, 2 hangs)

- The question line keeps one clause: what clears colour-space set 0 between jobs, given E271's
  first job after hung jobs converted with zeros. E1103 (r25-csc): a fill or copy with the load
  flag loads the set, a job without it keeps the last loaded set, across the runner's debugfs
  reset (E1097, E1103) and a 5 s idle (E399). **Can retire** (R29-3).
- Fork read (this plan): debugfs `reset` calls `sgxfive_recover(..., SGXFIVE_HANG_MANUAL)` with no
  suspect (`sgxfive_debug.c`), which `sgxfive_blame` treats as a hang, so it runs the same
  `sgxfive_reset` a hang (`SGXFIVE_HANG_TIMEOUT`, `sgxfive_sched.c`) or a fault
  (`SGXFIVE_HANG_FAULT`, `sgxfive.c`) runs: halt, `sgx_fw_build`, boot. E1097 and E1103 kept the
  set across it. So H-KEEP is predicted [infer]; the open difference is only the GPU's state when
  the halt comes (hung or faulted, not idle).
- Rows (copies on **t22**: before t22 the copy's poke set was a dangling pointer, HACKING; E1103's
  forms: `copy --every-value --pixels`, `tex:1=0x7d03f01f`, `tex:0^=0x90`, load with
  `xfer:17^=0x1` and xfer:18-22 the BT.601 words or zeros):
  - s0: `c10-zc` (load zeros: black 0xd3522437a14b6325), `c10-zn` (no load: black), `c10-bc`
    (load BT.601: 0xb6067a95fa98de2d), `c10-bn` (no load: the conversion): four controls that can
    fail, each hypothesis' reading shown reachable.
  - f1: `q010-ld` (load BT.601, control) first, after Q108's two faults `q010-af` (no load).
  - h1: `q010-ld2` (load, control), `q010-pre` (no load after the kit's reset, control:
    conversion), `q010-h1` (bit 24 hang, E737's form on t10, `expectfault`), `q010-p1` (no load),
    `q010-h2`, `q010-p2` (replicate).
- Frozen: **H-KEEP** (each no-load copy after a recovery reads 0xb6067a95fa98de2d) against
  **H-RECOV-CLR** (0xd3522437a14b6325). Planned 2 hangs (h1), 0 extra faults (f1 reuses Q108's);
  h1 `#limit 2`.
- Retire rule (R29-3 a): s0's four controls and h1's two pass, and the three held-out copies read
  one hypothesis. Under H-KEEP the answer is "no job, idle, reset, fault or hang recovery clears
  the set; E271's zeros were a set not loaded since the module loaded [infer]".

### Q163 (vdm, medium; last E1076): what decides block-2 v = 1 (stage h2, 3 hangs, t10 noreset)

- Open: what decides block-2 v = 1 (hung at c = 0, 2, 5 in E1035; completed at c = 3 and 8 in
  E545's grid and E701), v = 0 (block 1 below c = 4), what the counter is. Decides: narrow (the
  counter's identity stays).
- **O29-2 (offline, before the build):** on every kept block-2 v = 1 and v = 0 job (E545's two
  scripts, E701, E1021's re-read, E1035), fit at least three deciders (M1's c, the grid's bits
  7:0, the previous job's v and outcome) with E1035's rows held out; freeze the best and one
  rival, as E700 did. Build h2 only if one fits E1035's 3 of 3 and E701's c = 8 completion.
- Rows (r18-flag h2's form: E700's shape, `--vdm 1^=...`, `noreset` after the first row): three
  sequences of three, each from a reset, block 2 at v = 1 placed at the c values O29-2's two forms
  part (one of them c = 8, E701's lone completion, held out). Control first: E700's shape at
  v = 6, v = 6 (both complete under M1; a hang there stops the stage, 4).
- Frozen: O29-2's form against its rival; planned 3 hangs, `#limit 4` (a rival's hang row).
- Kit: `noreset` (only after an ok row or an expected hang), `idle:S` unused.

## 2. Rows dropped this round (no decidable flagged outcome)

| row | why not | what would make it decidable |
|---|---|---|
| Q040 | E266 ran all 256 counts: every odd one hangs. More hangs decide nothing about *why*; the open clauses (bits 6:0, bit 30, counts above 0x80) are **safe-class** rows that need a shader naming its output registers. | a safe session with that shader (no flag) |
| Q046 | Mapped offline here: page 0x37001000 is `HEAP_PIXELSHADER` (0x37000000, fork `sgxfive.c` `sgx_heap_base`) + 0x1000, the page after the one holding the probe's own programs (the tool's `--place` doc), unmapped in a tri probe. Parting "next page past the code" from "a fixed address" needs that page mapped, and `--place` is a fill-probe option. | a tool change: tri with a second mapped pixel-heap page (laptop build about 1 min, new binding) |
| Q036 | E463: after a base-only fault the next two jobs fault whatever they are, so the kit's strict health fill and triangle would be those jobs: a predicted stop (16 or 5). Five other clauses stay. | a kit word that defers strict health over a planned chain |
| Q069 | `--blk-add` takes bits 2-5 and 7 only (`sgxfive-test.c`); bits 16-31 need a tool change. Two other clauses (the 0.6 scale and bend, OUTSEL 13) stay. | the tool change, then a flagged stage |
| Q195 | `tools/fwtask/fwtask.py` refuses the narrow forms (unknown form): the verifier rows are offline repo work first; the fill clauses are safe class (E598, E599's form). | a tooling agent (verifier), then a safe fill session |

## 3. The session r29-flag (one session, kit fit)

Module E0CC40275493F8AEAD8180B (`--srcversion`), prefix `r29f`, tools t10 (rows and the kit's
health), t14 (f1), t22 (Q010 copies). Every flagged stage `gate = true`, `on_stop = "end"`.

| # | stage | jobs | planned | `#limit` | tool | rows | record |
|---|---|---|---|---|---|---|---|
| 1 | s0 | 12 | 0 | 0 | t10, t14, t22 | rf-c-depth, f1-ref-a, f2-ctl-256, c-512, x-ctl, c-lib-wA, c-lib-wB, c-ix-w4, c10-zc, -zn, -bc, -bn | (gates) |
| 2 | f1 | 4 | 2 faults | 2 | t14, t22 | q010-ld, q108-both-load, q108-both-tex, q010-af | E1108 |
| 3 | f2 | 2 | 2 faults | 2 | t10 | f2-x512, f2-y384 | E1109 |
| 4 | f3 | 2 | 2 faults | 2 | t10 | b18-wA, b18-wB (if O29-1) | E1110 |
| 5 | f4 | 2 | 2 faults | 2 | t10 | d8-w4a, d8-w4b | E1111 |
| 6 | h1 | 6 | 2 hangs | 2 | t22, t10 | q010-ld2, q010-pre, q010-h1, q010-p1, q010-h2, q010-p2 | E1112 |
| 7 | h2 | 11 | 3 hangs | 4 | t10 | control pair, three sequences of three (if O29-2) | E1113 |
| | total | 39 | **8 faults, 5 hangs** | 14 | | | E1108-E1113 |

(The builder drops c-lib-wB if O29-1 freezes one candidate.)

Kit fit, per stage (BRIEF-BUILD-KIT and `run_stage.sh`): s0 is safe (no `expectfault`, any fault
or hang stops, 4; a control without its reading stops, 25; a differing reading closes only its
stage's gate). f1 needs `[knobs] vm_pte_addr` (0x3e001000, 0x3e003000) and `vm_pte_flags` (0x12);
f2 `debugfs = ["render_param", "render_tadata"]`, `outdir_opts = ["--dump-render"]`; h2 `noreset`.
`hook_fault` (24, ends the session) on every expected event: any `SGX recovery failed`, a fault
stage's end other than a fault with its `BIF fault S at A` line, a hang stage's end other than
`job N hung, recovering`. `hook_check`: a copy or tri row ok without `job: ok`. Strict health after
every event is the kit's (16, 5). `#limit` counts `expectfault` rows that are not controls (E946).
`forbid_options` as r18-flag's (no `--fault`, `--refill`, `--kpoke-job`, ...). Nothing the kit
lacks for the kept stages.

Order and gates: f1 to f4 gated by their own s0 references; h1 by c10-bc and c10-bn; h2 by its own
control pair. Stop budget: zero unplanned events; any stop other than a clean finish ends the
session and is reported, never retried or rebooted.

Time: 26 non-event jobs at about 12 s (6 min), 13 events at about 50 s with the reset and strict
health (11 min), staging and seven preflights (5 min): **about 22 minutes**; with every `#limit`
used and two health retries about 30. Alarms: s0 15 min, f stages 10, h1 10, h2 15.

Replay vectors: `refused` for every stage (faults, hangs, PTE flags and the colour-space reset are
not modelled: SIM_UNMODELLED); the s0 references are kept records already replayed. If f1 reads
H-PASS the fold builds a `zls` load table from the kept store (as r18-flag f2's edm rows).

Offline parts (the builder, before the freeze): O29-1 (Q241 candidates), O29-2 (Q163 fit), the
512 x 256 n check (sgx-pipe), the marker pages' absence from the layout (f3, f4). Publishable:
everything (our tables, programs, scorer, fits; no firmware-derived file).

## 4. Risk

- Faults: f1 and f2 repeat forms that recovered at the first health try (E1071, E1074 at n = 2).
  f3 and f4 repeat E1072's and E737's faults with one word changed; a marker page that turns out
  mapped makes the TA or the ISP read our marker page as data [infer: then a fault elsewhere or a
  wrong image; `hook_fault` ends the session on a fault without its BIF line].
- Hangs: h1's bit 24 hang recovered every time (E737 2 of 2, E1075 1 of 1); h2's hangs are
  E1035's and E1076's kind (11 recovered, none failed).
- Class: flagged (planned faults and recovered hangs). No kernel change, boot, clock-gate write,
  held reset, firmware `str` or trc_hazard.

## 5. R29 decisions

1. **R29-1 Scope of r29-flag.**
   - a) The whole session: s0, f1-f4, h1, h2; 8 faults and 5 hangs planned, caps 14
     (recommended: under the ~20 the user allowed; one retirement, five narrowings).
   - b) Without f3 and f4 (the address-word rows): 4 faults and 5 hangs.
   - c) Q010 only (s0's four copies and h1): 2 hangs, the retirement alone.
2. **R29-2 Stages that wait on an offline fit (f3: O29-1; h2: O29-2).**
   - a) Build each only if its fit freezes a form and a rival before any data of the run
     (recommended: the brief's frozen-prediction rule; without them 6 faults and 2 hangs).
   - b) Build them with the rows listed here whatever the fit gives.
3. **R29-3 Q010's retirement rule.**
   - a) Retire when s0's four copy controls and h1's two pass and the three held-out copies
     (after the faults and after both hangs) read one hypothesis; the power-on state stays an
     [infer] in the answer (recommended: no boot is planned, and the question asks what clears
     the set between jobs).
   - b) Narrow only; keep a boot row (a no-load copy as the first job after a boot) for a later
     boot round.
4. **R29-4 Q139's four-macrotile empty axis.**
   - a) Not this round (recommended: E509's 640 x 480 faults each needed two health retries, a
     predicted kit stop).
   - b) Add it as the session's very last row (after h2), `on_stop = "end"`: +1 fault.
5. **R29-5 The dropped rows' changes (next tooling round, safe class).**
   - a) One tooling agent: tri with a second mapped pixel-heap page (Q046), `--blk-add` bits 16-31
     (Q069), the fwtask verifier rows for the narrow forms (Q195); Q036's kit word after that
     (recommended: each turns a dropped row into a decidable one).
   - b) Leave them on the morning list.
6. **R29-6 Q010's hang.**
   - a) E737's bit 24 hang on t10 (recommended: 3 of 3 recovered, and a third replicate of
     E1075's reading at no extra cost).
   - b) Q163's counter hang (E700's v = 6 triple): three jobs a hang instead of one.

**Planned events: 8 faults (f1 2, f2 2, f3 2, f4 2) and 5 hangs (h1 2, h2 3): 13; caps 14.**
