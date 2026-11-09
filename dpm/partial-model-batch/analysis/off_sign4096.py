"""Offline (landed E489 dumps, decoders of recompute_p1139.py): window, zeros and sign of the overflowed
4096x4096 ramp stores (G = 1 and 0, P = 0x2000) and of the no-overflow 1024x768 G = 33 store."""
import array, gzip, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recompute"))
import recompute_p1139 as R
D = "/Users/jtorra/src/resgx545-data/zls/store-layout-dumps/dumps/"
for case, ctl in (("ho-4096x4096-G1-rampx", "0x0017100c"), ("ho-4096x4096-G0-rampx", "0x00171004"),
                  ("ho-4096x4096-G1-rampy", "0x0017100c"), ("ho-4096x4096-G0-rampy", "0x00171004"),
                  ("fit-1024x768-G33-rampx", "0x0017110c")):
    a = array.array("I")
    a.frombytes(gzip.open(D + case + ".bin.gz").read())
    print(case, R.depth_facts(dict(args="--depth-ctl " + ctl), list(a)))
