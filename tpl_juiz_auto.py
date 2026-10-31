"""tpl_juiz_auto.py v3 - TPL: o arbitro dentro do proprio TPL.

O gabarito nao e escrito na hora: e a saida do commit BASE (ja no main, selado pelo git).
O commit NOVO e medido contra ele pelo GitHub Actions (executor que nao e o autor, R2).

  python -I tpl_juiz_auto.py BASE_DIR BASE_SHA NOVO_DIR NOVO_SHA    compara e emite o veredito
  python -I tpl_juiz_auto.py autoteste

Regras (fail-closed; v2 corrige J01-J08 da revisao do ChatGPT de 31/10/2026):
  IGUAL   stdout, stderr e codigo de saida identicos no BASE e no NOVO         -> passa
  MUDOU   saida diferente: passa SO se tpl_mudancas.json do NOVO declarar antes, para esse comando,
          o sha256 exato da nova saida OU {"linha": "<linha exata do stdout>"} (gabarito previo;
          a forma "linha" serve quando a saida traz a versao do interpretador)  -> senao DIVERGENTE
  v3: no CI, quem julga e o juiz do BASE (main); um PR nao pode afrouxar o proprio juiz.
  NOVO    script inexistente no BASE: passa se codigo 0 e a saida estiver declarada em tpl_mudancas.json
  FALHOU  codigo diferente de 0 no NOVO, timeout, ou BASE quebrado            -> DIVERGENTE
  P0      tpl_p0_v2.py no NOVO: exige codigo 0 E a linha exata "P0: CUMPRE" E "fora_do_estado: 0"
  IDENT   git rev-parse HEAD de cada pasta tem de ser o sha informado; git falho -> DIVERGENTE
Normalizacao unica: a linha "Ran N tests in X.XXXs" do unittest (tempo de relogio).
Limite declarado: python -I nao e sandbox; o isolamento real e a maquina descartavel do Actions.
Escrito por Claude (Arbitro 2), 31/10/2026. So biblioteca padrao.
"""
import hashlib, json, os, re, subprocess, sys, tempfile

PRE = "import sys; sys.path.insert(0, '.'); "
COMANDOS = [
    ("cadeia", "tpl_cadeia.py", []),
    ("malha_v0_3", "tpl_malha_v0_3.py", ["-c", PRE + "import tpl_malha_v0_3 as m; print('AUTOTESTE_TPL_MALHA_V0_3:', m.autoteste(), '/ 14')"]),
    ("malha_v0_4", "tpl_malha_v0_4.py", []),
    ("arbitro_v3_2", "tpl_arbitro_v3_2.py", ["autoteste"]),
    ("nucleo_v4", "NucleoTPLPMVA_CORRIGIDO_v4.py", ["--self-test"]),
    ("fala", "tpl_fala.py", ["autoteste"]),
    ("lacunas_v0_2", "tpl_lacunas_v0_2.py", ["autoteste"]),
    ("sintaxe", "tpl_sintaxe.py", ["autoteste"]),
    ("acervo", "acervo/acervo_tpl.py", ["autoteste"]),
    ("curto", "tpl_curto.py", []),
    ("bateria3", "bateria3.py", []),
    ("portal", "tpl_phi_omega_portal.py", []),
    ("mapa_v2", "tpl_phi_omega_mapa_v2.py", []),
    ("p0_autoteste", "tpl_p0_v2.py", ["autoteste"]),
    ("arbitro_v3_3", "tpl_arbitro_v3_3.py", ["autoteste"]),
]
TIMEOUT = 600
# Unico trecho variavel conhecido: o tempo que o unittest imprime. Normalizado so nesta forma exata.
TEMPO = re.compile(rb"^(Ran \d+ tests? in )\d+\.\d+s$", re.M)


def git(d, *a):
    r = subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("git %s falhou em %s" % (" ".join(a), d))
    return r.stdout


def rodar(raiz, script, args):
    if not os.path.exists(os.path.join(raiz, script)):
        return None
    cmd = [sys.executable, "-I", "-X", "utf8"] + (args if args[:1] == ["-c"] else [script] + args)
    try:
        r = subprocess.run(cmd, cwd=raiz, capture_output=True, timeout=TIMEOUT)
        norm = lambda b: TEMPO.sub(rb"\1<t>s", b.replace(b"\r\n", b"\n"))
        corpo = b"RC=%d\n--STDOUT--\n" % r.returncode + norm(r.stdout) + b"\n--STDERR--\n" + norm(r.stderr)
        return r.returncode, hashlib.sha256(corpo).hexdigest(), norm(r.stdout).decode("utf-8", "replace").split("\n")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT", []


