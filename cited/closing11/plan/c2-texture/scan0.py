import re,glob,sys,collections
for f in sorted(glob.glob("/Users/jtorra/src/resgx545/probes/texture/*.toml")):
    t=open(f).read()
    labels=re.search(r'labels = \[(.*?)\]',t,re.S)
    for m in re.finditer(r'mov r20, #(0x[0-9a-f]+)\\nmov r21, #(0x[0-9a-f]+)',t):
        t0=int(m.group(1),16); u=(t0>>6)&7; v=(t0>>3)&7
        if u>=4: print(f.split('/')[-1], m.group(1),m.group(2),u,v)
