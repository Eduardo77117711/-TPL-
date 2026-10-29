"""tpl_fala.py v0.1 - TPL: a fala do Eduardo guardada como ela e, e o refinamento conferido contra ela.

Problema: todo modelo que reescreve uma fala acrescenta o proprio vies. Pureza total
na reescrita nao existe. O que existe e separar as camadas e deixar o codigo conferir:

  CAMADA 0 (ORIGINAL)  - a fala literal, com sha256 e hora, numa cadeia de hash.
                         Nunca e editada; correcao vira nova entrada que aponta a anterior.
  CAMADA 1 (REFINO)    - cada ideia extraida pelo modelo precisa citar um trecho literal
                         da camada 0. O codigo confere:
                           trecho encontrado          -> DA_FALA (pertence ao Eduardo)
                           trecho ausente ou curto    -> DO_MODELO (interpretacao, nao fala)

Uso:
  python3 -I tpl_fala.py registrar "texto da fala"      # acrescenta a cadeia.jsonl
  python3 -I tpl_fala.py conferir refino.json            # refino contra a ultima fala
  python3 -I tpl_fala.py cadeia                          # confere a cadeia inteira
  python3 -I tpl_fala.py autoteste
Sem booleanos de decisao no resultado: estados textuais. So biblioteca padrao.
"""
import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone

ARQ = "cadeia_falas.jsonl"
MIN_TRECHO = 8
GENESE = "0" * 64


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = "".join(c if c.isalnum() else " " for c in s)
    return " ".join(s.split())


def na_fala(trecho, fala):
    t = norm(trecho)
    return len(t) >= MIN_TRECHO and t in norm(fala)


def entrada(fala, anterior, quando=None):
    corpo = {"quando": quando or datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "fala": fala, "sha_fala": sha(fala), "anterior": anterior}
    corpo["selo"] = sha(json.dumps(corpo, ensure_ascii=False, sort_keys=True))
    return corpo


def conferir_cadeia(linhas):
    anterior = GENESE
    for i, e in enumerate(linhas):
        selo = e.get("selo")
        corpo = {k: e[k] for k in ("quando", "fala", "sha_fala", "anterior") if k in e}
        if e.get("anterior") != anterior:
            return "QUEBRADA na entrada %d (ligacao com a anterior)" % i
        if sha(e.get("fala", "")) != e.get("sha_fala"):
            return "QUEBRADA na entrada %d (fala alterada)" % i
        if sha(json.dumps(corpo, ensure_ascii=False, sort_keys=True)) != selo:
            return "QUEBRADA na entrada %d (selo)" % i
        anterior = selo
    return "INTEGRA (%d entradas)" % len(linhas)


def conferir_refino(refino, fala):
    itens, da_fala = [], 0
    for x in refino if isinstance(refino, list) else []:
        estado = "DA_FALA" if na_fala(x.get("trecho"), fala) else "DO_MODELO"
        da_fala += estado == "DA_FALA"
        itens.append({"ideia": x.get("ideia"), "trecho": x.get("trecho"), "estado": estado})
    total = len(itens)
    return {"itens": itens, "da_fala": da_fala, "do_modelo": total - da_fala,
            "fidelidade": "%d/%d" % (da_fala, total)}


def ler():
    try:
        with open(ARQ, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


def autoteste():
    falhas = []

    def ok(c, m):
        print(("OK    " if c else "FALHA ") + m)
        if not c:
            falhas.append(m)

    fala = ("Da para ver se posso expressar meus pensamentos e serem refletidos como eles "
            "sao com pureza? Ou o que precisamos? Qual o segundo passo?")
    r = conferir_refino([{"ideia": "quer reflexo fiel", "trecho": "refletidos como eles sao com pureza"}], fala)
    ok(r["itens"][0]["estado"] == "DA_FALA", "trecho literal pertence a fala")
    r = conferir_refino([{"ideia": "x", "trecho": "REFLETIDOS COMO ELES SÃO COM PUREZA"}], fala)
    ok(r["itens"][0]["estado"] == "DA_FALA", "acento e maiuscula nao rebaixam")
    r = conferir_refino([{"ideia": "quer publicar um livro", "trecho": "quero publicar um livro"}], fala)
    ok(r["itens"][0]["estado"] == "DO_MODELO", "mutante: ideia inventada vira DO_MODELO")
    r = conferir_refino([{"ideia": "x", "trecho": "pureza"}], fala)
    ok(r["itens"][0]["estado"] == "DO_MODELO", "mutante: palavra solta nao prova")
    r = conferir_refino([{"ideia": "x"}], fala)
    ok(r["itens"][0]["estado"] == "DO_MODELO", "mutante: sem trecho vira DO_MODELO")
    ok(conferir_refino("lixo", fala)["fidelidade"] == "0/0", "refino quebrado nao derruba")
    a = entrada("fala um", GENESE, "2026-10-29T08:17:00+00:00")
    b = entrada("fala dois", a["selo"], "2026-10-29T08:18:00+00:00")
    ok(conferir_cadeia([a, b]).startswith("INTEGRA"), "cadeia integra")
    adulterada = dict(b, fala="fala dois editada")
    ok(conferir_cadeia([a, adulterada]).startswith("QUEBRADA"), "mutante: fala editada quebra a cadeia")
    ok(conferir_cadeia([b, a]).startswith("QUEBRADA"), "mutante: ordem trocada quebra a cadeia")
    ok(conferir_cadeia([a, dict(b, quando="2026-10-29T09:00:00+00:00")]).startswith("QUEBRADA"),
       "mutante: hora alterada quebra o selo")
    print("ESTADO: " + ("DIVERGENTE (%d)" % len(falhas) if falhas else "PROVADO (10/10)"))
    return 1 if falhas else 0


def main(a):
    if a == ["autoteste"]:
        return autoteste()
    if len(a) == 2 and a[0] == "registrar":
        linhas = ler()
        e = entrada(a[1], linhas[-1]["selo"] if linhas else GENESE)
        with open(ARQ, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        print("REGISTRADA selo=" + e["selo"])
        return 0
    if a == ["cadeia"]:
        print(conferir_cadeia(ler()))
        return 0
    if len(a) == 2 and a[0] == "conferir":
        linhas = ler()
        if not linhas:
            print("NAO EXECUTADO: nenhuma fala registrada")
            return 1
        with open(a[1], encoding="utf-8") as f:
            print(json.dumps(conferir_refino(json.load(f), linhas[-1]["fala"]), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
