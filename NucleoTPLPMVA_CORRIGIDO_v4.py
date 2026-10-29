#!/usr/bin/env python3
"""NucleoTPLPMVA — protótipo auditável para arbitragem independente.

Versão v4. Base: NucleoTPLPMVA_CORRIGIDO_v3.py (sha256 06be29ea...6da4), sem
alteração no código de produção. Acrescenta 4 autotestes: profundidade 11 com
d_max=10, adulteração de nó selado, janela temporal do ReplayGuard e execução
real do fuzz_fail_closed (com controle positivo).
AUTOR DA v4: Claude (Árbitro 2). Pela regra do TPL, o Árbitro 2 não pode
declarar esta versão VERIFICADA; exige execução por outro árbitro.

Dependências externas permitidas: NumPy e SciPy. Demais imports são biblioteca padrão.
Execução normal: python NucleoTPLPMVA.py --self-test
Execução de demonstração: python NucleoTPLPMVA.py --demo

Limites conhecidos:
- zero falsos negativos observados em fuzzing não prova zero universal;
- replay guard em memória não persiste entre reinícios nem coordena processos;
- hash-chain local detecta alterações internas, mas não substitui âncora externa;
- testes em profundidade finita não constituem prova por indução matemática.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import random
import secrets
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from types import MappingProxyType

import numpy as np
import scipy
from scipy.stats import wasserstein_distance

NAO_RECEBIDO = "NAO_RECEBIDO"
INSPECIONADO = "INSPECIONADO"
VERIFICADO = "VERIFICADO"
BLOQUEADO_COM_MOTIVO = "BLOQUEADO_COM_MOTIVO"
DIVERGENTE = "DIVERGENTE"
MENCIONADO = "MENCIONADO"


def canonical_json(value: Any) -> bytes:
    """JSON determinístico; rejeita NaN/Infinity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def freeze_json(value: Any) -> Any:
    """Converte recursivamente JSON em estruturas imutáveis para avaliação."""
    if isinstance(value, dict):
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_json(item) for item in value)
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalized_distribution(values: Sequence[float], name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name}: esperado vetor unidimensional não vazio")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0):
        raise ValueError(f"{name}: probabilidades devem ser finitas e não negativas")
    total = float(np.sum(arr))
    if not math.isfinite(total) or total <= 0:
        raise ValueError(f"{name}: soma deve ser positiva e finita")
    return arr / total


def laplace_smooth(values: Sequence[float], alpha: float = 1e-9) -> np.ndarray:
    """Smoothing aditivo de Laplace, seguido de normalização."""
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha deve ser finito e estritamente positivo")
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError("vetor vazio ou dimensão inválida")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0):
        raise ValueError("valores devem ser finitos e não negativos")
    smoothed = arr + alpha
    return smoothed / np.sum(smoothed)


def kl_divergence(intended: Sequence[float], observed: Sequence[float],
                  alpha: float = 1e-9) -> float:
    """Divergência KL(P || Q), em bits, para suportes categóricos idênticos."""
    if len(intended) != len(observed):
        raise ValueError("intenção e observação devem ter o mesmo suporte")
    p = laplace_smooth(intended, alpha)
    q = laplace_smooth(observed, alpha)
    value = float(np.sum(p * np.log2(p / q)))
    if not math.isfinite(value):
        raise ArithmeticError("divergência KL não finita")
    # Erros de arredondamento podem produzir um negativo minúsculo quando P≈Q.
    if value < 0 and abs(value) < 1e-12:
        value = 0.0
    if value < 0:
        raise ArithmeticError("resultado KL negativo além da tolerância numérica")
    return value


def wasserstein_1(intended: Sequence[float], observed: Sequence[float],
                  support_positions: Sequence[float]) -> float:
    """Distância Wasserstein-1 em suporte numérico unidimensional."""
    if not (len(intended) == len(observed) == len(support_positions)):
        raise ValueError("vetores devem ter comprimentos idênticos")
    p = normalized_distribution(intended, "intended")
    q = normalized_distribution(observed, "observed")
    x = np.asarray(support_positions, dtype=np.float64)
    if x.ndim != 1 or x.size == 0 or not np.all(np.isfinite(x)):
        raise ValueError("suporte deve ser um vetor finito não vazio")
    if np.any(np.diff(x) < 0):
        raise ValueError("support_positions deve estar em ordem crescente")
    result = float(wasserstein_distance(x, x, u_weights=p, v_weights=q))
    if not math.isfinite(result) or result < 0:
        raise ArithmeticError("distância Wasserstein inválida")
    return result


