# Round 20 plan: what one safe session on E0CC4027 can still retire

Planner (Opus, 2026-11-15, on the road, user present), offline and read only. Basis: resgx545 main
c0f8c41 (kit 50606dc, records to E1087, 143 open), data ba3990f01, module E0CC40275493F8AEAD8180B
(fork 456404fcffe5), tools t10 (a581c06) and t18b (ec50498, read from `git show`), the question
files Q038, Q088, Q107, Q191, Q192 (and Q036, Q096, Q119, Q123 for the re-check), records E1077 to
E1087, E466, E467, E625, E627, E628, E629, E169, the round 19 plan and session tables
(`closing19/plan/rank-round19.md`, `closing19/b/r19-dpm/tables/`, `closing19/b/r19-own*/tables/`),
the round 18 survey (`closing18/survey/unlock-survey.md`) and rounds 16 and 17's section 1b.
Records reserved: **E1088 to E1094**. Laptop wall time planned: about 30 min (section 5).

## 0. Honest summary

**Three retire-capable rows exist; one is clean, two need a clause decision from the user.**

- **Q088 (clean retire).** Round 19 left only the reload half: after a raised kick the final
  leaves a separate store buffer untouched (E1081), which three readings fit (it loads the load
  base, it reloads the partial render's store from the store base, it stores nothing). One host
  refill of the load buffer between the kick and the final, a moved final triangle and a 1.0 load
  fill part all three, and the ISP's own registers (`CR_ISP_ZLSCTL` 0x0480, `ZLOAD_BASE` 0x0484,
  `ZSTORE_BASE` 0x0488) read by regtimeline during each 3D render name the word and the bases the
  hardware ran with. R19-5 (a) already said Q088 retires on its result, relabelled hw.
- **Q038 (retire if R20-3 a).** The same rows decide "where a raised kick's final stores" and
  "whether dzo's kept depth is a load"; a moved final without a depth buffer decides whether a
  final that does not overflow repaints the partial render's colour. The E442-form reload itself
  in a geometry final needs a tool change; the user decides whether the repaint reading answers
  the clause.
- **Q192 (retire if R20-4 a).** An owner moved away from the second context's scene parts "the
  lists are the second context's" from "they are the owner's state stored at its eviction",
  repeats of E1084's o2-p30 test "a repeat", and P 0x2c and 0x34 test E627's two regimes. "Which
  event stores" is also Q191's clause and stays there.
- **Narrow only:** Q107 (the not-raised clause on the ramp, at P where its kick overflows without
  a raise, and what negates from 0x0480 bit 19), Q191 (whose scene, and the kick from DPM register
  timelines; clause (c), a load reading the words back, has no route), Q036 (owner words
  0x0700-0x0728 as readings).
- **No other open question became reachable** (section 1): the new module adds one debugfs knob
  and t18/t18b add `--final-pb-pages`, `--refill` and the copy after the early close, which reach
  only dpm and zls. Rounds 16 and 17's section 1b reasons still hold for the rest.

Two sessions, 29 jobs, safe class, no tool change, no flagged stage (R20-6 offers one).

## 1. Re-check: what the module and the tools reach now

| survey item (round 18) | state at c0f8c41 / E0CC4027 | questions it reaches this round |
|---|---|---|
| I1 T-pbfinal (final on its own PB) | done: module knob + t18b `--final-pb-pages` (E1077, E1078) | Q088, Q038, Q107 (S1) |
| I1 T-keptbig (copy after the early close) | done: d43e4bb (E1084, E1087) | Q192, Q191 (S2) |
| I1 T-kpokerd (rd:11 per render) | done: `--depth-ctl-next`, `--kpoke-render N:rd:11=` (E1083) | Q088 (load half left) |
| I2 T-kregword (kit `kreg` word) | not done; `--kreg-render` exists but the kit's rule is "no register write of ours" | Q024, Q076, Q001, Q111, Q110: still user-gated |
| I3 T-probe (code128k, scratchva, pdspatch) | not built | Q123 (two code bases: not a small change), Q096 (needs a texture at a target address + 0xc0000000: placement, or vm_pte_addr, flagged), Q057/Q058/Q060: narrow |
| I4 T-ta-kick (tadump-recover, kickflags, thdelay) | not built | Q139, Q004: flagged faults or recovered hangs; Q119 is fw-parked |
| N items (ctxswitch, K1 hold, edm-defpd) | no module change this round (brief) | Q068, Q049, Q095, Q109: not reachable |

