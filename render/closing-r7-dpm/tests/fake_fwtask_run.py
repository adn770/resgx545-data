#!/usr/bin/env python3
"""fake fwtask_run.py for the R7-dpm mock (R5-dpm's, logging the blob's name): the subcommands the runner may call (arm, write, page, status), each one JSON object, on the
fake debugfs (SGXFIVE_DEBUGFS): arm writes own_arm "armed" (FAKE_ARM_FAIL=1: not ok); write zeroes dwords of own_res.json; page serves
it (the page the world wrote through sgx-sim); status reads `stalled`.  Any other subcommand exits 9 (the runner must never call it)."""
import json
import os
import pathlib
import sys

d = pathlib.Path(os.environ["SGXFIVE_DEBUGFS"])
cmd, a = sys.argv[1], (json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
with open(d / "fw.log", "a") as f:
    f.write(cmd + " " + (pathlib.Path(a["blob"]).name + " " if "blob" in a else "") + json.dumps(a)[:80] + "\n")
page = json.loads((d / "own_res.json").read_text()) if (d / "own_res.json").exists() else [0] * 1024
if cmd == "arm":
    ok = os.environ.get("FAKE_ARM_FAIL") != "1" and pathlib.Path(a["blob"]).exists() and a["arm"] == "slots=0xf entry=0,1,2,3"
    (d / "own_arm").write_text("armed\n" if ok else "off\n")
    page = [0] * 1024
    page[0] = 0x4E574F53
    page[16:20] = [3, 1, 2, 1]
    (d / "own_res.json").write_text(json.dumps(page))
    print(json.dumps({"ok": ok, "own_arm": "armed", "alive": {"advancing": True}, "magic": page[0]}))
elif cmd == "write":
    page[a["dword"]:a["dword"] + len(a["vals"])] = a["vals"]
    (d / "own_res.json").write_text(json.dumps(page))
    print(json.dumps({"ok": True}))
elif cmd == "page":
    print(json.dumps({"page": page}))
elif cmd == "status":
    st = (d / "stalled").exists()
    if st:
        (d / "stalled").unlink()
    print(json.dumps({"alive": {"advancing": not st}, "health": {"ok": not st}}))
else:
    sys.exit(9)