class HashChainJSONL:
    """Log JSONL com encadeamento SHA-256; não é âncora externa autenticada."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = None
        with self.path.open("rb") as stream:
            for line in stream:
                if line.strip():
                    last = line
        if last is None:
            return "0" * 64
        return str(json.loads(last)["event_hash"])

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {"timestamp_utc": utc_now_iso(),
                      "prev_hash": self._last_hash(), "event": dict(event)}
            record["event_hash"] = sha256_hex(canonical_json(record))
            with self.path.open("ab") as stream:
                stream.write(canonical_json(record) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            return record

    def verify(self) -> tuple[bool, str]:
        if not self.path.exists():
            return True, "log inexistente; nenhuma entrada a verificar"
        expected_prev = "0" * 64
        try:
            with self.path.open("rb") as stream:
                for number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    supplied = record.pop("event_hash")
                    if record.get("prev_hash") != expected_prev:
                        return False, f"prev_hash inválido na linha {number}"
                    actual = sha256_hex(canonical_json(record))
                    if not hmac.compare_digest(actual, supplied):
                        return False, f"event_hash inválido na linha {number}"
                    expected_prev = supplied
            return True, "cadeia íntegra no arquivo verificado"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return False, f"falha de verificação: {type(exc).__name__}"


@dataclass(frozen=True)
class Decision:
    state: str
    allowed: bool
    reasons: tuple[str, ...]
    request_id: str
    timestamp_utc: str


class FailClosedGate:
    """Exceção, falso ou resultado ambíguo de qualquer regra bloqueia a entrada."""
    def __init__(self, rules: Mapping[str, Callable[[Mapping[str, Any]], bool]],
                 log: HashChainJSONL):
        if not rules:
            raise ValueError("ao menos uma regra explícita é obrigatória")
        self.rules = dict(rules)
        self.log = log

    def evaluate(self, payload: Mapping[str, Any], request_id: str | None = None) -> Decision:
        rid = request_id or secrets.token_hex(12)
        reasons: list[str] = []

        # Validar a serialização antes das regras. NaN/Infinity e payloads não
        # serializáveis devem gerar decisão explícita de bloqueio, nunca escapar
        # como exceção antes do registro auditável.
        try:
            payload_bytes = canonical_json(dict(payload))
            payload_hash: str | None = sha256_hex(payload_bytes)
        except Exception as exc:
            payload_hash = None
            reasons.append(f"payload_invalido:{type(exc).__name__}")

        if payload_hash is not None:
            # As regras recebem uma cópia reconstruída dos bytes que foram
            # hasheados. Mappings e sequências são congelados recursivamente,
            # evitando que uma regra altere o objeto avaliado ou o hash auditado.
            try:
                payload_for_rules = freeze_json(json.loads(payload_bytes.decode("utf-8")))
            except Exception as exc:
                payload_for_rules = None
                reasons.append(f"payload_reconstrucao_falhou:{type(exc).__name__}")

            if payload_for_rules is not None:
                for name, rule in self.rules.items():
                    try:
                        # Apenas o booleano True exato é aceitação; truthy não basta.
                        if rule(payload_for_rules) is not True:
                            reasons.append(f"regra_reprovada:{name}")
                    except Exception as exc:
                        reasons.append(f"regra_excecao:{name}:{type(exc).__name__}")

        allowed = not reasons
        decision = Decision(VERIFICADO if allowed else BLOQUEADO_COM_MOTIVO,
                            allowed, tuple(reasons), rid, utc_now_iso())
        self.log.append({"type": "decision", "request_id": rid,
                         "allowed": allowed, "state": decision.state,
                         "reasons": list(decision.reasons),
                         "payload_sha256": payload_hash})
        return decision


class ReplayGuard:
    """Protótipo em memória: não é armazenamento distribuído nem persistente."""
    def __init__(self, tolerance_seconds: float = 300.0):
        if not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
            raise ValueError("tolerância inválida")
        self.tolerance_seconds = tolerance_seconds
        self._seen: set[str] = set()
        self._lock = threading.Lock()
        self._start = time.monotonic()

    def validate(self, event_epoch: float, reference_epoch: float,
                 nonce: str) -> tuple[bool, str]:
        if not isinstance(nonce, str) or len(nonce) < 16:
            return False, "nonce ausente ou curto"
        if not (math.isfinite(event_epoch) and math.isfinite(reference_epoch)):
            return False, "timestamp não finito"
        if abs(event_epoch - reference_epoch) > self.tolerance_seconds:
            return False, "evento fora da janela temporal"
        if time.monotonic() < self._start:
            return False, "relógio monotônico inconsistente"
        with self._lock:
            if nonce in self._seen:
                return False, "replay detectado: nonce repetido"
            self._seen.add(nonce)
        return True, "aceito"


def new_nonce() -> str:
    """Nonce aleatório com fonte criptográfica do sistema operacional."""
    return secrets.token_urlsafe(24)


@dataclass(frozen=True)
class Node:
    name: str
    payload: Mapping[str, Any]
    privilege_level: int
    children: tuple["Node", ...] = ()
    expected_sha256: str = ""


def node_digest(node: Node) -> str:
    material = {"name": node.name, "payload": dict(node.payload),
                "privilege_level": node.privilege_level,
                "children": [{"name": child.name,
                              "expected_sha256": child.expected_sha256}
                             for child in node.children]}
    return sha256_hex(canonical_json(material))


def seal_tree(node: Node) -> Node:
    """Retorna cópia da árvore com hashes calculados de baixo para cima."""
    sealed_children = tuple(seal_tree(child) for child in node.children)
    provisional = Node(node.name, dict(node.payload), node.privilege_level,
                       sealed_children, "")
    return Node(provisional.name, provisional.payload, provisional.privilege_level,
                provisional.children, node_digest(provisional))


def validate_hierarchy(root: Node, d_max: int = 10) -> tuple[bool, list[str]]:
    """Verifica hashes, limite de profundidade e não escalada de privilégio.

    Convenção explícita: número menor representa privilégio maior; logo, um filho
    não pode ter número menor que o pai. A profundidade da raiz é zero.
    """
    if d_max < 10:
        return False, ["D_max deve ser >= 10"]
    errors: list[str] = []

    def walk(node: Node, depth: int, parent_level: int | None) -> None:
        if depth > d_max:
            errors.append(f"profundidade excedida:{node.name}")
            return
        if not node.expected_sha256 or not hmac.compare_digest(
                node_digest(node), node.expected_sha256):
            errors.append(f"hash divergente:{node.name}")
        if parent_level is not None and node.privilege_level < parent_level:
            errors.append(f"escalada de privilégio:{node.name}")
        for child in node.children:
            walk(child, depth + 1, node.privilege_level)

    walk(root, 0, None)
    return not errors, errors


def fuzz_fail_closed(gate: FailClosedGate,
                     payload_generator: Callable[[], Mapping[str, Any]],
                     must_reject: Callable[[Mapping[str, Any]], bool],
                     iterations: int = 100) -> dict[str, Any]:
    """Fuzzing amostral; zero observado não significa zero universal."""
    if iterations <= 0:
        raise ValueError("iterations deve ser positivo")
    false_negatives = 0
    harness_errors = 0
    for i in range(iterations):
        try:
            payload = payload_generator()
            if bool(must_reject(payload)) and gate.evaluate(
                    payload, request_id=f"fuzz-{i}").allowed:
                false_negatives += 1
        except Exception:
            harness_errors += 1
    result = {"iterations": iterations,
              "false_negatives_observed": false_negatives,
              "harness_errors": harness_errors,
              "observed_zero_false_negatives": false_negatives == 0 and harness_errors == 0,
              "status": INSPECIONADO if false_negatives == 0 and harness_errors == 0 else DIVERGENTE,
              "claim_limit": "amostra finita; não prova taxa universal zero"}
    gate.log.append({"type": "fuzz_summary", **result})
    return result


class NucleoTPLPMVATests(unittest.TestCase):
    def test_kl_identity_near_zero(self):
        self.assertLess(abs(kl_divergence([0.5, 0.5], [0.5, 0.5])), 1e-12)

    def test_kl_detects_distribution_change(self):
        self.assertGreater(kl_divergence([0.9, 0.1], [0.1, 0.9]), 1.0)

    def test_wasserstein_known_distance(self):
        self.assertLess(abs(wasserstein_1([1, 0], [0, 1], [0, 2]) - 2.0), 1e-12)

    def test_wasserstein_rejects_unsorted_support(self):
        with self.assertRaises(ValueError):
            wasserstein_1([0.5, 0.5], [0.5, 0.5], [2, 1])

    def test_fail_closed_rejects_false_and_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = HashChainJSONL(Path(tmp) / "log.jsonl")
            gate = FailClosedGate({"deny": lambda _: False}, log)
            self.assertFalse(gate.evaluate({"x": 1}).allowed)
            gate2 = FailClosedGate({"boom": lambda _: 1 / 0}, log)
            self.assertFalse(gate2.evaluate({"x": 1}).allowed)
            self.assertTrue(log.verify()[0])

    def test_fail_closed_prevents_rule_payload_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.jsonl"
            log = HashChainJSONL(path)

            def mutating_rule(payload):
                payload["x"] = 999
                return True

            def accepts_only_mutated_value(payload):
                return payload.get("x") == 999

            original = {"x": 1}
            expected_hash = sha256_hex(canonical_json(original))
            gate = FailClosedGate({
                "mutator": mutating_rule,
                "check_mutated_value": accepts_only_mutated_value,
            }, log)
            decision = gate.evaluate(original, request_id="mutation-test")

            self.assertFalse(decision.allowed)
            self.assertEqual(decision.state, BLOQUEADO_COM_MOTIVO)
            self.assertIn("regra_excecao:mutator:TypeError", decision.reasons)
            self.assertIn("regra_reprovada:check_mutated_value", decision.reasons)
            self.assertEqual(original, {"x": 1})
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            event = records[0]["event"]
            self.assertFalse(event["allowed"])
            self.assertEqual(event["payload_sha256"], expected_hash)
            self.assertTrue(log.verify()[0])

    def test_fail_closed_records_nan_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.jsonl"
            log = HashChainJSONL(path)
            gate = FailClosedGate({"allow": lambda _: True}, log)
            decision = gate.evaluate({"x": float("nan")}, request_id="nan-test")
            self.assertFalse(decision.allowed)
            self.assertEqual(decision.state, BLOQUEADO_COM_MOTIVO)
            self.assertIn("payload_invalido:ValueError", decision.reasons)
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["event"]["request_id"], "nan-test")
            self.assertFalse(records[0]["event"]["allowed"])
            self.assertIsNone(records[0]["event"]["payload_sha256"])
            self.assertTrue(log.verify()[0])

    def test_replay_guard_rejects_nonce_reuse(self):
        guard = ReplayGuard()
        now = time.time()
        nonce = new_nonce()
        self.assertTrue(guard.validate(now, now, nonce)[0])
        self.assertFalse(guard.validate(now, now, nonce)[0])

    def test_hierarchy_depth_and_hash(self):
        node = Node("root", {}, 0)
        for i in range(1, 11):
            node = Node(f"n{i}", {}, 0, (node,))
        sealed = seal_tree(node)
        self.assertTrue(validate_hierarchy(sealed, d_max=10)[0])
        self.assertFalse(validate_hierarchy(sealed, d_max=9)[0])

    def test_hierarchy_detects_privilege_escalation(self):
        child = Node("child", {}, 0)
        root = Node("root", {}, 1, (child,))
        sealed = seal_tree(root)
        ok, errors = validate_hierarchy(sealed, d_max=10)
        self.assertFalse(ok)
        self.assertTrue(any("escalada de privilégio" in e for e in errors))

    def test_hierarchy_rejects_depth_11_with_dmax_10(self):
        # Raiz em profundidade 0; 11 envoltórios colocam o nó mais interno em 11.
        node = Node("folha", {}, 0)
        for i in range(1, 12):
            node = Node(f"n{i}", {}, 0, (node,))
        ok, errors = validate_hierarchy(seal_tree(node), d_max=10)
        self.assertFalse(ok)
        self.assertIn("profundidade excedida:folha", errors)
        self.assertFalse(any("D_max deve ser" in e for e in errors))

    def test_hierarchy_detects_sealed_node_tampering(self):
        sealed = seal_tree(Node("root", {"v": 1}, 1,
                                (Node("filho", {"segredo": "original"}, 1),)))
        self.assertTrue(validate_hierarchy(sealed, d_max=10)[0])
        filho = sealed.children[0]
        adulterado = Node(filho.name, {"segredo": "adulterado"},
                          filho.privilege_level, filho.children,
                          filho.expected_sha256)
        raiz = Node(sealed.name, dict(sealed.payload), sealed.privilege_level,
                    (adulterado,), sealed.expected_sha256)
        ok, errors = validate_hierarchy(raiz, d_max=10)
        self.assertFalse(ok)
        self.assertEqual(errors, ["hash divergente:filho"])

    def test_replay_guard_time_window(self):
        guard = ReplayGuard(tolerance_seconds=300.0)
        ref = 1_000_000.0
        # Fronteira: diferença exatamente igual à tolerância é aceita.
        self.assertEqual(guard.validate(ref - 300.0, ref, "a" * 32), (True, "aceito"))
        self.assertEqual(guard.validate(ref + 300.0, ref, "b" * 32), (True, "aceito"))
        # Fora da janela, nos dois sentidos.
        self.assertEqual(guard.validate(ref - 301.0, ref, "c" * 32),
                         (False, "evento fora da janela temporal"))
        self.assertEqual(guard.validate(ref + 301.0, ref, "d" * 32),
                         (False, "evento fora da janela temporal"))
        # Nonce rejeitado por janela não fica consumido.
        self.assertEqual(guard.validate(ref, ref, "c" * 32), (True, "aceito"))
        # Timestamp não finito.
        self.assertEqual(guard.validate(float("nan"), ref, "e" * 32),
                         (False, "timestamp não finito"))
        self.assertEqual(guard.validate(float("inf"), ref, "f" * 32),
                         (False, "timestamp não finito"))

    def test_fuzz_fail_closed_real_run(self):
        def make_generator(seed):
            rng = random.Random(seed)

            def gen():
                if rng.random() < 0.1:
                    return {"x": float("nan")}
                return {"x": rng.randint(-50, 50)}
            return gen

        def must_reject(p):
            x = p["x"]
            return (isinstance(x, float) and math.isnan(x)) or x < 0

        iterations = 300

        # Contagem esperada de payloads avaliados (os que devem ser rejeitados).
        gen_count = make_generator(20261028)
        expected_evaluated = sum(1 for _ in range(iterations) if must_reject(gen_count()))
        self.assertGreater(expected_evaluated, 0)

        with tempfile.TemporaryDirectory() as tmp:
            # Portão correto: só aceita x inteiro >= 0.
            path = Path(tmp) / "log.jsonl"
            log = HashChainJSONL(path)
            gate = FailClosedGate(
                {"x_nao_negativo": lambda p: isinstance(p["x"], int) and p["x"] >= 0}, log)
            result = fuzz_fail_closed(gate, make_generator(20261028), must_reject,
                                      iterations=iterations)
            self.assertEqual(result["iterations"], iterations)
            self.assertEqual(result["false_negatives_observed"], 0)
            self.assertEqual(result["harness_errors"], 0)
            self.assertEqual(result["status"], INSPECIONADO)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), expected_evaluated + 1)
            self.assertTrue(log.verify()[0])

            # Controle positivo: portão permissivo deve gerar falsos negativos
            # (só os inteiros negativos; NaN é bloqueado pela validação do payload).
            path2 = Path(tmp) / "log2.jsonl"
            bad_gate = FailClosedGate({"aceita_tudo": lambda p: True},
                                      HashChainJSONL(path2))
            gen_neg = make_generator(20261028)
            expected_fn = 0
            for _ in range(iterations):
                p = gen_neg()
                if isinstance(p["x"], int) and p["x"] < 0:
                    expected_fn += 1
            bad = fuzz_fail_closed(bad_gate, make_generator(20261028), must_reject,
                                   iterations=iterations)
            self.assertGreater(expected_fn, 0)
            self.assertEqual(bad["false_negatives_observed"], expected_fn)
            self.assertEqual(bad["status"], DIVERGENTE)

    def test_log_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.jsonl"
            log = HashChainJSONL(path)
            log.append({"type": "test", "value": 1})
            self.assertTrue(log.verify()[0])
            raw = path.read_text(encoding="utf-8").replace('"value":1', '"value":2')
            path.write_text(raw, encoding="utf-8")
            self.assertFalse(log.verify()[0])


def run_demo() -> None:
    print(f"Python: {sys.version.split()[0]}")
    print(f"NumPy: {np.__version__}")
    print(f"SciPy: {scipy.__version__}")
    print(f"D_KL_bits: {kl_divergence([0.7, 0.3], [0.6, 0.4], alpha=1e-6):.12f}")
    print(f"Wasserstein_1: {wasserstein_1([0.7, 0.3], [0.6, 0.4], [0.0, 1.0]):.12f}")
    print("ESTADO: INSPECIONADO — demonstração local; não homologado")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(NucleoTPLPMVATests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        print(f"AUTOTESTE: {'PASSOU' if result.wasSuccessful() else 'FALHOU'}")
        print("HOMOLOGACAO: NAO ATRIBUIDA AUTOMATICAMENTE")
        return 0 if result.wasSuccessful() else 1
    run_demo()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
