#!/bin/bash
# stage-p1141tex.sh: the programs of the texture scripts (the generator wrote them to stage-bins/ already)
# copied to the laptop's ~/sgxprobes-stage-1141tex. SGX_TARGET_HOST / SGX_TARGET_SSH_OPTS as in the other stage scripts.
set -eu
P=$(cd "$(dirname "$0")" && pwd)
ls "$P"/stage-bins/*.bin | wc -l
if [ -n "${SGX_TARGET_HOST:-}" ]; then
	ssh ${SGX_TARGET_SSH_OPTS:-} "$SGX_TARGET_HOST" 'mkdir -p sgxprobes-stage-1141tex'
	scp -q ${SGX_TARGET_SSH_OPTS:-} "$P"/stage-bins/*.bin "$SGX_TARGET_HOST:sgxprobes-stage-1141tex/"
	echo "copied to $SGX_TARGET_HOST:sgxprobes-stage-1141tex"
fi
