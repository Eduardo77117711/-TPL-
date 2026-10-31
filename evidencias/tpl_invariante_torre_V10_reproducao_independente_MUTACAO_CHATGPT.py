#!/usr/bin/env python3
"""Reprodução modular independente da torre x_(n+1) = 3**x_n.

Proveniência:
- Pedido e contexto matemático: usuário.
- Implementação deste reprodutor e registro: ChatGPT.
- Este arquivo é uma reprodução independente; não é uma cópia nem uma
  execução do arquivo tpl_invariante_torre.py mencionado pelo usuário.

A torre não é materializada. Os resíduos são calculados por redução recursiva
via função totiente de Euler. A estabilização para todas as alturas h >= 13
é demonstrada separadamente com a função de Carmichael lambda(MOD).
"""

# Acréscimo do teste de mutação do oráculo: ChatGPT.

from functools import lru_cache
from math import gcd
import sys

MOD = 10**12
BASE = 3
V = 10
FIXED_RESIDUE = 262_464_195_387


def prime_powers(n: int) -> list[tuple[int, int]]:
    """Fatoração de n em pares (primo, expoente), por tentativa exata."""
    if n < 1:
        raise ValueError("n deve ser >= 1")
    factors: list[tuple[int, int]] = []
    remaining = n
    p = 2
    while p * p <= remaining:
        if remaining % p == 0:
            exponent = 0
            while remaining % p == 0:
                remaining //= p
                exponent += 1
            factors.append((p, exponent))
        p += 1 if p == 2 else 2
    if remaining > 1:
        factors.append((remaining, 1))
    return factors


