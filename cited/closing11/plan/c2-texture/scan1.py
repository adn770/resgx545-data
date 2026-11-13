import re,glob,collections
for f in sorted(glob.glob("/Users/jtorra/src/resgx545/probes/**/*.toml",recursive=True))+sorted(glob.glob("/Users/jtorra/src/resgx545-data/texture/p1141/**/*.s",recursive=True)):
    t=open(f).read()
    c=collections.Counter()
    for m in re.finditer(r'mov r20, #(0x[0-9a-f]+)',t):
        t0=int(m.group(1),16); u=(t0>>6)&7
        c[u>=4]+=1
    if c[True]: print(f,dict(c))
