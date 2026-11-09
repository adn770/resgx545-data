// SPDX-License-Identifier: MIT
/*
 * sgxfive-test: the kernel's debugfs checks (dri/N/sgx/...) redone from
 * userspace through the sgxfive render node, and the hardware probes.
 *
 *   sgxfive-test [--mock[=rev1|harness|none]] [--mock-pb-pages=N] [--device PATH]
 *                [--programs=asm|fake] <command> [options]
 *
 *   query                         DEV_QUERY: GPU, firmware, job limits, heaps
 *   dummy [-n N] [--kpoke-job N:SPEC]... [--wait-ms MS]
 *                                 N dummy transfers chained through one syncobj;
 *                                 --kpoke-job writes SPEC to debugfs kpoke just before
 *                                 job N (th:W=V, a word of the transfer context's HW
 *                                 context, is applied to that submission); --wait-ms MS:
 *                                 how long the chain is waited for (default 5000), a
 *                                 job that does not complete reported as such
 *   fill  [--width W --height H --x X --y Y --stride S --colour C] [--kpoke-job 1:SPEC]
 *         [JOB OPTIONS]
 *   copy  [--width W --height H --sx X --sy Y --src-stride S --dx X --dy Y --dst-stride S]
 *         [--every-value | --ramp CH=START [--ramp-base V]] [--print-addrs] [--page-before]
 *         [JOB OPTIONS]
 *   isolation                     VM separation, faults, lost contexts, read-only maps
 *   tri   [--width W --height H -n N] [--max-width W --max-height H] [--fault]
 *         [--scratch N [--scratch-fill V] [--scratch-at ADDR] [--scratch-file FILE]] [--kpoke-render N:SPEC]... [--move N:DX,DY]...
 *         [--geometry N]... [--keep-going] [--keep-overflow] [--dump-render DIR [--dump-each]]
 *         [--tri-full] [--tri-z A,B,C]
 *         [--depth [--depth-ctl V] [--depth-ctl-next V] [--depth-fill F] [--depth-base V]
 *                [--depth-pages N] [--depth-dump DIR] [--depth-store [--depth-store-fill F]]
 *                [--stencil [--stencil-fill F] [--stencil-store [--stencil-store-fill F]]]]
 *         [--words DIR]
 *         [--wait-ms MS] [--ctx2 [--share-pb] [--overlap] [--close-first-early] [--words-between]]
 *         [JOB OPTIONS]
 *                                 the first triangle on a render context, N times,
 *                                 every pixel against the CPU reference; the context
 *                                 takes targets up to --max-width x --max-height
 *                                 (default: the target's size); --fault unmaps the
 *                                 scene's stream first, so the render faults;
 *                                 --scratch maps N more pages (their address printed)
 *                                 for a kernel poke to point a unit at, filled with V
 *                                 (default 0.25f) before each render, the dwords it
 *                                 changed reported page by page; --scratch-file FILE: the
 *                                 first dwords of the pages are the file's (a table the
 *                                 host built) and the report counts against them;
 *                                 --scratch-at ADDR maps
 *                                 them at ADDR (a heap's page, say, that a unit fetches
 *                                 from) instead of in the general heap; --kpoke-render writes
 *                                 SPEC to debugfs kpoke just before render N (each
 *                                 render of the context its own kernel pokes); --move
 *                                 draws render N's triangle DX, DY pixels away;
 *                                 --geometry submits render N geometry only (the scene
 *                                 left open for the next render, nothing drawn);
 *                                 --keep-going reports every render, checked or not;
 *                                 --keep-overflow counts a render whose scene overflowed
 *                                 the parameter buffer and goes on; --dump-each: the
 *                                 --dump-render files after every render N (DIR/tri.N.*);
 *                                 --depth: a depth buffer the ZLS pokes point at, its
 *                                 changed dwords and frequent values reported per render;
 *                                 a fill F is a value, index or bit:K; --depth-store,
 *                                 --stencil, --stencil-store: further buffers (the store base
 *                                 on its own, the stencil bases); --tri-full: the triangle
 *                                 covers the target; --tri-z A,B,C: its vertices' depths
 *                                 --dump-render DIR: after the renders, the kernel's
 *                                 debugfs render_param and render_tadata copied to
 *                                 DIR/tri.param.bin and DIR/tri.tadata.bin;
 *                                 --words DIR: the kernel's debugfs render_words and
 *                                 buf09 (the TA/3D control block) copied to
 *                                 DIR/words.N.txt and DIR/ta3d.N.bin before the first
 *                                 render (N = 0) and after each render N, failed or
 *                                 not, while the context lives; --wait-ms MS: how long
 *                                 each render is waited for (default 5000);
 *                                 --ctx2: a second render context in the VM (the same
 *                                 scene, the other pair of colours), rendered after each
 *                                 render of the first and checked on its own (the lines
 *                                 "tri2"); --share-pb: it runs on the first's parameter
 *                                 buffer (writes Y to debugfs render_share_pb before it
 *                                 is created; the kernel needs the debug option);
 *                                 --overlap: its job is submitted before the first's is
 *                                 waited for (whether both were in the firmware at once
 *                                 is not checked);
 *                                 --close-first-early: in the last iteration the first
 *                                 context is closed after its render and before the
 *                                 second context's (with --words a snapshot before the
 *                                 close, N = 100 + the render, and one after it, 200 +
 *                                 the render; with --close-trace the cleanup's trace);
 *                                 --words-between (with --words): a snapshot, N = 100 +
 *                                 the render, before each second-context render;
 *                                 --kreg-render N:OFFSET=VALUE (or ^=): writes the
 *                                 register to debugfs kregnow just before render N,
 *                                 --kreg-render2 before the second context's render N;
 *                                 --close-first: the first context is closed before the
 *                                 second (the default closes the second first);
 *                                 --wait-second (with --overlap): the second context's job is
 *                                 waited for before the first's;
 *                                 --close-trace: after each close, the lines of debugfs
 *                                 render_cleanup and TA3DCtl dwords 32, 46 and 47;
 *                                 --kpoke-render2 N:SPEC: as --kpoke-render, before the
 *                                 second context's render N (with --overlap, 30 ms
 *                                 after the first context's job is submitted, so that
 *                                 the kernel has kicked it and the poke lands on the
 *                                 second context's kick)
 *   contexts [--width W --height H -n N]  N render contexts for targets up to W x H
 *                                 in one VM, and the memory they take (MemFree and
 *                                 LowFree of /proc/meminfo, before and after)
 *   regaccess                     client fill shaders that read and write SGX
 *                                 registers, read temporaries they did not write
 *                                 and kick code base 15
 *   probe [--stamp] [--temps N] [--coords] [--pixels] [--scratch-pages N] [--pds N --use USE]
 *         [--place OFFSET=FILE --place-form cbase|exe18]
 *         [--scratch-heap texture] [--poke xfer:N=V|bg:N=V]... [--low ADDR] [--late R:K=V] FILE...
 *                                 each FILE (tools/usse-asm output) as the fill
 *                                 shader of its own fill, with N temporaries
 *                                 (default 32) and a 64 KiB scratch buffer (--scratch-pages N: 16
 *                                 to 64 pages); prints
 *                                 o0 and the scratch dwords the program changed;
 *                                 --coords: as the copy shader of a copy whose
 *                                 source texel (x, y) is (y << 16) | x, so pa0 holds
 *                                 the pixel's coordinates; --pixels: every pixel too;
 *                                 --pds N --use USE: each FILE is a PDS program with N
 *                                 data dwords (U0-U2 in dwords 0-2 are set to kick the
 *                                 secondary USE task) as the fill's (with --coords, the
 *                                 copy's: USE then reads the texel in pa0) PDS secondary,
 *                                 USE its shader (a USE program that stores the
 *                                 secondary attributes sa0-sa15); --low ADDR: the scratch
 *                                 buffer mapped again at ADDR, a page in the first MiB
 *                                 (page 0 excepted), for the PDS's load and store; needs
 *                                 the kernel's debugfs sgx/vm_low; --late R:K=V: while
 *                                 the job runs, once scratch dword R leaves its fill
 *                                 (or after LATE_NS), the host writes V to dword K;
 *                                 --scratch-heap texture: the scratch buffer in the
 *                                 texture heap, so that a texture in it is in the
 *                                 texture region (its address 0xf0000000 and up);
 *                                 --place OFFSET=FILE --place-form cbase|exe18: the
 *                                 USE program FILE mapped at the USSE pixel heap's base
 *                                 + OFFSET (a multiple of 8, below the heap's 5 MiB), its
 *                                 scratch immediates patched, and started in place of the
 *                                 fill shader (the probe's own program, at the heap's
 *                                 base, stays unstarted) by a primary DOUTU whose EXE and
 *                                 CBASE hold the offset as cbase (bits 18:3 in EXE, bits
 *                                 22:19 in CBASE) or as exe18 (bits 20:3 in an 18-bit EXE,
 *                                 CBASE 0); the program placed is the emitter an emitpds
 *                                 probe needs (the --pds file, or the built-in secondary,
 *                                 is what it names); a limm of 0x5CB0nnnn or 0x5CB1nnnn in
 *                                 the fill shader or the placed program is patched to the
 *                                 PDS secondary's pixel PDS heap offset (0x5CB0) or GPU
 *                                 address (0x5CB1) shifted right by four, plus nnnn (the s1
 *                                 of an emitpds), and the probe prints where it is
 *   probe --tri SLOT[:N] [--slot SLOT=FILE[:N]]... [--width W --height H]
 *         [--max-width W --max-height H] [--vertices N [--copy-depth]] [--tri-full] [--vtx-coords N]
 *         [--isp2 V] [--blk-add BIT=V[,V]]...
 *         [--blk N=V]... [--cmd N=V]... [--vdm N=V]... [--pbe N=V]... [--sideband V]
 *         [--temps N]
 *         [--pixels] [--dump-render DIR] [--kpoke SPEC]...
 *         [--obj2 FIRST [--obj2-blk N=V]... [--obj2-pixel FILE]] FILE...
 *                                 each FILE as the program SLOT (pixev, eot, vtxpds,
 *                                 vtxuse, pixel, pixtask, pixpds, state, bgpds,
 *                                 bgpixel (the background object's primary PDS and
 *                                 pixel shader); a PDS one with
 *                                 N data dwords) of the
 *                                 first triangle's render, W x H (default 64 x 64),
 *                                 on a render context for up to --max-width x
 *                                 --max-height (default W x H); each --slot FILE
 *                                 replaces another slot's program in every render;
 *                                 --vertices N (3 to 1500, whole triangles): copies of
 *                                 the triangle after it, for the vertex programs;
 *                                 --vtx-coords N (1 to 11): N more output dwords per
 *                                 vertex, coordinate sets of four and the rest
 *                                 (OUTSEL, coordsize);
 *                                 --copy-depth: copy c at clip z = c / 16; --isp2 V:
 *                                 ISP word 2 (stencil) V in the state block, in place
 *                                 of the wrap word; --blk-add BIT=V[,V]: presence
 *                                 bit BIT (2-5, or 7 with two words) and its words
 *                                 added to the state block, which grows; --blk N=V:
 *                                 the state block's word N is V; --cmd N=V: the
 *                                 render command's word N is V; --vdm N=V: the
 *                                 VDM stream's word N is V (after --vtx-coords); N^=V
 *                                 flips the bits of V in the word instead (--blk, --cmd
 *                                 and --vdm alike); with --obj2 the stream is the
 *                                 two-object one (words 0-18, word 9 the second state
 *                                 block's), changed after the second object is built;
 *                                 --pbe N=V (N 0-3): the end-of-tile task's PBE word N,
 *                                 the default's or the eot slot's (word 4: --sideband);
 *                                 --dump-render DIR: after the render, the kernel's
 *                                 debugfs render_param and render_tadata copied to
 *                                 DIR/NAME.param.bin and DIR/NAME.tadata.bin;
 *                                 --kpoke SPEC: written to the kernel's debugfs kpoke
 *                                 before each case's render (the job's kernel words).
 *                                 --sideband V (with an eot slot): the end-of-tile
 *                                 emitpix2's sideband, 0x200 by default.
 *                                 --obj2 FIRST (with --vertices): the copies from
 *                                 vertex FIRST on as a second object, its state block
 *                                 the first's with --obj2-blk N=V words set and its
 *                                 pixel shader --obj2-pixel FILE (or the default fill)
 *                                 and primary pixel PDS program --obj2-pixpds FILE:N (N
 *                                 data dwords; or the default's).
 *                                 Patched as the defaults (sgxfive_tri_probe.h), with
 *                                 the scratch buffer; prints the target's pixels as o0
 *                                 and every scratch dword changed
 *
 * JOB OPTIONS (fill, copy, tri), for sweeps (one job run many times with one
 * word changed each time):
 *   --poke SPACE:INDEX=VALUE, --poke SPACE:INDEX^=VALUE (repeatable)
 *                                 set or flip one word of the built job right before
 *                                 it is submitted (include/sgxfive_poke.h: cmd, xfer,
 *                                 vdm, eos, blk, pds:SLOT, tex, bg)
 *   --pixels                      every pixel of the target, a row a line
 *   --regs LO-HI                  the SGX registers LO to HI after the job, read-only
 *                                 through /dev/mem (hardware only)
 *   --ramp CH=START [--ramp-base V]
 *                                 copy: one channel (a, r, g or b) of the source counts
 *                                 from START, one a pixel (modulo 256), the others V's
 *                                 (default 0)
 *   --print-addrs                 copy: the source's and destination's addresses
 *   --page-before                 copy: the source's buffer has a page before the source,
 *                                 dword i holding 0xB0000000 | i
 *   --every-value                 copy: a source with every value of every channel in
 *                                 each run of 256 pixels, a permutation per channel
 * They print the job's result, the target's hash, the pixels that differ from the
 * CPU reference (and the first) and the dwords written outside the target.
 *
 * fill, copy and isolation take their GPU programs from the assembled source
 * (our own code, default) or the fake test double (--programs=fake, mock only).
 *
 * A job that faults or hangs is recovered and fails: the commands report its
 * error as the wait returns it ("job faulted, context lost (...)"). A render
 * whose scene overflows the parameter buffer fails with -ENOSPC and keeps its
 * context ("scene overflowed the parameter buffer, context kept (...)"); on
 * the hardware debugfs sgx/render_pb_pages shrinks the PB of new render
 * contexts, in the mock --mock-pb-pages=N (0x23 to 0x422) does.
 *
 * Exit status: 0 all checks passed, 1 a check or call failed, 2 usage, 3 (probe and probe
 * --tri only) the run completed and at least one job failed: its output says which. stdout
 * is line-buffered, so a message on stderr lands after the lines printed before it.
 */
#define EXIT_JOB_FAILED	3

#include <errno.h>
#include <stdarg.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#include "sgxfive_mock.h"
#include "sgxfive_poke.h"
#include "sgxfive_render.h"
#include "sgxfive_tri_probe.h"
#include "sgxfive_xfer.h"

#define SENTINEL	0xdeadbeefu
#define WAIT_NS		(5LL * 1000000000LL)
/* A fault is found by the driver's BIF poll (a fault and no progress over two 50 ms
 * polls), not the 500 ms job timeout. */
#define FAULT_NS	(300LL * 1000000LL)
#define LATE_NS		(200LL * 1000000LL)	/* --late: how long the host waits for ready */