def euler_phi(n: int) -> int:
    """Calcula phi(n) a partir da fatoração prima."""
    result = n
    for p, _ in prime_powers(n):
        result = (result // p) * (p - 1)
    return result


def carmichael_lambda(n: int) -> int:
    """Calcula lambda(n) como o MMC dos valores para cada potência prima."""
    result = 1
    for p, exponent in prime_powers(n):
        if p == 2 and exponent >= 3:
            component = 2 ** (exponent - 2)
        else:
            component = (p ** (exponent - 1)) * (p - 1)
        result = (result // gcd(result, component)) * component
    return result


@lru_cache(maxsize=None)
def tower_mod(height: int, modulus: int) -> int:
    """Retorna T_height mod modulus sem construir a torre inteira.

    Convenção: T_1 = 3 e T_(h+1) = 3**T_h.
    A redução de expoente por phi(modulus) é válida porque gcd(3, modulus)=1
    para todos os módulos da cadeia de totientes iniciada em 10**12.
    """
    if height < 1:
        raise ValueError("height deve ser >= 1")
    if modulus < 1:
        raise ValueError("modulus deve ser >= 1")
    if modulus == 1:
        return 0
    if height == 1:
        return BASE % modulus
    if gcd(BASE, modulus) != 1:
        raise ValueError(
            "A redução direta por phi exige gcd(BASE, modulus) == 1"
        )
    reduced_exponent = tower_mod(height - 1, euler_phi(modulus))
    return pow(BASE, reduced_exponent, modulus)


def totient_chain(start: int) -> list[int]:
    chain = [start]
    while chain[-1] != 1:
        chain.append(euler_phi(chain[-1]))
    return chain


def validate_fixed_rows(rows: dict[int, int], expected: int) -> None:
    """Rejeita qualquer oráculo que não coincida com os resíduos calculados."""
    for height in (13, 14):
        actual = rows[height]
        if actual != expected:
            raise AssertionError(
                f"altura {height}: calculado={actual:012d}, esperado={expected:012d}"
            )


def test_expected_digit_mutation_is_rejected(rows: dict[int, int]) -> int:
    """Muda exatamente um dígito do esperado e exige rejeição por asserção."""
    expected_text = f"{FIXED_RESIDUE:012d}"
    last_digit = int(expected_text[-1])
    mutated_last_digit = (last_digit + 1) % 10
    mutated_text = expected_text[:-1] + str(mutated_last_digit)
    mutated_expected = int(mutated_text)

    differences = sum(a != b for a, b in zip(expected_text, mutated_text))
    if differences != 1:
        raise RuntimeError("A mutação não alterou exatamente um dígito")

    try:
        validate_fixed_rows(rows, mutated_expected)
    except AssertionError:
        return mutated_expected
    raise RuntimeError(
        "MUTAÇÃO SOBREVIVEU: o validador aceitou um valor esperado adulterado"
    )


def main() -> None:
    assert gcd(BASE, MOD) == 1

    # Vetor base solicitado: V = 10.
    base_value = pow(BASE, V, MOD)
    assert base_value == 59_049

    # Cálculo correto da totiente e do período de expoentes.
    phi_mod = euler_phi(MOD)
    lambda_mod = carmichael_lambda(MOD)
    assert phi_mod == 400_000_000_000
    assert lambda_mod == 50_000_000_000
    assert MOD % lambda_mod == 0
    assert MOD // lambda_mod == 20

    rows = {height: tower_mod(height, MOD) for height in range(3, 15)}
    # O modo adversarial altera um único dígito do oráculo e deve terminar
    # com AssertionError/EXIT=1, demonstrando que a validação não o aceita.
    expected_under_test = FIXED_RESIDUE
    if "--mutate-expected" in sys.argv:
        expected_under_test += 1
    validate_fixed_rows(rows, expected_under_test)

    # No modo normal, o teste de controle injeta a mesma mutação e confirma
    # que o validador a rejeita; mutação sobrevivente vira falha explícita.
    mutated_expected = test_expected_digit_mutation_is_rejected(rows)

    # Ponto fixo da exponenciação modular.
    fixed_image = pow(BASE, FIXED_RESIDUE, MOD)
    assert fixed_image == FIXED_RESIDUE

    # Elo da prova: T_13 e o resíduo fixo coincidem também módulo lambda(MOD).
    t13_mod_lambda = tower_mod(13, lambda_mod)
    assert t13_mod_lambda == FIXED_RESIDUE % lambda_mod
    assert pow(BASE, t13_mod_lambda, MOD) == FIXED_RESIDUE

    # Sensibilidade mínima: alterar V de 10 para 11 altera o resultado base.
    mutated_base_value = pow(BASE, V + 1, MOD)
    assert mutated_base_value != base_value

    print(f"MOD={MOD}")
    print(f"V={V}")
    print(f"3^{V} mod MOD = {base_value:012d}")
    print(f"phi(MOD) = {phi_mod}")
    print(f"lambda(MOD) = {lambda_mod}")
    print(f"MOD / lambda(MOD) = {MOD // lambda_mod}")
    print(f"T_13 mod lambda(MOD) = {t13_mod_lambda}")
    print(f"Teste de sensibilidade V->V+1: {mutated_base_value:012d} != {base_value:012d}")
    print(f"Teste de mutação do esperado: REJEITADO ({FIXED_RESIDUE:012d} -> {mutated_expected:012d})")
    print("\nCadeia de totientes:")
    print(" -> ".join(str(x) for x in totient_chain(MOD)))
    print("\nAltura | T_h mod 10^12")
    print("-------|---------------")
    for height, residue in rows.items():
        print(f"{height:>6} | {residue:012d}")

    print("\nVerificações finais:")
    print(f"3^{FIXED_RESIDUE} mod MOD = {fixed_image:012d}")
    print(f"T_13 mod MOD = {rows[13]:012d}")
    print(f"T_14 mod MOD = {rows[14]:012d}")
    print("Indução: lambda(MOD) divide MOD; logo T_h mod MOD = R implica "
          "T_h mod lambda(MOD) = R mod lambda(MOD), e então "
          "T_(h+1) mod MOD = 3^R mod MOD = R.")
    print("STATUS=PASS")


if __name__ == "__main__":
    main()