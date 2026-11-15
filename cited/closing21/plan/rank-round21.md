# Round 21 plan: what one safe session on E0CC4027 can still retire

Planner (Opus, 2026-11-15, on the road, user present), offline and read only. Basis: resgx545 main
8b8e41f (records to E1092, 142 open), data 99a8cda42, module E0CC40275493F8AEAD8180B (fork
456404fcffe5), tools t10, t14, t18, t18b on the laptop, t20 pending (closing21/tooling). Read: the
state digest, the r20 handover and DECISIONS-R20, `closing20/plan/rank-round20.md`, the r20-zls
fold (`closing20/r20-zls/FOLD-NOTES.md`, `fold/look.out`), records E625, E627, E628, E629, E1081,
E1082, E1088 to E1092, questions Q038, Q071, Q088, Q107, Q191, Q210, Q211, the round 18 survey
(`closing18/survey/unlock-survey.md`) and rounds 15 to 17's sections 1b and 7.
Records reserved: **E1093 to E1096**. Laptop wall time planned: about 20 min (section 6).

## 0. Honest summary

**Only one question can retire on the laptop this round: Q088.** That is fewer than two
retire-capable rows, so I recommend **the smaller round**: one safe session (r21-zls, 12 jobs plus
4 optional narrow jobs, about 20 min with staging) and an offline part. The alternative is an
offline-only round (R21-1 b).

- **Q088 (retire-capable, relabelled hw as R19-5 a).** Kept data (E1088) leave one live rival on
  the reload half. With the host's 0.25 refill, the moved final's triangle failed its depth test
  everywhere. So "the raised final loads the load base and tests against it" (H-LOADTEST) and "it
  loads and writes the load buffer back without its own depth" (H-LOADNOTEST) gave the same store.
  A 0.75 refill parts them: T2 at z 0.5 then passes. The other clause is "what reads the word". The
  partial renders' CR_ISP_ZLSCTL fits one frozen form on all four kept words, E336's 0x0011700a
  included: rd:11 | 0x000c4000 (bits 14, 18, 19 ORed in; H-PRMASK). New words and P hold it out.
- **Q107: narrow only.** The zero row's rule and the tile order rule have no frozen form. An
  optional 4-job stage tests a frozen count rule from kept data: 195584 zero window dwords when
  raised, 118784 when not, whatever P (E1082, E1090). The rule itself needs an offline fit first
  (O21-2, O21-3).
- **Q038: not reachable.** Its colour clause waits for a tool change: E442's reload in a geometry
  final, plus no sentinel fill before the final's kick (R20-3 b). That change is not in the round
  21 tooling pass and is not small (section 7).
- **Q191: not reachable.** Telling "the second context's TA kick" from "its render's end" needs a
  copy of render_kept between the two, or a planned 3D fault of the second context. t18b has
  neither: `--ctx2` refuses `--geometry`, and `tri2_submit` draws the default triangle. Clause (c)
  has no route. t20's retry and the 0x062c owner base help a later Q191 row, not a retirement now.
- **The round 18 survey's other S-route rows**: rounds 16 and 17's section 1b reasons still hold.
  Neither the module nor t18b nor t20 changes them. Q210 and Q211 keep "why" clauses and many
  targets; Q071, Q120 and Q036 narrow only.
- **E629 against E1090 (offline): no conflict between the claims.** E1090's "at odds with E629"
  sentence compares two different stores. An appended correction to E1090 fixes it, with one line
  in Q107's text (section 4).

## 1. Re-check: round 20's leftovers and the survey's dpm/zls rows

| question | open after round 20 | route with t10/t14/t18/t18b (+ t20) on E0CC4027 | outcome now |
|---|---|---|---|
| Q088 (fw) | reload half; zero region; bit 15; "what reads the word" | zl + zw (t18b, rt); zero region to Q107, bit 15 to Q071 (R21-2) | **retire** |
| Q107 | zero row rule (118784 / 195584); tile order rule | zz tests a count rule (narrow); rules need an offline fit (O21-2/3) | narrow |
| Q038 | colour clause only (R20-3 b) | needs E442's reload in a geometry final and no sentinel: tool change (section 7) | none |
| Q191 | which kick; why only after the run; (c) a read-back | needs a mid-run kept copy or a planned 3D fault of ctx2 (tool change, flagged); (c) none | none |
| Q210, Q211 | why a target is biased; S3; many-kick counts | S cells plus offline model (survey: narrow) | none |
| Q071, Q120 | several independent clauses | narrow rows only (survey, rounds 16/17 1b) | none |
| Q036, Q081 | nondeterministic / small-context faults | W or F (survey) | none |