static long long now_ns(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static const char *const heap_names[DRM_SGXFIVE_HEAP_COUNT] = {
	"GENERAL", "TEXTURE", "PDS_PIXEL", "PDS_VERTEX", "USSE_PIXEL", "USSE_VERTEX",
	"KERNEL_CODE", "KERNEL_DATA", "PARAMETERS", "TA_DATA",
};

#define KPR_MAX	16

/* A buffer's fill: one value, the dword's index, or 0.25f / 0.75f by bit K of the index. */
struct fill {
	enum { FILL_VALUE, FILL_INDEX, FILL_BIT } mode;
	uint32_t val;			/* the value, or the bit K */
	bool given;
};

static uint32_t fill_at(const struct fill *f, uint64_t i)
{
	if (f->mode == FILL_INDEX)
		return (uint32_t)i;
	if (f->mode == FILL_BIT)
		return i >> f->val & 1 ? 0x3f400000 : 0x3e800000;
	return f->val;
}

static void fill_print(const struct fill *f)
{
	if (f->mode == FILL_INDEX)
		printf("fill index");
	else if (f->mode == FILL_BIT)
		printf("fill bit %u", f->val);
	else
		printf("fill 0x%08x", f->val);
}

struct opts {
	uint32_t width, height, x, y, stride, colour;
	uint32_t sx, sy, src_stride, dst_stride;
	uint32_t n;
	uint32_t max_width, max_height;	/* tri: the render context's; 0: the target's */
	bool fault;			/* tri: unmap the scene's stream page first */
	uint32_t scratch;		/* tri: pages of a scratch buffer for kernel pokes */
	uint32_t scratch_fill;		/* tri: the scratch buffer's dwords before a render */
	uint32_t scratch_at;		/* tri: where the scratch buffer is mapped (0: allocated) */
	uint32_t *scratch_data;		/* tri: --scratch-file's dwords, the buffer's first ones */
	uint32_t scratch_words;
	/*
	 * tri: kernel pokes written to debugfs kpoke just before render n (--kpoke-render), or
	 * register writes to debugfs kregnow (--kreg-render, reg); dummy: pokes before job n
	 * (--kpoke-job, job)
	 */
	struct { uint32_t n; const char *spec; bool second, reg, job; } kpr[KPR_MAX];
	unsigned int nkpr;
	uint32_t geometry;		/* tri: renders submitted geometry only (bit n - 1) */
	const char *dump_dir;		/* tri: the scene's memory there after the renders */
	const char *words_dir;		/* tri: the context's words there around each render */
	uint32_t wait_ms;		/* tri: each render's wait; 0: WAIT_NS */
	bool keep_going;		/* tri: go on after a render that does not check */
	bool keep_overflow;		/* tri: an overflowed render is counted and the run goes on */
	bool dump_each;			/* tri: --dump-render after every render, not only the last */
	/* tri --depth: a depth buffer the ZLS pokes point at (all the depth_* below) */
	bool depth;
	bool depth_given;		/* a --depth-* option was given */
	uint32_t depth_base, depth_ctl, depth_ctl_next;
	/*
	 * the fills (a value, "index" or "bit:K") of the depth buffer and of the extra buffers:
	 * --depth-store (the store base on a buffer of its own), --stencil (the stencil flag and
	 * bases on a stencil buffer) and --stencil-store
	 */
	struct fill depth_fill, depth_store_fill, stencil_fill, stencil_store_fill;
	bool depth_store, stencil, stencil_store;
	bool zgiven;			/* a --depth-store, --stencil... option was given */
	bool tri_full;			/* tri --tri-full: the triangle covers the target */
	bool tri_v_given;		/* tri --tri-v: the vertices, in 1/2^tri_unit pixel (default 1/256) */
	int32_t tri_v[3][2];
	uint32_t tri_unit;		/* tri --tri-unit: 0 (8), or 4 to 20 */
	bool tri_z_given;		/* tri --tri-z A,B,C: the screen depth at each vertex */
	float tri_z[3];
	uint32_t depth_pages;		/* UINT32_MAX: the target's and sixteen over */
	const char *depth_dump;		/* --depth-dump DIR: the buffer after each render */
	bool ctx2;			/* tri: a second render context in the VM, rendering too */
	bool close_first;		/* tri --ctx2: close the first context before the second */
	bool close_early;		/* tri --ctx2: ... in the last iteration, between the renders */
	bool words_between;		/* tri --ctx2 --words: a snapshot before each second render */
	bool close_trace;		/* tri --ctx2: the kernel's cleanup trace after each close */
	bool wait_second;		/* tri --overlap: wait for the second job before the first */
	bool share_pb;			/* tri: ... on the first's parameter buffer (kernel debugfs) */
	bool overlap;			/* tri: ... its job submitted before the first's is waited for */
	/* tri: render n's triangle moved by dx, dy pixels (--move) */
	struct { uint32_t n; int32_t dx, dy; } moves[KPR_MAX];
	unsigned int nmoves;
	bool every_value;		/* copy: the every-value source pattern */
	bool ramp;			/* copy: --ramp CH=START, one channel counting */
	uint32_t ramp_shift, ramp_start;	/* ... the channel's low bit, its first value */
	uint32_t ramp_base;		/* ... the other channels' values (--ramp-base) */
	bool print_addrs;		/* copy: print where the buffers are (--print-addrs) */
	bool page_before;		/* copy: a counting page before the source */
	/* job options (fill, copy, tri) */
	struct sgxfive_poke pokes[SGXFIVE_POKE_MAX];
	const char *poke_args[SGXFIVE_POKE_MAX];
	unsigned int npokes;
	bool pixels;			/* print every pixel of the target */
	bool pixels_rle;		/* tri: ... as runs of equal pixels, a row a line */
	bool regs;			/* print the registers regs_lo..regs_hi after the job */
	uint32_t regs_lo, regs_hi;
};

struct tool {
	struct sgxfive_mock *mock;
	struct sgxfive_dev *dev;
	struct sgxfive_prog_source *progs;
};

static int usage(void)
{
	fprintf(stderr,
		"usage: sgxfive-test [--mock[=rev1|harness|none]] [--mock-pb-pages=N]\n"
		"                    [--device PATH] [--programs=asm|fake] <command>\n"
		"       commands: query, dummy [-n N --kpoke-job N:SPEC --wait-ms MS], isolation,\n"
		"                 regaccess,\n"
		"                 fill [--width W --height H --x X --y Y --stride S --colour C],\n"
		"                 copy [--width W --height H --sx X --sy Y --src-stride S\n"
		"                       --dx X --dy Y --dst-stride S --every-value | --ramp CH=START\n"
		"                       [--ramp-base V] --print-addrs --page-before],\n"
		"                 tri [--width W --height H -n N --max-width W --max-height H\n"
		"                      --fault --scratch N --scratch-fill V --scratch-at ADDR\n"
		"                      --scratch-file FILE\n"
		"                      --kpoke-render N:SPEC --move N:DX,DY --geometry N\n"
		"                      --keep-going --keep-overflow --dump-render DIR [--dump-each]\n"
		"                      --words DIR\n"
		"                      [--tri-full] [--tri-z A,B,C]\n"
		"                      [--depth [--depth-ctl V] [--depth-ctl-next V] [--depth-fill F]\n"
		"                       [--depth-base V] [--depth-pages N] [--depth-dump DIR]\n"
		"                       [--depth-store [--depth-store-fill F]] [--stencil\n"
		"                       [--stencil-fill F] [--stencil-store [--stencil-store-fill F]]]]\n"
		"                      --wait-ms MS --ctx2 [--share-pb] [--overlap] [--close-first]\n"
		"                      [--close-first-early] [--words-between]\n"
		"                      [--kreg-render N:OFFSET=VALUE]\n"
		"                      [--kreg-render2 N:OFFSET=VALUE]\n"
		"                      [--close-trace] [--wait-second]\n"
		"                      [--kpoke-render2 N:SPEC]],\n"
		"                 fill, copy and tri also take [--poke SPACE:INDEX=VALUE]...\n"
		"                      [--poke SPACE:INDEX^=VALUE]... [--pixels] [--regs LO-HI],\n"
		"                 contexts [--width W --height H -n N],\n"
		"                 probe [--stamp] [--temps N] [--coords] [--pixels] [--pds N --use USE]\n"
		"                       [--place OFFSET=FILE --place-form cbase|exe18]\n"
		"                       [--scratch-heap texture] [--scratch-pages N]\n"
		"                       [--poke xfer:N=V|bg:N=V]... [--low ADDR] [--late R:K=V] FILE...,\n"
		"                 probe --tri SLOT[:N] [--slot SLOT=FILE[:N]]... [--width W\n"
		"                       --height H --max-width W --max-height H] [--vertices N]\n"
		"                       [--copy-depth] [--tri-full] [--vtx-coords N] [--isp2 V]\n"
		"                       [--blk-add BIT=V[,V]]... [--blk N=V]...\n"
		"                       [--cmd N=V]... [--vdm N=V]... [--pbe N=V]... [--sideband V]\n"
		"                       (--blk, --cmd and --vdm also take N^=V)\n"
		"                       [--dump-render DIR] [--kpoke SPEC]...\n"
		"                       [--obj2 FIRST [--obj2-blk N=V]... [--obj2-pixel FILE]\n"
		"                        [--obj2-pixpds FILE:N]]\n"
		"                       [--slot SLOT=FILE[:N]]... (SLOT: pixev eot vtxpds vtxuse pixel\n"
		"                        pixtask pixpds state bgpds bgpixel)\n"
		"                       [--temps N] [--pixels] FILE...\n");
	return 2;
}

static int fail(const char *what, int err)
{
	fprintf(stderr, "sgxfive-test: %s: %s\n", what, strerror(-err));
	return 1;
}

/*
 * What a wait's error says about the job (sgxfive_syncobj_wait): a job that
 * faulted or hung was recovered and failed, and its context is lost; a render
 * whose scene overflowed the parameter buffer failed, and its context is
 * kept. Other errors are the wait's own, as strerror.
 */
static const char *job_error(int err, char *buf, size_t len)
{
	const char *what = err == -EIO ? "job faulted" : err == -ETIMEDOUT ? "job hung" :
			   err == -ECANCELED ? "job cancelled" : NULL;

	if (err == -ENOSPC)
		snprintf(buf, len, "scene overflowed the parameter buffer, context kept (%s)",
			 strerror(-err));
	else if (what)
		snprintf(buf, len, "%s, context lost (%s)", what, strerror(-err));
	else
		snprintf(buf, len, "%s", strerror(-err));
	return buf;
}

static int fail_job(const char *what, int err)
{
	char buf[96];

	fprintf(stderr, "sgxfive-test: %s: %s\n", what, job_error(err, buf, sizeof(buf)));
	return 1;
}

/* ---- Job results (fill, copy, tri) ------------------------------------------------- */

/*
 * The SGX register bank, physical (the laptop's: BAR 0 + 0x80000), and the
 * part of it --regs reads; SGXFIVE_REGS_BASE overrides the base.
 */
#define REGS_BASE	0x80080000ull
#define REGS_SIZE	0x4000u

/* The job: ok, rejected (the submission's error) or failed (the wait's). */
static void print_job(int submit_err, int wait_err)
{
	char buf[96];

	if (submit_err)
		printf("job: rejected (%s)\n", strerror(-submit_err));
	else if (wait_err)
		printf("job: failed: %s\n", job_error(wait_err, buf, sizeof(buf)));
	else
		printf("job: ok\n");
}

/* A target's pixels (row y at px + y * stride dwords) and their CPU reference. */
struct target {
	uint32_t width, height, stride;
	const uint32_t *px;
	/* Whether v is right at (x, y); *want the expected value. */
	bool (*ok)(const void *ctx, uint32_t x, uint32_t y, uint32_t v, uint32_t *want);
	const void *ctx;
};

/*
 * The target's hash (sgxfive_hash_dwords of its pixels, row after row), the
 * pixels that differ from the reference and the first of them, the dwords
 * written outside it, and with --pixels every pixel.
 */
static void print_target(const struct target *g, uint32_t outside, bool pixels, bool rle)
{
	const uint64_t n = (uint64_t)g->width * g->height;
	uint32_t *buf = calloc(n + 1, 4), bad = 0, fx = 0, fy = 0, fv = 0, fw = 0;

	if (!buf) {
		printf("target: %ux%u (out of memory)\n", g->width, g->height);
		return;
	}
	for (uint32_t y = 0; y < g->height; y++)
		for (uint32_t x = 0; x < g->width; x++) {
			const uint32_t v = g->px[(uint64_t)y * g->stride + x];
			uint32_t want;

			buf[(uint64_t)y * g->width + x] = v;
			if (!g->ok(g->ctx, x, y, v, &want) && !bad++) {
				fx = x;
				fy = y;
				fv = v;
				fw = want;
			}
		}
	printf("target: %ux%u hash 0x%016llx\n", g->width, g->height,
	       (unsigned long long)sgxfive_hash_dwords(buf, n));
	if (bad)
		printf("diff: %u of %llu pixels, first (%u, %u) 0x%08x expected 0x%08x\n", bad,
		       (unsigned long long)n, fx, fy, fv, fw);
	else
		printf("diff: 0 of %llu pixels\n", (unsigned long long)n);
	printf("outside: %u dwords\n", outside);
	for (uint32_t y = 0; pixels && y < g->height; y++) {
		printf("row %u:", y);
		for (uint32_t x = 0; x < g->width; x++)
			printf(" 0x%08x", buf[(uint64_t)y * g->width + x]);
		putchar('\n');
	}
	/* --pixels-rle: a row a line as runs of equal pixels, "rle Y: 0xVALUExN ..." */
	for (uint32_t y = 0; rle && y < g->height; y++) {
		const uint32_t *row = buf + (uint64_t)y * g->width;
		uint32_t x = 0;

		printf("rle %u:", y);
		while (x < g->width) {
			uint32_t e = x + 1;

			while (e < g->width && row[e] == row[x])
				e++;
			printf(" 0x%08xx%u", row[x], e - x);
			x = e;
		}
		putchar('\n');
	}
	free(buf);
}

/* --regs: the registers LO..HI after the job, read-only through /dev/mem. */
static void print_regs(const struct tool *t, const struct opts *o)
{
	const char *env = getenv("SGXFIVE_REGS_BASE");
	const unsigned long long base = env ? strtoull(env, NULL, 0) : REGS_BASE;
	const size_t len = ((size_t)o->regs_hi + 4 + SGXFIVE_PAGE_SIZE - 1) &
			   ~(size_t)(SGXFIVE_PAGE_SIZE - 1);
	volatile const uint32_t *m;
	int fd;

	if (!o->regs)
		return;
	if (t->mock) {
		printf("regs: not available on the mock\n");
		return;
	}
	fd = open("/dev/mem", O_RDONLY | O_SYNC);
	if (fd < 0) {
		printf("regs: /dev/mem: %s\n", strerror(errno));
		return;
	}
	m = mmap(NULL, len, PROT_READ, MAP_SHARED, fd, (off_t)base);
	close(fd);
	if (m == MAP_FAILED) {
		printf("regs: mmap 0x%llx: %s\n", base, strerror(errno));
		return;
	}
	printf("regs: 0x%04x-0x%04x at 0x%llx\n", o->regs_lo, o->regs_hi, base);
	for (uint32_t off = o->regs_lo; off <= o->regs_hi; off += 4)
		printf("reg 0x%04x 0x%08x\n", off, m[off / 4]);
	munmap((void *)m, len);
}

/* ---- query -------------------------------------------------------------------------- */

static int cmd_query(struct tool *t)
{
	const struct sgxfive_info *i = sgxfive_dev_info(t->dev);

	printf("device          %s\n", sgxfive_dev_path(t->dev));
	printf("core_id         0x%08x\n", i->gpu.core_id);
	printf("core_revision   0x%08x\n", i->gpu.core_revision);
	if (i->gpu.flags & DRM_SGXFIVE_GPU_INFO_SW_VALID)
		printf("core_sw         %u rev 0x%x\n", i->gpu.core_id_sw,
		       i->gpu.core_revision_sw);
	printf("host_bridge_rev %u\n", i->gpu.host_bridge_rev);
	printf("quirks          0x%llx%s\n", (unsigned long long)i->gpu.quirks,
	       i->gpu.quirks & DRM_SGXFIVE_QUIRK_SAMPLE_CACHE ? " SAMPLE_CACHE" : "");
	printf("ddk             %u.%u.%u build %u options 0x%x\n", i->fw.ddk_version >> 16,
	       (i->fw.ddk_version >> 8) & 0xff, i->fw.ddk_version & 0xff, i->fw.ddk_build,
	       i->fw.build_options);
	printf("fw_format       %u\n", i->fw.fw_format);
	printf("fw_state        %u\n", i->fw.state);
	printf("job_types       0x%llx\n", (unsigned long long)i->job.job_types);
	printf("max_jobs        %u\n", i->job.max_jobs);
	printf("max_sync_ops    %u\n", i->job.max_sync_ops);
	printf("transfer_cmd    0x%x\n", i->job.transfer_cmd_size);
	printf("max_updates     %u\n", i->job.max_updates);
	printf("render_cmd      0x%x pb 0x%x pages max %ux%u\n", i->job.render_cmd_size,
	       i->job.render_pb_pages, i->job.render_max_width, i->job.render_max_height);
	printf("pixel_parts     %u\n", i->runtime.num_pixel_partitions);
	printf("tile            %ux%u\n", i->runtime.tile_width, i->runtime.tile_height);
	for (uint32_t h = 0; h < DRM_SGXFIVE_HEAP_COUNT && h < i->num_heaps; h++) {
		const struct drm_sgxfive_heap *hp = &i->heaps[h];
		char name[32];

		snprintf(name, sizeof(name), "heap %s", heap_names[h]);
		if (!hp->size) {
			printf("%-16s absent\n", name);
			continue;
		}
		printf("%-16s base 0x%08llx size 0x%08llx%s%s\n", name,
		       (unsigned long long)hp->base, (unsigned long long)hp->size,
		       hp->flags & DRM_SGXFIVE_HEAP_RESERVED ? " RESERVED" : "",
		       hp->flags & DRM_SGXFIVE_HEAP_FIXED_WINDOWS ? " FIXED_WINDOWS" : "");
	}
	return 0;
}

/* ---- Shared set-up ------------------------------------------------------------------ */

struct side {
	struct sgxfive_vm *vm;
	uint32_t ctx;
	struct sgxfive_xfer *x;
};

static int side_init(struct tool *t, struct side *s)
{
	int ret;

	memset(s, 0, sizeof(*s));
	ret = sgxfive_vm_create(t->dev, &s->vm);
	if (!ret)
		ret = sgxfive_ctx_create(s->vm, &s->ctx);
	if (!ret && t->progs)
		ret = sgxfive_xfer_create(s->vm, s->ctx, t->progs, &s->x);
	return ret;
}

static void side_fini(struct tool *t, struct side *s)
{
	sgxfive_xfer_destroy(s->x);
	if (s->ctx)
		sgxfive_ctx_destroy(t->dev, s->ctx);
	sgxfive_vm_destroy(s->vm);
}

/* A CPU-visible BO of `pages` pages at addr (0: allocate in GENERAL), set to SENTINEL. */
static int surface(struct tool *t, struct sgxfive_vm *vm, uint32_t pages, uint32_t flags,
		   uint64_t *addr, struct sgxfive_bo **bo, uint32_t **map)
{
	const uint64_t size = pages * (uint64_t)SGXFIVE_PAGE_SIZE;
	void *p = NULL;
	int ret;

	ret = sgxfive_bo_create(t->dev, size, DRM_SGXFIVE_BO_ALLOW_CPU_ACCESS, bo);
	if (!ret)
		ret = sgxfive_bo_mmap(*bo, &p);
	if (!ret && !*addr)
		ret = sgxfive_vm_alloc(vm, DRM_SGXFIVE_HEAP_GENERAL, size, SGXFIVE_PAGE_SIZE, addr);
	if (!ret)
		ret = sgxfive_vm_map(vm, *addr, *bo, 0, size, flags);
	if (ret)
		return ret;
	*map = p;
	for (uint64_t i = 0; i < size / 4; i++)
		(*map)[i] = SENTINEL;
	return 0;
}

static uint32_t pages_for(uint32_t stride, uint32_t rows)
{
	const uint64_t bytes = (uint64_t)stride * rows;

	/* The surface plus one guard page. */
	return (uint32_t)((bytes + SGXFIVE_PAGE_SIZE - 1) / SGXFIVE_PAGE_SIZE) + 1;
}

/* ---- dummy -------------------------------------------------------------------------- */

static int kpoke_write(const char *spec);	/* below, with the tri command's */
static int debugfs_set(const char *name, const char *value);

/* A kernel poke (debugfs kpoke) or, with reg, a register write (debugfs kregnow). */
static int kpr_write(bool reg, const char *spec)
{
	char line[128];
	int n;

	if (!reg)
		return kpoke_write(spec);
	n = snprintf(line, sizeof(line), "%s\n", spec);
	if (n < 0 || (size_t)n >= sizeof(line))
		return -EINVAL;
	return debugfs_set("kregnow", line);
}

static int cmd_dummy(struct tool *t, const struct opts *o)
{
	const long long wait_ns = o->wait_ms ? o->wait_ms * 1000000LL : WAIT_NS;
	struct side s;
	uint32_t sync = 0;
	int wait_err = 0;
	int ret = side_init(t, &s);

	if (!ret)
		ret = sgxfive_syncobj_create(t->dev, false, &sync);
	for (uint32_t i = 0; !ret && i < o->n; i++) {
		for (unsigned int k = 0; !ret && k < o->nkpr; k++) {
			if (o->kpr[k].n != i + 1)
				continue;
			ret = kpoke_write(o->kpr[k].spec);
			if (!ret)
				printf("dummy: kpoke before job %u: %s\n", i + 1, o->kpr[k].spec);
		}
		if (!ret)
			ret = sgxfive_submit_transfer(t->dev, s.ctx,
						      DRM_SGXFIVE_SUBMIT_JOB_TRANSFER_DUMMY, NULL,
						      i ? sync : 0, sync);
	}
	if (!ret)
		wait_err = sgxfive_syncobj_wait(t->dev, sync, 0, wait_ns);
	if (sync)
		sgxfive_syncobj_destroy(t->dev, sync);
	side_fini(t, &s);
	if (wait_err && !ret)
		return fail_job("dummy", wait_err);
	if (ret)
		return fail("dummy", ret);
	printf("dummy: %u jobs ok\n", o->n);
	return 0;
}

/* ---- fill and copy ------------------------------------------------------------------ */

static bool in_rect(const struct sgxfive_rect *r, uint32_t x, uint32_t y)
{
	return x >= r->x0 && x < r->x1 && y >= r->y0 && y < r->y1;
}

/* The dwords of a destination buffer of `words` dwords outside rect that are not SENTINEL. */
static uint32_t outside_rect(const uint32_t *p, uint32_t words, uint32_t stride_words,
			     const struct sgxfive_rect *r)
{
	uint32_t n = 0;

	for (uint32_t i = 0; i < words; i++)
		n += !in_rect(r, i % stride_words, i / stride_words) && p[i] != SENTINEL;
	return n;
}

static bool fill_ok(const void *ctx, uint32_t x, uint32_t y, uint32_t v, uint32_t *want)
{
	*want = *(const uint32_t *)ctx;
	return v == *want;
}

/*
 * Wait for a fill or copy unless its submission failed; print the job line and, for a job
 * that was submitted, its time (from t0, taken before the submission, to the wait's return);
 * the error.
 */
static int xfer_job(struct side *s, int submit_err, long long t0)
{
	int wait_err = 0;

	if (!submit_err)
		wait_err = sgxfive_xfer_wait(s->x, WAIT_NS);
	print_job(submit_err, wait_err);
	if (!submit_err)
		printf("job time: %lld us\n", (now_ns() - t0) / 1000);
	return submit_err ? submit_err : wait_err;
}

static bool probe_stamp;	/* probe --stamp: the job's window in CLOCK_REALTIME ns too */

/*
 * A probe's wait, its time (from t0) printed when the job completed; with --stamp the window
 * (from t0 to the wait's return) in wall-clock ns, to place a write from another process in it.
 */
static int probe_wait(struct sgxfive_xfer *x, const char *name, long long t0)
{
	const int ret = sgxfive_xfer_wait(x, WAIT_NS);

	if (!ret) {
		const long long dt = now_ns() - t0;
		struct timespec ts;

		printf("probe %s: job time: %lld us\n", name, dt / 1000);
		if (probe_stamp) {
			clock_gettime(CLOCK_REALTIME, &ts);
			const long long end = ts.tv_sec * 1000000000LL + ts.tv_nsec;

			printf("probe %s: job window %lld %lld ns\n", name, end - dt, end);
		}
	}
	return ret;
}

static int cmd_fill(struct tool *t, const struct opts *o)
{
	const struct sgxfive_rect r = { o->x, o->y, o->x + o->width, o->y + o->height };
	const uint32_t rows = o->y + o->height, pages = pages_for(o->stride, rows);
	struct sgxfive_bo *bo = NULL;
	struct sgxfive_surface dst;
	uint32_t *p = NULL, bad = 0;
	uint64_t addr = 0;
	long long t0;
	struct side s;
	int ret = side_init(t, &s);

	if (!ret)
		ret = surface(t, s.vm, pages, 0, &addr, &bo, &p);
	dst = (struct sgxfive_surface){ addr, o->stride / 4, rows, o->stride };
	if (!ret) {
		sgxfive_xfer_set_hook(s.x, sgxfive_poke_hook,
				      &(struct sgxfive_poke_set){ o->pokes, o->npokes });
		for (unsigned int k = 0; !ret && k < o->nkpr; k++) {
			if (!o->kpr[k].job)
				continue;
			ret = kpoke_write(o->kpr[k].spec);
			if (!ret)
				printf("fill: kpoke before job 1: %s\n", o->kpr[k].spec);
		}
		t0 = now_ns();
		if (!ret)
			ret = xfer_job(&s, sgxfive_xfer_fill(s.x, &dst, &r, o->colour, 0), t0);
		print_regs(t, o);
		print_target(&(struct target){ o->width, o->height, o->stride / 4,
					       p + (uint64_t)o->y * (o->stride / 4) + o->x,
					       fill_ok, &o->colour },
			     outside_rect(p, pages * 1024, o->stride / 4, &r), o->pixels, false);
	}
	for (uint32_t i = 0; !ret && i < pages * 1024; i++) {
		uint32_t x = i % (o->stride / 4), y = i / (o->stride / 4);
		bool in = in_rect(&r, x, y);

		if (p[i] != (in ? o->colour : SENTINEL) && !bad++)
			printf("fill: dword %u (%u, %u) = 0x%08x\n", i, x, y, p[i]);
	}
	sgxfive_bo_destroy(bo);
	side_fini(t, &s);
	if (ret)
		return fail("fill", ret);
	if (bad) {
		printf("fill: FAIL, %u wrong dwords\n", bad);
		return 1;
	}
	printf("fill: ok, %ux%u at (%u, %u), stride %u, colour 0x%08x\n", o->width, o->height,
	       o->x, o->y, o->stride, o->colour);
	return 0;
}

/*
 * The copy's source texel (x, y) of a source sw pixels wide. --every-value: n = y * sw + x
 * runs through every byte value in each channel, each through its own permutation (odd
 * multipliers), so any per-channel function of the value shows in one job. --ramp CH=START:
 * one channel is START + n (modulo 256) and the others --ramp-base's.
 */
static uint32_t pattern(const struct opts *o, uint32_t x, uint32_t y)
{
	const uint32_t n = (y * (o->src_stride / 4) + x) & 0xff;

	if (o->ramp)
		return (o->ramp_base & ~(0xffu << o->ramp_shift)) |
		       ((o->ramp_start + y * (o->src_stride / 4) + x) & 0xff) << o->ramp_shift;
	if (o->every_value)
		return n << 24 | ((n * 167 + 13) & 0xff) << 16 | ((n * 29 + 101) & 0xff) << 8 |
		       ((n * 93 + 57) & 0xff);
	return 0xa5000000 | (y & 0xff) << 16 | (x & 0xff) << 8 | ((x ^ y) & 0xff);
}

/* The copy's reference: the source pattern at (sx, sy) + (x, y). */
static bool copy_ok(const void *ctx, uint32_t x, uint32_t y, uint32_t v, uint32_t *want)
{
	const struct opts *o = ctx;

	*want = pattern(o, o->sx + x, o->sy + y);
	return v == *want;
}

#define PAGE_BEFORE_FILL	0xB0000000u	/* --page-before: dword i of the page is this | i */

static int cmd_copy(struct tool *t, const struct opts *o)
{
	const struct sgxfive_rect r = { o->x, o->y, o->x + o->width, o->y + o->height };
	const uint32_t srows = o->sy + o->height, drows = o->y + o->height;
	const uint32_t spages = pages_for(o->src_stride, srows);
	const uint32_t dpages = pages_for(o->dst_stride, drows);
	const uint32_t before = o->page_before;	/* pages of the source's buffer before the source */
	struct sgxfive_bo *sbo = NULL, *dbo = NULL;
	struct sgxfive_surface src, dst;
	uint32_t *s = NULL, *d = NULL, bad = 0;
	const uint32_t sw = o->src_stride / 4, dw = o->dst_stride / 4;
	uint64_t saddr = 0, daddr = 0;
	long long t0;
	struct side sd;
	int ret = side_init(t, &sd);

	if (!ret)
		ret = surface(t, sd.vm, before + spages, DRM_SGXFIVE_VM_MAP_READ_ONLY, &saddr, &sbo,
			      &s);
	if (!ret)
		ret = surface(t, sd.vm, dpages, 0, &daddr, &dbo, &d);
	/* the page before the source counts: dword i holds PAGE_BEFORE_FILL | i */
	for (uint32_t i = 0; !ret && i < before * 1024; i++)
		s[i] = PAGE_BEFORE_FILL | i;
	if (!ret) {
		s += before * 1024;
		saddr += before * SGXFIVE_PAGE_SIZE;
	}
	for (uint32_t i = 0; !ret && i < spages * 1024; i++)
		s[i] = pattern(o, i % sw, i / sw);
	if (!ret && o->print_addrs)
		printf("copy: source at 0x%08llx, destination at 0x%08llx%s\n",
		       (unsigned long long)saddr, (unsigned long long)daddr,
		       before ? ", a counting page before the source" : "");
	src = (struct sgxfive_surface){ saddr, sw, srows, o->src_stride };
	dst = (struct sgxfive_surface){ daddr, dw, drows, o->dst_stride };
	if (!ret) {
		sgxfive_xfer_set_hook(sd.x, sgxfive_poke_hook,
				      &(struct sgxfive_poke_set){ o->pokes, o->npokes });
		t0 = now_ns();
		ret = xfer_job(&sd, sgxfive_xfer_copy(sd.x, &src, o->sx, o->sy, &dst, &r, 0), t0);
		print_regs(t, o);
		print_target(&(struct target){ o->width, o->height, dw,
					       d + (uint64_t)o->y * dw + o->x, copy_ok, o },
			     outside_rect(d, dpages * 1024, dw, &r), o->pixels, false);
	}
	for (uint32_t i = 0; !ret && i < dpages * 1024; i++) {
		uint32_t x = i % dw, y = i / dw;
		bool in = in_rect(&r, x, y);
		uint32_t want = in ? pattern(o, o->sx + x - r.x0, o->sy + y - r.y0) : SENTINEL;

		if (d[i] != want && !bad++)
			printf("copy: dword %u (%u, %u) = 0x%08x, expected 0x%08x\n", i, x, y,
			       d[i], want);
	}
	sgxfive_bo_destroy(sbo);
	sgxfive_bo_destroy(dbo);
	side_fini(t, &sd);
	if (ret)
		return fail("copy", ret);
	if (bad) {
		printf("copy: FAIL, %u wrong dwords\n", bad);
		return 1;
	}
	printf("copy: ok, %ux%u from (%u, %u) to (%u, %u)\n", o->width, o->height, o->sx,
	       o->sy, o->x, o->y);
	return 0;
}

/* ---- isolation ---------------------------------------------------------------------- */

static int check(int *failed, bool ok, const char *name)
{
	printf("%s %s\n", ok ? "PASS" : "FAIL", name);
	*failed += !ok;
	return ok;
}

static bool untouched(const uint32_t *p, uint32_t words)
{
	for (uint32_t i = 0; i < words; i++)
		if (p[i] != SENTINEL)
			return false;
	return true;
}

static bool filled(const uint32_t *p, uint32_t words, uint32_t colour)
{
	for (uint32_t i = 0; i < words; i++)
		if (p[i] != colour)
			return false;
	return true;
}

/*
 * The xfer_iso / alias_ro / xfer_ro checks: two VMs, a transfer context in
 * each. Order matters: the fault checks lose context A, then context B.
 */
static int cmd_isolation(struct tool *t)
{
	const struct sgxfive_info *info = sgxfive_dev_info(t->dev);
	const struct sgxfive_rect r = { 0, 0, 64, 32 };
	struct sgxfive_bo *ba = NULL, *bb = NULL, *bo = NULL, *bro = NULL, *bk = NULL;
	struct sgxfive_bo *bq = NULL, *bm = NULL;
	uint32_t *pa = NULL, *pb = NULL, *po = NULL, *pro = NULL, *pq = NULL, *pm = NULL;
	uint64_t shared = 0, only_b = 0, ro = 0, only_d = 0, mine = 0;
	struct sgxfive_surface dst = { 0, 64, 32, 256 };
	struct side A, B, C = { 0 }, D = { 0 };
	struct sgxfive_vm *banned_vm = NULL;
	uint32_t banned_ctx = 0;
	long long t0;
	int failed = 0, ret;

	ret = side_init(t, &A);
	if (!ret)
		ret = side_init(t, &B);
	if (ret)
		return fail("isolation set-up", ret);

	/* 1. The kernel heaps can never be mapped. */
	ret = sgxfive_bo_create(t->dev, SGXFIVE_PAGE_SIZE, 0, &bk);
	check(&failed, !ret && sgxfive_vm_map(A.vm,
		info->heaps[DRM_SGXFIVE_HEAP_KERNEL_CODE].base, bk, 0, SGXFIVE_PAGE_SIZE, 0) ==
		-EINVAL && sgxfive_vm_map(A.vm, info->heaps[DRM_SGXFIVE_HEAP_KERNEL_DATA].base,
		bk, 0, SGXFIVE_PAGE_SIZE, DRM_SGXFIVE_VM_MAP_READ_ONLY) == -EINVAL,
	      "kernel-heap-unmappable");

	/* 2. One address, two VMs, two BOs: a fill through A lands only in A's BO. */
	ret = surface(t, A.vm, 2, 0, &shared, &ba, &pa);
	if (!ret)
		ret = surface(t, B.vm, 2, 0, &shared, &bb, &pb);
	dst.addr = shared;
	if (!ret)
		ret = sgxfive_xfer_fill(A.x, &dst, &r, 0xff0000aa, 0);
	if (!ret)
		ret = sgxfive_xfer_wait(A.x, WAIT_NS);
	check(&failed, !ret && filled(pa, 2048, 0xff0000aa) && untouched(pb, 2048),
	      "same-address-separate-vms");

	/* 3. An address mapped only in B: A's fill faults and writes nothing. */
	if (!ret)
		ret = sgxfive_vm_alloc(B.vm, DRM_SGXFIVE_HEAP_GENERAL, 0x100000, 0x100000,
				       &only_b);
	if (!ret)
		ret = surface(t, B.vm, 2, 0, &only_b, &bo, &po);
	dst.addr = only_b;
	if (!ret)
		ret = sgxfive_xfer_fill(A.x, &dst, &r, 0xff0000bb, 0);
	t0 = now_ns();
	/* The job is recovered and fails: its fence carries the fault. */
	check(&failed, !ret && sgxfive_xfer_wait(A.x, WAIT_NS) == -EIO && untouched(po, 2048),
	      "other-vm-address-faults");
	t0 = now_ns() - t0;
	printf("fault recovered after %lld ms\n", t0 / 1000000);
	check(&failed, !ret && t0 < FAULT_NS, "fault-recovered-quickly");

	/* 4. The faulting context is lost. */
	check(&failed, sgxfive_submit_transfer(t->dev, A.ctx,
		DRM_SGXFIVE_SUBMIT_JOB_TRANSFER_DUMMY, NULL, 0, 0) == -ECANCELED,
	      "lost-context-cancelled");

	/* 5. Context B is unaffected. */
	ret = sgxfive_xfer_fill(B.x, &dst, &r, 0xff0000cc, 0);
	if (!ret)
		ret = sgxfive_xfer_wait(B.x, WAIT_NS);
	check(&failed, !ret && filled(po, 2048, 0xff0000cc), "other-context-survives");

	/*
	 * 6. A job queued right behind a faulting one, on another context, still
	 * runs: the recovery reset re-runs it.
	 */
	ret = side_init(t, &C);
	if (!ret)
		ret = side_init(t, &D);
	if (!ret)
		ret = surface(t, D.vm, 2, 0, &only_d, &bq, &pq);
	if (!ret)
		ret = surface(t, D.vm, 2, 0, &mine, &bm, &pm);
	if (!ret) {
		dst.addr = only_d;
		ret = sgxfive_xfer_fill(C.x, &dst, &r, 0xff0000ee, 0);
	}
	if (!ret) {
		dst.addr = mine;
		ret = sgxfive_xfer_fill(D.x, &dst, &r, 0xff0000ff, 0);
	}
	if (!ret)
		ret = sgxfive_xfer_wait(D.x, WAIT_NS);	/* re-run: no error */
	check(&failed, !ret && filled(pm, 2048, 0xff0000ff) && untouched(pq, 2048) &&
		       sgxfive_xfer_wait(C.x, WAIT_NS) == -EIO &&
		       sgxfive_submit_transfer(t->dev, C.ctx,
			       DRM_SGXFIVE_SUBMIT_JOB_TRANSFER_DUMMY, NULL, 0, 0) == -ECANCELED,
	      "queued-innocent-job-reruns");

	/* 7. A read-only mapping cannot be written by the GPU. */
	ret = surface(t, B.vm, 2, DRM_SGXFIVE_VM_MAP_READ_ONLY, &ro, &bro, &pro);
	dst.addr = ro;
	if (!ret)
		ret = sgxfive_xfer_fill(B.x, &dst, &r, 0xff0000dd, 0);
	check(&failed, !ret && sgxfive_xfer_wait(B.x, WAIT_NS) == -EIO && untouched(pro, 2048) &&
		       sgxfive_xfer_fill(B.x, &dst, &r, 0xff0000dd, 0) == -ECANCELED,
	      "read-only-faults");

	/*
	 * 8. That was the file's third fault within a minute: it may neither
	 * create contexts nor submit, even to a context that never faulted.
	 */
	ret = sgxfive_vm_create(t->dev, &banned_vm);
	check(&failed, !ret && sgxfive_ctx_create(banned_vm, &banned_ctx) == -ECANCELED &&
		       sgxfive_submit_transfer(t->dev, D.ctx,
			       DRM_SGXFIVE_SUBMIT_JOB_TRANSFER_DUMMY, NULL, 0, 0) == -ECANCELED,
	      "faulting-file-banned");
	if (banned_ctx)
		sgxfive_ctx_destroy(t->dev, banned_ctx);
	sgxfive_vm_destroy(banned_vm);

	sgxfive_bo_destroy(bk);
	sgxfive_bo_destroy(ba);
	sgxfive_bo_destroy(bb);
	sgxfive_bo_destroy(bo);
	sgxfive_bo_destroy(bro);
	sgxfive_bo_destroy(bq);
	sgxfive_bo_destroy(bm);
	side_fini(t, &A);
	side_fini(t, &B);
	side_fini(t, &C);
	side_fini(t, &D);
	return failed ? 1 : 0;
}

/* ---- regaccess: can a client's shader reach SGX registers? --------------------------- */

/*
 * The register-access probe: fill shaders that touch SGX registers with the
 * instructions the EDM uses for MMIO (doc/specs/hw_spec.md §10), run as an
 * ordinary client fill. The words are tools/usse-asm output for the source
 * beside them (tests/test_cli.py checks that).
 */
static const uint64_t probe_ldr[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0xFE21000020000007ull,	/* ldr r0, #7, drc0 (CORE_ID, 0x1c) */
	0xF920000000000000ull,	/* wdf drc0 */
	0x2885100120000000ull,	/* mov.skipinv.end o0, r0 */
};

static const uint64_t probe_str[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0xFCA16170001E0001ull,	/* mov.skipinv r0, #0x5AFE0001 */
	0xFE2900002001401Full,	/* str #671, r0 (USE_G0, 0xa7c) */
	0xFCA7F1810000AA55ull,	/* mov.skipinv.end o0, #0xFF00AA55 */
};

/* A page directory's physical address (BIF_DIR_LIST_BASE0, 0xc84). */
static const uint64_t probe_ldr_dirlist[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0xFE21000020018021ull,	/* ldr r0, #801, drc0 */
	0xF920000000000000ull,	/* wdf drc0 */
	0x2885100120000000ull,	/* mov.skipinv.end o0, r0 */
};

/* As probe_ldr, with r0 set first: does the ldr write r0 at all? */
static const uint64_t probe_ldr_marked[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0xFCA0408000111111ull,	/* mov.skipinv r0, #0x11111111 */
	0xFE21000020000007ull,	/* ldr r0, #7, drc0 (CORE_ID, 0x1c) */
	0xF920000000000000ull,	/* wdf drc0 */
	0x2885100120000000ull,	/* mov.skipinv.end o0, r0 */
};

/* A store, then a load of the same register: did the store land? */
static const uint64_t probe_str_ldr[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0xFCA16170001E0002ull,	/* mov.skipinv r0, #0x5AFE0002 */
	0xFE2900002001401Full,	/* str #671, r0 (USE_G0, 0xa7c) */
	0xFE2100002021401Full,	/* ldr r1, #671, drc0 */
	0xF920000000000000ull,	/* wdf drc0 */
	0x2885100120000080ull,	/* mov.skipinv.end o0, r1 */
};

/* A temporary the program never writes: what did earlier tasks leave? */
static const uint64_t probe_uninit[] = {
	0xFA44070000000000ull,	/* phas #0, #0, pixel, end, parallel */
	0x2885100120000000ull,	/* mov.skipinv.end o0, r0 */
};

/* A program source that is inner's, but with words for the fill shader. */
struct probe_source {
	struct sgxfive_prog_source base;
	struct sgxfive_prog_source *inner;
	const uint64_t *words;
	uint32_t n;
	bool cbase15;		/* the PDS primary kicks code base 15 instead */
	uint32_t id;		/* the program the words replace: USE_FILL or USE_COPY */
	uint32_t temps;		/* at least this many temporaries */
	uint64_t scratch;	/* 0, or where SCRATCH_IMM immediates point */
	const uint64_t *pds;	/* a PDS probe: the words replacing PDS_SEC (one per slot) */
	uint32_t pds_n;
	uint32_t pds_data;	/* its data segment, dwords */
	bool place_prim;	/* --place: the primary's DOUTU starts the placed program, */
	uint32_t placed_u0;	/* with these EXE and CBASE bits (21:0) */
	const uint64_t *place_words;	/* --place: its words, patched again when the programs are */
	uint32_t place_n;	/* built (the PDS references need the programs' addresses) */
	uint32_t *place_dst;	/* ... and where they are in the code heap page */
	uint64_t pds_sec;	/* where the PDS secondary was placed (set when built) */
	uint64_t pds_base;	/* and the pixel PDS heap's base */
	bool pds_ref;		/* a PDS reference immediate was patched */
};

/*
 * The secondary attributes a PDS probe may write with douta: sa0-sa15, which
 * the probe's USE program stores (douta writes secondary attributes).
 */
#define PROBE_PDS_ATTRS	16
#define DOUTU1_PIXEL	4	/* U1 of a pixel task: SDSOFT (fw_format.md §9.4) */

/*
 * A limm "mov d, #imm" whose immediate is SCRATCH_IMM | k (k < 0x10000) loads
 * the scratch buffer's address + k instead: probes of loads and stores address
 * a buffer the host fills and reads back.
 */
#define LIMM_MASK	0xFF30000000000000ull
#define LIMM_VAL	0xFC20000000000000ull
#define SCRATCH_IMM	0x5CAF0000u
/*
 * Two more immediates name the PDS secondary program of the fill (the --pds file or the
 * built-in one), for an emitpds in the probe's program or in a --place program: 0x5CB0nnnn is
 * its offset in the pixel PDS heap shifted right by four, plus nnnn; 0x5CB1nnnn is its GPU
 * address shifted right by four, plus nnnn (the low 32 bits). The probe prints the program's
 * address when it patched one.
 */
#define PDSREF_REL	0x5CB00000u
#define PDSREF_ABS	0x5CB10000u
static uint32_t scratch_pages = 16;		/* probe --scratch-pages: 64 KiB by default */
#define SCRATCH_PAGES	scratch_pages
#define SCRATCH_FILL(i)	(0xD0000000u | (i))	/* dword i of the scratch buffer, before */

/* A probe program's word with the immediates the host fills in patched (see SCRATCH_IMM). */
static uint64_t probe_patch(struct probe_source *p, const struct sgxfive_prog_env *env,
			    uint64_t w)
{
	const uint32_t imm = sgxfive_limm_get(w), k = imm & 0xffff;

	if ((w & LIMM_MASK) != LIMM_VAL)
		return w;
	if (p->scratch && (imm & ~0xffffu) == SCRATCH_IMM)
		return sgxfive_limm_set(w, (uint32_t)p->scratch + k);
	if ((imm & ~0xffffu) == PDSREF_REL || (imm & ~0xffffu) == PDSREF_ABS) {
		const uint64_t a = env->addr[SGXFIVE_PROG_PDS_SEC];
		const uint64_t b = env->heap_base[DRM_SGXFIVE_HEAP_PDS_PIXEL];

		p->pds_sec = a;
		p->pds_base = b;
		p->pds_ref = true;
		return sgxfive_limm_set(w, (uint32_t)((((imm & ~0xffffu) == PDSREF_REL ? a - b : a)
						       >> 4) + k));
	}
	return w;
}

static int probe_meta(struct sgxfive_prog_source *src, uint32_t id, struct sgxfive_prog_meta *m)
{
	struct probe_source *p = (struct probe_source *)src;
	int ret = p->inner->ops->meta(p->inner, id, m);

	if (!ret && p->pds && id == SGXFIVE_PROG_PDS_SEC) {
		m->size = p->pds_n * 4;
		m->data_size = p->pds_data * 4;
		m->attrs = PROBE_PDS_ATTRS;
		return 0;
	}
	if (!ret && id == p->id) {
		m->size = p->n * 8;
		if (m->temps < 4)
			m->temps = 4;		/* r0 */
		if (m->temps < p->temps)
			m->temps = p->temps;
	}
	return ret;
}

static int probe_build(struct sgxfive_prog_source *src, uint32_t id,
		       const struct sgxfive_prog_env *env, void *out)
{
	struct probe_source *p = (struct probe_source *)src;
	int ret;

	if (p->pds && id == SGXFIVE_PROG_PDS_SEC) {
		uint32_t *w = out;

		/* the probe's words, with its U0-U2 (data dwords 0-2) kicking the secondary task */
		for (uint32_t i = 0; i < p->pds_n; i++)
			w[i] = (uint32_t)p->pds[i];
		w[0] = env->doutu[SGXFIVE_PROG_USE_SEC];
		w[1] = DOUTU1_PIXEL;
		w[2] = 0;
		return 0;
	}
	if (id == p->id) {
		uint64_t *w = out;

		memcpy(out, p->words, p->n * 8);
		for (uint32_t i = 0; i < p->n; i++)
			w[i] = probe_patch(p, env, w[i]);
		return 0;
	}
	ret = p->inner->ops->build(p->inner, id, env, out);
	for (uint32_t i = 0; !ret && id == SGXFIVE_PROG_PDS_PRIM && i < p->place_n; i++) {
		const uint64_t w = probe_patch(p, env, p->place_words[i]);

		p->place_dst[2 * i] = (uint32_t)w;
		p->place_dst[2 * i + 1] = (uint32_t)(w >> 32);
	}
	if (!ret && id == SGXFIVE_PROG_PDS_PRIM && p->place_prim) {
		uint32_t u0;

		/* the placed program starts in place of the fill shader: EXE and CBASE (bits 21:0) */
		memcpy(&u0, out, 4);
		u0 = (u0 & 0xffc00000u) | p->placed_u0;
		memcpy(out, &u0, 4);
	}
	if (!ret && id == SGXFIVE_PROG_PDS_PRIM && p->cbase15) {
		uint32_t u0;

		/* Its DOUTU word U0 (the KICKONLY data, byte 0): EXE 0, CBASE 15. */
		memcpy(&u0, out, 4);
		u0 = (u0 & 0xff000000u) | 0xf;
		memcpy(out, &u0, 4);
	}
	return ret;
}

static void probe_destroy(struct sgxfive_prog_source *src)
{
}

static const struct sgxfive_prog_source_ops probe_ops = {
	.meta = probe_meta, .build = probe_build, .destroy = probe_destroy,
};

/* Fill 64x32 with the probe as the fill shader; report what reached memory. */
static int run_probe(struct tool *t, const char *name, const uint64_t *words, uint32_t n,
		     bool cbase15)
{
	struct probe_source src = {
		{ &probe_ops, name }, t->progs, words, n, cbase15, SGXFIVE_PROG_USE_FILL, 0, 0,
		NULL, 0, 0, false, 0, NULL, 0, NULL, 0, 0, false,
	};
	struct sgxfive_prog_source *saved = t->progs;
	const struct sgxfive_rect r = { 0, 0, 64, 32 };
	struct sgxfive_surface dst = { 0, 64, 32, 256 };
	struct sgxfive_bo *bo = NULL;
	uint32_t *p = NULL, same = 0;
	uint64_t addr = 0;
	struct side s;
	char why[96];
	int ret, job = 0;

	t->progs = &src.base;
	ret = side_init(t, &s);
	t->progs = saved;
	if (!ret)
		ret = surface(t, s.vm, 2, 0, &addr, &bo, &p);
	dst.addr = addr;
	if (!ret)
		ret = sgxfive_xfer_fill(s.x, &dst, &r, 0, 0);
	if (!ret)
		job = sgxfive_xfer_wait(s.x, WAIT_NS);
	if (p)
		for (uint32_t i = 0; i < 2048; i++)
			same += p[i] == p[0];
	if (ret) {
		printf("%s: failed: %s\n", name, strerror(-ret));
	} else if (job) {
		printf("%s: job failed: %s\n", name, job_error(job, why, sizeof(why)));
	} else {
		uint32_t val[8], cnt[8], nv = 0, other = 0;

		printf("%s: job completed, dword 0 = 0x%08x, %u of 2048 equal\n", name, p[0], same);
		for (uint32_t i = 0; i < 2048; i++) {
			uint32_t k = 0;

			while (k < nv && val[k] != p[i])
				k++;
			if (k < nv)
				cnt[k]++;
			else if (nv < 8)
				val[nv] = p[i], cnt[nv++] = 1;
			else
				other++;
		}
		for (uint32_t k = 0; k < nv; k++)
			printf("  0x%08x x%u\n", val[k], cnt[k]);
		if (other)
			printf("  (%u dwords with other values)\n", other);
		for (uint32_t y = 0; y < 4; y++)
			printf("  row %u: %08x %08x %08x %08x ... %08x\n", y, p[y * 64], p[y * 64 + 1],
			       p[y * 64 + 2], p[y * 64 + 3], p[y * 64 + 63]);
	}
	sgxfive_bo_destroy(bo);
	side_fini(t, &s);
	return 0;
}

static int cmd_regaccess(struct tool *t)
{
	run_probe(t, "uninit-temps", probe_uninit, 2, false);
	run_probe(t, "ldr-core-id", probe_ldr, 4, false);
	run_probe(t, "ldr-marked", probe_ldr_marked, 5, false);
	run_probe(t, "ldr-dir-list-base0", probe_ldr_dirlist, 4, false);
	run_probe(t, "str-use-g0", probe_str, 4, false);
	run_probe(t, "str-then-ldr-use-g0", probe_str_ldr, 6, false);
	run_probe(t, "kick-code-base-15", probe_ldr, 4, true);
	return 0;
}

/* ---- probe: our own programs as the fill shader --------------------------------------- */

#define PROBE_MAX_WORDS	256

struct probe_file {
	const char *name;	/* the file's base name without .bin */
	char label[64];
	uint64_t words[PROBE_MAX_WORDS];
	uint32_t n;
};

/*
 * Read a raw little-endian program (tools/usse-asm -o) into f: USSE words (width 8) or
 * PDS words (width 4, one per slot of f->words).
 */
static int probe_read(const char *path, struct probe_file *f, unsigned int width)
{
	const char *base = strrchr(path, '/');
	uint8_t buf[PROBE_MAX_WORDS * 8 + 1];
	size_t len, dot;
	FILE *fp = fopen(path, "rb");

	if (!fp) {
		fprintf(stderr, "sgxfive-test: %s: %s\n", path, strerror(errno));
		return -1;
	}
	len = fread(buf, 1, sizeof(buf), fp);
	fclose(fp);
	if (!len || len % width || len > PROBE_MAX_WORDS * width) {
		fprintf(stderr, "sgxfive-test: %s: not 1 to %u %s words\n", path,
			PROBE_MAX_WORDS, width == 8 ? "USSE" : "PDS");
		return -1;
	}
	f->n = (uint32_t)(len / width);
	for (uint32_t i = 0; i < f->n; i++) {
		f->words[i] = 0;
		for (unsigned int b = 0; b < width; b++)
			f->words[i] |= (uint64_t)buf[i * width + b] << (8 * b);
	}
	base = base ? base + 1 : path;
	dot = strcspn(base, ".");
	snprintf(f->label, sizeof(f->label), "%.*s", (int)dot, base);
	f->name = f->label;
	return 0;
}

static bool pixels_all(const uint32_t *p, uint32_t n, uint32_t v)
{
	for (uint32_t i = 0; i < n; i++)
		if (p[i] != v)
			return false;
	return true;
}

struct probe_opts {
	uint32_t temps;		/* at least this many temporaries */
	bool coords;		/* the copy shader of a copy of the coordinates */
	bool pixels;		/* print every pixel */
	uint32_t pds_data;	/* 0, or the files are PDS programs with this many data dwords */
	struct probe_file use;	/* with pds_data: the fill's shader (stores sa0-sa15) */
	bool scratch_texture;	/* --scratch-heap texture: the scratch buffer in the texture heap */
	struct probe_file place;	/* --place OFFSET=FILE: a USE program in the code heap */
	uint32_t place_off;	/* ... at the heap base + this */
	int place_form;		/* --place-form: 0 CBASE, 1 an 18-bit EXE; -1 not given */
	struct sgxfive_poke pokes[SGXFIVE_POKE_MAX];	/* --poke: words of the fill's command */
	const char *poke_args[SGXFIVE_POKE_MAX];
	unsigned int npokes;
	uint64_t low;		/* --low ADDR: the scratch also there (0: not) */
	bool late;		/* --late R:K=V: the host writes V to scratch dword K */
	uint32_t late_ready, late_dword, late_value;	/* once dword R leaves its fill */
	struct probe_tri {	/* --tri */
		int slot;	/* the slot the files replace, or -1: a fill probe */
		uint32_t data;	/* a PDS slot's data dwords */
		struct probe_file fixed[SGXFIVE_TRI_SLOT_COUNT];	/* --slot (n 0: none) */
		uint32_t fixed_data[SGXFIVE_TRI_SLOT_COUNT];
		uint32_t width, height, max_width, max_height;	/* 0: the default */
		uint32_t vertices;	/* --vertices: 0, or the triangle and copies of it */
		uint32_t coords;	/* --vtx-coords: more output dwords per vertex */
		bool copy_depth;	/* --copy-depth: the copies at z = c / 16 */
		bool full;		/* --tri-full: the triangle covers the target */
		bool v_set;		/* --tri-v: the vertices, in 1/2^unit pixel */
		int32_t v256[3][2];
		uint32_t unit;		/* --tri-unit: 0, or the shift (4 to 20) */
		bool z_set;		/* --tri-z: the vertices' screen depths */
		float z[3];
		bool isp2_set;		/* --isp2 V: ISP word 2 in the state block */
		uint32_t isp2;
		uint32_t blk_mask;	/* --blk N=V: state block words set */
		uint32_t blk_val[SGXFIVE_TRI_BLOCK_WORDS];
		uint32_t blk_xor_mask;	/* --blk N^=V: state block words flipped */
		uint32_t blk_xor_val[SGXFIVE_TRI_BLOCK_WORDS];
		uint32_t add_mask;	/* --blk-add BIT=V[,V]: presence bits added */
		uint32_t add_val[16][2];
		uint32_t cmd_mask;	/* --cmd N=V: render command words set */
		uint32_t cmd_val[SGXFIVE_TRI_PROBE_CMD_WORDS];
		uint32_t cmd_xor_mask;	/* --cmd N^=V: render command words flipped */
		uint32_t cmd_xor_val[SGXFIVE_TRI_PROBE_CMD_WORDS];
		uint32_t vdm_mask;	/* --vdm N=V: VDM stream words set */
		uint32_t vdm_val[SGXFIVE_TRI_PROBE_VDM2_WORDS];
		uint32_t vdm_xor_mask;	/* --vdm N^=V: VDM stream words flipped */
		uint32_t vdm_xor_val[SGXFIVE_TRI_PROBE_VDM2_WORDS];
		uint32_t pbe_mask;	/* --pbe N=V: the end-of-tile PBE words 0-3 set */
		uint32_t pbe_val[4];
		bool sideband_set;	/* --sideband V: the end-of-tile emitpix2's */
		uint32_t sideband;
		uint32_t obj2;		/* --obj2 FIRST: 0, or the second object's first vertex */
		uint32_t obj2_blk_mask;	/* --obj2-blk N=V: its state block words set */
		uint32_t obj2_blk_val[SGXFIVE_TRI_PROBE_BLK2_WORDS];
		struct probe_file obj2_pixel;	/* --obj2-pixel FILE (n 0: the default fill) */
		struct probe_file obj2_pixpds;	/* --obj2-pixpds FILE:N (n 0: the default primary) */
		uint32_t obj2_pixpds_data;	/* its N data dwords */
		const char *dump_dir;	/* --dump-render DIR: the render's memory there */
		const char *kpoke[KPR_MAX];	/* --kpoke SPEC: written before each render */
		unsigned int nkpoke;
	} tri;
};

/*
 * A probe that failed (it says "failed:"): counted, for the exit status 3 of probe and
 * probe --tri. The line is printed as always; only the status changed.
 */
static unsigned int probe_failed_jobs;
#define PROBE_FAILED(...)	(probe_failed_jobs++, printf(__VA_ARGS__))

/* The texel (x, y) of a --coords probe's source. */
static uint32_t coord_texel(uint32_t x, uint32_t y)
{
	return y << 16 | x;
}

/* The scratch dwords changed, at most max_shown of them: how many changed. */
static uint32_t probe_scratch(const char *name, const uint32_t *sp, uint32_t max_shown)
{
	uint32_t shown = 0;

	for (uint32_t i = 0; i < SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4; i++) {
		if (sp[i] == SCRATCH_FILL(i))
			continue;
		if (shown++ < max_shown)
			printf("probe %s: scratch +0x%03x 0x%08x\n", name, i * 4, sp[i]);
	}
	if (shown > max_shown)
		printf("probe %s: scratch %u more changed\n", name, shown - max_shown);
	return shown;
}

/*
 * A probe's readback: the target's width x height pixels as o0 (the value, or the four
 * most frequent when they differ; every pixel, row by row, with pixels) and the scratch
 * dwords changed, at most max_shown of them.
 */
static void probe_report(const char *name, const uint32_t *p, uint32_t width,
			 uint32_t height, bool pixels, const uint32_t *sp, uint32_t max_shown)
{
	const uint32_t total = width * height;
	uint32_t val[64], cnt[64], nv = 0, other = 0;

	for (uint32_t i = 0; i < total; i++) {
		uint32_t k = 0;

		while (k < nv && val[k] != p[i])
			k++;
		if (k < nv)
			cnt[k]++;
		else if (nv < 64)
			val[nv] = p[i], cnt[nv++] = 1;
		else
			other++;
	}
	/* the most frequent first */
	for (uint32_t a = 1; a < nv; a++)
		for (uint32_t b = a; b > 0 && cnt[b] > cnt[b - 1]; b--) {
			uint32_t tv = val[b], tc = cnt[b];

			val[b] = val[b - 1], cnt[b] = cnt[b - 1];
			val[b - 1] = tv, cnt[b - 1] = tc;
		}
	if (nv == 1) {
		printf("probe %s: o0 0x%08x (%u of %u)\n", name, val[0], total, total);
	} else {
		printf("probe %s: o0 mixed", name);
		for (uint32_t k = 0; k < nv; k++) {
			if (k < 4)
				printf(" 0x%08x x%u", val[k], cnt[k]);
			else
				other += cnt[k];
		}
		if (other)
			printf(" other x%u", other);
		printf("\n");
	}
	for (uint32_t y = 0; pixels && y < height; y++) {
		printf("probe %s: row %u:", name, y);
		for (uint32_t x = 0; x < width; x++)
			printf(" %08x", p[y * width + x]);
		printf("\n");
	}
	probe_scratch(name, sp, max_shown);
}

/*
 * A failed probe's readback: the scratch dwords changed, at most max_shown of them, or
 * that none was. What ran before a render hung or faulted may have stored there.
 */
static void probe_report_failed(const char *name, const uint32_t *sp, uint32_t max_shown)
{
	if (!probe_scratch(name, sp, max_shown))
		printf("probe %s: scratch unchanged\n", name);
}

/*
 * One probe: a 64x32 fill whose shader is the file's program, with temps
 * temporaries and a 64 KiB scratch buffer (dword i = SCRATCH_FILL(i)) its
 * SCRATCH_IMM immediates point at; with coords, a 64x32 copy whose shader
 * is the program and whose source texel (x, y) is coord_texel(x, y). Prints
 * o0 as the surface holds it (the four most frequent values when the pixels
 * differ; every pixel, row by row, with pixels) and every scratch dword the
 * program changed; a failed job is reported, with the scratch, and recovered from.
 */
/*
 * --late: while the job runs, wait for scratch dword late_ready to leave its fill (a
 * shader's "ready"), at most LATE_NS, then write late_value to dword late_dword. The
 * scratch is write-combined on the CPU: the reads go to memory, the fence drains the write.
 */
static void probe_late(const char *name, uint32_t *sp, const struct probe_opts *po)
{
	volatile uint32_t *v = sp;
	const long long t0 = now_ns();
	long long t = t0;
	bool ready;

	while (!(ready = v[po->late_ready] != SCRATCH_FILL(po->late_ready)) && t - t0 < LATE_NS)
		t = now_ns();
	v[po->late_dword] = po->late_value;
	__atomic_thread_fence(__ATOMIC_SEQ_CST);
	printf("probe %s: late: ready (scratch +0x%03x) %s %lld us; scratch +0x%03x = 0x%08x "
	       "written\n", name, po->late_ready * 4, ready ? "seen after" : "not seen in",
	       (t - t0) / 1000, po->late_dword * 4, po->late_value);
}

/*
 * The EXE and CBASE bits (19:0) of a DOUTU that starts a program placed at offset off (a multiple
 * of 8) of the code heap: form 0 has the offset's bits 18:3 in EXE (bits 19:4) and bits 22:19 in
 * CBASE (bits 3:0); form 1 has bits 20:3 in an 18-bit EXE (bits 21:4) and CBASE 0, which reaches
 * past bit 19: the word's bits 21:20 are then the offset's bits 20:19, not the temporaries'.
 */
static uint32_t placed_doutu(uint32_t off, int form)
{
	return form == 0 ? ((off << 1) & 0xffff0) | ((off >> 19) & 0xf) : (off << 1) & 0x3ffff0;
}

static void probe_one(struct tool *t, const struct probe_file *f, const struct probe_opts *po)
{
	struct probe_source src = {
		{ &probe_ops, f->name }, t->progs, f->words, f->n, false,
		po->coords ? SGXFIVE_PROG_USE_COPY : SGXFIVE_PROG_USE_FILL, po->temps, 0,
		NULL, 0, 0, false, 0, NULL, 0, NULL, 0, 0, false,
	};

	if (po->pds_data) {
		/* the file is the fill's PDS secondary; the fill's shader is the given one */
		src.words = po->use.words;
		src.n = po->use.n;
		src.pds = f->words;
		src.pds_n = f->n;
		src.pds_data = po->pds_data;
	}
	if (po->place.n) {
		src.place_prim = true;
		src.placed_u0 = placed_doutu(po->place_off, po->place_form);
	}
	struct sgxfive_prog_source *saved = t->progs;
	const struct sgxfive_rect r = { 0, 0, 64, 32 };
	struct sgxfive_surface dst = { 0, 64, 32, 256 };
	struct sgxfive_bo *bo = NULL, *sbo = NULL, *cbo = NULL, *pbo = NULL;
	uint32_t *p = NULL, *sp = NULL, *cp = NULL, *pp = NULL;
	uint64_t addr = 0, saddr = 0, caddr = 0;
	long long t0 = 0;
	struct side s;
	char why[96];
	int ret;

	t->progs = &src.base;
	ret = side_init(t, &s);
	t->progs = saved;
	if (!ret)
		ret = surface(t, s.vm, 2, 0, &addr, &bo, &p);
	if (!ret && po->scratch_texture)
		ret = sgxfive_vm_alloc(s.vm, DRM_SGXFIVE_HEAP_TEXTURE,
				       SCRATCH_PAGES * (uint64_t)SGXFIVE_PAGE_SIZE, SGXFIVE_PAGE_SIZE,
				       &saddr);
	if (!ret)
		ret = surface(t, s.vm, SCRATCH_PAGES, 0, &saddr, &sbo, &sp);
	if (!ret && po->place.n) {
		const uint64_t base = sgxfive_dev_info(t->dev)->heaps[DRM_SGXFIVE_HEAP_USSE_PIXEL].base;
		uint64_t paddr = base + (po->place_off & ~(uint64_t)(SGXFIVE_PAGE_SIZE - 1));
		const uint32_t at = (po->place_off & (SGXFIVE_PAGE_SIZE - 1)) / 4;	/* dword in its page */

		ret = (po->place_off & (SGXFIVE_PAGE_SIZE - 1)) + po->place.n * 8 > SGXFIVE_PAGE_SIZE ?
		      -EINVAL : surface(t, s.vm, 1, 0, &paddr, &pbo, &pp);
		for (uint32_t i = 0; !ret && i < po->place.n; i++) {
			uint64_t w = po->place.words[i];
			const uint32_t imm = sgxfive_limm_get(w);

			if ((w & LIMM_MASK) == LIMM_VAL && (imm & ~0xffffu) == SCRATCH_IMM)
				w = sgxfive_limm_set(w, (uint32_t)saddr + (imm & 0xffff));
			pp[at + 2 * i] = (uint32_t)w;
			pp[at + 2 * i + 1] = (uint32_t)(w >> 32);
		}
		src.place_words = po->place.words;
		src.place_n = po->place.n;
		src.place_dst = pp + at;
		if (!ret)
			printf("probe %s: program placed at 0x%08llx (code heap base + 0x%x), "
			       "started as %s: DOUTU bits 21:0 0x%06x\n", f->name,
			       (unsigned long long)paddr + at * 4, po->place_off,
			       po->place_form ? "an 18-bit EXE" : "EXE and CBASE", src.placed_u0);
		else
			PROBE_FAILED("probe %s: failed: program at 0x%08llx: %s\n", f->name,
			       (unsigned long long)paddr + at * 4, strerror(-ret));
	}
	if (!ret && po->low &&
	    (ret = sgxfive_vm_map(s.vm, po->low, sbo, 0, SCRATCH_PAGES * SGXFIVE_PAGE_SIZE, 0))) {
		PROBE_FAILED("probe %s: failed: scratch at 0x%08llx: %s\n", f->name,
		       (unsigned long long)po->low, strerror(-ret));
		goto out;
	}
	if (!ret && po->coords)
		ret = surface(t, s.vm, 3, DRM_SGXFIVE_VM_MAP_READ_ONLY, &caddr, &cbo, &cp);
	for (uint32_t i = 0; !ret && po->coords && i < 2048; i++)
		cp[i] = coord_texel(i % 64, i / 64);
	if (!ret) {
		for (uint32_t i = 0; i < SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4; i++)
			sp[i] = SCRATCH_FILL(i);
		src.scratch = saddr;
		printf("probe %s: scratch at 0x%08llx (%u KiB)\n", f->name,
		       (unsigned long long)saddr, SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 1024);
		if (po->low)
			printf("probe %s: scratch also at 0x%08llx\n", f->name,
			       (unsigned long long)po->low);
		dst.addr = addr;
		if (po->npokes) {
			printf("probe %s: pokes", f->name);
			for (unsigned int k = 0; k < po->npokes; k++)
				printf(" %s", po->poke_args[k]);
			printf("\n");
			sgxfive_xfer_set_hook(s.x, sgxfive_poke_hook,
					      &(struct sgxfive_poke_set){ po->pokes, po->npokes });
		}
		t0 = now_ns();
		if (po->coords) {
			const struct sgxfive_surface csrc = { caddr, 64, 32, 256 };

			ret = sgxfive_xfer_copy(s.x, &csrc, 0, 0, &dst, &r, 0);
		} else {
			ret = sgxfive_xfer_fill(s.x, &dst, &r, 0, 0);
		}
	}
	if (src.pds_ref)
		printf("probe %s: PDS secondary at 0x%08llx (pixel PDS heap base + 0x%llx)\n",
		       f->name, (unsigned long long)src.pds_sec,
		       (unsigned long long)(src.pds_sec - src.pds_base));
	if (!ret && po->late)
		probe_late(f->name, sp, po);
	if (ret) {
		PROBE_FAILED("probe %s: failed: %s\n", f->name, strerror(-ret));
	} else if ((ret = probe_wait(s.x, f->name, t0))) {
		/* faulted or hung: recovered, the job failed and the context is lost */
		PROBE_FAILED("probe %s: failed: %s\n", f->name, job_error(ret, why, sizeof(why)));
		probe_report_failed(f->name, sp, 32);
	} else if (pixels_all(p, 2048, SENTINEL)) {
		/* the job completed without writing a pixel */
		PROBE_FAILED("probe %s: failed: no pixel written\n", f->name);
	} else {
		probe_report(f->name, p, 64, 32, po->pixels, sp, 32);
	}
out:
	sgxfive_bo_destroy(pbo);
	sgxfive_bo_destroy(cbo);
	sgxfive_bo_destroy(sbo);
	sgxfive_bo_destroy(bo);
	side_fini(t, &s);
}

/* ---- probe --tri: our own programs in the first triangle's render --------------------- */

/* "SLOT" or "SLOT:N" (N data dwords, a PDS slot's): 0, or -1 if not well formed. */
static int probe_tri_slot(const char *arg, int *slot, uint32_t *data)
{
	char name[16], *end;
	const char *colon = strchr(arg, ':');
	size_t len = colon ? (size_t)(colon - arg) : strlen(arg);
	unsigned long v = 0;

	if (len >= sizeof(name))
		return -1;
	memcpy(name, arg, len);
	name[len] = 0;
	*slot = sgxfive_tri_slot_find(name);
	if (*slot < 0)
		return -1;
	if (colon) {
		v = strtoul(colon + 1, &end, 0);
		if (*end || !colon[1])
			return -1;
	}
	*data = (uint32_t)v;
	if (!sgxfive_tri_slot_is_pds(*slot))
		return colon ? -1 : 0;
	/* whole rows of four dwords, at most two banks of 64 */
	return !colon || v < 4 || v % 4 || v > 128 ? -1 : 0;
}

/* --slot SLOT=FILE[:N]: 0, 2 (usage) or 1 (the file). */
static int probe_tri_fixed(const char *arg, struct probe_tri *pt)
{
	const char *eq = strchr(arg, '=');
	char spec[32], path[4096];
	const char *colon;
	int slot;
	uint32_t data;

	if (!eq || (size_t)(eq - arg) >= 16 || strlen(eq + 1) >= sizeof(path))
		return usage();
	/* SLOT, then an optional :N at the end of FILE */
	snprintf(path, sizeof(path), "%s", eq + 1);
	colon = strrchr(path, ':');
	if (colon && colon[1] && strspn(colon + 1, "0123456789xabcdefABCDEF") == strlen(colon + 1))
		path[colon - path] = 0;
	else
		colon = NULL;
	snprintf(spec, sizeof(spec), "%.*s%s%s", (int)(eq - arg), arg, colon ? ":" : "",
		 colon ? colon + 1 : "");
	if (probe_tri_slot(spec, &slot, &data) || pt->fixed[slot].n)
		return usage();
	if (probe_read(path, &pt->fixed[slot], sgxfive_tri_slot_is_pds(slot) ? 4 : 8))
		return 1;
	if (data && pt->fixed[slot].n <= data) {
		fprintf(stderr, "sgxfive-test: %s: no code after %u data dwords\n", path, data);
		return 1;
	}
	pt->fixed_data[slot] = data;
	return 0;
}

/* --width/--height/--max-width/--max-height V: true if opt is one (V parsed or not). */
static bool probe_tri_size(const char *opt, const char *val, struct probe_tri *pt)
{
	uint32_t *v = !strcmp(opt, "--width") ? &pt->width : !strcmp(opt, "--height") ?
		      &pt->height : !strcmp(opt, "--max-width") ? &pt->max_width :
		      !strcmp(opt, "--max-height") ? &pt->max_height : NULL;

	char *end;
	unsigned long long x;

	if (!v || !val)
		return false;
	/* a bad value becomes one probe_tri_check refuses */
	x = strtoull(val, &end, 0);
	*v = *end || !*val || !x || x > SGXFIVE_TRI_MAX_W ? UINT32_MAX : (uint32_t)x;
	return true;
}

/* "N=V" or "N^=V" (N below limit, V a 32-bit number): 0, or -1 (usage). */
static int probe_word_arg(const char *arg, unsigned long limit, unsigned long *n, bool *flip,
			  unsigned long *v)
{
	char *eq, *end;

	*n = strtoul(arg, &eq, 0);
	*flip = eq[0] == '^';
	eq += *flip;
	if (*eq != '=' || eq == arg + *flip || *n >= limit || !eq[1])
		return -1;
	*v = strtoul(eq + 1, &end, 0);
	return *end || *v > UINT32_MAX ? -1 : 0;
}

/* The --tri options as a whole, with their defaults filled in: 0, or -1 (usage). */
static int probe_tri_check(struct probe_opts *po)
{
	struct probe_tri *pt = &po->tri;
	bool fixed = false;

	for (unsigned int k = 0; k < SGXFIVE_TRI_SLOT_COUNT; k++)
		fixed |= pt->fixed[k].n != 0;
	if (pt->slot < 0)
		return fixed || pt->width || pt->height || pt->max_width || pt->max_height ||
		       pt->vertices || pt->coords || pt->copy_depth || pt->isp2_set || pt->blk_mask ||
		       pt->v_set || pt->z_set || pt->unit ||
		       pt->add_mask || pt->blk_xor_mask || pt->cmd_xor_mask || pt->pbe_mask ||
		       pt->cmd_mask || pt->vdm_mask || pt->vdm_xor_mask || pt->sideband_set || pt->dump_dir ||
		       pt->nkpoke || pt->obj2 || pt->obj2_blk_mask || pt->obj2_pixel.n ||
		       pt->obj2_pixpds.n ? -1 : 0;
	if (pt->copy_depth && !pt->vertices)
		return -1;
	if (pt->v_set && (pt->full || pt->vertices))
		return -1;
	if (pt->unit && !pt->v_set)
		return -1;
	/* the second object: whole triangles among the copies, and its words only with it */
	if (pt->obj2 && (pt->obj2 % 3 || pt->obj2 >= pt->vertices))
		return -1;
	if (!pt->obj2 && (pt->obj2_blk_mask || pt->obj2_pixel.n || pt->obj2_pixpds.n))
		return -1;
	/* the stream's words past the one-object stream's are the second object's */
	if (!pt->obj2 && (pt->vdm_mask | pt->vdm_xor_mask) >> SGXFIVE_TRI_VDM_WORDS)
		return -1;
	if (pt->sideband_set && pt->slot != SGXFIVE_TRI_SLOT_EOT && !pt->fixed[SGXFIVE_TRI_SLOT_EOT].n)
		return -1;
	if (po->coords || po->pds_data || po->use.n || pt->fixed[pt->slot].n)
		return -1;
	pt->width = pt->width ? pt->width : 64;
	pt->height = pt->height ? pt->height : 64;
	pt->max_width = pt->max_width ? pt->max_width : pt->width;
	pt->max_height = pt->max_height ? pt->max_height : pt->height;
	if (pt->width % 2 || pt->height % 2 || pt->max_width > SGXFIVE_TRI_MAX_W ||
	    pt->max_height > SGXFIVE_TRI_MAX_H || pt->width > pt->max_width ||
	    pt->height > pt->max_height)
		return -1;
	return 0;
}

/*
 * --dump-render: the kernel's debugfs render_param and render_tadata (the newest render
 * context's parameter slot from its PB on, and its TA data; SGXFIVE_DEBUGFS overrides
 * their directory, for the tests) copied to DIR/NAME.param.bin and DIR/NAME.tadata.bin,
 * while the probe's render context lives; after a failed job (failed) recovery has reset
 * the TA data but kept the PB pages. Returns 0 or -errno.
 */
static int dump_render(const char *dir, const char *name, bool failed)
{
	static const char *const what[2] = { "param", "tadata" };
	const char *dbg = getenv("SGXFIVE_DEBUGFS");
	long long size[2] = { 0, 0 };
	static char buf[65536];
	char path[4096];
	int ret = 0;

	for (unsigned int i = 0; i < 2 && !ret; i++) {
		int in, out;
		ssize_t n;

		snprintf(path, sizeof(path), "%s/render_%s",
			 dbg ? dbg : "/sys/kernel/debug/dri/0/sgx", what[i]);
		in = open(path, O_RDONLY);
		if (in < 0)
			return -errno;
		snprintf(path, sizeof(path), "%s/%s.%s.bin", dir, name, what[i]);
		out = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
		if (out < 0) {
			ret = -errno;
			close(in);
			break;
		}
		while ((n = read(in, buf, sizeof(buf))) > 0) {
			if (write(out, buf, (size_t)n) != n) {
				ret = errno ? -errno : -EIO;
				break;
			}
			size[i] += n;
		}
		if (n < 0)
			ret = -errno;
		close(out);
		close(in);
	}
	if (!ret)
		printf("probe %s: render memory to %s/%s.{param,tadata}.bin (%lld, %lld bytes)%s\n",
		       name, dir, name, size[0], size[1], failed ? " after the failure" : "");
	return ret;
}

/*
 * One --tri probe: the first triangle's W x H render (sgxfive_tri_probe.h) with the
 * file's program in its slot and the --slot programs in theirs, every USE replacement
 * with temps temporaries, a 64 KiB scratch buffer (dword i = SCRATCH_FILL(i)) the
 * scratch immediates point at, on a render context of its own. Prints the slots
 * replaced, then as a fill probe the target's pixels as o0 and every scratch dword
 * changed (several tiles may each store their own); a failed render is reported, with the
 * scratch, and recovered from.
 */
static void probe_tri_one(struct tool *t, const struct probe_file *f,
			  const struct probe_opts *po)
{
	const struct probe_tri *pt = &po->tri;
	struct sgxfive_tri_probe pr = { 0 };
	struct sgxfive_tri_params p;
	struct sgxfive_tri_rig *g = NULL;
	struct sgxfive_vm *vm = NULL;
	struct sgxfive_bo *sbo = NULL;
	uint32_t *sp = NULL, ctx = 0;
	uint64_t saddr = 0;
	bool submitted = false;
	char why[96];
	int ret;

	for (unsigned int k = 0; k < SGXFIVE_TRI_SLOT_COUNT; k++)
		if (pt->fixed[k].n)
			pr.slot[k] = (struct sgxfive_tri_prog){ pt->fixed[k].words, pt->fixed[k].n,
								pt->fixed_data[k], po->temps };
	pr.slot[pt->slot] = (struct sgxfive_tri_prog){ f->words, f->n, pt->data, po->temps };
	pr.vertices = pt->vertices;
	pr.coords = pt->coords;
	pr.copy_depth = pt->copy_depth;
	pr.isp2_set = pt->isp2_set;
	pr.isp2 = pt->isp2;
	pr.blk_mask = pt->blk_mask;
	memcpy(pr.blk_val, pt->blk_val, sizeof(pr.blk_val));
	pr.blk_xor_mask = pt->blk_xor_mask;
	memcpy(pr.blk_xor_val, pt->blk_xor_val, sizeof(pr.blk_xor_val));
	pr.add_mask = pt->add_mask;
	memcpy(pr.add_val, pt->add_val, sizeof(pr.add_val));
	pr.cmd_mask = pt->cmd_mask;
	memcpy(pr.cmd_val, pt->cmd_val, sizeof(pr.cmd_val));
	pr.cmd_xor_mask = pt->cmd_xor_mask;
	memcpy(pr.cmd_xor_val, pt->cmd_xor_val, sizeof(pr.cmd_xor_val));
	pr.vdm_mask = pt->vdm_mask;
	memcpy(pr.vdm_val, pt->vdm_val, sizeof(pr.vdm_val));
	pr.vdm_xor_mask = pt->vdm_xor_mask;
	memcpy(pr.vdm_xor_val, pt->vdm_xor_val, sizeof(pr.vdm_xor_val));
	pr.pbe_mask = pt->pbe_mask;
	memcpy(pr.pbe_val, pt->pbe_val, sizeof(pr.pbe_val));
	pr.sideband_set = pt->sideband_set;
	pr.sideband = pt->sideband;
	pr.obj2_first = pt->obj2;
	pr.obj2_blk_mask = pt->obj2_blk_mask;
	memcpy(pr.obj2_blk_val, pt->obj2_blk_val, sizeof(pr.obj2_blk_val));
	if (pt->obj2_pixel.n)
		pr.obj2_pixel = (struct sgxfive_tri_prog){ pt->obj2_pixel.words, pt->obj2_pixel.n,
							   0, po->temps };
	if (pt->obj2_pixpds.n)
		pr.obj2_pixpds = (struct sgxfive_tri_prog){ pt->obj2_pixpds.words,
							    pt->obj2_pixpds.n, pt->obj2_pixpds_data, 0 };
	ret = sgxfive_vm_create(t->dev, &vm);
	if (!ret)
		ret = sgxfive_render_ctx_create(vm, pt->max_width, pt->max_height, &ctx);
	if (!ret)
		ret = sgxfive_tri_rig_create(vm, ctx, pt->max_width, pt->max_height, &g);
	if (!ret)
		ret = surface(t, vm, SCRATCH_PAGES, 0, &saddr, &sbo, &sp);
	if (!ret) {
		for (uint32_t i = 0; i < SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4; i++)
			sp[i] = SCRATCH_FILL(i);
		pr.scratch = (uint32_t)saddr;
		printf("probe %s: scratch at 0x%08llx (%u KiB)\n", f->name,
		       (unsigned long long)saddr, SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 1024);
		printf("probe %s: tri %ux%u", f->name, pt->width, pt->height);
		if (pt->vertices)
			printf(" (%u vertices%s)", pt->vertices,
			       pt->copy_depth ? ", at depths" : "");
		if (pt->coords)
			printf(" (%u coordinates)", pt->coords);
		if (pt->isp2_set)
			printf(" (isp2 0x%08x)", pt->isp2);
		if (pt->add_mask)
			printf(" (blk-add 0x%02x)", pt->add_mask);
		if (pt->blk_mask || pt->blk_xor_mask) {
			printf(" (block words");
			for (unsigned int k = 0; k < SGXFIVE_TRI_BLOCK_WORDS; k++) {
				if (pt->blk_mask >> k & 1)
					printf(" %u", k);
				if (pt->blk_xor_mask >> k & 1)
					printf(" ^%u", k);
			}
			printf(")");
		}
		if (pt->cmd_mask || pt->cmd_xor_mask) {
			printf(" (command words");
			for (unsigned int k = 0; k < SGXFIVE_TRI_PROBE_CMD_WORDS; k++) {
				if (pt->cmd_mask >> k & 1)
					printf(" %u", k);
				if (pt->cmd_xor_mask >> k & 1)
					printf(" ^%u", k);
			}
			printf(")");
		}
		if (pt->vdm_mask || pt->vdm_xor_mask) {
			printf(" (VDM words");
			for (unsigned int k = 0; k < SGXFIVE_TRI_PROBE_VDM2_WORDS; k++) {
				if (pt->vdm_mask >> k & 1)
					printf(" %u", k);
				if (pt->vdm_xor_mask >> k & 1)
					printf(" ^%u", k);
			}
			printf(")");
		}
		if (pt->pbe_mask) {
			printf(" (PBE words");
			for (unsigned int k = 0; k < 4; k++)
				if (pt->pbe_mask >> k & 1)
					printf(" %u", k);
			printf(")");
		}
		if (pt->sideband_set)
			printf(" (sideband 0x%08x)", pt->sideband);
		if (pt->obj2) {
			printf(" (obj2 from %u:", pt->obj2);
			if (pt->obj2_blk_mask) {
				printf(" block words");
				for (unsigned int k = 0; k < SGXFIVE_TRI_PROBE_BLK2_WORDS; k++)
					if (pt->obj2_blk_mask >> k & 1)
						printf(" %u", k);
			}
			printf("%s%s%s%s)", pt->obj2_blk_mask && pt->obj2_pixel.n ? "," : "",
			       pt->obj2_pixel.n ? " pixel" : "",
			       (pt->obj2_blk_mask || pt->obj2_pixel.n) && pt->obj2_pixpds.n ? "," : "",
			       pt->obj2_pixpds.n ? " primary" : "");
		}
		printf(",");
		for (unsigned int k = 0; k < SGXFIVE_TRI_SLOT_COUNT; k++)
			if (pr.slot[k].n)
				printf(" %s", sgxfive_tri_slot_name(k));
		printf(" replaced\n");
		if (pt->nkpoke) {
			printf("probe %s: kpoke", f->name);
			for (unsigned int k = 0; k < pt->nkpoke; k++)
				printf(" %s", pt->kpoke[k]);
			printf("\n");
		}
		/* the kernel takes them for the next render, this case's */
		for (unsigned int k = 0; k < pt->nkpoke && !ret; k++)
			ret = kpoke_write(pt->kpoke[k]);
		sgxfive_tri_default(&p, pt->width, pt->height);
		if (pt->full) {
			p.v[0][0] = p.v[0][1] = p.v[1][1] = p.v[2][0] = 0;
			p.v[1][0] = 3 * 16 * (int32_t)p.width;
			p.v[2][1] = 3 * 16 * (int32_t)p.height;
			printf("probe %s: triangle (%d,%d) (%d,%d) (%d,%d)\n", f->name,
			       p.v[0][0] / 16, p.v[0][1] / 16, p.v[1][0] / 16, p.v[1][1] / 16,
			       p.v[2][0] / 16, p.v[2][1] / 16);
		}
		if (pt->v_set)
			sgxfive_tri_fine_unit(&p, pt->v256, pt->unit ? pt->unit : 8);
		if (pt->z_set)
			for (int v = 0; v < 3; v++)
				p.zndc[v] = 2 * pt->z[v] - 1;
		if (pt->v_set || pt->z_set) {
			printf("probe %s:", f->name);
			if (pt->v_set)
				printf(" vertices%u %d %d %d %d %d %d%s", 1u << (pt->unit ? pt->unit : 8),
				       pt->v256[0][0], pt->v256[0][1],
				       pt->v256[1][0], pt->v256[1][1], pt->v256[2][0], pt->v256[2][1],
				       pt->z_set ? "," : "");
			if (pt->z_set)
				printf(" depth %g %g %g", pt->z[0], pt->z[1], pt->z[2]);
			printf("\n");
		}
		if (!ret)
			ret = sgxfive_tri_rig_build(g, &p, &pr);
		if (!ret)
			ret = sgxfive_tri_rig_submit(g);
		submitted = !ret;
	}
	if (ret) {
		PROBE_FAILED("probe %s: failed: %s\n", f->name, strerror(-ret));
	} else if ((ret = sgxfive_tri_rig_wait(g, WAIT_NS))) {
		/* faulted, hung or overflowed: recovered, the render failed */
		PROBE_FAILED("probe %s: failed: %s\n", f->name, job_error(ret, why, sizeof(why)));
		probe_report_failed(f->name, sp, SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4);
		/* an overflow keeps its context and its target holds the partial renders' stores */
		if (ret == -ENOSPC)
			probe_report(f->name, g->fb, pt->width, pt->height, po->pixels, sp,
				     SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4);
	} else if (pixels_all(g->fb, pt->width * pt->height, SGXFIVE_TRI_SENTINEL)) {
		PROBE_FAILED("probe %s: failed: no pixel written\n", f->name);
	} else {
		probe_report(f->name, g->fb, pt->width, pt->height, po->pixels, sp,
			     SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4);
	}
	/* what the TA wrote, before the context goes: after a failure too, how far it got */
	if (submitted && pt->dump_dir) {
		int dr = dump_render(pt->dump_dir, f->name, ret != 0);

		if (dr)
			PROBE_FAILED("probe %s: failed: --dump-render: %s\n", f->name, strerror(-dr));
	}
	sgxfive_tri_rig_destroy(g);
	sgxfive_bo_destroy(sbo);
	if (ctx)
		sgxfive_ctx_destroy(t->dev, ctx);
	sgxfive_vm_destroy(vm);
}

static int cmd_probe(struct tool *t, struct probe_file *files, uint32_t n,
		     const struct probe_opts *po)
{
	for (uint32_t i = 0; i < n; i++) {
		if (po->tri.slot >= 0)
			probe_tri_one(t, &files[i], po);
		else
			probe_one(t, &files[i], po);
	}
	return probe_failed_jobs ? EXIT_JOB_FAILED : 0;
}

/* ---- main --------------------------------------------------------------------------- */

/* ---- tri ---------------------------------------------------------------------------- */

/* The image as text, one character a pixel: # triangle, . background, ? other. */
static void tri_show(const struct sgxfive_tri_params *p, const uint32_t *fb)
{
	for (uint32_t y = 0; y < p->height && y < 128; y++) {
		for (uint32_t x = 0; x < p->width && x < 128; x++) {
			uint32_t v = fb[y * p->width + x];

			putchar(v == p->colour ? '#' : v == p->bg_colour ? '.' :
				v == SGXFIVE_TRI_SENTINEL ? 's' : '?');
		}
		putchar('\n');
	}
}

/* The triangle's reference: its colour inside, the background outside, either at edges. */
static bool tri_ok(const void *ctx, uint32_t x, uint32_t y, uint32_t v, uint32_t *want)
{
	const struct sgxfive_tri_params *p = ctx;
	const int e = sgxfive_tri_expect(p, x, y);

	*want = e ? p->colour : p->bg_colour;
	return v == *want || (e < 0 && v == p->bg_colour);
}

/*
 * tri --scratch: pages in the GENERAL heap that nothing of the scene uses, for a kernel
 * poke to point a unit's base at; filled before each render, what changed reported after.
 */
struct scratch {
	struct sgxfive_bo *bo;
	uint32_t *map;
	uint64_t addr, size;
};

static int scratch_create(struct tool *t, struct sgxfive_vm *vm, uint32_t pages, uint64_t at,
			  struct scratch *s)
{
	void *map;
	int ret;

	s->size = (uint64_t)pages * SGXFIVE_PAGE_SIZE;
	ret = sgxfive_bo_create(t->dev, s->size, DRM_SGXFIVE_BO_ALLOW_CPU_ACCESS, &s->bo);
	if (!ret)
		ret = sgxfive_bo_mmap(s->bo, &map);
	s->addr = at;
	if (!ret && !at)
		ret = sgxfive_vm_alloc(vm, DRM_SGXFIVE_HEAP_GENERAL, s->size, SGXFIVE_PAGE_SIZE,
				       &s->addr);
	if (!ret)
		ret = sgxfive_vm_map(vm, s->addr, s->bo, 0, s->size, 0);
	if (ret) {
		sgxfive_bo_destroy(s->bo);
		s->bo = NULL;
		return ret;
	}
	s->map = map;
	return 0;
}

/* every dword v, the first nd of them those of d (a table the host built) */
static void scratch_fill(const struct scratch *s, uint32_t v, const uint32_t *d, uint32_t nd)
{
	for (uint64_t i = 0; i < s->size / 4; i++)
		s->map[i] = i < nd ? d[i] : v;
}

/* every dword of the buffer as its fill says */
static void zbuf_fill(const struct scratch *s, const struct fill *f)
{
	for (uint64_t i = 0; i < s->size / 4; i++)
		s->map[i] = fill_at(f, i);
}

static void scratch_report(const struct scratch *s, uint32_t v, const uint32_t *d, uint32_t nd)
{
	const uint32_t per_page = SGXFIVE_PAGE_SIZE / 4;
	uint32_t total = 0;

	for (uint64_t pg = 0; pg < s->size / SGXFIVE_PAGE_SIZE; pg++) {
		const uint32_t *w = s->map + pg * per_page;
		uint32_t n = 0, first = 0;

		for (uint32_t i = 0; i < per_page; i++) {
			const uint64_t k = pg * per_page + i;

			if (w[i] != (k < nd ? d[k] : v) && !n++)
				first = i;
		}
		if (n)
			printf("scratch page %llu: %u changed, first +0x%x 0x%08x\n",
			       (unsigned long long)pg, n, first * 4, w[first]);
		total += n;
	}
	printf("scratch: %u dwords changed\n", total);
}

/*
 * tri --depth: the buffer of the ZLS load and store (a scratch buffer of the target's
 * width x height dwords and sixteen pages over), the pokes that point the render flags, the
 * ZLS clear value, the control word and both bases at it, and what a render left in it:
 * the dwords that differ from the fill and the most frequent values.
 */
#define DEPTH_MARGIN_PAGES	16
#define DEPTH_SLOTS		(1u << 16)
#define DEPTH_SLOTS_USED	(DEPTH_SLOTS / 2)

static uint32_t depth_min_pages(const struct opts *o)
{
	return (uint32_t)(((uint64_t)o->width * o->height * 4 + SGXFIVE_PAGE_SIZE - 1) /
			  SGXFIVE_PAGE_SIZE);
}

/* The ZLS buffers of tri --depth: the depth buffer, optional store, stencil and stencil store. */
struct zbufs {
	struct scratch depth, depth_store, stencil, stencil_store;
};

static int depth_poke(const char *fmt, ...)
{
	char line[40];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(line, sizeof(line), fmt, ap);
	va_end(ap);
	return kpoke_write(line);
}

/*
 * The pokes that point the job at the buffers: the render flags (depth buffer, with the stencil
 * buffer's bit 8 when there is one), the ZLS base, the control, the depth load and store bases
 * (offsets from the base; the store on its own buffer if there is one) and, with a stencil
 * buffer, the stencil load and store bases (bit 31 set).
 */
static int depth_arm(const struct zbufs *z, uint32_t base, uint32_t ctl)
{
	const struct scratch *ds = z->depth_store.bo ? &z->depth_store : &z->depth;
	const struct scratch *ss = z->stencil_store.bo ? &z->stencil_store : &z->stencil;
	int ret = depth_poke(z->stencil.bo ? "ta:7^=0x180" : "ta:7^=0x80");

	if (!ret)
		ret = depth_poke("rd:1=0x%x", base);
	if (!ret)
		ret = depth_poke("rd:11=0x%08x", ctl);
	if (!ret)
		ret = depth_poke("rd:12=0x%llx", (unsigned long long)(z->depth.addr - base));
	if (!ret)
		ret = depth_poke("rd:13=0x%llx", (unsigned long long)(ds->addr - base));
	if (!ret && z->stencil.bo)
		ret = depth_poke("rd:14=0x%llx", 0x80000000ull | (z->stencil.addr - base));
	if (!ret && z->stencil.bo)
		ret = depth_poke("rd:15=0x%llx", 0x80000000ull | (ss->addr - base));
	return ret;
}

static void depth_report(const char *name, const struct scratch *d, const struct fill *fill,
			 uint32_t render)
{
	const uint64_t n = d->size / 4;
	uint32_t *val = calloc(DEPTH_SLOTS, sizeof(*val));
	uint32_t *cnt = calloc(DEPTH_SLOTS, sizeof(*cnt));
	uint32_t changed = 0, distinct = 0, top[4];
	unsigned int nt = 0;
	bool full = false;

	if (!val || !cnt) {
		printf("%s #%u: no memory for the report\n", name, render);
		free(val);
		free(cnt);
		return;
	}
	for (uint64_t i = 0; i < n; i++) {
		const uint32_t v = d->map[i];
		uint32_t h = (v * 2654435761u) >> 16;

		changed += v != fill_at(fill, i);
		while (cnt[h] && val[h] != v)
			h = (h + 1) & (DEPTH_SLOTS - 1);
		if (!cnt[h]) {
			if (distinct == DEPTH_SLOTS_USED) {
				full = true;
				continue;
			}
			val[h] = v;
			distinct++;
		}
		cnt[h]++;
	}
	while (nt < 4) {		/* the four most frequent values, by repeated scan */
		uint32_t best = DEPTH_SLOTS;

		for (uint32_t h = 0; h < DEPTH_SLOTS; h++) {
			bool taken = false;

			for (unsigned int j = 0; j < nt; j++)
				taken |= top[j] == h;
			if (cnt[h] && !taken && (best == DEPTH_SLOTS || cnt[h] > cnt[best]))
				best = h;
		}
		if (best == DEPTH_SLOTS)
			break;
		top[nt++] = best;
	}
	printf("%s #%u: %llu dwords, %u changed, %u%s distinct;", name, render,
	       (unsigned long long)n, changed, distinct, full ? "+" : "");
	for (unsigned int k = 0; k < nt; k++)
		printf("%s 0x%08x x %u", k ? "," : "", val[top[k]], cnt[top[k]]);
	printf("\n");
	free(val);
	free(cnt);
}

static int depth_dump(const char *dir, const char *name, const struct scratch *d, uint32_t render)
{
	char path[4096];
	FILE *f;
	int ret = 0;

	snprintf(path, sizeof(path), "%s/%s.%u.bin", dir, name, render);
	f = fopen(path, "wb");
	if (!f)
		return -errno;
	if (fwrite(d->map, 1, d->size, f) != d->size)
		ret = -EIO;
	if (fclose(f) && !ret)
		ret = -EIO;
	return ret;
}

static void scratch_destroy(struct sgxfive_vm *vm, struct scratch *s)
{
	if (!s->bo)
		return;
	sgxfive_vm_unmap(vm, s->addr, s->size);
	sgxfive_bo_destroy(s->bo);
}

/*
 * One line to the kernel's debugfs kpoke (SGXFIVE_KPOKE overrides the path, for the
 * tests): the kernel arms it for the next job of its kind. One write(2), appending and
 * never seeking: the debugfs file has no seek, which stdio's append mode does.
 */
/* One debugfs file's value (SGXFIVE_DEBUGFS overrides the directory, for the tests). */
static int debugfs_set(const char *name, const char *value)
{
	const char *dbg = getenv("SGXFIVE_DEBUGFS");
	char path[4096];
	int fd, ret = 0;
	size_t n = strlen(value);

	snprintf(path, sizeof(path), "%s/%s", dbg ? dbg : "/sys/kernel/debug/dri/0/sgx", name);
	fd = open(path, O_WRONLY);
	if (fd < 0)
		return -errno;
	if (write(fd, value, n) != (ssize_t)n)
		ret = errno ? -errno : -EIO;
	close(fd);
	return ret;
}

static int kpoke_write(const char *spec)
{
	const char *path = getenv("SGXFIVE_KPOKE");
	char line[128];
	int fd, n, ret = 0;

	n = snprintf(line, sizeof(line), "%s\n", spec);
	if (n < 0 || (size_t)n >= sizeof(line))
		return -EINVAL;
	fd = open(path ? path : "/sys/kernel/debug/dri/0/sgx/kpoke", O_WRONLY | O_APPEND);
	if (fd < 0)
		return -errno;
	if (write(fd, line, (size_t)n) != n)
		ret = errno ? -errno : -EIO;
	close(fd);
	return ret;
}

/*
 * One debugfs file (SGXFIVE_DEBUGFS overrides the directory, for the tests) copied to
 * path; its size in *size. Returns 0 or -errno.
 */
static int debugfs_copy(const char *name, const char *path, long long *size)
{
	const char *dbg = getenv("SGXFIVE_DEBUGFS");
	static char buf[65536];
	char src[4096];
	ssize_t n;
	int in, out, ret = 0;

	*size = 0;
	snprintf(src, sizeof(src), "%s/%s", dbg ? dbg : "/sys/kernel/debug/dri/0/sgx", name);
	in = open(src, O_RDONLY);
	if (in < 0)
		return -errno;
	out = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (out < 0) {
		ret = -errno;
		close(in);
		return ret;
	}
	while ((n = read(in, buf, sizeof(buf))) > 0) {
		if (write(out, buf, (size_t)n) != n) {
			ret = errno ? -errno : -EIO;
			break;
		}
		*size += n;
	}
	if (n < 0 && !ret)
		ret = -errno;
	close(out);
	close(in);
	return ret;
}

/*
 * --close-trace: what the kernel keeps of the cleanup that just ran (debugfs render_cleanup,
 * the last render context's) and dwords 32, 46 and 47 of the TA/3D control block (buf09: the
 * PB descriptor it holds and the loaded PB's two slots), after the event named (which: "after closing the second context").
 */
static void close_trace(const char *which)
{
	const char *dbg = getenv("SGXFIVE_DEBUGFS");
	char path[4096], line[256];
	uint32_t w[48];
	FILE *f;

	snprintf(path, sizeof(path), "%s/render_cleanup", dbg ? dbg : "/sys/kernel/debug/dri/0/sgx");
	f = fopen(path, "r");
	if (!f) {
		printf("cleanup %s: unreadable\n", which);
	} else {
		while (fgets(line, sizeof(line), f)) {
			line[strcspn(line, "\n")] = 0;
			printf("cleanup %s: %s\n", which, line);
		}
		fclose(f);
	}
	snprintf(path, sizeof(path), "%s/buf09", dbg ? dbg : "/sys/kernel/debug/dri/0/sgx");
	f = fopen(path, "rb");
	if (f && fread(w, 4, 48, f) == 48)
		printf("ta3dctl %s: dword 32 0x%08x, dword 46 0x%08x, "
		       "dword 47 0x%08x\n", which, w[32], w[46], w[47]);
	else
		printf("ta3dctl %s: unreadable\n", which);
	if (f)
		fclose(f);
}

/*
 * --words DIR: the newest render context's words (debugfs render_words: its HW context,
 * RT data set, PB descriptor, kernel words and render details, a kpoke line each) and the
 * EDM's TA/3D control block (debugfs buf09) to DIR/words.N.txt and DIR/ta3d.N.bin.
 */
static int save_words(const struct tool *t, const struct opts *o, const char *dir, uint32_t n)
{
	char words[4096], ta3d[4096];
	long long ws, ts;
	int ret;

	snprintf(words, sizeof(words), "%s/words.%u.txt", dir, n);
	snprintf(ta3d, sizeof(ta3d), "%s/ta3d.%u.bin", dir, n);
	ret = debugfs_copy("render_words", words, &ws);
	if (!ret)
		ret = debugfs_copy("buf09", ta3d, &ts);
	if (!ret)
		printf("tri: words %u to %s (%lld bytes), %s (%lld bytes)\n", n, words, ws, ta3d,
		       ts);
	if (!ret && o->regs) {		/* the registers where the words were read */
		printf("tri: registers at snapshot %u\n", n);
		print_regs(t, o);
	}
	return ret;
}

/*
 * The first triangle from userspace: a render
 * context, our programs and scene in the VM, n renders with alternating
 * colours, every pixel against the CPU reference and the guard area intact.
 */
/* The second context's render i: the first's scene in the other pair of colours. */
static int tri2_submit(struct sgxfive_render *r2, const struct opts *o, uint32_t i,
		       struct sgxfive_tri_params *p2)
{
	int ret;

	static const uint32_t colours[2][2] = {
		{ 0xff00ff00, 0xff203040 }, { 0xffff0000, 0xff000080 },
	};

	for (unsigned int k = 0; k < o->nkpr; k++) {
		if (o->kpr[k].n != i + 1 || !o->kpr[k].second)
			continue;
		/*
		 * Overlapping, the kernel must have kicked the first context's job before the poke
		 * is armed, or the poke lands on that kick: give its scheduler 30 ms.
		 */
		if (o->overlap)
			usleep(30000);
		ret = kpr_write(o->kpr[k].reg, o->kpr[k].spec);
		if (ret)
			return ret;
		printf("tri: %s before second-context render %u: %s\n",
		       o->kpr[k].reg ? "kregnow" : "kpoke", i + 1, o->kpr[k].spec);
	}
	sgxfive_tri_default(p2, o->width, o->height);
	p2->colour = colours[(i + 1) % 2][0];
	p2->bg_colour = colours[(i + 1) % 2][1];
	return sgxfive_render_tri_flags(r2, p2, 0, 0, 0);
}

/* "tri.N": the name of render N's --dump-each files */
static const char *tri_name(uint32_t n)
{
	static char name[24];

	snprintf(name, sizeof(name), "tri.%u", n);
	return name;
}

static int cmd_tri(struct tool *t, const struct opts *o)
{
	static const uint32_t colours[2][2] = {
		{ 0xff00ff00, 0xff203040 }, { 0xffff0000, 0xff000080 },
	};
	struct sgxfive_render *r = NULL, *r2 = NULL;
	struct sgxfive_poke_set pokes = { o->pokes, o->npokes };
	struct sgxfive_tri_params p;
	struct sgxfive_vm *vm = NULL;
	uint32_t ctx = 0, ctx2 = 0, ok = 0;
	bool early_closed = false;	/* --close-first-early has closed the first context */
	bool first_first;		/* the first context is closed before the second */
	int bad = 0;
	const uint32_t max_w = o->max_width == UINT32_MAX ? o->width : o->max_width;
	const uint32_t max_h = o->max_height == UINT32_MAX ? o->height : o->max_height;
	const long long wait_ns = o->wait_ms ? o->wait_ms * 1000000LL : WAIT_NS;
	struct scratch sc = { 0 };
	struct zbufs z = { .depth = { 0 } };
	uint32_t overflowed = 0;
	int ret;

	ret = sgxfive_vm_create(t->dev, &vm);
	if (!ret)
		ret = sgxfive_render_ctx_create(vm, max_w, max_h, &ctx);
	if (!ret)
		ret = sgxfive_render_create(vm, ctx, &r);
	if (ret) {
		fail("render context", ret);
		goto out;
	}
	printf("tri: render context for targets up to %ux%u\n", max_w, max_h);
	if (o->scratch) {
		ret = scratch_create(t, vm, o->scratch, o->scratch_at, &sc);
		if (ret) {
			fail("scratch buffer", ret);
			goto out;
		}
		printf("scratch: 0x%08llx %u pages, fill 0x%08x", (unsigned long long)sc.addr,
		       o->scratch, o->scratch_fill);
		if (o->scratch_words)
			printf(", file %u dwords", o->scratch_words);
		printf("\n");
	}
	if (o->depth) {
		const uint32_t pages = o->depth_pages != UINT32_MAX ? o->depth_pages :
				       depth_min_pages(o) + DEPTH_MARGIN_PAGES;

		struct { const char *name; bool want; struct scratch *s; const struct fill *f; } zb[] = {
			{ "depth", true, &z.depth, &o->depth_fill },
			{ "depth store", o->depth_store, &z.depth_store, &o->depth_store_fill },
			{ "stencil", o->stencil, &z.stencil, &o->stencil_fill },
			{ "stencil store", o->stencil_store, &z.stencil_store, &o->stencil_store_fill },
		};

		for (unsigned int k = 0; k < sizeof(zb) / sizeof(zb[0]); k++) {
			if (!zb[k].want)
				continue;
			ret = scratch_create(t, vm, pages, 0, zb[k].s);
			if (ret) {
				fail(k ? "depth, stencil buffer" : "depth buffer", ret);
				goto out;
			}
			printf("%s: 0x%08llx %u pages, ", zb[k].name, (unsigned long long)zb[k].s->addr,
			       pages);
			fill_print(zb[k].f);
			if (!k)
				printf(", base 0x%08x, control 0x%08x", o->depth_base, o->depth_ctl);
			if (!k && o->depth_ctl_next)
				printf(", then 0x%08x", o->depth_ctl_next);
			printf("\n");
		}
	}
	if (o->fault) {
		struct sgxfive_tri_layout l;

		sgxfive_render_get_layout(r, &l);
		ret = sgxfive_vm_unmap(vm, l.gen, SGXFIVE_PAGE_SIZE);
		if (ret) {
			fail("unmap the stream", ret);
			goto out;
		}
	}
	sgxfive_render_set_hook(r, sgxfive_poke_hook, &pokes);	/* none: no change */
	if (o->ctx2) {
		if (o->share_pb) {
			ret = debugfs_set("render_share_pb", "Y");
			if (ret) {
				fail("render_share_pb", ret);
				goto out;
			}
		}
		ret = sgxfive_render_ctx_create(vm, max_w, max_h, &ctx2);
		if (!ret)
			ret = sgxfive_render_create(vm, ctx2, &r2);
		if (ret) {
			fail("second render context", ret);
			goto out;
		}
		printf(o->share_pb ? "tri: second render context shares the first's parameter buffer\n"
				   : "tri: second render context\n");
	}
	if (o->words_dir) {
		ret = save_words(t, o, o->words_dir, 0);
		if (ret) {
			fail("--words", ret);
			printf("tri: --words: %s\n", strerror(-ret));
			goto out;
		}
	}
	for (uint32_t i = 0; i < o->n; i++) {
		struct sgxfive_tri_counts n;
		struct sgxfive_tri_params p2;
		int ret2 = 0, wait2 = 0;
		bool early2;
		bool geometry;
		long long t0 = now_ns();
		uint32_t guard;
		int wait_err = 0;
		bool over;

		sgxfive_tri_default(&p, o->width, o->height);
		p.colour = colours[i % 2][0];
		p.bg_colour = colours[i % 2][1];
		if (o->tri_full) {
			p.v[0][0] = p.v[0][1] = p.v[1][1] = p.v[2][0] = 0;
			p.v[1][0] = 3 * 16 * (int32_t)p.width;
			p.v[2][1] = 3 * 16 * (int32_t)p.height;
		}
		if (o->tri_v_given)
			sgxfive_tri_fine_unit(&p, o->tri_v, o->tri_unit ? o->tri_unit : 8);
		if (o->tri_z_given)
			for (int v = 0; v < 3; v++)
				p.zndc[v] = 2 * o->tri_z[v] - 1;
		if (o->tri_v_given) {
			printf("tri: vertices%u %d %d %d %d %d %d", 1u << (o->tri_unit ? o->tri_unit : 8),
			       o->tri_v[0][0], o->tri_v[0][1],
			       o->tri_v[1][0], o->tri_v[1][1], o->tri_v[2][0], o->tri_v[2][1]);
			if (o->tri_z_given)
				printf(", depth %g %g %g", (p.zndc[0] + 1) / 2, (p.zndc[1] + 1) / 2,
				       (p.zndc[2] + 1) / 2);
			printf("\n");
			{	/* the clip words the job carries (float32 bits) */
				uint32_t cw[3][4];

				sgxfive_tri_vertex_words(&p, cw);
				for (int v = 0; v < 3; v++)
					printf("tri: clip%d 0x%08x 0x%08x 0x%08x 0x%08x\n", v, cw[v][0],
					       cw[v][1], cw[v][2], cw[v][3]);
			}
		} else if (o->tri_full || o->tri_z_given)
			printf("tri: triangle (%d,%d) (%d,%d) (%d,%d), depth %g %g %g\n",
			       p.v[0][0] / 16, p.v[0][1] / 16, p.v[1][0] / 16, p.v[1][1] / 16,
			       p.v[2][0] / 16, p.v[2][1] / 16, (p.zndc[0] + 1) / 2, (p.zndc[1] + 1) / 2,
			       (p.zndc[2] + 1) / 2);
		for (unsigned int k = 0; k < o->nmoves; k++) {
			if (o->moves[k].n != i + 1)
				continue;
			for (int v = 0; v < 3; v++) {
				p.v[v][0] += 16 * o->moves[k].dx;
				p.v[v][1] += 16 * o->moves[k].dy;
			}
			printf("tri: render %u moved by %d,%d\n", i + 1, o->moves[k].dx,
			       o->moves[k].dy);
		}
		if (z.depth.bo) {
			ret = depth_arm(&z, o->depth_base, i && o->depth_ctl_next ?
					o->depth_ctl_next : o->depth_ctl);
			if (ret) {
				fail("kpoke", ret);
				goto out;
			}
			if (!i || !o->depth_ctl_next) {
				zbuf_fill(&z.depth, &o->depth_fill);
				if (z.depth_store.bo)
					zbuf_fill(&z.depth_store, &o->depth_store_fill);
				if (z.stencil.bo)
					zbuf_fill(&z.stencil, &o->stencil_fill);
				if (z.stencil_store.bo)
					zbuf_fill(&z.stencil_store, &o->stencil_store_fill);
			}
		}
		for (unsigned int k = 0; k < o->nkpr; k++) {
			if (o->kpr[k].n != i + 1 || o->kpr[k].second)
				continue;
			ret = kpr_write(o->kpr[k].reg, o->kpr[k].spec);
			if (ret) {
				fail(o->kpr[k].reg ? "kregnow" : "kpoke", ret);
				goto out;
			}
			printf("tri: %s before render %u: %s\n", o->kpr[k].reg ? "kregnow" : "kpoke",
			       i + 1, o->kpr[k].spec);
		}
		if (sc.bo)
			scratch_fill(&sc, o->scratch_fill, o->scratch_data, o->scratch_words);
		geometry = o->geometry >> i & 1;
		ret = sgxfive_render_tri_flags(r, &p, 0, 0,
					       geometry ? DRM_SGXFIVE_SUBMIT_JOB_RENDER_GEOMETRY : 0);
		if (r2 && !ret && o->overlap)
			ret2 = tri2_submit(r2, o, i, &p2);
		early2 = r2 && !ret && !ret2 && o->overlap && o->wait_second;
		if (early2) {		/* the second's job first: the first's may never end */
			printf("tri: waiting for the second context's job first\n");
			wait2 = sgxfive_render_wait(r2, wait_ns);
			print_job(ret2, wait2);
		}
		if (!ret)
			wait_err = sgxfive_render_wait(r, wait_ns);
		print_job(ret, wait_err);
		if (r2 && !ret && !wait_err && (o->words_between ||
						(o->close_early && i + 1 == o->n))) {
			int wr = o->words_dir ? save_words(t, o, o->words_dir, 100 + i + 1) : 0;

			if (!wr && o->close_early && i + 1 == o->n) {
				sgxfive_ctx_destroy(t->dev, ctx);
				ctx = 0;
				early_closed = true;
				printf("tri: closed the first context before the second context's "
				       "render %u\n", i + 1);
				if (o->close_trace)
					close_trace("after closing the first context");
				if (o->words_dir)
					wr = save_words(t, o, o->words_dir, 200 + i + 1);
			}
			if (wr) {
				fail("--words", wr);
				ret = wr;
				break;
			}
		}
		if (r2 && !ret && !wait_err) {
			if (!o->overlap)
				ret2 = tri2_submit(r2, o, i, &p2);
			if (!early2) {
				wait2 = ret2 ? 0 : sgxfive_render_wait(r2, wait_ns);
				print_job(ret2, wait2);
			}
			if (!ret2 && !wait2) {
				struct sgxfive_tri_counts n2;

				ret2 = sgxfive_tri_check(&p2, sgxfive_render_fb(r2), &n2);
				printf("tri2 %ux%u #%u: %u triangle, %u background, %u other; wrong %u "
				       "inside, %u outside, %u at edges; %u if flipped; guard %u\n",
				       p2.width, p2.height, i + 1, n2.tri, n2.bg, n2.other,
				       n2.wrong_in, n2.wrong_out, n2.wrong_edge, n2.flipped,
				       sgxfive_render_guard_dirty(r2, &p2));
				if (!ret2 && sgxfive_render_guard_dirty(r2, &p2))
					ret2 = -EIO;
			}
			if (ret2 || wait2) {
				if (ret2 && ret2 != -EIO && !wait2)
					fail("second context render", ret2);
				else
					fail_job("second context render", wait2 ? wait2 : ret2);
				ret = wait2 ? wait2 : ret2;
				break;
			}
		}
		if (o->words_dir) {
			int wr = save_words(t, o, o->words_dir, i + 1);

			if (wr) {
				fail("--words", wr);
				ret = wr;
				break;
			}
		}
		if (geometry && !ret && !wait_err) {
			printf("tri %ux%u #%u: geometry only, the scene left open\n", p.width,
			       p.height, i + 1);
			ok++;
			continue;
		}
		print_regs(t, o);
		if (sc.bo)
			scratch_report(&sc, o->scratch_fill, o->scratch_data, o->scratch_words);
		if (z.depth.bo) {
			const struct { const char *name, *file; const struct scratch *s;
				       const struct fill *f; } zr[] = {
				{ "depth", "depth", &z.depth, &o->depth_fill },
				{ "depth store", "depth-store", &z.depth_store, &o->depth_store_fill },
				{ "stencil", "stencil", &z.stencil, &o->stencil_fill },
				{ "stencil store", "stencil-store", &z.stencil_store,
				  &o->stencil_store_fill },
			};

			for (unsigned int k = 0; k < sizeof(zr) / sizeof(zr[0]); k++) {
				if (!zr[k].s->bo)
					continue;
				depth_report(zr[k].name, zr[k].s, zr[k].f, i + 1);
				if (o->depth_dump && depth_dump(o->depth_dump, zr[k].file, zr[k].s, i + 1))
					printf("%s #%u: --depth-dump: %s\n", zr[k].name, i + 1,
					       strerror(errno));
			}
		}
		if (sgxfive_render_fb(r)) {	/* none before the first scene is built */
			struct sgxfive_tri_layout l;

			print_target(&(struct target){ p.width, p.height, p.width,
						       sgxfive_render_fb(r), tri_ok, &p },
				     sgxfive_render_guard_dirty(r, &p), o->pixels, o->pixels_rle);
			sgxfive_render_get_layout(r, &l);
			printf("layout: fb 0x%08x\n", l.fb);
		}
		/* an overflow keeps its context: --keep-overflow reports the image as it is */
		over = o->keep_overflow && (ret == -ENOSPC || wait_err == -ENOSPC);
		if (over) {
			ret = 0;
			wait_err = 0;
		}
		if (ret) {
			fail("render", ret);
			break;
		}
		ret = wait_err;
		if (ret) {
			fail_job("render", ret);
			break;
		}
		ret = sgxfive_tri_check(&p, sgxfive_render_fb(r), &n);
		guard = sgxfive_render_guard_dirty(r, &p);
		printf("tri %ux%u #%u: %s%u triangle, %u background, %u other; wrong %u inside, "
		       "%u outside, %u at edges; %u if flipped; guard %u\n", p.width, p.height,
		       i + 1, over ? "overflowed, " : "", n.tri, n.bg, n.other, n.wrong_in,
		       n.wrong_out, n.wrong_edge, n.flipped, guard);
		if (over) {		/* counted, not checked: the partial renders drew it */
			overflowed++;
			ret = 0;
			if (o->dump_each && o->dump_dir && dump_render(o->dump_dir, tri_name(i + 1), true))
				printf("tri: --dump-each: %s\n", strerror(errno));
			continue;
		}
		printf("tri %ux%u #%u: %lld us\n", p.width, p.height, i + 1,
		       (now_ns() - t0) / 1000);
		if (ret || guard) {
			if (!o->npokes)
				tri_show(&p, sgxfive_render_fb(r));
			if (o->keep_going) {
				bad = ret ? ret : -EIO;
				ret = 0;
				continue;
			}
			ret = ret ? ret : -EIO;
			break;
		}
		if (o->dump_each && o->dump_dir && dump_render(o->dump_dir, tri_name(i + 1), false))
			printf("tri: --dump-each: %s\n", strerror(errno));
		ok++;
	}
	/* what the TA wrote for the last scene, before the context goes */
	if (!ret && o->dump_dir) {
		ret = dump_render(o->dump_dir, "tri", false);
		if (ret)
			fail("--dump-render", ret);
	}
	if (!ret && bad) {
		ret = bad;
		printf("tri: %u of %u renders ok\n", ok, o->n);
	} else if (!ret && overflowed) {
		printf("tri: %u of %u renders ok, %u overflowed\n", ok, o->n, overflowed);
	} else if (!ret) {
		printf("tri: %u renders ok\n", ok);
	} else {
		printf("tri: FAILED after %u renders\n", ok);
	}
out:
	/*
	 * the second context first: it may run on the first's parameter buffer; --close-first
	 * closes the first (the donor of a shared one) before it, the kernel's reference on the
	 * donor keeping the buffer until the second goes. The kernel's contexts are the ones
	 * closed in that order (ctx, ctx2); the render objects only unmap the client's pages.
	 */
	first_first = o->close_first || early_closed;
	sgxfive_render_destroy(r2);
	sgxfive_render_destroy(r);
	scratch_destroy(vm, &sc);
	scratch_destroy(vm, &z.depth);
	scratch_destroy(vm, &z.depth_store);
	scratch_destroy(vm, &z.stencil);
	scratch_destroy(vm, &z.stencil_store);
	if (r2 && early_closed)
		printf("tri: closing the second context\n");
	else if (r2)
		printf("tri: closing the %s context before the %s\n", first_first ? "first" :
		       "second", first_first ? "second" : "first");
	if (first_first && ctx)
		sgxfive_ctx_destroy(t->dev, ctx);
	if (r2 && first_first && o->close_trace)
		close_trace("after closing the first context");
	if (ctx2)
		sgxfive_ctx_destroy(t->dev, ctx2);
	if (r2 && !first_first && o->close_trace)
		close_trace("after closing the second context");
	if (!first_first && ctx)
		sgxfive_ctx_destroy(t->dev, ctx);
	if (r2 && o->close_trace) {
		close_trace(first_first ? "after closing the second context" :
			    "after closing the first context");
		usleep(500000);	/* a deferred release may run the donor's cleanup */
		close_trace("500 ms after both are closed");
	}
	sgxfive_vm_destroy(vm);
	return ret ? 1 : 0;
}

/* ---- contexts ----------------------------------------------------------------------- */

/* MemFree and, on a 32-bit kernel with highmem, LowFree in KiB; -1 if absent. */
static void meminfo(long long *mem_free, long long *low_free)
{
	FILE *f = fopen("/proc/meminfo", "r");
	char line[128];

	*mem_free = *low_free = -1;
	if (!f)
		return;
	while (fgets(line, sizeof(line), f)) {
		sscanf(line, "MemFree: %lld kB", mem_free);
		sscanf(line, "LowFree: %lld kB", low_free);
	}
	fclose(f);
}

/*
 * The memory render contexts pin:
 * n render contexts for targets up to W x H in one VM, /proc/meminfo before
 * and after creating them. Other activity on the machine shows up too, so
 * compare runs, not single numbers.
 */
static int cmd_contexts(struct tool *t, const struct opts *o)
{
	uint32_t ctxs[64], n = 0;
	long long free0, low0, free1, low1;
	struct sgxfive_vm *vm = NULL;
	int ret;

	if (o->n > sizeof(ctxs) / sizeof(ctxs[0]))
		return fail("contexts", -E2BIG);
	ret = sgxfive_vm_create(t->dev, &vm);
	if (ret)
		return fail("vm", ret);
	meminfo(&free0, &low0);
	for (; n < o->n; n++) {
		ret = sgxfive_render_ctx_create(vm, o->width, o->height, &ctxs[n]);
		if (ret) {
			char what[32];

			snprintf(what, sizeof(what), "render context %u", n + 1);
			fail(what, ret);
			break;
		}
	}
	meminfo(&free1, &low1);
	if (!ret) {
		printf("contexts: %u render contexts for targets up to %ux%u: ", n, o->width,
		       o->height);
		if (free0 < 0 || free1 < 0)
			printf("no /proc/meminfo\n");
		else
			printf("MemFree -%lld KiB (%lld KiB each)%s", free0 - free1,
			       n ? (free0 - free1) / n : 0, low0 < 0 || low1 < 0 ? "\n" : ", ");
		if (free0 >= 0 && free1 >= 0 && low0 >= 0 && low1 >= 0)
			printf("LowFree -%lld KiB (%lld KiB each)\n", low0 - low1,
			       n ? (low0 - low1) / n : 0);
	}
	while (n)
		sgxfive_ctx_destroy(t->dev, ctxs[--n]);
	sgxfive_vm_destroy(vm);
	if (!ret)
		printf("contexts: destroyed\n");
	return ret ? 1 : 0;
}

static bool parse_u32(const char *s, uint32_t *v)
{
	char *end;
	unsigned long long x;

	errno = 0;
	x = strtoull(s, &end, 0);
	if (errno || !*s || *end || x > 0xffffffffull)
		return false;
	*v = (uint32_t)x;
	return true;
}

/* --regs LO-HI: dword-aligned offsets in the register bank, LO <= HI. */
static bool parse_regs(const char *s, struct opts *o)
{
	const char *dash = strchr(s, '-');
	char lo[24];

	if (!dash || dash == s || (size_t)(dash - s) >= sizeof(lo))
		return false;
	memcpy(lo, s, (size_t)(dash - s));
	lo[dash - s] = 0;
	if (!parse_u32(lo, &o->regs_lo) || !parse_u32(dash + 1, &o->regs_hi))
		return false;
	o->regs = true;
	return !(o->regs_lo % 4) && !(o->regs_hi % 4) && o->regs_lo <= o->regs_hi &&
	       o->regs_hi < REGS_SIZE;
}

/* A fill: a value, "index" or "bit:K" (K 0 to 31). */
static bool parse_fill(const char *s, struct fill *f)
{
	uint32_t k;

	f->given = true;
	if (!strcmp(s, "index")) {
		f->mode = FILL_INDEX;
		return true;
	}
	if (!strncmp(s, "bit:", 4)) {
		if (!parse_u32(s + 4, &k) || k > 31)
			return false;
		f->mode = FILL_BIT;
		f->val = k;
		return true;
	}
	f->mode = FILL_VALUE;
	return parse_u32(s, &f->val);
}

/* --tri-z A,B,C: three screen depths, 0 to 1 */
static bool parse_tri_z(const char *s, float z[3])
{
	char *end;

	for (int i = 0; i < 3; i++) {
		errno = 0;
		z[i] = strtof(s, &end);
		if (errno || end == s || !(z[i] >= 0.0f && z[i] <= 1.0f) ||
		    *end != (i < 2 ? ',' : 0))
			return false;
		s = end + 1;
	}
	return true;
}

/* --tri-v X0,Y0,X1,Y1,X2,Y2: six integers, window coordinates in 1/256 pixel (below 2^22) */
static bool parse_tri_v(const char *s, int32_t v[3][2])
{
	char *end;

	for (int i = 0; i < 6; i++) {
		long long x;

		errno = 0;
		x = strtoll(s, &end, 10);
		if (errno || end == s || x < -(1 << 30) || x >= (1 << 30) ||
		    *end != (i < 5 ? ',' : 0))
			return false;
		v[i / 2][i % 2] = (int32_t)x;
		s = end + 1;
	}
	return true;
}

static int parse_opts(int argc, char **argv, struct opts *o)
{
	static const char *const fills[] = {
		"--depth-fill", "--depth-store-fill", "--stencil-fill", "--stencil-store-fill",
	};
	struct fill *const fillp[] = { &o->depth_fill, &o->depth_store_fill, &o->stencil_fill,
				       &o->stencil_store_fill };

	static const struct { const char *name; size_t off; } names[] = {
		{ "--width", offsetof(struct opts, width) },
		{ "--height", offsetof(struct opts, height) },
		{ "--x", offsetof(struct opts, x) }, { "--y", offsetof(struct opts, y) },
		{ "--dx", offsetof(struct opts, x) }, { "--dy", offsetof(struct opts, y) },
		{ "--stride", offsetof(struct opts, stride) },
		{ "--dst-stride", offsetof(struct opts, dst_stride) },
		{ "--src-stride", offsetof(struct opts, src_stride) },
		{ "--sx", offsetof(struct opts, sx) }, { "--sy", offsetof(struct opts, sy) },
		{ "--colour", offsetof(struct opts, colour) },
		{ "-n", offsetof(struct opts, n) },
		{ "--max-width", offsetof(struct opts, max_width) },
		{ "--max-height", offsetof(struct opts, max_height) },
		{ "--scratch", offsetof(struct opts, scratch) },
		{ "--scratch-fill", offsetof(struct opts, scratch_fill) },
		{ "--scratch-at", offsetof(struct opts, scratch_at) },
		{ "--depth-base", offsetof(struct opts, depth_base) },
		{ "--depth-ctl", offsetof(struct opts, depth_ctl) },
		{ "--depth-ctl-next", offsetof(struct opts, depth_ctl_next) },
		{ "--depth-pages", offsetof(struct opts, depth_pages) },
	};

	for (int i = 0; i < argc; i += 2) {
		bool ok = false;

		if (!strcmp(argv[i], "--keep-going")) {
			o->keep_going = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--keep-overflow") || !strcmp(argv[i], "--dump-each") ||
		    !strcmp(argv[i], "--depth")) {
			*(argv[i][2] == 'k' ? &o->keep_overflow : argv[i][2] == 'd' && argv[i][3] == 'u' ?
			  &o->dump_each : &o->depth) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--depth-store") || !strcmp(argv[i], "--stencil") ||
		    !strcmp(argv[i], "--stencil-store") || !strcmp(argv[i], "--tri-full")) {
			*(!strcmp(argv[i], "--tri-full") ? &o->tri_full :
			  !strcmp(argv[i], "--depth-store") ? &o->depth_store :
			  !strcmp(argv[i], "--stencil-store") ? &o->stencil_store : &o->stencil) = true;
			o->zgiven |= argv[i][2] != 't';
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--tri-unit") && i + 1 < argc) {
			char *end;
			unsigned long k = strtoul(argv[i + 1], &end, 10);

			if (!*argv[i + 1] || *end || k < 5 || k > 20) {
				fprintf(stderr, "sgxfive-test: bad option --tri-unit (5 to 20: --tri-v is in "
					"1/2^K pixel)\n");
				return -1;
			}
			o->tri_unit = (uint32_t)k;
			continue;
		}
		if (!strcmp(argv[i], "--tri-v") && i + 1 < argc) {
			if (!parse_tri_v(argv[i + 1], o->tri_v)) {
				fprintf(stderr, "sgxfive-test: bad option --tri-v (six integers, window "
					"coordinates in 1/256 pixel, comma separated)\n");
				return -1;
			}
			o->tri_v_given = true;
			continue;
		}
		if (!strcmp(argv[i], "--tri-z") && i + 1 < argc) {
			if (!parse_tri_z(argv[i + 1], o->tri_z)) {
				fprintf(stderr, "sgxfive-test: bad option --tri-z (three screen depths, 0 "
					"to 1, comma separated)\n");
				return -1;
			}
			o->tri_z_given = true;
			continue;
		}
		for (size_t k = 0; k < sizeof(fills) / sizeof(fills[0]); k++) {
			if (strcmp(argv[i], fills[k]))
				continue;
			if (i + 1 >= argc || !parse_fill(argv[i + 1], fillp[k])) {
				fprintf(stderr, "sgxfive-test: bad option %s (a value, index or bit:K, K "
					"0 to 31)\n", argv[i]);
				return -1;
			}
			o->zgiven |= k > 1 || k == 1;
			o->depth_given |= k == 0;
			ok = true;
		}
		if (ok)
			continue;
		if (!strcmp(argv[i], "--depth-dump") && i + 1 < argc) {
			o->depth_dump = argv[i + 1];
			o->depth_given = true;
			continue;
		}
		if (!strcmp(argv[i], "--wait-second")) {
			o->wait_second = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--close-first-early") || !strcmp(argv[i], "--words-between")) {
			*(argv[i][2] == 'c' ? &o->close_early : &o->words_between) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--close-first") || !strcmp(argv[i], "--close-trace")) {
			*(argv[i][8] == 'f' ? &o->close_first : &o->close_trace) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--ctx2") || !strcmp(argv[i], "--share-pb") ||
		    !strcmp(argv[i], "--overlap")) {
			*(argv[i][2] == 'c' ? &o->ctx2 : argv[i][2] == 's' ? &o->share_pb :
			  &o->overlap) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--scratch-file") && i + 1 < argc) {
			/* FILE: dwords for the scratch buffer's start (checked against --scratch later) */
			FILE *f = fopen(argv[i + 1], "rb");
			long len = -1;

			if (f && !fseek(f, 0, SEEK_END))
				len = ftell(f);
			if (!f || len <= 0 || len % 4 || fseek(f, 0, SEEK_SET)) {
				fprintf(stderr, "sgxfive-test: bad --scratch-file %s (a readable file of "
					"4 to 4n bytes)\n", argv[i + 1]);
				if (f)
					fclose(f);
				return -1;
			}
			free(o->scratch_data);
			o->scratch_data = malloc((size_t)len);
			if (!o->scratch_data || fread(o->scratch_data, 4, (size_t)len / 4, f) !=
			    (size_t)len / 4) {
				fprintf(stderr, "sgxfive-test: --scratch-file %s: read failed\n",
					argv[i + 1]);
				fclose(f);
				return -1;
			}
			fclose(f);
			o->scratch_words = (uint32_t)len / 4;
			continue;
		}
		if (!strcmp(argv[i], "--print-addrs") || !strcmp(argv[i], "--page-before")) {
			*(argv[i][2] == 'p' && argv[i][3] == 'r' ? &o->print_addrs : &o->page_before) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--ramp") && i + 1 < argc) {
			/* CH=START: CH one of a, r, g, b (ARGB8888's byte 3 to 0) */
			static const char names[] = "bgra";
			const char *ch = strchr(names, argv[i + 1][0] ? argv[i + 1][0] : '?');
			char *end;
			unsigned long v;

			if (!ch || argv[i + 1][1] != '=' || o->ramp ||
			    (v = strtoul(argv[i + 1] + 2, &end, 0)) > 255 || *end || !argv[i + 1][2]) {
				fprintf(stderr, "sgxfive-test: bad --ramp %s (a, r, g or b = 0 to 255)\n",
					argv[i + 1]);
				return -1;
			}
			o->ramp = true;
			o->ramp_shift = (uint32_t)(ch - names) * 8;
			o->ramp_start = (uint32_t)v;
			continue;
		}
		if (!strcmp(argv[i], "--ramp-base") && i + 1 < argc) {
			if (!parse_u32(argv[i + 1], &o->ramp_base)) {
				fprintf(stderr, "sgxfive-test: bad --ramp-base %s\n", argv[i + 1]);
				return -1;
			}
			continue;
		}
		if (!strcmp(argv[i], "--pixels-rle")) {
			o->pixels_rle = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--fault") || !strcmp(argv[i], "--pixels") ||
		    !strcmp(argv[i], "--every-value")) {
			*(argv[i][2] == 'f' ? &o->fault :
			  argv[i][2] == 'p' ? &o->pixels : &o->every_value) = true;
			i--;		/* a flag: no value */
			continue;
		}
		if (!strcmp(argv[i], "--poke") && i + 1 < argc) {
			if (o->npokes == SGXFIVE_POKE_MAX ||
			    sgxfive_poke_parse(argv[i + 1], &o->pokes[o->npokes])) {
				fprintf(stderr, "sgxfive-test: bad poke %s\n", argv[i + 1]);
				return -1;
			}
			o->poke_args[o->npokes++] = argv[i + 1];
			continue;
		}
		if ((!strcmp(argv[i], "--kpoke-render") || !strcmp(argv[i], "--kpoke-render2")) &&
		    i + 1 < argc) {
			const bool second = argv[i][strlen(argv[i]) - 1] == '2';
			char *end;
			unsigned long n = strtoul(argv[i + 1], &end, 0);

			if (o->nkpr == KPR_MAX || end == argv[i + 1] || *end != ':' || !end[1]) {
				fprintf(stderr, "sgxfive-test: bad %s %s (N:SPEC)\n", argv[i],
					argv[i + 1]);
				return -1;
			}
			o->kpr[o->nkpr].n = (uint32_t)n;
			o->kpr[o->nkpr].second = second;
			o->kpr[o->nkpr++].spec = end + 1;
			continue;
		}
		if ((!strcmp(argv[i], "--kreg-render") || !strcmp(argv[i], "--kreg-render2") ||
		     !strcmp(argv[i], "--kpoke-job")) && i + 1 < argc) {
			const bool job = !strcmp(argv[i], "--kpoke-job");
			const bool second = argv[i][strlen(argv[i]) - 1] == '2';
			char *end;
			unsigned long n = strtoul(argv[i + 1], &end, 0);

			if (o->nkpr == KPR_MAX || end == argv[i + 1] || *end != ':' || !end[1]) {
				fprintf(stderr, "sgxfive-test: bad %s %s (N:%s)\n", argv[i], argv[i + 1],
					job ? "SPEC" : "OFFSET=VALUE");
				return -1;
			}
			o->kpr[o->nkpr].n = (uint32_t)n;
			o->kpr[o->nkpr].second = second;
			o->kpr[o->nkpr].job = job;
			o->kpr[o->nkpr].reg = !job;
			o->kpr[o->nkpr++].spec = end + 1;
			continue;
		}
		if (!strcmp(argv[i], "--geometry") && i + 1 < argc) {
			uint32_t n;

			if (!parse_u32(argv[i + 1], &n) || !n || n > 32) {
				fprintf(stderr, "sgxfive-test: bad --geometry %s\n", argv[i + 1]);
				return -1;
			}
			o->geometry |= 1u << (n - 1);
			continue;
		}
		if (!strcmp(argv[i], "--dump-render") && i + 1 < argc) {
			o->dump_dir = argv[i + 1];	/* i += 2 below */
			continue;
		}
		if (!strcmp(argv[i], "--words") && i + 1 < argc) {
			o->words_dir = argv[i + 1];
			continue;
		}
		if (!strcmp(argv[i], "--wait-ms") && i + 1 < argc) {
			if (!parse_u32(argv[i + 1], &o->wait_ms) || !o->wait_ms ||
			    o->wait_ms > 600000) {
				fprintf(stderr, "sgxfive-test: bad --wait-ms %s (1 to 600000)\n",
					argv[i + 1]);
				return -1;
			}
			continue;
		}
		if (!strcmp(argv[i], "--move") && i + 1 < argc) {
			char *end, *e2;
			unsigned long n = strtoul(argv[i + 1], &end, 0);
			long dx, dy;

			if (o->nmoves == KPR_MAX || end == argv[i + 1] || *end != ':')
				goto bad_move;
			dx = strtol(end + 1, &e2, 0);
			if (e2 == end + 1 || *e2 != ',')
				goto bad_move;
			dy = strtol(e2 + 1, &end, 0);
			if (end == e2 + 1 || *end)
				goto bad_move;
			o->moves[o->nmoves].n = (uint32_t)n;
			o->moves[o->nmoves].dx = (int32_t)dx;
			o->moves[o->nmoves++].dy = (int32_t)dy;
			continue;
bad_move:
			fprintf(stderr, "sgxfive-test: bad --move %s (N:DX,DY)\n", argv[i + 1]);
			return -1;
		}
		if (!strcmp(argv[i], "--regs") && i + 1 < argc) {
			if (!parse_regs(argv[i + 1], o)) {
				fprintf(stderr, "sgxfive-test: bad register range %s (LO-HI, "
					"dword-aligned, below 0x%x)\n", argv[i + 1], REGS_SIZE);
				return -1;
			}
			continue;
		}
		for (size_t k = 0; k < sizeof(names) / sizeof(names[0]) && !ok; k++)
			if (!strcmp(argv[i], names[k].name) && i + 1 < argc)
				ok = parse_u32(argv[i + 1],
					       (uint32_t *)((char *)o + names[k].off));
		if (!ok) {
			fprintf(stderr, "sgxfive-test: bad option %s\n", argv[i]);
			return -1;
		}
		o->depth_given |= !strncmp(argv[i], "--depth-", 8);
	}
	return 0;
}

/* Every poke against the job's layout: a space it has, an index inside it. */
static int check_pokes(const struct tool *t, const char *cmd, const struct opts *o)
{
	struct sgxfive_poke_view v[SGXFIVE_POKE_VIEWS_MAX];
	const struct sgxfive_poke_view *got;
	const bool tri = !strcmp(cmd, "tri");
	const unsigned int nv = tri ? sgxfive_render_poke_layout(v) :
			       sgxfive_xfer_poke_layout(t->progs, !strcmp(cmd, "copy"), v);

	for (unsigned int i = 0; i < o->npokes; i++) {
		const struct sgxfive_poke *pk = &o->pokes[i];
		int ret = sgxfive_poke_find(v, nv, pk, &got);

		if (ret == -ENOENT) {
			fprintf(stderr, "sgxfive-test: --poke %s: a %s job has no %s%s%s\n",
				o->poke_args[i], cmd, sgxfive_poke_space_name(pk->space),
				pk->slot[0] ? ":" : "", pk->slot);
			return -1;
		}
		if (ret) {
			for (unsigned int k = 0; k < nv; k++)
				if (v[k].space == pk->space &&
				    (!v[k].slot || !strcmp(v[k].slot, pk->slot)))
					got = &v[k];
			fprintf(stderr, "sgxfive-test: --poke %s: index %u out of range (%u "
				"words)\n", o->poke_args[i], pk->index, got->count);
			return -1;
		}
	}
	return 0;
}

int main(int argc, char **argv)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	struct opts o = {
		.width = 64, .height = 32, .stride = 256, .colour = 0xff336699,
		.src_stride = 256, .dst_stride = 256, .n = 8,
		.max_width = UINT32_MAX, .max_height = UINT32_MAX,
		.scratch_fill = 0x3e800000,	/* 0.25f */
		.depth_fill = { FILL_VALUE, 0x3f800000, false },	/* 1.0f */
		.depth_store_fill = { FILL_VALUE, 0xdeadbeef, false },
		.stencil_fill = { FILL_VALUE, 0xdeadbeef, false },
		.stencil_store_fill = { FILL_VALUE, 0xdeadbeef, false },
		.depth_base = 0x3e000000,	/* rd:1, the ZLS base: the general heap's */
		.depth_ctl = 0x0017100c,	/* a clearing frame that stores */
		.depth_pages = UINT32_MAX,	/* the target's, and sixteen over */
	};
	struct sgxfive_mock_config mcfg = { 0 };
	const char *device = NULL, *cmd;
	char *pb_end;
	bool use_mock = false, needs_programs, fake = false;
	struct tool t = { 0 };
	struct probe_file *probes = NULL;
	static struct probe_opts popts = { .temps = 32, .tri.slot = -1, .place_form = -1 };
	uint32_t nprobes = 0;
	int i = 1, ret;

	for (; i < argc && !strncmp(argv[i], "--", 2); i++) {
		if (!strcmp(argv[i], "--mock") || !strcmp(argv[i], "--mock=rev1")) {
			use_mock = true;
		} else if (!strcmp(argv[i], "--mock=harness")) {
			use_mock = true;
			mcfg.layout = SGXFIVE_MOCK_LAYOUT_HARNESS;
		} else if (!strcmp(argv[i], "--mock=none")) {
			use_mock = true;
			mcfg.no_sgxfive = true;
		} else if (!strcmp(argv[i], "--programs=asm")) {
			fake = false;
		} else if (!strcmp(argv[i], "--programs=fake")) {
			fake = true;
		} else if (!strncmp(argv[i], "--mock-pb-pages=", 16)) {
			mcfg.render_pb_pages = strtoul(argv[i] + 16, &pb_end, 0);
			if (*pb_end || pb_end == argv[i] + 16 || mcfg.render_pb_pages < 0x23 ||
			    mcfg.render_pb_pages > 0x422)
				return usage();
		} else if (!strcmp(argv[i], "--device") && i + 1 < argc) {
			device = argv[++i];
		} else {
			return usage();
		}
	}
	if (i >= argc || (mcfg.render_pb_pages && !use_mock))
		return usage();
	cmd = argv[i++];
	if (strcmp(cmd, "query") && strcmp(cmd, "dummy") && strcmp(cmd, "fill") &&
	    strcmp(cmd, "copy") && strcmp(cmd, "isolation") && strcmp(cmd, "regaccess") &&
	    strcmp(cmd, "tri") && strcmp(cmd, "contexts") && strcmp(cmd, "probe"))
		return usage();
	if (!strcmp(cmd, "probe")) {
		for (; i < argc && !strncmp(argv[i], "--", 2); i++) {
			char *end;
			unsigned long v;

			if (!strcmp(argv[i], "--coords")) {
				popts.coords = true;
				continue;
			}
			if (!strcmp(argv[i], "--pixels")) {
				popts.pixels = true;
				continue;
			}
			if (!strcmp(argv[i], "--scratch-pages") && i + 1 < argc) {
				/* 16 to 64 pages: a texture chain that does not fit 64 KiB */
				v = strtoul(argv[++i], &end, 0);
				if (*end || v < 16 || v > 64)
					return usage();
				scratch_pages = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--low") && i + 1 < argc) {
				/* a page of the first MiB, page 0 excepted; room for the scratch is
				 * checked after the options, when --scratch-pages is known */
				v = strtoul(argv[++i], &end, 0);
				if (*end || v < SGXFIVE_PAGE_SIZE || v % SGXFIVE_PAGE_SIZE ||
				    v >= 0x100000)
					return usage();
				popts.low = v;
				continue;
			}
			if (!strcmp(argv[i], "--late") && i + 1 < argc) {
				/* R:K=V, two distinct dwords of the scratch and a 32-bit value */
				/* the dwords' bound is checked after the options (--scratch-pages) */
				unsigned long long r, k, val;
				int used = -1;

				if (sscanf(argv[++i], "%lli:%lli=%lli%n", &r, &k, &val, &used) != 3 ||
				    argv[i][used] || r >= UINT32_MAX || k >= UINT32_MAX || r == k ||
				    val > 0xffffffffULL)
					return usage();
				popts.late = true;
				popts.late_ready = (uint32_t)r;
				popts.late_dword = (uint32_t)k;
				popts.late_value = (uint32_t)val;
				continue;
			}
			if (!strcmp(argv[i], "--poke") && i + 1 < argc) {
				/* the fill's transfer command (42 dwords) or background object */
				struct sgxfive_poke *pk = &popts.pokes[popts.npokes];

				if (popts.npokes == SGXFIVE_POKE_MAX ||
				    sgxfive_poke_parse(argv[i + 1], pk) ||
				    !((pk->space == SGXFIVE_POKE_XFER && pk->index < 42) ||
				      (pk->space == SGXFIVE_POKE_BG &&
				       pk->index < SGXFIVE_BGOBJ_DWORDS))) {
					fprintf(stderr, "sgxfive-test: probe --poke %s: xfer:0-41 "
						"or bg:0-16 only\n", argv[i + 1]);
					return 2;
				}
				popts.poke_args[popts.npokes++] = argv[++i];
				continue;
			}
			if (!strcmp(argv[i], "--stamp")) {
				probe_stamp = true;
				continue;
			}
			if (!strcmp(argv[i], "--tri") && i + 1 < argc) {
				if (probe_tri_slot(argv[++i], &popts.tri.slot, &popts.tri.data))
					return usage();
				continue;
			}
			if (!strcmp(argv[i], "--slot") && i + 1 < argc) {
				ret = probe_tri_fixed(argv[++i], &popts.tri);
				if (ret)
					return ret;
				continue;
			}
			if (!strcmp(argv[i], "--vertices") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				/* whole triangles that fit the (wide) vertex buffer */
				if (*end || !v || v % 3 || v > SGXFIVE_TRI_PROBE_WIDE_VERTICES)
					return usage();
				popts.tri.vertices = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--dump-render") && i + 1 < argc) {
				popts.tri.dump_dir = argv[++i];
				continue;
			}
			if (!strcmp(argv[i], "--kpoke") && i + 1 < argc) {
				if (popts.tri.nkpoke == KPR_MAX)
					return usage();
				popts.tri.kpoke[popts.tri.nkpoke++] = argv[++i];
				continue;
			}
			if (!strcmp(argv[i], "--obj2") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				if (*end || !v || v >= SGXFIVE_TRI_PROBE_MAX_VERTICES)
					return usage();
				popts.tri.obj2 = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--obj2-blk") && i + 1 < argc) {
				char *eq;
				unsigned long n;

				n = strtoul(argv[++i], &eq, 0);
				if (*eq != '=' || eq == argv[i] || n >= SGXFIVE_TRI_PROBE_BLK2_WORDS ||
				    !eq[1])
					return usage();
				v = strtoul(eq + 1, &end, 0);
				if (*end || v > UINT32_MAX)
					return usage();
				popts.tri.obj2_blk_mask |= 1u << n;
				popts.tri.obj2_blk_val[n] = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--obj2-pixel") && i + 1 < argc) {
				if (popts.tri.obj2_pixel.n || probe_read(argv[++i], &popts.tri.obj2_pixel, 8))
					return usage();
				continue;
			}
			if (!strcmp(argv[i], "--obj2-pixpds") && i + 1 < argc) {
				/* FILE:N, N data dwords (whole rows of four) before its code */
				char path[4096], *colon, *dend;
				unsigned long nd;

				if (popts.tri.obj2_pixpds.n || strlen(argv[++i]) >= sizeof(path))
					return usage();
				snprintf(path, sizeof(path), "%s", argv[i]);
				colon = strrchr(path, ':');
				if (!colon || !colon[1])
					return usage();
				nd = strtoul(colon + 1, &dend, 0);
				if (*dend || nd < 4 || nd % 4 || nd > 128)
					return usage();
				*colon = 0;
				if (probe_read(path, &popts.tri.obj2_pixpds, 4))
					return 1;
				if (popts.tri.obj2_pixpds.n <= nd) {
					fprintf(stderr, "sgxfive-test: %s: no code after %lu data dwords\n",
						path, nd);
					return 1;
				}
				popts.tri.obj2_pixpds_data = (uint32_t)nd;
				continue;
			}
			if (!strcmp(argv[i], "--copy-depth")) {
				popts.tri.copy_depth = true;
				continue;
			}
			if (!strcmp(argv[i], "--tri-full")) {
				popts.tri.full = true;
				continue;
			}
			if (!strcmp(argv[i], "--tri-unit") && i + 1 < argc) {
				char *end;
				unsigned long k = strtoul(argv[++i], &end, 10);

				if (!*argv[i] || *end || k < 5 || k > 20) {
					fprintf(stderr, "sgxfive-test: bad option --tri-unit (5 to 20: --tri-v "
						"is in 1/2^K pixel)\n");
					return 2;
				}
				popts.tri.unit = (uint32_t)k;
				continue;
			}
			if (!strcmp(argv[i], "--tri-v") && i + 1 < argc) {
				if (!parse_tri_v(argv[++i], popts.tri.v256)) {
					fprintf(stderr, "sgxfive-test: bad option --tri-v (six integers, "
						"window coordinates in 1/256 pixel, comma separated)\n");
					return 2;
				}
				popts.tri.v_set = true;
				continue;
			}
			if (!strcmp(argv[i], "--tri-z") && i + 1 < argc) {
				if (!parse_tri_z(argv[++i], popts.tri.z)) {
					fprintf(stderr, "sgxfive-test: bad option --tri-z (three screen "
						"depths, 0 to 1, comma separated)\n");
					return 2;
				}
				popts.tri.z_set = true;
				continue;
			}
			if ((!strcmp(argv[i], "--blk") || !strcmp(argv[i], "--cmd") ||
			     !strcmp(argv[i], "--vdm")) && i + 1 < argc) {
				/* N=V sets word N, N^=V flips the bits of V in it */
				const char which = argv[i][2];
				struct probe_tri *pt = &popts.tri;
				uint32_t *mask, *xmask, *val, *xval;
				unsigned long limit, n;
				bool flip;

				if (which == 'b') {
					mask = &pt->blk_mask, xmask = &pt->blk_xor_mask;
					val = pt->blk_val, xval = pt->blk_xor_val;
					limit = SGXFIVE_TRI_BLOCK_WORDS;
				} else if (which == 'c') {
					mask = &pt->cmd_mask, xmask = &pt->cmd_xor_mask;
					val = pt->cmd_val, xval = pt->cmd_xor_val;
					limit = SGXFIVE_TRI_PROBE_CMD_WORDS;
				} else {
					mask = &pt->vdm_mask, xmask = &pt->vdm_xor_mask;
					val = pt->vdm_val, xval = pt->vdm_xor_val;
					limit = SGXFIVE_TRI_PROBE_VDM2_WORDS;
				}
				if (probe_word_arg(argv[++i], limit, &n, &flip, &v))
					return usage();
				if (flip) {
					*xmask |= 1u << n;
					xval[n] = (uint32_t)v;
				} else {
					*mask |= 1u << n;
					val[n] = (uint32_t)v;
				}
				continue;
			}
			if (!strcmp(argv[i], "--pbe") && i + 1 < argc) {
				unsigned long n;
				bool flip;

				if (probe_word_arg(argv[++i], 4, &n, &flip, &v) || flip)
					return usage();
				popts.tri.pbe_mask |= 1u << n;
				popts.tri.pbe_val[n] = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--blk-add") && i + 1 < argc) {
				/* bits 2-5 one word, 7 two */
				char *eq, *p;
				unsigned long bit = strtoul(argv[++i], &eq, 0);
				unsigned int n, want;

				if (*eq != '=' || eq == argv[i] || !((bit >= 2 && bit <= 5) || bit == 7))
					return usage();
				want = bit == 7 ? 2 : 1;
				for (n = 0, p = eq + 1; n < want; n++, p = end + 1) {
					v = strtoul(p, &end, 0);
					if (end == p || v > UINT32_MAX ||
					    (n + 1 < want ? *end != ',' : *end != '\0'))
						return usage();
					popts.tri.add_val[bit][n] = (uint32_t)v;
				}
				popts.tri.add_mask |= 1u << bit;
				continue;
			}
			if (!strcmp(argv[i], "--isp2") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				if (*end || end == argv[i] || v > UINT32_MAX)
					return usage();
				popts.tri.isp2_set = true;
				popts.tri.isp2 = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--sideband") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				if (*end || end == argv[i] || v > UINT32_MAX)
					return usage();
				popts.tri.sideband_set = true;
				popts.tri.sideband = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--vtx-coords") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				/* the vertex size field: 4 position dwords + N, at most 15 */
				if (*end || !v || v > 11)
					return usage();
				popts.tri.coords = (uint32_t)v;
				continue;
			}
			if (probe_tri_size(argv[i], i + 1 < argc ? argv[i + 1] : NULL, &popts.tri)) {
				i++;
				continue;
			}
			if (!strcmp(argv[i], "--scratch-heap") && i + 1 < argc) {
				/* the scratch buffer in the texture heap (a texture's own region) */
				if (strcmp(argv[++i], "texture"))
					return usage();
				popts.scratch_texture = true;
				continue;
			}
			if (!strcmp(argv[i], "--place-form") && i + 1 < argc) {
				/* how the placed program's DOUTU is written */
				const char *f = argv[++i];

				if (!strcmp(f, "cbase"))
					popts.place_form = 0;
				else if (!strcmp(f, "exe18"))
					popts.place_form = 1;
				else
					return usage();
				continue;
			}
			if (!strcmp(argv[i], "--place") && i + 1 < argc) {
				/* OFFSET=FILE: a USE program at the code heap's base + OFFSET */
				const char *arg = argv[++i];

				v = strtoul(arg, &end, 0);
				if (*end != '=' || end == arg || v % 8 || v + SGXFIVE_PAGE_SIZE > 0x500000 ||
				    popts.place.n || probe_read(end + 1, &popts.place, 8))
					return usage();
				popts.place_off = (uint32_t)v;
				continue;
			}
			if (!strcmp(argv[i], "--use") && i + 1 < argc) {
				if (probe_read(argv[++i], &popts.use, 8))
					return 1;
				continue;
			}
			if (!strcmp(argv[i], "--pds") && i + 1 < argc) {
				v = strtoul(argv[++i], &end, 0);
				/* whole rows of four dwords; row 0 holds U0-U2 */
				if (*end || v < 4 || v % 4 || v > 128)
					return usage();
				popts.pds_data = (uint32_t)v;
				continue;
			}
			if (strcmp(argv[i], "--temps") || i + 1 >= argc)
				return usage();
			v = strtoul(argv[++i], &end, 0);
			if (*end || v < 1 || v > 128)
				return usage();
			popts.temps = (uint32_t)v;
		}
		/* --low and --late address the scratch buffer, whose size --scratch-pages sets, so
		 * they are checked here, whatever the order of the options */
		if (popts.low && popts.low + SCRATCH_PAGES * SGXFIVE_PAGE_SIZE > 0x100000)
			return usage();
		if (popts.late && (popts.late_ready >= SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4 ||
				   popts.late_dword >= SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4))
			return usage();
		if (i >= argc || (popts.pds_data && !popts.use.n) ||
		    (popts.place.n && popts.place_form < 0) || (!popts.place.n && popts.place_form >= 0) ||
		    ((popts.place.n || popts.scratch_texture) && popts.tri.slot >= 0) ||
		    probe_tri_check(&popts))
			return usage();
		nprobes = (uint32_t)(argc - i);
		probes = calloc(nprobes, sizeof(*probes));
		if (!probes)
			return fail("probe", -ENOMEM);
		for (uint32_t k = 0; k < nprobes; k++) {
			const bool tri_pds = popts.tri.slot >= 0 &&
					     sgxfive_tri_slot_is_pds(popts.tri.slot);
			const uint32_t data = tri_pds ? popts.tri.data : popts.pds_data;

			if (probe_read(argv[i + k], &probes[k], popts.pds_data || tri_pds ? 4 : 8) ||
			    (data && probes[k].n <= data)) {
				free(probes);
				return 1;
			}
		}
		i = argc;
	}
	if (!strcmp(cmd, "tri")) {
		o.height = 64;			/* the first triangle's 64 x 64 */
		o.n = 1;
	}
	if (!strcmp(cmd, "contexts")) {
		o.height = 64;			/* 32 contexts for 64 x 64 targets */
		o.n = 32;
	}
	if (parse_opts(argc - i, argv + i, &o))
		return 2;
	if ((o.npokes || o.pixels || o.regs) && strcmp(cmd, "fill") && strcmp(cmd, "copy") &&
	    strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --poke, --pixels and --regs are for fill, copy "
			"and tri\n");
		return 2;
	}
	if (o.scratch_words && (strcmp(cmd, "tri") || !o.scratch ||
				o.scratch_words > o.scratch * (SGXFIVE_PAGE_SIZE / 4))) {
		fprintf(stderr, "sgxfive-test: --scratch-file is for tri with --scratch N, and "
			"must fit in N pages\n");
		return 2;
	}
	if ((o.keep_overflow || o.dump_each || o.depth || o.depth_given) && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --keep-overflow, --dump-each and --depth are for tri\n");
		return 2;
	}
	if (o.dump_each && !o.dump_dir) {
		fprintf(stderr, "sgxfive-test: --dump-each needs --dump-render DIR\n");
		return 2;
	}
	if ((o.depth_given || o.zgiven) && !o.depth) {
		fprintf(stderr, "sgxfive-test: the --depth-*, --stencil* options need --depth\n");
		return 2;
	}
	if (((o.stencil_fill.given || o.stencil_store) && !o.stencil) ||
	    (o.stencil_store_fill.given && !o.stencil_store) ||
	    (o.depth_store_fill.given && !o.depth_store)) {
		fprintf(stderr, "sgxfive-test: --stencil-store and --stencil-fill need --stencil, "
			"--stencil-store-fill --stencil-store, --depth-store-fill --depth-store\n");
		return 2;
	}
	if (!strcmp(cmd, "probe") && popts.tri.full && popts.tri.slot < 0) {
		fprintf(stderr, "sgxfive-test: --tri-full is for tri and probe --tri\n");
		return 2;
	}
	if ((o.tri_full || o.tri_z_given || o.tri_v_given) && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --tri-full, --tri-z and --tri-v are for tri\n");
		return 2;
	}
	if (o.pixels_rle && (strcmp(cmd, "tri") || o.pixels)) {
		fprintf(stderr, "sgxfive-test: --pixels-rle is for tri, and not with --pixels\n");
		return 2;
	}
	if (o.tri_unit && !o.tri_v_given) {
		fprintf(stderr, "sgxfive-test: --tri-unit needs --tri-v\n");
		return 2;
	}
	if (o.tri_unit && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --tri-unit is for tri and probe --tri, with --tri-v\n");
		return 2;
	}
	if (o.tri_v_given && o.tri_full) {
		fprintf(stderr, "sgxfive-test: --tri-v and --tri-full both place the triangle\n");
		return 2;
	}
	if (o.depth && (o.ctx2 || (o.depth_ctl_next && o.n < 2) ||
			(o.depth_pages != UINT32_MAX && (o.depth_pages < depth_min_pages(&o) ||
							 o.depth_pages > 0x100000)))) {
		fprintf(stderr, "sgxfive-test: --depth does not take --ctx2; --depth-ctl-next needs -n 2 "
			"or more; --depth-pages N must hold the target (width x height dwords)\n");
		return 2;
	}
	if (o.dump_dir && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --dump-render is for tri (probe takes its own)\n");
		return 2;
	}
	if ((o.ctx2 || o.share_pb || o.overlap || o.close_first || o.close_trace) && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --ctx2, --share-pb, --overlap, --close-first and --close-trace "
			"are for tri\n");
		return 2;
	}
	if (o.wait_second && (strcmp(cmd, "tri") || !o.overlap)) {
		fprintf(stderr, "sgxfive-test: --wait-second is for tri with --ctx2 --overlap\n");
		return 2;
	}
	if ((o.share_pb || o.overlap || o.close_first || o.close_trace) && !o.ctx2) {
		fprintf(stderr, "sgxfive-test: --share-pb, --overlap, --close-first and --close-trace need "
			"--ctx2\n");
		return 2;
	}
	if (o.ctx2 && o.geometry) {
		fprintf(stderr, "sgxfive-test: --ctx2 does not take --geometry\n");
		return 2;
	}
	if (o.words_dir && strcmp(cmd, "tri")) {
		fprintf(stderr, "sgxfive-test: --words is for tri\n");
		return 2;
	}
	if (o.wait_ms && strcmp(cmd, "tri") && strcmp(cmd, "dummy")) {
		fprintf(stderr, "sgxfive-test: --wait-ms is for tri and dummy\n");
		return 2;
	}
	if (o.close_early && (strcmp(cmd, "tri") || !o.ctx2 || o.close_first || o.overlap)) {
		fprintf(stderr, "sgxfive-test: --close-first-early is for tri --ctx2, without "
			"--close-first and --overlap\n");
		return 2;
	}
	if (o.words_between && (strcmp(cmd, "tri") || !o.ctx2 || !o.words_dir || o.overlap)) {
		fprintf(stderr, "sgxfive-test: --words-between is for tri --ctx2 --words, without "
			"--overlap\n");
		return 2;
	}
	if (o.geometry && (strcmp(cmd, "tri") || o.geometry >> (o.n - 1))) {
		fprintf(stderr, "sgxfive-test: --geometry is for tri, renders 1 to %u (the last "
			"render closes the scene)\n", o.n - 1);
		return 2;
	}
	for (unsigned int k = 0; k < o.nkpr; k++) {
		if (o.kpr[k].second && !o.ctx2) {
			fprintf(stderr, "sgxfive-test: --kpoke-render2 needs --ctx2\n");
			return 2;
		}
	}
	for (unsigned int k = 0; k < o.nkpr + o.nmoves; k++) {
		const bool job = k < o.nkpr && o.kpr[k].job;
		const uint32_t n = k < o.nkpr ? o.kpr[k].n : o.moves[k - o.nkpr].n;

		const bool right = job ? (!strcmp(cmd, "dummy") || !strcmp(cmd, "fill")) :
				   !strcmp(cmd, "tri");

		if (!right || !n || n > (job && !strcmp(cmd, "fill") ? 1 : o.n)) {
			fprintf(stderr, "sgxfive-test: --kpoke-render, --kreg-render and --move are "
				"for tri, render 1 to %u; --kpoke-job for dummy, job 1 to %u, and "
				"fill, job 1\n", o.n, o.n);
			return 2;
		}
	}
	if (o.every_value && strcmp(cmd, "copy")) {
		fprintf(stderr, "sgxfive-test: --every-value is for copy\n");
		return 2;
	}
	if ((o.ramp || o.ramp_base || o.print_addrs || o.page_before) && strcmp(cmd, "copy")) {
		fprintf(stderr, "sgxfive-test: --ramp, --ramp-base, --print-addrs and --page-before "
			"are for copy\n");
		return 2;
	}
	if ((o.ramp && o.every_value) || (o.ramp_base && !o.ramp)) {
		fprintf(stderr, "sgxfive-test: --ramp-base needs --ramp, which excludes "
			"--every-value\n");
		return 2;
	}

	/*
	 * Programs: our assembled ones by default. The fake source's images are
	 * not runnable; refuse to send them to a real GPU.
	 */
	needs_programs = !strcmp(cmd, "fill") || !strcmp(cmd, "copy") ||
			 !strcmp(cmd, "isolation") || !strcmp(cmd, "regaccess") || !strcmp(cmd, "probe");
	if (needs_programs && fake && !use_mock) {
		fprintf(stderr, "sgxfive-test: the fake program source is for the mock only "
			"(use --mock, or the default --programs=asm)\n");
		return 2;
	}
	if (needs_programs) {
		t.progs = fake ? sgxfive_prog_fake_create() : sgxfive_prog_asm_create();
		if (!t.progs)
			return fail("programs", -ENOMEM);
	}
	if (o.npokes && check_pokes(&t, cmd, &o)) {
		sgxfive_prog_source_destroy(t.progs);
		return 2;
	}

	if (use_mock)
		t.mock = sgxfive_mock_create(&mcfg);
	ret = sgxfive_dev_open(use_mock ? sgxfive_mock_backend(t.mock) : NULL, device, &t.dev);
	if (!ret && needs_programs)
		printf("programs %s\n", t.progs->name);
	if (ret) {
		if (ret == -ENODEV && !device)
			fprintf(stderr, "sgxfive-test: no sgxfive render node found\n");
		else
			fail(device ? device : "open", ret);
		ret = 1;
	} else if (!strcmp(cmd, "query")) {
		ret = cmd_query(&t);
	} else if (!strcmp(cmd, "dummy")) {
		ret = cmd_dummy(&t, &o);
	} else if (!strcmp(cmd, "fill")) {
		ret = cmd_fill(&t, &o);
	} else if (!strcmp(cmd, "copy")) {
		ret = cmd_copy(&t, &o);
	} else if (!strcmp(cmd, "regaccess")) {
		ret = cmd_regaccess(&t);
	} else if (!strcmp(cmd, "probe")) {
		ret = cmd_probe(&t, probes, nprobes, &popts);
	} else if (!strcmp(cmd, "tri")) {
		ret = cmd_tri(&t, &o);
	} else if (!strcmp(cmd, "contexts")) {
		ret = cmd_contexts(&t, &o);
	} else {
		ret = cmd_isolation(&t);
	}
	sgxfive_dev_close(t.dev);
	sgxfive_prog_source_destroy(t.progs);
	sgxfive_mock_destroy(t.mock);
	free(probes);
	return ret;
}
