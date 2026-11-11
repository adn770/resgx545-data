"""Score rule_px.txt (model SEG-125): on R3-pixel's fills (FIT) and on E431/E357's kept timelines (round 4 scratch, read-only)."""
import os, re, sys, gzip
T, F = 125.0, 3 / 16
IDLE, TICK = 0x20, 0xccfa0

def model(tau):
    if tau < T: return None
    if tau < T / (1 - F): return tau + T
    if tau < T / F: return F * tau + T
    return T

def regimes(tau):
    out = {model(tau)}
    for b in (T, T / (1 - F), T / F):
        if abs(tau - b) <= 0.06 * b:
            out |= {model(b * 0.93), model(b * 1.07)}
    return out

def score(name, tl, i8, i118, load=False):
    runs, cur = [], []
    for t, v in tl:
        if v[i8] == IDLE:
            if cur: cur.append((t, v)); runs.append(cur); cur = []
        else: cur.append((t, v))
    if cur: runs.append(cur)
    job = [r for r in runs if any(v[i8] not in (IDLE, TICK) for _, v in r)]
    if not job: return None
    b = max(job, key=lambda r: r[-1][0] - r[0][0]); t0 = b[0][0]
    B = (b[-1][0] - t0) / 1000.0
    A = next((t for t, v in b if v[i8] in (0xfffa7, 0xfffa4)), None)
    t6 = next((t for t, v in tl if t >= t0 and v[i118] & 0x40), None)
    bit = t6 is not None
    tau = (B - 60.2) / 4
    d6 = None if (t6 is None or A is None) else (t6 - A) / 1000.0
    if 118 <= tau <= 132: vb = "edge"
    else: vb = "ok" if (tau >= T) == bit else "MISS"
    vd = "-"
    if bit and d6 is not None:
        ps = [p for p in regimes(tau) if p is not None]
        vd = "ok" if any(abs(d6 - p) <= 15 for p in ps) else "MISS"
    m = model(tau)
    return dict(name=name, B=B, tau=tau, bit=bit, d6=d6, pred=m, vb=vb, vd=vd)

def from_r3():
    D = "/Users/jtorra/src/resgx545-data/render/closing-r3-pixel/out/20261110-160415"
    for st in ("q-f0", "q-f1a", "q-f1b"):
        for f in sorted(os.listdir(os.path.join(D, st))):
            if not f.endswith(".txt.gz") or ".regs" in f or "health" in f or "ld8" in f: continue
            tl = []
            for ln in gzip.open(os.path.join(D, st, f), "rt", errors="replace"):
                if ln.startswith("tl "):
                    p = ln.split(); tl.append((int(p[1]), [int(x, 16) for x in p[2:]]))
            yield score(st + "/" + f[:-7], tl, 0, 1)

def from_output(path):
    cur = None; res = []
    def flush():
        if cur and cur["tl"] and cur["regs"] and "0x0118" in cur["regs"] and "0x0008" in cur["regs"]:
            res.append(score(cur["name"], cur["tl"], cur["regs"].index("0x0008"), cur["regs"].index("0x0118")))
    for line in open(path, errors="replace"):
        m = re.match(r"== (\S+)", line)
        if m:
            flush(); cur = {"name": m.group(1).rstrip(":"), "tl": [], "regs": None}; continue
        if cur is None: continue
        m = re.match(r"timeline: regs (.*) samples", line)
        if m: cur["regs"] = m.group(1).split()
        if line.startswith("tl "):
            p = line.split()
            try: cur["tl"].append((int(p[1]), [int(x, 16) for x in p[2:]]))
            except ValueError: pass
    flush()
    return [r for r in res if r]

def report(title, rs):
    rs = [r for r in rs if r]
    print("##", title)
    for r in rs:
        f = lambda x: "-" if x is None else f"{x:7.1f}"
        print(f"  {r['name']:44s} B {r['B']:9.1f} tau {r['tau']:8.1f} bit6 {'S' if r['bit'] else 'c'} ({r['vb']:4s}) d6 {f(r['d6'])} model {f(r['pred'])} ({r['vd']})")
    n = len(rs); ok = sum(r["vb"] == "ok" for r in rs); ed = sum(r["vb"] == "edge" for r in rs); mi = sum(r["vb"] == "MISS" for r in rs)
    s = [r for r in rs if r["bit"] and r["d6"] is not None]
    print(f"  BIT: {n} jobs: ok {ok}, edge {ed}, MISS {mi};  D6: {len(s)} set jobs with an anchor: ok {sum(r['vd']=='ok' for r in s)}, MISS {sum(r['vd']=='MISS' for r in s)}")

if __name__ == "__main__":
    report("R3-pixel fills without a load (FIT)", list(from_r3()))
    P = "/Users/jtorra/src/resgx545-data/platform"
    for d in ("event-fine", "event-steps", "event-trigger"):
        report(d + " (E431 / E357; model frozen before these were scored)", from_output(os.path.join(P, d, "output.txt")))
