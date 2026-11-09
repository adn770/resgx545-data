#!/usr/bin/env python3
"""Recompute of the 11.35 batch from the kept dumps only: python3 -B recompute_p1135.py DIR [bg|keep|dirs]...
DIR holds one directory per script (cases.tsv, NAME.txt.gz, NAME.param.bin.gz, NAME.kept.bin.gz, ...). Own decoders;
shares no code with the run scripts or the generator; reads the declared tables (declared.tsv,
predictions-declared.tsv) only to score. Prints, per script, the counts and observed against declared
by set and model."""
import collections, gzip, hashlib, pathlib, re, struct, sys
HERE = pathlib.Path(__file__).resolve().parent.parent

def rd(p):
    return gzip.open(p).read() if p.exists() else None

def load_preds():
    out = collections.defaultdict(list)
    for f in [HERE / "predictions-declared.tsv"] + sorted(HERE.glob("predictions-followup*.tsv")):
        for ln in f.read_text().splitlines()[1:]:
            c, q, v, m = ln.split("\t"); out[c].append((q, v, m))
    return out

def load_sets():
    out = {}
    for f in [HERE / "declared.tsv"] + sorted(HERE.glob("declared-followup*.tsv")):
        out.update({l.split("\t")[0]: l.split("\t")[2] for l in f.read_text().splitlines()[1:]})
    return out

class Score:
    def __init__(self): self.t = collections.defaultdict(collections.Counter)
    def add(self, model, sset, quantity, ok):
        self.t[(model, sset, quantity)]["explore" if ok is None else ("ok" if ok else "MISS")] += 1
    def show(self):
        for (m, s, q), c in sorted(self.t.items()):
            print("  %-9s %-8s %-18s scored %3d: ok %3d miss %3d; explore %d" %
                  (m, s, q, c["ok"] + c["MISS"], c["ok"], c["MISS"], c["explore"]))

def cases(d):
    out = []
    for ln in (d / "cases.tsv").read_text().splitlines()[1:]:
        out.append(ln.split("\t"))
    return out

def score(sc, preds, sets, case, obs):
    """obs: quantity -> observed value; a prediction of ? is explore"""
    for q, v, m in preds.get(case, []):
        if q not in obs:
            continue
        ok = None if v == "?" else (obs[q] == v)
        sc.add(m, sets.get(case, "?"), q, ok)

# ------------------------------------------------------------------ Q066
PIX = re.compile(r"row (\d+): (.*)$")
def image(txt):
    rows = {}
    for line in txt.decode().splitlines():
        m = PIX.search(line)
        if m: rows[int(m.group(1))] = m.group(2).split()
    return [rows[i] for i in sorted(rows)]

