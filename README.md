# Fechamento mensal Tarvo: Hackathon Barte AI (time Insper AI)

Lê os arquivos do mês **como chegam** (CSV da Orbe, planilha de taxas, e-mail .eml da Ponte com anexo, plano de contas, extrato CSV Aurora, extrato OFX Meridiano) e gera, em `saida/`, as comissões por lojista, as divergências de taxa, as notas a emitir, os lançamentos classificados, as pendências e o **rastro** de cada número até a linha de origem.

## Rodar do zero
```bash
python -m pip install -r requirements.txt          # Python 3.11+ (usa tomllib)
PYTHONPATH=src python -m tarvo.fechar --dados data/set2026 --saida saida
# Windows PowerShell: $env:PYTHONPATH="src"; python -m tarvo.fechar --dados data/set2026 --saida saida
```
O comando termina com código 1 se alguma validação falhar (ex.: total que não bate com a soma do rastro). O relatório das checagens fica em `saida/log_validacao.txt`.

## Fechar outro mês (ex.: outubro)
1. Coloque os 6 arquivos do mês numa pasta nova (ex.: `data/out2026/`). Os nomes podem mudar: os arquivos são achados por padrão (`*orbe*.csv`, `*taxa*.xlsx`, `*.eml`, `*plano*conta*.csv`, `*aurora*.csv`, `*.ofx`).
2. `PYTHONPATH=src python -m tarvo.fechar --dados data/out2026 --saida saida_out2026`
3. Revise `pendencias.csv`. Lojista novo sem EC na planilha entra em `config/de_para_ec.csv` depois de confirmado.

## Configuração (regras de negócio)
- `config/premissas.toml`: cada premissa de `HIPOTESES.md` (base da comissão, spread padrão, tratamento de spread negativo, tomador da NF de remessa…).
- `config/de_para_ec.csv`: ligação EC Orbe → CNPJ para lojistas sem EC na planilha, com status e evidência.

## Chaves
Nenhuma chave é necessária para o cálculo. (Se a classificação por IA do resíduo de extrato for ativada, ela usa `ANTHROPIC_API_KEY`.)

## Limitações conhecidas
- (em construção)
