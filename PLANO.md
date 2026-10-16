# Plano de execução — Hackathon Barte AI · Case Tarvo (fechamento set/2026)

## STATUS: 16/10, 20h25 (adiantado em relação ao cronograma)
- **Pronto e publicado** em https://github.com/lecotz3/tarvo-fechamento-insper-ai: Mínimo + Alvo + boa parte do Extra.
  - As 7 saídas, o rastro e o validador estão prontos.
  - 11 testes passam, incluindo a simulação de outubro.
  - Há uma conciliação Meridiano × Ponte e um resumo de 1 página.
  - A IA está implementada para o resíduo do extrato, desligada por padrão.
- **O que falta é principalmente humano:**
  - mandar as perguntas e trazer as respostas para `config/`;
  - pitch;
  - MOMENTOS.md;
  - exportar os transcripts no fim (`python PROMPTS/exportar_transcripts.py`);
  - checkpoints.
- **Divisão para amanhã (3 pessoas):**
  - **P1, cliente:** Slack, `HIPOTESES.md` (registro com horário) e ajuste de `config/premissas.toml` / `de_para_ec.csv` a cada resposta. Rodar `fechar` e `pytest` depois de cada mudança.
  - **P2, auditoria:** conferir à mão, contra os arquivos originais, 3 lojistas (sugestão: Rota Global, Mundo Aberto e Atlas), a NF da Ponte e 10 lançamentos. Cada erro encontrado vira teste. Ficar de olho no #hackathon-avisos e rodar o pipeline se chegarem dados novos.
  - **P3, pitch:** montar a apresentação a partir de `saida/resumo_fechamento.md` e da seção 9 deste plano. Escrever os checkpoints e revisar MOMENTOS.md.
- **Regra de ouro:** nenhuma mudança de número sem uma resposta do financeiro ou um teste que justifique.

> Montado em 16/10 às ~20h, depois de ler o enunciado e **todos os 6 arquivos do data pack** (cópia intacta em `data/set2026/`).
> Os números marcados como *preliminar* saíram de scripts exploratórios e precisam ser revalidados pelo pipeline final.

---

## 0. Resumo em 5 linhas

1. O peso maior da nota está em **números certos (25%)** e **uso de IA dirigido (20%)**. Juntos, causa raiz, hipóteses e perguntas valem mais 35%. Então o código importa menos do que **entender, perguntar e rastrear**.
2. Os dados têm armadilhas de propósito: cadastro EC↔CNPJ incompleto, taxas com vigência, lojista sem contrato, operação duplicada, spread negativo, CNPJs em 4 formatos. **Quem casar nomes "no olho" vai gerar alarme falso, e alarme falso tira ponto.**
3. Estratégia: **motor determinístico (REGRA)** para todos os números. Tudo o que não fecha vira **pendência com dono**. A IA só entra onde há texto livre (classificar extrato residual e redigir o motivo das pendências), sempre com `confianca`.
4. Ordem: **Mínimo (comissão checkout + rastro) ainda hoje à noite** → Alvo até ~15h30 de amanhã → Extra só depois de validar tudo.
5. **20h30 em ponto:** mandar o 1º lote de perguntas ao financeiro (já está pronto em `HIPOTESES.md`). Até 22h30 é a janela de hoje.

---

## 1. Causa raiz: por que o fechamento é lento *e* erra

"Automatizar as 8 planilhas" não resolve. Os dados mostram quatro causas estruturais:

| # | Causa raiz | Evidência no data pack |
|---|---|---|
| 1 | **Não existe cadastro único de lojista.** Cada sistema identifica o lojista de um jeito: EC na Orbe, CNPJ na Ponte e na planilha, nome livre nos bancos. | 3 lojistas sem EC na planilha (Horizonte Viagens, Kiwi "EC pendente", Novo Horizonte). A Orbe usa até 3 grafias por EC ("Mundo Aberto", "MUNDO ABERTO INTERCAMBIO", "MUNDO ABERTO INTERC LTDA"). Existem dois "Horizonte" diferentes. CNPJ aparece com máscara, sem máscara e como número sem o zero à esquerda (`3229837000103`, `8780784000120`). |
| 2 | **A tabela de taxas é a "fonte da verdade", mas é mantida à mão, sem vigência estruturada e com regras não escritas.** | Bridge tem 2 linhas com vigências diferentes. Taxas vêm como número (`0.0149`) e como texto (`"1,49%"`). Aparecem "padrão" e "spread em branco = padrão" sem valor definido. Um comentário diz "condição especial, ver c/ Diego". A aba "ANTIGO 2025 - nao usar" fica visível. Atlas Idiomas tem 57 transações em setembro e **não está na tabela vigente**. |
| 3 | **Ninguém confere a taxa aplicada pelos parceiros contra a contratada.** O erro só aparece quando o lojista reclama. | A Orbe aplica **+0,5 p.p. na Rota Global desde 12/09** (taxas da tabela 2025): 87 transações, ~R$ 1.546 *preliminar*. A Bridge segue com 2,59% depois da renegociação de 15/09. A Ponte aplica **1,5% na Mundo Aberto, cujo contrato é 1,2%**: ~R$ 1.419 em 23 operações *preliminar*. |
| 4 | **O relatório do parceiro é aceito como vem.** | A Ponte manda a operação PC-0926-0162 **duplicada** ("reprocessada"), e o total do rodapé (R$ 78.073,59) já inclui a duplicata. Há **4 spreads negativos** ("taxa travada D-1", −R$ 1.834,05). |

Conclusão para o pitch: o problema central é a falta de três coisas: **cadastro, contrato versionado e conferência automática**. Volume é consequência. O "agente que fecha o mês" sem isso só erra mais rápido.

---

## 2. Mapa dos dados e armadilhas (o que o código precisa tratar)

| Arquivo | Formato real | Armadilhas encontradas |
|---|---|---|
| `01_orbe_...csv` | `;`, vírgula decimal, datas dd/mm/aaaa, 1.943 linhas | 4 tipos: VENDA 1.840, ESTORNO 59 (**9 de vendas de agosto**), ANTECIPACAO 38, REVERSAO ANTECIPACAO 6 (cada uma anula uma antecipação pelo `id_referencia`). Os nomes variam por EC. Conferi `valor_taxa = bruto × taxa` e `liquido = bruto − taxa` (0 erros). |
| `02_tabela_taxas...xlsx` | 2 abas, cabeçalho na linha 5, título mesclado | Vigência por linha (Bridge muda em 15/09). Taxas em float e em texto "x,xx%". CNPJ em 3 formatos. Linhas sem EC. "padrão" e brancos. Linha tachada (Globo Trotter, inativo, sem transações). Comentário de célula na Casa do Estudante. Faixas de parcela 2-6x / 7-12x. Oxford 2-6x = 3,09% e EduAbroad 7-12x = 3,49% (exceções, não são erro). |
| `03_email_ponte...eml` | MIME com xlsx em base64 | Precisa extrair o anexo por código (a regra é "consumir como vem"). Cabeçalho na linha 5 e rodapé com totais. 233 linhas, mas 232 operações únicas. 16 "APROVADO C/ RESSALVA" (o e-mail diz que liquidam normalmente). 6 contratadas em set e liquidadas em 01/10. O e-mail informa **participação de 50% do spread realizado, paga mediante NF**. |
| `04_plano_de_contas...csv` | ISO-8859-1 | Só contas `ACEITA_LANCTO=S` (analíticas) são válidas. |
| `05a_aurora...csv` | UTF-8, 7 linhas de cabeçalho, rodapé | `ref_origem = L<nº da linha física>`: o 1º lançamento é **L9**, o último L92. Ignorar SALDO ANTERIOR/FINAL. Os saldos conferem linha a linha. |
| `05b_meridiano...ofx` | OFX SGML 1.02, latin-1 (CHARSET 1252) | 100 transações, FITID único. Memos com e sem acento ("PONTE AÉREA" × "PONTE AEREA"). |