S-route retire candidates of the survey (Q032, Q202, Q288, Q044, Q074, Q207, Q276, Q115, Q179,
Q181, Q129, Q132, Q136, Q143, Q146, Q042, Q053): t10/t14 reached them before round 18; rounds 16
and 17 (section 1b of each) found each with a fault, "why", nondeterministic or many-clause part,
and nothing in E0CC4027 or t18b changes that. Not ranked again.

## 2. Candidate rows, ranked (retire first)

| # | stage (session) | question | outcome if the frozen form (or one rival) holds | jobs | tool | risk |
|---|---|---|---|---|---|---|
| 1 | zc + zr (r20-zls) | Q088 reload half; Q038 clauses 1-2 | **retire Q088**; Q038 two of three clauses | 3 + 8 | t18b, rt | safe |
| 2 | ow + owt (r20-own) | Q191 whose scene, kick | narrow (Q191 (c) stays) | 4 + 2 | t18b, rt | safe |
| 3 | owp (r20-own) | Q192 repeat, regimes, whose lists | **retire Q192** (R20-4 a) | 5 | t18b, rt | safe |
| 4 | zm (r20-zls) | Q038 colour clause (repaint) | **retire Q038** with #1 (R20-3 a) | 3 | t18b | safe |
| 5 | zq (r20-zls) | Q107 not-raised clause, what negates | narrow | 4 | t18b, rt | safe |

## 3. S1 r20-zls (prefix `r20z`; E1088, E1089, E1090; 18 jobs)

