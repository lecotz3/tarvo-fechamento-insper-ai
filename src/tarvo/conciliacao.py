"""Conciliação das remessas: extrato Meridiano × relatório da Ponte.

Verificado em set/2026:
  (a) cada TED 'PONTE CAMBIO ... LIQ OPERACOES' = Σ (Valor R$ + IOF R$) das operações que liquidam
      no dia útil seguinte (21 de 21 TEDs batem ao centavo; a operação duplicada foi paga uma vez só);
  (b) por lojista, Σ PIX recebidos = Σ (Valor R$ + IOF R$) das suas remessas (13 de 14 batem ao centavo).
Diferenças viram pendência; nada é corrigido automaticamente.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from .lancamentos import norm
from .resultado import Resultado

ZERO = Decimal("0")


def _chave(nome: str) -> str:
    return " ".join(norm(nome).split()[:2])


def processar(ponte: pd.DataFrame, meridiano: pd.DataFrame, res: Resultado) -> pd.DataFrame:
    p = ponte[~ponte["duplicado"]].copy()
    p["total_liq"] = [v + i for v, i in zip(p["valor_brl"], p["iof_brl"])]
    p["chave"] = p["cliente"].map(_chave)

    # (a) TED de liquidação × operações do próximo dia de liquidação
    ted = meridiano[meridiano["descricao"].map(norm).str.contains(r"TED ENVIADA PONTE CAMBIO.*LIQ")].sort_values("data")
    datas_liq = sorted(p["data_liquidacao"].dt.date.unique())
    ted_ok = 0
    for _, t in ted.iterrows():
        prox = next((d for d in datas_liq if d > t["data"].date()), None)
        esperado = sum(p.loc[p["data_liquidacao"].dt.date == prox, "total_liq"], ZERO) if prox else None
        if esperado is not None and -t["valor"] == esperado:
            ted_ok += 1
        else:
            res.pendencia("TED_REMESSA_SEM_CORRESPONDENCIA", t["ref_origem"], t["valor"],
                          f"TED de liquidação de R$ {-t['valor']} em {t['data']:%Y-%m-%d} não bate com as operações "
                          f"da Ponte liquidadas em {prox} (esperado R$ {esperado}).",
                          "Financeiro Tarvo + Ponte Câmbio",
                          [(t["arquivo_origem"], t["ref_origem"], t["valor"])], banco="MERIDIANO")
    res.log.append(f"INFO conciliação TED Meridiano × liquidações Ponte: {ted_ok} de {len(ted)} TEDs batem ao centavo")

    # (b) aportes PIX por lojista × valor das remessas
    pix = meridiano[meridiano["descricao"].map(norm).str.startswith("PIX RECEB")].copy()
    pix["chave"] = pix["descricao"].map(lambda s: _chave(norm(s).replace("PIX RECEB ", "")))
    linhas = []
    for k in sorted(set(p["chave"]) | set(pix["chave"])):
        esperado = sum(p.loc[p["chave"] == k, "total_liq"], ZERO)
        recebido = sum(pix.loc[pix["chave"] == k, "valor"], ZERO)
        dif = recebido - esperado
        linhas.append({"lojista_chave": k, "remessas_valor_mais_iof": esperado, "pix_recebidos": recebido,
                       "diferenca": dif})
        if dif == 0:
            continue
        candidatos = pix[(pix["chave"] == k) & (pix["valor"] == dif)]
        if len(candidatos) == 1:
            c = candidatos.iloc[0]
            for l in res.lancamentos:
                if l["ref_origem"] == c["ref_origem"]:
                    l["confianca"] = 0.5
                    l["justificativa"] += " | Sem remessa correspondente na Ponte (ver pendência)."
            res.pendencia("APORTE_SEM_REMESSA", c["ref_origem"], c["valor"],
                          f"Meridiano {c['data']:%Y-%m-%d} '{c['descricao']}' R$ {c['valor']}: é o único aporte sem "
                          f"remessa correspondente. Os demais PIX de '{k}' somam exatamente o valor + IOF das remessas "
                          f"dela no mês. Confirmar se é adiantamento de remessa futura (manter em 2.1.02.001), "
                          f"crédito de outro pagador ou valor a devolver.", "Financeiro Tarvo",
                          [(c["arquivo_origem"], c["ref_origem"], c["valor"])], banco="MERIDIANO")
        else:
            res.pendencia("APORTE_DIVERGENTE", f"LOJISTA {k}", dif,
                          f"Aportes PIX de '{k}' (R$ {recebido}) diferem do valor + IOF das remessas (R$ {esperado}).",
                          "Financeiro Tarvo",
                          [(x["arquivo_origem"], x["ref_origem"], x["valor"]) for _, x in pix[pix["chave"] == k].iterrows()]
                          + [(x["arquivo_origem"], x["num_operacao"], -x["total_liq"]) for _, x in p[p["chave"] == k].iterrows()])
    return pd.DataFrame(linhas)
