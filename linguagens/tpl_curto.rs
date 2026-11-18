// TPL - medicao curta (Golden Gate) em Rust. Mesmo calculo do tpl_curto.py.
// Compile e rode: rustc -O -o tpl_curto_rs tpl_curto.rs && ./tpl_curto_rs
const K: [u32; 64] = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,
0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,
0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];

fn sha256_hex(msg: &[u8]) -> String { // SHA-256 (FIPS 180-4), sem bibliotecas externas
    let mut h: [u32; 8] = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    let mut m = msg.to_vec();
    let bits = (msg.len() as u64) * 8;
    m.push(0x80);
    while m.len() % 64 != 56 { m.push(0); }
    m.extend_from_slice(&bits.to_be_bytes());
    for bloco in m.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 { w[i] = u32::from_be_bytes([bloco[4*i], bloco[4*i+1], bloco[4*i+2], bloco[4*i+3]]); }
        for i in 16..64 {
            let s0 = w[i-15].rotate_right(7) ^ w[i-15].rotate_right(18) ^ (w[i-15] >> 3);
            let s1 = w[i-2].rotate_right(17) ^ w[i-2].rotate_right(19) ^ (w[i-2] >> 10);
            w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
        }
        let mut v = h;
        for i in 0..64 {
            let t1 = v[7].wrapping_add(v[4].rotate_right(6) ^ v[4].rotate_right(11) ^ v[4].rotate_right(25))
                .wrapping_add((v[4] & v[5]) ^ (!v[4] & v[6])).wrapping_add(K[i]).wrapping_add(w[i]);
            let t2 = (v[0].rotate_right(2) ^ v[0].rotate_right(13) ^ v[0].rotate_right(22))
                .wrapping_add((v[0] & v[1]) ^ (v[0] & v[2]) ^ (v[1] & v[2]));
            v = [t1.wrapping_add(t2), v[0], v[1], v[2], v[3].wrapping_add(t1), v[4], v[5], v[6]];
        }
        for i in 0..8 { h[i] = h[i].wrapping_add(v[i]); }
    }
    h.iter().map(|x| format!("{:08x}", x)).collect()
}

fn round_n(x: f64, n: usize) -> f64 { format!("{:.*}", n, x).parse().unwrap() }
fn sn(b: bool) -> &'static str { if b { "SIM" } else { "NAO" } }

fn main() {
    let (vao_central, vao_lateral, torre_agua, torre_pista) = (1280i64, 343i64, 227i64, 152i64);
    let pista = torre_agua - torre_pista;
    let flecha = torre_pista - 6;
    let razao = vao_lateral as f64 / vao_central as f64;
    let flecha_lat = flecha as f64 * razao.powi(2);
    let cabo: Vec<f64> = (0..33).map(|i| {
        let f = i as f64;
        round_n(torre_agua as f64 - 4.0 * flecha as f64 * (f / 32.0) * (1.0 - f / 32.0), 3)
    }).collect();
    let mut imin = 0;
    for i in 1..33 { if cabo[i] < cabo[imin] { imin = i; } }
    let simetrico = (0..33).all(|i| cabo[i] == cabo[32 - i]);
    // {:?} de f64 no Rust imprime o menor numero de digitos com ".0", como o repr do Python
    let texto = format!("{{\"cabo_minimo_m\": {:?}, \"cabo_minimo_no_meio\": \"{}\", \"cabo_simetrico\": \"{}\", \"flecha_central_m\": {}, \"flecha_lateral_m\": {:?}, \"lateral_sobre_central\": {:?}, \"pista_m\": {}}}",
        cabo[imin], sn(imin == 16), sn(simetrico), flecha, round_n(flecha_lat, 3), round_n(razao, 6), pista);
    println!("{}", texto);
    println!("resultado_sha256: {}", sha256_hex(texto.as_bytes()));
}
