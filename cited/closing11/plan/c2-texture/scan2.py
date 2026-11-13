import json,glob,collections
for f in ["texture/p1141/gen/cases.json","texture/p1141/support/specs.json"]+glob.glob("texture/p1132*/**/*.json",recursive=True):
    try: d=json.load(open(f))
    except Exception as e: print(f,e); continue
    items=d if isinstance(d,list) else list(d.values())
    c=collections.Counter(); hits=[]
    def walk(o,name):
        if isinstance(o,dict):
            if 't0' in o and isinstance(o['t0'],int):
                t0=o['t0']; c[(t0>>6)&7]+=1
                if (t0>>6)&7>=4: hits.append((name,hex(t0),hex(o.get('t1',0))))
            for k,v in o.items(): walk(v,name)
        elif isinstance(o,list):
            for v in o: walk(v,name)
    for it in items: walk(it, it.get('name') if isinstance(it,dict) else '')
    print(f,dict(c),hits[:10])
