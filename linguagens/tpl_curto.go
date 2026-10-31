// TPL - medicao curta (Golden Gate) em Go. Mesmo calculo do tpl_curto.py.
// Rode: go run tpl_curto.go
package main

import (
	"crypto/sha256"
	"fmt"
	"math"
	"strconv"
	"strings"
)

func roundN(x float64, n int) float64 { v, _ := strconv.ParseFloat(strconv.FormatFloat(x, 'f', n, 64), 64); return v }
func reprFloat(x float64) string { // repr do Python para floats
	s := strconv.FormatFloat(x, 'g', -1, 64)
	if !strings.ContainsAny(s, ".eEn") { s += ".0" }
	return s
}
func main() {
	vaoCentral, vaoLateral, torreAgua, torrePista := 1280, 343, 227, 152
	pista := torreAgua - torrePista
	flecha := torrePista - 6
	razao := float64(vaoLateral) / float64(vaoCentral)
	flechaLat := float64(flecha) * math.Pow(razao, 2)
	var cabo [33]float64
	for i := 0; i < 33; i++ {
		f := float64(i)
		cabo[i] = roundN(float64(torreAgua)-4*float64(flecha)*(f/32)*(1-f/32), 3)
	}
	imin, sim := 0, true
	for i := 1; i < 33; i++ { if cabo[i] < cabo[imin] { imin = i } }
	for i := 0; i < 33; i++ { if cabo[i] != cabo[32-i] { sim = false } }
	sn := func(b bool) string { if b { return "SIM" }; return "NAO" }
	texto := fmt.Sprintf(`{"cabo_minimo_m": %s, "cabo_minimo_no_meio": "%s", "cabo_simetrico": "%s", "flecha_central_m": %d, "flecha_lateral_m": %s, "lateral_sobre_central": %s, "pista_m": %d}`,
		reprFloat(cabo[imin]), sn(imin == 16), sn(sim), flecha, reprFloat(roundN(flechaLat, 3)), reprFloat(roundN(razao, 6)), pista)
	fmt.Println(texto)
	fmt.Printf("resultado_sha256: %x\n", sha256.Sum256([]byte(texto)))
}
