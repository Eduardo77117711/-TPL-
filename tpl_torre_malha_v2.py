"""tpl_torre_malha_v2.py - baterias cegas 1 a 4 da torre, medidas em toda a malha.

01/11/2026, Claude (Arbitro 2). Versao nova; tpl_torre_malha.py (v1) continua intacto.
So biblioteca padrao (decimal para logaritmos de alta precisao), sem estimativa.

Confere as respostas dos quatro gabaritos ja abertos, cujos compromissos foram:
  bateria 1  ed66b166...7e8e   (18 casos)
  bateria 2  0f51c5db...d3e9   (20 casos)
  bateria 3  659fccba...c8ac   (13 casos)
  bateria 4  d1df3f70...490e   (12 casos)
Saida identica em qualquer sistema; a ultima linha e o sha256 do resumo.
"""
import decimal
import functools
import hashlib
import sys

sys.setrecursionlimit(20000)
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


# ---------- torre T(h) = b^^h modulo 2^a 5^c (mesmo nucleo da v1) ----------
def capped(b, h, cap):
    """min(b^^h, cap), exato."""
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
    return (a - 1 if a >= 1 else 0) + (2 if c >= 1 else 0), (c - 1 if c >= 1 else 0)


@functools.lru_cache(maxsize=None)
def tet(b, h, a, c):
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


