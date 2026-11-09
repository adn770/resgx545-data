#!/bin/bash
# deploy1140.sh: build this tree's sgxfive-test on the laptop as ~/sgxfive-test-1140 (userspace compile, no git, no
# deletion: the build directory must not exist); prints the sha256 of the sources and of the binary.
cd "$(dirname "$0")/tool" || exit 1
sha256sum userspace/libsgxfive/tools/sgxfive-test.c userspace/libsgxfive/src/render.c userspace/libsgxfive/include/sgxfive_render.h
COPYFILE_DISABLE=1 tar cf - --exclude=build --exclude=__pycache__ --exclude='*.dSYM' userspace/libsgxfive include/uapi 2>/dev/null |
	ssh -o HostKeyAlias=cedar jtorra@10.42.0.2 'mkdir ~/libsgxfive-1140 || exit 1; cd ~/libsgxfive-1140 && tar xf - 2>/dev/null;
	sha256sum userspace/libsgxfive/tools/sgxfive-test.c userspace/libsgxfive/src/render.c userspace/libsgxfive/include/sgxfive_render.h;
	cd userspace/libsgxfive && make -j2 build/sgxfive-test 2>&1 | grep -E " error |warning:";
	cp build/sgxfive-test ~/sgxfive-test-1140; sha256sum ~/sgxfive-test-1140'
