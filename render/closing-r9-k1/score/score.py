#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-k1's scorer (Q190's layered background; closing9/k1/exp-k1-r9.md section 3). Every
verdict rule comes from kit/scorekit.py, the kept files are read through kit/kitscore.py (byte
copies of resgx545 d95a26469000, pinned in FROZEN.commits); the model is gen/bgl_model.py (frozen),
and every texel-map prediction is recomputed from it and checked against predictions/STAGE.tsv
before it is used (a mismatch is an error: exit 1, no SUMMARY).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when STAGE may run (GATE_RULES below)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Scored pixels: the 3034 background pixels of the hardware's 64 x 64 image (gen/bgmask.txt).

Gates (session.toml `gate = true`; ROOTS newest attempt first):
  s0p  s0t's c-off and c-tex:built passed (H-BUILT: the 23-word object, the tag's one layer)
  s1n  as s0p, s0p's c-pos-off and c-pos passed, and H-NONE held at c-rawu and c-rawv
  s1   every control of s0t and s0p passed (H-BUILT, H-TEX, c-noop, H-POS, H-ITER u and v)
  s2   s1 ran: H-VM right on >= 28 of the 30 held-out rows, and H-LM, H-SWAP and H-NOREAD each
       wrong on >= 3 (plan: else skip s2 and s3)
  s3   as s2
  s4   as s0p and s0p's c-pos passed (the end controls run whenever the layer was built)"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
import bgl_model as M  # noqa: E402
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

TRI_FILES = (".txt", ".tri.param.bin", "cases.tsv", "void.tsv")
CTL_FILES = (".txt", ".tri.param.bin", ".words.1.txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"s0t": CTL_FILES, "s0p": (".txt", "cases.tsv", "void.tsv", "readings.tsv"),
            "s1n": TRI_FILES, "s1": TRI_FILES, "s2": TRI_FILES, "s3": TRI_FILES,
            "s4": CTL_FILES}
HELDOUT_RIGHT = 28          # s1 gate: H-VM right on >= 28 of 30 held-out rows
RIVAL_WRONG = 3             # ... and every rival wrong on >= 3
S1_RIVALS = ("H-LM", "H-SWAP", "H-NOREAD")
CLAIMS = {
    "s0t": "H-BUILT and H-TEX: the render's object is the 23-word one-layer form and its "
           "background samples the source's identity texels",
    "s0p": "H-POS and H-ITER: the background primary works with the layer, and the layer's "
           "coordinate set iterates u = (x + 0.5) / 64, v = (y + 0.5) / 64",
    "s1n": "H-NONE: the layer's coordinates are not iterated (one texel whatever the poke)",
    "s1": "H-VM + H-AFF: words 3-8 are (u, v) of TL, TR, BL, the plane at the pixel centre",
    "s2": "H-VBOX: the plane is anchored at the render box, whatever words 15-22 say",
    "s3": "H-FMT0 (explore): words 9-14 and bgobj_words[1] at 0, 1 or 4 rows change nothing",
    "s4": "the end controls: the layer and the layerless render as at the start",
}


def producible(row):
    a = row["args"].split()
    layer = {"inplace", "layer"} if "--bg-layer" in a else set()
    if a[:1] == ["tri"]:
        return {"job", "hash", "diff"} | layer
    if a[:2] == ["probe", "--tri"] and "--pixels" in a:
        return {"rows"} | ({"layer"} if "--bg-layer" in a else set())
    return set()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    if "readings.tsv" in REQUIRED[stage]:
        K.readings(d)
    for n in cases:
        for s in REQUIRED[stage]:
            if s.startswith("."):
                M.gz(os.path.join(d, n + s))


def _state(v):
    return "PASS" if v is True else "FAILED" if v is False else "cannot tell"


def _held(v):
    return "held" if v is True else "FAILED" if v is False else "cannot tell"


def done(cases, n):
    return n in cases and K.completed(cases[n])


def image(d, n):
    return M.tri_rows(K.text(d, n + ".txt"))


def pimage(d, n):
    return M.probe_rows(K.text(d, n + ".txt"))


def identity(img, mask):
    """H-TEX: the background pixels that are their own texel: (state, matched)."""
    m = sum(1 for x, y in mask if y in img and x < len(img[y]) and img[y][x] == M.texel(x, y))
    if not all(y in img for _, y in mask):
        return None, m
    return (True if m >= M.RAW_RIGHT else False if m < M.RAW_WRONG else None), m


def obj_of(d, n):
    return M.object_words(M.gz(os.path.join(d, n + ".tri.param.bin")))


