"""tpl_invariantes.py v1 - o nucleo de invariantes do TPL medido por codigo.
Escrito por Claude (Arbitro 2), 03/11/2026. Especificacao: TPL_NUCLEO_INVARIANTES_v1.md.
Autor nao verifica a si mesmo (R2): este arquivo so vale como VERIFICADO quando outro executor o rodar.

  python -I tpl_invariantes.py estado <repo>              N1-N6 no tpl_estado.json atual
  python -I tpl_invariantes.py historia <repo> <base> <novo>   N7: o registro so cresce
  python -I tpl_invariantes.py auditoria <repo>           N7 sobre toda a historia do registro
  python -I tpl_invariantes.py autoteste                  N9: cada invariante pega o proprio erro

Tres niveis: VIOLACAO (exit 1), LACUNA (registrada, nao reprova na v1), OK.
So biblioteca padrao. Saida deterministica: mesma entrada, mesmos bytes.
"""
import hashlib, json, os, re, subprocess, sys, tempfile

EXECUCAO = ("VERIFICADO", "DIVERGENTE", "NAO EXECUTADO", "MENCIONADO")
CAMPOS = ("repositorio", "arquivo", "sha256", "estado", "executor", "evidencia")
HEX64 = re.compile(r"[0-9a-f]{64}")
# registro publico reexaminavel: id de execucao (>= 9 digitos), commit (>= 7 hex) ou sha256
REGISTRO = re.compile(r"\b\d{9,}\b|\b[0-9a-f]{7,40}\b|\b[0-9a-f]{64}\b")
NOME_REPO = "-TPL-"


def _ler(p):
    with open(p, "rb") as f:
        return f.read()


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def medir_estado(est, raiz):
    """N1-N6. Devolve (violacoes, lacunas, n_atuais)."""
    viol, lac = [], []
    arts = est.get("artefatos")
    if not isinstance(arts, list):
        return ["N1 registro sem lista 'artefatos'"], [], 0
    atual = {}
    for i, a in enumerate(arts):
        tag = "#%d %s" % (i, a.get("arquivo") if isinstance(a, dict) else "?")
        if not isinstance(a, dict) or any(c not in a for c in CAMPOS):
            viol.append("N1 %s: faltam campos" % tag); continue
        if not HEX64.fullmatch(str(a["sha256"])):
            viol.append("N1 %s: sha256 invalido" % tag)
        if a["estado"] not in EXECUCAO:
            viol.append("N2 %s: estado fora da lista: %r" % (tag, a["estado"]))
        atual[(a["repositorio"], a["arquivo"])] = (i, a)          # N3: prevalece o ultimo
    for (repo, arq), (i, a) in sorted(atual.items()):
        tag = "#%d %s" % (i, arq)
        if repo == NOME_REPO and raiz is not None:
            p = os.path.join(raiz, arq)
            if not os.path.isfile(p):
                viol.append("N3 %s: registro atual aponta arquivo inexistente" % tag)
            elif _sha(_ler(p)) != a["sha256"]:
                viol.append("N3 %s: bytes diferem do registro atual" % tag)
        if a["estado"] == "VERIFICADO":
            ex = str(a["executor"]).strip()
            if not ex:
                viol.append("N4 %s: VERIFICADO sem executor" % tag)
            elif a.get("autor"):
                if str(a["autor"]).strip().lower() in ex.lower():
                    viol.append("N4 %s: executor contem o autor (%s)" % (tag, a["autor"]))
            else:
                lac.append("N4 %s: autor nao registrado; independencia nao demonstravel" % tag)
            if ex and not REGISTRO.search(ex + " " + str(a["evidencia"])):
                lac.append("N5 %s: VERIFICADO sem registro publico reexaminavel (run/commit/hash)" % tag)
        if a["estado"] in ("DIVERGENTE", "NAO EXECUTADO") and not str(a["evidencia"]).strip():
            viol.append("N6 %s: %s sem motivo na evidencia" % (tag, a["estado"]))
    return viol, lac, len(atual)


def comparar_historia(antes, depois):
    """N7: o registro so cresce. Toda entrada anterior continua identica e na mesma posicao."""
    a, b = antes.get("artefatos", []), depois.get("artefatos", [])
    if len(b) < len(a):
        return ["N7 registro encolheu: %d -> %d entradas" % (len(a), len(b))]
    return ["N7 entrada #%d (%s) reescrita no lugar" % (i, x.get("arquivo"))
            for i, (x, y) in enumerate(zip(a, b)) if x != y]


def _estado_em(repo, commit):
    r = subprocess.run(["git", "-C", repo, "show", commit + ":tpl_estado.json"], capture_output=True)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout.decode("utf-8"))


def _relatorio(titulo, viol, lac, extra):
    print("TPL_INVARIANTES v1 |", titulo)
    print("nucleo sha256:", _sha(_ler(os.path.abspath(__file__))))
    for linha in extra:
        print(linha)
    for v in viol:
        print("  VIOLACAO", v)
    for l in lac:
        print("  LACUNA  ", l)
    print("violacoes:", len(viol), "| lacunas:", len(lac))
    print("RESULTADO:", "CUMPRE" if not viol else "NAO CUMPRE")
    return 0 if not viol else 1


