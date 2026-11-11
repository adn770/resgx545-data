# SPDX-License-Identifier: MIT
"""Stage q4-f (Q082, pixel side, the load; 16 jobs, plan section 3.2): what a load does to the latch of bit 6 in a fill.

Round 3 (E805): every ALU body set bit 6 in a fill when its tile time (B - 60.2) / 4 passed about 125 us and the body with a load and
a wait (ld8: a load, a wait, 4 multiply-adds, counter, branch) never did, to 320 iterations and 13.4 ms bursts.  Three readings:
H-YIELD (a wait ends a piece of work: the timer restarts at every load), H-LOADOFF (a program that waits on a load never latches) and
H-SUM (the busy time of the tile, waits not counted, is summed: a long sum sets it, which ld8's data already make unlikely).  Rows:
the bridge to E804 / E805 on the rgn4 module (the relative b8 loop at 16, 53, 56, 136 iterations and ld8 at 70: c, c, S, S; c);
ld0-K: ONE load and wait, then the b8 loop K times (K = 28, 53, 70, 110); ldo-K-M: M times (load, wait, the b8 loop K times) for
(K, M) = (28, 4) (28, 16) (40, 8) (70, 1) (70, 4) (110, 2) (220, 1).  The frozen table (plan 3.2):
  H-YIELD    ld0 28, 53, 70, 110: c, either, S, S   ldo (28,4) (28,16) (40,8): c, c, c   ldo (70,1) (70,4) (110,2) (220,1): S, S, S, S
  H-LOADOFF  ld0: c, c, c, c                        ldo (first three): c, c, c           ldo (last four): c, c, c, c
  H-SUM      ld0: c, either, S, S                   ldo (first three): S, S, S           ldo (last four): S, S, S, S
sgx-pipe's `events::status2_bit6` (the rule over a tile's time, a 64 x 32 fill WITHOUT a load, clear below 118 us, set above 132 us,
refused between) agrees with the bridge rows where it speaks: at 16 iterations (tile time 36 us) clear, at 136 (307 us) set, and it
REFUSES 53 and 56 (119.5 and 126.5 us, inside its edge): those two predictions are E804's measured bracket (2 of 2 each), not the rule's.
Every load row is outside the rule (a fill with a load is refused by status2_bit6, E805's ld8): the three readings are what is tested.
The time of the latch d6 is recorded with no prediction (round 4's timing model of the latch was refuted on the older data).  Two-level
counters; MARK only when both counters end (o0 = MARK on 2048 of 2048), every program checked in sgx-sim at code index 0.  A bridge
control that reads otherwise stops the session (runner knob want2).
"""
from __future__ import annotations

import r4common as K
from r4common import C, LP, Row, build_bin

S2 = "stophang s2"
FILL = 2048


def fill_cmd(path):
    return f'probe "{path}"'


def pipe_word(n):
    import r4tl
    return r4tl.bit6_rule(C.b8_tau(n))


