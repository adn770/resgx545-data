#!/usr/bin/env python3
"""score_rd7.py: the frozen scorer of stages p7-rdc and p7-rd of r7-rp (Q276; plan closing7/a/exp-pixel-r7.md 1.4 and 3.4).
Standard library and the session's own modules only.  Readers are R6's, unchanged (score/rd_score_rd.py = closing6/r6-pixel/score/
score_rd.py, rd_score_o5.py, rd_score_o4.py, rd_r4lib.py, rd_rdmodel.py, rd_o5model.py, each with only its imports renamed so that
no module name clashes with another area's in one process); the round-7 rules are here and in rd7model.py.

p7-rdc (R6's 14 bridge controls).  G-o4 on c-e709 and G-o1 on c-u (R5's code via R6's r5_controls), c-all4 5:1 (R5's reader), TRI
= the pixels whose word is their own in both c-rd-0 jobs (R6's tri_of; fewer than 300: cannot tell), c-ow 1:1 and c-rd-0 1:2 at
>= 0.95 of TRI, c-prd-0 k = 1 and 7 lanes as frozen (R6's lanes_read, >= 0.95 of each lane's TRI pixels in both jobs).
gate("p7-rdc") = R6's bridge: G-o4, G-o1, c-ow, c-rd-0, c-prd-0-k1, c-prd-0-k7: 0 every one PASS, 1 one FAILED, 2 cannot tell (a
missing file, a void job, no TRI).  c-all4 is not in the gate (as R6): when it does not read 5:1 p7-rd's verdict is cannot tell.

p7-rd (reads its own kept directory and the sibling ../p7-rdc for TRI, the gate and c-all4).
  Own-source rule (rd-1..rd-7, n-rd-4, x-rd-4, x-rd-6, x-rd-7, n-rd-5): over TRI, a job's own-source words are those with the job's
  marker that decode to the pixel itself (R6's labels "T:B"; "D", "O:..", "bg" are not own-source).  The configuration reads class
  L when in both jobs L holds >= 0.85 of the own-source words AND no other model class (S, A0, A4 of its labels) more than 0.02 of
  them; fewer than 300 own-source words in a job: cannot tell.  L is named S, A0, A4 by the frozen labels, else W:T.B.
  Replicates (rd-1..rd-7, n-rd-4, x-rd-4): a replicate whose top own-source label differs from R6's (r6_top) in either job is "not
  replicated" and its entry is void.
  Clean rows (cl-4..cl-7): R6's original rule unchanged (R6's read_rd: one class at >= 0.90 of ALL TRI pixels in both jobs; X when
  fewer than 5 percent carry the job's marker in both jobs; O:..; S, A0 or W:..).  cl-4: A0 (word A, H-MOD4) or S (word B, H-STORE);
  cl-5..cl-7: "not word B" (any decided class but S, H-MOD4) or S (H-STORE); the class read is reported.  cl-p4: R6's lane rule.
  Verdict: H-STORE at j when a decided entry reading o4..o7 reads S (or cl-p4 shows word B on lane 0): E878's post hoc reading is
  refuted; H-MOD4 held when every entry is decided and as H-MOD4 predicts; H-MOD4 refuted when a decided entry differs; else
  cannot tell, naming the undecided and not replicated entries.

CLI:  score_rd7.py STAGE KEPT          detail lines, then one SUMMARY line (exit 0; non-zero only on a scorer error)
      score_rd7.py gate STAGE KEPT     exit = gate (0 pass, 1 failed, 2 cannot tell); p7-rd has no gate of its own (0)
      score_rd7.py verdict ATT_DIR     one SUMMARY line per stage"""
from __future__ import annotations

import collections
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rd7model as R7  # noqa: E402
import rd_r4lib as L  # noqa: E402
import rd_rdmodel as RM  # noqa: E402
import rd_score_o5 as S5  # noqa: E402
import rd_score_rd as SR  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("p7-rdc", "p7-rd")
RDC_ROWS = [f"{c}-{ax}" for c in R7.CONTROLS for ax in "xy"]
REQUIRED = {"p7-rdc": ("cases.tsv", ".txt"),
            "p7-rd": ("cases.tsv", ".txt")}        # and the sibling p7-rdc's files (missing() adds them: REQUIRED's names are per directory)
BRIDGE = ("G-o4 c-e709", "G-o1 c-u", "c-ow (last o0 write)", "c-rd-0 (readback)", "c-prd-0-k1", "c-prd-0-k7")


