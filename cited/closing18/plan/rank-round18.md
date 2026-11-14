# Round 18 ranking: the flagged rows deferred "later, with the user" (Opus, 2026-11-14, user present)

Basis: resgx545 `main` 2c0fe18 (records to E1069), resgx545-data 45423fbc3, fork resgx545 2a650d74
(read only), laptop on module B60AB0B4 (one-shot boot), tools t4, t9, t10, t14 as built. Inputs
read: `closing18/BRIEF-COMMON.md`, the round 17 handover (Next item 4), the 2026-11-13/14 lines of
`plans/resgx545-question-closing.md`, the "later, with the user" sections of
`closing15/plan/rank-round15.md` (7), `closing16/plan/rank-round16.md` (7) and
`closing17/plan/rank-round17.md` (7), `BRIEF-BUILD-KIT.md`, r13-flag's f3 table and r14-flag's
README (worked examples), r14-bif's and r15-zls's tables (row forms), the question files of Q299,
Q108, Q163, Q241, Q046, Q139, Q036, Q040, Q112, Q195, records E065, E411, E991, E1034, E1041,
E1051, the BIF fault table of `doc/specs/hw_spec.md` section 5.5, the heap table of
`doc/specs/render_uapi.md`, and the tool sources at a581c06 (t10) and c58f9f9 (t14):
`sgxfive-test.c` (`scratch_create`, `--depth-pages`, `--place`), `src/dev.c` (`sgxfive_vm_alloc`),
`src/tri_probe.c` (the rig's pages). Kept data read: the case markers and BIF fault lines of
`resgx545-data/ta/mtile-fields{,-risky}/kernel.log` (E509's datasets, counted only), r14-flag's
f1-ref-a output header. Nothing staged, built or run; no laptop, SSH or cachix; no file written
outside this directory.

## 0. Honest summary

- **One row retires a question: Q299** (E411's store past its buffer). Two planned faults, t10, the
  r15-zls `zv-` form with `--depth-pages 16`. Q299's only open clause is "does it fault", and every
  outcome answers it, so a passing control is the only gate.
- **Five more rows narrow**: Q108 (WRITEONLY and EDMPROTECT alone on a depth load and on a texture
  read, 4 rows), Q139 (the fault kind and page of new faulting words, held out on an offline fit
  of E509's kept kernel lines, 2 rows), Q241 bit 18 (2 rows), Q112 bit 24 over a 32-bit list (1
  hang), Q163 on two new stream shapes (2 planned hangs).
- **Dropped**: Q046 bit 11 (needs a tool change: nothing a run reads today parts any rival), Q036's
  builder fault (a failed recovery is its predicted outcome), Q040 (no rival parts an odd-count
  hang), Q163 below v = 2 (no frozen form survives E1035), Q069, Q195, Q024 (tool or kit word
  first). Section 5.
- **Shape**: one session, r18-flag: a safe stage of references first, then four fault stages,
  then two hang stages. 26 jobs. **11 planned faults and hangs** (8 faults, 3 hangs); the
  `#limit`s allow **15** if rivals land (10 faults, 5 hangs). About 20 minutes of
  laptop time, 30 at worst. Records E1070 to E1076.

## 1. Every candidate, ranked (retire first)

"Retire" as R16-6 (a): every open clause decided by held-out rows with passing controls, the lead
confirming. Planned = rows that fault or hang under the frozen hypothesis; allowed = the stage's
`#limit` (every row a rival says faults or hangs is `expectfault`, so a rival outcome is not an
unplanned stop).

| # | Stage | Question | If it holds | Jobs (+ s0 ref) | Planned / allowed | Tool | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | f1 | Q299 store past a 16-page buffer | **retire** | 2 (+2) | 2 / 2 faults | t10 | ZLS write to an unmapped page; ZLS faults recovered in E965, E411 |
| 2 | f2 | Q108 WO / EDM alone on a depth load and a texture read | narrow | 4 (+2) | 2 / 4 faults | t14 + knobs | known fault kinds (E945, E946, E964) |
| 3 | f3 | Q139 why words fault: kind and page held out | narrow | 2 (+1) | 2 / 2 faults | t10 | TA header and parameter faults, recovered 168 times in E509 |
| 4 | f4 | Q241 bit 18: does it need a missing buffer, which requestor | narrow | 2 (+1) | 2 / 2 faults | t10 | fault kind unknown (E065, one run on an old fork): last fault stage |
| 5 | h1 | Q112 bit 24 over a 32-bit list | narrow | 1 (+1) | 1 / 1 hang | t10 | hang recovered 2 of 2 (E737) |
| 6 | h2 | Q163 the counter on two new stream shapes | narrow | 8 | 2 / 4 hangs | t10 | hangs recovered 8 of 8 (E1035) |

## 2. The rows

### f1, Q299 (E1070): does a ZLS store past its buffer fault the job? Retire-capable.

Form: r15-zls `zv-g5` (E1051, t10: `tri ... --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl
0x0017102c --depth-fill 0xdeadbeef --depth-dump "$W" --poke blk:1=0x00400200 --kpoke-render
1:rd:13=0xd000`) with `--depth-pages 16`, at G 3 (ctl 0x0017101c, as `zv-c-g3`) and G 5.

Premise [infer, from source]: t10's `scratch_create` maps exactly the pages asked for, the library's
`sgxfive_vm_alloc` is a bump allocator with no gaps, and with `--depth` alone (no `--depth-store`,
no `--stencil`) the depth buffer is the last GENERAL allocation, so the pages past it are unmapped.
E411's own tool (probes/zls, an older layout) is why its G 3 did not fault: something was mapped
past its buffer [infer; E1041 "does not show" what lay past page 15]. The builder checks the
premise with the tool's printed `depth:` address and the next allocation, if any, in the mock.

Frozen (E991's page rule, E1041's H-NEXTTILE at 20 pages, E1051's H-E465-EXT at 24):

- **H-PAST-FAULT**: a store reaching an unmapped page faults the job: G 3 at the buffer's page 16
  (tile rows 2 and 3 go to pages 16 and 18), G 5 at page 18 (pages 12 and 15, then 18); the
  kernel line names FAULT_REQ bit 9, the ZLS requestor of E965 (0x80200 / 0xa0200), with a
  FAULT_TYPE of an unmapped page [infer: 0x9xxxx as the unmapped rows of hw_spec 5.5], so
  0x90200 at depth base + 0x10000 and + 0x12000.
- **H-DROP**: stores past the mapping are dropped; both complete; pages 0 to 15 as the kept
  20-page and 24-page stores (E1041, E1051) restricted to the buffer.
- **H-E411-LIT**: E411's table read literally: G 3 completes, G 5 faults.

Controls that can fail (in s0): `zv-c-g3` at 20 pages (E1041's kept store, byte for byte) and
`zv-g5` at 24 pages (E1051's kept store). Held out: both planned rows (never run on t10 at 16
pages). The fault page is a second reading: a page other than the frozen one is reported, not
scored as a refutation of the fault clause. Retire Q299 if both rows read as one hypothesis and
the controls pass: the question asks only whether it faults (R17 section 7: "this one row can
retire Q299"). sgx-pipe's `zls` refusal of a store past its buffer becomes the measured outcome.

### f2, Q108 (E1071): WRITEONLY and EDMPROTECT alone on a depth load and a texture read

Knobs `dbg:vm_pte_addr` and `dbg:vm_pte_flags` (r14-bif's words; the fork takes bits of 0x1a;
flags on the whole mapping whose first page is the address, E964).

- Depth load: r14-bif's `rf-c-depth` argv (t14: load from the depth buffer at 0x3e001000 under ctl
  0x0017500e, the store into the separate `--depth-store` buffer), so the flagged mapping is only
  read. Rows `q108-edm-load` (0x10) and `q108-wo-load` (0x2).
- Texture read: r14-flag's `f1-ref-a` (t14 `probe --temps 32 --coords --pixels --scratch-pages 256`,
  E566's tx_map reading the scratch at 0x3e003000 as a texture; the printed address in r14-flag's
  kept output). Rows `q108-edm-tex` (0x10) and `q108-wo-tex` (0x2). The program writes only o0
  (the builder confirms from the bin that no scratch dword is written).

Frozen: **H-WO-ALL** (E945, E964: WRITEONLY faults every read): `wo-load` faults with FAULT_REQ bit
9 at 0x3e001000 (FAULT_TYPE 0, as 0x80008 and 0x80002), `wo-tex` faults 0x80002 at 0x3e003000.
**H-EDM-READ** (E945, E964: EDMPROTECT lets client reads through): both `edm-` rows complete with
the control's store and image byte for byte. Rivals: H-WO-LOAD-OK (the ZLS load is not stopped:
completes as the control), H-EDM-ZLS (EDMPROTECT stops the ZLS requestor whatever the access:
0xa0200 at the first page, E965's store fault), H-EDM-TEX (stops the texture read: 0xa0002).
Planned faults 2, `#limit 4` (every flag row `expectfault`). Controls in s0: `rf-c-depth` (E1046's
kept store) and `f1-ref-a` (E1047's kept image). Order: edm rows before wo rows. Narrow: the TA's
and the EDM's own buffers (reserved heaps; the knob takes a client mapping), data cached within one
render and the last-page unit under WRITEONLY stay.

### f3, Q139 (E1073 offline, E1074 laptop): why words fault, without a dump

Offline first, O18-1 (no laptop). E509's kept kernel logs mark each case and hold its fault lines:
162 faulting cases, 155 with 0x90100 at 0x10000012 (FAULT_REQ bit 8, the PARAMETERS heap's first
page, SB 1) and 13 with 0x90004 at TA_DATA pages 0x20007 to 0x20010 (FAULT_REQ bit 2, the TA's
header write past the kernel's layout, hw_spec 5.5; SB 2 or 6). O18-1 fits, post hoc and on those
lines only, which words give which kind and, for 0x90004, the page from E1048's H-EVEN slots and
the kernel's header layout (E1048's `render_param` read). It freezes the form by hash, then the
builder picks two words never run (sizes and fields outside E509's cases), one predicted of each
kind, and freezes kind and page. Rows: two `tri --kpoke-render 1:ta:143=V` rows of E1048's form.
Rival: H-ONE-KIND (every faulting word faults one way: E1048 H-COVER read as one mechanism).
Control in s0: E1048's `f2-ctl-256` baseline (kept hash and dump). Stop: if O18-1 finds no form
that fits the 162 lines' kinds (at least 95 %), f3 is not built and Q139 narrows offline only
(E1073). Narrow either way: the stride's relation to the RT data has no frozen relation to test.
A fault on B60AB0B4 at another page than the old fork's is read through the layout, not the
address (the page rule is relative to the kernel's printed layout).

### f4, Q241 bit 18 (E1072): which requestor, and does it need a buffer the run lacked?

E065 saw bit 18 fault once, on the library triangle, on an old fork, the fault word not kept in its
claim. Rows: `b18-lib` (E065's job again: t10 `tri --poke blk:1^=0x00040000`) and `b18-ramp` (E998's
isp0x form, E977's ramp at 80 x 40 with the depth buffer loaded and stored, bit 18 set alone).
Frozen: **H-FAULT-ANY** (both fault, same FAULT_REQ bit); rival **H-NEEDS-BUF** (bit 18 enables an
access to a buffer E065's job never mapped: the ramp row with depth buffers draws, the lib row
faults) [infer, weak]. Reading: the fault word names the requestor (hw_spec 5.5), the first
measurement of what bit 18 does. Control in s0: E998's unpoked ramp (kept image and depth dump).
Last fault stage: its fault kind is the least known. Narrow (Q241 keeps bits 15 to 17, the
counter, the offset, the pass types, the gate pairs).

### h1, Q112 (E1075): bit 24 alone over a 32-bit index list

E737: bit 24 hung over E414's 16-bit list (2 of 2); E756: bit 25 faults over both widths and bits 24
and 25 together faulted over the 32-bit list (bit 25's fault first [infer]); bit 24 alone over the
32-bit list never ran. Row `b24-w32` (t10 `probe --tri ... --index-width 32 --vdm N^=0x01000000`,
E756's form). Frozen: **H-B24-HANG** (hangs as over 16 bits) against **H-B24-W32** (bit 24
selects 32-bit indices: E414's five-copy object, no hang). Control in s0: E756's bit-clear 32-bit
list (the 5-vertex object read as 16-bit, 2 of 2 kept). One planned hang, `#limit 1`. Narrow (the
fault word 0xd0008 and what the hang waits on stay).

### h2, Q163 (E1076): the counter on two new stream shapes

E700's M1 (c + add > 8 hangs; g(v) = v - 2 for v of 2 to 7; a reset clears c) is held out on one
two-block shape (E700, E1021) and on a 128 x 128 one-block pair (E1035). Rows (t10 `probe --tri`,
E1035's form): shape A, 24 vertices, one object, 8 temporaries, 64 x 64; shape B, 48 vertices,
two objects, 16 temporaries, 128 x 64. Each shape: a reset row then two `noreset` rows, with v
chosen so M1's add is 4 a job: ok, ok (c = 8, not above 8), hang. Control first: the same triple's
first two rows on E700's shape (both complete under M1; a hang there fails the control and stops
the stage). Frozen: **M1-SHAPE** (the shape-1 rule, unchanged) against **H-ALT** (E413's
alternation: the second row hangs) and **H-SCALE** (the threshold scales with the vertex count:
shape A's third row completes) [infer]. 8 jobs, planned hangs 2, `#limit 4` (rows 2 and 3 of each
shape `expectfault`). Narrow: what decides v = 1, v = 0 and what the counter is stay.

## 3. Session r18-flag (one session; kit fit)

Prefix `r18f`, module B60AB0B4, tools t10 (`~/sgxfive-test-t10`) and t14 (`~/sgxfive-test-t14`),
both on the laptop and bound by source as in r14-flag. No tool change, no kernel change, no boot,
no clock-gate write, no held reset. Knobs: `vm_pte_addr` (0, 0x3e001000, 0x3e003000) and
`vm_pte_flags` (0, 0x2, 0x10), restored after every job; preflight debugfs `vm_pte_addr`,
`vm_pte_flags`, `render_param`.

| Order | Stage | Class | Jobs | `#limit` | Planned | Record |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | s0 references (gate) | safe | 7 | 0 | 0 | (controls of all) |
| 2 | f1 Q299 | flagged, faults | 2 | 2 | 2 | E1070 |
| 3 | f2 Q108 | flagged, faults | 4 | 4 | 2 | E1071 |
| 4 | f3 Q139 (if O18-1 freezes) | flagged, faults | 2 | 2 | 2 | E1074 |
| 5 | f4 Q241 bit 18 | flagged, faults | 2 | 2 | 2 | E1072 |
| 6 | h1 Q112 | flagged, hang | 1 | 1 | 1 | E1075 |
| 7 | h2 Q163 | flagged, hangs | 8 | 4 | 2 | E1076 |
| | **total** | | **26** (24 if f3 is not built) | **15** | **11** | |

(s0's seven references: `zv-c-g3`, `zv-g5` at 24 pages, `rf-c-depth`, `f1-ref-a`, E1048's
`f2-ctl-256`, E998's unpoked ramp, E756's bit-clear 32-bit list; each gates only its own stage via
`score.py gate`.) **Planned faults and hangs: 11 (8 faults, 3 hangs). Allowed by the `#limit`s:
15 (10 faults, 5 hangs).** One more is possible only as h2's control failing by a hang, which stops
h2. Every `#limit` counts planned rows only (E946); controls have no `expectfault` (E934); the
last planned row of each stage is its last row.

Kit fit: every word exists at 2c0fe18: `expectfault` (planned and rival rows), `noreset` (h2's
rows 2 and 3), `dbg:NAME=V` (f2), `hook_fault` (stops at a failed recovery, a hang without its
kernel line, or a fault of a row not marked), `on_stop = "end"` on every flagged stage (a failed
recovery ends the session), `gate = true` on f1 to h2. `idle:S` is not needed. The scorer reads the
kernel slice (fault word and page) and the kept outputs; `expectdiff` rows need `job: ok` and
only the s0 references and f2's edm rows carry it. The library-mock replay runs t10 and t14 rows
(no probe program of ours except f2's tx_map: the c12542e "not simulated" path); the mock needs
one world per stop: a fault in s0, a rival fault in f2, a failed recovery, h2's control hang.

Wall time: s0 about 2 minutes; each fault or hang about 45 s with the reset and strict health
(r14-flag's estimate); 11 events about 8 minutes, 15 about 11; other jobs about 2 minutes;
staging and preflight 4 minutes. **About 18 minutes, 25 at worst**, inside the 45 minute bound.
Alarms: 600 s per fault stage, 900 s for h2.

Offline parts (before the build): O18-1 (Q139's kind and page fit on E509's kernel lines, E1073),
O18-2 (Q046 note, below), the f1 premise check in the mock (the depth buffer is the last mapping).

## 4. Retire summary if every frozen hypothesis holds

Q299 retires (one). Q108, Q139, Q241, Q112 and Q163 narrow. Rounds 13-17 retired 11; this round's
ceiling is one, as round 17 foresaw.

## 5. Dropped rows, and why

- **Q046 bit 11.** O18-2 (offline, no record needed unless the lead wants one): page 0x37001000 is
  the USSE_PIXEL heap's base plus one page (render_uapi heap 4), the page after the probe rig's one
  pixel-code page (`tri_probe.c` maps one page per heap from a bump allocator) [infer], and
  0x91000 is FAULT_REQ bit 12, the requestor of E573's fault at the firmware code alias
  (0x3000b021), so bit 11 makes an instruction-fetch-like access one page past the pixel code
  [infer]. A run today only repeats the fault (E383, E1034: six times), and its low address bits
  vary run to run, so no row is decidable. A decidable row needs a tool change, T18-A: `probe --tri`
  accepting `--scratch-at 0x37001000` (refused today, sgxfive-test.c line 4489 at c58f9f9) with a
  page of known words; then H-FETCH (no fault, the page's words read as code) against H-WRITE
  (a write fault on the mapped page). Later round.
- **Q036's builder-fault clause.** Its premise is state a core reset does not clear: a failed
  recovery is the expected outcome, which this round's limits stop on.
- **Q040 odd EMIT2 counts.** Both rivals (a pair count, a whole unit) predict the hang: no outcome
  parts them.
- **Q163 below v = 2.** Every frozen form failed in E1035 (M1 0 of 3, M3 1 of 3, H-C05 2 of 3);
  nothing to freeze.
- **Q112's fault word 0xd0008; Q139's stride relation.** No hypothesis gives a predicted reading.
- **Q069** (`--blk-add` past bit 7: tool change), **Q195** (verifier first), **Q024** (a `kreg` kit
  word and 150+ timed jobs; not F-class), **Q177** two passes (safe class, offline fit first).

## 6. R18 decisions (recommendation first)

1. **R18-1 Session shape.**
   - a) r18-flag as section 3: s0, f1, f2, f3, f4, h1, h2; 26 jobs, 11 planned, 15 allowed, about 18
     minutes, E1070 to E1076 (recommended).
   - b) Retire only: s0 (two references) and f1: 4 jobs, 2 planned faults, 5 minutes, E1070.
   - c) a without f4 and h2 (the weakest narrowings): 15 jobs, 7 planned, 9 allowed.
2. **R18-2 Q108's EDMPROTECT rows.**
   - a) Run them as `expectfault` rows (`#limit 4`; a rival fault is a reading, not a stop)
     (recommended).
   - b) WRITEONLY rows only (`#limit 2`).
3. **R18-3 Q139.**
   - a) O18-1 offline first; f3 runs only if a form fits at least 95 % of E509's 162 fault kinds
     (recommended).
   - b) O18-1 only, no laptop row (Q139 narrows post hoc).
   - c) Skip Q139.
4. **R18-4 Q046 bit 11.**
   - a) Drop this round; O18-2 as a note and T18-A proposed for a later tooling pass (recommended).
   - b) T18-A now (tooling agent, cachix build of a t18, staged copy): adds about 1 hour and 2
     planned faults.
5. **R18-5 Q163 shapes.**
   - a) h2 as planned: two shapes, 8 jobs, 2 planned and 4 allowed hangs (recommended).
   - b) One shape (shape A): 5 jobs, 1 planned, 2 allowed.
   - c) Skip.
6. **R18-6 Q299's retirement.**
   - a) Retire under R16-6 (a) when both f1 rows read as one hypothesis with the s0 controls
     passing,
     whatever the hypothesis; the fault page is a reading (recommended).
   - b) Retire only if H-PAST-FAULT holds with its frozen pages.
7. **R18-7 Record numbers.**
   - a) E1070 f1 (Q299), E1071 f2 (Q108), E1072 f4 (Q241), E1073 O18-1 (Q139 offline), E1074 f3
     (Q139), E1075 h1 (Q112), E1076 h2 (Q163) (recommended).
   - b) The lead renumbers after the builds.
