#!/bin/bash
# stage1139.sh: copy the scripts, tables and the green pixel program to the laptop (NOT RUN in 11.39
# planning: no laptop access). The tool: ~/sgxfive-test-1135 (built by deploy1135.sh from the overlay
# 11.35 source, sha256 f5cdccb15a73de6584e33e43c5a2eb1ba5e37de7e43a07c39cb9a8d386c6e74b); the changed
# copy ~/sgxfive-test-1139 only for part B (deploy1139.sh).
set -eu
P=$(cd "$(dirname "$0")" && pwd)
O="-o BatchMode=yes -o HostKeyAlias=cedar"
ssh $O jtorra@10.42.0.2 'mkdir -p sgxprobes-stage-1139 p1139/tables'
scp -q $O "$P"/stage-bins/p1139-green.bin jtorra@10.42.0.2:sgxprobes-stage-1139/
scp -q $O "$P"/lib1139.sh "$P"/run_table.sh "$P"/run-all-1139.sh jtorra@10.42.0.2:p1139/
scp -q $O "$P"/tables/*.txt jtorra@10.42.0.2:p1139/tables/
