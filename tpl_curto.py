# TPL — medição curta (Golden Gate). Copie, cole e rode: python tpl_curto.py
import hashlib, json
V = {"vao_central": 1280, "vao_lateral": 343, "torre_agua": 227, "torre_pista": 152}
pista = V["torre_agua"] - V["torre_pista"]                    # 75 m
flecha = V["torre_pista"] - 6                                  # 146 m (folga de 6 m: estimativa)
flecha_lat = flecha * (V["vao_lateral"] / V["vao_central"]) ** 2  # f = wL²/8H
cabo = [round(V["torre_agua"] - 4 * flecha * (i / 32) * (1 - i / 32), 3) for i in range(33)]
medida = {
    "pista_m": pista,
    "flecha_central_m": flecha,
    "flecha_lateral_m": round(flecha_lat, 3),
    "lateral_sobre_central": round(V["vao_lateral"] / V["vao_central"], 6),
    "cabo_minimo_m": min(cabo),
    "cabo_minimo_no_meio": "SIM" if cabo.index(min(cabo)) == 16 else "NAO",
    "cabo_simetrico": "SIM" if cabo == cabo[::-1] else "NAO",
}
texto = json.dumps(medida, sort_keys=True)
print(texto)
print("resultado_sha256:", hashlib.sha256(texto.encode()).hexdigest())
