"""Round 7 plan, Q293 (offline, read-only): for the 13 kept two-object dumps of obj2_inserted.out, the job's own output:
the kpokes before render 2 at dword 11 and the last render's 'N triangle, M background' line.  Render 2's own object (at
dword 27, zero at 38, format word at 39 in all 13) covers the whole 64 x 64 target (--tri-full), so an image with 0
triangle pixels means the 3D drew nothing for it."""
import gzip, re
ROOT = "/Users/jtorra/src/resgx545-data/render/"
empty = total = 0
for line in open("obj2_inserted.out"):
    p = line.split(" ")[0]
    t = p.replace(".tri.param.bin.gz", ".txt.gz")
    txt = gzip.open(ROOT + t, "rt", errors="replace").read()
    poke = re.findall(r"kpoke before render 2: par:11=(0x[0-9a-f]+)", txt)
    te = re.search(r"te(\w+)", p)
    img = re.findall(r"tri \d+x\d+ #(\d): (\d+) triangle, (\d+) background, (\d+) other", txt)
    total += 1
    last = img[-1] if img else None
    if last and last[1] == "0":
        empty += 1
    print("%-70s par:11 poke %-12s last image %s" % (t[len("closing-"):-7], poke[0] if poke else "-", last))
print("dumps %d, last image with 0 triangle pixels %d" % (total, empty))
