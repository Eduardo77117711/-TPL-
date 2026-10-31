#!/usr/bin/env python3
"""tpl_arbitro_v3_3.py — régua do TPL, versão 3.3 (CANDIDATA, NÃO VERIFICADA).
v3.3 (31/10/2026, Claude, Árbitro 2): no Windows, o ambiente mínimo passa SYSTEMROOT. Sem ela o Python
     3.10 não inicia o processo filho ("failed to get random numbers"), provado nos runs 41185925741 e
     41186100858. Única mudança de comportamento sobre a v3.2, que continua selada.

v3.2 (30/10/2026, Claude, Árbitro 2): portabilidade Windows, sem alterar o v3 selado.
  Defeito medido: o filho grava CRLF no Windows; o corpo do veredito levava "\r\n",
  a leitura em modo texto o convertia em "\n" e o SELO deixava de conferir.
  Correção: forma canônica na captura. Só o par CRLF vira LF; um CR isolado é
  preservado (dois conteúdos diferentes nunca recebem o mesmo selo).
  O filho roda com -X utf8 (o -I ignora PYTHONUTF8; sem isso o Windows usa cp1252).
  Vereditos são lidos sem tradução de fim de linha: o selo confere os bytes reais.

AUTOR: Claude (Árbitro 2). Base: tpl_arbitro_v2.py (sha256 ae878798...9736),
régua oficial, que permanece intacta. A v3 só a substitui depois de verificada
por outro executor (regra 4).

Novidades da v3 (AUTOJULGAMENTO_TPL_20261028.txt):
  1) Falso positivo corrigido: os sinais de Google Doc (def init(self, if name
     == "main", from future import, métodos especiais sem sublinhado) são
     procurados só no código, fora de strings e comentários. A régua deixa de
     bloquear a si mesma e qualquer arquivo que apenas mencione esses padrões.
  2) Núcleo invariante: todo veredito grava o que não pode mudar com o
     observador (hash do arquivo, critério, código de saída, estado, motivos,
     resultado de cada teste, textos esperados) e o sha256 desse núcleo. O
     comando "comparar" diz se dois vereditos de executores diferentes
     CONVERGEM ou DIVERGEM, e em quê.
  3) Matriz opcional: "matriz" roda o mesmo arquivo em vários interpretadores
     (--python) e compara os núcleos. Não é obrigatória: custa N vezes o tempo.

Correções herdadas da v2 (revisão adversarial da Meta AI, ADENDO_4):
  a) Sublinhados perdidos: além dos 3 padrões fixos, detecta métodos especiais
     sem sublinhados (call, len, enter...) quando o arquivo não tem nenhum "__"
     — a assinatura de um Doc/Markdown que comeu todos os sublinhados.
  b) Caracteres invisíveis e homoglifos: NBSP, espaços de largura zero,
     espaços Unicode, controles bidirecionais (Trojan Source) e identificadores
     que misturam alfabetos. No código: bloqueio. Em strings/comentários: aviso
     (controles bidirecionais bloqueiam em qualquer lugar).
  c) Saída longa: a comparação sempre usa a saída completa; o veredito guarda
     início e fim (não só o início), o sha256 e o tamanho da saída completa, a
     posição de cada texto esperado, e grava a saída completa em arquivos ao lado.
  d) Dependências: antes de executar, verifica no mesmo interpretador e ambiente
     mínimo se cada import absoluto existe; ausente = NAO EXECUTADO com motivo.
     Imports dentro de try/except ImportError são opcionais (aviso).
  BOM e CRLF continuam apenas avisos.

Uso:
  python3 -I tpl_arbitro_v3.py arbitrar ARQUIVO.py --autor A --executor E \
      [--esperar-exit 0] [--esperar "texto"]... [--hash-informado SHA] \
      [--timeout 300] [--saida DIR] [--python INTERPRETADOR] -- [args]
  python3 -I tpl_arbitro_v3.py matriz ARQUIVO.py --autor A --executor E \
      --python P1 --python P2 [...mesmas opções...] -- [args]
  python3 -I tpl_arbitro_v3.py comparar VEREDITO_a.txt VEREDITO_b.txt
  python3 -I tpl_arbitro_v3.py conferir VEREDITO_x.txt
  python3 -I tpl_arbitro_v3.py autoteste

Limite: registra o autor e o executor declarados; não prova identidade.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import unicodedata
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERSAO = "3.3"
VERIFICADO = "VERIFICADO"
DIVERGENTE = "DIVERGENTE"
NAO_EXECUTADO = "NAO EXECUTADO"
MENCIONADO = "MENCIONADO"
ESTADOS = (VERIFICADO, DIVERGENTE, NAO_EXECUTADO, MENCIONADO)
LIMITE_SAIDA = 20000            # caracteres gravados no veredito por fluxo
PREFIXO_SELO = "SELO: sha256 do corpo (todas as linhas acima desta) = "

# --- (a) sublinhados perdidos ------------------------------------------------
SINAIS_DE_DOC = (
    (re.compile(r"^\s*from\s+future\s+import", re.M), "'from future import' (sublinhados de __future__ perdidos)"),
    (re.compile(r"\bdef\s+init\s*\(\s*self"), "'def init(self' (sublinhados de __init__ perdidos)"),
    (re.compile(r"\bif\s+name\s*==\s*['\"]main['\"]"), "'if name == \"main\"' (sublinhados de __name__/__main__ perdidos)"),
)
METODOS_ESPECIAIS = frozenset("""
    init new del repr str bytes format hash bool call len iter next reversed
    contains getitem setitem delitem missing enter exit aenter aexit await
    aiter anext getattr getattribute setattr delattr dir get set delete
    set_name init_subclass class_getitem eq ne lt le gt ge add sub mul
    matmul truediv floordiv mod divmod pow lshift rshift and or xor neg pos
    abs invert index int float complex round trunc floor ceil post_init
