"""tpl_cadeia.py - cadeia de hash append-only para o log do TPL.
Prova: ordem e adulteracao DETECTAVEL. Nao prova tempo. Reescrita total da
cadeia so e detectada contra uma ancora (hash da cabeca) guardada FORA do host.
Estado: [PROPOSTO] ate o autoteste rodar (python tpl_cadeia.py)."""
import hashlib, json, sys

GENESE = "0" * 64
VERSAO = "tpl_cadeia/1"

def _canon(o):
    def chk(x):
        if isinstance(x, (float, bool)):
            raise ValueError("float/bool proibido no payload")
        if isinstance(x, dict): [chk(v) for v in x.values()]
        if isinstance(x, list): [chk(v) for v in x]
    chk(o)
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _h(idx, prev, payload):
    return hashlib.sha256(_canon({"i": idx, "prev": prev, "p": payload, "v": VERSAO}).encode()).hexdigest()

def anexar(cadeia, payload):
    prev = cadeia[-1]["hash"] if cadeia else GENESE
    i = len(cadeia)
    cadeia.append({"i": i, "prev": prev, "p": payload, "hash": _h(i, prev, payload)})
    return cadeia[-1]["hash"]          # cabeca: publicar fora do host

def verificar(cadeia, ancora=None):
    prev = GENESE
    for i, b in enumerate(cadeia):
        if set(b) != {"i", "prev", "p", "hash"}: return False, f"campos fora do esquema em {i}"
        if b["i"] != i: return False, f"indice quebrado em {i}"
        if b["prev"] != prev: return False, f"prev_hash quebrado em {i}"
        if b["hash"] != _h(i, prev, b["p"]): return False, f"conteudo adulterado em {i}"
        prev = b["hash"]
    if ancora is not None and prev != ancora:
        return False, "cabeca difere da ancora externa (truncamento ou reescrita)"
    if ancora is None:
        return True, "integridade interna OK; SEM ancora: reescrita total nao e detectavel"
    return True, "integridade OK e cabeca confere com a ancora"

def _autoteste():
    import copy
    c = []; [anexar(c, {"lote": n, "estado": "APPROVED"}) for n in range(5)]
    anc = c[-1]["hash"]
    r = []
    r.append(("integra com ancora", verificar(c, anc)[0] is True))
    t = copy.deepcopy(c); t[2]["p"]["estado"] = "BLOCKED"
    r.append(("altera conteudo", verificar(t, anc)[0] is False))
    t = copy.deepcopy(c); del t[2]
    r.append(("apaga bloco", verificar(t, anc)[0] is False))
    t = copy.deepcopy(c); t[1], t[2] = t[2], t[1]
    r.append(("troca ordem", verificar(t, anc)[0] is False))
    t = copy.deepcopy(c)[:3]
    r.append(("trunca cauda (so com ancora)", verificar(t, anc)[0] is False and verificar(t)[0] is True))
    t = []; [anexar(t, {"lote": n, "estado": "BLOCKED" if n == 2 else "APPROVED"}) for n in range(5)]
    r.append(("reescreve tudo: passa SEM ancora", verificar(t)[0] is True))
    r.append(("reescreve tudo: barrado COM ancora", verificar(t, anc)[0] is False))
    try: anexar([], {"x": 1.5}); r.append(("rejeita float", False))
    except ValueError: r.append(("rejeita float", True))
    t = copy.deepcopy(c); t[1]["extra"] = "x"
    r.append(("campo extra no bloco", verificar(t, anc)[0] is False))
    t = copy.deepcopy(c); t[1].pop("prev")
    r.append(("campo removido do bloco", verificar(t, anc)[0] is False))
    for n, ok in r: print(("PASSOU " if ok else "FALHOU ") + n)
    return all(ok for _, ok in r)

if __name__ == "__main__":
    sys.exit(0 if _autoteste() else 1)
