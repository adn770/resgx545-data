# r8-k2 (round 8, K2: Q108, the PTE flags WRITEONLY, CACHECONSISTENT, EDMPROTECT)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 68b3136 and resgx545-data 1e83dc86. Plan:
`closing8/rank/rank-round8.md` section 3 (K2); decisions `closing8/DECISIONS-R8.md` R8-5 (the
round 8 kernel, one fork series, one one-shot boot) and R8-6 (RO|WO allowed as a reading row).
Built offline; nothing here touched the laptop, cachix or a git repository. Records E945 and E946
are reserved for its fold (the builder folds it).

## What runs, in order: 16 jobs, about 10 minutes

Laptop: the round 8 module, srcversion B60AB0B475DD1E8972419B5 (fork branch r8-kernel tip
2a650d74, `kernel/deliver/2a650d74b3a1/manifest`), loaded and installed; debugfs `vm_pte_flags`
and `vm_pte_addr` (0600, default 0). Tool t4 only, `~/sgxfive-test-rgn4` (sha256 e6951558...,
source `TOOLSRC.sha256`: sgxfive-test.c 703cbcea at resgx545 4dd6251, whose libsgxfive and uapi
trees are 4623753's, the commit the binary was built from). Files under `~/scratch/r8k/`.

| # | stage | jobs | what | controls |
|---|---|---|---|---|
| 1 | xf | 9 | WO on a fill's destination (a write) and on a copy's read-only source (RO\|WO 0x6, a read); CACHED on the copy's source; EDMPROT on a fill's destination | fill, copy, the address alone, isolation's READONLY fault, fill again |
| 2 | tri | 7 | WO on the 64 x 64 triangle's colour target (a write) and its GENERAL page (VDM stream, indices, vertices: reads); CACHED on the GENERAL page; EDMPROT on both | the triangle, before and after |

Every knob row writes `vm_pte_addr` (the first page of one mapping) and `vm_pte_flags` (one flag)
before the job; the runner restores both to 0 after every job and in its exit trap (the knobs
persist through resets, so a missed restore would leak into the health jobs and the next
session; the preflight refuses knobs not at 0). Each knob row then takes the strict health fill
and triangle (`after`). Time: about 6 s a job with its reset and health, isolation 1 s more, the
stage health, staging and copy back: about 10 minutes.

### Addresses

The tool allocates per VM with a bump allocator from each heap's base, so the addresses are its
own order (tests/test_twin.py reads them back from the tool's source on the library mock):
a transfer maps its PDS, USSE and stream pages first (stream 0x3e000000), then a fill's
destination at 0x3e001000 (64 x 32, stride 256: 3 pages with the guard) or a copy's read-only
source at 0x3e001000 (3 pages) and destination at 0x3e004000; a render maps its GENERAL page at
0x3e000000 (VDM stream, indices, vertices), then the 64 x 64 colour target at 0x3e001000 (5 pages).
The laptop agrees: copy-addresses (`texture/copy-addresses`, source 0x3e002000 behind its page)
and every health triangle (`layout: fb 0x3e001000`, r7-rp). The kernel logs `vm_map A +S: PTE
flags F` for the mapping that took the flags: that line is each knob row's premise.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

Outcomes: `exact` (job ok, diff 0, the knob-free control's hash), `diff` (job ok, pixels differ),
`fault` (job faulted, a kernel `BIF fault S at A` line with A's page inside the mapping); read
but matching no hypothesis: `fault-elsewhere`, `hang`; not a reading (cannot tell): `rejected`,
a job with no job line, a row without its PTE line with the frozen flags.

- **WRITEONLY.** Frozen H-WO (a read of the page faults and the fault names it, as E021's
  READONLY write; a write passes): xf-wo-fill and tri-wo-fb exact, xf-wo-copy (RO|WO) and
  tri-wo-gen fault. Rivals H-WO-NONE (all exact) and H-WO-ALL (all fault).
- **CACHECONSISTENT.** Frozen H-CC-NEW (the unit reads the host's writes, made after the map in
  both jobs: the copy's source pattern, the triangle's stream and vertices): xf-cc-copy and
  tri-cc-gen exact. Rival H-CC-STALE (diff).
- **EDMPROTECT.** Two frozen rivals, neither favoured: H-EDM-NONE (exact) and H-EDM-CLIENT (a
  client requestor faults: the transfer's pixel write, the 3D's colour write, the VDM's reads) on
  xf-edm-fill, tri-edm-fb, tri-edm-gen.
- **Controls** (they gate every row of their stage): xf-c-fill, xf-c-addr (the address knob with
  flags 0: nothing logged, the same image) and xf-c-end, the hash 0xb60c6095080bd325 of r7-rp's
  health fill; xf-c-copy, hash 0x9b1c0be484ac0d25 and source 0x3e001000 (copy-addresses);
  xf-c-ro, the tool's `isolation`: E021's READONLY write redone (PASS read-only-faults and the
  kernel's last fault 0x80020 at page 0x3e200000, render/client-jobs; two other known faults of
  its own come first); tri-c and tri-c-end, hash 0x99385a04ee01c585 and fb 0x3e001000 (r7-rp's
  health triangle). Every fault row's BIF_INT_STAT and address are printed (READ lines) for Q108's
  "what does the fault report" and Q003.

**Predicted outcomes.** H-WO and H-CC-NEW held on both stages; EDMPROT open. Faults predicted: the
isolation control, xf-wo-copy, tri-wo-gen; up to 3 more if H-EDM-CLIENT holds (6, the plan's
budget).

**Stops.** A stage stops (rc 24, the driver goes on) at its 4th fault or hang with rows left
(`#limit 4`: the rivals allow 3 a stage). Every fault is followed by the kit's reset and strict
health: a recovery that does not draw at the first try (the -110 recoveries of E848 and E892)
stops the session at once (16 or 5), stricter than the plan's "two -110 in a row". A fault or
failure of a knob-free fill, copy or triangle control stops the session (4). hook_check stops
the stage (24) when a fill, copy or triangle reads ok without `job: ok` (r8-geo lost 23 rows to
`job: rejected` with a diff line under expectdiff) or when a knob row with flags has no kernel PTE
line for its address. A control without its reading stops at its stage (25).

## The mock's worlds (mock/world.py, kit/session.py mock)

The fake tool runs every argv through the real tool's source on libsgxfive's in-process mock
(`debug/libmock`, built by tests/run_all.sh), so an option the tool refuses or a job the library
rejects behaves as on the laptop; the PTE knobs are read from the fake debugfs. Worlds: model (H-WO,
H-CC-NEW, H-EDM-NONE; 0), edmclient and rival (0, the other verdicts), allfault (each stage stops
at its 4th fault, 24), nopte (no PTE line: each stage stops at its first knob row, 24), rejected
(every knob row rejected with a diff line: hook_check stops each stage, 24), ctlfault (a control
faults: 4), ctlnohash (premise, 25), hang (a hang is a reading, 0), rono (isolation without its
fault: 4).

## Replay vectors

The fold builds `vectors/closing/r8-k2/pte-flags.table.json` (`sgx545-tables`; per knob row:
the flag, the mapping, the requestor's access, the outcome, BIF_INT_STAT and the fault page) from
the kept files alone, with `tools/usse-asm/closing_tables.py` and `closing_vectors.py` (pinned at
68b3136; at that commit they have no PTE kind: the round's tooling agent adds it test first, or the
fold reports the table as not built). Replay: `crates/sgx-pipe/src/bif.rs` (pinned), whose stub
refuses Q108 today: a test there replays the rows of every flag whose hypothesis holds; the rows of
a flag that stays open are `refused` (no model to replay).

## Layout

- gen/make.py writes `tables/` and `predictions/` from one spec (rows, mappings, hypotheses,
  the control values and their sources); tests/test_twin.py checks it is current.
- score/score.py, run/hooks.sh (readings job, hash, src, fb, ro, rostat; the job-ok and PTE
  checks), mock/world.py, `tests/` (test_twin.py, test_score.py, kept.py), PREFLIGHT.md,
  TOOLSRC.sha256.

Publishable: everything (our own tables, scorer and mock; no firmware-derived file). **Nothing is
marked for data-private.** `debug/` is scratch (the library mock's build, the mock's runs).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the library mock, the guard, the session's tests, the mock of
  every world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/run-r8k.log`): a new file here fails the
  verify (stop codes: kit/session.py).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plan (the lead may object before staging)

1. The READONLY fault control is the tool's `isolation` (E021's RO write as the tool redoes it,
   with two known faults of its own and the file's ban after the third), not a plain RO fill: no
   fill option maps its destination read-only and the plan allows no tool change.
2. WO on the copy's source is RO|WO (the copy maps its source read-only; decision R8-6). A clean
   WO read is tri-wo-gen (the render's GENERAL page is mapped read-write).
3. Rows added within the ~16: the address-alone control (xf-c-addr), WO on the colour target
   (tri-wo-fb), CACHED on the GENERAL page (tri-cc-gen) and the knob-free controls at each stage's
   end; the stop rule on -110 is the kit's strict health (stricter, above).
