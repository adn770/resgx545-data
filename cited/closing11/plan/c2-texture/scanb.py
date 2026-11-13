import json
d=json.load(open("/Users/jtorra/src/resgx545-data/texture/p1141/support/specs.json"))
for k,v in d.items():
    t0=v["spec"].get("t0")
    if t0 is not None and t0>>27&1: print(k,v["bin"],v["group"],v["set"],hex(t0),hex(v["spec"]["t1"]),v["spec"].get("ins"), v["hyps"][:3])
c=json.load(open("/Users/jtorra/src/resgx545-data/texture/p1141/gen/cases.json"))
for v in c:
    t0=v["spec"].get("t0")
    if t0 is not None and t0>>27&1: print("cases",v["name"],v["group"],hex(t0))
