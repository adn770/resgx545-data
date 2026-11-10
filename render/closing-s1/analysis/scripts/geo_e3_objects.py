"""Post hoc: decoded first object (rhw words, x, y, packed z word) of g-e3 jobs (read-only)."""
import sys, pathlib, struct
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "score"))
from s1lib import Kept
import score_geo as G
k = Kept(sys.argv[1])
f = lambda b: struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]
for n in (sys.argv[2:] or k.names()):
    d = G.decode_object(k.dump(n, "param.bin"), k.dump(n, "tadata.bin"))
    if d["state"] != "present":
        print(n, d["state"], len(d["words"])); continue
    xy = G._xy(d)
    print(n, "nvert", d["nvert"], "rhw", [f"{w:#010x}={f(w):.6g}" for w in d["rhw"]])
    print("    xy", [(round(x, 4), round(y, 4)) for x, y in xy], "z", [f"{z:#010x}={f(z):.6g}" for _, _, z in d["packed"]])
