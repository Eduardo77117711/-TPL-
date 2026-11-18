# TPL — Núcleo de invariantes v1

Proposta de 03/11/2026. Autor: Claude (Árbitro 2), a partir dos cinco pilares escritos pelo fundador.
Estado: **MENCIONADO**. Só vale como norma depois de entrar na `main` com os checks `juiz` e `comparar` verdes e de outro executor rodar o `tpl_invariantes.py`.

> Não precisamos de um homem infalível. Precisamos de um método que encontre os próprios erros.

## Para que serve

Uma especificação pequena, que não depende de nenhum modelo nem de nenhuma pessoa, dizendo o que pode ser afirmado, como se verifica e como se preserva. Cada invariante abaixo é medido por código (`tpl_invariantes.py`, só biblioteca padrão). O que o código ainda não consegue medir aparece em **Limites**, não é escondido.

O núcleo não substitui o `TPL_CANONE.md`. Ele dá a régua para conferir se o registro (`tpl_estado.json`) obedece ao cânone.

## As cinco camadas

| Camada | O que entra | Pilar |
|---|---|---|
| Realidade | fenômenos, observações, dados | nenhuma hipótese ganha imunidade |
| Matemática | definições, equações, provas, limites | toda relação tem definição e demonstração |
| Código | implementação e experimento | — |
| Verificação independente | reprodução, divergência, auditoria | reprodutibilidade · independência |
| Conhecimento preservado | resultados, erros, proveniência, histórico | memória histórica |

## Invariantes

Três níveis de resultado: **VIOLAÇÃO** (reprova), **LACUNA** (é registrada e não reprova na v1) e **OK**.

| Id | Invariante | Pilar | Como o código mede |
|---|---|---|---|
| N1 | Toda entrada tem identidade: `repositorio`, `arquivo`, `sha256` (64 hex), `estado`, `executor`, `evidencia`. | Memória | campos e formato |
| N2 | Só existem os estados do cânone: `VERIFICADO`, `DIVERGENTE`, `NAO EXECUTADO`, `MENCIONADO`. | Matemática (definição fechada) | lista fechada |
| N3 | Para cada arquivo, vale a **última** entrada; as anteriores são histórico. Os bytes do arquivo têm de bater com a entrada atual. | Realidade | sha256 dos bytes |
| N4 | `VERIFICADO` exige executor. Se a entrada registra `autor`, o executor não pode ser o autor. Sem `autor`, a independência não pode ser demonstrada: é LACUNA. | Independência | campo `autor` × `executor` |
| N5 | `VERIFICADO` aponta um registro público reexaminável: id de execução, commit ou sha256. Sem isso, é LACUNA. | Reprodutibilidade | padrão na evidência |
| N6 | Divergência tem tratamento: `DIVERGENTE` e `NAO EXECUTADO` dizem o motivo. | Realidade | evidência não vazia |
| N7 | O registro só cresce. Nenhuma entrada é apagada nem reescrita no lugar. Promoção, rebaixamento e correção entram como entrada **nova** no fim. | Memória | compara o registro entre dois commits |
| N8 | Nenhum estado é imune. Um `VERIFICADO` pode receber depois uma entrada `DIVERGENTE`, e o núcleo aceita. | Realidade | caso no autoteste |
| N9 | O núcleo se mede. Cada invariante tem um caso que precisa passar e um erro que precisa pegar. Se o verificador deixar passar um erro plantado, ele mesmo reprova. | Independência | `autoteste` (17 casos) |

## Como rodar

```
python -I tpl_invariantes.py autoteste
python -I tpl_invariantes.py estado .
python -I tpl_invariantes.py historia . <commit_base> <commit_novo>
python -I tpl_invariantes.py auditoria .
```

A saída imprime o sha256 do próprio núcleo e do registro medido, então quem compara dois resultados sabe se mediu a mesma coisa.

## Primeira medição (autor, 03/11/2026, `main` = `1d98115`; reprodução, não verificação)

- `autoteste`: 17/17.
- `estado`: 0 violações, 79 lacunas. 57 lacunas N4: nenhuma entrada `VERIFICADO` registra o autor, então hoje a independência é afirmada e não demonstrável pelo registro. 22 lacunas N5: entradas `VERIFICADO` sem id de execução, commit ou hash na evidência.
- `auditoria`: **38 violações N7** em 4 commits da `main` (`1ef7b70`, `f7d2647`, `884e3b3`, `45d9209`). Nesses commits, entradas antigas foram reescritas no lugar: promoções de `NAO EXECUTADO` para `VERIFICADO`, troca de sha256 e um rebaixamento. O git guarda as versões anteriores, então nada se perdeu. Mas o próprio registro não guarda a história, ao contrário do que diz "o que existe não se muda". Fica registrado aqui como erro do processo, não de uma pessoa (R5). Daqui para frente, N7 vale para cada mudança.

## Conflito conhecido

O `tpl_sintaxe_v3.py` confere o hash de **todas** as entradas, não só da última. Com N7 (promoção como entrada nova), toda vez que um arquivo mudar de bytes, a entrada antiga vai reprovar no `tpl_sintaxe_v3`. A correção, se aprovada, entra como `tpl_sintaxe_v4.py` (arquivo novo), conferindo o hash só da entrada atual, como o `tpl_p0_v2.py` já faz.

## Limites (o que a v1 não mede)

- **Matemática:** a v1 não julga se uma demonstração está certa. Uma afirmação matemática só pode ser `PROVADO` quando houver um artefato registrado com a definição e a prova em forma conferível por máquina (script ou prova formal). Julgar essa prova fica para uma versão futura.
- **Realidade:** o código confere bytes e registros, não fenômenos. Os dados de observação entram como artefatos com sha256 e proveniência; o núcleo garante que nenhum deles fique imune a reexame, mas não garante que o dado em si seja verdadeiro.
- **Independência:** N4 só reprova quando o campo `autor` existe. Passar N4 de LACUNA a VIOLAÇÃO depende de as entradas novas registrarem o autor.
- O workflow `invariantes.yml` roda em toda mudança, mas não é check obrigatório. Torná-lo obrigatório é decisão do fundador (configuração do repositório).

## Mudanças neste núcleo

Este arquivo não se edita. Uma mudança entra como `TPL_NUCLEO_INVARIANTES_v2.md`, com o motivo, e o `tpl_invariantes` da versão nova roda o autoteste da versão anterior.
