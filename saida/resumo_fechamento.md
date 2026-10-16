# Fechamento Tarvo: competência 09/2026

> Gerado automaticamente a partir dos arquivos do mês. Cada número abaixo tem rastro até a linha de origem em `rastro.csv`.

## Receita do mês (comissões)

| Linha de negócio | Comissão | Lojistas |
|---|---:|---:|
| Checkout | R$ 230.304,13 | 22 |
| Remessa | R$ 39.542,92 | 14 |
| **Total** | **R$ 269.847,05** | |

**Notas fiscais a emitir:** 23, somando R$ 269.847,05.

A NF de remessa (R$ 39.542,92) vai para **PONTE CAMBIO S.A.**: o repasse da participação só é pago depois que a Ponte recebe a nota.

## Dinheiro em jogo

| Item | Valor | O que fazer |
|---|---:|---|
| Taxa cobrada acima do contrato (checkout, 92 transações) | R$ 1.576,23 | Devolver ao lojista e pedir à Orbe a correção do cadastro |
| Taxa cobrada acima do contrato (remessa, 23 transações) | R$ 1.418,88 | Devolver ao lojista e pedir à Ponte a correção do cadastro |
| Operação duplicada no relatório da Ponte (participação que seria contada em dobro) (1) | R$ 410,94 | Ver `pendencias.csv` |
| Spreads negativos da Ponte (participação negativa, fora da comissão até decisão) (4) | R$ -917,03 | Ver `pendencias.csv` |
| Taxas cobradas de lojista sem contrato na planilha (1) | R$ 7.876,05 | Ver `pendencias.csv` |
| Crédito sem pagador identificado (Aurora) (1) | R$ 7.350,00 | Ver `pendencias.csv` |
| Devolução de PIX de lojista a esclarecer (Aurora) (1) | R$ 12.400,00 | Ver `pendencias.csv` |
| Aporte de lojista sem remessa correspondente (Meridiano) (1) | R$ 18.240,00 | Ver `pendencias.csv` |

## Pendências por responsável

**Financeiro Tarvo (aceitar ou contestar com a Ponte)** (4)
- `PEN-006` SPREAD_NEGATIVO | PC-0926-0210 | R$ -343,76
- `PEN-007` SPREAD_NEGATIVO | PC-0926-0326 | R$ -254,61
- `PEN-008` SPREAD_NEGATIVO | PC-0926-0491 | R$ -146,14
- `PEN-009` SPREAD_NEGATIVO | PC-0926-0545 | R$ -172,52

**Financeiro Tarvo (confirmar cadastro)** (3)
- `PEN-002` CADASTRO_EC_NAO_CONFIRMADO | EC 1043396662 | R$ 9.014,07
- `PEN-003` CADASTRO_EC_NAO_CONFIRMADO | EC 1043300981 | R$ 7.767,49
- `PEN-004` CADASTRO_EC_NAO_CONFIRMADO | EC 1038867654 | R$ 10.711,06

**Financeiro Tarvo** (3)
- `PEN-010` CREDITO_NAO_IDENTIFICADO | L50 | R$ 7.350,00
- `PEN-011` DEVOLUCAO_PIX | L65 | R$ 12.400,00
- `PEN-012` APORTE_SEM_REMESSA | MRD2026090425 | R$ 18.240,00

**Financeiro Tarvo (ressarcimento) + Orbe (correção da taxa)** (2)
- `PEN-014` DIVERGENCIA_A_RESSARCIR | CNPJ 22224579000109 | R$ 29,95
- `PEN-015` DIVERGENCIA_A_RESSARCIR | CNPJ 95927868000148 | R$ 1.546,28

**Financeiro Tarvo + Comercial (definir contrato)** (1)
- `PEN-001` SEM_TAXA_CONTRATADA | CNPJ 39566044000119 | R$ 7.876,05

**Financeiro Tarvo + Ponte Câmbio** (1)
- `PEN-005` OPERACAO_DUPLICADA | PC-0926-0162 | R$ 410,94

**Financeiro Tarvo (ressarcimento) + Ponte Câmbio (correção da taxa)** (1)
- `PEN-013` DIVERGENCIA_A_RESSARCIR | CNPJ 17217888000111 | R$ 1.418,88

**Comercial (Diego) + Financeiro Tarvo** (1)
- `PEN-016` CONDICAO_COMERCIAL_NAO_REGISTRADA | Taxas vigentes!L13

## Lançamentos bancários

184 lançamentos classificados: 184 por regra, 0 por IA, 0 aguardando uma pessoa.

## Checagens automáticas

- OK  rastro × comissoes: 36 linhas, 0 divergentes
- OK  rastro × divergencias: 115 linhas, 0 divergentes
- OK  rastro × notas: 23 linhas, 0 divergentes
- OK  rastro × lancamentos: 184 linhas, 0 divergentes
- OK  rastro × pendencias: 16 linhas, 0 divergentes
- OK  truncamento × valor_taxa Orbe: 0 linhas diferentes
- OK  conciliação checkout (base contratada): Σ valor_taxa Orbe 231880.36 = comissão 230304.13 + divergência 1576.23 + taxa fora da comissão 0 -> FECHA
- OK  lançamentos classificados 184 de 184 linhas de extrato
