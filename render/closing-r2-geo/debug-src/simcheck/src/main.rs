// scratch harness (R2 T5): run a USSE .bin as a vertex task in sgx-sim at a chosen code_index, as the tool places a
// vtxuse program (SGXFIVE_TRI_PROBE_UV_VTX = 0x200 bytes = instruction 0x40 from the code base, plus the page).
//   simcheck PROG.bin CODE_INDEX [--set REG=VALUE]...   prints "ended|stopped STEPS", the o registers written, emits.
use sgx_sim::vectors::{SCRATCH_BASE, SCRATCH_DWORDS};
use sgx_sim::{Bus, Error, Machine, Memory, Program};
use usse_isa::Core;

struct Scratch {
    mem: Memory,
    emits: Vec<String>,
}

impl Bus for Scratch {
    fn load32(&mut self, addr: u32) -> Result<u32, Error> {
        self.mem.load32(addr)
    }
    fn store32(&mut self, addr: u32, v: u32) -> Result<(), Error> {
        self.mem.store32(addr, v)
    }
    fn emit(&mut self, text: &str, srcs: [u32; 3]) -> Result<(), Error> {
        let name = text.split(['.', ' ']).next().unwrap_or(text);
        self.emits.push(format!("{name} 0x{:08x} 0x{:08x} 0x{:08x}", srcs[0], srcs[1], srcs[2]));
        Ok(())
    }
}

fn num(s: &str) -> u32 {
    match s.strip_prefix("0x") {
        Some(h) => u32::from_str_radix(h, 16).unwrap(),
        None => s.parse().unwrap(),
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let bytes = std::fs::read(&a[1]).unwrap();
    let words: Vec<u64> = bytes.chunks(8).map(|c| u64::from_le_bytes(c.try_into().unwrap())).collect();
    let code_index = num(&a[2]);
    let prog = Program::new(&words, Core::Sgx545);
    let mut m = Machine { core: Core::Sgx545, temps: 16, vertex_task: true, code_index, ..Machine::default() };
    let mut i = 3;
    while i < a.len() {
        if a[i] == "--set" {
            let (r, v) = a[i + 1].split_once('=').unwrap();
            let n: usize = r[2..].parse().unwrap();
            match &r[..2] {
                "pa" => (m.pa[n], m.written.pa) = (num(v), m.written.pa | 1 << n),
                _ => panic!("only pa"),
            }
            i += 1;
        }
        i += 1;
    }
    let mut bus = Scratch {
        mem: Memory { base: SCRATCH_BASE, words: (0..SCRATCH_DWORDS as u32).map(|i| 0xD000_0000 | i).collect() },
        emits: Vec::new(),
    };
    let r = loop {
        if m.steps >= 2_000_000 {
            break Err(Error::StepLimit);
        }
        match m.step(&prog, &mut bus) {
            Ok(true) => break Ok(()),
            Ok(false) => {}
            Err(e) => break Err(e),
        }
    };
    match r {
        Ok(()) => println!("ended {}", m.steps),
        Err(e) => println!("stopped {} {e}", m.steps),
    }
    for n in 0..16 {
        if m.written.o >> n & 1 != 0 {
            println!("o{n} = 0x{:08x}", m.o[n]);
        }
    }
    for e in &bus.emits {
        println!("emit {e}");
    }
}
