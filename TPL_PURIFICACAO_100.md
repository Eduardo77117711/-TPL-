# TPL — Auditoria de purificação e critérios de 100%

**Documento de trabalho em revisão.** Não altera o cânone, não muda estados em `tpl_estado.json` e não promove qualquer artefato.  
**Base examinada:** `7fbb325f60e4c3a011a6c942a231b0b4c6567c84` — branch `main`, 30/10/2026.  
**Objetivo:** converter “100%” em um resultado fechado, mensurável e auditável para um escopo explícito.

## 1. O que 100% pode significar — e o que não pode

O TPL pode alcançar **100% dos critérios de aceitação previamente declarados** em uma campanha delimitada. Isso significa: todos os testes obrigatórios executados; todos os resultados esperados conferidos; nenhuma divergência sem explicação; nenhum mutante obrigatório escapando; todas as origens e dependências necessárias verificáveis; e nenhuma falha crítica/alta conhecida ainda aberta no escopo.

Isso **não** significa segurança absoluta, ausência de toda vulnerabilidade possível, independência absoluta de infraestrutura, nem prova de que qualquer código futuro será correto. Toda declaração de 100% deve citar versão, ambiente, entradas, critérios, conjunto de mutantes, resultados e limites.

A promoção de uma execução continua obedecendo ao cânone: `VERIFICADO`, `DIVERGENTE`, `NAO EXECUTADO` ou `MENCIONADO`. Para afirmações, permanecem `PROVADO`, `MOSTRADO`, `MENCIONADO` e `FORA`. `AUTOMEDICAO` e `INDEPENDENTE` continuam graus internos de `tpl_malha`, não estados epistemológicos.

## 2. Linha de base efetivamente observada

Na execução GitHub Actions **#49**, run `41050825707`, associada ao commit-base:

- 16 jobs de matriz concluíram com sucesso;
- 16 artefatos de resumo foram produzidos;
- o job `juiz` baixou os 16 artefatos, confirmou a contagem e comparou cada resumo com `malha_3.12_x64_ubuntu-24.04.txt`;
- o comando `diff` não encontrou divergências.

**Alcance:** execução e igualdade dos 16 resumos naquela matriz. Isso não autentica os autores/executores declarados, não prova independência da infraestrutura e não demonstra que cada resultado numérico esteja correto.

