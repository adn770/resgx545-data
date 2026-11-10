"""Post hoc: per job of a kept stage, the 0x0658 stretches with the status at entry, run peaks,
the control block dwords 34-40 of every ta3d snapshot kept, and the open-kick lines."""
import sys, pathlib, re, gzip, struct
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "score"))
from s1lib import Kept, timeline, runs, knob_value
k = Kept(sys.argv[1])
names = sys.argv[2:] or k.names()
for n in names:
    t = k.out(n); tl = timeline(t)
    if not tl:
        print(n, "no timeline"); continue
    prs, peaks = runs(tl)
    regs, rows = tl
    ip, ist = regs.index("0x0658") + 1, regs.index("0x0724") + 1
    # stretches with sample times
    st, inpr, s0 = [], False, None
    for r in rows:
        if r[ip] & 1 and not inpr:
            inpr, s0 = True, r
        elif not (r[ip] & 1) and inpr:
            inpr = False; st.append((s0[0], r[0], hex(s0[ist] & 0xffff)))
    snaps = sorted(k.d.glob(f"{n}.ta3d.*.bin.gz"))
    dws = []
    for p in snaps:
        b = gzip.open(p).read()
        if len(b) >= 164:
            w = struct.unpack("<41I", b[:164]); dws.append((p.name.split(".")[-3], [hex(x) for x in w[34:41]]))
    print(n, "rc", k.case(n).get("rc"), "prs", [hex(p) for p in prs], "peaks", [hex(p) for p in peaks],
          "stretches(us)", [(a // 1000, b // 1000, s) for a, b, s in st])
    for s, d in dws:
        print("   ta3d", s, d)
    for ln in (t or "").splitlines():
        if re.search(r"geometry only|overflowed|renders ok|moved by|job:", ln):
            print("   ", ln[:120])
