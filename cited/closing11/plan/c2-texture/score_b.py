"""Score check B (rule_b.py, frozen). Run: python -I score_b.py > score_b.out
Footprints: r10-tex gen/srgb.py footprint() (strided g-bl-st form) and, for an-t0b27, the 11.32
model texmodel.py (p1141/support) with level_read instrumented to capture the bilinear corners."""
import gzip, importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
D = "/Users/jtorra/src/resgx545-data"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("rule_b", HERE + "/rule_b.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
sys.path.insert(0, D + "/render/closing-r10-tex/gen")
import pins, srgb as S
sys.path.insert(0, D + "/texture/p1141/support")
import texmodel as TM

cases = {c["name"]: c for c in json.loads(pins.blob("data:texture/p1141/gen/cases.json"))}
E723 = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/"
r9 = pins.module("data:render/closing-r9-x/gen/srgb.py", "r9x_srgb")

def foot_strided(sp):
    out = []
    for p in range(2048):
        t, fx, fy = S.footprint(sp, p % 64, p // 64)
        out.append((t, int(fx * 64 // 1), int(fy * 64 // 1)))
    return out

def foot_r9(sp):
    return [r9.footprint(sp, p % 64, p // 64) for p in range(2048)]

def foot_tm(spc):
    cap = {}
    orig = TM.Tex.level_read
    def lr(self, u, v, l, bilinear):
        if bilinear:
            lw, lh, _ = self.level_geom(l)
            x, y = u * lw - 0.5, v * lh - 0.5
            import math
            x0, y0 = math.floor(x), math.floor(y)
            cap.setdefault("n", 0); cap["n"] += 1
            cap["last"] = ([self.fetch(x0 + dx, y0 + dy, l) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))],
                           int((x - x0) * 64), int((y - y0) * 64))
        return orig(self, u, v, l, bilinear)
    TM.Tex.level_read = lr
    out, hw_none = [], 0
    r = dict(TM.RULES); r.update(spc.get("rules", {}))
    inj = {int(k): v for k, v in spc.get("inject", {}).items()}
    tex = TM.Tex(spc["t0"], spc["t1"], spc["base"], spc["t3"], spc.get("pages", 16), r, inj)
    for y in range(TM.H):
        for x in range(TM.W):
            cap.clear(); cap["n"] = 0
            u, v = TM.ev(spc["u"], x, y), TM.ev(spc["v"], x, y)
            g = [TM.ev(s, x, y) for s in spc["grad"]]
            lod = TM.lod_of(g, tex.w, tex.h, r["lodf"])
            tex.sample(u, v, lod)
            out.append(cap.get("last") if cap["n"] == 1 else None)
    TM.Tex.level_read = orig
    return out

def score(name, foot, hw, note):
    ex = {m: 0 for m in ("none", "out", "in", "inout")}
    hx = {m: 0 for m in ex}
    part = sub = n = 0; pixsub = 0
    for fp, got in zip(foot, hw):
        if fp is None: continue
        t, kx, ky = fp
        n += 1
        pred = {m: 0 for m in ex}; log = []
        for c in (0, 1):
            b4 = [v >> 8 * c & 255 for v in t]
            hh = got >> 16 * c & 0xFFFF
            lg = []
            res = {m: R.two_stage(b4, kx, ky, m, lg if m == "none" else None) for m in ex}
            for m in ex:
                pred[m] |= res[m] << 16 * c; hx[m] += res[m] == hh
            part += res["none"] != res["out"]
            sub += bool(lg)
            pixsub += 0
        for m in ex: ex[m] += pred[m] == (got & 0xFFFFFFFF)
    print(f"{name}: {note}; pixels with a footprint {n}; exact pixels BF11 {ex['none']} FTZ-OUT {ex['out']} "
          f"FTZ-IN {ex['in']} FTZ-INOUT {ex['inout']}; exact halves BF11 {hx['none']} OUT {hx['out']} "
          f"IN {hx['in']} INOUT {hx['inout']} of {2 * n}; PART halves {part}; SUB halves {sub}")

for nm in ("g-bl-st-a", "g-bl-st-b"):
    sp = cases[nm]["spec"]
    score(nm, foot_strided(sp), pins.kept_pixels(E723 + nm + ".txt.gz"), "E723 original (b held out for BF11, a scored after freeze; neither in the FTZ fit)")
sp = cases["g-bl-st-a"]["spec"]
score("srgb2-ctl", foot_strided(sp), pins.pixels(gzip.open(D + "/render/closing-r10-tex/out/20261113-102730/srgb2/srgb2-ctl.txt.gz", "rt").read(), 2048), "r10-tex rerun of g-bl-st-a (same inputs, second observation)")
score("srgb-ctl", foot_strided(sp), pins.kept_pixels("data:render/closing-r9-x/out/20261113-081821/srgb/srgb-ctl.txt.gz"), "r9-x rerun of g-bl-st-a (third observation)")
spq = r9.spec_a(r9.eq_rows(9050))
score("srgb-eq", foot_r9(spq), pins.kept_pixels("data:render/closing-r9-x/out/20261113-081821/srgb/srgb-eq.txt.gz"), "r9-x equal-corner control")
spec_an = json.load(open(D + "/texture/p1141/support/specs.json"))["an-t0b27"]["spec"]
hw = pins.pixels(gzip.open(D + "/texture/p1132/tx-lod/an-t0b27.txt.gz", "rt").read(), 2048)
score("an-t0b27", foot_tm(spec_an), hw, "p1132 tx-lod 64x64 twiddled, aniso grad, texmodel footprint (LOD and layout are the model's)")
