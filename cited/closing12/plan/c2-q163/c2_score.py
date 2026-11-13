import importlib.util, re, sys, collections
spec = importlib.util.spec_from_file_location("r", "c2_rule.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
D = "/Users/jtorra/src/resgx545-data/vdm/state-units/"
cases = []
for line in open(D + "cases.tsv").read().split("\n")[1:]:
    f = line.split("\t")
    if len(f) >= 6: cases.append(dict(name=f[0], script=f[1], set=f[2], args=f[5]))
rc = {}
cur = None
for line in open(D + "output.txt"):
    m = re.match(r"== (\S+) set=", line)
    if m: cur = m.group(1)
    m = re.match(r"\s+rc (\d+)", line)
    if m and cur: rc[cur] = int(m.group(1))
sect = collections.defaultdict(lambda: [0, 0]); cur = None
for line in open(D + "kernel.log", errors="replace"):
    m = re.search(r"resgx545 case (\S+) ", line)
    if m: cur = m.group(1); continue
    if line.startswith("## script"): cur = None
    if cur:
        if "hung, recovering" in line: sect[cur][0] += 1
        if "SGX reset:" in line: sect[cur][1] += 1
MODELS = ["M0", "M1", "M2", "M3", "NULL", "NEVER", "V16"]
tab = collections.defaultdict(lambda: collections.Counter())
rows = []; misses = collections.defaultdict(list)
state = {m: 0 for m in ("M0", "M1", "M2", "M3")}; prev_script = None
for cs in cases:
    if cs["script"] != prev_script:
        state = {m: 0 for m in state}; prev_script = cs["script"]
    n = cs["name"]; hung = sect[n][0] > 0; resets = sect[n][1]
    r = rc.get(n)
    v1, v2, why = R.job_input(cs["args"])
    void = (not hung) and r not in (0,)
    kind = "TRIV" if (v1 == 2 and v2 == 2) else ("S37" if all(v == 2 or v >= 3 for v in (v1, v2)) else "SLO")
    pred = {}
    for m in MODELS:
        c = state.get(m, 0)
        pred[m] = R.predict(m, c, v1, v2)[0]
    rows.append((cs["script"], n, v1, v2, why, kind, hung, r, resets, {m: state[m] for m in state}, pred))
    scored = why is None and not void
    for m in MODELS:
        if scored:
            key = (cs["script"], kind)
            tab[m][("all", kind, "n")] += 1; tab[m][(cs["script"], kind, "n")] += 1
            if pred[m] == hung:
                tab[m][("all", kind, "ok")] += 1; tab[m][(cs["script"], kind, "ok")] += 1
            elif m in ("M0", "M1", "M2", "M3"):
                misses[m].append((cs["script"], n, kind, "c=%d v=(%d,%d) pred=%s obs=%s" % (state[m], v1, v2, "H" if pred[m] else "C", "H" if hung else "C")))
    # state update from observed outcome
    for m in state:
        if hung or resets:
            state[m] = 0
        elif not void:
            state[m] = R.predict(m, state[m], v1, v2)[1]
print("jobs", len(rows), "hung", sum(1 for x in rows if x[6]), "void", sum(1 for x in rows if (not x[6]) and x[7] != 0))
print("hung per script:", {s: sum(1 for x in rows if x[0] == s and x[6]) for s in sorted({x[0] for x in rows})})
print("jobs with reset but no hang:", [x[1] for x in rows if x[8] and not x[6]])
print("jobs with hang line but rc 0:", [x[1] for x in rows if x[6] and x[7] == 0])
print("excluded:", collections.Counter((x[0], x[4]) for x in rows if x[4]))
print("excluded observed hung/complete:", collections.Counter((x[4] is not None and x[6]) for x in rows if x[4]))
sets = ["S37", "SLO", "TRIV"]
for scr in ["all", "vdm-state-units", "vdm-state-risky", "vdm-state-grid"]:
    print("\n== %s" % scr)
    for m in MODELS:
        out = []
        tn = to = 0
        for k in sets:
            n_ = tab[m][(scr, k, "n")]; o_ = tab[m][(scr, k, "ok")]
            out.append("%s %d/%d" % (k, o_, n_)); tn += n_; to += o_
        print("  %-6s %s  total %d/%d" % (m, "  ".join(out), to, tn))
print("\n== verdicts")
for m in ("M0", "M1", "M2", "M3"):
    ms = sum(tab[m][("all", k, "n")] - tab[m][("all", k, "ok")] for k in ("S37", "TRIV"))
    rs = tab[m][("all", "S37", "ok")] + tab[m][("all", "SLO", "ok")]
    rn = tab["NEVER"][("all", "S37", "ok")] + tab["NEVER"][("all", "SLO", "ok")]
    rv = tab["V16"][("all", "S37", "ok")] + tab["V16"][("all", "SLO", "ok")]
    print(m, "misses S37+TRIV", ms, "right on S", rs, "never", rn, "V16", rv, "->", R.verdict(ms, rs, rn, rv))
print("\n== per v (non-excluded, hang/total, by block of the non-2 word)")
byv = collections.defaultdict(lambda: [0, 0])
for x in rows:
    if x[4] or (not x[6] and x[7] != 0): continue
    for blk, v in ((1, x[2]), (2, x[3])):
        if v != 2:
            byv[(blk, v)][1] += 1; byv[(blk, v)][0] += x[6]
for k in sorted(byv): print("  block %d v=%d: hung %d of %d" % (k[0], k[1], *byv[k]))
print("\n== misses")
for m in ("M0", "M1", "M2", "M3"):
    print(m, len(misses[m]))
    for x in misses[m]: print("   ", *x)
print("\n== job table: script name v1 v2 excl kind hung rc resets c(M0,M1,M2,M3) predH(M1,M2)")
for x in rows:
    print(x[0][10:], x[1], x[2], x[3], x[4] or "-", x[5], "H" if x[6] else "C", x[7], x[8], tuple(x[9].values()), "".join("H" if x[10][m] else "C" for m in ("M1", "M2")))