def built(d, n):
    """H-BUILT: the tag says one layer (rd:18 bits 30:25 = 1) and words 3-10 are the kernel's."""
    wt = M.gz(os.path.join(d, n + ".words.1.txt"))
    lay = M.bg_layers(wt.decode(errors="replace")) if wt else None
    o = obj_of(d, n)
    if lay is None or o is None:
        return None, "layers %s, object %s" % (lay, "unread" if o is None else "read")
    ok = lay == 1 and o[3:11] == [M.CTRL[w] for w in range(3, 11)]
    return ok, "layers %d, words 3-10 %s" % (lay, ",".join("0x%x" % w for w in o[3:11]))


def readback(d, n, pokes):
    """Whether every poked object word reads back after the job (None: no dump)."""
    o = obj_of(d, n)
    if o is None:
        return None
    return all(o[w] == v for w, v in pokes.items())


def pokes_of(row):
    """{word: value} of a row's --kpoke-render 1:bg:N=V options."""
    out = {}
    a = row["args"].split()
    for i, x in enumerate(a):
        if x == "--kpoke-render" and i + 1 < len(a) and a[i + 1].startswith("1:bg:"):
            w, v = a[i + 1][5:].split("=")
            out[int(w)] = int(v, 0)
    return out


def checked_preds(stage, mask):
    """{case: {model: prediction}} recomputed from the model, each equal to its frozen id."""
    preds = K.predictions(KP, stage)
    out = {}
    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {}).get("texmap", {})
        for m, frozen in want.items():
            if m not in M.TEX_MODELS:
                continue
            p = M.predict_tex(m, pokes_of(r), mask)
            if M.map_id(p) != frozen:
                raise SystemExit("score.py: %s %s: the model gives %s, the frozen prediction %s"
                                 % (n, m, M.map_id(p), frozen))
            out.setdefault(n, {})[m] = p
    return out


# ---- the stages ------------------------------------------------------------------------------
def verdicts(stage, d):
    """(controls {name: state}, rows [state], lines, extra) of a kept stage directory."""
    mask = M.load_mask()
    cases = K.rows(d, "cases.tsv")
    controls, rows, lines, extra = {}, [], [], {}
    if stage in ("s0t", "s4"):
        for r in K.table(KP, stage):
            n = r["name"]
            ok = done(cases, n)
            if n.startswith("c-off"):
                t = K.text(d, n + ".txt")
                good = ("job: ok\n" in t and "target: 64x64 hash %s\n" % M.HASH_OFF in t
                        and "diff: 0 of 4096 pixels\n" in t)
                controls[n] = good if ok else None
                lines.append("CONTROL %s: hash %s, diff 0 (E590): %s" % (n, M.HASH_OFF,
                                                                         _state(controls[n])))
                continue
            b, why = built(d, n) if ok else (None, "not completed")
            tex, m = identity(image(d, n), mask) if ok else (None, 0)
            if n == "c-noop":
                rb = readback(d, n, {5: M.ONE}) if ok else None
                controls[n] = tex if rb is not False else False
                lines.append("CONTROL c-noop: bg:5 = 0x3f800000 read back %s, identity texels "
                             "%d of %d: %s" % (rb, m, len(mask), _state(controls[n])))
                rows.append(controls[n])
                continue
            controls[n + ":built"] = b
            controls[n + ":tex"] = tex
            rows += [b, tex]
            lines.append("CONTROL %s:built: H-BUILT (%s): %s" % (n, why, _state(b)))
            lines.append("CONTROL %s:tex: H-TEX identity texels %d of %d: %s"
                         % (n, m, len(mask), _state(tex)))
        return controls, rows, lines, extra
    if stage == "s0p":
        for r in K.table(KP, stage):
            n = r["name"]
            ok = done(cases, n)
            img = pimage(d, n)
            if n.startswith("c-pos"):
                s, m = M.score_pos(img, mask) if ok else (None, 0)
                controls[n] = s
                lines.append("CONTROL %s: H-POS f32(x + 0.5) at %d of %d: %s"
                             % (n, m, len(mask), _state(s)))
                rows.append(s)
                continue
            comp = 0 if n == "c-rawu" else 1
            res = {h: (M.score_raw(h, comp, img, mask) if ok else (None, 0))
                   for h in ("H-ITER", "H-SWAP", "H-LM", "H-NONE", "H-17")}
            controls[n] = res["H-ITER"][0]
            extra[n] = {h: s for h, (s, _) in res.items()}
            rows.append(controls[n])
            lines.append("CONTROL %s: H-ITER %s at %d of %d: %s; rivals %s" % (
                n, "u" if comp == 0 else "v", res["H-ITER"][1], len(mask), _state(controls[n]),
                ", ".join("%s %s (%d)" % (h, _held(s), m) for h, (s, m) in res.items()
                          if h != "H-ITER")))
        return controls, rows, lines, extra
    # the texel stages: s1n, s1, s2, s3
    preds = checked_preds(stage, mask)
    head = {"s1n": "H-NONE", "s1": "H-VM", "s2": "H-VBOX", "s3": "H-VM"}[stage]
    tallies = {}
    for r in K.table(KP, stage):
        n = r["name"]
        ok = done(cases, n)
        pk = pokes_of(r)
        rb = readback(d, n, pk) if ok and pk else None
        img = image(d, n) if ok else {}
        res = {}
        for m, p in preds.get(n, {}).items():
            res[m] = M.score_tex(p, img, mask) if ok else (None, 0, 0)
            if pk and rb is not True:
                res[m] = (None,) + tuple(res[m][1:])     # the poke did not reach the object
            tallies.setdefault((r["set"], m), []).append(res[m][0])
        main = "H-VM" if head == "H-VBOX" else head
        st = res.get(main, (None,))[0]
        if r["set"] in ("heldout", "explore") or stage == "s1n":
            rows.append(st)
        lines.append("ROW %s [%s]: read back %s; %s" % (
            n, r["set"], {True: "yes", False: "NO", None: "-"}[rb] if pk else "(no bg poke)",
            "; ".join("%s %s (%d of %d)" % (m, _held(s), mm, sc)
                      for m, (s, sc, mm) in res.items())))
    for (sset, m), sts in sorted(tallies.items()):
        lines.append("TALLY %s %s: %s" % (sset, m, SK.tally(sts)))
    extra["tallies"] = tallies
    return controls, rows, lines, extra


