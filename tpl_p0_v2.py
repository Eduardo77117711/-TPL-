# TPL - Portao P0 (completude do estado) v2. Escrito por Claude (Arbitro 2), 31/10/2026.
# Regra v2: todo arquivo da arvore entra no universo; so sai o que esta em EXCLUIR, com motivo.
# Fonte do universo: a arvore do git na versao (git ls-tree), nunca o proprio tpl_estado.json.
# Uso: python3 -I tpl_p0.py <pasta_do_repositorio>   |   python3 -I tpl_p0.py autoteste
import hashlib, json, subprocess, sys, os, tempfile

EXCLUIR = {
    '.gitignore': 'configuracao do git; nao e executado nem lido por codigo',
    'LICENSE': 'texto legal; nao e executado nem lido por codigo',
    'NOTICE': 'texto legal; nao e executado nem lido por codigo',
    'README.md': 'texto; nao e executado nem lido por codigo',
    'tpl_estado.json': 'auto-referencia: o estado nao pode conter o proprio hash',
}

def universo(repo):
    out = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', 'HEAD'],
                         capture_output=True, text=True, check=True).stdout.split('\n')
    return sorted(f for f in out if f and f not in EXCLUIR)

def medir(repo, nome_repo='-TPL-'):
    est = json.load(open(os.path.join(repo, 'tpl_estado.json'), encoding='utf-8'))
    decl = {a['arquivo']: a['sha256'] for a in est['artefatos'] if a['repositorio'] == nome_repo}
    fora, pin_errado = [], []
    for f in universo(repo):
        if f not in decl:
            fora.append(f)
        else:
            h = hashlib.sha256(open(os.path.join(repo, f), 'rb').read()).hexdigest()
            if h != decl[f]:
                pin_errado.append(f)
    fantasmas = sorted(f for f in decl if not os.path.exists(os.path.join(repo, f)))
    return fora, pin_errado, fantasmas

def autoteste():
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, check=True)
        g('init', '-q'); g('config', 'user.email', 't@t'); g('config', 'user.name', 't')
        open(os.path.join(d, 'a.py'), 'w').write('print(1)\n')
        open(os.path.join(d, 'b.py'), 'w').write('print(2)\n')
        ha = hashlib.sha256(b'print(1)\n').hexdigest()
        est = {'artefatos': [{'repositorio': '-TPL-', 'arquivo': 'a.py', 'sha256': ha},
                             {'repositorio': '-TPL-', 'arquivo': 'x.py', 'sha256': '0' * 64}]}
        json.dump(est, open(os.path.join(d, 'tpl_estado.json'), 'w'))
        g('add', '.'); g('commit', '-qm', 't')
        fora, pin, fant = medir(d)
        ok += fora == ['b.py']            # omitido e achado pela arvore
        ok += pin == []                   # pin certo nao acusa
        ok += fant == ['x.py']            # declarado que nao existe
        open(os.path.join(d, 'a.py'), 'w').write('print(9)\n'); g('commit', '-qam', 'm')
        ok += medir(d)[1] == ['a.py']     # bytes mudados acusam
    print('AUTOTESTE_TPL_P0:', ok, '/ 4'); return ok == 4

if __name__ == '__main__':
    if sys.argv[1:] == ['autoteste']:
        sys.exit(0 if autoteste() else 1)
    fora, pin, fant = medir(sys.argv[1])
    print('universo:', len(universo(sys.argv[1])), '| excluidos:', len(EXCLUIR))
    print('fora_do_estado:', len(fora)); [print('  FORA', f) for f in fora]
    print('pin_errado:', len(pin)); [print('  PIN', f) for f in pin]
    print('declarado_inexistente:', len(fant))
    print('P0:', 'CUMPRE' if not (fora or pin or fant) else 'FALHA')
    sys.exit(0 if not (fora or pin or fant) else 1)
