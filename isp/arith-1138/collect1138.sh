#!/bin/bash
# collect1138.sh SET_NAME_DIR: copy the laptop's ~/p1138-dumps/main (and pilot, pilot2) into the untracked data
# repository as isp/arith-1138/, with env.toml and the kernel log since the start. Copies only; deletes nothing.
cd "$(dirname "$0")" || exit 1
DS=$HOME/src/resgx545-data/isp/arith-1138
LAP="ssh -o HostKeyAlias=cedar -o BatchMode=yes -o ConnectTimeout=10 jtorra@10.42.0.2"
mkdir -p "$DS"
$LAP 'cd ~/p1138-dumps && tar cf - main fine fine2 pilot pilot2' | tar xf - -C "$DS"
START=$($LAP 'cat ~/p1138-dumps/main/start.epoch')
$LAP 'sudo -n journalctl -k --since "@'$START'" --no-pager' | gzip -n -6 > "$DS/kernel.log.gz"
cp cases.tsv cases-fine.tsv cases-fine2.tsv pilot-cases.tsv plan.md iter.toml deploy1138.sh deploy1138b.sh stage1138.sh freeze1138.sh freeze-fine1138.sh freeze-fine2-1138.sh analyze1138.sh collect1138.sh "$DS/"
cp predictions-1138.toml predictions-1138.sha256 manifest-1138.sha256 predictions-fine-1138.toml predictions-fine-1138.sha256 manifest-fine-1138.sha256 predictions-fine2-1138.toml predictions-fine2-1138.sha256 manifest-fine2-1138.sha256 "$DS/"
cp -R templates gen run recompute analysis-main "$DS/" 2>/dev/null
mkdir -p "$DS/tool-sources" && cp tool/userspace/libsgxfive/tools/sgxfive-test.c "$DS/tool-sources/sgxfive-test-1138.c" && cp tool/userspace/libsgxfive/src/render.c "$DS/tool-sources/render-1138.c" && cp tool-b/userspace/libsgxfive/tools/sgxfive-test.c "$DS/tool-sources/sgxfive-test-1138b.c" && cp tool-b/userspace/libsgxfive/src/render.c "$DS/tool-sources/render-1138b.c"
{ echo "# phase 11.38 arithmetic sweep"
  echo "name = \"arith-1138\""
  echo "date = \"$(date +%Y-%m-%dT%H:%M:%S%z)\""
  echo "cases_sha256 = \"$(shasum -a 256 cases.tsv | cut -d' ' -f1)\""
  echo "predictions_sha256 = \"$(shasum -a 256 predictions-1138.toml | cut -d' ' -f1)\""
  echo "manifest_sha256 = \"$(shasum -a 256 manifest-1138.sha256 | cut -d' ' -f1)\""
  echo "tool_source_sha256 = \"$(shasum -a 256 tool/userspace/libsgxfive/tools/sgxfive-test.c | cut -d' ' -f1)\""
  echo "tool_render_c_sha256 = \"$(shasum -a 256 tool/userspace/libsgxfive/src/render.c | cut -d' ' -f1)\""
  echo "run_script_sha256 = \"$(shasum -a 256 run/run_p1138.py | cut -d' ' -f1)\""
  $LAP 'echo "tool_sha256 = \"$(sha256sum ~/sgxfive-test-1138 | cut -d" " -f1)\""; echo "kernel = \"$(uname -r)\""; echo "module_srcversion_installed = \"$(modinfo -F srcversion gma500_gfx)\""; echo "module_srcversion_loaded = \"$(sudo -n cat /sys/module/gma500_gfx/srcversion)\""; echo "firmware_sha256 = \"$(sha256sum /lib/firmware/sgx545_ukernel.fw | cut -d" " -f1)\""; echo "run_script_on_laptop_sha256 = \"$(sha256sum ~/p1138-run/run_p1138.py | cut -d" " -f1)\""; echo "bins_sha256_of_list = \"$(cat ~/p1138-bins/*.bin | sha256sum | cut -d" " -f1)\""'
} > "$DS/env.toml"
du -sh "$DS"