def s1_gate(d):
    _, _, _, extra = verdicts("s1", d)
    t = extra["tallies"]
    vm = SK.tally(t.get(("heldout", "H-VM"), []))
    probs = []
    if vm.held < HELDOUT_RIGHT:
        probs.append("H-VM right on %d of the held-out rows (needs %d)" % (vm.held, HELDOUT_RIGHT))
    for rv in S1_RIVALS:
        w = SK.tally(t.get(("heldout", rv), []))
        if w.failed < RIVAL_WRONG:
            probs.append("%s wrong on %d held-out rows (needs %d)" % (rv, w.failed, RIVAL_WRONG))
    return probs


def gate_problems(stage, roots):
    def find(dep):
        for root in roots:
            p = os.path.join(root, dep)
            if os.path.isdir(p):
                return p
        return None

    def need(dep, names):
        d = find(dep)
        if d is None:
            return ["%s has not run" % dep]
        c = verdicts(dep, d)[0]
        g = SK.gate({k: c.get(k) for k in names} if names else c)
        return ["%s %s" % (dep, p) for p in g.problems]

    base = need("s0t", ("c-off", "c-tex:built"))
    if stage == "s0p":
        return base
    if stage == "s1n":
        probs = base + need("s0p", ("c-pos-off", "c-pos"))
        d = find("s0p")
        if d is not None:
            ex = verdicts("s0p", d)[3]
            for n in ("c-rawu", "c-rawv"):
                if ex.get(n, {}).get("H-NONE") is not True:
                    probs.append("%s: H-NONE did not hold" % n)
        return probs
    if stage == "s1":
        return need("s0t", ()) + need("s0p", ())
    if stage in ("s2", "s3"):
        d = find("s1")
        return ["s1 has not run"] if d is None else s1_gate(d)
    if stage == "s4":
        return base + need("s0p", ("c-pos",))
    return []


# the texel stages have no control row of their own: their headline is gated by the s0 controls
# they rest on (s1n by those that do not presume H-ITER)
_S0 = {"c-off": "s0t", "c-tex:built": "s0t", "c-tex:tex": "s0t", "c-noop": "s0t",
       "c-pos-off": "s0p", "c-pos": "s0p", "c-rawu": "s0p", "c-rawv": "s0p"}
BORROWED = {"s1": _S0, "s2": _S0, "s3": _S0,
            "s1n": {k: v for k, v in _S0.items() if k in ("c-off", "c-tex:built", "c-pos-off",
                                                        "c-pos")}}


def borrowed(stage, roots):
    out = {}
    for name, dep in BORROWED[stage].items():
        d = next((os.path.join(r, dep) for r in roots if os.path.isdir(os.path.join(r, dep))),
                 None)
        out[name] = verdicts(dep, d)[0].get(name) if d else None
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        if argv[2] == "s0t":
            return 0
        probs = gate_problems(argv[2], argv[3:])
        print("gate %s: %s" % (argv[2], "open" if not probs else "; ".join(probs)))
        return 1 if probs else 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, rows, lines, _ = verdicts(argv[1], argv[2])
        if argv[1] in BORROWED:
            controls = borrowed(argv[1], argv[3:] or [os.path.dirname(argv[2])])
            lines += ["CONTROL %s (of %s): %s" % (k, BORROWED[argv[1]][k], _state(v))
                      for k, v in controls.items()]
        print("\n".join(lines))
        print("SUMMARY: " + argv[1] + ": " + SK.headline(CLAIMS[argv[1]], controls, rows))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
