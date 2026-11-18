# Mapa operacional do TPL

> Documento de navegação e fotografia do estado em **30/10/2026**. Não é cânone, não cria estados, não substitui evidências e não promove nenhum artefato. Para qualquer divergência, prevalecem as fontes primárias abaixo.

## 1. Onde está a fonte de verdade

| Fonte | Função | Como usar |
|---|---|---|
| [`TPL_CANONE.md`](TPL_CANONE.md) | Regras, sintaxe e critérios do TPL | Ler antes de interpretar ou alterar o método |
| [`tpl_estado.json`](tpl_estado.json) | Registro de artefatos, hashes, estados e evidências | Conferir o objeto exato; não inferir estados por conversa |
| [GitHub Actions](https://github.com/Eduardo77117711/-TPL-/actions) | Registros das execuções | Conferir commit, workflow, jobs, ambiente e resultado |
| [Pull requests](https://github.com/Eduardo77117711/-TPL-/pulls) | Propostas de alteração | Uma proposta aberta não altera `main` |
| [`README.md`](README.md) | Apresentação pública e propósito | Visão geral; não substitui o cânone nem o registro de estado |

Este mapa apenas aponta para essas fontes. Ele não é uma terceira fonte canônica.

## 2. Estado do repositório

- Repositório: [Eduardo77117711/-TPL-](https://github.com/Eduardo77117711/-TPL-)
- Branch padrão: `main`
- Commit de `main` nesta fotografia: [`b6eaabc64ad74e21770fb9e0d198808aa8ee9fb2`](https://github.com/Eduardo77117711/-TPL-/commit/b6eaabc64ad74e21770fb9e0d198808aa8ee9fb2)
- Última mensagem desse commit: `Add functions to calculate and print fractions (#15)`.
- As alterações do PR #16 ainda não estão em `main`.

## 3. Propostas abertas

### PR #16 — malha v0.4 e malha de 32 nós

[Ver PR #16](https://github.com/Eduardo77117711/-TPL-/pull/16)

- Estado: aberto, não integrado.
- Branch: `malha-v0-4-e-malha32`.
- Commit examinado nesta fotografia: [`8ad5d8bee49428ba0ba48e5309a8aba684cba820`](https://github.com/Eduardo77117711/-TPL-/commit/8ad5d8bee49428ba0ba48e5309a8aba684cba820).
- Workflow `verificar`, execução #76: 17/17 jobs retornados com sucesso.
- Workflow `malha32`, execução #18: 33/33 jobs com sucesso — 32 nós da matriz e o job `juiz32`.
- Os passos da malha identificam autotestes do `tpl_arbitro_v3_2.py` (47/47) e do `tpl_malha_v0_4.py` (22/22).
- O próprio PR declara o grau como **AUTOMEDIÇÃO**: a execução distribuída ocorreu na mesma infraestrutura; não declarar REPRODUZIDO ou INDEPENDENTE por causa desses checks.

Resultado estritamente delimitado: os dois workflows desse commit terminaram com sucesso, nos escopos e ambientes descritos por eles. Isso não equivale à integração do PR, à conclusão da auditoria P-01–P-10 ou à validação integral do TPL.

### PR #13 — auditoria de purificação

[Ver PR #13](https://github.com/Eduardo77117711/-TPL-/pull/13)

- Estado: aberto, em rascunho.
- Base da auditoria declarada: commit `7fbb325`.
- Conteúdo: dez achados identificados como P-01 a P-10 e critérios propostos de aceitação.
- Natureza: auditoria estática/documental; o próprio PR exige converter achados aplicáveis em casos de teste e executá-los.
- O PR #16 declara corrigir P-01 e P-02, mas isso não fecha automaticamente esses achados. A correspondência entre achado, correção, regressão e critério de encerramento ainda precisa ser revisada.

### PR #14 — limite probatório dos checks verdes (R7)

[Ver PR #14](https://github.com/Eduardo77117711/-TPL-/pull/14)

- Estado: aberto, em rascunho.
- Propõe explicitar que um check verde vale apenas para o commit, ambiente e escopo efetivamente executados.
- Propõe critérios explícitos de encerramento e evidência reproduzível.
- Não está integrado ao cânone de `main`.

## 4. Organização dos arquivos de `main`

| Grupo | Arquivos/diretórios | Papel geral |
|---|---|---|
| Cânone e estado | `TPL_CANONE.md`, `tpl_estado.json` | Regras e registro dos estados/hashes |
| Execução e arbitragem | `tpl_arbitro_v3.py`, `tpl_cadeia.py`, `tpl_malha_v0_3.py` | Componentes de execução e avaliação |
| Sintaxe e verificações | `tpl_sintaxe.py`, `bateria3.py`, `tpl_curto.py` | Conferências e testes |
| Comunicação e lacunas | `tpl_fala.py`, `tpl_lacunas.py` | Componentes auxiliares |
| Modelo Phi-Omega | `tpl_phi_omega_portal.py`, `tpl_phi_omega_mapa_v2.py` | Portal e representação do modelo |
| Acervo | `acervo/` | Índice e conferência da base pública |
| CI | `.github/workflows/` | Execuções automatizadas |

Os nomes e agrupamentos acima servem para navegação. Não atribuem estado de validação a arquivos.

## 5. O que não deve ser confundido

1. `main` é o estado integrado; branch de PR é proposta até o merge.
2. Workflow verde prova somente o resultado do escopo realmente executado.
3. Teste do próprio projeto/infraestrutura não se transforma automaticamente em reprodução independente.
4. Correção alegada não fecha achado sem critério, regressão e evidência correspondentes.
5. Branch antiga não é trabalho ativo só por continuar aparecendo no GitHub.

## 6. Próxima ordem de trabalho sugerida

1. Revisar PR #16 no escopo do código e da evidência, sem fazer merge automático.
2. Confrontar cada achado P-01–P-10 do PR #13 com correção, teste de regressão e critério de encerramento.
3. Revisar o texto R7 do PR #14 e integrá-lo somente pelos checks exigidos pelo cânone.
4. Atualizar este mapa apenas quando a fonte primária mudar; preservar a data da fotografia.

**Regra de manutenção:** ao atualizar, registrar o commit/PR/workflow exato e o escopo observado. Não escrever “100%”, “independente”, “reproduzido” ou “concluído” sem a evidência exigida pelo TPL.
