// TPL - medicao curta (Golden Gate) em JavaScript (Node). Mesmo calculo do tpl_curto.py.
// Rode: node tpl_curto.js
const crypto = require("crypto");
const V = { vao_central: 1280, vao_lateral: 343, torre_agua: 227, torre_pista: 152 };
const roundN = (x, n) => Number(x.toFixed(n));
const reprFloat = (x) => (Number.isInteger(x) ? x.toFixed(1) : String(x));  // repr do Python para floats
const pista = V.torre_agua - V.torre_pista;
const flecha = V.torre_pista - 6;
const razao = V.vao_lateral / V.vao_central;
const flechaLat = flecha * razao ** 2;
const cabo = [];
for (let i = 0; i < 33; i++) cabo.push(roundN(V.torre_agua - 4 * flecha * (i / 32) * (1 - i / 32), 3));
const minimo = Math.min(...cabo);
const simetrico = cabo.every((v, i) => v === cabo[32 - i]);
const texto = `{"cabo_minimo_m": ${reprFloat(minimo)}, "cabo_minimo_no_meio": "${cabo.indexOf(minimo) === 16 ? "SIM" : "NAO"}", ` +
  `"cabo_simetrico": "${simetrico ? "SIM" : "NAO"}", "flecha_central_m": ${flecha}, "flecha_lateral_m": ${reprFloat(roundN(flechaLat, 3))}, ` +
  `"lateral_sobre_central": ${reprFloat(roundN(razao, 6))}, "pista_m": ${pista}}`;
console.log(texto);
console.log("resultado_sha256: " + crypto.createHash("sha256").update(texto, "utf8").digest("hex"));
