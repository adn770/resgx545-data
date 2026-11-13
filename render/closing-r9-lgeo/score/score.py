#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-lgeo's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(headline), the kept files are read through kit/kitscore.py (byte copies of resgx545 f32dfac,
pinned in FROZEN.commits); the models' frozen outputs are predictions/ (written by gen/lgen.py),
the readers gen/texmodel.py, gen/tx6model.py, gen/q139even.py (pure functions) and score/lib_dump.py
with its byte copies (r8-lgeo's, pinned). Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage of r9-lgeo is gated by another's controls)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Row states: held (True), FAILED (False), cannot tell (None). A job whose kept class is not ok
(rc 0, or rc 1 with `job: ok` and its diff line: expectdiff), a void (soft) row, an output without
its whole image or dump, is cannot tell, never a pass. Every stage's controls gate every row of
the stage (scorekit.headline).

tx6 (Q283): the 64 x 32 probe image (2048 dwords of `probe NAME: row N:` lines) against each
hypothesis's frozen pixels_sha; a control passes iff its image is the kept one; a row whose
`scratch at ... (N KiB)` line is not the frozen size cannot tell. Type 4 (seven windows): H-CEIL,
H-P2, H-PACK each over every row (rows where they agree count for each). Type 3 at format 5: the
16-bit words read back from the pixels (tx6model.word_of) against each rule's frozen words_sha;
whether the pixels are also sgx-sim's widening is printed, and a match of the high half first is
a reading (no verdict). The two linear type 1 rows are cannot tell unless their bridge (type 1
32 x 16 through the linear axis) gave E725's image.
q139b (Q139): the controls pass iff the image is exact (no wrong tile) and every target tile has
one header with a stream (lib_dump.baseline_layout): they give the header base. Their header
slots are then a held-out claim of H-EVEN (= R7-BLK there), as is the 768 x 640 m2-B3p1 row's
wrong-tile set and every header slot (lib_dump.observed_slots from the same size's base). The
1280 x 720 m2-B3p1 residue is a reading: its wrong tiles against its dataset's and each model's,
its slots against each model's."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import texmodel as T  # noqa: E402
import tx6model as X  # noqa: E402
import lib_dump as L  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"tx6": (".txt",) + FIXED, "q139b": (".txt", ".tri.param.bin", ".tri.tadata.bin") + FIXED}
GATES = {}
MODELS = ("H-EVEN", "blkrow", "raster", "blkdown", "mtblk")


def producible(row):
    a = row["args"]
    if a.startswith("probe"):
        return {"rows"}
    keys = {"hash"}
    if "--dump-render" in a:
        keys.add("dump")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        if stage == "q139b":
            L.read_bytes(os.path.join(d, n + ".tri.param.bin"))
            L.read_bytes(os.path.join(d, n + ".tri.tadata.bin"))


def done(cases, n):
    return n in cases and K.completed(cases[n])


def one(P, n, q, m):
    return P.get(n, {}).get(q, {}).get(m)


# ================================================================================ tx6
def tex_reading(d, cases, P, n):
    """(image or None, why)."""
    if not done(cases, n):
        return None, "not a completed job" if n in cases else "did not run (or void)"
    text = K.text(d, n + ".txt")
    want = one(P, n, "scratch", "all") or "64 KiB"
    m = re.search(r"^probe \S+: scratch at 0x[0-9a-f]+ \((\d+) KiB\)", text, re.M)
    if not m or "%s KiB" % m.group(1) != want:
        return None, "scratch %s, frozen %s" % (m.group(1) + " KiB" if m else "not printed", want)
    img = T.probe_rows(text)
    if len(img) != T.FW * T.FH:
        return None, "%d pixels, not 2048" % len(img)
    return img, "read"


def tex_rows(stage, d, cases, P, names, hyps, lines, q="pixels_sha", conv=None):
    """{hyp: [state per row]} over the named rows; conv turns an image into what q hashes."""
    out = {h: [] for h in hyps}
    tab = {t["name"]: t for t in K.table(KP, stage)}
    for n in names:
        img, why = tex_reading(d, cases, P, n)
        sha = None if img is None else T.sha_list(conv(img) if conv else img)
        got = []
        for h in hyps:
            want = one(P, n, q, h)
            s = None if sha is None or want is None else sha == want
            out[h].append(s)
            if s:
                got.append(h)
        lines.append("ROW %s (%s): %s; matches %s" % (n, tab[n]["set"], why if img is None else "image read",
                                                     ",".join(got) or ("none" if img is not None else "-")))
    return out


