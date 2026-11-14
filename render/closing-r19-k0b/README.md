# r19-k0b: the E0CC4027 module's own controls (round 19 S1; E1077, E1078)

**Lead decision (2026-11-14):** r19-k0 (`closing19/b/r19-k0`, attempt 20261114-223342) stopped
at k0-a0 (rc 24, no fault): its param dump differed from r10-dpm's kept one in 4 dwords only
(0x12de30 to 0x12de3c, 0xc0000000 kept, 0 now), past a stream's end; tadata, image counts, page
steps and the controls before it equal; the fork's knob-0 path is unchanged (2a650d74..456404fc).
The lead kept E0CC4027 and asked for this session: r19-k0's rows, k0-a0's param control masked.
**Mask:** the dump is read as little-endian dwords; a terminate word 0xc0000000 that directly
follows another is replaced by 0, so each stream ends at its first terminate word and the rest of
that run (words the job need not write: stale ones) is not compared; the control is the sha256 of
the masked dwords as `%08x` lines (run/hooks.sh pmask, score/read.py pmask), ed097a08... for both
r10-dpm's dump and r19-k0's. tadata keeps its plain sha256.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 50606dc1cd12, data 95df71e98. Plan:
`closing19/plan/rank-round19.md` section 2; decisions `closing19/DECISIONS-R19.md` (R19-1 a: this
session gates the round). Prefix `r19k2`. Module E0CC40275493F8AEAD8180B (fork 456404fcffe5).
Safe class; f0-down medium (last, `soft`, `stop:jobfail`). No planned fault, no hang.

## What runs, in order (22 jobs)

1. **k0 (6 jobs, E1077)**: knob 0 runs B60AB0B4's jobs byte for byte (H-SAME against H-DIFF), on
   the kept twins: k0-pr1-1/2 (r13-dpm pr2-c1: 3072x2048, P 0x2b6, 1 partial render, 0x0624
   0x294), k0-z-t10/t18b (r13-zls zb-c-ctl: depth-store.1.bin sha256 92f04c7c..., 2048 drawn, 2048
   store dwords changed), k0-a0 (r10-dpm a0-cal-2048: param masked ed097a08..., tadata ddf914f0...),
   all
   controls; k0-pr4 (pr2-c4: 4 partial renders, 0xc0) held out. `on_stop = "end"`.
2. **kg (4 jobs, E1077)**: the geometry form (`tri 1024x768 -n 2 --geometry 1`, P 0x28) on t10
   and t18b, no kept twin: controls k0-geo-t10-1/t18b-1 (the geometry kick overflows, 0x0624
   0x6); H-SAME (t18b's final dumps = t10's), H-E625 (TA3DCtl dwords 35, 37, 38 = 0x4, 0x10006,
   0x20 at snapshot 1), pb:10-13 = 0x38, 0x6, 0x6, 0. Gated on k0, `on_stop = "end"`.
3. **f0 (12 jobs, E1078)**: the threshold update. Geometry kick at P, final at N (t18b
   `--final-pb-pages`). Controls (fit) f0-same-1/2 (P 0x422, N 0x200: no overflow, final 0x0624
   0x1de) and f0-up-1/2 (P 0x28, N 0x100: the kick overflows, final 0x0624 0xde); held out
   f0-up-h1-1/2 (0x30, 0x60: 0x3e), f0-up-h2-1/2 (0x24, 0x422: 0x400), f0-back-1/2 (`-n 3`: render
   3 back at 0x6 and overflowing; H-STICK: completes at 0xde), f0-down-1/2 last (0x100, 0x30:
   kick completes, final 0x0624 0xe and overflows; H-IGN/H-LATE: completes). Gated on k0 and kg.