def build():
    rows, preds, needs = [], [], []
    P = lambda *a: preds.append(a)

    def common(name, mk, st):
        P(name, "status2_pre", "0x400", "R1-events / E784 (a debugfs reset leaves CR_EVENT_STATUS2 at 0x400)", st)
        P(name, "proof", f"0x{mk:08x} {FILL}", "the MARK loop proof: o0 = MARK on 2048 of 2048 (both counters ended)", st)

    # ------------------------------------------------------------ the bridge (set control)
    for tag, n in C.F_BRIDGE:
        pname, text, info = LP.pixel_loop_source("b8", n)
        path = build_bin(pname, text)
        needs.append(path)
        mk = LP.mark(n)
        bit = {16: "clear", 53: "clear", 56: "set", 136: "set"}[n]
        want = "0x40:0x00" if bit == "clear" else "0x40:0x40"
        rows.append(Row(f"f-{tag}", "control", K.SAFE, f"{S2} proofstop:0x{mk:08x}:{FILL} want2:{want}", C.RT_REGS, fill_cmd(path),
                        f"bridge to E804 / E805: the relative b8 loop in a fill, N = {n}: bit 6 {bit}"))
        common(f"f-{tag}", mk, "control")
        pw = pipe_word(n)
        model = ("E804 (53 clear, 56 set: 2 of 2 each with a relative br; E431) and sgx-pipe status2_bit6: " + (
            f"it refuses (tile time {C.b8_tau(n):.1f} us is inside its edge 118..132), so this prediction is E804's measured bracket, not the rule's"
            if pw == "edge" else f"it agrees (tile time {C.b8_tau(n):.1f} us: {pw})"))
        P(f"f-{tag}", "bit6", bit, model, "control")
        P(f"f-{tag}", "pipe_rule", pw, "sgx-pipe events::status2_bit6 on the modelled tile time (B = 60.2 + 9.02 N; clear < 118, set > 132 us)", "control")
        if n == 136:
            P(f"f-{tag}", "t6_us", f"{C.T6_LO:.0f}..{C.T6_HI:.0f}", "E805 (bit 6 shows 120..340 us after the burst starts: 48 of 48 set jobs)", "control")
    pname, text, info = LP.pixel_loop_source("ld8", 70)
    path = build_bin(pname, text)
    needs.append(path)
    mk = LP.mark(70)
    rows.append(Row("f-ld8-70", "control", K.SAFE, f"{S2} proofstop:0x{mk:08x}:{FILL} want2:0x40:0x00", C.RT_REGS, fill_cmd(path),
                    "bridge to E805: the ld8 body (a load, a wait, 4 multiply-adds) at N = 70: bit 6 clear (E805: ld8 never set, to 320)"))
    common("f-ld8-70", mk, "control")
    P("f-ld8-70", "bit6", "clear", "E805 (ld8 clear at every point of its ladder, to 320 iterations; sgx-pipe refuses a fill with a load)", "control")
    # ------------------------------------------------------------ ld0-K: one load, then K iterations
    for i, k in enumerate(C.F_LD0):
        pname, text, info = LP.pixel_load_source(k)
        path = build_bin(pname, text)
        needs.append(path)
        name = f"f-ld0-k{k}"
        knobs = S2 + (f" proofstop:0x{info['mark']:08x}:{FILL}" if i == 0 else "")
        rows.append(Row(name, "heldout", K.SAFE, knobs, C.RT_REGS, fill_cmd(path),
                        f"ld0: ONE load and wait, then the b8 loop K = {k} times: HELD OUT"))
        common(name, info["mark"], "heldout")
        for h, tab in C.F_HYP.items():
            v = tab["ld0"][i]
            P(name, "bit6", {"c": "clear", "S": "set"}.get(v, "either"), f"{h} ({'a wait restarts the timer' if h == 'H-YIELD' else 'a waiting program never latches' if h == 'H-LOADOFF' else 'the busy time of the tile is summed'})", "heldout")
        P(name, "d6", "record", "recorded, no prediction (the latch time model was refuted on the older data)", "heldout")
    # ------------------------------------------------------------ ldo-K-M: M times (load, wait, K iterations)
    for i, (k, m) in enumerate(C.F_LDO):
        pname, text, info = LP.pixel_load_source(k, m)
        path = build_bin(pname, text)
        needs.append(path)
        name = f"f-ldo-k{k}-m{m}"
        knobs = S2 + (f" proofstop:0x{info['mark']:08x}:{FILL}" if i == 0 else "")      # the first nested loop on hardware: its proof stops the stage
        rows.append(Row(name, "heldout", K.SAFE, knobs, C.RT_REGS, fill_cmd(path),
                        f"ldo: M = {m} times (load, wait, the b8 loop K = {k} times): HELD OUT"))
        common(name, info["mark"], "heldout")
        for h, tab in C.F_HYP.items():
            v = tab["ldo"][i]
            P(name, "bit6", {"c": "clear", "S": "set"}.get(v, "either"), f"{h} ({'a wait restarts the timer' if h == 'H-YIELD' else 'a waiting program never latches' if h == 'H-LOADOFF' else 'the busy time of the tile is summed'})", "heldout")
        P(name, "d6", "record", "recorded, no prediction (the latch time model was refuted on the older data)", "heldout")
    return rows, preds, list(dict.fromkeys(needs)), __doc__