def score_tx6(d):
    P, cases, lines = K.predictions(KP, "tx6"), K.rows(d), []
    tab = K.table(KP, "tx6")
    ctl = {}
    for t in tab:
        if t["set"] != "control":
            continue
        n = t["name"]
        img, why = tex_reading(d, cases, P, n)
        want = one(P, n, "pixels_sha", "kept")
        ctl[n] = None if img is None else T.sha_list(img) == want
        lines.append("CONTROL %s: %s (kept image %s...): %s" % (n, why, want[:12], cword(ctl[n])))
    ty4 = [t["name"] for t in tab if t["set"] == "heldout" and t["name"].startswith("tx6-ty4-")]
    pad = [t["name"] for t in tab if t["set"] == "heldout" and t["name"].startswith("tx6-ty3-f5-")]
    lin = [t["name"] for t in tab if t["set"] == "heldout" and t["name"].startswith("tx6-lin-")]
    r4 = tex_rows("tx6", d, cases, P, ty4, X.TYPE4, lines)
    words = lambda img: [X.word_of(p) for p in img]  # noqa: E731
    r3 = tex_rows("tx6", d, cases, P, pad, X.PAD16, lines, q="words_sha", conv=words)
    for n in pad:
        img, _ = tex_reading(d, cases, P, n)
        if img is None:
            continue
        sha = T.sha_list(img)
        wsha = T.sha_list(words(img))
        widen = [h for h in X.PAD16 if one(P, n, "pixels_sha", h) == sha]
        hi = [h for h in X.PAD16 if one(P, n, "words_sha", h + ":hi") == wsha]
        alpha = sorted({p >> 24 for p in img})
        lines.append("READING %s: pixels are sgx-sim's widening of %s; the high half first matches %s; alpha bytes %s" % (
            n, ",".join(widen) or "no rule", ",".join(hi) or "none", " ".join("%02x" % a for a in alpha[:4])))
    br = tex_rows("tx6", d, cases, P, ["tx6-lin-ty1-32x16"], ("kept",), lines)["kept"]
    bridge = br[0] if br else None
    lines.append("BRIDGE tx6-lin-ty1-32x16 (type 1 through the linear axis gives E725's 32 x 16 image): %s" % word(bridge))
    rl = tex_rows("tx6", d, cases, P, lin, X.TYPE1, lines)
    if bridge is not True:
        rl = {h: [None] * len(v) for h, v in rl.items()}
    out = lines + ["SUMMARY: Q283 type 4 past a multiple of 32: " + SK.headline(
        "H-CEIL (ceil(w / 32) blocks a block row) held", ctl, r4["H-CEIL"])]
    out += ["SUMMARY: Q283 type 4 rival: " + SK.headline("%s held" % h, ctl, r4[h]) for h in X.TYPE4[1:]]
    out += ["SUMMARY: Q283 type 3 padding at a 16-bit format: " + SK.headline(
        "H-DW8 (rows max(8 dwords, w texels) apart) held", ctl, r3["H-DW8"])]
    out += ["SUMMARY: Q283 type 3 padding rival: " + SK.headline("%s held" % h, ctl, r3[h]) for h in X.PAD16[1:]]
    out += ["SUMMARY: Q283 type 1 at 24 and 40 wide (soft, bridge %s): " % word(bridge)
            + SK.headline("%s held" % h, ctl, rl[h]) for h in X.TYPE1]
    return out


# ================================================================================ q139b
def q139_job(d, cases, n):
    if not done(cases, n):
        return None, "not a completed job" if n in cases else "did not run"
    j = dict(text=K.text(d, n + ".txt"), param=L.read_bytes(os.path.join(d, n + ".tri.param.bin")),
             tadata=L.read_bytes(os.path.join(d, n + ".tri.tadata.bin")))
    if not j["tadata"] or not j["param"]:
        return None, "no dump"
    return j, "read"


def slots_of(n, model):
    import q139even as E
    return E.slots_parse(open(os.path.join(KP, "predictions/q139b/%s.%s.slots" % (n, model))).read().strip())