Hypotheses (frozen in `predictions/`, written by `python3 gen/plan.py`): H-UPD (the EDM applies flag
0x2000's
dwords 10-13 before that kick's TA), H-IGN, H-LATE (stored, applied later), H-STICK, H-STORE
against H-NOSTORE (the PB descriptor's pb:10-13 after the final, from `--words`), H-GEO0 against
H-LIST (f0-geo, 0 jobs: f0-up's geometry kick against kg's k0-geo-t18b-1: knob, ovf1, d35, d37,
d38). Expected: H-SAME holds; H-UPD holds (the fork's arithmetic), H-STORE [infer].

## Stops

- Any control off (hook_check `ctl:` words): rc 24; k0 and kg end the session (R19-1 a: reinstall
  B60AB0B4, run S3 and ldb only), f0 ends it (S2 and S4 void, S3 runs).
- A control without its reading: rc 25. Any fault, hang or unexplained failure: rc 4.
- f0-down: `soft` (one failure is void, a second stops, rc 24); `stop:jobfail` stops the stage
  when a render ends `job: failed:` other than an overflow though the job ended ok.
- Stop budget: `#limit 0` in every stage (no expected fault).

## Time

About 13 s a job with reset and health: k0 ~1.5 min, kg ~1 min, f0 ~3 min; with staging and three
preflights about 10 min.

## Deviations from the plan

- The plan's k0 is split into k0 (the kept twins) and kg (the geometry form): the kit holds every
  row of a stage to the same kept files (REQUIRED), and only the geometry rows write `--words`.
- k0-a0 is a control: the library-mock scene check (`debug/scenecheck/`, run.sh and patch.py)
  gave rgn4 (4623753), t10 (a581c06) and t18b (ec50498) the same job image byte for byte
  (61dad21f...) for its argv; its dumps are read by the hooks (16 hex digits in readings.tsv).
  The same check gave t10 and t18b the same geometry jobs.
- f0-down's N is 0x30, not 0x28: the library mock overflows a 1024x768 final below 0x30 and the
  kit takes a kept overflow's `job: failed:` line (rc 0) for an unexpected end; 0x30 keeps the
  final's threshold (0xe) below the 19 pages the open scene holds. (A kit gap reported to the
  lead: an `expect:` outcome for `tri --keep-overflow`'s overflow at rc 0.)
- The TA command's flag and dwords 10-13 are not in debugfs render_words (its spaces are ctx,
  rtds, pb, kw, rd); the kernel-side premise is read from the PB descriptor (pb:10-13) and the
  module's `render context: PB ..., final kicks' PB ...` dmesg line (kept .dmesg), not scored.
- f0 has 12 jobs as the plan's header says (its table listed 10): f0-up-h1 and f0-up-h2 twice.

## Files

- Tools: t10 = `~/sgxfive-test-t10` (9bedc2d6..., a581c06, recipe
  `data:render/closing-r10-st1/lead/build_tool10.sh`); t18b = `~/sgxfive-test-t18b` (58e79855...,
  ec50498, recipe `lead/build_tool18b.sh`, round 18's byte for byte, first published here as
  `data:render/closing-r19-k0b/lead/build_tool18b.sh`); rt = `~/regtimeline` (079f6359..., wraps).
- `bins/p1139-green.bin` (r13-dpm's, the probe's program; ours). `mock/fixtures/` (r10-dpm's kept
  a0 dumps, byte copies of the pins). No firmware-derived file: nothing for data-private.

## Replay vectors

- k0: `dpm/r19-k0b-k0`, replay `refused`: register timelines and dump hashes against B60AB0B4's
  kept twins, no model step (E1032's form).
- kg, f0: `dpm/r19-k0b-kg`, `dpm/r19-k0b-f0`, replay `refused`: sgx-pipe's DPM model does not model
  the free list, thresholds or partial renders (E625, E627 stay in `crates/SIM_UNMODELLED.toml`,
  "dpm: not modelled"); E1077 and E1078 join that list at the fold unless a model lands.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
- Score: `python3 score/score.py STAGE out/ATTEMPT/STAGE out/ATTEMPT` (f0 reads kg of the attempt).
