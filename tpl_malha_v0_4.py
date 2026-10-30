"""TPL-MALHA v0.4 - medicao de independencia entre verificacoes (corrige P-01 e P-02 do PR #13).
Base: tpl_malha_v0_3.py (selado em 7fbb325, nao alterado). Regras herdadas:
- confirmacoes da mesma origem do autor contam como AUTOMEDICAO (uma so medicao);
- qualquer divergencia (hash diferente ou selo nao VERIFICADO) prevalece: DIVERGENTE.
Correcoes da v0.4 (30/10/2026):
- P-02: a saida bruta precisa ter EXATAMENTE uma linha HASH e EXATAMENTE uma linha RESULTADO.
  Linha repetida, contraditoria ou ausente -> BLOQUEADO_COM_MOTIVO (fail-closed).
- P-01: um nome de origem diferente do autor NAO prova independencia. Sem atestado verificavel,
  a origem externa vale como EXTERNA_NAO_AUTENTICADA, nunca como INDEPENDENTE.
  A verificacao criptografica de atestados ainda nao existe nesta versao (NAO EXECUTADO);
  por isso INDEPENDENTE so e alcancavel quando essa verificacao for implementada (v0.5).
Uso: python tpl_malha_v0_4.py --extrato PIN origem1=saida1.txt origem2=saida2.txt ..."""
import re
import sys
from enum import Enum


class Grau(Enum):
    SEM_MEDICAO = "SEM_MEDICAO"
    AUTOMEDICAO = "AUTOMEDICAO"
    EXTERNA_NAO_AUTENTICADA = "EXTERNA_NAO_AUTENTICADA"
    INDEPENDENTE = "INDEPENDENTE"
    DIVERGENTE = "DIVERGENTE"
    INVALIDO = "INVALIDO"

    def __bool__(self):
        raise TypeError("Grau nao e booleano: compare com Grau.X")


_HEX = r"[0-9a-f]{64}"


def _motivo_invalido(autor, pin, registro):
    if not (isinstance(autor, str) and autor.strip()):
        return "autor ausente"
    if not (isinstance(pin, str) and re.fullmatch(_HEX, pin) is not None):
        return "pin invalido"
    if not isinstance(registro, list):
        return "registro nao e lista"
    for r in registro:
        if not (isinstance(r, dict) and isinstance(r.get("origem"), str) and r["origem"].strip()
                and isinstance(r.get("sha256"), str) and isinstance(r.get("selo"), str)):
            return "entrada malformada: " + repr(r)
    return None


def atestado_verificado(medicao):
    """Verificacao criptografica de origem: ainda nao implementada. Fail-closed: sempre False."""
    return False


def medir(autor, pin, registro):
    motivo = _motivo_invalido(autor, pin, registro)
    if motivo is not None:
        return Grau.INVALIDO, motivo
    diverge = sorted({r["origem"] for r in registro
                      if r["sha256"] != pin or r["selo"] != "VERIFICADO"})
    if len(diverge) > 0:
        return Grau.DIVERGENTE, "divergem: " + ", ".join(diverge)
    origens = {r["origem"] for r in registro}
    if len(origens) == 0:
        return Grau.SEM_MEDICAO, "nenhuma medicao registrada"
    externas = sorted(origens - {autor})
    if len(externas) == 0:
        return Grau.AUTOMEDICAO, "so o autor mediu (" + autor + "): uma medicao, nao duas"
    atestadas = sorted({r["origem"] for r in registro if r["origem"] != autor and atestado_verificado(r)})
    if len(atestadas) > 0:
        return Grau.INDEPENDENTE, "confirmado por origem externa atestada: " + ", ".join(atestadas)
    return Grau.EXTERNA_NAO_AUTENTICADA, "origem externa so declarada (nome nao prova identidade): " + ", ".join(externas)


_LINHA_HASH = re.compile(r"^HASH tpl_coerencia_v1_4\.py ([0-9a-f]{64}) (OK|DIVERGE)$", re.MULTILINE)
_LINHA_RESULTADO = re.compile(r"^RESULTADO: (REPRODUZIDO|DIVERGENTE)$", re.MULTILINE)
_QUALQUER_HASH = re.compile(r"^HASH\b", re.MULTILINE)
_QUALQUER_RESULTADO = re.compile(r"^RESULTADO\b", re.MULTILINE)


def de_saida(origem, texto):
    """Converte a saida bruta numa medicao. Exige exatamente uma linha HASH e uma linha RESULTADO validas."""
    if not isinstance(texto, str):
        return {"origem": origem, "sha256": "", "selo": "BLOQUEADO_COM_MOTIVO", "motivo": "saida nao e texto"}
    hs = _LINHA_HASH.findall(texto)
    rs = _LINHA_RESULTADO.findall(texto)
    n_h = len(_QUALQUER_HASH.findall(texto))
    n_r = len(_QUALQUER_RESULTADO.findall(texto))
    if len(hs) != 1 or n_h != 1:
        return {"origem": origem, "sha256": "", "selo": "BLOQUEADO_COM_MOTIVO", "motivo": "linhas HASH: %d (exige 1 valida)" % n_h}
    if len(rs) != 1 or n_r != 1:
        return {"origem": origem, "sha256": hs[0][0], "selo": "BLOQUEADO_COM_MOTIVO", "motivo": "linhas RESULTADO: %d (exige 1 valida)" % n_r}
    sha, estado_hash = hs[0]
    ok = estado_hash == "OK" and rs[0] == "REPRODUZIDO"
    return {"origem": origem, "sha256": sha, "selo": "VERIFICADO" if ok else "BLOQUEADO_COM_MOTIVO",
            "motivo": "" if ok else "hash ou resultado nao conferem"}


