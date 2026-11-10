# S2 e1c run 1: frozen verdict and post-hoc reading

Run id 1794264422-17682, 2026-11-09 23:47. Data: out/e1c/, out/score-e1c.txt.
(out/e1c.run1-stopped is the earlier stop from the kmsg append-mode bug: no science.)

## Frozen verdict

GATE e1c CLOSED. q50 3/3 held; q8 2/2 held (9 and 8 entries for 8.57 and 8.31 ms open,
pa1 0x02000000, pa2 0x01061a70, diffs 24998-25002); clock control held (median 25000, counting
up). Kick 0/3 against the frozen control (one entry, pa0 2, pa1 0x03000000, from E538). Each
kick ring held 16 entries plus 9-10 drops. By the frozen rule nothing after e1c ran.

## Post-hoc reading (fitted to the three kick jobs; not frozen before the run)

All entries in slot 0.

| job | entry | pa0 | pa1 | pa2 | stamp | diff |
|---|---|---|---|---|---|---|
| kick | r0 | 0 | 0x02000100 | 0x0100700c | 0x6cbd56c9 | - |
| kick | r1..r15 | 2 | 0x03000000 | 0x01061a70 | | 1790, then 25000+-4 |
| kick-r2 | r0 | 2 | 0x03000000 | 0x01061a70 | 0x6d1e428b | - |
| kick-r2 | r1 | 0 | 0x03000100 | 0x0105da97 | 0x6d1e4688 | 1021 |
| kick-r2 | r2..r15 | 2 | 0x04000000 | 0x01061a70 | | 23975, then 25000+-4 |
| kick-r3 | r0 | 0 | 0x04000100 | 0x0103bb6f | 0x6d7f4d3a | - |
| kick-r3 | r1..r15 | 2 | 0x05000000 | 0x01061a70 | | 15285, then 25000+-5 |

1. The kick is one event: pa0 = 0, pa1 = (K << 24) | 0x100; bit 8 goes to the general slot
   by E146's dispatch, matching slot 0.
2. pa1[31:24] is a count K every event carries: the kick carries K, every later tick K+1
   (2->3, 3->4, 4->5), persisting across jobs. Ticks before the first kick carry 2; what made
   it 2 is not shown (possibly the arm's own miscinfo read [infer]).
3. pa2 is EVENT_TIMER sampled when the event is taken: kick pa2 low 24 bits 28684, 383639,
   244591 (< 400000, E009's format); as a down-counter from 400000 core clocks,
   (400000 - low)/16 = 23207.3, 1022.6, 9713.1 CR_TIMER units since the last tick; stamps agree
   within 3 units (kick-r2: 1021 after the previous tick; the ticks after the other kicks at 1790
   and 15285 against 1792.8 and 15286.9). A tick's 0x01061a70 is 400000 - 16: one CR_TIMER unit
   after reload.
4. E538's "kick" words were the tick after the kick: its stubs logged pa1 & 0xfdffffff != 0 and
   kept the last hit; each E538 run reloaded the firmware (K back to 2), giving 0x03000000.
5. The same mask was S2's window-1 filter, which filled the kick rings with ticks.

Implications (post hoc until the rerun's held-out rows): Q033: bit 8 comes from a host kick with
pa0 0 (fits E155's kernel-CCB reading); a client job's own CCB kick may log bit 8, so bit 8 is no
SW_EVENT witness; pa1[31:24] are not event bits. Q153: "bit 25" is bit 1 of K; the open question
becomes what K counts. Q157: pa2 is a live EVENT_TIMER sample (3/3); the 0c inference that pa2 is
a constant is refuted (its five readings were all ticks). E538 needs a dated correction; E539 and
E605 are unaffected (tick-only windows).

Rebuilt for the rerun: window-1 filter masks pa1[31:24]; kick rows use window 2; new control
q50k; kick identity gated, the rest held out, labelled "fit: S2 run 1". See PREFLIGHT.md section 7.
