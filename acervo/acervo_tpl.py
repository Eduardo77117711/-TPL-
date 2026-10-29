"""acervo_tpl.py v0.1 - TPL: acervo atomico enderecado por conteudo.

Cada arquivo vira um atomo identificado pelo sha256 dos proprios bytes.
Bytes iguais = mesmo atomo, guardado uma vez so; todas as localizacoes ficam no manifesto.
Nada e apagado: cada copia continua listada com sua origem (Drive ou GitHub).

Uso:
  python3 -I acervo_tpl.py montar META_DIR RAW_DIR [REPO_DIR ...] SAIDA_DIR
  python3 -I acervo_tpl.py conferir SAIDA_DIR
  python3 -I acervo_tpl.py autoteste
Estados textuais; so biblioteca padrao.
"""
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def ler_meta(meta_dir):
    linhas = []
    for nome in sorted(os.listdir(meta_dir)):
        if nome.endswith(".jsonl"):
            with open(os.path.join(meta_dir, nome), encoding="utf-8") as f:
                linhas.extend(json.loads(l) for l in f if l.strip())
    return linhas


def montar(meta_dir, raw_dir, repos, saida):
    obj = os.path.join(saida, "objetos")
    os.makedirs(obj, exist_ok=True)
    atomos, erros, vistos = {}, [], set()

    def guardar(b, local):
        h = sha_bytes(b)
        destino = os.path.join(obj, h[:2], h)
        if not os.path.exists(destino):
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "wb") as f:
                f.write(b)
        a = atomos.setdefault(h, {"bytes": len(b), "locais": []})
        a["locais"].append(local)

    for m in ler_meta(meta_dir):
        if m["id"] in vistos:
            continue
        vistos.add(m["id"])
        caminho = os.path.join(raw_dir, m["id"])
        if m.get("erro") or not os.path.exists(caminho):
            erros.append({"id": m["id"], "title": m.get("title"), "erro": m.get("erro", "bytes ausentes")})
            continue
        b = open(caminho, "rb").read()
        if m.get("sha256") and m["sha256"] != sha_bytes(b):
            erros.append({"id": m["id"], "title": m.get("title"), "erro": "sha256 do registro diverge dos bytes"})
            continue
        guardar(b, {"origem": "drive", "id": m["id"], "titulo": m.get("title"), "mime": m.get("mimeType"),
                    "pasta": m.get("parentId"), "criado": m.get("createdTime"), "exportado": bool(m.get("exportado"))})

    for repo in repos:
        nome = os.path.basename(os.path.normpath(repo))
        for raiz, dirs, arqs in os.walk(repo):
            dirs[:] = [d for d in dirs if d != ".git"]
            for a in sorted(arqs):
                p = os.path.join(raiz, a)
                guardar(open(p, "rb").read(), {"origem": "github", "repo": nome,
                                               "caminho": os.path.relpath(p, repo)})

    manifesto = {"versao": "acervo_tpl v0.1", "atomos": dict(sorted(atomos.items())), "erros": erros}
    total_locais = sum(len(a["locais"]) for a in atomos.values())
    manifesto["resumo"] = {
        "arquivos_lidos": total_locais,
        "atomos_unicos": len(atomos),
        "copias_repetidas": total_locais - len(atomos),
        "bytes_brutos": sum(a["bytes"] * len(a["locais"]) for a in atomos.values()),
        "bytes_unicos": sum(a["bytes"] for a in atomos.values()),
        "ligados_drive_github": sum(1 for a in atomos.values()
                                    if {l["origem"] for l in a["locais"]} == {"drive", "github"}),
        "erros": len(erros),
    }
    with open(os.path.join(saida, "manifesto.json"), "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=1, sort_keys=False)
    pacote = os.path.join(saida, "acervo_tpl.tar.xz")
    with tarfile.open(pacote, "w:xz", preset=9) as t:
        t.add(os.path.join(saida, "manifesto.json"), arcname="manifesto.json")
        t.add(obj, arcname="objetos")
    manifesto["resumo"]["bytes_comprimido"] = os.path.getsize(pacote)
    return manifesto["resumo"]


def conferir(saida):
    man = json.load(open(os.path.join(saida, "manifesto.json"), encoding="utf-8"))
    falhas = []
    for h, a in man["atomos"].items():
        p = os.path.join(saida, "objetos", h[:2], h)
        if not os.path.exists(p):
            falhas.append("atomo ausente " + h[:12])
            continue
        b = open(p, "rb").read()
        if sha_bytes(b) != h:
            falhas.append("bytes alterados " + h[:12])
        if len(b) != a["bytes"]:
            falhas.append("tamanho diverge " + h[:12])
    soltos = []
    for raiz, _, arqs in os.walk(os.path.join(saida, "objetos")):
        soltos.extend(a for a in arqs if a not in man["atomos"])
    if soltos:
        falhas.append("atomos fora do manifesto: %d" % len(soltos))
    estado = "INTEGRO (%d atomos)" % len(man["atomos"]) if not falhas else "DIVERGENTE (%d)" % len(falhas)
    return estado, falhas


def autoteste():
    falhas = []

    def ok(c, m):
        print(("OK    " if c else "FALHA ") + m)
        if not c:
            falhas.append(m)

    with tempfile.TemporaryDirectory() as d:
        meta, raw, repo, out = (os.path.join(d, x) for x in ("meta", "raw", "repo", "out"))
        for x in (meta, raw, repo):
            os.makedirs(x)
        arquivos = {"id1": b"verdade\n", "id2": b"verdade\n", "id3": b"outra\n"}
        with open(os.path.join(meta, "T.jsonl"), "w") as f:
            for i, b in arquivos.items():
                open(os.path.join(raw, i), "wb").write(b)
                f.write(json.dumps({"id": i, "title": i, "sha256": sha_bytes(b)}) + "\n")
            f.write(json.dumps({"id": "id4", "title": "falhou", "erro": "403"}) + "\n")
            f.write(json.dumps({"id": "id1", "title": "id1 repetido na listagem"}) + "\n")
        open(os.path.join(repo, "base.py"), "wb").write(b"outra\n")
        r = montar(meta, raw, [repo], out)
        ok(r["atomos_unicos"] == 2, "bytes iguais viram 1 atomo (3 arquivos + 1 do repo -> 2)")
        ok(r["copias_repetidas"] == 2, "copias repetidas contadas, nao apagadas")
        ok(r["ligados_drive_github"] == 1, "mesmo hash no Drive e no GitHub fica ligado")
        ok(r["erros"] == 1, "download falho fica registrado como erro, sem bytes inventados")
        ok(conferir(out)[0].startswith("INTEGRO"), "acervo montado confere")
        h = sha_bytes(b"verdade\n")
        p = os.path.join(out, "objetos", h[:2], h)
        open(p, "ab").write(b"x")
        ok(conferir(out)[0].startswith("DIVERGENTE"), "mutante: 1 byte alterado e detectado")
        open(p, "wb").write(b"verdade\n")
        os.remove(p)
        ok(conferir(out)[0].startswith("DIVERGENTE"), "mutante: atomo removido e detectado")
        open(p, "wb").write(b"verdade\n")
        extra = os.path.join(out, "objetos", "ff", "f" * 64)
        os.makedirs(os.path.dirname(extra), exist_ok=True)
        open(extra, "wb").write(b"intruso")
        ok(conferir(out)[0].startswith("DIVERGENTE"), "mutante: atomo intruso fora do manifesto e detectado")
        os.remove(extra)
        ok(conferir(out)[0].startswith("INTEGRO"), "restaurado volta a conferir")
        with tarfile.open(os.path.join(out, "acervo_tpl.tar.xz")) as t:
            nomes = t.getnames()
        ok("manifesto.json" in nomes, "pacote comprimido contem o manifesto")
    print("ESTADO: " + ("DIVERGENTE (%d)" % len(falhas) if falhas else "PROVADO (10/10)"))
    return 1 if falhas else 0


def main(a):
    if a == ["autoteste"]:
        return autoteste()
    if len(a) >= 4 and a[0] == "montar":
        print(json.dumps(montar(a[1], a[2], a[3:-1], a[-1]), indent=1))
        return 0
    if len(a) == 2 and a[0] == "conferir":
        estado, falhas = conferir(a[1])
        print("ESTADO: " + estado)
        for x in falhas[:20]:
            print("  " + x)
        return 0 if estado.startswith("INTEGRO") else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