def load(stage):
    """The frozen predictions of a stage (p7-rd: with p7-rdc's, for the controls' markers)."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for st in (("p7-rdc",) if stage == "p7-rdc" else ("p7-rdc", "p7-rd")):
        for c, qs in L.load_preds(stage=st).items():
            for q, v in qs.items():
                out[c][q] += v
    return out


def missing(stage, kept):
    rows = [c["name"] for c in L.Kept(kept).cases]
    out = SK.missing_files(REQUIRED[stage], kept, rows)
    if stage == "p7-rd":                    # p7-rd also reads TRI, the gate and c-all4 from ../p7-rdc
        rdc = os.path.join(os.path.dirname(os.path.abspath(kept)), "p7-rdc")
        out += ["../p7-rdc/" + f for f in SK.missing_files(REQUIRED["p7-rdc"], rdc, RDC_ROWS)]
    return out


# ------------------------------------------------------------------------------------------------------------------- p7-rdc
def read_rdc(kc, preds):
    """dict(lines, controls, gate, all4, tri) of the control stage's kept files (R6's readers)."""
    out = []
    ctl = SR.r5_controls(kc, preds, out)
    r = S5.read_cfg(kc, preds, "c-all4")
    all4 = None if r["void"] or r["cls"] is None else r["cls"] == "5:1"
    out.append(f"c-all4: {'NODATA ' + r['void'] if r['void'] else 'reads ' + str(r['cls'])} (frozen 5:1; else p7-rd is void)")
    tri, why = SR.tri_of(kc, preds)
    out.append(f"TRI: {len(tri)} pixels" if tri else f"TRI: cannot tell ({why})")
    for name, cfg, label in (("c-ow (last o0 write)", "c-ow", "1:1"), ("c-rd-0 (readback)", "c-rd-0", "1:2")):
        if not tri:
            ctl[name] = None
            continue
        s, w = SR.share(kc, preds, cfg, tri, label)
        ctl[name] = None if s is None else s >= RM.CTL_SHARE
        out.append(f"{cfg}: {label} at {s if s is None else round(s, 3)} of TRI (frozen >= {RM.CTL_SHARE}){' ' + w if w else ''}")
    for kk in RM.CPRD_K:
        cfg = f"c-prd-0-k{kk}"
        want = tuple(preds.get(f"{cfg}-x", {}).get("lanes", [("",)])[0][0].split(","))
        if not tri:
            ctl[cfg] = None
            continue
        lr, why = SR.lanes_read(kc, preds, cfg, tri)
        ctl[cfg] = None if lr is None or None in lr else lr == want
        out.append(f"{cfg}: lanes {lr if lr else 'NODATA ' + why} (frozen {','.join(want)})")
    bridge = {n: ctl.get(n) for n in BRIDGE}
    g = SK.gate(bridge)
    out.append("bridge controls: " + ("PASS" if g.ok else "; ".join(g.problems)))
    return dict(lines=out, controls=bridge, gate=g, all4=all4, tri=tri)


def gate_code(g):
    return 0 if g.ok else (1 if g.failed else 2)


def score_rdc(kept):
    r = read_rdc(L.Kept(kept), load("p7-rdc"))
    g = r["gate"]
    s = ("gate PASS" if g.ok else ("gate FAILED: " if g.failed else "gate CANNOT TELL: ") + "; ".join(g.problems))
    s += f"; c-all4 {'5:1' if r['all4'] else ('not 5:1' if r['all4'] is False else 'cannot tell')}; TRI {len(r['tri']) if r['tri'] else 0}"
    return s, r["lines"], r


# ------------------------------------------------------------------------------------------------------------------- p7-rd
def names_of(preds, cfg):
    """({label: class}, {class: label}) from the frozen labels of a configuration."""
    lab2c, c2lab = {}, {}
    for item in preds.get(f"{cfg}-x", {}).get("labels", [("",)])[0][0].split():
        c, v = item.split("=")
        lab2c.setdefault(v, c)
        c2lab[c] = v
    return lab2c, c2lab


def own_rule(k, preds, cfg, tri):
    """The own-source reading of one configuration: dict(void, cls, tops, own, shares, rivals, dist)."""
    g, why = SR.grids(k, cfg)
    if g is None:
        return dict(void=why)
    m = SR.marker_of(preds, cfg)
    if m is None:
        return dict(void="no frozen marker")
    cs = SR.job_labels(g, tri, m)
    lab2c, c2lab = names_of(preds, cfg)
    owns = [collections.Counter({lab: v for lab, v in c.items() if ":" in lab and not lab.startswith("O:")}) for c in cs]
    n = [sum(o.values()) for o in owns]
    tops = [o.most_common(1)[0][0] if o else None for o in owns]
    shares = [(o.get(t, 0) / x if x else 0.0) for o, t, x in zip(owns, tops, n)]
    res = dict(void=None, cls=None, tops=tops, own=n, shares=shares, dist=cs, owns=owns, rivals={}, why="")
    if min(n) < R7.OWN_MIN:
        res["why"] = f"own-source words {n[0]} / {n[1]} (< {R7.OWN_MIN} in a job)"
        return res
    if tops[0] != tops[1]:
        res["why"] = f"top labels differ ({tops[0]} / {tops[1]})"
        return res
    top = tops[0]
    res["rivals"] = {c: [o.get(lab, 0) / x for o, x in zip(owns, n)] for c, lab in c2lab.items() if lab != top}
    if min(shares) < R7.OWN_SHARE:
        res["why"] = f"{top} at {shares[0]:.3f} / {shares[1]:.3f} of own-source (< {R7.OWN_SHARE})"
        return res
    over = [c for c, v in res["rivals"].items() if max(v) > R7.RIVAL_MAX]
    if over:
        res["why"] = "rival class " + ", ".join(f"{c} {max(res['rivals'][c]):.3f}" for c in over) + f" (> {R7.RIVAL_MAX})"
        return res
    res["cls"] = lab2c.get(top, f"W:{top.replace(':', '.')}")
    return res


def frozen_cls(preds, cfg):
    return {m: v for v, m, st in preds.get(f"{cfg}-x", {}).get("class", [])}


def fmt_own(r):
    if r.get("void"):
        return f"NODATA ({r['void']})"
    js = "; ".join(f"{ax} top {t} {o.get(t, 0)}/{x} = {s:.3f} of own-source, D {c.get('D', 0)}, bg {c.get('bg', 0)}"
                   for ax, t, s, x, c, o in zip("xy", r["tops"], r["shares"], r["own"], r["dist"], r["owns"]))
    return f"class {r['cls']}" + (f" (cannot tell: {r['why']})" if r["cls"] is None else "") + "  " + js


def score_rd(kept):
    kept = os.path.abspath(kept)
    preds = load("p7-rd")
    rdc_dir = os.path.join(os.path.dirname(kept), "p7-rdc")
    out = [f"p7-rdc read from {rdc_dir}"]
    rc = read_rdc(L.Kept(rdc_dir), preds)
    out += ["  " + ln for ln in rc["lines"]]
    k = L.Kept(kept)
    tri = rc["tri"]
    entries, repl, notrep, reads = {}, {}, [], {}
    for cfg in R7.REPL + R7.HELD:
        r = own_rule(k, preds, cfg, tri) if tri else dict(void="no TRI")
        line = f"{cfg}: {fmt_own(r)}"
        cls = None if r.get("void") else r["cls"]
        if cfg in R7.REPL:
            want = preds.get(f"{cfg}-x", {}).get("r6_top", [("",)])[0][0]
            if r.get("void") or min(r["own"]) < R7.OWN_MIN:
                repl[cfg] = None
            else:
                repl[cfg] = r["tops"][0] == want and r["tops"][1] == want
            if repl[cfg] is False:
                notrep.append(cfg)
                line += f"  NOT REPLICATED (R6's top {want}): entry void"
                cls = None
            elif repl[cfg]:
                line += f"  replicated (R6's top {want})"
        entries[cfg] = cls
        reads[cfg] = r
        out.append(line)
    for cfg in R7.CLEAN:
        r = SR.read_rd(k, preds, cfg, tri) if tri else dict(void="no TRI")
        entries[cfg] = None if r["void"] else r["cls"]
        reads[cfg] = r
        if r["void"]:
            out.append(f"{cfg}: NODATA ({r['void']})")
        else:
            n = len(tri)
            tops = "; ".join(f"{ax} {dict(c.most_common(3))} top {c.most_common(1)[0][1] / n:.3f} of TRI" for ax, c in zip("xy", r["dist"]))
            out.append(f"{cfg}: class {r['cls']} (R6's rule, all TRI)  {tops}")
    lanes = None
    if tri:
        lr, why = SR.lanes_read(k, preds, R7.CLP, tri)
        lanes = lr
        out.append(f"{R7.CLP}: lanes {lr if lr else 'NODATA ' + str(why)} (R6's lane rule)")
    else:
        out.append(f"{R7.CLP}: NODATA (no TRI)")
    clp_frozen = {m: tuple(v.split(",")) for v, m, st in preds.get(f"{R7.CLP}-x", {}).get("lanes", [])}
    clp_mod = clp_frozen.get("H-MOD4", ("",) * 4)
    # ---- the rd vector
    vec = tuple(entries[c] for c in R7.RD)
    mvec = {}
    for item in preds.get("@p7-rd", {}).get("models", [("",)])[0][0].split():
        mn, v = item.split("=")
        mvec[mn] = tuple(v.split(","))
    fits = [mn for mn, fv in mvec.items() if None not in vec and all(RM.matches(f, r) for f, r in zip(fv, vec))]
    out.append("rd vector (j = 1..7): " + " ".join(str(v) for v in vec) + (f"  fits {', '.join(fits)}" if fits else ""))
    # ---- per entry against H-MOD4, H-STORE hits
    mod4 = {}
    for cfg, v in entries.items():
        mod4[cfg] = None if v is None else RM.matches(frozen_cls(preds, cfg).get("H-MOD4", ""), v)
    if lanes is None or None in lanes:
        mod4[R7.CLP] = None
    else:
        mod4[R7.CLP] = all(R7.lane_match(f, r) for f, r in zip(clp_mod, lanes))
    hits = [cfg for cfg, v in entries.items() if v == "S" and R7.store_j(cfg) >= 4]
    if lanes is not None and lanes[R7.CLP_K] is not None and lanes[R7.CLP_K] == R7.labels(R7.CLP)["S"]:
        hits.append(f"{R7.CLP} (lane {R7.CLP_K})")
    und = [c for c, v in mod4.items() if v is None]
    bad = [c for c, v in mod4.items() if v is False]
    out.append("against H-MOD4: " + ", ".join(f"{c} {SK._state(v)}" for c, v in mod4.items()))
    vtxt = "rd vector " + " ".join(str(v) for v in vec) + (f" ({', '.join(fits)})" if fits else "")
    word = lambda c: {"X": "X (no word of the job)"}.get(entries[c], str(entries[c]))
    if not rc["gate"].ok:
        s = "cannot tell: p7-rdc gate " + ("FAILED: " if rc["gate"].failed else "cannot tell: ") + "; ".join(rc["gate"].problems)
    elif rc["all4"] is not True:
        s = "cannot tell: c-all4 does not read 5:1 (" + ("FAILED" if rc["all4"] is False else "cannot tell") + "): the stage is void"
    elif hits:
        s = (f"H-STORE at {', '.join(hits)}: a read of o4..o7 returns the word written there; E878's post hoc reading (H-MOD4) is "
             f"refuted, Q276 reopened; {vtxt}")
    elif not und and not bad:
        s = (f"H-MOD4 held ({len(mod4)} of {len(mod4)} entries): {vtxt} replicated; n-rd-4 {entries['n-rd-4']}, x-rd-4 "
             f"{entries['x-rd-4']}; x-rd-6 {entries['x-rd-6']} (o2's word), x-rd-7 {entries['x-rd-7']} (o3's), n-rd-5 "
             f"{entries['n-rd-5']} (o1's); cl-4 {entries['cl-4']} (word A); cl-5 {word('cl-5')}, cl-6 {word('cl-6')}, cl-7 "
             f"{word('cl-7')} (not word B); cl-p4 {','.join(lanes)} (word A on every lane)")
    elif bad:
        s = (f"H-MOD4 refuted at {', '.join(f'{c} ({entries.get(c, lanes)})' for c in bad)}; {vtxt}"
             + (f"; not decided: {', '.join(und)}" if und else ""))
    else:
        s = f"cannot tell: not decided: {', '.join(und)}" + (f" (not replicated: {', '.join(notrep)})" if notrep else "") + f"; {vtxt}"
    res = dict(entries=entries, vector=vec, fits=fits, mod4=mod4, hits=hits, notrep=notrep, repl=repl, reads=reads, lanes=lanes,
               rdc=rc, gate=SK.gate({"(p7-rd: gated by p7-rdc)": True}))
    return s, out, res


# ------------------------------------------------------------------------------------------------------------------- API
def score(stage, kept):
    """(summary without 'SUMMARY: ', detail lines)."""
    if stage == "p7-rdc":
        s, lines, _ = score_rdc(kept)
    elif stage == "p7-rd":
        s, lines, _ = score_rd(kept)
    else:
        raise SystemExit(f"score_rd7: unknown stage {stage}")
    return s, lines


def result(stage, kept):
    return (score_rdc if stage == "p7-rdc" else score_rd)(kept)[2]


def gate(stage, kept):
    """0 pass, 1 failed, 2 cannot tell (p7-rdc: R6's bridge); 0 for p7-rd (no gate of its own)."""
    if stage != "p7-rdc":
        return 0
    return gate_code(read_rdc(L.Kept(kept), load("p7-rdc"))["gate"])


def verdict(att_dir):
    out = []
    for st in STAGES:
        d = os.path.join(att_dir, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append(f"SUMMARY: {st}: did not run")
            continue
        out.append(f"SUMMARY: {st}: {score(st, d)[0]}")
    return out


def main(a):
    if len(a) == 3 and a[0] == "gate":
        g = gate(a[1], a[2])
        print(f"gate {a[1]}: {('PASS', 'FAILED', 'CANNOT TELL')[g]}")
        return g
    if len(a) == 2 and a[0] == "verdict":
        print("\n".join(verdict(a[1])))
        return 0
    if len(a) == 2 and a[0] in STAGES:
        s, lines = score(a[0], a[1])
        print("\n".join(lines))
        print(f"SUMMARY: {s}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