def slot_agree(pred, obs):
    return sum(1 for t, v in pred.items() if (v is None and not obs.get(t)) or (v is not None and v in obs.get(t, [])))


def score_q139b(d):
    P, cases, lines = K.predictions(KP, "q139b"), K.rows(d), []
    tab = K.table(KP, "q139b")
    size = {t["name"]: tuple(int(x) for x in one(P, t["name"], "size", "all").split("x")) for t in tab}
    ctl, lay, base_slots = {}, {}, []
    for t in tab:
        n = t["name"]
        if t["set"] != "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        if j is None:
            ctl[n] = None
            base_slots.append(None)
            lines.append("CONTROL %s: cannot tell (%s)" % (n, why))
            continue
        complete, bad = L.image_tiles(j["text"], w, h)
        ok, txt, ly = L.baseline_layout(j["tadata"], j["param"], w, h)
        ctl[n] = complete and not bad and ok
        if ctl[n]:
            lay[(w, h)] = ly
        lines.append("CONTROL %s: image %s, %d wrong tiles; %s: %s" % (
            n, "complete" if complete else "INCOMPLETE", len(bad), txt, cword(ctl[n])))
        if ctl[n]:
            pred = slots_of(n, "H-EVEN")
            agree = sum(1 for tl, v in pred.items() if ly["slot"].get(tl) == v)
            base_slots.append(agree == len(pred))
            lines.append("ROW %s (baseline slots): H-EVEN (= %s) %d of %d slots: %s" % (
                n, one(P, n, "same_as_H-EVEN", "all"), agree, len(pred), word(base_slots[-1])))
        else:
            base_slots.append(None)
    held = []
    for t in tab:
        n, sset = t["name"], t["set"]
        if sset == "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        comp = None
        if j is not None:
            comp, bad = L.image_tiles(j["text"], w, h)
        if j is None or not comp or (w, h) not in lay:
            if sset == "heldout":
                held.append(None)
            lines.append("ROW %s (%s): cannot tell (%s)" % (n, sset, why if j is None else "image not whole" if not comp
                                                           else "no baseline layout of %dx%d" % (w, h)))
            continue
        obs = L.observed_slots(j["tadata"], lay[(w, h)]["base"], w, h)
        parts, st = [], {}
        for m in MODELS:
            same = L.tiles_text(bad) == one(P, n, "wrong", m)
            pred = slots_of(n, m)
            ag = slot_agree(pred, obs)
            st[m] = same and ag == len(pred)
            parts.append("%s %s (wrong %s, slots %d of %d)" % (m, "yes" if st[m] else "no", "=" if same else "differs",
                                                               ag, len(pred)))
        if sset == "heldout":
            held.append(st["H-EVEN"])
        kept = one(P, n, "wrong", "kept")
        rep = "replicated" if L.tiles_text(bad) == kept else "NOT replicated (%d kept)" % len(L.tiles_parse(kept))
        lines.append("ROW %s (%s): %d wrong tiles; the dataset's image %s; %s" % (n, sset, len(bad), rep, "; ".join(parts)))
        if sset == "residue":
            extra = sorted(set(L.tiles_parse(L.tiles_text(bad))) - set(L.tiles_parse(one(P, n, "wrong", "H-EVEN"))),
                           key=lambda t: (t[1], t[0]))
            lines.append("READING %s: %d wrong tiles beyond H-EVEN's (%s); tiles with no header %d, with more than one %d" % (
                n, len(extra), L.tiles_text(extra)[:200], sum(1 for tl in L.target_tiles(w, h) if not obs.get(tl)),
                sum(1 for v in obs.values() if len(v) > 1)))
    out = lines + ["SUMMARY: Q139 the baselines' header slots at 1280 x 720 and 768 x 640: " + SK.headline(
        "H-EVEN (= R7-BLK at fx 12 and 8) gives every baseline header slot", ctl, base_slots)]
    out += ["SUMMARY: Q139 768 x 640 m2-B3p1: " + SK.headline(
        "H-EVEN (= R7-BLK and the round 8 orders there) predicts the wrong-tile set and every header slot", ctl, held)]
    return out


SCORERS = {"tx6": score_tx6, "q139b": score_q139b}


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        print("\n".join(SCORERS[argv[1]](argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
