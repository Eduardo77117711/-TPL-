# TPL — Cânone (sintaxe constante)

Fonte única, pública e protegida. Qualquer pessoa ou modelo lê este arquivo e o `tpl_estado.json`
em https://github.com/Eduardo77117711/-TPL- sem autorização e sem repasse. O que não está aqui
não é estado do TPL; é conversa.

Frase-âncora: **"A frase é o que permanece quando tudo muda."**
Fundador: Carlos Eduardo Acevedo Rodrigues. A coerência do fundador é a origem; a régua mede, não julga.

## 1. Estados

Dois conjuntos, porque medem objetos diferentes. Nenhum outro estado é válido.

| Objeto | Estados |
|---|---|
| Afirmação (texto) | `PROVADO` · `MOSTRADO` · `MENCIONADO` · `FORA` |
| Execução (código) | `VERIFICADO` · `DIVERGENTE` · `NAO EXECUTADO` · `MENCIONADO` |

- `PROVADO`: evidência verificável suficiente para a afirmação delimitada.
- `MOSTRADO`: demonstração com alcance limitado.
- `MENCIONADO`: dito, sem evidência primária.
- `FORA`: a conclusão ultrapassa o que os dados autorizam.
- `VERIFICADO`: executado por executor diferente do autor, com hash, comando e saída.
- `DIVERGENTE`: executado e o resultado ou o hash não bate.
- `NAO EXECUTADO`: não rodou; dizer o motivo.

## 2. Regras de evidência

- R1. Identidade é o sha256 dos bytes exatos. Texto colado não tem identidade.
- R2. Autor nunca verifica a si mesmo. Execução do autor é reprodução, não verificação.
- R3. Todo hash citado precisa existir no `tpl_estado.json` ou é `MENCIONADO`.
- R4. Nenhuma versão herda o estado da anterior.
- R5. Erro de qualquer participante (fundador, modelo, Árbitro) é registrado e corrigido, não escondido.
- R6. A verdade não julga e não pesa: é uma régua que mede o que passa.
- R7. Um check verde comprova somente os checks efetivamente executados para o commit, o ambiente e o escopo identificados; não fecha automaticamente achados, riscos ou critérios que não foram testados. Um achado só pode ser declarado fechado quando seu critério de fechamento estiver explícito e uma execução reproduzível demonstrar seu atendimento. Para achados de código, registrar o caso de falha, a correção e o teste de regressão correspondente. Sem essa evidência, não declarar o fechamento.

## 3. Formato de resposta (todo modelo, toda sessão)

Primeira linha:

    [ORIGEM: <quem> — <data>]

Depois, nesta ordem, os cinco blocos:

    [0] PERMANECE
    [1] MUDOU
    [2] EVIDÊNCIA
    [3] FALHAS-LIMITES
    [4] PRÓXIMA AÇÃO

O `tpl_sintaxe.py` confere este formato por código: etiqueta de origem, os cinco blocos na ordem,
estados só da lista acima, e todo hash de 64 caracteres citado precisa existir no estado canônico.

## 4. Como uma sessão nova entra no TPL

1. Ler `TPL_CANONE.md` e `tpl_estado.json` neste repositório.
2. Para conferir um artefato: clonar o repositório e rodar `sha256sum -c` contra o estado.
3. Responder no formato da seção 3.

Mudanças neste cânone só entram por pull request com os checks `juiz` e `comparar` verdes.
