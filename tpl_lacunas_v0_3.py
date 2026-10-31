"""tpl_lacunas_v0_3.py v0.3 - TPL: o que existe nos chats e falta no acervo verificado.

Entrada: uma pasta ACERVO (arquivos já guardados: repos clonados, núcleo) e uma pasta
ENTRADA (exportações de chats e repositórios trazidos de outros modelos).
Saída por item, com a fonte (arquivo e linha):
  JA_GUARDADO   bloco de código idêntico (sha256 normalizado) a um arquivo do acervo
  LACUNA        bloco de código ou arquivo citado que não existe no acervo
  HASH_SEM_BASE hash de 64 hex citado no chat que não bate com nenhum arquivo do acervo
  HASH_CONFERE  hash citado que bate com um arquivo do acervo
Uso: python3 -I tpl_lacunas_v0_3.py ACERVO ENTRADA |  python3 -I tpl_lacunas_v0_3.py autoteste
Só biblioteca padrão. Estados textuais.
v0.3 (31/10/2026, Claude, Árbitro 2): única mudança = toda gravação de arquivo do autoteste fecha o arquivo (with open). No PyPy, open(...).write() sem fechar deixava o arquivo vazio na leitura seguinte (run 41189589674).
v0.2 (30/10/2026, Claude, Árbitro 2): base tpl_lacunas.py v0.1 (8aacd519..., selado, não alterado).
  Defeito medido no Windows: o autoteste gravava em modo texto; o Windows grava CRLF e cp1252,
  o hash dos bytes deixava de bater (2 de 6 casos falhavam). Agora grava UTF-8 com LF explícito.
"""
import hashlib, os, re, sys, tempfile

HEX = re.compile(r"\b[0-9a-f]{64}\b")
NOME = re.compile(r"\b[\w\-]+\.(?:py|js|html|json|md|yml|txt)\b")
BLOCO = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def norm(t):
    return "\n".join(l.rstrip() for l in t.replace("\r\n", "\n").strip().splitlines())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def indexar(acervo):
    bytes_h, norm_h, nomes = {}, {}, set()
    for raiz, _, arqs in os.walk(acervo):
        if "/.git" in raiz:
            continue
        for a in arqs:
            p = os.path.join(raiz, a)
            b = open(p, "rb").read()
            bytes_h[sha(b)] = p
            norm_h[sha(norm(b.decode("utf-8", "replace")).encode())] = p
            nomes.add(a)
    return bytes_h, norm_h, nomes


def analisar(acervo, entrada):
    bytes_h, norm_h, nomes = indexar(acervo)
    itens = []
    for raiz, _, arqs in os.walk(entrada):
        for a in sorted(arqs):
            p = os.path.join(raiz, a)
            t = open(p, encoding="utf-8", errors="replace").read()
            for m in BLOCO.finditer(t):
                linha = t.count("\n", 0, m.start()) + 1
                corpo = m.group(1)
                if len(corpo.strip().splitlines()) < 5:
                    continue
                h = sha(norm(corpo).encode())
                est = ("JA_GUARDADO", norm_h[h]) if h in norm_h else ("LACUNA", "bloco de código sem arquivo no acervo")
                itens.append((est[0], "%s:%d" % (a, linha), est[1]))
            for h in sorted(set(HEX.findall(t))):
                linha = t.count("\n", 0, t.find(h)) + 1
                itens.append(("HASH_CONFERE", "%s:%d" % (a, linha), bytes_h[h]) if h in bytes_h
                             else ("HASH_SEM_BASE", "%s:%d" % (a, linha), h[:8] + "..." + h[-4:]))
            for n in sorted(set(NOME.findall(t)) - nomes):
                linha = t.count("\n", 0, t.find(n)) + 1
                itens.append(("LACUNA", "%s:%d" % (a, linha), "arquivo citado e ausente: " + n))
    return itens


def autoteste():
    with tempfile.TemporaryDirectory() as d:
        ac, en = os.path.join(d, "a"), os.path.join(d, "e")
        os.makedirs(ac); os.makedirs(en)
        cod = "def f(x):\n    a = 1\n    b = 2\n    c = 3\n    return x + a + b + c\n"
        with open(os.path.join(ac, "f.py"), "w", encoding="utf-8", newline="\n") as _f: _f.write(cod)
        h = sha(cod.encode())
        chat = ("Codigo:\n```python\n" + cod.replace("\n", "  \n") + "```\n"
                "Outro:\n```python\ndef g():\n    1\n    2\n    3\n    return 4\n```\n"
                "hash do f: " + h + "\nhash inventado: " + "ab" * 32 + "\nver tpl_fantasma.py e f.py\n")
        with open(os.path.join(en, "gemini.txt"), "w", encoding="utf-8", newline="\n") as _f: _f.write(chat)
        r = analisar(ac, en)
        est = sorted(e for e, _, _ in r)
        casos = [
            ("bloco igual ao acervo (com espaços no fim) = JA_GUARDADO", est.count("JA_GUARDADO") == 1),
            ("bloco novo = LACUNA", any(e == "LACUNA" and "bloco" in x for e, _, x in r)),
            ("hash verdadeiro = HASH_CONFERE", est.count("HASH_CONFERE") == 1),
            ("hash inventado = HASH_SEM_BASE", est.count("HASH_SEM_BASE") == 1),
            ("arquivo citado ausente = LACUNA", any("tpl_fantasma.py" in x for _, _, x in r)),
            ("arquivo citado presente nao vira lacuna", not any(x.endswith(" f.py") for _, _, x in r)),
        ]
        f = [m for m, ok in casos if not ok]
        for m, ok in casos:
            print(("OK    " if ok else "FALHA ") + m)
        print("ESTADO: " + ("DIVERGENTE" if f else "PROVADO (6/6)"))
        return 1 if f else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["autoteste"]:
        sys.exit(autoteste())
    if len(a) != 2:
        sys.exit(__doc__)
    r = analisar(*a)
    for e, onde, x in r:
        print("%-13s %-28s %s" % (e, onde, x))
    from collections import Counter
    print("RESUMO:", dict(Counter(e for e, _, _ in r)))