def H_mult10(b, k):
    d = min(v(2, b), v(5, b))
    for h in range(1, 10):
        if d * capped(b, h - 1, -(-k // d)) >= k:
            return h
    raise SystemExit("H_mult10 sem resposta")


# ---------- torre de bases mistas a^b^c... modulo m qualquer ----------
def phi(m):
    r, n, p = m, m, 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            r -= r // p
        p += 1
    if n > 1:
        r -= r // n
    return r


def ge(t, L):
    """a torre t (lista, associacao pela direita) vale >= L ?"""
    if len(t) == 1:
        return t[0] >= L
    if t[0] == 1:
        return 1 >= L
    e, p = 0, 1
    while p < L:
        p *= t[0]
        e += 1
    return ge(t[1:], e)


def val(t):
    return t[0] if len(t) == 1 else t[0] ** val(t[1:])


def tmod(t, m):
    if m == 1:
        return 0
    if len(t) == 1:
        return t[0] % m
    ph = phi(m)
    if ge(t[1:], ph):
        return pow(t[0], tmod(t[1:], ph) + ph, m)
    return pow(t[0], val(t[1:]), m)


def cauda_estavel(b, k):
    h = H(b, k)[0]
    return str(tet(b, h + 5, k, k)).zfill(k)


# ---------- logaritmos com decimal (precisao fixa, deterministica) ----------
CTX = decimal.Context(prec=120)


def log10d(n):
    return CTX.log10(decimal.Decimal(n))


def digitos(expoente, base):
    """quantidade de digitos de base^expoente."""
    return int(CTX.multiply(decimal.Decimal(expoente), log10d(base)).to_integral_value(decimal.ROUND_FLOOR)) + 1


def cabeca(expoente, base, n):
    x = CTX.multiply(decimal.Decimal(expoente), log10d(base))
    f = CTX.subtract(x, x.to_integral_value(decimal.ROUND_FLOOR))
    y = CTX.power(decimal.Decimal(10), f)
    return str(y).replace(".", "")[:n]


# ---------- os quatro gabaritos ----------
B1 = [((182, 60), (17, "943588069376")), ((624, 80), (21, "054443749376")), ((3126, 60), (11, "906503909376")),
      ((65535, 100), (7, "081787109375")), ((255, 100), (13, "019287109375")), ((1024, 90), (46, "838892158976")),
      ((1048576, 70), (34, "790129688576")), ((9765625, 90), (29, "338134765625")), ((18, 100), (52, "325354315776")),
      ((15, 100), (25, "765380859375")), ((25, 99), (32, "908447265625")), ((2, 100), (102, "353432948736")),
      ((5, 100), (49, "618408203125")), ((250, 50), (2, "000000000000")), ((31250, 40), (2, "000000000000")),
      ((4374, 70), (19, "653583589376")), ((1250, 60), (2, "000000000000")), ((80, 30), (2, "000000000000"))]
B2 = [((68, 150), (51, "554408677376")), ((124, 120), (41, "109982437376")), ((74, 100), (51, "549492146176")),
      ((126, 140), (46, "900759781376")), ((95, 150), (30, "433349609375")), ((4095, 200), (17, "081787109375")),
      ((128, 120), (121, "099289501696")), ((1875, 150), (75, "936279296875")), ((1944, 80), (81, "082234003456")),
      ((7, 100), (51, "511565172343")), ((3, 60), (61, "262464195387")), ((432, 150), (51, "904095461376")),
      ((1068, 150), (26, "870971109376"))]
B2_M10 = [((300, 600), 2), ((300, 601), 3), ((7000, 3), 1), ((4000, 10 ** 500), 3), ((20, 10 ** 30), 4),
          ((40, 10 ** 70), 4), ((10, 10 ** 10 + 1), 4)]


def bateria3():
    return [
        str(tmod([89060441849856, 12816128, 16, 6, 3], 10 ** 30)).zfill(30) == "358547048845066128708606099456",
        str(tmod([7, 11, 13, 17], 10 ** 30)).zfill(30) == "264467997001233768059349022743",
        str(tmod([2, 3, 5, 7, 11], 10 ** 30)).zfill(30) == "856593738181920705647065694208",
        str(tmod([12, 12, 12, 12], 10 ** 30)).zfill(30) == "950527023094648977415697596416",
        str(tmod([99, 98, 97, 96], 10 ** 30)).zfill(30) == "084657641971472603173565235201",
        str(tmod([3500, 3, 3, 3], 10 ** 30)).zfill(30) == "0" * 30,
        str(tmod([1250, 3, 2], 10 ** 30)).zfill(30) == "007450580596923828125000000000",
        H(864, 100) == (101, "089740660736"),
        H(46875, 200) == (100, "215576171875"),
        H(57, 120) == (40, "156879688057"),
        H_mult10(4000, 4) == 2 and H(4000, 4)[0] == 2,
        digitos(12816128 ** 2, 16) == 197780484370122,
        cabeca(10 ** 20, 7, 12) == "166581151278",
    ]


def bateria4():
    g20 = cauda_estavel(3, 20)
    return [
        g20 == "04575627262464195387",                    # Graham
        g20 == "04575627262464195387",                    # 3^^^3
        cauda_estavel(2, 20) == "98615075353432948736",  # 2^^^4
        str(tmod([5, 4, 3, 2], 10 ** 30)).zfill(30) == "113455914892256259918212890625",
        str(pow(2, 65536, 10 ** 30)).zfill(30) == "506072339445587895905719156736" and len(str(2 ** 65536)) == 19729,
        digitos(9 ** 9, 9) == 369693100,
        cabeca(2 ** 64, 2, 12) == "190697401160",
        tmod([7] * 50, 999999937) == 631922168,
        tmod([3, 3, 3, 3], 1000000007) == 200170240,
        str(tmod([6, 5, 4, 3, 2, 1], 10 ** 30)).zfill(30) == "893380022607743740081787109376",
        H_mult10(5120, 10 ** 20) == 3,
        H(98, 150) == (152, "728941735936"),
    ]


def main():
    linhas, falhas = [], 0

    def reg(rotulo, ok):
        nonlocal falhas
        falhas += not ok
        linhas.append("%s %s" % (rotulo, "OK" if ok else "DIVERGE"))

    for i, ((b, k), esp) in enumerate(B1, 1):
        reg("B1.%02d b=%d k=%d" % (i, b, k), H(b, k) == esp)
    for i, ((b, k), esp) in enumerate(B2, 1):
        reg("B2.%02d b=%d k=%d" % (i, b, k), H(b, k) == esp)
    for i, ((b, k), esp) in enumerate(B2_M10, 14):
        h = H_mult10(b, k)
        ok = h == esp and (k > 1000 or H(b, k)[0] == esp)
        reg("B2.%02d b=%d H=%d" % (i, b, h), ok)
    for i, ok in enumerate(bateria3(), 1):
        reg("B3.%02d" % i, ok)
    for i, ok in enumerate(bateria4(), 1):
        reg("B4.%02d" % i, ok)
    linhas.append("ESTADO: %s (%d/%d)" % ("PROVADO" if falhas == 0 else "DIVERGENTE",
                                        len(linhas) - falhas, len(linhas)))
    resumo = "\n".join(linhas) + "\n"
    sys.stdout.write(resumo)
    print("sha256_resumo=" + hashlib.sha256(resumo.encode()).hexdigest())
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
