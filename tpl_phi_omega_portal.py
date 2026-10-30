# TPL — Phi_Omega pelo portal de Higgs: o que o "silencio que permanece" permite medir.
# V = -mu2*h^2/2 + lam*h^4/4 + m0^2*phi^2/2 + lp*phi^4/4 + kap*phi^2*h^2/2   (h, phi reais; [h]=[phi]=GeV)
import sympy as sp, hashlib, math
h, phi, mu2, lam, m0, lp, kap = sp.symbols('h phi mu2 lam m0 lp kap', real=True)
V = -mu2*h**2/2 + lam*h**4/4 + m0**2*phi**2/2 + lp*phi**4/4 + kap*phi**2*h**2/2
v, C = sp.symbols('v C', positive=True)
# 1) Silencio estrito: phi congelado em C (sem flutuacao). So h e dinamico.
Vh = V.subs(phi, C)
mu2_sol = sp.solve(sp.diff(Vh, h).subs(h, v), mu2)[0]          # mu2 que coloca o minimo em v
mh2_frozen = sp.simplify(sp.diff(Vh, h, 2).subs({h: v, mu2: mu2_sol}))
print("1) phi congelado: mu2_efetivo =", sp.simplify(mu2_sol), "| massa^2 do Higgs =", mh2_frozen)
print("   -> massa = 2*lam*v^2, identica ao Modelo Padrao: C so redefine mu2 (nao observavel).")
# 2) Silencio com flutuacao: phi = C + s. Matriz de massa (h, s) no minimo (v, C).
sol = sp.solve([sp.diff(V, h).subs({h: v, phi: C}), sp.diff(V, phi).subs({h: v, phi: C})], [mu2, m0**2], dict=True)[0]
M = sp.Matrix([[sp.diff(V, a, b) for b in (h, phi)] for a in (h, phi)]).subs({h: v, phi: C}).subs(sol)
M = sp.simplify(M)
print("2) phi flutua: matriz de massa (h, s) =", M.tolist())
print("   termo de mistura = 2*kap*v*C  (zero se kap=0 ou C=0)")
# 3) Numero: angulo de mistura e sinal do Higgs no LHC (mu = cos^2 theta).
vnum, mh = 246.22, 125.25
lamnum = mh**2/(2*vnum**2)
linhas = []
for kapn in (0.0, 0.01, 0.05, 0.1):
    for Cn in (100.0, 1000.0):
        for lpn in (0.1,):
            Mn = M.subs({v: vnum, C: Cn, lam: lamnum, kap: kapn, lp: lpn})
            a, b, c = float(Mn[0,0]), float(Mn[0,1]), float(Mn[1,1])
            d = math.sqrt((a-c)**2 + 4*b*b)
            est = []
            for m2 in ((a+c-d)/2, (a+c+d)/2):
                vx, vy = (b, m2 - a) if abs(b) > 1e-12 else ((1.0, 0.0) if abs(m2-a) < abs(m2-c) else (0.0, 1.0))
                n = math.hypot(vx, vy); est.append((math.sqrt(max(m2, 0)), (vx/n)**2))
            hig = max(est, key=lambda e: e[1])   # estado com mais componente de Higgs
            out = min(est, key=lambda e: e[1])
            linhas.append(f"kap={kapn} C={Cn:.0f}GeV lp={lpn}: tipo_Higgs m={hig[0]:.2f}GeV fracao_h={hig[1]:.4f} | novo m={out[0]:.2f}GeV fracao_h={out[1]:.4f}")
for l in linhas: print("3)", l)
bloco = "\n".join(linhas) + "\n"
print("sha256_tabela=" + hashlib.sha256(bloco.encode()).hexdigest())
