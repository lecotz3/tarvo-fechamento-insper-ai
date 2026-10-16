# Fechamento mensal Tarvo: Hackathon Barte AI (time Insper AI)

Lê os arquivos do mês **como chegam** e gera, em `saida/`:
- as comissões por lojista;
- as divergências de taxa;
- as notas a emitir;
- os lançamentos classificados;
- as pendências;
- o **rastro** de cada número até a linha de origem.

Os arquivos lidos são o CSV da Orbe, a planilha de taxas, o e-mail `.eml` da Ponte com o anexo, o plano de contas, o extrato CSV do Aurora e o extrato OFX do Meridiano.

## Rodar do zero
```bash
python -m pip install -r requirements.txt          # Python 3.11+ (usa tomllib)
PYTHONPATH=src python -m tarvo.fechar --dados data/set2026 --saida saida
# Windows PowerShell:
#   $env:PYTHONPATH="src"; python -m tarvo.fechar --dados data/set2026 --saida saida
PYTHONPATH=src python -m pytest -q                 # testes com números-âncora + simulação de outubro
```
O comando termina com código 1 se alguma validação falhar (por exemplo, um total que não bate com a soma do rastro).

## O que sai em `saida/`
| Arquivo | Conteúdo |
|---|---|
| `comissoes_por_lojista.csv` | comissão por lojista e linha (CHECKOUT/REMESSA) |
| `divergencias_taxa.csv` | transação a transação: taxa contratada × aplicada e diferença em R$ |
| `notas_a_emitir.csv` | NF por tomador, linha de negócio e valor |
| `lancamentos_classificados.csv` | 184 lançamentos dos 2 extratos com conta, método (REGRA/IA/HUMANO) e confiança |
| `pendencias.csv` | o que precisa de uma pessoa: motivo e quem decide |
| `rastro.csv` | cada `id_saida` → linhas de origem. A soma de `valor` por `id_saida` = número reportado |
| `resumo_fechamento.md` | resumo de 1 página para a analista e o CFO |
| `log_validacao.txt` | resultado das checagens automáticas |
| `detalhe/` | cálculo linha a linha (checkout, remessa, conciliação Meridiano × Ponte) |

## Como a analista usa no fechamento de outubro
1. Salva os 6 arquivos do mês numa pasta nova (ex.: `data/out2026/`). Os nomes podem mudar: os arquivos são achados por padrão (`*orbe*.csv`, `*taxa*.xlsx`, `*.eml`, `*plano*conta*.csv`, `*aurora*.csv`, `*.ofx`).
2. Roda `PYTHONPATH=src python -m tarvo.fechar --dados data/out2026 --saida saida_out2026`.
3. Lê `resumo_fechamento.md` e trata `pendencias.csv`. Cada linha diz o motivo e quem decide.
4. Quando uma regra for decidida (ex.: o financeiro confirma um EC), atualiza `config/` e roda de novo.

O teste `test_roda_em_outubro_sem_retrabalho` comprova isso: copia o data pack com nomes de outubro para uma pasta nova e confere que o resultado é idêntico.

## Configuração (regras de negócio, sem mexer no código)
- `config/premissas.toml`: cada premissa de `HIPOTESES.md`, como a base da comissão, o spread padrão, o tratamento de spread negativo e o tomador da NF de remessa.
- `config/de_para_ec.csv`: ligação EC Orbe → CNPJ para lojistas sem EC na planilha, com status (CONFIRMADO / PENDENTE_CONFIRMACAO / SEM_CONTRATO) e a evidência.
- `config/regras_contas.csv`: regras de classificação dos extratos (regex → conta).

## Onde a IA atua e onde não atua
| Etapa | Quem faz |
|---|---|
| Comissão, divergência, nota, conciliação | **Regra determinística.** Nenhum número é decidido por IA. |
| Ligar EC ↔ CNPJ | **Planilha + de-para confirmado por pessoa.** Nunca por semelhança de nome. |
| Classificar lançamento bancário | **Regra** (`regras_contas.csv`). Só o que nenhuma regra cobre vai para a **IA**, com `--ia`. A conta fica restrita por schema às contas analíticas do plano, e confiança abaixo de 0,8 vira pendência. |
| Regra de negócio desconhecida | **Pergunta ao financeiro** (registrada em `HIPOTESES.md`). Até a resposta, vale uma premissa explícita. |

Em set/2026 as regras cobrem os 184 lançamentos, então a IA não é acionada.
A IA foi usada intensivamente **na construção**: exploração dos dados, desenho das regras e código, sempre conferida por testes e pelo validador. O histórico está em `PROMPTS/`.

## Chaves
- O cálculo não precisa de nenhuma chave.
- Com `--ia`: `pip install anthropic` e uma credencial Anthropic (`ANTHROPIC_API_KEY` ou um perfil `ant auth login`).

## Limitações conhecidas
- **Premissas não confirmadas** estão em `HIPOTESES.md` (H1–H15). Os números mudam se o financeiro responder diferente: basta ajustar `config/` e rodar de novo.
- **Conciliação Aurora × Orbe** (TEDs recebidos × líquido das vendas) não foi implementada. A Orbe liquida parcelas e antecipações em datas diferentes, e não temos a agenda de recebíveis.
- **Lojista novo** sem EC na planilha vira pendência até entrar no de-para. Isso é intencional: nada é casado por nome.
- **Mudança de layout** de um arquivo (coluna renomeada, cabeçalho diferente) faz o leitor falhar com uma mensagem clara, em vez de calcular errado.
- **Remessa:** a comissão do lojista é 50% × soma dos spreads dele, com um arredondamento. Pode diferir em centavos de um cálculo operação a operação.
- Os spreads negativos e a operação duplicada da Ponte ficam **fora da comissão** até alguém decidir (premissas H7 e H8).
