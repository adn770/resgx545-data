/* SPDX-License-Identifier: MIT */
/*
 * libsgxfive render jobs (the render commands of include/uapi/sgxfive_drm.h):
 * the first triangle built in userspace. The scene builders
 * are pure: they write the programs, the MTE state, the VDM stream and the
 * geometry into buffers at given GPU addresses and fill the job's register
 * words (struct drm_sgxfive_render_cmd); the kernel builds the firmware side.
 * The render engine places a scene in a VM, submits it on a render context
 * and checks the image against a CPU reference.
 *
 * Every program is our own: asm/, generated into src/tri_progs_gen.h.
 */
#ifndef SGXFIVE_RENDER_H
#define SGXFIVE_RENDER_H

#include "sgxfive.h"
#include "sgxfive_poke.h"
#include "sgxfive_xfer.h"

#define SGXFIVE_TRI_MAX_W	4096	/* the device's largest render target */
#define SGXFIVE_TRI_MAX_H	4096

/*
 * The tiling words of a W x H render target, the layout the kernel sized the
 * context's tiling data for and requires (the rule in sgxfive_drm.h): TE_SCREEN, TE_MTILE1/2 and TE_MTILE.
 */
struct sgxfive_tiling {
	uint32_t te_screen, te_mtile1, te_mtile2, te_mtile_stride;
};

void sgxfive_tiling(struct sgxfive_tiling *t, uint32_t width, uint32_t height);
/* The same, into a render command's TE words. */
void sgxfive_tiling_cmd(struct drm_sgxfive_render_cmd *c, uint32_t width, uint32_t height);

/* One flat-coloured triangle over a background colour, ARGB8888 W x H. */
struct sgxfive_tri_params {
	uint32_t width, height;		/* even, at most SGXFIVE_TRI_MAX_W x _H */
	uint32_t colour, bg_colour;	/* ARGB8888 */
	int32_t v[3][2];		/* vertices in 1/16 pixel, window coordinates */
	float zndc[3];			/* each vertex's clip z; 0: depth 0.5 (= 0.5 + 0.5 z) */
	/*
	 * fine: the vertices are v256, in 1/256 pixel (an exact clip coordinate for a target whose
	 * half-size is a power of two); v then holds the nearest 1/16 for the CPU reference.
	 */
	bool fine;
	uint32_t fine_shift;		/* the unit of v256 is 1/2^fine_shift pixel (8: 1/256) */
	int32_t v256[3][2];
};

/* Set the triangle's vertices in 1/256 pixel (see sgxfive_tri_params.fine). */
void sgxfive_tri_fine(struct sgxfive_tri_params *p, const int32_t v256[3][2]);
/* The same in 1/2^shift pixel (shift 5 to 20): exact clip coordinates while the target's half-size times 2^shift
 * stays below 2^24. */
void sgxfive_tri_fine_unit(struct sgxfive_tri_params *p, const int32_t v[3][2], unsigned int shift);
/* The vertices' clip words {x, y, z, w} (float32 bits) as the scene writes them. */
void sgxfive_tri_vertex_words(const struct sgxfive_tri_params *p, uint32_t w[3][4]);

/* The first triangle's: (8, 8), (56, 20), (20, 56) in a 64 x 64 target, scaled. */
void sgxfive_tri_default(struct sgxfive_tri_params *p, uint32_t width, uint32_t height);

/*
 * Where the scene lives, by GPU address: one page each for the vertex PDS and
 * USSE programs, the pixel PDS and USSE programs and the VDM streams with the
 * geometry, then the colour buffer (stride = 4 x width). The code and PDS
 * bases are the heap bases DEV_QUERY reports: USE_CODE_BASE_0 (pixel),
 * USE_CODE_BASE_10 (vertex) and PDS_EXEC_BASE, which the kernel keeps at the
 * PDS_PIXEL heap base.
 */
struct sgxfive_tri_layout {
	uint32_t pdsv, usev, pdsp, usep, gen, fb;
	uint32_t pds_exec_base, usep_base, usev_base;
};

/*
 * CPU views of the five program/stream pages (4 KiB each). gen_size, in bytes, is how far the
 * gen view reaches (0: its one page); a scene of more vertices than that page holds needs the
 * extra pages sgxfive_tri_rig_create maps after it.
 */
