# HIPÓTESES, premissas e perguntas ao financeiro

> Convenção: **[FATO]** foi verificado nos arquivos (com referência). **[PREMISSA]** é o que assumimos até ter resposta (com o impacto se estiver errado). **[RESPOSTA]** veio do financeiro, com horário e canal.
> Atualizar este arquivo **na hora** em que cada resposta chegar.

## 1. Fatos verificados nos arquivos

- [FATO] A Orbe tem 1.943 linhas: VENDA 1.840, ESTORNO 59, ANTECIPACAO 38, REVERSAO ANTECIPACAO 6. 22 ECs distintos. Para todas as linhas, `valor_taxa = valor_bruto × taxa_aplicada` **truncado nos centavos (em direção a zero)** e `valor_liquido = bruto − taxa`. O truncamento reproduz as 1.943 linhas; o arredondamento comum erra 1.001 linhas por R$ 0,01. Por isso a comissão pela taxa contratada usa o mesmo truncamento: sem isso surgiriam ~900 divergências falsas de 1 centavo.
- [FATO] 9 estornos de setembro se referem a vendas de agosto (fora do arquivo). Ex.: TX88444848 (Oxford, venda 22/08).
- [FATO] Cada REVERSAO ANTECIPACAO aponta para uma ANTECIPACAO do mesmo valor pelo `id_referencia`. Ex.: AN88445093 → AN88445076 (Kiwi).
- [FATO] Rota Global (EC 1074504011): de 01 a 11/09 a Orbe aplicou a taxa da planilha. **A partir de 12/09 aplicou +0,5 p.p.** (2,99% crédito à vista, 3,49% 2-6x, 4,09% 7-12x), que é a taxa da aba "ANTIGO 2025". São 87 linhas.
- [FATO] Bridge (EC 1075624862): o crédito à vista mudou de 2,59% para 2,19% a partir de 15/09. A partir dessa data, 9 vendas saíram a 2,19% e 5 ainda a 2,59%.
- [FATO] Atlas Idiomas (EC 1076801732) tem 57 linhas em setembro (R$ 7.876,05 de taxa aplicada). Não está na aba "Taxas vigentes", só na aba "ANTIGO 2025 - nao usar". As taxas aplicadas a ela são as mais altas do arquivo (3,49%, 3,99%, 4,49%).
- [FATO] Não têm EC na planilha: Horizonte Viagens, Kiwi ("EC pendente") e Novo Horizonte. A Orbe tem os ECs 1043396662 "HORIZONTE VIAGENS TURISMO", 1043300981 "HORIZONTE INTERCAMBIO" e 1038867654 "KIWI EXPERIENCE TURISMO". As taxas aplicadas ao EC 1043300981 (2,39% / 2,89%) batem com as da Novo Horizonte, não com as da Horizonte Viagens. O extrato Aurora tem PIX separados para "HORIZONTE VIAGENS E TURISM" e "NOVO HORIZONTE INTERCAMBIO".
- [FATO] Ponte: 233 linhas, 232 operações únicas. PC-0926-0162 aparece 2x (a 2ª com obs. "reprocessada"). O rodapé "Spread total R$ 78.073,59" inclui a duplicata; sem ela, R$ 77.251,71.
- [FATO] Ponte: 4 operações com spread negativo, todas com obs. "Taxa travada no pedido (D-1)", somando −R$ 1.834,05. O "Spread Estimado D-1" delas soma +R$ 1.622,90.
- [FATO] Ponte: o spread % aplicado bate com a planilha para todos os lojistas, **exceto Mundo Aberto**: 1,50% aplicado × 1,2% na planilha ("negociado em jul/26"), em 23 operações.
- [FATO] O e-mail da Ponte diz: "repasse da participação de 50% do spread realizado … creditado em 06/10/2026, mediante recebimento da nota fiscal de intermediação". Também diz que "APROVADO C/ RESSALVA" segue normalmente para liquidação.
- [FATO] CNPJs aparecem com máscara, sem máscara e como número sem o zero à esquerda (Fluente `3229837000103`, Campus `8780784000120`). Normalizar com zfill(14).
- [FATO] Os saldos do extrato Aurora conferem linha a linha (saldo final −R$ 1.920.088,60). O OFX Meridiano tem 100 transações com FITID único.

## 2. Premissas (default até resposta)

| # | Premissa | Impacto se estiver errada |
|---|---|---|
| H1 | A comissão de checkout usa a **taxa contratada** (planilha) na data da venda. A diferença para a aplicada é divergência a devolver ao lojista. | Muda a comissão da Rota Global e da Bridge, e as NFs delas. |
| H2 | Estorno abate a comissão do mês em que ocorre (inclusive de venda de agosto), pela taxa da venda original. | Muda a comissão de 9 lojistas. |
| H3 | Antecipação entra na comissão de checkout. Reversão anula a antecipação referenciada. | Muda o checkout de quem antecipou. |
| H4 | Comissão de remessa = 50% do Spread R$ por operação única. | Linha REMESSA inteira. |
| H5 | NF de remessa: única, contra a Ponte Câmbio (75374179000146). NF de checkout: uma por lojista. | `notas_a_emitir.csv` inteiro. |
| H6 | "Spread padrão" = 1,5% (é o que a Ponte aplicou a todos os lojistas com campo em branco ou "padrão"). | Divergências de remessa. |
| H7 | Spread negativo fica fora da comissão e vira pendência (Financeiro + Ponte decidem). | −R$ 917 na participação. |
| H8 | Operação duplicada conta uma vez. A duplicata vira pendência para contestar com a Ponte. | R$ 410,94 de participação. |
| H9 | O EC 1043300981 é a Novo Horizonte, o EC 1043396662 é a Horizonte Viagens e o EC 1038867654 é a Kiwi. **Até a confirmação, marcar como pendência de cadastro.** | Comissão e NF de 3 lojistas. |
| H10 | Atlas: sem taxa contratada, não calcular divergência. A comissão usa a taxa aplicada, marcada como pendência. | Alarme falso ou comissão faltando. |
| H11 | Operações contratadas em setembro e liquidadas em 01/10 entram em setembro (competência do relatório). | 6 operações. |
| H12 | Pagamentos de folha e tributos de competência anterior dão baixa no passivo (2.1.03.x / 2.1.04.x). | Classificação de ~9 lançamentos. |

