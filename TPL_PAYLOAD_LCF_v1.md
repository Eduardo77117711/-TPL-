# TPL-PAYLOAD-v1 e TPL-LCF-v1 — protótipo executável

**Estado desta entrega:** protótipo local com testes automatizados. Não é uma fronteira de segurança de produção.

## 1. Separação de autoridade

- A IA/propositora pode criar somente uma proposta MENCIONADO sem assinatura.
- O LCF é o único componente autorizado a assinar recibos de execução.
- O verificador confere assinatura Ed25519, identidade da chave, manifesto, bytes de cada artefato e raiz Merkle.
- Este v1 promove somente MENCIONADO -> MOSTRADO, para a política registrada stdout-exact-v1.
- PROVADO e FORA não são emitidos pelo LCF v1. PROVADO exige um contrato próprio de verificador de demonstração; não é inferido de stdout nem de consenso entre modelos.

## 2. Contrato do Payload

Campos exatos: claim_id, evidence_root, execution_id, parent_root, provenance, schema, signature, state.

provenance possui exatamente executor, key_id, producer, validator.

A assinatura é ed25519:<base64url-sem-padding> sobre a serialização canônica do objeto com signature: null. key_id identifica a chave pública confiável pelo SHA-256 integral da chave pública raw (64 caracteres hexadecimais).

## 3. Serialização TPL-CJ/1

Perfil compatível com o formato compacto desejado, mas explicitamente não declarado como implementação completa da RFC 8785:

- UTF-8 estrito;
- strings e chaves normalizadas para Unicode NFC;
- chaves ordenadas lexicograficamente;
- separadores , e : sem espaços;
- floats proibidos; inteiros limitados ao intervalo seguro interoperável de 53 bits;
- chaves duplicadas e colisões após NFC rejeitadas.

A NFC adicional e a proibição de floats diferenciam este perfil do JCS/RFC 8785 puro. Assinaturas e hashes usam os bytes emitidos por canonical_json_bytes.

## 4. Raiz Merkle e cadeia

Cada descritor de artefato (nome, SHA-256, tamanho) e os metadados de execução viram folhas com prefixo de domínio 0x00. Nós internos usam 0x01. Para quantidade ímpar de nós, o último é duplicado. A raiz cobre a política, a afirmação textual vinculada ao claim_id, dados de execução e descritores dos artefatos.

Os bytes brutos permanecem em artifacts/; manifest.json registra os descritores. A verificação recalcula o hash de cada arquivo e a raiz. parent_root encadeia o Payload anterior, mas a prevenção de truncamento/reescrita da cadeia exige âncora guardada fora do mesmo armazenamento.

## 5. Regra de promoção neste protótipo

A política stdout-exact-v1 precisa vir de um registro confiável do LCF, inacessível ao processo proponente. Para o protótipo de demonstração, a condição é: compilação com código zero, execução com código zero e SHA-256 do stdout igual ao hash esperado registrado na política.

Isso prova somente a afirmação operacional estreita codificada na política. Não demonstra que um texto natural arbitrário é semanticamente verdadeiro. A relação entre claim_text e o verificador precisa ser revisada/registrada por uma autoridade fora da IA propositora.

## 6. Fronteira de segurança necessária em produção

O demo compila e executa uma fixture C fixa e inofensiva. A função genérica evaluate_c_source exige allow_unsafe_local_execution=True; essa opção é um aviso explícito, não uma sandbox. subprocess, diretório temporário, timeout e processo separado não impedem acesso ao mesmo usuário, rede, filesystem, kernel ou recursos do host.

Perfil de implantação requerido antes de aceitar código não confiável:

1. LCF sob UID/conta de serviço distinta da IA; diretório e chave privada Ed25519 acessíveis somente ao LCF (permissão mínima 0600, diretório 0700).
2. A IA não recebe shell, acesso ao arquivo de chave, ao processo do LCF, ao socket administrativo nem ao diretório de política confiável.
3. Política de claims é carregada pelo LCF de armazenamento somente leitura protegido; o proponente envia claim_id, nunca escolhe o verificador ou o hash esperado.
4. Compilação e execução em sandbox descartável do sistema operacional/OCI: sem rede, sem capabilities, sem privilégios, filesystem somente leitura mais diretório de saída limitado, limites de CPU/memória/PIDs e timeout; sem montar socket do runtime ou segredos do host.
5. Chave privada permanece fora do container de execução de código; somente o daemon LCF assina após verificar o bundle.
6. A cabeça da cadeia/Merkle é publicada em um segundo domínio de confiança (ex.: mídia offline ou serviço independente). Sem âncora externa, reescrita total da cadeia não é detectável.

## 7. Dependência e execução local

~~~bash
python -m pip install -r requirements-tpl-lcf.txt
python -I test_tpl_payload_lcf_v1.py
python -I tpl_lcf_v1.py demo --evidence-dir ./tpl_evidence
~~~

O teste demo usa uma fixture incorporada e imprime a chave pública efêmera para permitir verificação independente dessa execução. Não passe código de terceiros a evaluate_c_source sem uma sandbox real.

## 8. Escopo ainda não implementado

- daemon IPC/HTTP com autenticação mútua e controle de acesso;
- isolamento OCI/seccomp/AppArmor/SELinux e gestão de recursos;
- política de claims assinada e registro confiável persistente;
- verificador formal para PROVADO;
- captura/identificação das bibliotecas dinâmicas e imagem completa do ambiente de execução;
- rotação/revogação de chaves e timestamp confiável;
- Índice Lardner (diagnóstico estatístico; sem autoridade para alterar estados).

O que permanece quando tudo muda.
