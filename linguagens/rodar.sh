#!/usr/bin/env bash
# TPL - roda o tpl_curto em todas as linguagens desta pasta e compara com o valor selado.
# Uso (de dentro da pasta linguagens/): bash rodar.sh
set -u
ESPERADO="resultado_sha256: f68601e2c3d8920f49fffff21d871939aad6094c335aabe217a873d78b272260"
T="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/tpl_ling"; mkdir -p "$T"
falhas=0; total=0
medir() {  # $1 = nome, $2.. = comando
  local nome="$1"; shift; total=$((total+1))
  local ultima; ultima="$("$@" 2>"$T/$nome.err" | tr -d '\r' | tail -n 1)"
  if [ "$ultima" = "$ESPERADO" ]; then echo "$nome | REPRODUZ"; else echo "$nome | DIVERGE: ${ultima:-sem saida} $(head -c 300 "$T/$nome.err")"; falhas=$((falhas+1)); fi
}
medir python    python3 -I -X utf8 ../tpl_curto.py
medir c         sh -c "gcc -O2 -o '$T/c' tpl_curto.c -lm && '$T/c'"
medir cpp       sh -c "g++ -O2 -o '$T/cpp' tpl_curto.cpp && '$T/cpp'"
medir rust      sh -c "rustc -O -o '$T/rs' tpl_curto.rs && '$T/rs'"
medir go        go run tpl_curto.go
medir javascript node tpl_curto.js
medir java      java TplCurto.java
medir php       php tpl_curto.php
medir ruby      ruby tpl_curto.rb
echo "LINGUAGENS QUE REPRODUZEM: $((total-falhas)) / $total"
[ "$falhas" -eq 0 ]
