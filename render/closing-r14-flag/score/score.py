#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r14-flag's scorer, frozen before the run. Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
c58f9f9c87aa, pinned in FROZEN.commits); f2's dumps through score/lib_dump.py (r10-geo's, a byte
copy with its pbdump_dump.py and region_tiles_dump.py, pinned) and gen/q139even.py (r10-geo's).
Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py dumps f2 KEPT_DIR           f2 with its dumps: the slot and flag verdicts as well
  score.py gate STAGE ROOTS...         exit 0 (no stage is gated: f1's stop ends the session)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

f1 (Q078): readings of a row: end (the runner's class: ok, fault, hang; fail reads nothing), image
(the sha256 of the 2048 `row Y:` tokens, "%08x", raster order, of an ok probe), fpage (a fault's
last kernel `BIF fault S at A` line: A's page from the probe's `scratch at` address, "+0x..."),
fstat (S). A model's row is held when every quantity it predicts equals the reading, FAILED when
one differs, cannot tell when a reading is missing or the row's control did not pass (f1-tw32's is
f1-ref-a, f1-small's and f1-zero's f1-ref-b). READING lines decode an ok bit-14 image: how many
pixels name a scratch dword, the largest, and each frozen form's pixels.
f2 (Q139): a control passes iff it drew exactly (and, with `dumps`, its dump gives one header with a
stream for every target tile, lib_dump.baseline_layout: the header base of its size, and its slots
are H-EVEN's = R7-BLK's at the rule's words). A planned row: end against H-COVER (ok) and H-FAULT23
(fault); with `dumps`, if it drew and dumped, every target tile's header slot (observed_slots from its size's base)
against H-EVEN and R7-BLK (blkrow) (all tiles, a tile with no header where the model has none),
and the headers with flag bit 7 (exactly one, at the frozen slot) and the image's wrong tiles
against H-LASTBLOCK and H-HIGHSLOT. A row whose size's control did not pass is cannot tell; a
faulted row is cannot tell for the slot and flag models (t10 dumps nothing after a failed render).

REQUIRED: the per-row files every kept row has (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what the scorer reads; producible(row) is the set of reading
keys a row's job can produce (the generator refuses a control that reads anything else)."""
import hashlib
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
# f2's dumps are not REQUIRED: a planned row that faults has none (t10 dumps nothing after a failed
# render) and the kit checks REQUIRED on every kept row (no per-class REQUIRED: README.md, kit
# need). So the kit's `score.py f2` reads only the text and kernel slices (ends, the controls'
# images), and `score.py dumps f2 KEPT_DIR` reads the dumps where they were kept (the slot and
# flag verdicts; a missing dump is cannot tell); hook_check stops f2 on an ok row without its dump
# line, so every row that drew has its dump.
REQUIRED = {"f1": (".txt", ".dmesg") + FIXED, "f2": (".txt", ".dmesg") + FIXED}
ROW = re.compile(r"row (\d+): ([0-9a-fA-F ]+)$", re.M)
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
SCRATCH = re.compile(r"scratch at (0x[0-9a-f]+) \((\d+) KiB\)")
F1_GATE = {"f1-tw32": "f1-ref-a", "f1-small": "f1-ref-b", "f1-zero": "f1-ref-b"}
F1_FORMS = ("H-TWP4096", "H-TWP4128", "H-TWP4096-NS", "H-MOVE0")
CLAIM_F1 = "T3 bit 14 on a twiddled 32 x 32 texture, 256 scratch pages"


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"]:
        return {"pixels"}
    if a[:1] == ["tri"]:
        keys = {"job", "hash", "diff"}
        if "--pixels" in a:
            keys.add("pixels")
        if "--dump-render" in a:
            keys.add("dump")
        return keys
    return set()


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n, r in cases.items():
        K.text(d, n + ".txt")
        K.text(d, n + ".dmesg")


# ================================================================================ f1
def pixels(text, n):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = m.group(2).split()
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [t.lower().zfill(8) for y in sorted(rows) for t in rows[y]]
    return px if len(px) == n else None


def fault_line(dmesg):
    f = FAULT.findall(dmesg or "")
    return f[-1] if f else None


def f1_reading(name, cases, d):
    """({quantity: value}, the image's tokens or None) of a kept row ({} when it did not run)."""
    r = cases.get(name)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return {}, None
    out, px = {"end": r["class"]}, None
    text, dm = K.text(d, name + ".txt"), K.text(d, name + ".dmesg")
    sc = SCRATCH.search(text or "")
    if r["class"] == "ok":
        px = pixels(text, 2048)
        if px is not None:
            out["image"] = hashlib.sha256(" ".join(px).encode()).hexdigest()
    if r["class"] == "fault":
        fl = fault_line(dm)
        if fl:
            a = int(fl[1], 16)
            out["fstat"] = fl[0]
            out["fpage"] = f"+{(a & ~0xFFF) - int(sc.group(1), 16):#x}" if sc else f"{a & ~0xFFF:#x}"
            if sc:
                inside = (a & ~0xFFF) - int(sc.group(1), 16) < int(sc.group(2)) * 1024
                out["fwhere"] = "inside the scratch" if inside else "past the scratch"
    return out, px


def model_state(pred, rd):
    if not rd:
        return None
    if pred.get("end") is not None and rd.get("end") != pred["end"]:
        return False
    states = [None if rd.get(q) is None else str(rd.get(q)) == v for q, v in pred.items() if q != "end"]
    if any(s is False for s in states):
        return False
    if any(s is None for s in states):
        return None
    return True


def decode(name, px):
    """A READING line: what an ok bit-14 image reads (each token a scratch dword's name or not),
    and each frozen form's agreement, pixel by pixel."""
    vals = [int(t, 16) for t in px]
    named = [v & 0x0FFFFFFF for v in vals if v >> 28 == 0xD]
    parts = [f"{len(named)} of 2048 pixels name a scratch dword"]
    if named:
        parts.append(f"dwords {min(named)} to {max(named)}")
    for m in F1_FORMS:
        p = os.path.join(KP, "predictions/f1", f"{name}.{m}.txt")
        if os.path.exists(p):
            want = open(p).read().split()
            parts.append(f"{m} {sum(a == b for a, b in zip(px, want))} of 2048")
    return f"READING {name}: " + "; ".join(parts)


def score_f1(d):
    preds = K.predictions(KP, "f1")
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, "f1")
    reads = {r["name"]: f1_reading(r["name"], cases, d) for r in table}
    controls, lines, per_model = {}, [], {}
    for r in table:
        n = r["name"]
        if r["set"] != "control":
            continue
        p = {q: next(iter(mv.values())) for q, mv in preds.get(n, {}).items()}
        st = model_state(p, reads[n][0])
        controls[n] = st
        lines.append(f"CONTROL {n}: {reads[n][0] or 'no reading'} (frozen {p}): {cword(st)}")
    for r in table:
        n = r["name"]
        if r["set"] == "control":
            continue
        rd, px = reads[n]
        gate = SK.gate({F1_GATE[n]: controls.get(F1_GATE[n])})
        if px is not None:
            lines.append(decode(n, px))
        models = {}
        for q, mv in preds.get(n, {}).items():
            for m, v in mv.items():
                models.setdefault(m, {})[q] = v
        for m, p in sorted(models.items()):
            st = SK.gated(gate, model_state(p, rd))
            per_model.setdefault(m, []).append(st)
            lines.append(f"ROW {n} {m}: {rd or 'no reading'} (frozen {p}): {word(st)}")
    for m, rows in sorted(per_model.items()):
        lines.append(f"SUMMARY: f1: {m}: " + SK.headline(CLAIM_F1, controls, rows))
    return lines


# ================================================================================ f2
def frozen_slots(name, m, one):
    import q139even as E
    body = open(os.path.join(KP, "predictions", "f2", f"{name}.{m}.slots")).read()
    if "sha256:" + hashlib.sha256(body.encode()).hexdigest() != one(name, "slots", m):
        raise SystemExit(f"score.py: {name} {m}: the slots file is not the frozen one")
    return E.slots_parse(body.strip())


def f2_job(d, cases, n, dumps=True):
    import lib_dump as L
    r = cases.get(n)
    if r is None:
        return None, "did not run"
    if r["class"] != "ok":
        return None, f"ended {r['class']}"
    j = dict(text=K.text(d, n + ".txt"), param=None, tadata=None)
    if not dumps:
        return j, "read"
    j.update(param=L.read_bytes(os.path.join(d, n + ".tri.param.bin")),
             tadata=L.read_bytes(os.path.join(d, n + ".tri.tadata.bin")))
    if not j["tadata"] or not j["param"]:
        return None, "no dump"
    return j, "read"


def slot_agree(pred, obs):
    return sum(1 for t, v in pred.items()
               if (v is None and not obs.get(t)) or (v is not None and v in obs.get(t, [])))


def flagged(tadata, base):
    import lib_dump as L
    return sorted(i for i, c, r, fl, st in L.headers(tadata, base, stop_zero=1 << 30) if fl & 0x80)


def score_f2(d, dumps=False):
    import lib_dump as L
    P, cases, lines = K.predictions(KP, "f2"), K.rows(d, "cases.tsv"), []
    tab = K.table(KP, "f2")
    one = lambda n, q, m: P.get(n, {}).get(q, {}).get(m)  # noqa: E731
    size = {t["name"]: tuple(int(x) for x in one(t["name"], "size", "all").split("x")) for t in tab}
    ctl, lay, ctl_of = {}, {}, {}
    for t in tab:
        n = t["name"]
        w, h = size[n]
        if t["set"] != "control":
            ctl_of[n] = next(c for c in ctl if size[c] == (w, h))
            continue
        j, why = f2_job(d, cases, n, dumps)
        if j is None:
            ctl[n] = None
            lines.append(f"CONTROL {n}: cannot tell ({why})")
            continue
        complete, bad = L.image_tiles(j["text"], w, h)
        if not dumps:
            ctl[n] = bool(complete and not bad)
            lines.append(f"CONTROL {n}: image {'complete' if complete else 'INCOMPLETE'}, {len(bad)} "
                         f"wrong tiles (its dump: score.py dumps f2): {cword(ctl[n])}")
            continue
        ok, txt, ly = L.baseline_layout(j["tadata"], j["param"], w, h)
        agree = 0
        if ok:
            pred = frozen_slots(n, "H-EVEN", one)
            agree = sum(1 for tl, v in pred.items() if ly["slot"].get(tl) == v)
        ctl[n] = bool(complete and not bad and ok and agree == len(L.target_tiles(w, h)))
        if ctl[n]:
            lay[(w, h)] = ly
        lines.append(f"CONTROL {n}: image {'complete' if complete else 'INCOMPLETE'}, {len(bad)} wrong "
                     f"tiles; {txt}; H-EVEN slots {agree} of {len(L.target_tiles(w, h))}: {cword(ctl[n])}")
    st = {m: [] for m in ("H-COVER", "H-FAULT23", "H-EVEN", "blkrow", "H-LASTBLOCK", "H-HIGHSLOT")}
    for t in tab:
        n = t["name"]
        if t["set"] == "control":
            continue
        w, h = size[n]
        gate = SK.gate({ctl_of[n]: ctl.get(ctl_of[n])})
        r = cases.get(n)
        end = r["class"] if r is not None and r["class"] in ("ok", "fault", "hang") else None
        fl = fault_line(K.text(d, n + ".dmesg")) if end == "fault" else None
        for m in ("H-COVER", "H-FAULT23"):
            s = SK.gated(gate, None if end is None else end == one(n, "end", m))
            st[m].append(s)
        lines.append(f"ROW {n} end: {end or 'no reading'}"
                     + (f" (BIF fault {fl[0]} at {fl[1]})" if fl else "")
                     + f"; H-COVER (ok) {word(st['H-COVER'][-1])}, H-FAULT23 (fault) "
                     f"{word(st['H-FAULT23'][-1])}")
        if not dumps:
            continue
        j, why = f2_job(d, cases, n)
        comp = None
        if j is not None:
            comp, bad = L.image_tiles(j["text"], w, h)
        if j is None or not comp or (w, h) not in lay:
            for m in ("H-EVEN", "blkrow", "H-LASTBLOCK", "H-HIGHSLOT"):
                st[m].append(SK.gated(gate, None))
            lines.append(f"ROW {n}: slots and flag cannot tell ("
                         + (why if j is None else "image not whole" if not comp
                            else f"no baseline layout of {w}x{h}") + ")")
            continue
        obs = L.observed_slots(j["tadata"], lay[(w, h)]["base"], w, h)
        parts = []
        for m in ("H-EVEN", "blkrow"):
            pred = frozen_slots(n, m, one)
            ag = slot_agree(pred, obs)
            st[m].append(SK.gated(gate, ag == len(pred)))
            parts.append(f"{m} slots {ag} of {len(pred)} ({word(st[m][-1])})")
        lines.append(f"ROW {n}: {len(bad)} wrong tiles; " + "; ".join(parts))
        last = flagged(j["tadata"], lay[(w, h)]["base"])
        for m in ("H-LASTBLOCK", "H-HIGHSLOT"):
            ok = len(last) == 1 and str(last[0]) == one(n, "flagslot", m) and \
                L.tiles_text(bad) == one(n, "image", m)
            st[m].append(SK.gated(gate, ok))
        lines.append(f"ROW {n} flag: bit 7 at slots {last[:4]}; H-LASTBLOCK (slot "
                     f"{one(n, 'flagslot', 'H-LASTBLOCK')}) {word(st['H-LASTBLOCK'][-1])}, H-HIGHSLOT "
                     f"(slot {one(n, 'flagslot', 'H-HIGHSLOT')}) {word(st['H-HIGHSLOT'][-1])}")
    claims = {"H-COVER": "a job at fx 2 or 3 mod 4 whose first macrotile covers the target draws",
              "H-FAULT23": "a job at fx 2 or 3 mod 4 faults",
              "H-EVEN": "a block row of the first macrotile takes 8 floor(fx / 2) slots (E950), every slot",
              "blkrow": "R7-BLK: 16 floor(fx / 4) slots a block row (E907), every slot",
              "H-LASTBLOCK": "the one bit-7 header is the last target tile's in block order",
              "H-HIGHSLOT": "the one bit-7 header is the highest target slot's"}
    for m, rows in st.items():
        if rows or dumps:
            lines.append(f"SUMMARY: f2: {m}: " + SK.headline(claims[m], ctl, rows))
    if not dumps:
        lines.append("NOTE: f2's slot and flag verdicts (H-EVEN, R7-BLK, H-LASTBLOCK, H-HIGHSLOT) read "
                     "the dumps: python3 score/score.py dumps f2 KEPT_DIR")
    return lines


SCORERS = {"f1": score_f1, "f2": score_f2}


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (no stage is gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 4 and argv[1:3] == ["dumps", "f2"]:
        print("\n".join(score_f2(argv[3], dumps=True)))
        return 0
    if len(argv) >= 3 and argv[1] in SCORERS:
        print("\n".join(SCORERS[argv[1]](argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
