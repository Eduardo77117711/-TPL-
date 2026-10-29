"""TPL-MALHA v0.3 - medicao de independencia entre verificacoes.
Principio do fundador (27/10/2026): medir dois estados entrelacados e medir a mesma coisa;
quem acha que mede duas coisas esta medindo uma so.
Regra: confirmacoes que vem da mesma origem do artefato contam como AUTOMEDICAO (uma so medicao).
So ha INDEPENDENTE quando pelo menos uma origem diferente do autor confirma o mesmo pin.
Qualquer divergencia (hash diferente ou selo nao VERIFICADO) prevalece: DIVERGENTE.
v0.3 (malha unida, como contas conectadas por um protocolo comum): cada tela roda referencia_tpl_27out.py
e cola a saida bruta num arquivo; o extrato le todas as saidas e mede a malha inteira de uma vez.
Uso: python tpl_malha.py registro.json
     python tpl_malha.py --extrato PIN origem1=saida1.txt origem2=saida2.txt ..."""
import json
import re
import sys
from enum import Enum


class Grau(Enum):
    SEM_MEDICAO = "SEM_MEDICAO"
    AUTOMEDICAO = "AUTOMEDICAO"
    INDEPENDENTE = "INDEPENDENTE"
    DIVERGENTE = "DIVERGENTE"
    INVALIDO = "INVALIDO"

    def __bool__(self):
        raise TypeError("Grau nao e booleano: compare com Grau.X")


_HEX = r"[0-9a-f]{64}"


def _motivo_invalido(autor, pin, registro):
    """Devolve o motivo de invalidade da entrada, ou None se ela for bem formada."""
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
    return Grau.INDEPENDENTE, "confirmado por origem externa: " + ", ".join(externas)


_LINHA_HASH = re.compile(r"^HASH tpl_coerencia_v1_4\.py ([0-9a-f]{64}) (OK|DIVERGE)$", re.MULTILINE)
_LINHA_RESULTADO = re.compile(r"^RESULTADO: (REPRODUZIDO|DIVERGENTE)$", re.MULTILINE)


def de_saida(origem, texto):
    """Converte a saida bruta de referencia_tpl_27out.py numa medicao da malha."""
    h = _LINHA_HASH.search(texto)
    r = _LINHA_RESULTADO.search(texto)
    sha = h.group(1) if h is not None else ""
    selo = "VERIFICADO" if (h is not None and h.group(2) == "OK" and r is not None
                            and r.group(1) == "REPRODUZIDO") else "BLOQUEADO_COM_MOTIVO"
    return {"origem": origem, "sha256": sha, "selo": selo}


def autoteste():
    p, a = "a" * 64, "claude-arbitro2"
    assert medir(a, p, [])[0] is Grau.SEM_MEDICAO
    assert medir(a, p, [{"origem": a, "sha256": p, "selo": "VERIFICADO"}])[0] is Grau.AUTOMEDICAO
    assert medir(a, p, [{"origem": a, "sha256": p, "selo": "VERIFICADO"},
                        {"origem": a, "sha256": p, "selo": "VERIFICADO"}])[0] is Grau.AUTOMEDICAO
    assert medir(a, p, [{"origem": a, "sha256": p, "selo": "VERIFICADO"},
                        {"origem": "chatgpt-executor", "sha256": p, "selo": "VERIFICADO"}])[0] is Grau.INDEPENDENTE
    assert medir(a, p, [{"origem": "chatgpt-executor", "sha256": "b" * 64, "selo": "VERIFICADO"}])[0] is Grau.DIVERGENTE
    bloqueado = [{"origem": "chatgpt-executor", "sha256": p, "selo": "BLOQUEADO_COM_MOTIVO"}]
    assert medir(a, p, bloqueado)[0] is Grau.DIVERGENTE
    assert medir(a, p, [{"origem": "x", "sha256": p, "selo": "VERIFICADO"},
                        {"origem": "y", "sha256": "c" * 64, "selo": "VERIFICADO"}])[0] is Grau.DIVERGENTE
    assert medir("", p, [])[0] is Grau.INVALIDO
    assert medir(a, "A" * 64, [])[0] is Grau.INVALIDO
    assert medir(a, p, [{"origem": "", "sha256": p, "selo": "VERIFICADO"}])[0] is Grau.INVALIDO
    assert medir(a, p, "nao-lista")[0] is Grau.INVALIDO
    ok = "HASH tpl_coerencia_v1_4.py " + p + " OK\nRESULTADO: REPRODUZIDO\n"
    assert de_saida("x", ok) == {"origem": "x", "sha256": p, "selo": "VERIFICADO"}
    assert de_saida("x", ok.replace("REPRODUZIDO", "DIVERGENTE"))["selo"] == "BLOQUEADO_COM_MOTIVO"
    assert de_saida("x", "texto sem saida")["selo"] == "BLOQUEADO_COM_MOTIVO"
    try:
        bool(Grau.INDEPENDENTE)
    except TypeError:
        return 14
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
        print("  ", m["origem"], "|", m["selo"], "|", m["sha256"][:16])
    grau, motivo = medir("claude-arbitro2", pin, medicoes)
    print("GRAU DA MALHA:", grau.name, "|", motivo)
    return 0 if grau is Grau.INDEPENDENTE else 1


def main(argv):
    n = autoteste()
    print("AUTOTESTE:", n, "/ 14")
    if len(argv) >= 1 and argv[0] == "--extrato":
        return _extrato(argv[1:])
    if len(argv) < 1:
        raise SystemExit("TPL-MALHA FAIL-CLOSED: informe registro.json")
    try:
        with open(argv[0], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, UnicodeDecodeError, ValueError) as e:
        raise SystemExit("TPL-MALHA FAIL-CLOSED: registro ilegivel: " + type(e).__name__) from e
    if not isinstance(d, dict):
        raise SystemExit("TPL-MALHA FAIL-CLOSED: registro nao e objeto")
    grau, motivo = medir(d.get("autor"), d.get("pin"), d.get("medicoes"))
    print("ARTEFATO:", d.get("artefato"))
    print("GRAU:", grau.name, "|", motivo)
    if grau is not Grau.INDEPENDENTE:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