---

## 3. Estratégia e priorização

### Níveis (regra do enunciado: o mínimo certo vale mais que o extra errado)
| Nível | Entrega | Meta de horário |
|---|---|---|
| **Mínimo** | `comissoes_por_lojista.csv` (CHECKOUT) + `rastro.csv` + validação "soma do rastro = número" | **Hoje até ~23h30** |
| **Alvo** | + REMESSA, `divergencias_taxa.csv`, `notas_a_emitir.csv`, `lancamentos_classificados.csv` | Amanhã até ~14h |
| **Extra** | `pendencias.csv` completo e explicado, rastro de 100% dos números, roda em outubro só trocando a pasta | Amanhã até ~16h30 |

### Onde a IA atua e onde não atua (isso vira slide do pitch)
| Tarefa | Quem faz | Por quê |
|---|---|---|
| Cálculo de comissão, divergência e nota | **REGRA** (código determinístico) | Precisa ser auditável e reproduzível. IA não decide número. |
| Casamento EC↔CNPJ | **REGRA + HUMANO** (de-para confirmado pelo financeiro em `config/`) | O enunciado alerta contra o casamento aproximado de nomes. |
| Classificação do extrato | **REGRA** (regex → conta) para os padrões conhecidos. **IA** só no resíduo, com `confianca`. Abaixo de 0,8 vira **HUMANO** (pendência) | Os memos são texto livre e mudam. A regra cobre ~95%. |
| Redação do motivo das pendências e resumo para a analista | **IA** (rascunho) revisada | Texto, não número. |
| Regra de negócio desconhecida | **HUMANO** (pergunta ao financeiro) | "A resposta estava a uma pergunta de distância." |

---

## 4. Arquitetura da solução

Stack: **Python 3.12 + pandas + openpyxl** (já instalados na máquina). Uma CLI, sem banco, sem front.
O pitch não avalia ferramenta. Uma CLI simples e verificável é o que mais protege a nota de números.

```
HACKATOn/                      ← vira o repositório público
├── README.md                  instalar e rodar do zero, limitações
├── HIPOTESES.md               fatos × premissas × perguntas/respostas (com horário)
├── PROMPTS/                   transcripts Claude Code (.jsonl exportado) + MOMENTOS.md
├── data/set2026/              data pack INTACTO (não limpar nada à mão)
├── config/
│   ├── lojistas.csv           de-para EC ↔ CNPJ ↔ nome canônico + fonte da confirmação
│   ├── regras_contas.csv      regex do histórico → conta_codigo, por banco
│   └── premissas.yaml         spread padrão, % participação Ponte, tratamento de estorno…
├── src/tarvo/
│   ├── loaders/               orbe.py · taxas.py · ponte_eml.py · plano.py · aurora.py · meridiano_ofx.py
│   │                          (cada loader devolve DataFrame com arquivo_origem + ref_origem)
│   ├── checkout.py            taxa contratada por transação (vigência + faixa) → comissão, divergência
│   ├── remessa.py             dedup, spread contratado × aplicado, participação
│   ├── notas.py               NF por tomador e linha de negócio
│   ├── lancamentos.py         classificação dos 2 extratos (REGRA → IA → HUMANO)
│   ├── pendencias.py          exceções com motivo + quem_decide
│   ├── rastro.py              liga cada id_saida às linhas de origem
│   └── validar.py             soma(rastro)=número, CNPJ 14 dígitos, formato CSV, contas analíticas
├── saida/                     7 CSVs no formato fixo
└── tests/                     números-âncora (ex.: 87 divergências Rota, 232 ops únicas)
```

Comando único: `python -m tarvo.fechar --competencia 2026-09 --dados data/set2026 --saida saida/`
**Outubro:** só muda a pasta e a competência. Taxas, vigências e lojistas são lidos da planilha e do `config/`. Nada fica fixo no código.

