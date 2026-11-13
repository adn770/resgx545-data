# POST HOC (after c2_score.out was read): misses on S37+TRIV of the M1 counter as T varies
# and with a one-job memory rival; for reading how tight the fit is, not a frozen test.
import importlib.util, subprocess, re
spec = importlib.util.spec_from_file_location("r", "c2_rule.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
rows = []
for line in open("c2_score.out").read().split("## ")[0].split("\n"):
    pass
txt = open("c2_score.out").read().split("== job table")[1].split("\n")[1:]
for l in txt:
    f = l.split()
    if len(f) < 9: continue
    scr, name, v1, v2, ex, kind, hc, rc, resets = f[:9]
    rows.append((scr, int(v1), int(v2), ex != "-", hc == "H", int(resets)))
for T in range(5, 12):
    R.LIMIT = T
    miss = 0; c = 0; prev = None
    for scr, v1, v2, ex, hung, resets in rows:
        if scr != prev: c = 0; prev = scr
        pred, c2 = R.predict("M1", c, v1, v2)
        if not ex and (v1 != 2 or v2 != 2 or True) and all(v in (2, 3, 4, 5, 6, 7) for v in (v1, v2)) and pred != hung: miss += 1
        c = 0 if (hung or resets) else c2
    print("T=%d misses on non-excluded rows with v in 2..7: %d" % (T, miss))