""".split())
RE_DEF_METODO = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]+)\s*\(\s*(self|cls)\b", re.M)

# --- (b) caracteres invisíveis ------------------------------------------------
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}
INVISIVEIS = {0x00A0, 0x00AD, 0x180E, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x202F,
              0x205F, 0x3000, *range(0x2000, 0x200B)}


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def agora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mesmo_agente(a: str, b: str) -> bool:
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    return norm(a) == norm(b)


def so_codigo(texto: str) -> str:
    """(v3) Cópia do texto com strings e comentários trocados por espaços.

    Mantém as quebras de linha, para que âncoras de linha (^) e números de linha
    continuem valendo. Se o texto não tokenizar, devolve o texto original
    (conservador: o compile() vai recusar o arquivo de qualquer forma).
    """
    faixas = _faixas_texto_livre(texto)
    if faixas is None:
        return texto
    chars = list(texto)
    for a, b in faixas:
        for i in range(a, b):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def sinais_de_sublinhado(texto: str) -> list[str]:
    """(a) Bloqueios por sublinhados perdidos — procurados só no código (v3)."""
    codigo = so_codigo(texto)
    achados = [f"sinal de Google Doc: {d}" for p, d in SINAIS_DE_DOC if p.search(codigo)]
    if "__" not in texto:
        nomes = sorted({m.group(1) for m in RE_DEF_METODO.finditer(codigo)
                        if m.group(1) in METODOS_ESPECIAIS and m.group(1) != "init"})
        if nomes:
            achados.append("sinal de Google Doc: métodos especiais sem sublinhados "
                           f"({', '.join(nomes)}) num arquivo sem nenhum '__'")
    return achados


def _faixas_texto_livre(texto: str) -> list[tuple[int, int]] | None:
    """Faixas [início, fim) de strings e comentários; None se não tokenizar."""
    inicio_linha = [0]
    for linha in texto.split("\n"):          # v3: mesma divisão de linhas do tokenize
        inicio_linha.append(inicio_linha[-1] + len(linha) + 1)
    tipos = {tokenize.STRING, tokenize.COMMENT}
    for nome in ("FSTRING_MIDDLE", "TSTRING_MIDDLE"):
        if hasattr(tokenize, nome):
            tipos.add(getattr(tokenize, nome))
    faixas: list[tuple[int, int]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
            if tok.type in tipos:
                (l1, c1), (l2, c2) = tok.start, tok.end
                faixas.append((inicio_linha[l1 - 1] + c1, inicio_linha[l2 - 1] + c2))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    return faixas


def _escrita(ch: str) -> str:
    try:
        return unicodedata.name(ch).split(" ")[0]
    except ValueError:
        return "?"


def sinais_invisiveis(texto: str) -> tuple[list[str], list[str]]:
    """(b) Retorna (bloqueios, avisos) por caracteres invisíveis e homoglifos."""
    bloqueios: list[str] = []
    avisos: list[str] = []
    faixas = _faixas_texto_livre(texto)
    dentro = lambda i: faixas is not None and any(a <= i < b for a, b in faixas)
    for i, ch in enumerate(texto):
        cp = ord(ch)
        if cp not in BIDI and cp not in INVISIVEIS:
            continue
        linha = texto.count("\n", 0, i) + 1
        desc = f"U+{cp:04X} ({unicodedata.name(ch, 'sem nome')}) na linha {linha}"
        if cp in BIDI:
            bloqueios.append(f"controle bidirecional {desc} (Trojan Source)")
        elif dentro(i):
            avisos.append(f"caractere invisível em string/comentário: {desc}")
        else:
            bloqueios.append(f"caractere invisível no código: {desc}")
    if faixas is not None:
        try:
            for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
                if tok.type != tokenize.NAME or tok.string.isascii():
                    continue
                escritas = {_escrita(c) for c in tok.string if c.isalpha()}
                if len(escritas) > 1:
                    bloqueios.append(f"identificador mistura alfabetos {sorted(escritas)}: "
                                     f"{tok.string!r} na linha {tok.start[0]} (possível homoglifo)")
                elif escritas and escritas != {"LATIN"}:
                    avisos.append(f"identificador em alfabeto {sorted(escritas)[0]}: "
                                  f"{tok.string!r} na linha {tok.start[0]}")
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
    return bloqueios, avisos


def inspecionar_formato(dados: bytes) -> tuple[list[str], list[str]]:
    """Retorna (bloqueios, avisos) sobre o formato do arquivo."""
    bloqueios: list[str] = []
    avisos: list[str] = []
    if dados.startswith(b"\xef\xbb\xbf"):
        avisos.append("arquivo começa com BOM UTF-8 (típico de exportação de Doc)")
    if b"\r\n" in dados:
        avisos.append("quebras de linha CRLF (típico de exportação de Doc)")
    try:
        texto = dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ["arquivo não é UTF-8 válido"], avisos
    bloqueios += sinais_de_sublinhado(texto)
    b_inv, a_inv = sinais_invisiveis(texto)
    bloqueios += b_inv
    avisos += a_inv
    linhas = texto.splitlines()
    if linhas and len(linhas) < 5 and max(len(l) for l in linhas) > 2000:
        bloqueios.append("código em poucas linhas muito longas (linhas juntadas)")
    try:
        compile(texto, "<entrada>", "exec")
    except SyntaxError as exc:
        bloqueios.append(f"sintaxe inválida: {exc.msg} (linha {exc.lineno})")
    return bloqueios, avisos


# --- (d) dependências ----------------------------------------------------------
def _protege_import(tratador: ast.ExceptHandler) -> bool:
    t = tratador.type
    if t is None:
        return True
    nomes = [t] if not isinstance(t, ast.Tuple) else list(t.elts)
    return any(isinstance(n, ast.Name) and n.id in ("ImportError", "ModuleNotFoundError", "Exception",
                                                    "BaseException") for n in nomes)


def coletar_imports(texto: str) -> tuple[list[str], list[str], list[str]]:
    """Retorna (obrigatórios, opcionais, avisos) — módulos de topo com import absoluto."""
    arvore = ast.parse(texto)
    obrig: set[str] = set()
    opc: set[str] = set()
    avisos: list[str] = []

    def visitar(no: ast.AST, protegido: bool) -> None:
        if isinstance(no, ast.Try):
            prot_corpo = protegido or any(_protege_import(h) for h in no.handlers)
            for filho in no.body:
                visitar(filho, prot_corpo)
            for filho in no.handlers + no.orelse + no.finalbody:
                visitar(filho, protegido)
            return
        if isinstance(no, ast.Import):
            for a in no.names:
                (opc if protegido else obrig).add(a.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            if no.module != "__future__":
                (opc if protegido else obrig).add(no.module.split(".")[0])
        elif isinstance(no, ast.Call):
            f = no.func
            nome = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if nome in ("__import__", "import_module"):
                avisos.append(f"import dinâmico na linha {no.lineno} não verificado antes da execução")
        for filho in ast.iter_child_nodes(no):
            visitar(filho, protegido)

    visitar(arvore, False)
    return sorted(obrig), sorted(opc - obrig), avisos


def ambiente_minimo(diretorio: str, nome_os: str | None = None, ambiente: dict | None = None) -> dict:
    nome_os = nome_os or os.name
    ambiente = os.environ if ambiente is None else ambiente
    env = {"PATH": ambiente.get("PATH", os.defpath) if nome_os == "nt" else "/usr/bin:/bin",
           "HOME": diretorio, "TMPDIR": diretorio, "TEMP": diretorio, "TMP": diretorio}
    if nome_os == "nt" and ambiente.get("SYSTEMROOT"):
        env["SYSTEMROOT"] = ambiente["SYSTEMROOT"]   # v3.3: Python < 3.11 no Windows não inicia sem ela
    return env


def modulos_ausentes(modulos: list[str], py: str | None = None) -> list[str]:
    """Consulta o mesmo interpretador, isolado e em ambiente mínimo, sem importar nada."""
    if not modulos:
        return []
    codigo = ("import importlib.util, json, sys\n"
              "m = json.loads(sys.argv[1])\n"
              "print(json.dumps([x for x in m if importlib.util.find_spec(x) is None]))\n")
    with tempfile.TemporaryDirectory(prefix="tpl_dep_") as tmp:
        proc = subprocess.run([py or sys.executable, "-I", "-X", "utf8", "-c", codigo, json.dumps(modulos)],
                              cwd=tmp, env=ambiente_minimo(tmp), capture_output=True, timeout=60)
    if proc.returncode != 0:
        return [f"(verificação falhou: {proc.stderr.decode('utf-8', 'replace').strip()[-200:]})"]
    return json.loads(proc.stdout.decode("utf-8"))


def canonico(texto: str) -> str:
    """Forma canônica de uma saída capturada: só o par CRLF vira LF."""
    return texto.replace("\r\n", "\n")


def ler_veredito(caminho: Path) -> str:
    """Lê exatamente os bytes gravados, sem traduzir fim de linha."""
    return caminho.read_bytes().decode("utf-8")


@dataclass
class Execucao:
    comando: list
    codigo_saida: int | None
    stdout: str
    stderr: str
    timeout: bool = False


def executar(arquivo: Path, argumentos: list[str], timeout: int, py: str | None = None) -> Execucao:
    with tempfile.TemporaryDirectory(prefix="tpl_") as tmp:
        alvo = Path(tmp) / arquivo.name
        shutil.copyfile(arquivo, alvo)
        comando = [py or sys.executable, "-I", "-X", "utf8", alvo.name, *argumentos]
        try:
            proc = subprocess.run(comando, cwd=tmp, env=ambiente_minimo(tmp),
                                  capture_output=True, timeout=timeout)
            return Execucao(comando, proc.returncode,
                            canonico(proc.stdout.decode("utf-8", "replace")),
                            canonico(proc.stderr.decode("utf-8", "replace")))
        except subprocess.TimeoutExpired as exc:
            return Execucao(comando, None,
                            canonico((exc.stdout or b"").decode("utf-8", "replace")),
                            canonico((exc.stderr or b"").decode("utf-8", "replace")), timeout=True)


def versoes_ambiente(py: str | None = None) -> str:
    codigo = ("import sys\nprint('Python', sys.version.split()[0])\n"
              "for m in ('numpy','scipy'):\n"
              "    try:\n        mod=__import__(m); print(m, mod.__version__)\n"
              "    except Exception: print(m, 'ausente')\n")
    with tempfile.TemporaryDirectory(prefix="tpl_v_") as tmp:
        proc = subprocess.run([py or sys.executable, "-I", "-X", "utf8", "-c", codigo], cwd=tmp,
                              env=ambiente_minimo(tmp), capture_output=True, timeout=60)
    return canonico(proc.stdout.decode("utf-8", "replace")).strip()


@dataclass
class Decisao:
    estado: str
    motivos: list = field(default_factory=list)
    nota: str = ""
    evidencias: list = field(default_factory=list)


def localizar(texto: str, execucao: Execucao) -> str:
    for nome, fluxo in (("stdout", execucao.stdout), ("stderr", execucao.stderr)):
        pos = fluxo.find(texto)
        if pos >= 0:
            return f"{texto!r} encontrado em {nome}, caractere {pos} de {len(fluxo)}"
    return f"{texto!r} AUSENTE em stdout e stderr"


def decidir(bloqueios: list[str], execucao: Execucao | None, autor: str, executor: str,
            esperar_exit: int | None, esperar: list[str],
            hash_arquivo: str, hash_informado: str | None) -> Decisao:
    if hash_informado and hash_informado.lower() != hash_arquivo:
        return Decisao(DIVERGENTE, [f"hash informado {hash_informado} difere do hash dos bytes {hash_arquivo}"])
    if bloqueios:
        return Decisao(NAO_EXECUTADO, list(bloqueios))
    if execucao is None:
        return Decisao(NAO_EXECUTADO, ["execução não realizada"])
    if esperar_exit is None and not esperar:
        return Decisao(MENCIONADO, ["sem critério COMO_CONFERIR (--esperar-exit/--esperar)"])
    falhas: list[str] = []
    if execucao.timeout:
        falhas.append("tempo limite excedido")
    elif esperar_exit is not None and execucao.codigo_saida != esperar_exit:
        falhas.append(f"código de saída {execucao.codigo_saida}, esperado {esperar_exit}")
    evidencias = [localizar(t, execucao) for t in esperar]   # (c) sempre na saída completa
    for texto in esperar:
        if texto not in execucao.stdout and texto not in execucao.stderr:
            falhas.append(f"texto esperado ausente: {texto!r}")
    resultado = "bateu com o critério" if not falhas else "não bateu com o critério"
    if mesmo_agente(autor, executor):
        return Decisao(NAO_EXECUTADO,
                       [f"executor ({executor}) é o próprio autor; regra 4 impede VERIFICADO"],
                       nota=f"relato do autor: execução {resultado}" + (f" ({'; '.join(falhas)})" if falhas else ""),
                       evidencias=evidencias)
    if falhas:
        return Decisao(DIVERGENTE, falhas, evidencias=evidencias)
    return Decisao(VERIFICADO, ["executor independente; saída bateu com o critério"], evidencias=evidencias)


def resumir_fluxo(texto: str) -> str:
    """(c) Até LIMITE_SAIDA caracteres: metade do início e metade do fim."""
    if len(texto) <= LIMITE_SAIDA:
        return texto
    metade = LIMITE_SAIDA // 2
    return (texto[:metade] + f"\n[... {len(texto) - LIMITE_SAIDA} caracteres do meio omitidos;"
            " saída completa no arquivo SAIDA indicado ...]\n" + texto[-metade:])


def montar_corpo(nome_arquivo: str, hash_arquivo: str, tamanho: int, autor: str, executor: str,
                 hash_informado: str | None, avisos: list[str], versoes: str, deps: str,
                 execucao: Execucao | None, esperar_exit: int | None, esperar: list[str],
                 decisao: Decisao, arquivos_saida: dict, nucleo: dict | None = None) -> str:
    l: list[str] = []
    l.append(f"VEREDITO_{nome_arquivo}.txt")
    l.append(f"Gerado por tpl_arbitro_v3.py versão {VERSAO}")
    l.append(f"DATA_UTC: {agora_utc()}")
    l.append(f"AUTOR: {autor}")
    l.append(f"EXECUTOR: {executor} (declarado; a ferramenta não prova identidade)")
    l.append("")
    l.append(f"ARQUIVO: {nome_arquivo} ({tamanho} bytes)")
    l.append(f"SHA256: {hash_arquivo}")
    l.append(f"HASH_INFORMADO: {hash_informado or 'não informado'}"
             + ("" if not hash_informado else (" -> IGUAL" if hash_informado.lower() == hash_arquivo else " -> DIFERENTE")))
    for aviso in avisos:
        l.append(f"AVISO: {aviso}")
    l.append("")
    l.append("AMBIENTE:")
    l.append(versoes or "(não obtido)")
    l.append(f"DEPENDENCIAS: {deps}")
    l.append("")
    l.append("COMO_CONFERIR:")
    l.append(f"  código de saída esperado: {esperar_exit if esperar_exit is not None else 'não definido'}")
    for texto in esperar:
        l.append(f"  texto esperado: {texto}")
    l.append("")
    if execucao is not None:
        l.append("COMANDO (em diretório novo e vazio, ambiente mínimo):")
        l.append("  " + " ".join(execucao.comando))
        l.append(f"CODIGO_DE_SAIDA: {'TIMEOUT' if execucao.timeout else execucao.codigo_saida}")
        for nome, fluxo in (("STDOUT", execucao.stdout), ("STDERR", execucao.stderr)):
            completo = fluxo.encode("utf-8")
            l.append(f"{nome}_COMPLETO: {len(fluxo)} caracteres, sha256 {sha256_bytes(completo)}"
                     + (f", arquivo {arquivos_saida[nome]}" if nome in arquivos_saida else ""))
            l.append(f"{nome} ({'integral' if len(fluxo) <= LIMITE_SAIDA else 'início e fim'}):")
            l.append(resumir_fluxo(fluxo).rstrip("\n"))
        if decisao.evidencias:
            l.append("EVIDENCIAS (procuradas na saída completa):")
            for e in decisao.evidencias:
                l.append(f"  {e}")
    else:
        l.append("COMANDO: nenhum (não executado)")
    l.append("")
    if nucleo is not None:
        l.append("NUCLEO_INVARIANTE: " + json.dumps(nucleo, sort_keys=True, ensure_ascii=False))
        l.append(f"NUCLEO_INVARIANTE_SHA256: {hash_nucleo(nucleo)}")
    l.append(f"ESTADO: {decisao.estado}")
    for motivo in decisao.motivos:
        l.append(f"MOTIVO: {motivo}")
    if decisao.nota:
        l.append(f"NOTA: {decisao.nota}")
    return "\n".join(l) + "\n"


# --- (v3) núcleo invariante -----------------------------------------------------
RE_LINHA_TESTE = re.compile(
    r"^(test\w*) \(.*?\) \.\.\. (ok|FAIL|ERROR|skipped|expected failure|unexpected success)",
    re.M)


def montar_nucleo(hash_arquivo: str, esperar_exit: int | None, esperar: list[str],
                  execucao: Execucao | None, decisao: Decisao, executor: str) -> dict:
    """O que não pode mudar quando muda o observador (executor, versão, hora, tempo).

    Fica de fora: data, nome do executor, versões, tempos, formato com que cada
    versão do unittest imprime a classe, posição dos textos na saída e avisos.
    """
    saida = "" if execucao is None else execucao.stdout + "\n" + execucao.stderr
    codigo = None
    if execucao is not None:
        codigo = "TIMEOUT" if execucao.timeout else execucao.codigo_saida
    return {
        "sha256_arquivo": hash_arquivo,
        "criterio_exit": esperar_exit,
        "criterio_textos": list(esperar),
        "executado": execucao is not None,
        "codigo_saida": codigo,
        "estado": decisao.estado,
        "motivos": [m.replace(f"({executor})", "(<executor>)") for m in decisao.motivos],
        "testes": sorted(f"{n} {r}" for n, r in RE_LINHA_TESTE.findall(saida)),
        "textos": {t: (t in saida) for t in esperar},
    }


def hash_nucleo(nucleo: dict) -> str:
    return sha256_bytes(json.dumps(nucleo, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def ler_nucleo(texto_veredito: str) -> dict | None:
    for linha in texto_veredito.splitlines():
        if linha.startswith("NUCLEO_INVARIANTE: "):
            return json.loads(linha[len("NUCLEO_INVARIANTE: "):])
    return None


def comparar_vereditos(texto_a: str, texto_b: str) -> tuple[bool, list[str]]:
    """CONVERGENTE se os dois selos conferem e os núcleos são idênticos."""
    linhas: list[str] = []
    for rot, t in (("A", texto_a), ("B", texto_b)):
        ok, msg = conferir_selo(t)
        linhas.append(f"{rot}: {msg}")
        if not ok:
            return False, linhas + [f"{rot}: selo inválido; comparação recusada"]
    na, nb = ler_nucleo(texto_a), ler_nucleo(texto_b)
    if na is None or nb is None:
        return False, linhas + ["veredito sem NUCLEO_INVARIANTE (gerado por versão anterior da régua?)"]
    linhas.append(f"A núcleo: {hash_nucleo(na)}")
    linhas.append(f"B núcleo: {hash_nucleo(nb)}")
    difs = [k for k in sorted(set(na) | set(nb)) if na.get(k) != nb.get(k)]
    for k in difs:
        linhas.append(f"DIFERE em {k}: A={na.get(k)!r} | B={nb.get(k)!r}")
    return not difs, linhas


def selar(corpo: str) -> str:
    return corpo + PREFIXO_SELO + sha256_bytes(corpo.encode("utf-8")) + "\n"


def conferir_selo(texto: str) -> tuple[bool, str]:
    if not texto.endswith("\n"):
        return False, "arquivo não termina em quebra de linha"
    linhas = texto[:-1].split("\n")
    ultima = linhas[-1]
    if not ultima.startswith(PREFIXO_SELO):
        return False, "última linha não é um SELO"
    informado = ultima[len(PREFIXO_SELO):].strip()
    corpo = "\n".join(linhas[:-1]) + "\n"
    calculado = sha256_bytes(corpo.encode("utf-8"))
    if informado == calculado:
        return True, f"SELO confere ({calculado})"
    return False, f"SELO NAO confere: informado {informado}, calculado {calculado}"


def arbitrar(arquivo: Path, autor: str, executor: str, argumentos: list[str],
             esperar_exit: int | None, esperar: list[str], hash_informado: str | None,
             timeout: int, saida: Path, py: str | None = None) -> tuple[Path, Decisao]:
    dados = arquivo.read_bytes()
    hash_arquivo = sha256_bytes(dados)
    destino = saida / f"VEREDITO_{arquivo.name}.txt"
    destinos_saida = {"STDOUT": saida / f"SAIDA_{arquivo.name}.stdout.txt",
                      "STDERR": saida / f"SAIDA_{arquivo.name}.stderr.txt"}
    for d in (destino, *destinos_saida.values()):
        if d.exists():
            raise FileExistsError(f"{d} já existe; o TPL não sobrescreve vereditos (use um ADENDO)")
    bloqueios, avisos = inspecionar_formato(dados)
    deps = "não verificadas (formato bloqueado)"
    if not bloqueios:
        obrig, opc, avisos_imp = coletar_imports(dados.decode("utf-8-sig"))
        avisos += avisos_imp
        faltando = modulos_ausentes(obrig, py)
        faltando_opc = modulos_ausentes(opc, py)
        for m in faltando:
            bloqueios.append(f"dependência ausente no ambiente do executor: {m} (verificado antes da execução)")
        for m in faltando_opc:
            avisos.append(f"dependência opcional ausente (import protegido por try/except): {m}")
        deps = (f"obrigatórias {obrig or '[]'}; opcionais {opc or '[]'}; "
                f"ausentes {faltando + faltando_opc or '[]'}")
    hash_ok = not hash_informado or hash_informado.lower() == hash_arquivo
    execucao = executar(arquivo, argumentos, timeout, py) if (not bloqueios and hash_ok) else None
    versoes = versoes_ambiente(py)
    decisao = decidir(bloqueios, execucao, autor, executor, esperar_exit, esperar,
                      hash_arquivo, hash_informado)
    saida.mkdir(parents=True, exist_ok=True)
    gravados: dict = {}
    if execucao is not None:
        for nome, fluxo in (("STDOUT", execucao.stdout), ("STDERR", execucao.stderr)):
            if len(fluxo) > LIMITE_SAIDA:
                with destinos_saida[nome].open("x", encoding="utf-8", newline="") as f:
                    f.write(fluxo)
                gravados[nome] = destinos_saida[nome].name
    nucleo = montar_nucleo(hash_arquivo, esperar_exit, esperar, execucao, decisao, executor)
    corpo = montar_corpo(arquivo.name, hash_arquivo, len(dados), autor, executor, hash_informado,
                         avisos, versoes, deps, execucao, esperar_exit, esperar, decisao, gravados,
                         nucleo)
    with destino.open("x", encoding="utf-8", newline="\n") as f:
        f.write(selar(corpo))
    return destino, decisao


def matriz(arquivo: Path, autor: str, executor: str, argumentos: list[str],
           esperar_exit: int | None, esperar: list[str], hash_informado: str | None,
           timeout: int, saida: Path, interpretadores: list[str]) -> tuple[Path, bool]:
    """(v3) Mesmo arquivo, vários interpretadores; compara os núcleos invariantes."""
    if len(interpretadores) < 2:
        raise ValueError("a matriz precisa de pelo menos 2 interpretadores (--python)")
    destino = saida / f"MATRIZ_{arquivo.name}.txt"
    if destino.exists():
        raise FileExistsError(f"{destino} já existe; o TPL não sobrescreve registros")
    linhas = [f"MATRIZ_{arquivo.name}.txt", f"Gerado por tpl_arbitro_v3.py versão {VERSAO}",
              f"DATA_UTC: {agora_utc()}", f"AUTOR: {autor}", f"EXECUTOR: {executor}",
              f"ARQUIVO: {arquivo.name}", f"SHA256: {sha256_bytes(arquivo.read_bytes())}", ""]
    hashes = []
    for i, py in enumerate(interpretadores, start=1):
        sub_saida = saida / f"matriz_{i}"
        v, d = arbitrar(arquivo, autor, executor, argumentos, esperar_exit, esperar,
                        hash_informado, timeout, sub_saida, py)
        texto = ler_veredito(v)
        n = ler_nucleo(texto)
        h = hash_nucleo(n) if n is not None else "sem-nucleo"
        hashes.append(h)
        versao = next((l for l in texto.splitlines() if l.startswith("Python ")), "Python ?")
        linhas.append(f"[{i}] {versao} | interpretador {py} | estado {d.estado} | "
                      f"núcleo {h} | veredito {sub_saida.name}/{v.name}")
    convergente = len(set(hashes)) == 1
    linhas.append("")
    linhas.append("RESULTADO_MATRIZ: " + ("CONVERGENTE (núcleo idêntico em todos os interpretadores)"
                                          if convergente else "DIVERGENTE (ver vereditos individuais e comparar)"))
    saida.mkdir(parents=True, exist_ok=True)
    with destino.open("x", encoding="utf-8", newline="\n") as f:
        f.write(selar("\n".join(linhas) + "\n"))
    return destino, convergente


# ----------------------------------------------------------------- autotestes
class TplArbitroTests(unittest.TestCase):
    """Os 12 testes da v1, inalterados no comportamento."""

    def _arbitrar(self, codigo: str, autor="ChatGPT", executor="Claude", args=(),
                  esperar_exit=0, esperar=("OK-FIM",), hash_informado=None, timeout=60):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_bytes(codigo.encode("utf-8"))
            destino, decisao = arbitrar(alvo, autor, executor, list(args), esperar_exit,
                                        list(esperar), hash_informado, timeout, Path(tmp) / "out")
            texto = ler_veredito(destino)
            extras = {p.name: p.read_text(encoding="utf-8") for p in (Path(tmp) / "out").glob("SAIDA_*")}
            self._extras = extras
            return decisao, texto

    def test_verificado_com_executor_independente(self):
        d, t = self._arbitrar("print('OK-FIM')\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertTrue(conferir_selo(t)[0])
        self.assertIn("CODIGO_DE_SAIDA: 0", t)

    def test_autor_igual_executor_nunca_verifica(self):
        d, _ = self._arbitrar("print('OK-FIM')\n", autor="Claude", executor="claude ")
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertIn("regra 4", d.motivos[0])

    def test_codigo_de_saida_diferente_diverge(self):
        d, _ = self._arbitrar("import sys\nprint('OK-FIM')\nsys.exit(3)\n")
        self.assertEqual(d.estado, DIVERGENTE)
        self.assertIn("código de saída 3", d.motivos[0])

    def test_texto_ausente_diverge(self):
        d, _ = self._arbitrar("print('outra coisa')\n")
        self.assertEqual(d.estado, DIVERGENTE)

    def test_sem_criterio_e_mencionado(self):
        d, _ = self._arbitrar("print('x')\n", esperar_exit=None, esperar=())
        self.assertEqual(d.estado, MENCIONADO)

    def test_formato_de_doc_bloqueia(self):
        quebrado = 'from future import annotations\nclass A:\n    def init(self): pass\nif name == "main": pass\n'
        d, t = self._arbitrar(quebrado)
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertIn("COMANDO: nenhum", t)
        self.assertTrue(any("__init__" in m for m in d.motivos))

    def test_sintaxe_quebrada_bloqueia(self):
        d, _ = self._arbitrar("def f(:\n")
        self.assertEqual(d.estado, NAO_EXECUTADO)

    def test_hash_informado_diferente_diverge_sem_executar(self):
        d, t = self._arbitrar("print('OK-FIM')\n", hash_informado="0" * 64)
        self.assertEqual(d.estado, DIVERGENTE)
        self.assertIn("COMANDO: nenhum", t)

    def test_timeout_diverge(self):
        d, t = self._arbitrar("import time\ntime.sleep(10)\n", timeout=1)
        self.assertEqual(d.estado, DIVERGENTE)
        self.assertIn("CODIGO_DE_SAIDA: TIMEOUT", t)

    def test_ambiente_minimo_sem_variaveis_herdadas(self):
        os.environ["TPL_SEGREDO_TESTE"] = "vazou"
        try:
            d, t = self._arbitrar("import os\nprint('OK-FIM', os.environ.get('TPL_SEGREDO_TESTE'))\n",
                                  esperar=("OK-FIM None",))
        finally:
            del os.environ["TPL_SEGREDO_TESTE"]
        self.assertEqual(d.estado, VERIFICADO)

    def test_selo_detecta_alteracao(self):
        texto = selar("linha 1\nESTADO: DIVERGENTE\n")
        self.assertTrue(conferir_selo(texto)[0])
        self.assertFalse(conferir_selo(texto.replace("DIVERGENTE", "VERIFICADO"))[0])

    def test_nao_sobrescreve_veredito(self):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_text("print('OK-FIM')\n", encoding="utf-8")
            arbitrar(alvo, "A", "B", [], 0, ["OK-FIM"], None, 60, Path(tmp))
            with self.assertRaises(FileExistsError):
                arbitrar(alvo, "A", "B", [], 0, ["OK-FIM"], None, 60, Path(tmp))


class TplArbitroV2Tests(TplArbitroTests):
    """Testes adversariais da v2 (pontos a, b, c, d do ADENDO_4)."""

    # (a) sublinhados ---------------------------------------------------------
    def test_a_metodos_especiais_sem_sublinhado_bloqueiam(self):
        codigo = ("class Pilha:\n    def len(self):\n        return 0\n"
                  "    def call(self, x):\n        return x\n    def enter(self):\n        return self\n"
                  "print('OK-FIM')\n")
        d, t = self._arbitrar(codigo)
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("call, enter, len" in m for m in d.motivos))
        self.assertIn("COMANDO: nenhum", t)

    def test_a_metodo_legitimo_com_nome_comum_nao_bloqueia(self):
        # Há "__" no arquivo: um Doc que come sublinhados não deixaria nenhum.
        codigo = ("class Cliente:\n    def __init__(self):\n        self.n = 0\n"
                  "    def call(self, numero):\n        return numero\n"
                  "    def len(self):\n        return 1\nprint('OK-FIM')\n")
        d, _ = self._arbitrar(codigo)
        self.assertEqual(d.estado, VERIFICADO)

    def test_a_arquivo_sem_classes_nem_sublinhados_nao_bloqueia(self):
        d, _ = self._arbitrar("def soma(a, b):\n    return a + b\nprint('OK-FIM', soma(1, 2))\n")
        self.assertEqual(d.estado, VERIFICADO)

    # (b) invisíveis ------------------------------------------------------------
    def test_b_nbsp_no_codigo_bloqueia(self):
        d, t = self._arbitrar("x\u00a0= 1\nprint('OK-FIM')\n")
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("U+00A0" in m and "no código" in m for m in d.motivos))
        self.assertIn("COMANDO: nenhum", t)

    def test_b_espaco_largura_zero_em_identificador_bloqueia(self):
        d, _ = self._arbitrar("valor\u200b = 1\nprint('OK-FIM')\n")
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("U+200B" in m for m in d.motivos))

    def test_b_invisivel_em_string_e_comentario_so_avisa(self):
        codigo = "# nota\u00a0com NBSP\nprint('OK-FIM', 'a\u200bb')\n"
        d, t = self._arbitrar(codigo)
        self.assertEqual(d.estado, VERIFICADO)
        self.assertEqual(t.count("AVISO: caractere invisível em string/comentário"), 2)

    def test_b_controle_bidirecional_bloqueia_mesmo_em_string(self):
        d, _ = self._arbitrar("s = 'abc\u202edef'\nprint('OK-FIM')\n")
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("Trojan Source" in m for m in d.motivos))

    def test_b_homoglifo_cirilico_misturado_bloqueia(self):
        d, _ = self._arbitrar("v\u0430lor = 1\nprint('OK-FIM', v\u0430lor)\n")  # 'а' cirílico
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("mistura alfabetos" in m for m in d.motivos))

    def test_b_acentos_portugueses_nao_bloqueiam(self):
        d, t = self._arbitrar("função = 'ação'\nprint('OK-FIM', função)\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertNotIn("AVISO: identificador", t)

    def test_b_f_string_com_invisivel_so_avisa(self):
        d, _ = self._arbitrar("n = 1\nprint(f'OK-FIM {n}\u200b')\n")
        self.assertEqual(d.estado, VERIFICADO)

    # (c) saída longa -------------------------------------------------------------
    def test_c_texto_esperado_apos_o_corte_e_encontrado(self):
        codigo = "print('x' * 30000)\nprint('MARCA-FINAL')\n"
        d, t = self._arbitrar(codigo, esperar=("MARCA-FINAL",))
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("MARCA-FINAL", t)                       # o fim aparece no veredito
        self.assertIn("caracteres do meio omitidos", t)
        self.assertIn("'MARCA-FINAL' encontrado em stdout, caractere 30001", t)
        arquivo = self._extras["SAIDA_alvo.py.stdout.txt"]
        self.assertEqual(len(arquivo), 30000 + 1 + len("MARCA-FINAL") + 1)
        self.assertIn(f"sha256 {sha256_bytes(arquivo.encode('utf-8'))}", t)

    def test_c_erro_no_fim_de_saida_longa_aparece_no_veredito(self):
        codigo = "import sys\nprint('y' * 25000)\nprint('OK-FIM')\nsys.exit('ERRO-NO-FIM')\n"
        d, t = self._arbitrar(codigo)
        self.assertEqual(d.estado, DIVERGENTE)
        self.assertIn("ERRO-NO-FIM", t)

    def test_c_texto_ausente_em_saida_longa_diverge(self):
        d, _ = self._arbitrar("print('z' * 30000)\n", esperar=("NAO-EXISTE",))
        self.assertEqual(d.estado, DIVERGENTE)

    # (d) dependências -------------------------------------------------------------
    def test_d_dependencia_ausente_bloqueia_antes_de_executar(self):
        with tempfile.TemporaryDirectory() as marca_dir:
            marca = Path(marca_dir) / "executou.txt"
            codigo = (f"open({str(marca)!r}, 'w').write('sim')\n"
                      "import modulo_inexistente_tpl_xyz\nprint('OK-FIM')\n")
            d, t = self._arbitrar(codigo)
            self.assertEqual(d.estado, NAO_EXECUTADO)
            self.assertTrue(any("modulo_inexistente_tpl_xyz" in m and "antes da execução" in m
                                for m in d.motivos))
            self.assertIn("COMANDO: nenhum", t)
            self.assertFalse(marca.exists())

    def test_d_import_opcional_protegido_nao_bloqueia(self):
        codigo = ("try:\n    import modulo_inexistente_tpl_xyz\nexcept ImportError:\n"
                  "    modulo_inexistente_tpl_xyz = None\nprint('OK-FIM')\n")
        d, t = self._arbitrar(codigo)
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("dependência opcional ausente", t)

    def test_d_biblioteca_padrao_nao_bloqueia(self):
        d, t = self._arbitrar("import json, os.path\nfrom collections import OrderedDict\nprint('OK-FIM')\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("ausentes []", t)

    def test_d_import_dinamico_gera_aviso(self):
        d, t = self._arbitrar("import importlib\nm = importlib.import_module('json')\nprint('OK-FIM')\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("import dinâmico", t)

    # BOM e CRLF continuam avisos ----------------------------------------------------
    def test_bom_e_crlf_sao_avisos_nao_bloqueios(self):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_bytes(b"\xef\xbb\xbfprint('OK-FIM')\r\n")
            destino, d = arbitrar(alvo, "A", "B", [], 0, ["OK-FIM"], None, 60, Path(tmp) / "out")
            t = ler_veredito(destino)
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("AVISO: arquivo começa com BOM", t)
        self.assertIn("AVISO: quebras de linha CRLF", t)


class TplArbitroV3Tests(TplArbitroV2Tests):
    """Testes da v3: falso positivo do autojulgamento, núcleo invariante, matriz."""

    # 1) falso positivo -------------------------------------------------------------
    def test_v3_padroes_de_doc_em_string_e_comentario_nao_bloqueiam(self):
        codigo = ("EXEMPLO = 'def init(self): pass'\n"
                  "DOC = \"\"\"\nfrom future import annotations\nif name == 'main': pass\n\"\"\"\n"
                  "# comentário: def init(self) e if name == \"main\"\n"
                  "print('OK-FIM')\n")
        d, _ = self._arbitrar(codigo)
        self.assertEqual(d.estado, VERIFICADO)

    def test_v3_padrao_de_doc_no_codigo_continua_bloqueando(self):
        codigo = ("NOTA = 'texto qualquer'\nclass A:\n    def init(self):\n        pass\n"
                  "print('OK-FIM')\n")
        d, _ = self._arbitrar(codigo)
        self.assertEqual(d.estado, NAO_EXECUTADO)
        self.assertTrue(any("__init__" in m for m in d.motivos))

    def test_v3_regua_nao_bloqueia_a_si_mesma(self):
        bloqueios, _ = inspecionar_formato(Path(__file__).read_bytes())
        self.assertEqual(bloqueios, [])

    def test_v3_formfeed_nao_desalinha_mapa_de_strings(self):
        codigo = "x = 1\x0c\ny = 2\nprint('OK-FIM', 'a\u00a0b')\n"
        d, t = self._arbitrar(codigo)
        self.assertEqual(d.estado, VERIFICADO)
        self.assertIn("AVISO: caractere invisível em string/comentário", t)

    # 2) núcleo invariante -------------------------------------------------------------
    CODIGO_COM_TESTES = ("import sys\nprint('OK-FIM')\n"
                         "print('test_a (m.C) ... ok', file=sys.stderr)\n"
                         "print('test_b (m.C) ... ok', file=sys.stderr)\n")

    def _dois_vereditos(self, executor_a: str, executor_b: str, autor="ChatGPT"):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_text(self.CODIGO_COM_TESTES, encoding="utf-8")
            va, _ = arbitrar(alvo, autor, executor_a, [], 0, ["OK-FIM"], None, 60, Path(tmp) / "a")
            vb, _ = arbitrar(alvo, autor, executor_b, [], 0, ["OK-FIM"], None, 60, Path(tmp) / "b")
            return ler_veredito(va), ler_veredito(vb)

    def test_v3_nucleo_converge_entre_executores_independentes(self):
        ta, tb = self._dois_vereditos("Meta AI", "Gemini")
        ok, linhas = comparar_vereditos(ta, tb)
        self.assertTrue(ok, linhas)
        self.assertEqual(ler_nucleo(ta)["testes"], ["test_a ok", "test_b ok"])
        self.assertIn("NUCLEO_INVARIANTE_SHA256: ", ta)

    def test_v3_autor_e_independente_divergem_no_estado(self):
        ta, tb = self._dois_vereditos("Claude", "Meta AI", autor="Claude")
        ok, linhas = comparar_vereditos(ta, tb)
        self.assertFalse(ok)
        self.assertTrue(any(l.startswith("DIFERE em estado") for l in linhas))

    def test_v3_nucleo_ignora_formato_do_unittest_e_tempo(self):
        dec = Decisao(VERIFICADO, ["executor independente; saída bateu com o critério"])
        e39 = Execucao(["py"], 0, "", "test_a (__main__.C) ... ok\nRan 1 test in 0.010s\n")
        e313 = Execucao(["py"], 0, "", "test_a (__main__.C.test_a) ... ok\nRan 1 test in 9.999s\n")
        n1 = montar_nucleo("h", 0, [], e39, dec, "X")
        n2 = montar_nucleo("h", 0, [], e313, dec, "Y")
        self.assertEqual(hash_nucleo(n1), hash_nucleo(n2))

    def test_v3_nucleo_diverge_quando_um_teste_muda(self):
        dec = Decisao(VERIFICADO, [])
        ok_ = Execucao(["py"], 0, "", "test_a (m.C) ... ok\n")
        fail = Execucao(["py"], 0, "", "test_a (m.C) ... FAIL\n")
        self.assertNotEqual(hash_nucleo(montar_nucleo("h", 0, [], ok_, dec, "X")),
                            hash_nucleo(montar_nucleo("h", 0, [], fail, dec, "X")))

    def test_v3_comparar_recusa_selo_adulterado(self):
        ta, tb = self._dois_vereditos("Meta AI", "Gemini")
        ok, linhas = comparar_vereditos(ta.replace("OK-FIM", "OK-FIX", 1), tb)
        self.assertFalse(ok)
        self.assertTrue(any("selo inválido" in l for l in linhas))

    # 3) matriz -------------------------------------------------------------------------
    def test_v3_matriz_com_dois_interpretadores_converge(self):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_text(self.CODIGO_COM_TESTES, encoding="utf-8")
            destino, conv = matriz(alvo, "ChatGPT", "Meta AI", [], 0, ["OK-FIM"], None, 60,
                                   Path(tmp) / "m", [sys.executable, sys.executable])
            texto = ler_veredito(destino)
        self.assertTrue(conv)
        self.assertIn("RESULTADO_MATRIZ: CONVERGENTE", texto)
        self.assertTrue(conferir_selo(texto)[0])

    @unittest.skipIf(os.name == "nt", "usa interpretador-embrulho em /bin/sh")
    def test_v3_matriz_detecta_interpretador_que_diverge(self):
        with tempfile.TemporaryDirectory() as tmp:
            # "Interpretador" que se comporta diferente: acrescenta um argumento extra.
            embrulho = Path(tmp) / "py_diferente"
            embrulho.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@" DIFERENTE\n', encoding="utf-8")
            os.chmod(embrulho, 0o755)
            alvo = Path(tmp) / "alvo.py"
            alvo.write_text("import sys\nprint('OK-FIM' if len(sys.argv) == 1 else 'OUTRO')\n",
                            encoding="utf-8")
            destino, conv = matriz(alvo, "ChatGPT", "Meta AI", [], 0, ["OK-FIM"], None, 60,
                                   Path(tmp) / "m", [sys.executable, str(embrulho)])
            texto = ler_veredito(destino)
        self.assertFalse(conv)
        self.assertIn("RESULTADO_MATRIZ: DIVERGENTE", texto)

    # 4) v3.2: portabilidade (caracteres reais, nenhum escape duplo) --------------
    def test_v32_canonico_so_converte_crlf(self):
        self.assertEqual(canonico("a\r\nb\r\n"), "a\nb\n")
        self.assertEqual(canonico("a\rb"), "a\rb")
        self.assertNotEqual(canonico("a\rb"), canonico("a\nb"))

    def test_v32_cr_isolado_nao_colide_no_selo(self):
        self.assertNotEqual(selar("a\rb\n"), selar("a\nb\n"))

    def test_v32_execucao_canoniza_crlf_do_filho(self):
        d, t = self._arbitrar("import sys\nsys.stdout.buffer.write(b'OK-FIM\\r\\nfim\\r\\n')\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertNotIn("\r\n", t)
        self.assertTrue(conferir_selo(t)[0])

    def test_v32_saida_unicode_com_x_utf8(self):
        d, t = self._arbitrar("print('OK-FIM \u00e7\u00e3o \u200b')\n")
        self.assertEqual(d.estado, VERIFICADO)
        self.assertTrue(conferir_selo(t)[0])

    def test_v32_veredito_lido_sem_traducao(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "v.txt"
            p.write_bytes(selar("x\n").replace("\n", "\r\n").encode("utf-8"))
            self.assertIn("\r\n", ler_veredito(p))
            self.assertFalse(conferir_selo(ler_veredito(p))[0])

    def test_v33_windows_passa_systemroot_e_so_ela(self):
        amb = {"PATH": "C:\\x", "SYSTEMROOT": "C:\\Windows", "SEGREDO": "nao-passa"}
        e = ambiente_minimo("D:\\t", "nt", amb)
        self.assertEqual(e.get("SYSTEMROOT"), "C:\\Windows")
        self.assertNotIn("SEGREDO", e)
        self.assertEqual(set(e), {"PATH", "HOME", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT"})
        self.assertNotIn("SYSTEMROOT", ambiente_minimo("/t", "posix", amb))
        self.assertEqual(ambiente_minimo("/t", "posix", amb)["PATH"], "/usr/bin:/bin")

    def test_v3_matriz_exige_dois_interpretadores(self):
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / "alvo.py"
            alvo.write_text("print('OK-FIM')\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                matriz(alvo, "A", "B", [], 0, ["OK-FIM"], None, 60, Path(tmp), [sys.executable])


# ----------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extras: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, extras = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(prog="tpl_arbitro_v3_3.py", description="Árbitro do TPL, versão 3.3")
    sub = p.add_subparsers(dest="cmd", required=True)
    for nome in ("arbitrar", "matriz"):
        a = sub.add_parser(nome)
        a.add_argument("arquivo", type=Path)
        a.add_argument("--autor", required=True)
        a.add_argument("--executor", required=True)
        a.add_argument("--esperar-exit", type=int, default=None)
        a.add_argument("--esperar", action="append", default=[])
        a.add_argument("--hash-informado", default=None)
        a.add_argument("--timeout", type=int, default=300)
        a.add_argument("--saida", type=Path, default=Path("."))
        a.add_argument("--python", action="append", default=[],
                       help="interpretador do arquivo julgado (matriz: um por versão)")
    c = sub.add_parser("conferir")
    c.add_argument("veredito", type=Path)
    k = sub.add_parser("comparar")
    k.add_argument("veredito_a", type=Path)
    k.add_argument("veredito_b", type=Path)
    sub.add_parser("autoteste")
    args = p.parse_args(argv)

    if args.cmd == "autoteste":
        print(f"Python {sys.version.split()[0]}")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TplArbitroV3Tests)
        ok = unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
        print(f"AUTOTESTE_TPL_ARBITRO_V3_3: {'PASSOU' if ok else 'FALHOU'}")
        return 0 if ok else 1
    if args.cmd == "conferir":
        ok, msg = conferir_selo(ler_veredito(args.veredito))
        print(msg)
        return 0 if ok else 1
    if args.cmd == "comparar":
        ok, linhas = comparar_vereditos(ler_veredito(args.veredito_a),
                                        ler_veredito(args.veredito_b))
        print("\n".join(linhas))
        print("RESULTADO: " + ("CONVERGENTE" if ok else "DIVERGENTE"))
        return 0 if ok else 1
    if args.cmd == "matriz":
        destino, conv = matriz(args.arquivo, args.autor, args.executor, extras,
                               args.esperar_exit, args.esperar, args.hash_informado,
                               args.timeout, args.saida, args.python)
        print(ler_veredito(destino))
        return 0 if conv else 1
    if len(args.python) > 1:
        p.error("arbitrar aceita um só --python; use 'matriz' para vários")
    destino, decisao = arbitrar(args.arquivo, args.autor, args.executor, extras,
                                args.esperar_exit, args.esperar, args.hash_informado,
                                args.timeout, args.saida, args.python[0] if args.python else None)
    print(f"ESTADO: {decisao.estado}")
    for m in decisao.motivos:
        print(f"MOTIVO: {m}")
    if decisao.nota:
        print(f"NOTA: {decisao.nota}")
    print(f"VEREDITO gravado em: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
