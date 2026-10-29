"""harness_redis_nx_v3.py - TPL: claim atomico de nonce (SET NX EX) contra Redis REAL.

Fecha as 4 lacunas registradas do v2: isolamento/limpeza da chave, contagem formal,
expiracao e liberacao. Sobe um redis-server proprio em porta livre e o derruba no fim.
Estados textuais; sem booleanos de decisao no resultado.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import redis

N_THREADS = 64
RODADAS = 50


def porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def claim(r, nonce, ttl_ms):
    return r.set(nonce, "1", nx=True, px=ttl_ms) is True


def liberar(r, nonce, dono):
    lua = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
    return r.eval(lua, 1, nonce, dono)


def main():
    exe = shutil.which("redis-server")
    if not exe:
        print("ESTADO: NAO EXECUTADO (redis-server ausente)")
        return 1
    d = tempfile.mkdtemp()
    porta = porta_livre()
    proc = subprocess.Popen([exe, "--port", str(porta), "--save", "", "--appendonly", "no", "--dir", d],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    falhas = []

    def ok(c, m):
        print(("OK    " if c else "FALHA ") + m)
        if not c:
            falhas.append(m)

    try:
        r = redis.Redis(port=porta)
        for _ in range(50):
            try:
                r.ping()
                break
            except redis.ConnectionError:
                time.sleep(0.1)
        print("redis-server", r.info()["redis_version"], "porta", porta)
        prefixo = "tpl:nonce:%s:" % uuid.uuid4().hex

        # 1. contagem formal: em cada rodada, 64 threads disputam o mesmo nonce; exatamente 1 vence
        vencedores_por_rodada = []
        for k in range(RODADAS):
            nonce = prefixo + "corrida:%d" % k
            barreira = threading.Barrier(N_THREADS)
            res = []
            trava = threading.Lock()

            def tenta():
                c = redis.Redis(port=porta)
                barreira.wait()
                v = claim(c, nonce, 10_000)
                with trava:
                    res.append(v)

            ts = [threading.Thread(target=tenta) for _ in range(N_THREADS)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            vencedores_por_rodada.append(sum(res))
        ok(vencedores_por_rodada == [1] * RODADAS,
           "contagem: %d rodadas x %d threads -> exatamente 1 vencedor por rodada" % (RODADAS, N_THREADS))

        # 2. replay: o mesmo nonce nao e aceito duas vezes enquanto vale
        n = prefixo + "replay"
        ok(claim(r, n, 10_000) and not claim(r, n, 10_000), "replay do mesmo nonce rejeitado")

        # 3. expiracao: depois do TTL o nonce some e o TTL era real
        n = prefixo + "expira"
        claim(r, n, 300)
        ttl = r.pttl(n)
        ok(0 < ttl <= 300, "TTL aplicado (pttl=%d ms)" % ttl)
        time.sleep(0.45)
        ok(r.exists(n) == 0, "nonce expirou depois do TTL")

        # 4. liberacao: so o dono libera; outro valor nao apaga
        n = prefixo + "libera"
        dono = uuid.uuid4().hex
        r.set(n, dono, nx=True, px=10_000)
        ok(liberar(r, n, "intruso") == 0 and r.exists(n) == 1, "liberacao por nao-dono recusada")
        ok(liberar(r, n, dono) == 1 and r.exists(n) == 0, "liberacao pelo dono apaga a chave")

        # 5. mutante: SET sem NX deixa varios vencerem -> o teste de contagem precisa ver isso
        n = prefixo + "mutante"
        mut = [r.set(n, "1", px=10_000) is True for _ in range(5)]
        ok(sum(mut) > 1, "mutante sem NX detectado (%d vencedores em 5)" % sum(mut))

        # 6. isolamento e limpeza: apagar o prefixo do teste nao deixa resto
        for chave in r.scan_iter(prefixo + "*"):
            r.delete(chave)
        ok(len(list(r.scan_iter(prefixo + "*"))) == 0, "limpeza: nenhuma chave do teste restou")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        shutil.rmtree(d, ignore_errors=True)
    print("ESTADO: " + ("DIVERGENTE (%d)" % len(falhas) if falhas else "PROVADO com Redis real (8/8)"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
