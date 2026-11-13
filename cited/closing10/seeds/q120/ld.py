import gzip, numpy as np
D="/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/zst"
def ld(name,kind,sz):
    return np.frombuffer(gzip.open(f"{D}/z120-{name}-{sz}.{kind}.1.bin.gz").read(),dtype="<u4")
