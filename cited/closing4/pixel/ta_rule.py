"""Score rule_ta.txt on kept regtimeline jobs (round 4 planning scratch; read-only)."""
import gzip, os, re, sys
IDLE, TICK = 0x20, 0xccfa0
TA = 0xccff8

def rows(path):
    out = []; regs = []
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", errors="replace") as f:
        for ln in f:
            if ln.startswith("tl "):
                p = ln.split()
                try:
                    out.append((int(p[1]), [int(x, 16) for x in p[2:]]))
                except ValueError:
                    pass
            elif ln.startswith("timeline: regs"):
                regs = ln.split("samples")[0].split()[2:]
    return regs, out

def ta_run(path, value=TA):
    regs, rs = rows(path)
    if "0x0008" not in regs or "0x0118" not in regs:
        return None
    i8, i118 = regs.index("0x0008"), regs.index("0x0118")
    best, cur = None, None
    for k, (t, v) in enumerate(rs):
        if v[i8] == value:
            if cur is None:
                cur = t
        else:
            if cur is not None:
                if best is None or t - cur > best[1] - best[0]:
                    best = (cur, t)
                cur = None
    if best is None:
        return dict(L=0.0, d7=None, s2=rs[-1][1][i118] if rs else None)
    t7 = next((t for t, v in rs if v[i118] & 0x80), None)
    return dict(L=(best[1] - best[0]) / 1000.0, d7=None if t7 is None else (t7 - best[0]) / 1000.0, s2=rs[-1][1][i118])

if __name__ == "__main__":
    d = sys.argv[1]
    tot = ok = edge = bad = 0
    for f in sorted(os.listdir(d)):
        if not (f.endswith(".txt.gz") or f.endswith(".txt")) or ".regs" in f or "health" in f:
            continue
        r = ta_run(os.path.join(d, f))
        if r is None:
            continue
        a = os.path.join(d, f.replace(".txt", ".after.regs.txt"))
        post = None
        if os.path.exists(a):
            txt = (gzip.open(a, "rt") if a.endswith(".gz") else open(a)).read()
            m = re.search(r"0x0*118\D+(?:0x)?([0-9a-fA-F]{8})", txt)
            post = int(m[1], 16) if m else None
        bit = bool((post if post is not None else r["s2"]) & 0x80)
        L = r["L"]
        if 120 <= L <= 131:
            v = "edge"; edge += 1
        elif (L >= 125) == bit and (not bit or (r["d7"] is not None and 118 <= r["d7"] <= 132)):
            v = "ok"; ok += 1
        else:
            v = "MISS"; bad += 1
        if bit and v == "edge" and not (r["d7"] is not None and 118 <= r["d7"] <= 132):
            v = "MISS(d7)"; bad += 1; edge -= 1
        tot += 1
        print(f"{f:40s} L {L:7.1f} bit7 {'S' if bit else 'c'} d7 {r['d7'] if r['d7'] is None else round(r['d7'],1)} {v}")
    print(f"TOTAL {tot}: ok {ok}, edge {edge}, MISS {bad}")