### Princípios que protegem a nota
- **Todo DataFrame carrega `arquivo_origem` e `ref_origem` desde o loader.** O rastro nasce junto com o dado, não é reconstruído no fim.
- **`validar.py` roda ao fim de cada execução e falha alto** se algum total não fechar com o rastro. É isso que impede "número inventado".
- Arredondamento: calcular com `Decimal` por linha, arredondar a 2 casas por linha e só depois somar, para o total bater com o rastro.
- Lojista ou transação sem regra **não some e não vira zero**: vai para `pendencias.csv`.

---

## 5. Regras de cálculo propostas (default até o financeiro responder)

Cada uma vira uma premissa em `HIPOTESES.md`. Se o financeiro responder diferente, muda o `config/` e roda de novo.

**Comissão CHECKOUT por lojista** = Σ por transação de `valor_bruto × taxa_contratada`, somando VENDA, ESTORNO (negativo), ANTECIPACAO e REVERSAO (negativa).
- Taxa contratada = linha da planilha pelo EC (ou pelo CNPJ do de-para), modalidade, faixa de parcelas e **vigência na data da venda**. Para estorno, vale a data da venda original.
- *Alternativa a perguntar:* comissão = `valor_taxa` aplicado pela Orbe. Isso muda o total da Rota Global e da Bridge.
- **Divergência** = `valor_bruto × (aplicada − contratada)`, só quando ≠ 0 e a taxa contratada é conhecida. Atlas e qualquer lojista sem contrato vão para **pendência**, não para divergência, para não gerar alarme falso.

**Comissão REMESSA por lojista** = 50% × Spread R$ por operação única (dedup por Nº Operação).
- Spread negativo: **premissa** = entra como pendência (Financeiro/Ponte decidem) e fica fora da comissão até a decisão. *Perguntar.*
- **Divergência REMESSA** = Spread R$ − (Valor ME × PTAX × spread contratado). Hoje só a Mundo Aberto (1,5% aplicado × 1,2% contratado) *preliminar*.

**Notas a emitir**
- CHECKOUT: 1 NF por lojista com comissão > 0. Tomador = o lojista (CNPJ normalizado).
- REMESSA: **1 NF para a Ponte Câmbio S.A. (CNPJ 75374179000146)**, pela participação total. O e-mail diz "repasse … mediante recebimento da nota fiscal de intermediação". *Confirmar.* Se a NF de remessa for feita contra os lojistas, a nota zera nesse arquivo.

**Lançamentos classificados**: 84 (Aurora) + 100 (Meridiano) = 184 linhas. Primeiro mapa (regra):

| Padrão do histórico | Conta |
|---|---|
| TED RECEBIDA … ORBE ADQUIRENCIA | 1.1.03.001 Recebíveis Orbe |
| PIX ENVIADO <lojista> (Aurora) | 2.1.01.001 Repasses a lojistas |
| TRANSF ENTRE CONTAS / MESMA TITULARIDADE | 1.1.09.001 Transf. entre contas próprias |
| PIX RECEB <lojista> (Meridiano) · TED ENVIADA PONTE … LIQ OPERACOES | 2.1.02.001 Recursos p/ remessas |
| TED RECEB PONTE … REPASSE COMISSAO 08/2026 | 1.1.03.002 Comissões câmbio a receber |
| APLICACAO / RESGATE AUTOMATICO CDB | 1.1.02.001 · RENDIMENTO → 3.2.01 |
| TAR / TARIFA | 4.2.01 · SEGURO → 4.2.05 · IOF → 4.3.01 |
| AWS → 4.2.03 · GOOGLE WORKSPACE → 4.2.04 · CONDOMINIO → 4.2.02 · CONTABILIDADE → 4.2.06 | |
| FOLHA / INSS / FGTS / DARF 0561 / ISS / DARF 8109 (PIS) / DARF 2172 (COFINS) | baixa do passivo 2.1.04.x / 2.1.03.x (*perguntar: baixa de passivo ou despesa?*) |
| PIX RECEBIDO … SEM IDENTIFICACAO (L50, R$ 7.350) | 1.1.09.002 + **pendência** |
| DEVOLUCAO PIX - MUNDO ABERTO (L65, R$ 12.400) | **pendência** (2.1.01.001 ou 2.1.01.002?) |