def julgar(base, base_sha, novo, novo_sha):
    linhas, ok = [], True
    try:
        for d, s, rot in ((base, base_sha, "BASE"), (novo, novo_sha, "NOVO")):
            real = git(d, "rev-parse", "HEAD").strip()
            if real != s:
                return [("IDENT", "DIVERGENTE", "%s e %s, esperado %s" % (rot, real, s))], False
        linhas.append(("IDENT", "OK", "base %s / novo %s" % (base_sha[:12], novo_sha[:12])))
    except Exception as e:
        return [("IDENT", "DIVERGENTE", str(e))], False
    try:
        decl = json.load(open(os.path.join(novo, "tpl_mudancas.json"), encoding="utf-8"))
    except FileNotFoundError:
        decl = {}
    except Exception as e:
        return linhas + [("tpl_mudancas.json", "DIVERGENTE", "ilegivel: " + type(e).__name__)], False
    for nome, script, args in COMANDOS:
        n = rodar(novo, script, args)
        if n is None:
            linhas.append((nome, "AUSENTE", "script nao existe no NOVO")); ok = False; continue
        b = rodar(base, script, args)
        if n[0] != 0:
            est, nota = "FALHOU", "codigo %s no NOVO" % n[0]
        elif b is not None and b[0] != 0:
            est, nota = "FALHOU", "BASE quebrado (codigo %s): gabarito invalido" % b[0]
        elif b is not None and b[1] == n[1]:
            est, nota = "IGUAL", n[1][:16]
        elif decl.get(nome) == n[1] or (isinstance(decl.get(nome), dict) and decl[nome].get("linha") in n[2]):
            est, nota = ("NOVO" if b is None else "MUDOU"), "declarado antes em tpl_mudancas.json: %s" % (n[1][:16] if decl.get(nome) == n[1] else repr(decl[nome]["linha"]))
        else:
            est, nota = "FALHOU", "saida %s nao declarada (%s)" % (n[1][:16], "sem BASE" if b is None else "BASE " + b[1][:16])
        ok = ok and est in ("IGUAL", "MUDOU", "NOVO")
        linhas.append((nome, est, nota))
    p0s = os.path.join(novo, "tpl_p0_v2.py")
    try:
        p0 = subprocess.run([sys.executable, "-I", "-X", "utf8", p0s, novo], capture_output=True, text=True, timeout=TIMEOUT) if os.path.exists(p0s) else None
    except subprocess.TimeoutExpired:
        p0 = None
    saida = p0.stdout.replace("\r\n", "\n").splitlines() if p0 else []
    p0_ok = p0 is not None and p0.returncode == 0 and "P0: CUMPRE" in saida and "fora_do_estado: 0" in saida
    linhas.append(("P0", "CUMPRE" if p0_ok else "FALHA", saida[-1] if saida else "sem saida (ausente ou timeout)"))
    return linhas, ok and p0_ok


