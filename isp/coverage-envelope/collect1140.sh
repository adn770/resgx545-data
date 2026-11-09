#!/bin/bash
# collect1140.sh: copy the laptop's ~/p1140-dumps (pilot, main, far) into the untracked data repository as
# isp/coverage-envelope/, with env.toml and the kernel log since the start; copies only, deletes nothing.
cd "$(dirname "$0")" || exit 1
DS=$HOME/src/resgx545-data/isp/coverage-envelope
LAP="ssh -o HostKeyAlias=cedar -o BatchMode=yes -o ConnectTimeout=10 jtorra@10.42.0.2"
mkdir -p "$DS"
for d in pilot main far; do
	$LAP "cd ~/p1140-dumps && [ -d $d ] && tar cf - $d" | tar xf - -C "$DS" 2>/dev/null
done
START=$($LAP 'cat ~/p1140-dumps/start.epoch')
$LAP 'sudo -n journalctl -k --since "@'$START'" --no-pager' | gzip -n -6 > "$DS/kernel.log.gz"
for d in pilot main far; do [ -d "$DS/$d" ] && cp cases-1140.tsv "$DS/$d/"; done
mkdir -p "$DS/tool-sources" "$DS/gen" "$DS/run" "$DS/recompute" "$DS/tests"
cp cases-1140.tsv predictions-1140.toml predictions-1140.sha256 manifest-1140.sha256 deploy1140.sh freeze1140.sh runchunk.sh collect1140.sh plan.md "$DS/" 2>/dev/null
cp gen/gen_p1140.py "$DS/gen/"; cp run/run_p1140.py "$DS/run/"; cp recompute/model1140.py recompute/recompute_p1140.py "$DS/recompute/"
cp tests/test_run_p1140.py tests/test_recompute_p1140.py "$DS/tests/"
cp tool/userspace/libsgxfive/tools/sgxfive-test.c "$DS/tool-sources/sgxfive-test-1140.c"
cp tool/userspace/libsgxfive/src/render.c "$DS/tool-sources/render-1140.c"
cp tool/userspace/libsgxfive/include/sgxfive_render.h "$DS/tool-sources/sgxfive_render-1140.h"
{ echo "# phase 11.40 coverage envelope sweep"
  echo "name = \"coverage-envelope\""
  echo "date = \"$(date +%Y-%m-%dT%H:%M:%S%z)\""
  for f in cases-1140.tsv predictions-1140.toml manifest-1140.sha256 run/run_p1140.py; do echo "$(echo $f | tr -c 'a-z0-9\n' _)_sha256 = \"$(shasum -a 256 $f | cut -d' ' -f1)\""; done
  echo "tool_source_sha256 = \"$(shasum -a 256 tool/userspace/libsgxfive/tools/sgxfive-test.c | cut -d' ' -f1)\""
  echo "tool_render_c_sha256 = \"$(shasum -a 256 tool/userspace/libsgxfive/src/render.c | cut -d' ' -f1)\""
  $LAP 'echo "tool_sha256 = \"$(sha256sum ~/sgxfive-test-1140 | cut -d" " -f1)\""; echo "kernel = \"$(uname -r)\""; echo "module_srcversion_installed = \"$(modinfo -F srcversion gma500_gfx)\""; echo "module_srcversion_loaded = \"$(sudo -n cat /sys/module/gma500_gfx/srcversion)\""; echo "firmware_sha256 = \"$(sha256sum /lib/firmware/sgx545_ukernel.fw | cut -d" " -f1)\""; echo "run_script_on_laptop_sha256 = \"$(sha256sum ~/p1140-run/run/run_p1140.py | cut -d" " -f1)\""; echo "cases_on_laptop_sha256 = \"$(sha256sum ~/p1140-run/cases-1140.tsv | cut -d" " -f1)\""'
} > "$DS/env.toml"
du -sh "$DS"
