// OQ069: E987's zw-0125 and E981's z2-a-f0 vertex depths (s = 0.5) through sgx-pipe's
// isp::depth_cut_image (E1056's H-POLYCLIP coverage) on their 256 x 128 target.
use sgx_pipe::isp::{depth_cut_image, FarTri};
fn main() {
    let t = FarTri { v: [(0, 0), (512 * 256, 0), (0, 256 * 256)] };
    for w in [0.125f32, 0.25, 0.0, 0.0625, 0.1875, 0.3125, 0.375, 0.4375] {
        let z = [w - 0.5, w + 0.5, w - 0.5];
        let img = depth_cut_image(256, 128, &t, z).unwrap();
        let n = img.iter().filter(|b| **b).count();
        let first = (0..256).find(|&x| img[x]).unwrap_or(256);
        println!("w {w}: covered {n} of 32768, first x {first}");
    }
    let (w, s) = (0.25f32, 0.75f32);
    let img = depth_cut_image(256, 128, &t, [w - s, w + s, w - s]).unwrap();
    println!("w {w} s {s}: covered {} of 32768", img.iter().filter(|b| **b).count());
}
