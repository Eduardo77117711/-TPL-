# TPL - medicao curta (Golden Gate) em Ruby. Mesmo calculo do tpl_curto.py.
# Rode: ruby tpl_curto.rb
require "digest"
V = { vao_central: 1280, vao_lateral: 343, torre_agua: 227, torre_pista: 152 }
def round_n(x, n) = format("%.#{n}f", x).to_f
pista = V[:torre_agua] - V[:torre_pista]
flecha = V[:torre_pista] - 6
razao = V[:vao_lateral].to_f / V[:vao_central]
flecha_lat = flecha * razao**2
cabo = (0..32).map { |i| round_n(V[:torre_agua] - 4 * flecha * (i / 32.0) * (1 - i / 32.0), 3) }
minimo = cabo.min
texto = %({"cabo_minimo_m": #{minimo}, "cabo_minimo_no_meio": "#{cabo.index(minimo) == 16 ? 'SIM' : 'NAO'}", ) +
        %("cabo_simetrico": "#{cabo == cabo.reverse ? 'SIM' : 'NAO'}", "flecha_central_m": #{flecha}, ) +
        %("flecha_lateral_m": #{round_n(flecha_lat, 3)}, "lateral_sobre_central": #{round_n(razao, 6)}, "pista_m": #{pista}})
puts texto
puts "resultado_sha256: #{Digest::SHA256.hexdigest(texto)}"
