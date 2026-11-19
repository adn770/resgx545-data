#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of r40-d0-survey (closing29/n3e/design.md §3.1, row D0: where an emitted
`douta` lands). Built on the r40-s-* generator (STEP "D0": ST's arm, the timer pass, no kick, the
blob emitsb14d). Writes tables/own.txt, tables/post.txt, predictions/own.tsv, predictions/post.tsv
and gen/constants.txt; every input is read at the commits session.toml's [freeze] names
(gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stage own (flagged, the task armed once on slot 0, entry 0, `slots=0x1 entry=0 pds=crumb3
pdsat=fw14 form=fw14`, ST's): one row, one tester command 1 with `"ticks": true`, no kick. The
blob emitsb14d is emitsb14 (ST's: #14's emit word, emits on the first tick that sees cmd 1) plus
the survey: before the emit, sa0-sa31 into page dwords 128-159 (pre); in the started task (entry
1) after S1 and before M4, sa0-sa31 into 160-191 and pa0-pa15 into 192-207 (post). The host fills
slots 2-5 (dwords 72-87) and dwords 128-223 with 0xdeadc0de first.

The start table is ST's (the design's §3 common table, no tick band); DONE is the precondition of
the landing, so DONE splits into the four landing outcomes of the design (§3.1: D0-HID, D0-PA,
D0-SHIFT, D0-STIR), told apart by one derived quantity `land` (score.py `land_of`); any start
outcome short of DONE, or a landing none of the four names, is CANNOT TELL. Controls: ST's (PG,
E0, T0, B) and the design's P0 (no fill left in 128-159) and P1 (pre sa0-sa3 = TA3DCtl dwords
0-3, snap0). Stage post: the stock firmware's triangle and fill after the disarm.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "D0"
STEPS = ("SB", "S2", "SP", "ST", "D0")
ARMS = {"SB": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14",
        "S2": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 pds2=req",
        "SP": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 pds2=req form=fw14",
        "ST": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14",
        "D0": "slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14"}
BLOBS = {"SB": "emitsk14", "S2": "emitsk", "SP": "emitsb14", "ST": "emitsb14", "D0": "emitsb14d"}
ROWNAME = {"SB": "row S-SB, Z with s2 = 0", "S2": "row S-S2, Z with our old emit word",
           "SP": "row S-PASS, Z from the timer pass",
           "ST": "row S-SBT, S-PASS with s2 = 0",
           "D0": "N3e row D0, the landing survey (ST with emitsb14d)"}
KICK = STEP not in ("SP", "ST", "D0")                      # SB and S2 emit on the miscinfo kick pass, as Z
ARM, BLOB = ARMS[STEP], BLOBS[STEP]
# the emit word of each blob (usse-asm text): ours (sideband 0) or #14's sideband 0x843 (N3d O1)
OWN_WORD = "emitpds.tasks.taske #0, r2, r3, r4, #0x0"
FW14_WORD = "emitpds.tasks.taske #0, r2, r3, r4, #0x843"
EMIT = {"SB": FW14_WORD, "S2": OWN_WORD, "SP": FW14_WORD, "ST": FW14_WORD, "D0": FW14_WORD}
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SOURCE = f"asm/fwtask/{BLOB}.s"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1 = 0x5A5A3301           # entry 0's marker (slot 1 dword 0)
X0 = 0x5A5A3303           # past the emit (slot 1 dword 2)
M4 = 0x5A5A3302           # entry 1's marker (slot 4)
S1 = 0x5A5A3304           # entry 1's first store (slot 5 dword 0)
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5 = 0x44, 0x48, 0x4C, 0x50, 0x54
X0_AT, S1_AT = SLOT1 + 2, SLOT5           # dwords 70 and 84
FILL = 0xDEADC0DE
FILL_AT, FILL_N = SLOT_PA, 16             # slots 2, 3, 4 and 5 (dwords 72-87)
PRE_AT, POST_SA_AT, POST_PA_AT = 128, 160, 192     # the survey (N3e §3.1), emitsb14d
SURVEY_FILL_AT, SURVEY_FILL_N = 128, 96   # dwords 128-223 (the design's fill)
TIMEOUT_MS = 200
T3 = 0x005A3305                           # crumb's and crumb3's dword 7
# the hooks' fallback for V0-V3 (a snap0 without ta3dctl lines: the kit mock's fake regs only):
# TA3DCtl dwords 0-3 in a kept snap0 of r35-sa (E1144), module 7CE8E38E
SNAP_PIN = "data:render/closing-r35-sa/out/20261118-085610/a/c0a-k.snap0.regs.gz"
ROWS = [("c1-a", "fit")]
DESIGN = "n3e design §3.1 (row D0)"
KICK_GATE = 0x100                         # pa1 bit 8, the CCB reader's (E746)


