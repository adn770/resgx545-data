#!/bin/bash
# deploy1138b.sh: build this tree's sgxfive-test on the laptop as ~/sgxfive-test-1138b (a userspace compile,
# no git, no deletion: the build directory must not exist) and print the sha256 of the source file, of the
# copy the laptop built from and of the binary.
cd "$(dirname "$0")/tool-b" || exit 1
sha256sum userspace/libsgxfive/tools/sgxfive-test.c userspace/libsgxfive/src/render.c
COPYFILE_DISABLE=1 tar cf - --exclude=build --exclude=__pycache__ --exclude='*.dSYM' userspace/libsgxfive include/uapi 2>/dev/null |
	ssh -o HostKeyAlias=cedar jtorra@10.42.0.2 'mkdir ~/libsgxfive-1138b || exit 1; cd ~/libsgxfive-1138b && tar xf - 2>/dev/null;
	sha256sum userspace/libsgxfive/tools/sgxfive-test.c userspace/libsgxfive/src/render.c;
	cd userspace/libsgxfive && make -j2 build/sgxfive-test 2>&1 | grep -E " error |warning:";
	cp build/sgxfive-test ~/sgxfive-test-1138b; sha256sum ~/sgxfive-test-1138b'