Evidência: [execução #49](https://github.com/Eduardo77117711/-TPL-/actions/runs/41050825707) · [workflow da matriz](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/verificar.yml) · [workflow multiplataforma curto](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/tpl.yml).

## 3. Brechas e limites encontrados na leitura estática

As observações abaixo são **MOSTRADAS pelo código consultado**; não devem ser apresentadas como exploração executada, salvo quando houver uma execução de teste específica anexada.

### P-01 — Proveniência externa declarada, mas não autenticada

Arquivo: [`tpl_malha_v0_3.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/tpl_malha_v0_3.py), especialmente `medir` (linha 46) e `_extrato` (linha 105).

`medir` decide que há grau `INDEPENDENTE` quando encontra uma string `origem` diferente da string do autor, desde que o hash e o selo textual coincidam. A função não autentica quem controla aquela origem, não verifica uma assinatura e não prova que as duas origens tenham operadores, credenciais ou infraestrutura separados. O próprio `--extrato` recebe a origem como texto na forma `origem=arquivo`.

**Risco:** uma origem inventada pode ser contabilizada como externa. Isso impede interpretar `INDEPENDENTE` como identidade autenticada.

**Fechamento necessário:** substituir a declaração livre por uma atestação verificável e vinculada ao artefato, commit, execução e identidade da origem. Verificar assinatura/chave e política de confiança. Documentar que uma assinatura autentica a posse da chave, não prova por si só independência organizacional ou física.

### P-02 — Parser aceita a primeira ocorrência e ignora contradições posteriores

Arquivo: [`tpl_malha_v0_3.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/tpl_malha_v0_3.py), `de_saida` (linha 67).

O parser usa `re.search` para obter a primeira linha de hash e a primeira linha de resultado. Não exige exatamente uma ocorrência de cada campo e não rejeita uma segunda linha contraditória.

**Caso adversarial derivado diretamente da implementação:**

```text
HASH tpl_coerencia_v1_4.py <PIN_CORRETO> OK
RESULTADO: REPRODUZIDO
RESULTADO: DIVERGENTE
```

A lógica atual encontra primeiro `REPRODUZIDO` e não examina a contradição seguinte. O caso deve ser transformado em teste de regressão executável; até lá, é uma falha mostrada na leitura do parser, não um resultado de campanha.

**Fechamento necessário:** gramática estrita; exatamente uma ocorrência de cada campo obrigatório; rejeitar duplicatas, contradições, campos desconhecidos e conteúdo malformado; vincular o resultado ao identificador da execução e ao hash do artefato. A ausência de qualquer prova deve bloquear, nunca ser convertida em confirmação.

### P-03 — Identidade no árbitro também é autodeclarada

Arquivo: [`tpl_arbitro_v3.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/tpl_arbitro_v3.py), `decidir` (linha 348), `arbitrar` (linha 522).

Os campos `autor` e `executor` são fornecidos ao comando. `mesmo_agente` compara rótulos normalizados, não credenciais ou identidades verificadas. A própria documentação do arquivo declara que registra autor e executor declarados, mas não prova identidade.

**Risco:** nomes diferentes não provam pessoas ou agentes diferentes.

**Fechamento necessário:** identidade do executor com atestação verificável, chave sob controle separado e política explícita para conflitos de autoria. Sem prova de identidade, o resultado deve permanecer limitado a reprodução/menção, nunca ser elevado por diferença de rótulo.

### P-04 — Diretório temporário e ambiente mínimo não constituem sandbox de segurança

Arquivo: [`tpl_arbitro_v3.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/tpl_arbitro_v3.py), `ambiente_minimo` (linha 275) e `executar` (linha 304).

O alvo é copiado para um diretório temporário e executado em subprocesso com ambiente reduzido e timeout. Isso é isolamento de diretório/ambiente, não uma fronteira de segurança do sistema operacional: o processo ainda roda com o UID e permissões do runner e o código não impõe bloqueio de rede, limites de memória/processos ou política de acesso ao sistema de arquivos.

**Risco:** código não confiável pode tentar ler arquivos acessíveis ao usuário do runner, acessar rede ou consumir recursos. O timeout do subprocesso não equivale a contenção completa de processos descendentes.

**Fechamento necessário:** não executar código adversarial no runner normal. Usar worker efêmero descartável, usuário sem privilégios, sistema de arquivos mínimo e somente leitura quando possível, rede desativada por padrão, limites de CPU/memória/processos, timeout com encerramento do grupo inteiro, ausência de segredos e descarte do ambiente após cada execução. Testar essas restrições com provas adversariais.

### P-05 — Dependências e ações mutáveis comprometem reprodutibilidade

Arquivos: [`verificar.yml`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/verificar.yml) e [`tpl.yml`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/tpl.yml).

O workflow `verificar` instala `numpy scipy` sem versões e hashes fixados. As ações são referenciadas por tags (`checkout@v5`, `setup-python@v6`, `upload-artifact@v4)); o workflow `tpl.yml` usa tags ainda anteriores (`checkout@v4`, `setup-python@v5`). Os rótulos `ubuntu-22.04` e `ubuntu-24.04` também identificam imagens hospedadas que recebem atualizações. A execução não registra no resumo uma impressão digital completa das bibliotecas numéricas e bibliotecas matemáticas nativas.

**Fechamento necessário:** lockfile completo com hashes para dependências diretas e transitivas; ações fixadas em SHA completo verificado; versões explícitas; registrar versão exata do Python, NumPy, SciPy, BLAS/LAPACK, arquitetura e imagem do runner. Tornar explícita a permissão mínima do `GITHUB_TOKEN` em cada workflow.

Referência de segurança do próprio GitHub: [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use). O GitHub recomenda fixar ações por SHA completo e aplicar privilégio mínimo.

### P-06 — Comparação de consenso sem oráculo independente para todos os resultados

Arquivo: [`verificar.yml`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/verificar.yml), etapa do juiz (linha 125).

O juiz compara os resumos entre si usando como referência o resumo de um dos próprios 16 nós. Isso detecta divergência entre nós, mas um erro comum reproduzido por todos pode continuar igual e passar. O workflow já contém alguns valores de referência fixados para cálculos específicos, o que é bom; a cobertura não equivale a um oráculo independente para todas as saídas relevantes.

**Fechamento necessário:** vetor de referência previamente congelado, com entradas e respostas esperadas derivadas por método independente ou cálculo exato auditável. O teste deve comparar cada nó contra esse oráculo, além da comparação entre nós. Não gerar o valor esperado a partir do próprio nó testado.

### P-07 — Estabilidade bit a bit de `float64` ainda não faz parte da medição da malha

Arquivo: [`NucleoTPLPMVA_CORRIGIDO_v4.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/NucleoTPLPMVA_CORRIGIDO_v4.py), funções `kl_divergence` e `wasserstein_1`; [workflow](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/.github/workflows/verificar.yml).

O núcleo calcula com `float64` e os autotestes verificam relações numéricas com tolerância. A etapa do núcleo não acrescenta ao resumo os bits de cada resultado numérico. Portanto, a igualdade dos 16 resumos não demonstra igualdade bit a bit dessas saídas.

**Fechamento necessário:** congelar entradas; serializar cada resultado IEEE-754 de modo não ambíguo (por exemplo, bytes de `struct.pack('>d', valor)` e hexadecimal); registrar metadados do ambiente; comparar exatamente os bits; separar qualquer tolerância numérica em um critério distinto, escrito antes da execução. Uma divergência não pode ser escondida por arredondamento.

### P-08 — Manifesto do acervo e resumo retornado não coincidem em `bytes_comprimido`

Arquivo: [`acervo/acervo_tpl.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/acervo/acervo_tpl.py), função `montar` (linhas 35–92).

O arquivo `manifesto.json` é escrito e o pacote TAR é criado antes de `bytes_comprimido` ser acrescentado ao objeto `manifesto` em memória. Assim, o valor aparece no resumo retornado pela função, mas não no manifesto já gravado nem no manifesto incluído no TAR.

**Fechamento necessário:** definir explicitamente esse campo como metadado externo do processo de empacotamento (não parte do manifesto interno que afeta o tamanho do próprio pacote), ou reorganizar o formato para não haver divergência entre retorno, manifesto persistido e pacote. Adicionar teste que compare os três resultados.

### P-09 — Integridade interna do acervo não substitui âncora externa

Arquivo: [`acervo/acervo_tpl.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/acervo/acervo_tpl.py), função `conferir` (linha 96).

A conferência compara os objetos com os hashes presentes no manifesto. Isso detecta corrupção de um objeto isolado, mas se o manifesto e os objetos forem substituídos juntos por uma nova coleção internamente consistente, a função não dispõe, por si só, de uma âncora externa para reconhecer a substituição.

**Fechamento necessário:** fixar o hash do manifesto fora do próprio acervo e verificar uma assinatura/âncora independente antes de aceitar a coleção. Preservar cópia externa e histórico de mudanças.

### P-10 — Validador de sintaxe não é autenticador de evidência

Arquivo: [`tpl_sintaxe.py`](https://github.com/Eduardo77117711/-TPL-/blob/7fbb325/tpl_sintaxe.py), `conferir_estado` (linha 24) e `conferir_resposta` (linha 47).

O validador verifica estados permitidos, presença de executor e hashes locais. A presença de um campo `executor` não prova identidade independente. A análise de resposta é textual/regex; não valida a verdade do conteúdo nem a autenticidade de uma origem. Além disso, o esquema de entrada não é validado integralmente antes de acessar os campos.

**Fechamento necessário:** validar um esquema estrito e versionado, rejeitar campos/estruturas inválidos com erro explícito e sem exceção não tratada, e manter a autenticação de origem fora da mera validação sintática.

## 4. Condições de aceitação para declarar 100% no escopo

Nenhum item abaixo pode ser substituído por concordância verbal.

1. **Escopo congelado:** commit-base, arquivos, entradas, versões, arquitetura e ameaça coberta estão identificados.
2. **Oráculo:** cada saída numérica crítica tem resultado esperado independente, ou cálculo exato reproduzível.
3. **Proveniência:** origem, executor, commit, execução e artefato são vinculados por evidência verificável; rótulos digitados não bastam.
4. **Parser fail-closed:** duplicatas, contradições, saída incompleta, saída forjada, hash incorreto e estrutura malformada são rejeitados.
5. **Execução segura:** código não confiável roda em ambiente descartável, sem segredos, sem rede por padrão e com limites de recursos demonstrados.
6. **Reprodutibilidade:** ações e dependências fixadas; impressão digital ambiental registrada.
7. **Bits:** resultados exatos preservam a representação exata; resultados `float64` têm seus 64 bits registrados e comparados. Diferenças ficam visíveis.
8. **Matriz:** 16/16 nós passam contra o oráculo e contra os critérios de consistência; repetir a campanha sem mudança deve reproduzir o resultado.
9. **Mutantes pré-registrados:** incluir pelo menos mutantes de origem falsificada, saída contraditória, hash trocado, peça removida, peça intrusa, saída truncada, juiz com referência manipulada, dependência alterada, artefato velho e manifesto/objeto reescritos em conjunto. O denominador é congelado antes do teste. Para a bateria obrigatória, o resultado exigido é zero mutantes não equivalentes escapando; mutantes equivalentes precisam de justificativa revisável.
10. **Governança:** checks obrigatórios `juiz` e `comparar` verdes, revisão independente registrada e nenhuma alteração silenciosa de arquivo selado.
11. **Limites:** nenhuma falha crítica/alta conhecida sem correção ou bloqueio. Riscos residuais e dependências comuns ficam escritos no certificado.

O resultado só pode ser declarado como **100% dos critérios desta campanha**, com commit e evidência anexados. Não se deve converter esse resultado em “100% seguro” ou “impossível falhar”.

## 5. Ordem de fechamento

**Primeiro:** P-01 e P-02 (proveniência e parser). Sem isso, o grau de independência pode ser atribuído por rótulo ou saída ambígua.

**Segundo:** P-03 e P-04 (identidade do executor e contenção de execução). Sem isso, não existe base para executar código adversarial com segurança nem para certificar independência por nome.

**Terceiro:** P-05 e P-06 (cadeia de suprimentos e oráculo). Sem isso, o resultado pode depender de dependências mutáveis ou de um erro comum a todos os nós.

**Quarto:** P-07 (medição dos bits), P-08 e P-09 (acervo e âncora), P-10 (esquema do validador).

**Quinto:** executar a bateria de mutantes congelada, repetir a matriz e emitir relatório final com os resultados reais. O documento de plano não é prova de execução.

## 6. Preservação

Esta auditoria não modifica `TPL_CANONE.md`, `tpl_estado.json`, pins, scripts selados ou workflow na branch principal. Correções devem entrar em mudanças isoladas, com testes que primeiro reproduzam cada falha e depois demonstrem a correção. O histórico e a evidência anteriores devem permanecer acessíveis.

**Regra final:** nenhuma promoção de estado para satisfazer a meta de 100%. Se uma condição não foi executada, ela permanece `NAO EXECUTADO`; se divergir, permanece `DIVERGENTE`; se só foi examinada no código, a afirmação fica limitada ao que foi `MOSTRADO`.