def m_table(s):
    """§3's common table (R4's M table), as Z's refreeze: T = 0x0acc in snap9 and the stop dump; no
    tick band (Δtick is printed, not scored: r39-n3d-k read 7, outside the first 8-11)."""
    return {
        f"{s}-NEVER": {"T": "running", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                       "res:0x2": "0x0"},
        f"{s}-T1": {"T": "0x00000000", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                    "res:0x2": "0x0"},
        f"{s}-T2": {"T": "0x00000200", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                    "res:0x2": "0x0"},
        f"{s}-T3": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                    "res:0x2": "0x0"},
        f"{s}-E1": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                    f"res:0x{SLOT4:x}": "fill", "res:0x2": "0x0"},
        f"{s}-DONE": {"T": f"0x{T3:08x}", f"res:0x{S1_AT:x}": f"0x{S1:08x}",
                      f"res:0x{SLOT4:x}": f"0x{M4:08x}", f"res:0x{SLOT4 + 1:x}": "@runid",
                      "res:0x2": "0x2"},
    }


# {model: {quantity: value}}. Values: 0xV; `fill` (the host's fill); `@runid`; `LO-HI` and `>=N`
# (Δtick, the record's ticks); `running` (T: bit 24 set, bits 23:0 at most 400000, two reads
# differ); `true`/`false` (alive: the record's alive_at_stop.advancing, the tick after the stop)
OUTCOMES = {s: m_table(s) for s in STEPS}
# D0: DONE is the landing's precondition; it splits by `land` (score.py land_of) into the design's
# four outcomes, D0-HID predicted to hold [infer, n3e §1.2]
LANDS = {"HID": "post sa4-sa31 = pre and no V0 or V2 in pa0-pa15: the douta landed nowhere D0 "
                "can see (sa0/sa2 own values) [predicted: held]",
         "PA": "V0 at pa k and V2 at pa k+2 for some k [predicted: failed]",
         "SHIFT": "post sa j = V0 and sa j+2 = V2 (j >= 4) where pre differed [predicted: failed]",
         "STIR": "any other pre/post difference in sa4-sa31, printed with its indices "
                 "[predicted: failed]"}
_done = OUTCOMES["D0"].pop("D0-DONE")
for _k in LANDS:
    OUTCOMES["D0"][f"D0-{_k}"] = dict(_done, land=_k)
MEANING = {
    "NEVER": "the program never started (T running, S1 fill): {}",
    "T1": "started, stopped at a douta",
    "T2": "stopped at the doutu",
    "T3": "doutu issued, entry 1 never stored",
    "E1": "entry 1 started, stopped after S1",
    "DONE": "all ran",
}
NEVER = {"SB": "with the kick and #14's word, s2 = 0x00020000 is needed",
         "S2": "with the kick and s2 = 0x00020000, #14's sideband is needed",
         "SP": "with #14's word and s2, the kick pass is needed",
         "ST": "on a tick with #14's word, s2 = 0x00020000 is needed",
         "D0": "ST's combination did not start this time: the survey has no landing to read"}
RUN = {"SB": "SB-RUN: s2 is not needed: #14's sideband with the kick pass suffices",
       "S2": "S2-RUN: the sideband is not needed: s2 with the kick pass suffices",
       "SP": "SP-RUN: the kick pass is not needed: #14's word and s2 suffice on a tick",
       "ST": "ST-RUN: #14's sideband alone suffices, on a tick, with s2 = 0",
       "D0": "D0-RUN short of DONE: the landing needs DONE, cannot tell"}
WHAT = {f"{s}-{k}": (v.format(NEVER[s]) if k == "NEVER" else f"{v} ({RUN[s]})")
        for s in STEPS for k, v in MEANING.items()}
WHAT.update({f"D0-{k}": f"all ran; landing {k}: {v}" for k, v in LANDS.items()})
# the controls (every row; all can fail): r37's PG, T0 and B; K1 (r37's E0: the gate fired) and,
# with the kick only, K0 (the record's k0, read between the command write and the kick)
E0 = "K1" if KICK else "E0"
CONTROLS = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read")] + ([
    ("k0:cmd", "0x1", "K0: cmd still 1 right before the kick (no tick took the command)"),
    ("k0:slot1", "fill", "K0: slot 1 still the fill right before the kick (no tick emitted)"),
] if KICK else []) + [
    (f"res:0x{SLOT1:x}", f"0x{M1:08x}", f"{E0}: entry 0 ran this command (slot 1 marker)"),
    (f"res:0x{SLOT1 + 1:x}", "@runid", f"{E0}: entry 0 ran this command (slot 1 run id)"),
    ("res:0x1", "0x0", f"{E0}: cmd 0 (entry 0 cleared it" + (", on the kick pass)" if KICK
                                                             else ")")),
    ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
    ("snap9:0x0c08", "0x0", "B: no BIF fault after the job (a fault is its own outcome)"),
] + ([("survey:p0", "true", "P0: every pre dword overwritten (no 0xdeadc0de left in 128-159)"),
      ("survey:p1", "true", "P1: pre sa0-sa3 = TA3DCtl dwords 0-3 of snap0 (the EDM's own, E002)")]
     if STEP == "D0" else [])


