"""Linha de negócio REMESSA: participação da Tarvo no spread das operações da Ponte Câmbio.

Para cada operação do relatório anexado ao e-mail:
  1. duplicata (mesmo Nº Operação) conta uma vez; a repetição vira pendência;
  2. lojista pelo CNPJ (normalizado) na planilha; spread contratado = coluna 'Spread remessa'
     (vazio ou 'padrão' -> spread padrão das premissas);
  3. participação = Spread R$ × % do contrato com a Ponte (lido do e-mail), arredondada por operação;
  4. spread negativo -> pendência (fora da comissão) ou abatido, conforme premissa;
  5. divergência = Spread R$ cobrado − spread pelo % contratado (base PTAX), quando a diferença
     de % passa da tolerância.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .lojistas import Cadastro
from .resultado import Resultado
from .util import money, ratear

ZERO = Decimal("0")


def participacao_pct(prem: dict, meta: dict) -> Decimal:
    pr = prem["remessa"]
    if pr["participacao"] == "email" and meta.get("participacao_pct_email") is not None:
        return meta["participacao_pct_email"]
    if pr["participacao"] not in ("email",):
        return Decimal(str(pr["participacao"]))
    return Decimal(str(pr["participacao_fallback_pct"]))


def processar(ponte: pd.DataFrame, meta: dict, cad: Cadastro, prem: dict, res: Resultado) -> pd.DataFrame:
    pr = prem["remessa"]
    pct = participacao_pct(prem, meta)
    padrao = Decimal(str(pr["spread_padrao_pct"]))
    tol = Decimal(str(pr["tolerancia_spread_pp"]))
    det = []
    sem_cadastro = defaultdict(list)

    for _, r in ponte.iterrows():
        d = {"num_operacao": r["num_operacao"], "linha_anexo": r["linha_anexo"], "arquivo_origem": r["arquivo_origem"],
             "cnpj": r["cnpj"], "cliente": r["cliente"], "data_contratacao": r["data_contratacao"].date(),
             "data_liquidacao": r["data_liquidacao"].date(), "moeda": r["moeda"], "valor_me": r["valor_me"],
             "ptax": r["ptax"], "valor_brl": r["valor_brl"], "spread_brl": r["spread_brl"],
             "spread_pct": r["spread_pct"], "status_compliance": r["status_compliance"],
             "observacao": r["observacao"], "spread_contratado_pct": None, "origem_spread": None,
             "participacao": None, "divergencia": None, "situacao": "OK"}
        part = money(r["spread_brl"] * pct / 100)

        if r["duplicado"]:
            d["situacao"] = "DUPLICADO"
            res.pendencia("OPERACAO_DUPLICADA", r["num_operacao"], part,
                          f"Operação repetida no relatório da Ponte (linha {r['linha_anexo']} do anexo, obs. "
                          f"'{r['observacao']}'). Contada uma vez. O total do rodapé da Ponte inclui a repetição: "
                          f"contestar antes de emitir a NF. Valor = participação que seria contada em dobro.",
                          "Financeiro Tarvo + Ponte Câmbio",
                          [(r["arquivo_origem"], r["num_operacao"], part)], linha_origem=r["linha_anexo"])
            det.append(d)
            continue

        cands = cad.contratos(r["cnpj"], d["data_contratacao"])
        if len(cands) != 1:
            d["situacao"] = "SEM_CADASTRO" if len(cands) == 0 else "VIGENCIA_AMBIGUA"
            sem_cadastro[r["cnpj"]].append((d, part))
            det.append(d)
            continue
        linha = cands.iloc[0]
        if linha["spread_remessa"] is not None:
            contratado, origem = linha["spread_remessa"], "planilha"
        else:
            contratado, origem = padrao, f"padrão ({linha['spread_remessa_marcador']})"
        d["spread_contratado_pct"], d["origem_spread"] = contratado, origem
        d["ref_contrato"] = linha["ref_origem"]

        if r["spread_brl"] < 0:
            d["situacao"] = "SPREAD_NEGATIVO"
            aceitar = pr["spread_negativo"] == "aceitar"
            d["participacao"] = part if aceitar else None
            res.pendencia("SPREAD_NEGATIVO", r["num_operacao"], part,
                          f"Spread negativo ({d['spread_pct']:.4f}%; obs. '{r['observacao']}'). Spread estimado D-1 "
                          f"era R$ {r['spread_estimado_brl']}. "
                          + ("Abatido da comissão (premissa)." if aceitar else
                             "Fora da comissão até alguém decidir se a Tarvo aceita ou contesta com a Ponte."),
                          "Financeiro Tarvo (aceitar ou contestar com a Ponte)",
                          [(r["arquivo_origem"], r["num_operacao"], part)])
            det.append(d)
            continue

        d["participacao"] = part
        if abs(d["spread_pct"] - contratado) > tol:
            spread_contr = money(r["valor_me"] * r["ptax"] * contratado / 100)
            d["divergencia"] = r["spread_brl"] - spread_contr
            if pr["base_comissao"] == "contratado":
                d["participacao"] = money(spread_contr * pct / 100)
        det.append(d)

    df = pd.DataFrame(det)

    ok = df[df["participacao"].notna()]
    for c, g in ok.groupby("cnpj", sort=True):
        id_saida = f"COM-REM-{c}"
        # comissão do lojista = % × soma dos spreads dele (um arredondamento só); os centavos
        # são rateados entre as operações para o rastro fechar exatamente com o total
        base_ops = [p * 100 / pct for p in g["participacao"]] if pr["base_comissao"] == "contratado" else None
        spreads = list(g["spread_brl"]) if base_ops is None else base_ops
        total = money(sum(spreads, ZERO) * pct / 100)
        fatias = ratear(total, spreads)
        df.loc[g.index, "participacao"] = fatias
        g = df.loc[g.index]
        res.comissoes.append({"id_saida": id_saida, "cnpj": c, "lojista": cad.nome.get(c, g["cliente"].iloc[0]),
                              "linha_negocio": "REMESSA", "comissao_brl": total,
                              "qtd_transacoes": len(g), "participacao_pct": pct,
                              "situacao": ",".join(sorted(set(g["situacao"])))})
        for _, t in g.iterrows():
            res.rastrear(id_saida, t["arquivo_origem"], t["num_operacao"], t["participacao"])

    div = df[df["divergencia"].notna() & (df["divergencia"] != 0)]
    for _, t in div.iterrows():
        id_saida = f"DIV-REM-{t['num_operacao']}"
        res.divergencias.append({"id_saida": id_saida, "cnpj": t["cnpj"], "linha_negocio": "REMESSA",
                                 "ref_origem": t["num_operacao"], "taxa_contratada_pct": t["spread_contratado_pct"],
                                 "taxa_aplicada_pct": t["spread_pct"].quantize(Decimal("0.0001")),
                                 "diferenca_brl": t["divergencia"], "lojista": cad.nome.get(t["cnpj"], t["cliente"]),
                                 "data": t["data_contratacao"], "tipo_lancamento": "REMESSA", "modalidade": t["moeda"],
                                 "qtd_parcelas": None, "valor_bruto": t["valor_brl"],
                                 "ref_contrato": t.get("ref_contrato")})
        res.rastrear(id_saida, t["arquivo_origem"], t["num_operacao"], t["divergencia"])

    for c, itens in sem_cadastro.items():
        v = sum((p for _, p in itens), ZERO)
        res.pendencia("LOJISTA_SEM_CADASTRO", f"CNPJ {c}", v,
                      f"Cliente '{itens[0][0]['cliente']}' (CNPJ {c}) tem {len(itens)} remessas e não está (ou está "
                      f"ambíguo) na planilha de taxas. Participação não calculada.", "Financeiro Tarvo (cadastro)",
                      [(d["arquivo_origem"], d["num_operacao"], p) for d, p in itens])

    # conferência com o rodapé do relatório (informativo)
    rod = meta.get("rodape", {})
    if "Spread total R$" in rod:
        soma_todas = sum(ponte["spread_brl"], ZERO)
        soma_unicas = sum(ponte.loc[~ponte["duplicado"], "spread_brl"], ZERO)
        res.log.append(f"INFO rodapé Ponte: spread total declarado {rod['Spread total R$']} | soma de todas as linhas "
                       f"{soma_todas} | soma das operações únicas {soma_unicas}")
    return df
