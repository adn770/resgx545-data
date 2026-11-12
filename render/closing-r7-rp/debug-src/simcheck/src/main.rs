// Round 7 plan, Q291 (scratch harness after closing6/r6-pixel/debug-src/simcheck): run pix_posstore.bin in sgx-sim as a
// triangle's pixel instance at every pixel of a W x H tile area (Machine.tri_pixel: g23, g24, g25 as E808 measured), with
// pa0 = x + 0.5 and pa1 = y + 0.5 as floats (E437's position pair), and check every store against the slot rule.
//   posstore-simcheck PROG.bin W H     prints one "pixel X Y: ..." line per failure and a summary; exit 1 on any failure.
use sgx_sim::vectors::{SCRATCH_BASE, SCRATCH_DWORDS};
use sgx_sim::{Bus, Error, Machine, Memory, Program};
use usse_isa::Core;

struct Scratch {
    mem: Memory,
    stores: Vec<(u32, u32)>,
}

impl Bus for Scratch {
    fn load32(&mut self, addr: u32) -> Result<u32, Error> {
        self.mem.load32(addr)
    }
    fn store32(&mut self, addr: u32, v: u32) -> Result<(), Error> {
        self.stores.push((addr, v));
        self.mem.store32(addr, v)
    }
    fn emit(&mut self, _text: &str, _srcs: [u32; 3]) -> Result<(), Error> {
        Ok(())
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let bytes = std::fs::read(&a[1]).unwrap();
    let (w, h): (u32, u32) = (a[2].parse().unwrap(), a[3].parse().unwrap());
    // the host's patch of the scratch immediates 0x5CAFnnnn (sgxfive-test.c): scratch address + nnnn
    let words: Vec<u64> = bytes
        .chunks(8)
        .map(|c| u64::from_le_bytes(c.try_into().unwrap()))
        .collect();
    let prog0 = Program::new(&words, Core::Sgx545);
    let mut pc = 0;
    while let Some(t) = Machine::text(&prog0, pc) {
        println!("insn {pc} {t}");
        pc += 1;
    }
    let (mut bad, mut n) = (0, 0);
    for y in 0..h {
        for x in 0..w {
            let mut m = Machine { core: Core::Sgx545, temps: 4, vertex_task: false, ..Machine::default() };
            m.pixel = Some((x, y));
            m.tri_pixel = true;
            let (px, py) = ((x as f32 + 0.5).to_bits(), (y as f32 + 0.5).to_bits());
            m.pa[0] = px;
            m.pa[1] = py;
            m.written.pa |= 3;
            let mut bus = Scratch {
                mem: Memory { base: 0x5CAF_0000, words: (0..SCRATCH_DWORDS as u32).map(|i| 0xD000_0000 | i).collect() },
                stores: Vec::new(),
            };
            let _ = SCRATCH_BASE;
            let r = loop {
                if m.steps >= 10_000 {
                    break Err(Error::StepLimit);
                }
                match m.step(&prog0, &mut bus) {
                    Ok(true) => break Ok(()),
                    Ok(false) => {}
                    Err(e) => break Err(e),
                }
            };
            n += 1;
            let slot = (y % 16) << 5 | (x % 32);
            let base = 0x5CAF_0000 + 16 * slot;
            let lane = 0x7E57_0000 | (x & 1) | (y & 1) << 1;
            let want = vec![(base, px), (base + 4, px), (base + 8, py), (base + 12, lane)];
            let o0 = if m.written.o & 1 != 0 { Some(m.o[0]) } else { None };
            if r.is_err() || bus.stores != want || o0 != Some(px) {
                bad += 1;
                println!("pixel {x} {y}: {:?} stores {:x?} want {:x?} o0 {:x?}", r.err().map(|e| e.to_string()), bus.stores, want, o0);
            }
        }
    }
    println!("posstore: {n} pixels, {bad} failures, slots distinct within a tile: {}", if bad == 0 { "yes" } else { "unchecked" });
    std::process::exit(if bad == 0 { 0 } else { 1 });
}