Common form (r19-dpm's, `closing19/b/r19-dpm/tables/dza.txt`): `tri --width 1024 --height 768 -n 2
--geometry 1 --final-pb-pages 0x100 --keep-going --keep-overflow --wait-ms 20000 --dump-render $W
--dump-each --words $W --regs 0x0600-0x0750`, P by `dbg:render_pb_pages`, every row under rt with
r19's register list **plus `0x0480-0x0490`** (ZLS control, load base, store base, stencil bases;
read only, as the DPM range). Premise per row as r19 (`ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde`), and
the regime read, not assumed: raised iff TA3DCtl dword 38 of `ta3d.1.bin` is non-zero (E625,
E1082). A row whose regime differs from its label is scored under the regime read (rule frozen in
the scorer), so E1082's premise slip cannot void it. Knobs: render_pb_pages (0x422, 0x28, 0x2c,
0x30, 0x44, 0x4c), render_final_pb_pages (default "0", values ["0"]). `#limit 0` everywhere.

### 3a. Stage zc: controls (gate; 3 jobs)

| row | form | frozen reading (can fail) |
|---|---|---|
| zc-nl | -n 1 P 0x422, E628's dl form (`--poke blk:1=0x00400200` depth less, `--depth --depth-ctl 0x17110c --depth-fill index --depth-store`) | store holds the scene's depth (sidx 0, as E1081's dz-ac-nl); **zregs**: 0x0480 during the 3D = 0x0017110c, bit 0 as the job's render flag bit 4 (E169, read from `words.1.txt`); 0x0484 and 0x0488 = the load and store buffers' addresses (rd:1 + rd:12, rd:1 + rd:13 as `depth_arm` pokes them) |
| zc-ld | as zc-nl with 0x17510e | store holds the indices (sidx 1); zregs as above with 0x0017510e |
| zc-geo | E1081's dz-a-nl28-1 again, unchanged | store after the final = after render 1, 802816 of 802816 dwords (E1081); one partial render |

Gate on the store contents only. **zregs** is its own control: if 0x0480 reads 0 or never the
poked word, every register reading of the session is void (the rows still score on dumps), not a
stop. No param hash anywhere (the round 19 lesson): the controls compare depth dumps inside the
store window and the tool's own target check.

### 3b. Stage zr: Q088's reload half, Q038's store clauses (E1088; 8 jobs)

Form R: the common form with `--poke blk:1=0x00400200 --depth --depth-ctl C --depth-ctl-next C
--depth-fill 0x3f800000 --depth-store --depth-store-fill M --refill 2:depth=0x3e800000 --move
2:96,0 --depth-dump $W` (M a per-row marker). Render 1 (the overflowing kick, read): the partial
render stores 0.5 inside T1 and 1.0 outside, signed when raised (E629), zeros in tile rows 0-11
(E628), into the store buffer (E1081: a raised partial render loads whatever its bits). Then the
host writes 0.25 into the **load** buffer (`--refill`, after render 1 is read back, before the
final's kick; with `--depth-ctl-next` nothing else refills). The final draws T2 = T1 moved 96
pixels right at z 0.5. Frozen, for the store buffer after the final (`depth-store.2.bin`) on raised
rows, as rules applied to the row's own `depth-store.1.bin` (edge pixels of T2 take either value):

- **H-LOADBASE**: the final loads `ZLOAD_BASE` (now 0.25) whatever its bits: 0.25 at every stored
  dword of its window, no zero row; T2 fails the test everywhere (the tool's wrong-inside = |T2|);
  rt: 0x0484 = the load buffer during the final.
- **H-STOREBASE**: the final reloads the partial render's store (the store base), clearing its sign
  (E467): |store.1| everywhere, 0.5 where T2 covers a loaded 1.0, the zero row kept; rt: 0x0484 =
  the store buffer during the final.
- **H-NOSTORE**: the final writes no depth: store.2 = store.1 byte for byte (signs kept).
- **H-HOSTBITS** (the final follows its own word): without load bits 1.0 and T2's 0.5, unsigned, no
  zero row; with them as H-LOADBASE.

On rows that are not raised, every rule above predicts H-HOSTBITS (E1081's 2 of 2 at 0x30, frozen
as the regime rule). The four forms differ on every no-load raised row (0.25 / |store.1| + T2 /
signed store.1 / 1.0 + T2), so one fit row decides and the held-out rows test it.

| row | P | C (both renders) | label |
|---|---|---|---|
| zr-28-nl-1, -2 | 0x28 (raised) | 0x17110c (G 33, no load) | fit |
| zr-28-ld | 0x28 | 0x17510e (load) | fit |
| zr-2c-nl | 0x2c (raised, E1079) | 0x17110c | heldout |
| zr-28-nm | 0x28 | 0x17110c, no `--move` | heldout (H-STOREBASE: \|store.1\| exactly) |
| zr-30-nl, zr-30-ld | 0x30 (not raised) | 0x17110c, 0x17510e | heldout (regime rule) |
| zr-28-e336 | 0x28 | 0x0011700a (E336's word, G 1) | reading only: 0x0480 during each render and store.2 |

Readings (not scored for retirement): **H-RDREG** (E1083 made direct): during each partial render
and the final, 0x0480 = the kick's rd:11 (bit 0 per flag bit 4); rival **H-EDMPATCH**: after a
raise the restart writes another word (edm_dataflow.md's masks at 0xc23-0xdbe [infer]: load bits
1, 13, 14 or bit 19, E466's negated store). Fit on zc, held out on zr.

**Retire Q088** if one of H-LOADBASE, H-STOREBASE, H-NOSTORE holds on all four raised scored rows
(fit and held out) and H-HOSTBITS on both not-raised rows, the controls passing: answer "the
render details' word is the ZLS control of every 3D render of its kick (E1083, the 0x0480
reading); after a raised kick the final [the rule that held]; otherwise it follows its bits". No
form holding on all rows: narrow, as round 19. Q038 clauses "where a raised kick's final stores"
and "whether dzo's kept depth is a load" are the same verdict (H-NOSTORE is already at odds with
dzo's cleared signs, E1081, so a hold of it would need the per-buffer reading reported).

### 3c. Stage zm: does a final that does not overflow repaint the partial render's colour (E1089; 3)

The common form without a depth buffer, `--move 2:96,0`: render 1's triangle T1 is drawn by the
partial render, the final draws T2. Frozen **H-REPAINT** (E038/E311: the final's background paints
every tile it processes): the final image is T2's reference exactly (wrong 0); rival **H-KEEP**:
wrong-outside = |T1 \ T2| (the CPU count from the tool's reference, the library mock, frozen).
zm-28 (fit, raised), zm-2c and zm-30 (heldout). `expectdiff` with `job: ok` required (E934's
slip), `--keep-going`. Q038's colour clause answered as "repaints, so only a reload keeps them
(E442's remedy) [infer]" if the user takes R20-3 (a).

### 3d. Stage zq: Q107's not-raised clause (E1090; 4 jobs) - narrow

E629's ramp as r19's zs rows (`--tri-full --tri-z 0.25,0.75,0.25`, the same control on both
renders, G 33 0x17110c and G 1 0x17100c) at P where the ramp overflows without a raise: need 49
pages (E1082, post hoc), raised iff 2 (P - 0x22) < U + 2 (E625, E627's k): **P 0x44 and 0x4c**
(thr0 34 and 42; the builder confirms with dpm_raise.py and the premise reads the raise per row).
Frozen **H-NR-PLAIN**: not raised, the final's store is a plain store: no signed dword in
depth.2, no zero row in tile rows 0-11, and q107_rule.py's RULE holds on the G 1 dump against its
G 33 twin (61440 of 61440, as the -n 1 controls of E1082); rival **H-AFTERPR** (E1082's form
whatever the raise: zero row kept, RULE fails). Rows: zq-44-g33, zq-44-g1 (fit), zq-4c-g33,
zq-4c-g1 (heldout). Reading: 0x0480 bit 19 during the partial renders of zr's raised rows and zq's
not-raised ones (what negates). Q107 keeps the tile-order rule, the first row's shortfall and the
11264 extra zero dwords.

## 4. S2 r20-own (prefix `r20o`; E1091, E1092; 11 jobs)

Form E1087's (`closing19/b/r19-own1b/tables/own1.txt`): `tri --width 1024 --height 768 -n 1
--keep-overflow --wait-ms 20000 --ctx2 --close-first-early --kept-copy $W --words $W --kpoke-render
1:ta:7^=0xc`, `dbg:render_keep=1`, P by render_pb_pages (both contexts take it at creation), every
row under rt. New: `--move 1:DX,DY` moves **only the owner's** triangle (`tri2_submit` draws the
library default, t18b lines 3023-3051). Pages located by the fork's layout (control, OTPM, state at
0x4000, 0x5000, 0x6000 for 1024x768, E1084). The copy right after the close may read empty (E1085's
park race): counted, never a stop; hook_check stops only on a missing `kept.1.bin` twice in a row.
The scorers read pages 4 to 6 of `kept.1.bin` by dword (no whole-buffer hash).

### 4a. Stages ow and owt: Q191, whose scene and which kick (E1091; 6 jobs) - narrow

At P 0x422 (no partial render) E1087's state page after the second render holds 11 macrotile
lists summing to U - 1 at macrotiles 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 13 (column-major, the default
triangle's cover), both contexts drawing the same scene. Moved owner `--move 1:-128,-96` (vertices
(0, 0), (768, 144), (192, 576): cover {0, 1, 2, 4, 5, 6, 8, 9} [check: the builder computes the
cover on the CPU and freezes it]). Frozen **H-SECOND** (the lists are the second context's scene):
state page, control-page words and OTPM word equal E1087's o1-big rows dword for dword; rival
**H-OWNER** (the owner's DPM state stored when the second context takes its slot [infer]): the
listed macrotiles are the moved cover and their counts sum to the owner's U - 1 (U read from
0x0724's peak in the owner's job). Rows: ow-c (control, unmoved: E1087's pages exactly, reads
ovf,kept,size), ow-m1-a, ow-m1-b (fit), ow-m2 (`--move 1:64,64`, heldout). rt list:
0x0620-0x0634, 0x0658, 0x065c, 0x0674, 0x0694, 0x0698, 0x0700-0x0728 (Q036's owner words, readings).

owt (2 jobs, unmoved, rt on 0x062c, 0x0634, 0x0694, 0x0698 only, about 3 us a sweep): **H-TA**
(the state base takes the owner's TA data page 0x6000 and a task write shows before the second
context's first 3D activity) against **H-END** (after it); no task write seen: cannot tell. A
reading for "which kick" [infer: a register value is not the store's time].

### 4b. Stage owp: Q192, the 0x30 lists and the regimes (E1092; 5 jobs) - retire-capable

E1084: after the second render the owner's state page is zero at P 0x28, 0x24 (raised) and holds 10
other dwords at 0x30 (not raised, one row). Frozen **H-REGIME**: zero iff the kick is raised (P
0x2c and below at this scene, E1079), non-zero lists in E627's format otherwise (0x2d to 0x34).
Rows: owp-30-a, owp-30-b (fit: E1084's o2-p30 repeated, "a repeat": its 10 dwords exactly),
owp-30m (`--move 1:-128,-96`, heldout: H-SECOND predicts owp-30-a's dwords, H-OWNER other lists;
the owner's own overflow read, its regime may move), owp-2c (heldout: zero), owp-34 (heldout:
non-zero lists). **Retire Q192** if H-REGIME holds on both held-out P, the repeat holds and owp-30m
plus ow decide whose lists, with "which event" left to Q191 (R20-4 a).

## 5. Order, time, stops

1. Laptop as it is (E0CC4027 loaded, cable up; runbook section 3). Health as the kit's preflight.
2. S1 r20-zls: zc (gate) -> zr -> zm -> zq; 18 jobs, about 7 min + 3 staging. zc's store
   controls off: the session stops (`on_stop = "end"`); S2 still runs (it needs no S1 result).
3. S2 r20-own: ow (ow-c gates ow) -> owt -> owp; 11 jobs, about 5 min + 3.
4. Optional, last, only with R20-6 (b): the flagged row.

About 20 min of runs, 30 with staging and health: under the hour with margin for one re-stage.
Rate as r19 (41 jobs in about 12 min at 1024x768).

Kit fit (both): yes as is at c0f8c41: rt wraps t18b (r19-dpm, r13-dpm); knobs render_pb_pages,
render_final_pb_pages (declared at 0), render_keep (S2); `--refill`, `--move` and `--kpoke-render`
are not on the kit's forbid list (S1 forbids none of `--refill`, `--move`, `--geometry`,
`--final-pb-pages`; S2 keeps r19-own1b's session forbid list, which already allows `--move`);
debugfs files as r19-dpm (S1) and r19-own1b (S2). t18b bound as r19 does
(`data:render/closing-r19-own/lead/build_tool18b.sh`, binary 58e79855). Replay vectors: zr, zm, zq
refused by sgx-pipe's `zls::final_store` (it refuses stores after partial renders; name the
SIM_UNMODELLED entry); ow, owp refused (no DPM owner model).

## 6. Tool change and flagged rows

No tool change: every retire-capable row runs on t18b as built. Rejected: `--bg-layer` with
`--geometry` (R19-4 b: the layer samples its own source, not the target, so it is not E442's
reload; Q038's colour clause gets zm instead); `--ctx2` with `--geometry` (would separate Q191's TA
kick from the render end, but needs the second context's final path and its reference: not small);
a probe above 256 words (Q123: two code bases, not small).

Flagged (user's OK, after every safe stage), **none proposed**. If time remains (R20-6 b):
fl-thr1 (1 job, round 19's: P 0x422, N 0x23, the final's ZLS threshold 1 on a 19-page scene; a
livelock or a recovered hang possible; value low: E1078's untested abort at a lowered threshold).

## 7. Offline parts (Mac)

Before the freeze: the moved covers (S2), the zr rules as scorer code applied to each row's own
store.1 (no assumed dump), dpm_raise.py for P 0x44 and 0x4c, the zm |T1 \ T2| counts from the
library mock. After: folds by the builders; question edits per R20-2 to R20-5; E1020's G 1 dumps
re-read under whichever reload rule held (does the repeated tile come from the reload) [infer].

Records: E1088 (zc, zr), E1089 (zm), E1090 (zq), E1091 (ow, owt), E1092 (owp); E1093, E1094 spare
(a no-verdict stage or a correction: H-STOREBASE would need an appended correction to E628's "loads
whatever the control" reading and E1081's "stores nowhere or elsewhere" [infer]).

## 8. R20 decisions for the user

1. **R20-1 Round size.**
   - a) S1 and S2, 29 safe jobs, about 30 min (recommended).
   - b) S1 only (Q088, Q038, Q107; 18 jobs): the smaller round.
   - c) S1, S2 and the flagged fl-thr1 (R20-6 b).
2. **R20-2 Q088 on zr.**
   - a) Retire, relabelled hw (R19-5 a), if one reload rule holds on every raised row and
     H-HOSTBITS on the not-raised rows (recommended).
   - b) Narrow only; keep it parked as fw.
3. **R20-3 Q038's colour clause.**
   - a) zm's repaint verdict answers it ("a final that does not overflow repaints the partial
     render's pixels; E442's reload is what keeps them" [infer]); retire Q038 if zr decides the
     store clauses (recommended).
   - b) Keep Q038 open for a tool change that runs E442's reload program in a geometry final.
4. **R20-4 Q192's "which event stores".**
   - a) Leave it to Q191 (its clause already) and retire Q192 if owp and ow hold (recommended).
   - b) Narrow Q192 only.
5. **R20-5 Q191's clause (c), a load reading the words back (no route this round).**
   - a) Narrow Q191; keep (c) (recommended).
   - b) Split (c) into a new question and retire Q191 if whose scene and the kick are decided.
6. **R20-6 Flagged rows.**
   - a) None this round (recommended).
   - b) fl-thr1 (1 job) after every safe stage.
7. **R20-7 regtimeline on the ISP's ZLS registers 0x0480-0x0490 (read only).**
   - a) Sample them in S1, with zc's zregs control voiding only the register readings if it fails
     (recommended).
   - b) Leave them out; S1 scores on the dumps alone.