def snap_v():
    """TA3DCtl dwords 0-3 of the pinned snap0 (`ta3dctl 0xOO 0xVVVVVVVV` lines)."""
    t = pins.blob(SNAP_PIN).decode()
    v = {int(m.group(1), 16) // 4: int(m.group(2), 16)
         for m in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$", t, re.M)}
    return [v[i] for i in range(4)]


def source_facts():
    """What the blob's source stores where, read at the frozen commit: the res patches (byte offsets), the
    markers in order, the attribute reads, the emit count and the two breadcrumbs' places."""
    s = pins.blob("resgx545:" + SOURCE).decode()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip() and not ln.startswith(";")]
    emit = next(i for i, ln in enumerate(lines) if ln.startswith("emitpds"))
    e1 = lines.index("@entry 1")
    return dict(patches=[int(x) for x in re.findall(r"@patch res\+(\d+)", s)],
                marks=[int(x, 16) for x in re.findall(r"mov r7, #(0x5a5a33[0-9a-f]{2})", s)],
                pa=re.findall(r"mov r[4-7], (pa[0-9]+)\b", s),
                sa=re.findall(r"mov r[4-7], (sa[0-9]+)\b", s),
                emit=sum(1 for ln in lines if ln.startswith("emitpds")),
                emit_word=lines[emit].split(";")[0].strip(),
                c1=lines[lines.index("c1:") + 1:lines.index("c1:") + 7],
                after_emit=lines[emit + 1:emit + 5],
                entry1=[ln for ln in lines[e1 + 1:] if not ln.endswith(":")][:5])


def own_job():
    fill = ", ".join([str(FILL)] * FILL_N)
    survey = (', "%d": [%s]' % (SURVEY_FILL_AT, ", ".join([str(FILL)] * SURVEY_FILL_N))
              if STEP == "D0" else "")
    return ('{"cmd": 1, "params": {"%d": [%s]%s}, "timeout_ms": %d, "ticks": true%s}'
            % (FILL_AT, fill, survey, TIMEOUT_MS, ', "kick": "miscinfo"' if KICK else ""))


def tables():
    own = ["#stage own",
           "#limit 0",
           f"# own: Q128 {ROWNAME[STEP]} (closing29/n3d/design.md §3), the task {BLOB}",
           f"# armed once ({ARM}); one command 1 with ticks"
           + (" and the miscinfo kick," if KICK else " (no kick: the timer pass),"),
           "# the fill 0xdeadc0de in slots 2-5" + (" and dwords 128-223" if STEP == "D0" else "")
           + " first. One row by design: any stop",
           "# ends the session (rc 4);",
           "# run/hooks.sh stops it (rc 24, on_stop end) after an ok end whose markers, run id,",
           "# cmd, state or sa0-sa3 are wrong."]
    for n, st in ROWS:
        own.append(f"{n}|{st}|flagged|-|owntask|{own_job()}")
    post = ["#stage post",
            "#limit 0",
            "# post: the stock firmware (own_arm off since own's disarm) draws the health pair's",
            "# triangle and fill exactly.",
            "p1-tri|control|safe|reads:diff|t30|tri",
            "p2-fill|control|safe|reads:diff|t30|fill"]
    return "\n".join(own) + "\n", "\n".join(post) + "\n"


def predictions():
    own = [HEAD]
    for n, st in ROWS:
        for model, qs in OUTCOMES[STEP].items():
            for q, v in qs.items():
                own.append(f"{n}\t{q}\t{v}\t{model}\t{st}\t{DESIGN}: {WHAT[model]}\n")
        for q, v, why in CONTROLS:
            own.append(f"{n}\t{q}\t{v}\tCTL\t{st}\t{DESIGN} {why}\n")
    post = [HEAD,
            "p1-tri\tdiff\t0\tCTL\tcontrol\tthe kit's health triangle (E1134's health pair)\n",
            "p2-fill\tdiff\t0\tCTL\tcontrol\tthe kit's health fill (E1134's health pair)\n"]
    return "".join(own), "".join(post)


def constants():
    v = snap_v()
    out = [f"STEP {STEP}", f"ARM {ARM}", f"BLOB {BLOB}", f"EMIT {EMIT[STEP]}",
           f"KICK {'miscinfo' if KICK else 'none'}"]
    out += [f"KICK_GATE 0x{KICK_GATE:08x}"] if KICK else []
    out += [f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}", f"S1 0x{S1:08x}",
            f"T3 0x{T3:08x}"] + ([f"PRE {PRE_AT}", f"POST_SA {POST_SA_AT}", f"POST_PA {POST_PA_AT}"]
                                 if STEP == "D0" else []) + [f"V{i} 0x{x:08x}" for i, x in enumerate(v)]
    return "\n".join(out) + "\n"


def build():
    to, tp = tables()
    po, pp = predictions()
    return {"tables/own.txt": to, "tables/post.txt": tp, "predictions/own.tsv": po,
            "predictions/post.tsv": pp, "gen/constants.txt": constants()}


def main(argv):
    out = build()
    check = "--check" in argv
    bad = []
    for rel, body in out.items():
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p).read() != body:
                bad.append(rel)
        else:
            open(p, "w").write(body)
    if bad:
        print("not current: " + ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
