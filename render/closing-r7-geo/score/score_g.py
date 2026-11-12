#!/usr/bin/env python3
"""score_g.py: r7-geo's scorers.  Every verdict rule comes from scorekit.py (a byte copy of resgx545 1c64f3a's
tools/closing/scorekit.py); the models from gen/models.py; the frozen predictions from predictions/STAGE.tsv.  Refuses to score when
the freeze does not verify (run/freeze_g.sh verify), unless R7G_NO_FREEZE_CHECK=1 (the offline tests on copies).

  score_g.py STAGE KEPT_DIR      ROW / CONTROL lines, then SUMMARY lines (exit 0; 2 usage; 3 the freeze does not verify)
  score_g.py verdict ATT_DIR     every stage's SUMMARY lines of an attempt (out/ATT)

Rows: cases.tsv (complete jobs), void.tsv (a soft row's failure or a gate's refusal: cannot tell); a table row in neither did not
run (cannot tell).  REQUIRED: the files each stage's scorer reads (sessioncheck.py kept checks them; read_files(STAGE, DIR) reads
exactly what score() reads, for its --call).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import hashlib  # noqa: E402
import os  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import numpy as np  # noqa: E402

import models as M  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("xf", "tx", "zd", "zi", "zf", "zs")
DUMP = ".depth.1.bin"
REQUIRED = {"xf": (".txt", "cases.tsv", "void.tsv"), "tx": (".txt", "cases.tsv", "void.tsv"), "zd": (".txt", DUMP, "cases.tsv", "void.tsv"),
            "zi": (".txt", "cases.tsv", "void.tsv"), "zf": (".txt", DUMP, "cases.tsv", "void.tsv"), "zs": (".txt", "cases.tsv", "void.tsv")}


# ---------------------------------------------------------------------------------------------------------------- reading
def _open(path):
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rb") as f:
            return f.read()
    with open(path, "rb") as f:
        return f.read()


def table(stage, kp=KP):
    out = []
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            n, s, risk, knobs, tool, args = ln.split("|", 5)
            out.append(dict(name=n, set=s, knobs=knobs.split(), tool=tool, args=args))
    return out


def preds(stage, kp=KP):
    P = {}
    for ln in open(os.path.join(kp, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        P.setdefault(c, {}).setdefault(q, {})[m] = v
    return P


def tsv_rows(d, name):
    p = os.path.join(d, name)
    if not os.path.exists(p) and not os.path.exists(p + ".gz"):
        return {}
    out = {}
    for ln in _open(p).decode().splitlines()[1:]:
        f = ln.split("\t")
        if f and f[0]:
            out[f[0]] = dict(rc=int(f[7]), cls=f[8], args=f[6])
    return out


def parse_out(text):
    r = dict(hash=None, tri=None, rows={}, diff=None)
    for ln in text.splitlines():
        if ln.startswith("target: ") and " hash " in ln:
            r["hash"] = int(ln.split()[3], 16)
        elif ln.startswith("tri ") and " triangle, " in ln and r["tri"] is None:
            r["tri"] = int(ln.split(": ")[1].split()[0])
        elif ln.startswith("diff: "):
            r["diff"] = ln
        elif ln.startswith("row "):
            y, _, rest = ln[4:].partition(":")
            r["rows"][int(y)] = [int(t, 16) for t in rest.split()]
        elif ln.startswith("probe ") and ": row " in ln:
            i = ln.index(": row ")
            y, _, rest = ln[i + 6:].partition(":")
            r["rows"][int(y)] = [int(t, 16) for t in rest.split()]
    return r


def image(r, w, h):
    rows = r["rows"]
    if len(rows) != h or any(len(rows.get(y, ())) != w for y in range(h)):
        return None
    return np.array([rows[y] for y in range(h)], dtype=np.uint64).astype(np.uint32)


def wh(args):
    a = shlex.split(args)
    if "--width" in a:
        return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
    return 64, 32


def tri_v(args):
    a = shlex.split(args)
    return [int(t) for t in a[a.index("--tri-v") + 1].split(",")]


def tri_z(args):
    a = shlex.split(args)
    return [M.Fraction(t) for t in a[a.index("--tri-z") + 1].split(",")]


def read_files(stage, d):
    """Read every file score() reads (sessioncheck.py kept --call)."""
    _open(os.path.join(d, "void.tsv"))
    for n in tsv_rows(d, "cases.tsv"):
        _open(os.path.join(d, n + ".txt"))
        if DUMP in REQUIRED[stage]:
            _open(os.path.join(d, n + DUMP))


def missing_files(stage, d):
    return SK.missing_files(REQUIRED[stage], d, list(tsv_rows(d, "cases.tsv")))


# ---------------------------------------------------------------------------------------------------------------- per stage
class Ctx:
    def __init__(self, stage, d, kp=KP):
        self.stage, self.d, self.kp = stage, d, kp
        self.T = table(stage, kp)
        self.P = preds(stage, kp)
        self.cases = tsv_rows(d, "cases.tsv")
        self.void = tsv_rows(d, "void.tsv")
        self.out = []

    def text(self, n):
        return _open(os.path.join(self.d, n + ".txt")).decode(errors="replace")

    def ok(self, n):
        return n in self.cases and self.cases[n]["cls"] == "ok"

    def say(self, *a):
        self.out.append(" ".join(str(x) for x in a))


def _ctl_eq(cx, n, q, got, model):
    want = cx.P[n][q][model]
    v = True if str(got) == want else (False if got is not None else None)
    cx.say("CONTROL", n, q, "got", got, "frozen", want, "PASS" if v else ("FAILED" if v is False else "cannot tell"))
    return v


def _h(v):
    return None if v is None else "0x%016x" % v


def score_xf(cx):
    ctl, rows = {}, {"INDEP": [], "XFIRST": [], "YFIRST": []}
    for t in cx.T:
        n = t["name"]
        h = parse_out(cx.text(n))["hash"] if cx.ok(n) else None
        if t["set"] == "control":
            ctl[n] = _ctl_eq(cx, n, "hash", _h(h), "E884")
            continue
        for m in rows:
            st = None if h is None else _h(h) == cx.P[n]["hash"]["H-" + m]
            rows[m].append(st)
        cx.say("ROW", n, "hash", _h(h), "matches", ",".join(m for m in rows if rows[m][-1]) or "none")
    for m, r in rows.items():
        cx.say("SUMMARY: Q206 both fields:", SK.headline("H-" + m + " held", ctl, r))


def score_tx(cx):
    ctl, obs = {}, {}
    for t in cx.T:
        n = t["name"]
        px = [v for y in sorted(parse_out(cx.text(n))["rows"]) for v in parse_out(cx.text(n))["rows"][y]] if cx.ok(n) else None
        obs[n] = None if px is None or len(px) != 2048 else M.sha_list(px)
        if t["set"] == "control":
            m = "E725" if "ty3" in n else "E894"
            ctl[n] = _ctl_eq(cx, n, "pixels_sha", obs[n], m)
    rows = {}
    for t in cx.T:
        n = t["name"]
        if t["set"] == "control":
            continue
        P = cx.P[n]
        ty = int(P["type"]["all"])
        if t["set"] == "memory":
            st = None if obs[n] is None or obs.get("tx-ty5-16x16") is None else obs[n] == obs["tx-ty5-16x16"]
            rows.setdefault("H-STEP (memory: the image does not follow the texture)", []).append(st)
            cx.say("ROW", n, "same as the plain 16 x 16:", st)
            continue
        hyps = list(P["pixels_sha"])
        hit = [h for h in hyps if obs[n] is not None and P["pixels_sha"][h] == obs[n]]
        cx.say("ROW", n, "type", ty, "matches", ",".join(hit) or ("none" if obs[n] else "cannot tell"))
        for h in hyps:
            key = "type %d %s" % (ty if ty == 5 else (ty if ty == 4 else 13), h)
            rows.setdefault(key, []).append(None if obs[n] is None else h in hit)
    for k, r in sorted(rows.items()):
        claim = ("Q283 types 1 and 3 " + k.split()[2]) if k.startswith("type 13") else (
            "Q283 type 4 " + k.split()[2] if k.startswith("type 4") else "Q178 " + k)
        cx.say("SUMMARY: %s:" % claim, SK.headline(claim + " held", ctl, r))


def _cov_from_depth(raw, w, h):
    buf = np.frombuffer(raw, dtype="<u4")
    img = buf[M.depth_index(w, h)]
    return img, (img != M.FILL) & (img != M.ONE) & (M.f32(img) < 1.0)


def _zls(raw, w, h):
    """(dead: tile-area dwords still 0xdeadbeef, outside: dwords outside the tile area not 0xdeadbeef)"""
    buf = np.frombuffer(raw, dtype="<u4")
    aw, ah = M.G.area(w, h)
    idx = M.depth_index(aw, ah).ravel()
    mask = np.zeros(buf.size, dtype=bool)
    mask[idx[idx < buf.size]] = True
    return int(np.count_nonzero(buf[mask] == M.FILL)), int(np.count_nonzero(buf[~mask] != M.FILL))


def d_row(cx, n, args):
    """(coverage state, zls state, depth state, note) of one D row."""
    w, h = wh(args)
    v, z = tri_v(args), tri_z(args)
    P = cx.P[n]
    r = parse_out(cx.text(n))
    raw = _open(os.path.join(cx.d, n + DUMP))
    pred_cov = M.cover(v, w, h)
    img = image(r, w, h)
    dimg, dcov = _cov_from_depth(raw, w, h)
    obs_cov = (img == M.GREEN) if img is not None else dcov
    other = int(np.count_nonzero((img != M.GREEN) & (img != M.BG))) if img is not None else 0
    cov_ok = bool((obs_cov == pred_cov).all()) and other == 0 and r["tri"] == int(P["tri"]["H-E606"])
    if P["hash"]["H-E606"] != "-":
        cov_ok = cov_ok and _h(r["hash"]) == P["hash"]["H-E606"]
    dead, outside = _zls(raw, w, h)
    zls_ok = dead == 0 and outside == 0
    planev = M.plane_image(v, z, w, h)
    err = np.abs(M.f32(dimg) - planev) / M.U
    cerr = float(err[pred_cov].max()) if pred_cov.any() else 0.0
    dep_ok = (bool((dcov == pred_cov).all()) and cerr <= M.DEPTH_TOL) if pred_cov.any() else None
    wrong = int(np.count_nonzero(obs_cov != pred_cov))
    cx.say("ROW", n, "%dx%d" % (w, h), "coverage", "exact" if cov_ok else "WRONG %d px (other %d, tri %s)" % (wrong, other, r["tri"]),
           "zls dead %d outside %d" % (dead, outside), "depth max %.2f U" % cerr, "depth<1 = covered" if (dcov == pred_cov).all() else
           "depth<1 != covered (%d)" % int(np.count_nonzero(dcov != pred_cov)))
    return cov_ok, zls_ok, dep_ok, r, raw


def _void_note(cx, t):
    n = t["name"]
    if n in cx.void:
        cx.say("ROW", n, "void (rc %d: soft failure or gate refusal): cannot tell" % cx.void[n]["rc"])
    elif n not in cx.cases:
        cx.say("ROW", n, "not run: cannot tell")
    else:
        cx.say("ROW", n, "class", cx.cases[n]["cls"], ": cannot tell")


def score_d(cx, label):
    ctl, by = {}, {}
    for t in cx.T:
        n = t["name"]
        size = cx.P[n]["size"]["all"]
        if not cx.ok(n):
            _void_note(cx, t)
            if t["set"] == "control":
                ctl[n] = None
            else:
                for k in ("H-E606", "H-ZLS", "H-DEPTH"):
                    by.setdefault(k, {}).setdefault(size, []).append(None)
            continue
        cov, zls, dep, r, raw = d_row(cx, n, t["args"])
        if t["set"] == "control":
            a = _ctl_eq(cx, n, "hash", _h(r["hash"]), "E606")
            b = _ctl_eq(cx, n, "tri", r["tri"], "E606")
            c = _ctl_eq(cx, n, "dump_sha", hashlib.sha256(raw).hexdigest(), "E606")
            ctl[n] = a is True and b is True and c is True if None not in (a, b, c) else None
            continue
        for k, s in (("H-E606", cov), ("H-ZLS", zls), ("H-DEPTH", dep)):
            by.setdefault(k, {}).setdefault(size, []).append(s)
    for k in ("H-E606", "H-ZLS", "H-DEPTH"):
        allrows = []
        for size, rows in by.get(k, {}).items():
            allrows += rows
            cx.say("SIZE %s %s: %s" % (k, size, SK.tally(rows)))
        cx.say("SUMMARY: %s %s:" % (label, k), SK.headline("%s %s held on every size" % (label, k), ctl, allrows))


def score_zi(cx):
    ctl, rows = {}, {"H-E606": [], "H-ITER": []}
    for t in cx.T:
        n = t["name"]
        if not cx.ok(n):
            _void_note(cx, t)
            if t["set"] == "control":
                ctl[n] = None
            else:
                rows["H-E606"].append(None)
                rows["H-ITER"].append(None)
            continue
        r = parse_out(cx.text(n))
        if n == "zi-ctl-e680-1024x768":
            a = _ctl_eq(cx, n, "hash", _h(r["hash"]), "E680")
            b = _ctl_eq(cx, n, "tri", r["tri"], "E680")
            ctl[n] = None if None in (a, b) else (a and b)
            continue
        w, h = wh(t["args"])
        img = image(r, w, h)
        if t["set"] == "control":
            ctl[n] = _ctl_eq(cx, n, "pixels_sha", None if img is None else M.sha_list(img.ravel()), "E606")
            continue
        if img is None:
            cx.say("ROW", n, "no complete pixel rows: cannot tell")
            rows["H-E606"].append(None)
            rows["H-ITER"].append(None)
            continue
        v, z = tri_v(t["args"]), tri_z(t["args"])
        pc = M.cover(v, w, h)
        oc = img != M.BG
        cov_ok = bool((oc == pc).all())
        err = np.abs(M.f32(img) - M.plane_image(v, [2 * x - 1 for x in z], w, h)) / M.U
        e = float(err[pc].max()) if pc.any() else 0.0
        rows["H-E606"].append(cov_ok)
        rows["H-ITER"].append((cov_ok and e <= M.ITER_TOL) if pc.any() else None)
        cx.say("ROW", n, "coverage", "exact" if cov_ok else "WRONG %d px" % int(np.count_nonzero(oc != pc)), "pa0 max %.2f U" % e)
    for k, r in rows.items():
        cx.say("SUMMARY: Q262 iteration %s:" % k, SK.headline("Q262 iteration %s held" % k, ctl, r))


def score_zs(cx):
    ctl, obs = {}, {}
    for t in cx.T:
        n = t["name"]
        if not cx.ok(n):
            _void_note(cx, t)
            obs[n] = None
        else:
            img = image(parse_out(cx.text(n)), M.SW, M.SH)
            obs[n] = None if img is None or ((img != M.GREEN) & (img != M.BG)).any() else M.cov_sha(img == M.GREEN)
        if t["set"] == "control":
            if n.startswith("zs-ctl-"):
                m = "E681" if "e681" in n else "E683"
                h = parse_out(cx.text(n))["hash"] if cx.ok(n) else None
                ctl[n] = _ctl_eq(cx, n, "hash", _h(h), m)
            else:
                ctl[n] = None if obs[n] is None else obs[n] == cx.P[n]["covered_sha"]["H-HU"]
                cx.say("CONTROL", n, "HU", "PASS" if ctl[n] else ("FAILED" if ctl[n] is False else "cannot tell"))
    fit = [t["name"] for t in cx.T if t["set"] == "fit"]
    cs = [c for c in range(16) if all(obs[n] is not None and obs[n] == cx.P[n]["covered_sha"]["SETUP%d" % c] for n in fit)]
    cx.say("FIT SETUP(c) on the -0.5 x sweep: c in", cs or "none")
    held = [t["name"] for t in cx.T if t["set"] == "heldout"]
    rivals = [("H-HU", "H-HU"), ("H-HA", "H-HA"), ("H-FAR", "H-FAR")] + ([("SETUP(c=%d)" % cs[0], "SETUP%d" % cs[0])] if len(cs) == 1 else [])
    for label, key in rivals:
        r = [None if obs[n] is None else obs[n] == cx.P[n]["covered_sha"][key] for n in held]
        cx.say("SUMMARY: Q260 %s:" % label, SK.headline("Q260 %s exact on the held-out rows" % label, ctl, r))
    if len(cs) != 1:
        cx.say("SUMMARY: Q260 SETUP(c):", "refuted on fit (no c)" if not cs else "cannot tell: %d values of c fit" % len(cs))
    mir = [t["name"] for t in cx.T if t["set"] == "mirror"]
    r = [None if obs[n] is None else obs[n] == cx.P[n]["covered_sha"]["H-HU"] for n in mir]
    cx.say("SUMMARY: Q260 positive mirror HU:", SK.headline("HU at +0.5 y and +64.5 (the mirror)", ctl, r))
    # the model-free per-step table: the steps at which each sweep's image changes
    sweeps = {}
    for t in cx.T:
        p = cx.P[t["name"]].get("sweep")
        if p:
            pos, ax, d = p["all"].split()
            sweeps.setdefault((pos, ax), []).append((int(d), obs[t["name"]]))
    for (pos, ax), lst in sweeps.items():
        lst.sort()
        flips = [d for (d0, a), (d, b) in zip(lst, lst[1:]) if a is not None and b is not None and a != b]
        cx.say("STEP %s %s: image changes at d = %s" % (pos, ax, ",".join(map(str, flips)) or "none"))


SCORERS = {"xf": score_xf, "tx": score_tx, "zd": lambda cx: score_d(cx, "Q262 depth"), "zi": score_zi,
           "zf": lambda cx: score_d(cx, "Q240 family"), "zs": score_zs}


def score(stage, d, kp=KP):
    cx = Ctx(stage, d, kp)
    miss = missing_files(stage, d)
    if miss:
        cx.say("STOP: kept files missing:", " ".join(miss[:5]))
    SCORERS[stage](cx)
    return cx.out


def freeze_ok():
    if os.environ.get("R7G_NO_FREEZE_CHECK") == "1":
        return True
    return subprocess.run([os.path.join(KP, "run/freeze_g.sh"), "verify"], capture_output=True).returncode == 0


def main(argv):
    if len(argv) == 3 and argv[1] == "verdict":
        for st in STAGES:
            p = os.path.join(argv[2], "score-%s.txt" % st)
            if os.path.exists(p):
                for ln in open(p):
                    if ln.startswith("SUMMARY:"):
                        print(ln.rstrip())
            else:
                print("SUMMARY: %s: not run" % st)
        return 0
    if len(argv) != 3 or argv[1] not in STAGES:
        print(__doc__)
        return 2
    if not freeze_ok():
        print("the freeze does not verify (run/freeze_g.sh verify): not scored")
        return 3
    print("\n".join(score(argv[1], argv[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