def autoteste():
    casos = []
    with tempfile.TemporaryDirectory() as t:
        def repo(nome, arquivos):
            d = os.path.join(t, nome); os.makedirs(d)
            for f, c in arquivos.items():
                open(os.path.join(d, f), "w").write(c)
            for a in (["init", "-q"], ["add", "."], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"]):
                subprocess.run(["git", "-C", d] + a, capture_output=True)
            return d, git(d, "rev-parse", "HEAD").strip()
        p0_bom = "print('universo: 1 | excluidos: 0'); print('fora_do_estado: 0'); print('P0: CUMPRE')\n"
        p0_mente = "print('fora_do_estado: 3'); print('P0: FALHA')\n"   # FALHA com codigo 0 (J01)
        global COMANDOS
        salvo = COMANDOS
        COMANDOS = [("a", "a.py", []), ("n", "n.py", [])]
        try:
            B = repo("base", {"a.py": "print(1)\n", "tpl_p0_v2.py": p0_bom})
            def r(arqs, nome, decl=None, sha_errado=False):
                if decl is not None:
                    arqs = dict(arqs, **{"tpl_mudancas.json": json.dumps(decl)})
                N = repo(nome, arqs)
                lin, ok = julgar(B[0], B[1], N[0], "0" * 40 if sha_errado else N[1])
                return {x: e for x, e, _ in lin}, ok
            base_arqs = {"a.py": "print(1)\n", "n.py": "print(5)\n", "tpl_p0_v2.py": p0_bom}
            sha_n = rodar(B[0], "a.py", [])  # referencia de formato
            # n.py nao existe no BASE: so passa se a saida estiver declarada
            d_tmp, _ = repo("tmp", base_arqs); sha_n5 = rodar(d_tmp, "n.py", [])[1]
            res, ok = r(base_arqs, "c1", {"n": sha_n5}); casos.append(res["a"] == "IGUAL" and res["n"] == "NOVO" and ok)
            res, ok = r(base_arqs, "c2"); casos.append(res["n"] == "FALHOU" and not ok)                      # NOVO nao declarado
            mud = dict(base_arqs, **{"a.py": "print(9)\n"})
            res, ok = r(mud, "c3", {"n": sha_n5}); casos.append(res["a"] == "FALHOU" and not ok)               # J06: mudou sem declarar
            d_tmp2, _ = repo("tmp2", mud); sha_a9 = rodar(d_tmp2, "a.py", [])[1]
            res, ok = r(mud, "c4", {"n": sha_n5, "a": sha_a9}); casos.append(res["a"] == "MUDOU" and ok)        # mudou declarado
            res, ok = r(dict(base_arqs, **{"a.py": "import sys; print(1); sys.stderr.write('x')\n"}), "c5", {"n": sha_n5}); casos.append(res["a"] == "FALHOU")  # J04: stderr conta
            res, ok = r(dict(base_arqs, **{"tpl_p0_v2.py": p0_mente}), "c6", {"n": sha_n5}); casos.append(res["P0"] == "FALHA" and not ok)  # J01
            res, ok = r(dict(base_arqs, **{"a.py": "import sys; sys.exit(2)\n"}), "c7", {"n": sha_n5}); casos.append(res["a"] == "FALHOU")  # codigo != 0
            res, ok = r(base_arqs, "c8", {"n": sha_n5}, sha_errado=True); casos.append(res.get("IDENT") == "DIVERGENTE" and not ok)  # J07
            semp0 = {k: v for k, v in base_arqs.items() if k != "tpl_p0_v2.py"}
            res, ok = r(semp0, "c9", {"n": sha_n5}); casos.append(res["P0"] == "FALHA" and not ok)              # P0 ausente
            tempo = dict(base_arqs, **{"a.py": "import sys; print(1); sys.stderr.write('Ran 3 tests in 0.%d01s\\n' % (len(sys.argv) + 4))\n"})
            d_t1, _ = repo("t1", dict(base_arqs, **{"a.py": "import sys; print(1); sys.stderr.write('Ran 3 tests in 0.001s\\n')\n"}))
            casos.append(rodar(d_t1, "a.py", [])[1] == rodar(repo("t2", tempo)[0], "a.py", [])[1])          # so o tempo do unittest e normalizado
            res, ok = r(base_arqs, "c11", {"n": {"linha": "5"}}); casos.append(res["n"] == "NOVO" and ok)            # v3: linha exata declarada
            res, ok = r(base_arqs, "c12", {"n": {"linha": "6"}}); casos.append(res["n"] == "FALHOU" and not ok)      # v3: linha errada
            os.makedirs(os.path.join(t, "naogit"))
            lin, ok = julgar(B[0], B[1], os.path.join(t, "naogit"), "x"); casos.append(not ok and lin[0][1] == "DIVERGENTE")  # J05
        finally:
            COMANDOS = salvo
    n = sum(casos)
    print("AUTOTESTE_TPL_JUIZ_AUTO_V3:", n, "/", len(casos))
    return n == len(casos) == 13


if __name__ == "__main__":
    if sys.argv[1:] == ["autoteste"]:
        sys.exit(0 if autoteste() else 1)
    linhas, ok = julgar(*sys.argv[1:5])
    print("| comando | estado | nota |\n|---|---|---|")
    for n, e, nota in linhas:
        print("| %s | %s | %s |" % (n, e, nota))
    print("\nVEREDITO:", "CONFORME" if ok else "DIVERGENTE")
    sys.exit(0 if ok else 1)
