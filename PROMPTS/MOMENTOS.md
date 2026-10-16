# Momentos que importaram no uso de IA

> RASCUNHO. O time revisa e reescreve com as próprias palavras. Só entram fatos que aconteceram de verdade.

## 1. A IA errou: tolerância que escondeu a regra de truncamento da Orbe (16/10, ~20h20)
- **Pedido:** explorar o relatório da Orbe e conferir se `valor_taxa = valor_bruto × taxa_aplicada`.
- **O que a IA devolveu:** "0 divergências". Mas o script comparava com tolerância de R$ 0,011, o que esconde diferenças de exatamente 1 centavo.
- **O que fizemos:** o validador do pipeline (comparação exata) acusou 1.001 linhas diferentes e 1.014 "divergências". Testamos 4 modos de arredondamento: só o **truncamento** reproduz as 1.943 linhas. Adotamos o truncamento e as divergências caíram para 92, todas reais. Sem isso, entregaríamos ~900 alarmes falsos de R$ 0,01.

## 2. Não casar "HORIZONTE INTERCAMBIO" pelo nome (16/10, ~20h)
- **Pedido:** ligar os ECs da Orbe aos CNPJs da planilha.
- **O que vimos:** o nome sugere a Horizonte Viagens, mas as taxas aplicadas (2,39% / 2,89%) são as da **Novo Horizonte**. Fica no de-para como PENDENTE_CONFIRMACAO, com a evidência registrada, e a pergunta foi para o financeiro.

## 3. (a preencher)