S-route retire candidates of the survey (Q032, Q202, Q288, Q044, Q074, Q207, Q276, Q115, Q179,
Q181, Q129, Q132, Q136, Q143, Q146, Q042, Q053, Q262) are blocked as round 20 section 1 says. Each
has a fault, a "why", a nondeterministic part or many clauses (rank-round16.md and
rank-round17.md, section 1b). t20 only retries an empty kept read and moves the owner base to
0x062c. It reaches none of them.

## 2. Candidate rows, ranked (retire first)

| # | stage (session) | question | outcome if the frozen form (or one rival) holds | jobs | tool | risk |
|---|---|---|---|---|---|---|
| 1 | zc + zl (r21-zls) | Q088 reload half | with #2: **retire Q088** | 2 + 7 | t18b, rt | safe |
| 2 | zw (r21-zls) | Q088 "what reads the word" | with #1: **retire Q088** | 3 | t18b, rt | safe |
| 3 | zz (r21-zls, optional) | Q107 zero-row count by the raise | narrow | 4 | t18b, rt | safe |
| - | (none) | Q038 colour, Q191 kick | not this round (sections 1, 7) | - | - | - |

## 3. S1 r21-zls (prefix `r21z`; E1093, E1094, E1095; 12 jobs + 4 optional)

Common form (r20-zls's zr, `closing20/r20-zls/tables/zr.txt`): `tri --width 1024 --height 768 -n
2 --geometry 1 --final-pb-pages 0x100 --keep-going --keep-overflow --wait-ms 20000 --dump-render
$W --dump-each --words $W --regs 0x0600-0x0750 --poke blk:1=0x00400200 --depth --depth-ctl C
--depth-ctl-next C --depth-pages 0x340 --depth-fill 0x3f800000 --depth-dump $W --depth-store
--depth-store-fill M --refill 2:depth=R --move 2:96,0`. Every row runs under rt with r20-zls's
register list (`0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,
0x0748,0x0a74,0x0480-0x0490`, read only). P comes from `dbg:render_pb_pages`, and
render_final_pb_pages is declared at its default "0". `#limit 0` everywhere, `expectdiff` rows
with `job: ok`. Premise per row as r20: `ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde ctl:refill=1`. The
regime is read, not assumed: raised iff TA3DCtl dword 38 of `ta3d.1.bin` is non-zero (E625). A row
whose regime differs from its label is scored under the regime read, a rule frozen in the scorer.

Regions (r20's `score.py` `window`, `look.py`): the G 33 store window, **hi** = tile rows 12 and
below, **lo** = tile rows 0-11. Every depth rule is scored on hi only. The lo region holds E1088's
zero region (65246 zeros after a load), which no rule predicts. Its counts are readings for Q107.
T2 edge dwords may take either value, as r20. No param hash anywhere. Every control compares
depth dwords inside the store window, or registers in the rt samples.

### 3a. Stage zc: controls (gate; 2 jobs)

| row | form | frozen reading (from kept data; can fail) |
|---|---|---|
| zc-r25 | E1088's zr-28-nl-1 again (P 0x28, C 0x0017110c, R 0x3e800000) | store.2 hi = 0.25 at 586752 of 586752; store.1 = depth.1 in hi (E1088, look.out) |
| zc-nl | -n 1 at P 0x422, E628's dl cell without load bits (C 0x0017110c) | store holds the scene's depth, sidx 0 (E1081's dz-ac-nl, E1088's zc-nl) |

**zregs2** is a register control frozen from E1088's post hoc reading (H-OFFS). In every non-zero
sample, 0x0484 = rd:12 and 0x0488 = rd:13 (`words.1.txt`). If it fails, only zw's readings are
void (as R20-7 a), and Q088 then cannot retire. The session does not stop. A store control off
stops the session (`on_stop = "end"`).

### 3b. Stage zl: Q088's reload half (E1093; 7 jobs)

Frozen for the store after the final (`depth-store.2.bin`), hi region, R = 0x3f400000 (0.75):

- **H-LOADTEST** (E1088 read as a load plus the final's own test): after a raised kick the final
  loads the load buffer whatever its load bits and draws T2 against it. 0.5 strictly inside T2
  (T2 = T1 moved 96 px), 0.75 elsewhere. The target check has wrong 0 inside T2.
- **H-LOADNOTEST** (the same store at 0.25, read as a copy): 0.75 at every hi dword. T2's depth is
  not written.
- **H-HOSTBITS** (the final follows its own word; E1081 2 of 2 and E1088's 0x30 rows when not
  raised). With load bits, as H-LOADTEST. Without them, 0.5 inside T2, and 0.5 or 1.0 inside T1
  \ T2 (render 1's remainder: 18582 dwords at 0x30, counted). 1.0 elsewhere.

Regime rule (frozen): a raised row scores H-LOADTEST against H-LOADNOTEST. A not-raised row scores
H-HOSTBITS against both. E1088's raised no-load rows already refute "raised follows its bits"
(their store held the refilled 0.25).

| row | P | C | regime (E625, U 19, k 2-3) | label |
|---|---|---|---|---|
| zl-28-nl | 0x28 | 0x0017110c | raised | fit (decides LOADTEST vs LOADNOTEST) |
| zl-24-nl | 0x24 | 0x0017110c | raised (thr0 2) | heldout |
| zl-2a-ld | 0x2a | 0x0017510e | raised (thr0 8) | heldout |
| zl-2c-nl | 0x2c | 0x0017110c | raised (E1088) | heldout |
| zl-2e-nl | 0x2e | 0x0017110c | not raised (thr0 12) | heldout (H-HOSTBITS, no load) |
| zl-2e-ld | 0x2e | 0x0017510e | not raised | heldout (H-HOSTBITS, load) |
| zl-34-nl | 0x34 | 0x0017110c | not raised, overflows (thr0 18 < 19, E625) | heldout |

Readings (not scored): the lo region's zero count after the final, in store.2 and depth.2 (Q107,
E1088's 65246 and 183107); the final's target check counts.

### 3c. Stage zw: what reads the render details' word (E1094; 3 jobs, plus zl's rows)

Frozen from the four kept words of E1088 (`fold/look.out`: 0x0017110c -> 0x001f510c, 0x0017510e ->
0x001f510e, 0x0011700a -> 0x001d700a, zc-geo alike). **H-PRMASK**: during the partial renders
(0x0658 bit 0), at least 80 % of the samples read rd:11 | 0x000c4000. No sample reads anything but
that or rd:11 itself (E1088 had one rd:11 sample per stretch at the start). Rivals:
**H-PR1419** (rd:11 | 0x00084000) already fails on 0x0011700a. **H-OTHER** is any other value.
The scorer reads rd:11 from `words.1.txt` (r20's `rdreg`, `zls_word`).

| row | P | C (both renders) | predicted 0x0480 in the partial renders | label |
|---|---|---|---|---|
| zw-2c-e336 | 0x2c (raised) | 0x0011700a (E336's word, G 1) | 0x001d700a | heldout |
| zw-2e-e336 | 0x2e (not raised) | 0x0011700a | 0x001d700a | heldout |
| zw-28-g1 | 0x28 | 0x0017100c (E1082's G 1 word) | 0x001f500c | heldout (new word) |

zl's seven rows are held-out samples of H-PRMASK at new P too. The zw rows have no depth rule:
E336's word stores nothing, and G 1 overlaps tiles. Their stores are readings.

**Retire Q088** (R21-2 a) if all of these hold:

- zc passes;
- the rival zl-28-nl picks (H-LOADTEST or H-LOADNOTEST) holds on all three held-out raised rows;
- H-HOSTBITS holds on the three not-raised rows;
- H-PRMASK holds on zw's three rows and on zl's seven, with zregs2 passing.

The answer would read: "the firmware loads the render details' ZLS word into CR_ISP_ZLSCTL for
every render of its kick, with bits 14, 18 and 19 ORed in for the partial renders (E1083, E1094).
So the closed driver's unpatched 0x0011700a is what a partial render of the next TA kick runs with
before the 3D patch [infer for the closed driver's order]. After a raised kick the final loads the
load base [and tests T2 against it]; otherwise it follows its bits (E1093)." The zero region moves
to Q107 and bit 15 (0x0480 bits 14 and 15 after the partial renders, E1088) to Q071. If any part
fails, Q088 narrows and stays parked.

### 3d. Stage zz (optional, R21-1 a): Q107's zero-row count (E1095; 4 jobs) - narrow

E629's ramp as r20's zq (`--tri-full --tri-z 0.25,0.75,0.25`, G 33 0x0017110c on both renders,
no refill, no move). The ramp's need is U 49, so it is raised iff 2 (P - 0x22) < 51. Frozen
**H-ZCOUNT** from kept rows: depth.2 holds 195584 zero window dwords in tile rows 0-11 when the
kick is raised (E1082: 0x28 with two partial renders, 0x30 with one) and 118784 when it is not
(E1090: 0x44, 0x4c). No signed dword in depth.2's window. H-AFTERPR's zero row is kept. Rival
**H-ZP**: the count follows P (any other count). Rows: zz-24 (raised, thr0 2), zz-38 (raised,
thr0 22), zz-3c (not raised, thr0 26), zz-50 (not raised, thr0 46 < 49), all held out. If it
holds, Q107's zero-row clause narrows to "why 382 against 232 tiles". If it fails, the counts
feed O21-2.

## 4. E629 against E1090 (offline check)

- **E629** (-n 1 jobs, `analysis/tables/depth.txt` of `dpm/partial-model-batch`): one kick, its
  partial renders and its final on one PB, and one depth dump after the job. The claim is about
  the store left at the end of the job, the last render's. It is signed iff dword 38 is non-zero
  (44 of 44). E629 never dumped a partial render's own store.
- **E1090** (geometry form: final on its own PB, depth.1 after render 1, depth.2 after the
  final). depth.2 is unsigned when not raised (0 signed), which agrees with E629's "positive when
  not raised". depth.1, the partial render's own store, is signed without a raise (636928). That
  is a store E629 did not see.
- **E1082's correction**: the geometry final stores unsigned when raised too. So the sign by the
  raise holds for a final that continues the raised kick on its PB (E629). It does not hold for a
  final on a fresh PB [infer: the fresh final's own TA3DCtl is not raised].
- **A scope slip in Q107's text, not E629's.** The partial render's store is not signed "raised
  or not" in every form. E1088's raised dl rows stored the loaded 1.0 unsigned in the separate
  store buffer (look.out: depth-store.1 = depth.1, no sign). Only the not-raised 0x30 row signed
  T1. The ramp rows (single buffer, E1082, E1090) are signed in both regimes.

**What fixes it:** an appended **Correction to E1090** (no claim edit; the claim's numbers stand).
It replaces the body's "at odds with E629's sign by the raise if the raise is TA3DCtl dword 38" with
the scope: E629's sign is of the store at the end of an -n 1 job, and E1090's depth.2 agrees with
it. E1090's depth.1 is a store E629 never dumped. Also one corrective line in **Q107**'s
2026-11-15 paragraph: "signed raised or not" holds for the ramp's single buffer (E1082, E1090), not
for E1088's raised separate store. E629 itself needs nothing: its claim and its [infer] reading
("whether the negation is the partial render's store or the load is not seen") stand. E1088's
0x0480 bit 19 during the partial renders now reads it [infer]. If the lead wants one record to
cite, E1096 can hold the three-form table as an offline record (R21-3 b).

## 5. Offline parts (Mac)

- **O21-1 (before the freeze):** the zl and zw predictions as scorer code over each row's own
  files. That covers the T2 cover at +96 px (205206 dwords, r20's `tri_default`), the hi and lo
  masks, the regime rule, H-PRMASK's values from `words.1.txt`, and E1088's kept zc-r25 dwords,
  frozen by hash.
- **O21-2 (Q107, offline fit, no run):** the zero region's rule on the kept dumps (E628, E1081,
  E1082, E1088, E1090, and zz if it runs). Features: the state page's macrotile lists (E627), the
  partial renders' cover, P, the raise. Freeze any rule that fits by hash for a later held-out row.
- **O21-3 (Q107, offline fit):** the tile order on the 14 kept G 1 dumps with G 33 twins (E1020's
  10, E1082's 2, E1090's 2). E1020's four orders failed 0 of 10. Try "slot keeps the last tile
  stored by the final's lo/hi pass".
- **O21-4:** the E1090 correction and the Q107 line (section 4), drafted for the fold.

## 6. Order, time, stops, kit fit

1. Laptop as it is (E0CC4027 loaded, cable up; runbook section 3), with the kit's preflight health.
2. S1 r21-zls: zc (gate) -> zl -> zw -> zz (optional). 12 jobs (16 with zz), about 6 min of runs
   at r20's rate (18 jobs in about 7 min) plus about 10 min of staging and health. Stops: a zc
   store control off ends the session. A hook stop is only a missing `depth-store.2.bin` twice in
   a row. No fault or hang is planned. `#limit 0`.
3. Offline O21-1 before the freeze, O21-2 to O21-4 in parallel or at the fold.

Laptop wall time **about 20 min**, under the 45 min limit with room for one re-stage.

- **Kit fit:** yes, as is on main 8b8e41f. It is r20-zls's form unchanged except for R, P and C.
  rt wraps t18b. The knobs are render_pb_pages and render_final_pb_pages (declared at 0).
  `--refill`, `--move`, `--geometry`, `--final-pb-pages` and `--depth-ctl-next` are not on r20's
  forbid list. The debugfs files are r20-zls's. t18b is bound as r19 and r20 bind it
  (`data:render/closing-r19-k0/lead/build_tool18b.sh`, binary 58e79855).
- **t20 is not needed.** S1 takes no param hash and no kept copy. The tooling pass's kit fixes
  (stream-bounded hashes, the 0x062c owner base) do not change S1. If the kit moves before the
  build, the builder scaffolds on the new main.
- **Replay vectors:** zl, zw and zz are refused by sgx-pipe's `zls::final_store` (it refuses
  stores after partial renders); the builder names the SIM_UNMODELLED entry.

Records: **E1093** (zc, zl), **E1094** (zw), **E1095** (zz, if it runs), **E1096** spare (R21-3
b, or an O21-2/O21-3 rule). The E1090 correction takes no number.

## 7. Tool changes and flagged rows (for the user, last)

No tool change for S1. Not proposed this round, with what each would need:

- **Q038's colour clause:** a geometry final with E442's reload background (a pixel shader
  fetching the target at the pixel's position). That needs three changes. (1) `--bg-layer` or a
  reload object accepted with `--geometry` (refused today, sgxfive-test.c 2598). (2) The library's
  sentinel fill skipped before the final's kick (libsgxfive render.c). (3) The reference for a
  kept colour. Not small, and not in the round 21 pass.
- **Q191's kick:** a second-context render that faults in its 3D after its TA completes (flagged,
  planned fault). `tri2_submit` draws only the default triangle, and no frozen faulting poke of
  the second context's 3D is in the kept data, so its premise would be unfrozen (the round 19-20
  slip). Clause (c) has no route anyway: narrow at best.
- **fl-thr1** (rounds 19-20's leftover: a final ZLS threshold of 1; livelock or recovered hang
  possible; low value).

Flagged rows proposed: **none**.

## 8. R21 decisions for the user

1. **R21-1 Round size** (fewer than two retire-capable rows).
   - a) The smaller round: S1 r21-zls with zz (16 safe jobs, about 20 min), plus O21-1 to O21-4
     (recommended).
   - b) Offline only: the E1090 correction, the Q107 line and the O21-2/3 fits; Q088 stays parked.
   - c) S1 without zz (12 jobs).
2. **R21-2 Q088 on zl plus zw.**
   - a) Retire, relabelled hw (R19-5 a), answered by E1094 with E1093, if every part of section
     3c holds. The zero region moves to Q107 and bit 15 to Q071 (recommended).
   - b) Narrow only; keep it parked as fw (the closed driver's purpose for the word).
3. **R21-3 E629 against E1090.**
   - a) An appended correction to E1090 (scope of E629's sign) and one corrective line in Q107; no
     new record (recommended).
   - b) As a), plus an offline record E1096 with the three-form sign table (-n 1 final, geometry
     final, partial render's own store).
   - c) Leave both as they are.
4. **R21-4 Q038's colour clause.**
   - a) Keep it open for the tool change of section 7, specified as a later round's tooling item
     (recommended; R20-3 b stands).
   - b) Add that change to this round's laptop t20 build (about 3 changes; the round grows).
5. **R21-5 Flagged rows.**
   - a) None this round (recommended).
   - b) fl-thr1 (1 job) after every safe stage.
6. **R21-6 Register control.**
   - a) zregs2 voids only the register readings (zw, Q088's word clause) if it fails, as R20-7 a
     (recommended).
   - b) Make zregs2 a gate for zl too.