struct sgxfive_tri_cpu {
	uint32_t *pdsv, *usev, *pdsp, *usep, *gen;
	uint32_t gen_size;
};

/* Offsets inside the pages (the kernel's debugfs triangle test's). */
#define SGXFIVE_TRI_PV_VTX	0x000	/* pds_vtx */
#define SGXFIVE_TRI_PV_MTE	0x040	/* pds_mte: the triangle's state */
#define SGXFIVE_TRI_PV_EOS	0x080	/* pds_mte: end of scene */
#define SGXFIVE_TRI_PV_BLOCK	0x100	/* the triangle's MTE state block */
#define SGXFIVE_TRI_PV_EOSBLOCK	0x180	/* the end-of-scene state block */
#define SGXFIVE_TRI_UV_VTX	0x000	/* use_vtx */
#define SGXFIVE_TRI_UV_MTE18	0x080	/* use_mtest18 */
#define SGXFIVE_TRI_UV_MTE2	0x100	/* use_mtest2 */
#define SGXFIVE_TRI_PP_PRIM	0x000	/* pds_prim: the triangle's colour */
#define SGXFIVE_TRI_PP_BGPRIM	0x020	/* pds_prim: the background colour */
#define SGXFIVE_TRI_PP_SEC	0x040	/* pds_sec */
#define SGXFIVE_TRI_PP_PIXEV	0x080	/* pds_pixevent */
#define SGXFIVE_TRI_UP_FILL	0x000	/* use_fill: the triangle's colour */
#define SGXFIVE_TRI_UP_BGFILL	0x010	/* use_fill: the background colour */
#define SGXFIVE_TRI_UP_SEC	0x020	/* use_sec */
#define SGXFIVE_TRI_UP_PTOFF	0x030	/* use_ptoff */
#define SGXFIVE_TRI_UP_EOT	0x040	/* use_eot */
#define SGXFIVE_TRI_UP_EOR	0x080	/* use_eor */
#define SGXFIVE_TRI_G_VDM	0x000	/* the VDM stream */
#define SGXFIVE_TRI_G_VTX	0x100	/* three vertices {x, y, z, w} */
#define SGXFIVE_TRI_G_IDX	0x200	/* three 16-bit indices */

#define SGXFIVE_TRI_BLOCK_WORDS	18	/* the triangle's MTE state block */
#define SGXFIVE_TRI_EOS_WORDS	2
#define SGXFIVE_TRI_VDM_WORDS	11	/* state, index list, end of scene, end */
#define SGXFIVE_TRI_USEV_CBASE	10	/* the code base of vertex programs */

/* Word builders. */
uint32_t sgxfive_tri_doutu(uint32_t addr, uint32_t code_base, uint32_t cbase, uint32_t temps);
uint32_t sgxfive_tri_pix_ptr(const struct sgxfive_tri_layout *l, uint32_t addr,
			     uint32_t data_dwords);
uint32_t sgxfive_tri_doutd(uint32_t dwords);
uint32_t sgxfive_f32(float f);
void sgxfive_tri_block(uint32_t blk[SGXFIVE_TRI_BLOCK_WORDS], const struct sgxfive_tri_layout *l,
		       const struct sgxfive_tri_params *p);
void sgxfive_tri_eos(uint32_t blk[SGXFIVE_TRI_EOS_WORDS], const struct sgxfive_tri_params *p);
void sgxfive_tri_vdm(uint32_t vdm[SGXFIVE_TRI_VDM_WORDS], const struct sgxfive_tri_layout *l);

/*
 * The whole client side: programs, state blocks, VDM stream, vertices and
 * indices into c, and the job's register words into cmd. -EINVAL for a size
 * the kernel would refuse or that does not fit the layout.
 */
int sgxfive_tri_scene(const struct sgxfive_tri_cpu *c, const struct sgxfive_tri_layout *l,
		      const struct sgxfive_tri_params *p, struct drm_sgxfive_render_cmd *cmd);

/*
 * The CPU reference for pixel (x, y), row y = window y: 1 when its centre is
 * inside the triangle by at least a pixel, 0 when outside by at least a
 * pixel, -1 near an edge, where either colour is accepted.
 */