**Pendências** (quem decide): Atlas sem contrato (Financeiro/Comercial) · de-para EC↔CNPJ não confirmado (Financeiro) · Casa do Estudante "condição especial" (Comercial, Diego) · spreads negativos e operação duplicada (Financeiro + Ponte) · PIX não identificado e devolução (Financeiro) · divergências a devolver/cobrar da Orbe e da Ponte (Financeiro).

---

## 6. Cronograma hora a hora

### Hoje, 16/10
| Horário | O quê |
|---|---|
| 20h00–20h30 | Criar repo GitHub público + estrutura. Exportar este transcript para `PROMPTS/`. Revisar o 1º lote de perguntas. |
| **20h30** | **Postar o lote 1 no #tarvo-financeiro**, começando com o nome do time, em 2–3 mensagens por tema. |
| 20h30–21h30 | Loaders dos 6 arquivos (incluindo extração do .eml) + teste de leitura com contagens-âncora (1.943 / 233 / 84 / 100). |
| 21h30–22h30 | `checkout.py` + `rastro.py` + `validar.py` → **Nível Mínimo**. Registrar cada resposta do financeiro em `HIPOTESES.md` com horário. Fazer perguntas de follow-up **antes das 22h30**. |
| 22h30–23h30 | Divergências de checkout + primeiro commit. **Dormir.** O credenciamento às 8h conta pontualidade por pessoa. |

### Amanhã, 17/10
| Horário | O quê |
|---|---|
| 8h00 | Chegar (pontualidade conta). |
| 9h30 | Lote 2 de perguntas (o financeiro volta às 9h30). |
| 9h30–11h | `remessa.py` + `notas.py`. |
| **até 11h** | **Checkpoint 1** no thread: o que atacamos, principais hipóteses, o que fica de fora (ver texto pronto em §9). |
| 11h–13h30 | `lancamentos.py` (regras) + `pendencias.py`. |
| 13h30–15h | Rastro 100% + testes. Rodar `validar.py` e conferir os totais à mão em 3 lojistas. |
| **até 15h30** | **Checkpoint 2**: o que funciona, o que mudou. |
| 15h30–17h | IA no resíduo do extrato (opcional) + README + MOMENTOS.md + rascunho do pitch. Atenção ao **#hackathon-avisos (novos dados podem chegar)**: o pipeline deve rodar de novo em 1 comando. |
| 17h–17h30 | Últimas perguntas (o financeiro sai às 17h30). |
| **17h45** | **Congelar o código.** Rodada final, validar formato e push. |
| 18h00–18h25 | Folga para imprevisto. **Último commit antes de 18h30** (commits depois não contam). |
| 18h30–19h | Finalizar o pitch (PDF/slides). **Link até 19h.** |

---

## 7. Divisão de trabalho (se o time tiver 2–3 pessoas)

| Pessoa | Frente |
|---|---|
| A (dados/código) | loaders + checkout + remessa + validar |
| B (negócio) | perguntas ao financeiro, `HIPOTESES.md`, de-para de lojistas, classificação do extrato, pendências |
| C (comunicação) | checkpoints, MOMENTOS.md, pitch, conferência manual dos números |

Solo: seguir o cronograma na ordem. B e C acontecem nos intervalos de espera das respostas.

---

## 8. Uso de IA (20% da nota): como deixar isso visível

