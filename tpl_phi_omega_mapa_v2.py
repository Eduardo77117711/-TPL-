# TPL — Phi_Omega que vibra, mapa v2: inclui o decaimento exotico h -> s s (quando m_novo < m_h/2).
# Convencao: V = -mu2 h^2/2 + lam h^4/4 + m0^2 phi^2/2 + lp phi^4/4 + kap phi^2 h^2/2  (mesma do portal, SHA 4972d64d...)
# Forca do sinal: mu = c^4 / (c^2 + Gamma_novo/Gamma_SM), Gamma_SM(125 GeV) = 4.07e-3 GeV. Corte declarado antes: mu >= 0.88.
import sympy as sp, math, hashlib
H, S = sp.symbols('H S', real=True)            # estados de massa
v, mh, GSM = 246.22, 125.25, 4.07e-3
linhas = []
C = 1000.0
for mn in (30.0, 50.0, 200.0, 500.0):
    for s2 in (0.01, 0.05, 0.10, 0.20):
        c2 = 1 - s2; c, s = math.sqrt(c2), math.sqrt(s2)
        sgn = 1.0 if mn > mh else -1.0         # sinal do angulo que reproduz a mistura com kap > 0 ou < 0
        Mhh = c2*mh**2 + s2*mn**2; Mss = s2*mh**2 + c2*mn**2; Mhs = c*s*(mn**2 - mh**2)
        lam, lp, kap = Mhh/(2*v*v), Mss/(2*C*C), Mhs/(2*v*C)
        # rotacao: h = v + c*H - s*S*sgn' ; phi = C + s*H + c*S  (escolhida para que H seja o estado tipo Higgs)
        th = math.atan2(2*Mhs, Mhh - Mss)/2
        ct, st = math.cos(th), math.sin(th)
        hh = v + ct*H - st*S; pp = C + st*H + ct*S
        mu2 = lam*v*v + kap*C*C; m02 = -lp*C*C - kap*v*v
        V = -mu2*hh**2/2 + lam*hh**4/4 + m02*pp**2/2 + lp*pp**4/4 + kap*pp**2*hh**2/2
        P = sp.Poly(sp.expand(V), H, S)
        mH2 = 2*float(P.coeff_monomial(H**2)); mS2 = 2*float(P.coeff_monomial(S**2))
        mH, mS = math.sqrt(mH2), math.sqrt(mS2)
        if abs(mH - mh) > abs(mS - mh): mH, mS = mS, mH; ct, st = st, ct   # H = estado tipo Higgs
        frac = ct**2
        g = 2*float(P.coeff_monomial(H*S**2)) if abs(math.sqrt(mH2)-mh) < abs(math.sqrt(mS2)-mh) else 2*float(P.coeff_monomial(S*H**2))
        Gnovo = 0.0
        if mS < mH/2:
            Gnovo = g*g/(32*math.pi*mH)*math.sqrt(1 - 4*mS*mS/(mH*mH))
        mu = frac**2/(frac + Gnovo/GSM)
        linhas.append(f"m_novo={mn:.0f}GeV sin2={s2:.2f}: m_H={mH:.2f} m_S={mS:.2f} fracao_h={frac:.4f} Gamma_novo={Gnovo:.3e}GeV mu={mu:.4f} sinal_LHC={'PASSA' if mu >= 0.88 else 'EXCLUIDO'}")
for l in linhas: print(l)
bloco = "\n".join(linhas) + "\n"
print("sha256_mapa_v2=" + hashlib.sha256(bloco.encode()).hexdigest())
