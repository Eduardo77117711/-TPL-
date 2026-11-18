<?php
// TPL - medicao curta (Golden Gate) em PHP. Mesmo calculo do tpl_curto.py.
// Rode: php tpl_curto.php
function round_n($x, $n) { return (float) sprintf("%.{$n}F", $x); }
function repr_float($x) { // repr do Python para floats: menor numero de digitos que volta ao mesmo valor
    for ($p = 1; $p <= 17; $p++) { $s = sprintf("%.{$p}G", $x); if ((float) $s === $x) break; }
    if (strpbrk($s, ".EN") === false) $s .= ".0";
    return $s;
}
$V = ["vao_central" => 1280, "vao_lateral" => 343, "torre_agua" => 227, "torre_pista" => 152];
$pista = $V["torre_agua"] - $V["torre_pista"];
$flecha = $V["torre_pista"] - 6;
$razao = $V["vao_lateral"] / $V["vao_central"];
$flecha_lat = $flecha * ($razao ** 2);
$cabo = [];
for ($i = 0; $i < 33; $i++) $cabo[] = round_n($V["torre_agua"] - 4 * $flecha * ($i / 32) * (1 - $i / 32), 3);
$minimo = min($cabo);
$simetrico = $cabo === array_reverse($cabo);
$texto = sprintf('{"cabo_minimo_m": %s, "cabo_minimo_no_meio": "%s", "cabo_simetrico": "%s", "flecha_central_m": %d, "flecha_lateral_m": %s, "lateral_sobre_central": %s, "pista_m": %d}',
    repr_float($minimo), array_search($minimo, $cabo, true) === 16 ? "SIM" : "NAO", $simetrico ? "SIM" : "NAO", $flecha,
    repr_float(round_n($flecha_lat, 3)), repr_float(round_n($razao, 6)), $pista);
echo $texto, "\n", "resultado_sha256: ", hash("sha256", $texto), "\n";