def autoteste():
    p, a = "a" * 64, "claude-arbitro2"
    n = 0
    def ok(cond):
        nonlocal n
        assert cond
        n += 1
    v = lambda o, s=p, selo="VERIFICADO": {"origem": o, "sha256": s, "selo": selo}
    ok(medir(a, p, [])[0] is Grau.SEM_MEDICAO)
    ok(medir(a, p, [v(a)])[0] is Grau.AUTOMEDICAO)
    ok(medir(a, p, [v(a), v(a)])[0] is Grau.AUTOMEDICAO)
    ok(medir(a, p, [v("chatgpt-executor", "b" * 64)])[0] is Grau.DIVERGENTE)
    ok(medir(a, p, [v("chatgpt-executor", p, "BLOQUEADO_COM_MOTIVO")])[0] is Grau.DIVERGENTE)
    ok(medir(a, p, [v("x"), v("y", "c" * 64)])[0] is Grau.DIVERGENTE)
    ok(medir("", p, [])[0] is Grau.INVALIDO)
    ok(medir(a, "A" * 64, [])[0] is Grau.INVALIDO)
    ok(medir(a, p, [v("")])[0] is Grau.INVALIDO)
    ok(medir(a, p, "nao-lista")[0] is Grau.INVALIDO)
    # P-01: nome diferente do autor nao vira INDEPENDENTE
    ok(medir(a, p, [v(a), v("chatgpt-executor")])[0] is Grau.EXTERNA_NAO_AUTENTICADA)
    ok(medir(a, p, [v("origem-inventada")])[0] is Grau.EXTERNA_NAO_AUTENTICADA)
    linha_h = "HASH tpl_coerencia_v1_4.py " + p + " OK\n"
    boa = linha_h + "RESULTADO: REPRODUZIDO\n"
    ok(de_saida("x", boa)["selo"] == "VERIFICADO" and de_saida("x", boa)["sha256"] == p)
    ok(de_saida("x", boa.replace("REPRODUZIDO", "DIVERGENTE"))["selo"] == "BLOQUEADO_COM_MOTIVO")
    ok(de_saida("x", "texto sem saida")["selo"] == "BLOQUEADO_COM_MOTIVO")
    # P-02: o caso adversarial do PR #13 (verificado em 30/10/2026 contra a v0.3)
    contraditoria = linha_h + "RESULTADO: REPRODUZIDO\nRESULTADO: DIVERGENTE\n"
    ok(de_saida("origem-inventada", contraditoria)["selo"] == "BLOQUEADO_COM_MOTIVO")
    ok(medir(a, p, [de_saida("origem-inventada", contraditoria)])[0] is Grau.DIVERGENTE)
    ok(de_saida("x", linha_h + linha_h + "RESULTADO: REPRODUZIDO\n")["selo"] == "BLOQUEADO_COM_MOTIVO")
    ok(de_saida("x", boa + "RESULTADO: REPRODUZIDO\n")["selo"] == "BLOQUEADO_COM_MOTIVO")
    ok(de_saida("x", boa + "HASH outro.py " + p + " OK\n")["selo"] == "BLOQUEADO_COM_MOTIVO")
    ok(de_saida("x", None)["selo"] == "BLOQUEADO_COM_MOTIVO")
    try:
        bool(Grau.INDEPENDENTE)
    except TypeError:
        n += 1
        return n
    raise AssertionError("bool() permitido")


def _extrato(args):
    if len(args) < 1:
        raise SystemExit("TPL-MALHA FAIL-CLOSED: --extrato exige PIN e saidas")
    pin, medicoes = args[0], []
    for par in args[1:]:
        origem, _, caminho = par.partition("=")
        try:
            with open(caminho, encoding="utf-8") as f:
                medicoes.append(de_saida(origem, f.read()))
        except (OSError, UnicodeDecodeError) as e:
            raise SystemExit("TPL-MALHA FAIL-CLOSED: saida ilegivel: " + caminho) from e
    for m in medicoes:
        print("  ", m["origem"], "|", m["selo"], "|", m["sha256"][:16], "|", m.get("motivo", ""))
    grau, motivo = medir("claude-arbitro2", pin, medicoes)
    print("GRAU DA MALHA:", grau.name, "|", motivo)
    return 0 if grau is Grau.INDEPENDENTE else 1


def main(argv):
    n = autoteste()
    print("AUTOTESTE_TPL_MALHA_V0_4:", n, "/ 22")
    if len(argv) >= 1 and argv[0] == "--extrato":
        return _extrato(argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