int sgxfive_tri_expect(const struct sgxfive_tri_params *p, uint32_t x, uint32_t y);

/* Every pixel of fb (stride 4 x width) against the reference. */
struct sgxfive_tri_counts {
	uint32_t tri, bg, other;	/* pixels of each colour, and neither */
	uint32_t wrong_in, wrong_out, wrong_edge;
	uint32_t flipped;		/* mismatches against the image flipped in y */
};

int sgxfive_tri_check(const struct sgxfive_tri_params *p, const uint32_t *fb,
		      struct sgxfive_tri_counts *n);

/* ---- Render engine ------------------------------------------------------------------ */

#define SGXFIVE_TRI_SENTINEL	0xdeadbeefu

struct sgxfive_render;

/*
 * One render context's engine in vm: a BO of five program/stream pages mapped
 * in the PDS_VERTEX, USSE_VERTEX, PDS_PIXEL, USSE_PIXEL and GENERAL heaps,
 * and a colour buffer in GENERAL of the largest target rendered so far plus a
 * guard page (allocated, or grown, by sgxfive_render_tri). ctx is a render
 * context on vm.
 */
int sgxfive_render_create(struct sgxfive_vm *vm, uint32_t ctx, struct sgxfive_render **out);
void sgxfive_render_destroy(struct sgxfive_render *r);

/*
 * Build the scene, fill the target's pixels and the colour buffer after them
 * with the sentinel, submit (waiting for syncobj wait, signalling signal, if
 * not 0). The previous job must be finished (sgxfive_render_wait).
 */
int sgxfive_render_tri(struct sgxfive_render *r, const struct sgxfive_tri_params *p,
		       uint32_t wait, uint32_t signal);
/*
 * The same with the job's flags: DRM_SGXFIVE_SUBMIT_JOB_RENDER_GEOMETRY tiles the
 * triangle into the context's scene and leaves the scene open, drawing nothing; the
 * next job without it renders the whole scene.
 */
int sgxfive_render_tri_flags(struct sgxfive_render *r, const struct sgxfive_tri_params *p,
			     uint32_t wait, uint32_t signal, uint32_t flags);
/*
 * Wait for the last job: 0, -ETIME, or once its error if it failed (-EIO, ...;
 * -ENOSPC: the scene overflowed the parameter buffer, the image is undefined).
 */
int sgxfive_render_wait(struct sgxfive_render *r, int64_t timeout_ns);

/* The colour buffer, and the dwords after the target that are not the sentinel. */
const uint32_t *sgxfive_render_fb(const struct sgxfive_render *r);
uint32_t sgxfive_render_guard_dirty(const struct sgxfive_render *r,
				    const struct sgxfive_tri_params *p);
const struct drm_sgxfive_render_cmd *sgxfive_render_last_cmd(const struct sgxfive_render *r);
void sgxfive_render_get_layout(const struct sgxfive_render *r, struct sgxfive_tri_layout *l);
/* The CPU view of the engine's page in heap (PDS_VERTEX, ..., GENERAL), or NULL. */
const void *sgxfive_render_page(const struct sgxfive_render *r, uint32_t heap);

/*
 * Pokes (sgxfive_poke.h). The views of the triangle's job: cmd, vdm, eos,
 * blk and the data of its PDS programs, pds:vtx, pds:state (the triangle's
 * state), pds:eos (the end of scene's), pds:prim, pds:bgprim, pds:sec and
 * pds:pixev; sizes only. Returns the count.
 */
unsigned int sgxfive_render_poke_layout(struct sgxfive_poke_view v[SGXFIVE_POKE_VIEWS_MAX]);
/* The same views over the words of the engine's last built job. */
unsigned int sgxfive_render_poke_views(struct sgxfive_render *r,
				       struct sgxfive_poke_view v[SGXFIVE_POKE_VIEWS_MAX]);
/*
 * Call fn(priv, views, n) on every later render once its scene is built,
 * right before it is submitted (sgxfive_poke_hook applies pokes); its error
 * fails the render unsubmitted. fn NULL: none.
 */
void sgxfive_render_set_hook(struct sgxfive_render *r, sgxfive_job_hook fn, void *priv);

#endif