def autoteste():
    """N9. Cada invariante tem um caso que precisa passar e um erro que precisa pegar."""
    ok, total = 0, 0

    def caso(nome, cond):
        nonlocal ok, total
        total += 1; ok += bool(cond)
        if not cond:
            print("  FALHOU:", nome)

    h1, h2 = _sha(b"a\n"), _sha(b"b\n")
    base = lambda **k: dict({"repositorio": NOME_REPO, "arquivo": "a.py", "sha256": h1,
                             "estado": "NAO EXECUTADO", "executor": "", "evidencia": "so o autor rodou"}, **k)
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.py"), "wb") as f:
            f.write(b"a\n")
        m = lambda arts: medir_estado({"artefatos": arts}, d)
        caso("registro limpo cumpre", m([base()])[0] == [])
        caso("N1 pega campo faltando", any(v.startswith("N1") for v in m([{"arquivo": "a.py"}])[0]))
        caso("N1 pega sha256 curto", any(v.startswith("N1") for v in m([base(sha256="abc")])[0]))
        caso("N2 pega estado inventado", any(v.startswith("N2") for v in m([base(estado="QUASE")])[0]))
        caso("N3 pega bytes mudados", any(v.startswith("N3") for v in m([base(sha256=h2)])[0]))
        caso("N3 pega arquivo inexistente", any(v.startswith("N3") for v in m([base(arquivo="x.py")])[0]))
        caso("N3 ultimo prevalece (historia com hash antigo nao reprova)",
             m([base(sha256=h2), base()])[0] == [])
        ver = base(estado="VERIFICADO", executor="GitHub Actions run 123456789", evidencia="ok")
        caso("N4 pega VERIFICADO sem executor", any(v.startswith("N4") for v in m([base(estado="VERIFICADO")])[0]))
        caso("N4 pega autor verificando a si mesmo",
             any(v.startswith("N4") for v in m([dict(ver, autor="Claude", executor="Claude, run 123456789")])[0]))
        caso("N4 autor diferente do executor cumpre", m([dict(ver, autor="ChatGPT")]) [0:2] == ([], []))
        caso("N4 sem autor vira lacuna, nao violacao",
             m([ver])[0] == [] and any(l.startswith("N4") for l in m([ver])[1]))
        caso("N5 pega VERIFICADO sem registro publico",
             any(l.startswith("N5") for l in m([dict(ver, autor="X", executor="alguem", evidencia="confia")])[1]))
        caso("N6 pega DIVERGENTE sem motivo", any(v.startswith("N6") for v in m([base(estado="DIVERGENTE", evidencia="")])[0]))
        caso("N8 rebaixar VERIFICADO para DIVERGENTE e permitido",
             m([dict(ver, autor="X"), base(estado="DIVERGENTE", evidencia="nao reproduziu")])[0] == [])
    a = {"artefatos": [base()]}
    caso("N7 acrescentar no fim cumpre", comparar_historia(a, {"artefatos": [base(), base(arquivo="b.py")]}) == [])
    caso("N7 pega reescrita no lugar", comparar_historia(a, {"artefatos": [base(estado="VERIFICADO")]}) != [])
    caso("N7 pega entrada apagada", comparar_historia(a, {"artefatos": []}) != [])
    print("AUTOTESTE_TPL_INVARIANTES: %d / %d" % (ok, total))
    return ok == total


def main(argv):
    if argv[:1] == ["autoteste"]:
        return 0 if autoteste() else 1
    if argv[:1] == ["estado"] and len(argv) == 2:
        raiz = argv[1]
        p = os.path.join(raiz, "tpl_estado.json")
        est = json.loads(_ler(p).decode("utf-8"))
        viol, lac, n = medir_estado(est, raiz)
        return _relatorio("estado", viol, lac, ["registro sha256: " + _sha(_ler(p)),
                                                "entradas: %d | artefatos atuais: %d" % (len(est.get("artefatos", [])), n)])
    if argv[:1] == ["historia"] and len(argv) == 4:
        repo, b, n = argv[1:]
        antes, depois = _estado_em(repo, b), _estado_em(repo, n)
        if antes is None or depois is None:
            return _relatorio("historia", [], [], ["registro ausente em %s; N7 nao se aplica" % (b if antes is None else n)])
        return _relatorio("historia", comparar_historia(antes, depois), [], ["base %s -> novo %s" % (b, n)])
    if argv[:1] == ["auditoria"] and len(argv) == 2:
        repo = argv[1]
        cs = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=%H", "HEAD", "--", "tpl_estado.json"],
                            capture_output=True, text=True, check=True).stdout.split()
        viol, prev = [], None
        for c in cs:
            atual = _estado_em(repo, c)
            if prev is not None and atual is not None:
                viol += ["%s: %s" % (c[:12], v) for v in comparar_historia(prev, atual)]
            prev = atual
        return _relatorio("auditoria", viol, [], ["commits do registro examinados: %d" % len(cs)])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
