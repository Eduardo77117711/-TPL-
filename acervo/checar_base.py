"""checar_base.py - TPL: liga a base (arquivos fixados no juiz) ao acervo atomico.
Cada arquivo fixado no verificar.yml precisa existir no indice do acervo com o mesmo sha256.
Uso: python3 -I acervo/checar_base.py acervo/indice_publico.txt ARQ1 ARQ2 ...
"""
import hashlib, sys
indice = {l.split()[0] for l in open(sys.argv[1], encoding="utf-8") if len(l.split()[0]) == 64}
falta = []
for p in sys.argv[2:]:
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    print(("LIGADO   " if h in indice else "SOLTO    ") + h[:16] + "  " + p)
    if h not in indice:
        falta.append(p)
print("ESTADO: " + ("BASE LIGADA AO ACERVO (%d/%d)" % (len(sys.argv) - 2, len(sys.argv) - 2) if not falta else "DIVERGENTE (%d soltos)" % len(falta)))
sys.exit(1 if falta else 0)
