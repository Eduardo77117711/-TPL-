"""tpl_sintaxe.py v1 - TPL: a sintaxe constante conferida por código (ver TPL_CANONE.md).

  python -I tpl_sintaxe.py estado              confere tpl_estado.json (esquema, estados, e
                                               hashes dos artefatos deste repositório)
  python -I tpl_sintaxe.py resposta ARQ.txt    confere uma resposta de qualquer modelo
  python -I tpl_sintaxe.py autoteste
Só biblioteca padrão. Saída: lista de violações e ESTADO textual; exit 1 se houver violação.
"""
import hashlib, json, os, re, sys, tempfile

AFIRMACAO = {"PROVADO", "MOSTRADO", "MENCIONADO", "FORA"}
EXECUCAO = {"VERIFICADO", "DIVERGENTE", "NAO EXECUTADO", "MENCIONADO"}
BLOCOS = ["[0] PERMANECE", "[1] MUDOU", "[2] EVIDÊNCIA", "[3] FALHAS-LIMITES", "[4] PRÓXIMA AÇÃO"]
HEX = re.compile(r"\b[0-9a-f]{64}\b")
ORIGEM = re.compile(r"^\[ORIGEM: [^\]\n]+\]")
ESTADO_EM_TEXTO = re.compile(r"\bEstado:\s*([A-ZÇÃÕ ]+?)(?=[.;,\n]|$)")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def conferir_estado(caminho, raiz):
    v = []
    try:
        e = json.load(open(caminho, encoding="utf-8"))
    except Exception as x:
        return ["estado ilegivel: " + type(x).__name__]
    for i, a in enumerate(e.get("artefatos", []) + e.get("pendentes", [])):
        tag = "%s (%s)" % (a.get("arquivo"), i)
        if not HEX.fullmatch(str(a.get("sha256", ""))):
            v.append(tag + ": sha256 invalido")
        if a.get("estado") not in EXECUCAO:
            v.append(tag + ": estado fora da lista: %r" % a.get("estado"))
        if a in e.get("artefatos", []) and a.get("estado") == "VERIFICADO" and not a.get("executor"):
            v.append(tag + ": VERIFICADO sem executor (R2)")
        if a.get("repositorio") == "-TPL-":
            p = os.path.join(raiz, a["arquivo"])
            if not os.path.exists(p):
                v.append(tag + ": arquivo ausente no repositorio")
            elif sha(p) != a["sha256"]:
                v.append(tag + ": hash do arquivo diverge do estado canonico")
    return v


def conferir_resposta(texto, estado_json):
    v = []
    if not ORIGEM.match(texto.lstrip("﻿")):
        v.append("falta etiqueta [ORIGEM: ...] na primeira linha")
    pos = [texto.find(b) for b in BLOCOS]
    for b, p in zip(BLOCOS, pos):
        if p < 0:
            v.append("bloco ausente: " + b)
    presentes = [p for p in pos if p >= 0]
    if presentes != sorted(presentes):
        v.append("blocos fora da ordem [0]..[4]")
    conhecidos = {a["sha256"] for a in estado_json.get("artefatos", []) + estado_json.get("pendentes", [])}
    for h in sorted(set(HEX.findall(texto)) - conhecidos):
        v.append("hash citado fora do estado canonico (R3): %s...%s" % (h[:8], h[-4:]))
    for m in ESTADO_EM_TEXTO.finditer(texto):
        s = m.group(1).strip()
        if s not in AFIRMACAO | EXECUCAO:
            v.append("estado invalido: %r" % s)
    return v


def autoteste():
    ok_total, falhas = 0, []

    def ok(c, m):
        nonlocal ok_total
        print(("OK    " if c else "FALHA ") + m)
        ok_total += c
        if not c:
            falhas.append(m)

    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.py"), "w").write("print(1)\n")
        h = sha(os.path.join(d, "a.py"))
        est = {"artefatos": [{"repositorio": "-TPL-", "arquivo": "a.py", "sha256": h, "estado": "VERIFICADO", "executor": "CI"}], "pendentes": []}
        p = os.path.join(d, "e.json")
        json.dump(est, open(p, "w"))
        ok(conferir_estado(p, d) == [], "estado integro passa")
        open(os.path.join(d, "a.py"), "w").write("print(2)\n")
        ok(any("diverge" in x for x in conferir_estado(p, d)), "mutante: arquivo alterado diverge do estado")
        est["artefatos"][0]["estado"] = "CONSOLIDADO"
        json.dump(est, open(p, "w"))
        ok(any("fora da lista" in x for x in conferir_estado(p, d)), "mutante: estado inventado no json")
        est["artefatos"][0].update(estado="VERIFICADO", executor="")
        json.dump(est, open(p, "w"))
        ok(any("R2" in x for x in conferir_estado(p, d)), "mutante: VERIFICADO sem executor")
        bom = ("[ORIGEM: MODELO X — 29/10/2026]\n[0] PERMANECE\na\n[1] MUDOU\nb\n[2] EVIDÊNCIA\nhash " + h +
               "\nEstado: VERIFICADO.\n[3] FALHAS-LIMITES\nc\n[4] PRÓXIMA AÇÃO\nd\n")
        ok(conferir_resposta(bom, est) == [], "resposta no formato passa")
        ok(any("ORIGEM" in x for x in conferir_resposta(bom.split("\n", 1)[1], est)), "mutante: sem etiqueta de origem")
        ok(any("ausente" in x for x in conferir_resposta(bom.replace("[3] FALHAS-LIMITES", ""), est)), "mutante: bloco faltando")
        trocado = bom.replace("[1] MUDOU", "[X]").replace("[2] EVIDÊNCIA", "[1] MUDOU").replace("[X]", "[2] EVIDÊNCIA")
        ok(any("ordem" in x for x in conferir_resposta(trocado, est)), "mutante: blocos fora de ordem")
        ok(any("R3" in x for x in conferir_resposta(bom.replace(h, "ab" * 32), est)), "mutante: hash inventado")
        ok(any("estado invalido" in x for x in conferir_resposta(bom.replace("Estado: VERIFICADO", "Estado: ESTASE FUNCIONAL SOBERANA"), est)), "mutante: estado inventado no texto")
    print("ESTADO: " + ("DIVERGENTE (%d)" % len(falhas) if falhas else "PASSOU (%d/10) - autoteste do autor; verificacao independente = CI (R2)" % ok_total))
    return 1 if falhas else 0


def main(a):
    raiz = os.path.dirname(os.path.abspath(__file__))
    if a == ["autoteste"]:
        return autoteste()
    if a == ["estado"]:
        v = conferir_estado(os.path.join(raiz, "tpl_estado.json"), raiz)
    elif len(a) == 2 and a[0] == "resposta":
        v = conferir_resposta(open(a[1], encoding="utf-8").read(), json.load(open(os.path.join(raiz, "tpl_estado.json"), encoding="utf-8")))
    else:
        print(__doc__)
        return 2
    for x in v:
        print("VIOLACAO", x)
    print("ESTADO: " + ("DIVERGENTE (%d violacoes)" % len(v) if v else "CONFORME"))
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
