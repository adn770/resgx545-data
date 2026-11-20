#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r40-n3e-* sessions (closing29/n3e/design.md §3.2-§3.3, N3e: which
bits of the emit's sideband start our emitted PDS program, and where an emitted `douta` lands).
One session per row, STEP below says which: B0 (the control: D0's blob and arm on the new
module), L (the land image), B1-B4 (the H-DM ladder), B5-B10 (conditional), B11 (0xc43, last).
Built on r40-d0-survey's generator. Writes tables/own.txt, tables/post.txt, predictions/own.tsv,
predictions/post.tsv and gen/constants.txt; every input is read at the commits session.toml's
[freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stage own (flagged, the task armed once on slot 0, entry 0): one row, one tester command 1 with
`"ticks": true`, no kick (the timer pass, as ST and D0). The blob is emitsb14d (B0, L) or
emitsb_<form> (B1-B11: emitsb14d with only the emit word changed, resgx545 r40-n3e): each stores
M1 and the run id in slot 1, sa0-sa31 into page dwords 128-159 (pre), clears cmd, emits, X0 =
0x5a5a3303 (dword 70); entry 1 stores S1 = 0x5a5a3304 (dword 84), pa0-pa3/sa0-sa3 (72-79),
sa0-sa31 (160-191) and pa0-pa15 (192-207) (post), M4 = 0x5a5a3302 and the run id (80-81), state
2. The host fills slots 2-5 (dwords 72-87) and dwords 128-223 with 0xdeadc0de first.

B rows: image crumb3 at pdsat=fw14 (ST's), arm form=<the row's form>; the design's common table
(§3: NEVER, T1, T2, T3, E1, DONE; no tick band), frozen with the row's H-DM and H-ALL predictions
(RUN = any of T1..DONE); controls ST's (PG, E0, T0, B); D0's landing survey printed, never scored.
Row L: image land at pdsat=fw14 (two douta of Ma 0x5a5a3a18 to sa24 and Mb 0x5a5a3a1a to sa26, the
doutu, halt, no tim), form=fw14, emitsb14d: T runs in every outcome (no tim); L-NEVER (S1 fill),
L-E1 (S1, no M4), and DONE split by one derived quantity `lland` (score.py lland_of) into L-SA
(predicted held), L-SHIFT, L-PA, L-ONE, L-NONE; controls ST's plus D0's P0 and P1. Stage post: the
stock firmware's triangle and fill after the disarm.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "B7"
# the rows (n3e §3.3): form= name, sideband, blob, image, H-DM and H-ALL predictions (RUN, NEVER or
# "-": none), the design's stage order, when the row runs
ROWS = {
    "B0": ("fw14", 0x843, "RUN", "RUN", "E1, 1st",
           "always, first after the build and boot: the control (the build reproduces ST); B0 not "
           "DONE stops everything (D0 reran first)"),
    "L": ("fw14", 0x843, "-", "-", "E1, 2nd",
          "after B0-DONE (n3e §3.3 row L, the user's decision C (a)); L-NEVER: no other image in "
          "this build"),
    "B1": ("sb003", 0x003, "RUN", "NEVER", "E1, 3rd", "after B0-DONE"),
    "B2": ("sb841", 0x841, "NEVER", "NEVER", "E1, last",
           "after B1, the last row of E1 (bits 1:0 = 1, a new risk class, decision B (a)); a FAULT "
           "stops the ladder for the user"),
    "B3": ("sb842", 0x842, "NEVER", "NEVER", "E2",
           "after E1 (bits 1:0 = 2, a new risk class, decision B (a)); a FAULT stops the ladder"),
    "B4": ("sb840", 0x840, "NEVER", "NEVER", "E3", "after E2"),
    "B5": ("sb043", 0x043, "RUN", "NEVER", "conditional",
           "only if B1 read NEVER (H-DM falsified as enough), or at the lead's choice when B0-B4 "
           "read as H-DM (then it says whether bits 6 and 11 change what is seen)"),
    "B6": ("sb803", 0x803, "RUN", "NEVER", "conditional",
           "only if B1 read NEVER (H-DM falsified as enough), or at the lead's choice when B0-B4 "
           "read as H-DM (then it says whether bits 6 and 11 change what is seen)"),
    "B7": ("sb001", 0x001, "NEVER", "NEVER", "conditional",
           "only if B2, B3 or B4 read RUN (H-DM falsified as needed); bits 1:0 = 1, a new risk "
           "class (decision B (a)); a FAULT stops the ladder"),
    "B8": ("sb002", 0x002, "NEVER", "NEVER", "conditional",
           "only if B2, B3 or B4 read RUN (H-DM falsified as needed); bits 1:0 = 2, a new risk "
           "class (decision B (a)); a FAULT stops the ladder"),
    "B9": ("sb040", 0x040, "NEVER", "NEVER", "conditional",
           "only if B2, B3 or B4 read RUN (H-DM falsified as needed)"),
    "B10": ("sb800", 0x800, "NEVER", "NEVER", "conditional",
            "only if B2, B3 or B4 read RUN (H-DM falsified as needed)"),
    "B11": ("sbc43", 0xC43, "RUN", "-", "last",
            "last of all, its own session, after every other row that runs (decision D (a)): "
            "bit 10, H-SA's risk (n3e §4)"),
}
STEPS = tuple(ROWS)
FORM, SIDEBAND, HDM, HALL, ORDER, WHEN = ROWS[STEP]
LAND = STEP == "L"
KICK = False                              # every row emits on the timer pass, as ST and D0
BLOB = "emitsb14d" if FORM == "fw14" else f"emitsb_{FORM}"
IMAGE = "land" if LAND else "crumb3"
ARM = f"slots=0x1 entry=0 pds={IMAGE} pdsat=fw14 form={FORM}"
EMIT_WORD = f"emitpds.tasks.taske #0, r2, r3, r4, #0x{SIDEBAND:x}"
EMIT = {STEP: EMIT_WORD}
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SOURCE = f"asm/fwtask/{BLOB}.s"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1 = 0x5A5A3301           # entry 0's marker (slot 1 dword 0)
X0 = 0x5A5A3303           # past the emit (slot 1 dword 2)
M4 = 0x5A5A3302           # entry 1's marker (slot 4)
S1 = 0x5A5A3304           # entry 1's first store (slot 5 dword 0)
MA, MB = 0x5A5A3A18, 0x5A5A3A1A           # land's markers (asm/fwtask/pds/land.s)
ATT_A, ATT_B = 24, 26                     # their secondary attributes
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5 = 0x44, 0x48, 0x4C, 0x50, 0x54
X0_AT, S1_AT = SLOT1 + 2, SLOT5           # dwords 70 and 84
FILL = 0xDEADC0DE
FILL_AT, FILL_N = SLOT_PA, 16             # slots 2, 3, 4 and 5 (dwords 72-87)
PRE_AT, POST_SA_AT, POST_PA_AT = 128, 160, 192     # the survey (N3e §3.1), every row's blob
SURVEY_FILL_AT, SURVEY_FILL_N = 128, 96   # dwords 128-223 (the design's fill)
TIMEOUT_MS = 200
T3 = 0x005A3305                           # crumb3's dword 7
# the hooks' fallback for V0-V3 (a snap0 without ta3dctl lines: the kit mock's fake regs only):
# TA3DCtl dwords 0-3 in a kept snap0 of r35-sa (E1144), module 7CE8E38E
SNAP_PIN = "data:render/closing-r35-sa/out/20261118-085610/a/c0a-k.snap0.regs.gz"
ROWNAMES = [("c1-a", "fit")]
DESIGN = f"n3e design §3.3 (row {STEP})"


def m_table(s):
    """§3's common table (ST's): T = 0x0acc in snap9 and the stop dump; no tick band."""
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


# row L (n3e §3.3): no tim, so T runs in every outcome; DONE split by `lland` (score.py lland_of)
LLANDS = {"SA": "post sa24 = Ma and sa26 = Mb, pre not: douta writes the secondary attribute its "
                "control names [predicted: held]",
          "SHIFT": "Ma at post sa j and Mb at sa j+2, j != 24, pre not [predicted: failed]",
          "PA": "Ma and Mb in post pa0-pa15, no sa pair [predicted: failed]",
          "ONE": "only one marker found (sa or pa) [predicted: failed]",
          "NONE": "DONE but neither marker found in post sa0-sa31 or pa0-pa15 [predicted: failed]"}


def l_table():
    done = {"T": "running", f"res:0x{S1_AT:x}": f"0x{S1:08x}", f"res:0x{SLOT4:x}": f"0x{M4:08x}",
            f"res:0x{SLOT4 + 1:x}": "@runid", "res:0x2": "0x2"}
    out = {"L-NEVER": {"T": "running", f"res:0x{S1_AT:x}": "fill", f"res:0x{SLOT4:x}": "fill",
                       "res:0x2": "0x0"},
           "L-E1": {"T": "running", f"res:0x{S1_AT:x}": f"0x{S1:08x}", f"res:0x{SLOT4:x}": "fill",
                    "res:0x2": "0x0"}}
    for k in LLANDS:
        out[f"L-{k}"] = dict(done, lland=k)
    return out


# {model: {quantity: value}}. Values: 0xV; `fill` (the host's fill); `@runid`; `running` (T: bit
# 24 set, bits 23:0 at most 400000, two reads differ); for L, `lland` a label of LLANDS
OUTCOMES = {STEP: l_table() if LAND else m_table(STEP)}
MEANING = {
    "NEVER": "the program never started (T running, S1 fill)",
    "T1": "started, stopped at a douta",
    "T2": "stopped at the doutu",
    "T3": "doutu issued, entry 1 never stored",
    "E1": "entry 1 started, stopped after S1",
    "DONE": "all ran",
}


def predicted(s):
    """The row's frozen H-DM and H-ALL lines (n3e §3.2-§3.3)."""
    hdm, hall = ROWS[s][2], ROWS[s][3]
    return (f"H-DM predicts {hdm}" if hdm != "-" else "H-DM: no prediction") + "; " + \
        (f"H-ALL predicts {hall}" if hall != "-" else "H-ALL: no prediction")


def what(s, k):
    if s == "L":
        return {"NEVER": "land never reached entry 1 (S1 fill, T running: no tim, so never "
                         "started and stopped before entry 1 read alike): the landing cannot tell",
                "E1": "entry 1 started, stopped after S1: the landing needs DONE"}.get(k) or \
            f"all ran; landing {k}: {LLANDS[k]}"
    run = "NEVER" if k == "NEVER" else "RUN"
    return f"{MEANING[k]} (sideband 0x{ROWS[s][1]:03x} reads {run}; {predicted(s)})"


WHAT = {f"{STEP}-{k.split('-', 1)[1]}": what(STEP, k.split("-", 1)[1]) for k in OUTCOMES[STEP]}
# the controls (every row; all can fail): ST's PG, E0, T0 and B; L adds D0's P0 and P1
CONTROLS = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
            (f"res:0x{SLOT1:x}", f"0x{M1:08x}", "E0: entry 0 ran this command (slot 1 marker)"),
            (f"res:0x{SLOT1 + 1:x}", "@runid", "E0: entry 0 ran this command (slot 1 run id)"),
            ("res:0x1", "0x0", "E0: cmd 0 (entry 0 cleared it)"),
            ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
            ("snap9:0x0c08", "0x0", "B: no BIF fault after the job (a fault is its own outcome)"),
            ] + ([("survey:p0", "true", "P0: every pre dword overwritten (no 0xdeadc0de left in "
                                        "128-159)"),
                  ("survey:p1", "true", "P1: pre sa0-sa3 = TA3DCtl dwords 0-3 of snap0 (the EDM's "
                                        "own, E002)")] if LAND else [])


def snap_v():
    """TA3DCtl dwords 0-3 of the pinned snap0 (`ta3dctl 0xOO 0xVVVVVVVV` lines)."""
    t = pins.blob(SNAP_PIN).decode()
    v = {int(m.group(1), 16) // 4: int(m.group(2), 16)
         for m in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$", t, re.M)}
    return [v[i] for i in range(4)]


def source_facts():
    """What the blob's source stores where, read at the frozen commit: the res patches (byte
    offsets), the markers in order, the attribute reads, the emit count and the breadcrumbs'
    places."""
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
    survey = ', "%d": [%s]' % (SURVEY_FILL_AT, ", ".join([str(FILL)] * SURVEY_FILL_N))
    return ('{"cmd": 1, "params": {"%d": [%s]%s}, "timeout_ms": %d, "ticks": true}'
            % (FILL_AT, fill, survey, TIMEOUT_MS))


def tables():
    own = ["#stage own",
           "#limit 0",
           f"# own: N3e row {STEP} (closing29/n3e/design.md §3.3), the task {BLOB}",
           f"# armed once ({ARM}); one command 1 with ticks (no kick: the timer pass),",
           "# the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first. One row by design: any",
           "# stop ends the session (rc 4);",
           "# run/hooks.sh stops it (rc 24, on_stop end) after an ok end whose markers, run id,",
           "# cmd, state or sa0-sa3 are wrong."]
    for n, st in ROWNAMES:
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
    for n, st in ROWNAMES:
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
    out = [f"STEP {STEP}", f"ARM {ARM}", f"BLOB {BLOB}", f"IMAGE {IMAGE}", f"FORM {FORM}",
           f"SIDEBAND 0x{SIDEBAND:03x}", f"EMIT {EMIT_WORD}", f"HDM {HDM}", f"HALL {HALL}",
           "KICK none", f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}", f"S1 0x{S1:08x}",
           f"T3 0x{T3:08x}", f"PRE {PRE_AT}", f"POST_SA {POST_SA_AT}", f"POST_PA {POST_PA_AT}"]
    out += [f"MA 0x{MA:08x} sa{ATT_A}", f"MB 0x{MB:08x} sa{ATT_B}"] if LAND else []
    return "\n".join(out + [f"V{i} 0x{x:08x}" for i, x in enumerate(v)]) + "\n"


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