def run_bg(d, preds, sets, sc):
    OFF = 0x463000   # the background object in tri.N.param.bin (debugfs render_param)
    ctl = None; res = {}
    cs = cases(d)
    print("bg-words: %d case runs" % len(cs))
    base = None
    for c in cs:
        name = c[0]
        if name != "b66-control-1": continue
        pb = rd(d / (name + ".param.bin.gz"))
        base = list(struct.unpack_from("<17I", pb, OFF)) if pb else None
    print("  control object words:", " ".join("%08x" % w for w in base) if base else "none")
    ctlhash = None
    for c in cs:
        name = c[0]
        txt = rd(d / (name + ".txt.gz"))
        if txt is None:
            print("  %s: no output" % name); continue
        s = txt.decode(errors="replace")
        ok = "tri: 1 renders ok" in s
        img = image(txt)
        h = hashlib.sha256("\n".join(" ".join(r) for r in img).encode()).hexdigest()[:16]
        m = re.search(r"diff: (\d+) of 4096", s)
        diff = int(m.group(1)) if m else -1
        pb = rd(d / (name + ".param.bin.gz"))
        obj = list(struct.unpack_from("<17I", pb, OFF)) if pb else None
        res[name] = dict(ok=ok, h=h, diff=diff, obj=obj, npix=sum(len(r) for r in img))
        if name == "b66-control-1": ctlhash = h
    # observed quantities
    for c in cs:
        name = c[0]; r = res.get(name)
        if not r: continue
        mm = re.match(r"b66-w(\d+)-(f(\d+)|z|o)$", name)
        obs = {"image-vs-control": "same" if (r["h"] == ctlhash and r["ok"]) else "differs"}
        if name.startswith("b66-control"):
            obs["diff-of-4096"] = str(r["diff"])
        if mm and r["obj"] and base:
            w = int(mm.group(1)); kind = mm.group(2)
            want = {"z": 0, "o": 0xffffffff}.get(kind)
            if want is None: want = base[w] ^ (1 << int(mm.group(3)))
            obs["poke-in-object"] = "yes" if r["obj"][w] == want else "no"
        score(sc, preds, sets, name, obs)
        r["obs"] = obs
    # tables
    n_ok = sum(1 for r in res.values() if r["ok"]); print("  completed %d of %d, failed %d" % (n_ok, len(res), len(res) - n_ok))
    grp = collections.defaultdict(lambda: collections.Counter())
    for name, r in sorted(res.items()):
        mm = re.match(r"b66-w(\d+)-", name)
        if not mm: continue
        w = int(mm.group(1))
        k = "same" if r["obs"]["image-vs-control"] == "same" else ("fault" if not r["ok"] else "wrong-image")
        grp[w][k] += 1
        grp[w]["poke-in-object-" + r["obs"].get("poke-in-object", "n/a")] += 1
    for w in sorted(grp): print("  word %2d: %s" % (w, dict(grp[w])))
    controls = [(n, r["h"], r["diff"]) for n, r in sorted(res.items()) if n.startswith("b66-control")]
    print("  controls:", controls)
    return res