## 3. Perguntas ao financeiro: prontas para colar

> Começar toda mensagem com o nome do time. Mandar em blocos por tema, os mais importantes primeiro. Pergunta específica, com exemplo de ID, recebe resposta específica.

### Lote 1: hoje, 20h30 (o que mais mexe nos números)

**Mensagem 1: comissão de checkout**
```
[Insper AI] Três dúvidas sobre a comissão de checkout:
1) Quando a taxa aplicada pela Orbe difere da contratada na planilha, a comissão (e a NF) do lojista deve usar a contratada, e a diferença é devolvida ao lojista? Ex.: Rota Global, crédito à vista. Desde 12/09 a Orbe aplica 2,99%, e a planilha diz 2,49%.
2) Estorno abate a comissão do mês em que ocorreu, mesmo quando a venda é de agosto? Ex.: TX88444848 (Oxford, venda de 22/08, estornada em 01/09). Vale a taxa da venda original?
3) A taxa de antecipação (2,10%) faz parte da comissão de checkout, na mesma NF do MDR? E uma REVERSAO ANTECIPACAO anula integralmente a antecipação que ela referencia (ex.: AN88445093 reverte AN88445076, Kiwi)?
```

**Mensagem 2: cadastro de lojistas**
```
[Insper AI] Cadastro EC × CNPJ. A planilha não tem EC para três lojistas. Podem confirmar?
a) EC 1043300981 "HORIZONTE INTERCAMBIO" = Novo Horizonte Intercâmbio (66.564.512/0001-99)?
b) EC 1043396662 "HORIZONTE VIAGENS TURISMO" = Horizonte Viagens (78.576.234/0001-79)?
c) EC 1038867654 "KIWI EXPERIENCE TURISMO" = Kiwi Experience (07.752.116/0001-26)?
d) Atlas Idiomas (EC 1076801732) tem 57 lançamentos em setembro, mas só aparece na aba "ANTIGO 2025 - nao usar". É lojista ativo? Qual o CNPJ e a taxa contratada?
```

**Mensagem 3: remessas / Ponte**
```
[Insper AI] Sobre remessas:
1) A comissão de remessa de cada lojista é 50% do "Spread R$" das operações dele, como diz o e-mail da Ponte? A NF dessa receita é emitida contra a Ponte Câmbio (75.374.179/0001-46), uma NF com o total, e não contra os lojistas?
2) Qual é o spread "padrão" (campo em branco e "padrão" na planilha: Kiwi, Ponte Aérea, Canguru…)?
3) Há 4 operações com spread negativo ("Taxa travada no pedido D-1", ex.: PC-0926-0210, −R$ 687,52). A Tarvo aceita e abate da comissão, ou contesta? Quem decide?
4) PC-0926-0162 veio duas vezes (a 2ª como "reprocessada"). Contamos uma vez só?
5) Mundo Aberto: a planilha diz spread de 1,2% ("negociado em jul/26"), mas a Ponte cobrou 1,5% nas 23 operações de setembro. O 1,2% já valia em setembro? A diferença é divergência?
```

### Lote 2: amanhã, 9h30 (ou hoje, se sobrar tempo)
```
[Insper AI]
1) Casa do Estudante tem um comentário na planilha: "condição especial, conversar com Diego". Existe alguma condição diferente da planilha em vigor em setembro? Qual?
2) Bridge: a nova taxa de crédito à vista (2,19% a partir de 15/09) vale pela data da venda? Depois de 15/09, 5 vendas ainda saíram a 2,59%.
3) Rota Global teve alguma renegociação em 12/09? Desde essa data a Orbe aplica as taxas da tabela 2025.
4) Folha 08/2026, INSS, FGTS, ISS, PIS, COFINS e IRRF pagos em setembro: lançamos como baixa do passivo (2.1.03/2.1.04) ou direto como despesa?
5) Aurora: um PIX de R$ 7.350 de 38.686.002/0001-80 "SEM IDENTIFICACAO" (16/09). Conhecem esse CNPJ? E a "DEVOLUCAO PIX - MUNDO ABERTO" de R$ 12.400 (23/09), o que é?
6) Meridiano: o PIX de R$ 18.240,00 de "PONTE AEREA ESTUDANTIL" (17/09, FITID MRD2026090425) é aporte normal para remessa?
7) Remessas contratadas em setembro e liquidadas em 01/10 (6 operações) entram no fechamento de setembro? Operações "APROVADO C/ RESSALVA" geram comissão normalmente?
8) Lojista com comissão de checkout zerada ou negativa no mês (por estornos) recebe NF? Como fica?
```

## 4. Registro de perguntas e respostas

| Horário | Canal | Pergunta (resumo) | Resposta | Premissa afetada |
|---|---|---|---|---|
| | | | | |
