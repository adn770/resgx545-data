"""Post hoc: TA3DCtl dwords 34-40, partial renders and all run peaks per g-e1 job (read-only)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "score"))
from s1lib import Kept, timeline, runs, knob_value
k = Kept(sys.argv[1])
for n in k.names():
    t = k.out(n); tl = timeline(t); b = k.buf09(n)
    prs, peaks = runs(tl)
    print(n, k.case(n).get("rc"), k.case(n).get("class"), "knob", hex(knob_value(tl, t) or 0),
          "prs", [hex(p) for p in prs], "peaks", [hex(p) for p in peaks],
          "dw34-40", [hex(x) for x in b[34:41]] if b else None)
