#!/usr/bin/env python3
"""Simulacao local, por vetor de estado, do polinomio de Mermin para GHZ-8.

Usa apenas a biblioteca padrao do Python. Nao exige Qiskit nem hardware quantico.
Convencao: X em cada qubit; Y nos subconjuntos de cardinalidade par;
coeficiente (-1)^(|S|/2).
"""

from math import sqrt

N = 8
DIM = 1 << N
ALL_BITS = DIM - 1


def bit_count(value: int) -> int:
    # Compativel com Python 3.10+.
    return value.bit_count()


def apply_x_y_string(state, y_mask: int):
    """Aplica tensor de X/Y indicado por y_mask: 0->X, 1->Y."""
    result = [0j] * DIM
    for basis_index, amplitude in enumerate(state):
        phase = 1 + 0j
        for qubit in range(N):
            if (y_mask >> qubit) & 1:
                bit = (basis_index >> qubit) & 1
                # Y|0> = i|1>; Y|1> = -i|0>.
                phase *= 1j if bit == 0 else -1j
        destination = basis_index ^ ALL_BITS  # X e Y invertem cada qubit.
        result[destination] += phase * amplitude
    return result


def inner_product(left, right) -> complex:
    return sum(a.conjugate() * b for a, b in zip(left, right))


def build_mermin_terms():
    """Lista os 2^(N-1)=128 termos com numero par de observaveis Y."""
    terms = []
    for y_mask in range(DIM):
        k = bit_count(y_mask)
        if k % 2 == 0:
            coefficient = -1 if (k // 2) % 2 else 1
            terms.append((y_mask, coefficient))
    return terms


def classical_deterministic_bound(terms) -> int:
    """Maximiza o polinomio sobre resultados locais X_i,Y_i em {-1,+1}.

    A expressao depende dos 16 resultados locais apenas por d_i=X_i*Y_i
    e pelo fator global produto(X_i), de modulo 1. Portanto basta percorrer
    todos os 2^8 padroes possiveis de d_i, sem perder estrategias classicas.
    """
    maximum = 0
    for d_mask in range(DIM):
        value = 0
        for y_mask, coefficient in terms:
            parity = bit_count(y_mask & d_mask) % 2
            product = -1 if parity else 1
            value += coefficient * product
        maximum = max(maximum, abs(value))
    return maximum


def main():
    # Estado GHZ+ = (|00000000> + |11111111>)/sqrt(2).
    ghz = [0j] * DIM
    ghz[0] = 1 / sqrt(2)
    ghz[-1] = 1 / sqrt(2)

    terms = build_mermin_terms()
    quantum_value = 0j
    individual_correlations = []

    for y_mask, coefficient in terms:
        transformed = apply_x_y_string(ghz, y_mask)
        correlation = inner_product(ghz, transformed)
        individual_correlations.append(correlation)
        quantum_value += coefficient * correlation

    classical_bound = classical_deterministic_bound(terms)
    quantum_max_for_operator = DIM // 2  # 2^(N-1) para esta convencao GHZ/Mermin.

    # Testes de consistencia: impedem imprimir um resultado esperado se falhar.
    assert len(terms) == 128, f"Numero de termos inesperado: {len(terms)}"
    assert all(abs(c.imag) < 1e-10 for c in individual_correlations)
    assert all(abs(abs(c.real) - 1.0) < 1e-10 for c in individual_correlations)
    assert abs(quantum_value.imag) < 1e-10
    assert abs(quantum_value.real - quantum_max_for_operator) < 1e-10
    assert classical_bound == 16, f"Limite classico inesperado: {classical_bound}"

    print("=== SIMULACAO GHZ-8 / MERMIN ===")
    print(f"Qubits: {N}")
    print(f"Estado: (|0...0> + |1...1>)/sqrt(2)")
    print(f"Termos do polinomio: {len(terms)}")
    print(f"Valor de Mermin (simulacao): {quantum_value.real:.1f}")
    print(f"Limite classico (maximizacao exaustiva): {classical_bound}")
    print(f"Ideal quantico desta convencao: {quantum_max_for_operator}")
    print(f"Razao quantico/classico: {quantum_value.real / classical_bound:.1f}x")
    print("TESTES: PASSOU")
    print("Escopo: simulacao matematica local; nao e experimento em hardware quantico.")


if __name__ == "__main__":
    main()
