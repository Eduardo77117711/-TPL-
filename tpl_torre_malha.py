"""tpl_torre_malha.py - Torre fora do dominio coprimo (2|b ou 5|b), medida em toda a malha.

01/11/2026, Claude (Arbitro 2). So biblioteca padrao, sem ponto flutuante, sem estimativa.

Definicoes:
  T(1)=b, T(h+1)=b^T(h)
  H(b,k) = menor h com T(h) = T(h+1) = T(h+2) (mod 10^k)
  s(h)   = quantos digitos finais T(h) e T(h+1) tem em comum

Mede:
  [A] os 18 casos da bateria cega (gabarito ed66b166...7e8e): H e os 12 ultimos digitos
  [B] os 14 pares (V,c) com s(h) = V*h + c, conferidos ate k=160
  [C] multiplos de 10 pela regra H = min{h : min(v2,v5)*T(h-1) >= k}, com T(0)=1,
      incluindo H(20480, 10^100) = 3

Todo modulo usado e da forma 2^a 5^c: phi(2^a 5^c) fica no mesmo conjunto, entao a
recursao de Euler com overflow nunca sai dele. min(T(h), cap) e calculado exato.
Saida identica em qualquer sistema; a ultima linha e o sha256 do resumo.
"""
import functools
import hashlib
import sys

sys.setrecursionlimit(20000)


def capped(b, h, cap):
    """min(T(h), cap), exato, sem construir torre gigante."""
    if cap <= 1:
        return cap
    if h == 0:
        return 1
    if h == 1:
        return min(b, cap)
    e_cap, p = 0, 1
    while p < cap:
        p *= b
        e_cap += 1
    prev = capped(b, h - 1, e_cap)
    if prev >= e_cap:
        return cap
    return min(b ** prev, cap)


def phi_exp(a, c):
    """expoentes de phi(2^a 5^c) = 2^a' 5^c'."""
    a2 = (a - 1 if a >= 1 else 0) + (2 if c >= 1 else 0)
    c2 = c - 1 if c >= 1 else 0
    return a2, c2


@functools.lru_cache(maxsize=None)
def tet(b, h, a, c):
    """T(h) mod 2^a 5^c, exato."""
    m = (2 ** a) * (5 ** c)
    if m == 1:
        return 0
    if h == 1:
        return b % m
    a2, c2 = phi_exp(a, c)
    ph = (2 ** a2) * (5 ** c2)
    e = capped(b, h - 1, ph)
    if e < ph:
        return pow(b, e, m)
    return pow(b, tet(b, h - 1, a2, c2) + ph, m)


def H(b, k, persist=10):
    r = []
    for h in range(1, 1000):
        r.append(tet(b, h, k, k))
        if len(r) >= 3 and r[-1] == r[-2] == r[-3]:
            for x in range(h + 1, h + 1 + persist):
                if tet(b, x, k, k) != r[-1]:
                    raise SystemExit("PLATO QUEBROU b=%d k=%d" % (b, k))
            return h - 2, str(r[-1]).zfill(k)[-12:]
    raise SystemExit("SEM PLATO b=%d k=%d" % (b, k))


def v(p, n):
    x = 0
    while n % p == 0:
        n //= p
        x += 1
    return x


CASOS = [(182, 60), (624, 80), (3126, 60), (65535, 100), (255, 100), (1024, 90),
         (1048576, 70), (9765625, 90), (18, 100), (15, 100), (25, 99), (2, 100),
         (5, 100), (250, 50), (31250, 40), (4374, 70), (1250, 60), (80, 30)]
GABARITO = [(17, "943588069376"), (21, "054443749376"), (11, "906503909376"),
            (7, "081787109375"), (13, "019287109375"), (46, "838892158976"),
            (34, "790129688576"), (29, "338134765625"), (52, "325354315776"),
            (25, "765380859375"), (32, "908447265625"), (102, "353432948736"),
            (49, "618408203125"), (2, "000000000000"), (2, "000000000000"),
            (19, "653583589376"), (2, "000000000000"), (2, "000000000000")]
RETAS = {182: (4, -8, 2), 624: (4, -4, 1), 4374: (4, -4, 1), 3126: (5, 5, 2),
         65535: (16, 1, 2), 255: (8, 1, 2), 1024: (2, -2, 1), 1048576: (2, 2, 1),
         9765625: (3, 3, 1), 18: (2, -4, 2), 15: (4, 1, 2), 25: (3, 3, 2),
         2: (1, -2, 2), 5: (2, 2, 3)}
MULT10 = [(80, 1, 1), (80, 30, 2), (80, 10 ** 100, 3), (50, 1, 1), (50, 50, 2), (50, 51, 3),
          (100, 2, 1), (250, 250, 2), (250, 251, 3), (20480, 10 ** 100, 3)]


def H_mult10(b, k):
    d = min(v(2, b), v(5, b))
    for h in range(1, 10):
        if d * capped(b, h - 1, -(-k // d)) >= k:
            return h
    raise SystemExit("H_mult10 sem resposta")


def main():
    linhas, falhas = [], 0
    for (b, k), (gh, gt) in zip(CASOS, GABARITO):
        h, t = H(b, k)
        ok = (h, t) == (gh, gt)
        falhas += not ok
        linhas.append("A b=%d k=%d H=%d ultimos12=%s %s" % (b, k, h, t, "OK" if ok else "DIVERGE"))
    K = 160
    for b, (V, c, h0) in RETAS.items():
        r = [tet(b, h, K, K) for h in range(1, K + 6)]
        ok = True
        for h in range(h0, len(r)):
            d = (r[h] - r[h - 1]) % (10 ** K)
            s = 0
            while s < K and d % 10 ** (s + 1) == 0:
                s += 1
            if s >= K:
                break
            if s != V * h + c:
                ok = False
                break
        falhas += not ok
        linhas.append("B b=%d V=%d c=%d inicio_h=%d %s" % (b, V, c, h0, "OK" if ok else "DIVERGE"))
    for b, k, esperado in MULT10:
        h = H_mult10(b, k)
        if k <= 300:
            h2 = H(b, k)[0]
            ok = h == esperado == h2
        else:
            ok = h == esperado
        falhas += not ok
        kk = "10^100" if k == 10 ** 100 else str(k)
        linhas.append("C b=%d k=%s H=%d %s" % (b, kk, h, "OK" if ok else "DIVERGE"))
    linhas.append("ESTADO: %s (%d/%d)" % ("PROVADO" if falhas == 0 else "DIVERGENTE",
                                        len(linhas) - falhas, len(linhas)))
    resumo = "\n".join(linhas) + "\n"
    sys.stdout.write(resumo)
    print("sha256_resumo=" + hashlib.sha256(resumo.encode()).hexdigest())
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
