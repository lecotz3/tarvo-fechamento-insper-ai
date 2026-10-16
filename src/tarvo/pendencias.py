"""Pendências que atravessam as linhas de negócio (cada uma com motivo e quem decide)."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .lojistas import Cadastro
from .resultado import Resultado

ZERO = Decimal("0")

PARCEIRO = {"CHECKOUT": "Orbe", "REMESSA": "Ponte Câmbio"}


def processar(res: Resultado, cad: Cadastro, cnpjs_com_movimento: set[str]) -> None:
    # 1) divergências: alguém precisa decidir ressarcir o lojista e cobrar a correção do parceiro
    origem = defaultdict(list)
    for r in res.rastro:
        origem[r["id_saida"]].append((r["arquivo_origem"], r["ref_origem"], r["valor"]))
    grupos = defaultdict(list)
    for d in res.divergencias:
        grupos[(d["cnpj"], d["linha_negocio"])].append(d)
    for (c, linha), ds in sorted(grupos.items()):
        total = sum((d["diferenca_brl"] for d in ds), ZERO)
        datas = sorted(d["data"] for d in ds)
        pares = sorted({(str(d["taxa_contratada_pct"]), str(d["taxa_aplicada_pct"])) for d in ds})
        resumo_taxas = " / ".join(f"contratada {a}% x aplicada {b}%" for a, b in pares[:4])
        res.pendencia("DIVERGENCIA_A_RESSARCIR", f"CNPJ {c}", total,
                      f"{cad.nome.get(c, c)} ({linha}): {len(ds)} transações cobradas fora do contrato entre "
                      f"{datas[0]} e {datas[-1]} ({resumo_taxas}). Total cobrado a mais: R$ {total}. "
                      f"Decidir devolução ao lojista e pedir correção do cadastro à {PARCEIRO[linha]}.",
                      f"Financeiro Tarvo (ressarcimento) + {PARCEIRO[linha]} (correção da taxa)",
                      [o for d in ds for o in origem[d["id_saida"]]],
                      linha_negocio=linha, cnpj=c)

    # 2) observações/comentários na planilha que indicam regra comercial fora da planilha
    gatilhos = ("comercial", "condi", "especial", "ver c/")
    t = cad.taxas
    for _, r in t.iterrows():
        texto = " | ".join(str(x) for x in (r["comentario"], r["obs"]) if isinstance(x, str) and x.strip())
        if r["cnpj"] in cnpjs_com_movimento and any(g in texto.lower() for g in gatilhos):
            res.pendencia("CONDICAO_COMERCIAL_NAO_REGISTRADA", r["ref_origem"], None,
                          f"{r['lojista_planilha']}: a planilha indica condição comercial fora da tabela ('{texto}'). "
                          f"Cálculo feito com as taxas da linha; confirmar se havia condição especial em vigor.",
                          "Comercial (Diego) + Financeiro Tarvo", cnpj=r["cnpj"])

    # 3) lojista marcado como inativo com movimento no mês
    for _, r in t[t["inativo"]].iterrows():
        if r["cnpj"] in cnpjs_com_movimento:
            res.pendencia("LOJISTA_INATIVO_COM_MOVIMENTO", r["ref_origem"], None,
                          f"{r['lojista_planilha']} está marcado como inativo na planilha mas tem movimento no mês.",
                          "Financeiro Tarvo + Comercial", cnpj=r["cnpj"])