# ------------------------------------------------------------------ Q045
def u32s(b): return struct.unpack("<%dI" % (len(b) // 4), b)

def run_keep(d, preds, sets, sc):
    cs = cases(d); print("keep-closed: %d case runs" % len(cs)); out = {}
    for c in cs:
        name = c[0]
        txt = rd(d / (name + ".txt.gz")); kept = rd(d / (name + ".kept.bin.gz"))
        if txt is None: print("  %s: no output" % name); continue
        s = txt.decode(errors="replace")
        diffs = [int(x) for x in re.findall(r"diff: (\d+) of 4096", s)]
        failed = bool(re.search(r"job: failed|faulted|FAILED|context lost", s))
        t2 = re.search(r"tri2 64x64 #1: .* wrong (\d+) inside, (\d+) outside, (\d+) at edges", s)
        exact = (not failed) and "tri: 1 renders ok" in s and bool(diffs) and all(x == 0 for x in diffs) and \
            bool(t2) and t2.groups() == ("0", "0", "0")
        obs = {"second-render": "exact" if exact else "faults" if failed else "other",
               "kept-readable": "yes" if kept else "no"}
        pg = None
        if kept and len(kept) >= 0x4000:
            w = u32s(kept[0x3000:0x4000])
            changed = [i for i, v in enumerate(w) if v != 0xa5000000 + i]
            obs["state-page-vs-ramp"] = "changed" if changed else "equal"
            pg = (len(changed), changed[:34])
        score(sc, preds, sets, name, obs)
        out[name] = (obs, diffs, pg)
        print("  %-20s %-8s diffs %s kept %s page3-changed %s" % (name, sets.get(name, "?"), diffs, len(kept or b""), pg and pg[0]))
    return out

# ------------------------------------------------------------------ Q066 follow-up 1: the whole object at once
def run_bgf1(d, preds, sets, sc):
    OFF = 0x463000; cs = cases(d); print("bg-words-f1: %d case runs" % len(cs)); res = {}
    ctlhash = None
    for c in cs:
        name = c[0]
        txt = rd(d / (name + ".txt.gz")); pb = rd(d / (name + ".param.bin.gz"))
        if txt is None: print("  %s: no output" % name); continue
        s = txt.decode(errors="replace")
        ok = "tri: 1 renders ok" in s
        img = image(txt); h = hashlib.sha256("\n".join(" ".join(r) for r in img).encode()).hexdigest()[:16]
        obj = list(struct.unpack_from("<17I", pb, OFF)) if pb else None
        want = {int(w): int(v, 16) for w, v in re.findall(r"bg:(\d+)=(0x[0-9a-f]+)", c[5])}
        if name == "b66f1-control-1": ctlhash = h
        res[name] = (ok, h, obj, want)
    for name, (ok, h, obj, want) in res.items():
        obs = {"image-vs-control": "same" if (h == ctlhash and ok) else "differs"}
        if want and obj: obs["poke-in-object"] = "yes" if all(obj[w] == v for w, v in want.items()) else "no"
        score(sc, preds, sets, name, obs)
        print("  %-16s completed %s image %s %s poked words read back %s" % (name, ok, h, obs["image-vs-control"],
              ("%d of %d" % (sum(1 for w, v in want.items() if obj and obj[w] == v), len(want))) if want else "-"))
    return {n: {"ok": r[0], "h": r[1]} for n, r in res.items()}

# ------------------------------------------------------------------ Q045 follow-up 2: a partial render's state page
def run_keep2(d, preds, sets, sc):
    """d = the dumps directory itself: keep-partial-solo (the solo rows) and keep-partial-ctx2 (the ctx2 rows)"""
    data = {}; solo = {}
    for sub in ("keep-partial-solo", "keep-partial-ctx2"):
        dd = d.parent / sub
        for c in cases(dd):
            name = c[0]
            txt = rd(dd / (name + ".txt.gz")); kept = rd(dd / (name + ".kept.bin.gz"))
            if txt is None or ("solo" in name) != (sub.endswith("solo")): continue
            w = u32s(kept[:len(kept) // 4 * 4]) if kept else ()
            pg = {p: w[p * 1024:(p + 1) * 1024] for p in (4, 5, 6)} if len(w) >= 7 * 1024 else None
            data[name] = (txt.decode(errors="replace"), kept, pg)
    print("keep-partial: %d case runs (4 solo, 4 ctx2)" % len(data))
    for name, (s, kept, pg) in data.items():
        m = re.match(r"kp-solo-(4|c)-\d", name)
        if m and pg: solo.setdefault(m.group(1), []).append(pg)
    for name, (s, kept, pg) in sorted(data.items()):
        obs = {"kept-readable": "yes" if kept else "no"}
        notrun = "closing the second context before the first" in s
        bad = bool(re.search(r"faulted|context lost|hung|BIF fault", s))
        if name.startswith("kp-ctx2"):
            if notrun: obs["second-render-state"] = "not-run (not scored)"
            else: obs["second-render"] = "faults" if bad else "completes"
        m = re.match(r"kp-ctx2-(4|c)-\d", name)
        nz = {p: sum(1 for v in x if v) for p, x in pg.items()} if pg else None
        if m and pg and solo.get(m.group(1)) and not notrun:
            ref = solo[m.group(1)][0]
            obs["pages4-6-vs-solo"] = "equal" if all(pg[p] == ref[p] for p in (4, 5, 6)) else "changed"
        score(sc, preds, sets, name, obs)
        print("  %-14s %-8s kept %d bytes, non-zero dwords of pages 4,5,6: %s; %s%s" % (name, sets.get(name, "?"), len(kept or b""), nz,
              {k: v for k, v in obs.items() if k in ("second-render", "second-render-state", "pages4-6-vs-solo")},
              "  (the tool closed the second context first: the kept context is the second, not rendered)" if notrun else ""))
    sd = {k: ("agree" if all(l[p] == lst[0][p] for l in lst for p in (4, 5, 6)) else "differ") for k, lst in solo.items()}
    print("  solo runs of one flag agree:", sd)
    return {n: {"kept": len(v[1] or b"")} for n, v in data.items()}

# ------------------------------------------------------------------ Q045 follow-up 3: a ramp in page 1 or 2
def run_keep3(d, preds, sets, sc):
    cs = cases(d); print("keep-pages: %d case runs" % len(cs)); out = {}
    for c in cs:
        name = c[0]
        txt = rd(d / (name + ".txt.gz")); kept = rd(d / (name + ".kept.bin.gz"))
        if txt is None: print("  %s: no output" % name); continue
        s = txt.decode(errors="replace")
        page = int(re.search(r"ramp=(\d+)", c[5]).group(1))
        diffs = [int(x) for x in re.findall(r"diff: (\d+) of 4096", s)]
        failed = bool(re.search(r"job: failed|faulted|FAILED|context lost", s))
        t2 = re.search(r"tri2 64x64 #1: .* wrong (\d+) inside, (\d+) outside, (\d+) at edges", s)
        exact = (not failed) and "tri: 1 renders ok" in s and bool(diffs) and all(x == 0 for x in diffs) and bool(t2) and t2.groups() == ("0", "0", "0")
        obs = {"second-render": "exact" if exact else "faults" if failed else "other"}
        ch = None
        if kept and len(kept) >= (page + 1) * 4096:
            w = u32s(kept[page * 4096:(page + 1) * 4096])
            idx = [i for i, v in enumerate(w) if v != 0xa5000000 + i]
            obs["page-vs-ramp"] = "changed" if idx else "equal"; obs["changed-dwords"] = str(len(idx))
            ch = (len(idx), [(i, "%08x" % w[i]) for i in idx[:6]])
        score(sc, preds, sets, name, obs); out[name] = obs
        print("  %-12s page %d: second render %s, page vs ramp %s, changed dwords %s" % (name, page, obs["second-render"], obs.get("page-vs-ramp"), ch))
    return out

# ------------------------------------------------------------------ Q076
def run_dirs(d, preds, sets, sc):
    cs = cases(d); print("dirs: %d case runs" % len(cs)); out = {}
    for c in cs:
        name = c[0]
        wf = sorted(d.glob(name + ".words.*.txt.gz"), key=lambda p: int(p.name.split(".words.")[1].split(".")[0]))
        o = rd(d / (name + ".txt.gz"))
        if not wf or o is None: print("  %s: no words or output" % name); continue
        w = gzip.open(wf[-1]).read().decode()
        m = re.search(r"^ctx:2=0x([0-9a-f]+)", w, re.M)
        blocks = o.decode(errors="replace").split("regs: ")
        regs = {int(a, 16): int(v, 16) for a, v in re.findall(r"^reg (0x[0-9a-f]{4}) (0x[0-9a-f]{8})", blocks[-1], re.M)}
        if not m or len(blocks) < 2: print("  %s: no ctx:2 line or no register block" % name); continue
        pd = int(m.group(1), 16)
        inl = [k for k in range(0, 16) if regs.get(0x0c34 + 4 * k) == pd]
        obs = {"pd-in-list": ",".join(map(str, inl)) or "none", "pd-eq-base15": "yes" if regs.get(0x0c70) == pd else "no"}
        failed = bool(re.search(r"FAILED|faulted", o.decode(errors="replace")))
        score(sc, preds, sets, name, obs); out[name] = (pd, inl)
        print("  %-18s %-7s words.%s pd 0x%08x lists %s base15 0x%08x snapshots %d" %
              (name, "failed" if failed else "ok", wf[-1].name.split(".")[2], pd, inl, regs.get(0x0c70, 0), len(blocks) - 1))
    return out

def main():
    import json
    d = pathlib.Path(sys.argv[1]); which = [a for a in sys.argv[2:] if not a.startswith("--")] or ["bg", "keep", "dirs"]
    jout = [a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--json=")]
    preds, sets, sc = load_preds(), load_sets(), Score()
    summary = {}
    for w in which:
        sub = {"bg": "bg-words", "keep": "keep-closed", "dirs": "dirs", "bgf1": "bg-words-f1", "keep2": "keep-partial-solo", "keep3": "keep-pages"}[w]
        r = {"bg": run_bg, "keep": run_keep, "dirs": run_dirs, "bgf1": run_bgf1, "keep2": run_keep2, "keep3": run_keep3}[w](d / sub, preds, sets, sc)
        summary[w] = {k: (v if not isinstance(v, dict) else {a: b for a, b in v.items() if a != "obj"}) for k, v in r.items()} if r else {}
    print("scoring:"); sc.show()
    summary["scoring"] = {"|".join(k): dict(v) for k, v in sc.t.items()}
    if jout:
        pathlib.Path(jout[0]).write_text(json.dumps(summary, indent=1, default=str))

if __name__ == "__main__":
    main()
