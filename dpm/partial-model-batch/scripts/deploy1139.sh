#!/bin/bash
# deploy1139.sh: part B only (NOT RUN in planning): build the changed tool copy (T2, T3, T4) on the laptop
# as ~/sgxfive-test-1139 and print the sha256 of the source file and of the binary. Userspace compile only.
cd "$(dirname "$0")/tool-new"
sha256sum userspace/libsgxfive/tools/sgxfive-test.c
tar cf - --exclude=build userspace/libsgxfive include/uapi 2>/dev/null | ssh -o HostKeyAlias=cedar jtorra@10.42.0.2 'rm -f ~/libsgxfive-1139.tar; mkdir -p ~/libsgxfive-1139 && cd ~/libsgxfive-1139 && tar xf - 2>/dev/null; sha256sum userspace/libsgxfive/tools/sgxfive-test.c; cd userspace/libsgxfive && make -j2 build/sgxfive-test 2>&1 | grep -E " error |warning:"; cp build/sgxfive-test ~/sgxfive-test-1139; sha256sum ~/sgxfive-test-1139; ls -l ~/sgxfive-test-1139'