- **Transcripts:** os do Claude Code ficam em `C:\Users\Leonardo\.claude\projects\C--Users-Leonardo-HACKATOn\*.jsonl`. Copiar **sem editar** (só remover chaves) para `PROMPTS/`. Esta sessão de preparação também conta.
- **Mostrar direção:** pedir para a IA *explorar e listar anomalias*, depois *verificar* cada uma com uma contagem. Nunca aceitar uma regra que ela "deduziu" sem perguntar ao financeiro.
- **MOMENTOS.md (2–4)**, incluindo pelo menos um em que a IA errou. Candidatos reais a observar ao longo do trabalho:
  - casamento "HORIZONTE INTERCAMBIO": uma IA tende a ligar à Horizonte Viagens pelo nome. A taxa aplicada (2,39%/2,89%) é a da **Novo Horizonte**. Ligar errado gera divergências negativas falsas.
  - total do rodapé da Ponte aceito sem dedup;
  - bugs de parsing (vírgula decimal, CNPJ sem zero à esquerda).
  Registrar **na hora** o que aconteceu de verdade, sem inventar.

---

## 9. Textos prontos

**Checkpoint 1 (até 11h), rascunho:**
> Vamos atacar: comissão por lojista (checkout e remessa) com rastro até a transação, divergências contratada × aplicada, NFs e classificação dos extratos. Tudo por regra determinística. A IA entra só no resíduo do extrato e na redação das pendências.
> Hipóteses principais: (1) a comissão usa a taxa contratada na data da venda; (2) remessa = 50% do spread realizado, deduplicado, com NF única contra a Ponte; (3) lojista sem contrato (Atlas) e spread negativo viram pendência, não divergência.
> Fora do escopo: conciliação completa repasse × extrato por lojista e interface gráfica.

**Pitch (para o CFO, 15 min):**
1. O que está quebrado: 4 causas raiz (§1), com casos reais da Rota Global, da Mundo Aberto e da duplicata da Ponte.
2. O que a solução faz, em 1 frase: "Lê os 6 arquivos como chegam, calcula comissão e nota de cada lojista, aponta onde o parceiro cobrou errado e entrega uma lista curta do que precisa de uma pessoa."
3. **Dinheiro em jogo** (*preliminar*): ~R$ 1,6 mil de taxa a mais no checkout (Rota + Bridge), ~R$ 1,4 mil de spread a mais na Mundo Aberto, ~R$ 0,8 mil de spread duplicado, −R$ 1,8 mil de spread negativo para decidir, R$ 7,9 mil de taxas da Atlas sem contrato, ~R$ 38,6 mil de participação da Ponte que **só é paga com NF**.
4. Como a analista usa em outubro: soltar os arquivos na pasta, rodar 1 comando, revisar `pendencias.csv`.
5. Onde a IA atua e onde não atua (tabela §3).
6. Onde falha: arquivo com layout novo, lojista novo sem de-para, regra comercial não registrada. Nesses casos vira pendência, nunca número.
7. Próximo mês de desenvolvimento: cadastro único de lojistas, tabela de taxas versionada (sai do Excel), conferência diária em vez de mensal, integração direta com Orbe/Ponte.

---

## 10. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Financeiro não responde a tempo | Toda pergunta tem uma premissa default escrita. Parâmetros no `config/` permitem rodar de novo em 1 min. |
| Novos dados chegam durante o dia | Loaders tolerantes (cabeçalho localizado por nome de coluna, não por posição). Testes com contagens-âncora. |
| Total não fecha com o rastro | `validar.py` bloqueia a saída. Arredondar por linha antes de somar. |
| Alarme falso | Só reportar divergência quando a taxa contratada é conhecida e o de-para foi confirmado. O resto vai para pendência. |
| Gastar a tarde no extra | Congelar o código às 17h45. O mínimo fica pronto hoje à noite. |
| Commit fora do horário | Push incremental a cada marco, e não só no fim. |

## 11. Sugestões extras (se sobrar tempo)
- `saida/resumo_fechamento.md`: 1 página em português para a analista, com totais por linha, top divergências e pendências por responsável. Ajuda muito no pitch.
- Teste de regressão "outubro simulado": rodar com o data pack de setembro renomeado para provar que nada está fixo no código.
- Conciliação Orbe → Aurora (TEDs recebidas × líquido por dia) e Meridiano → Ponte (TED LIQ × Valor R$+IOF por data de liquidação), como extra de credibilidade.
