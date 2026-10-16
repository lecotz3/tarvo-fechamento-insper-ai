"""Checagens que impedem 'número inventado'. Rodam ao fim de toda execução."""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .resultado import Resultado
from .util import valor_taxa

ZERO = Decimal("0")

# arquivo de saída -> coluna com o número que precisa bater com o rastro
VALOR_POR_SAIDA = {
    "comissoes": "comissao_brl",
    "divergencias": "diferenca_brl",
    "notas": "valor_brl",
    "lancamentos": "valor",
    "pendencias": "valor_brl",
}


def validar(res: Resultado, fontes, det_checkout: pd.DataFrame | None = None,
            base_checkout: str = "contratada") -> list[str]:
    erros: list[str] = []
    ok: list[str] = []

    soma = defaultdict(lambda: ZERO)
    for r in res.rastro:
        soma[r["id_saida"]] += r["valor"]

    # 1) todo número de saída = soma das linhas de origem no rastro
    for nome, col in VALOR_POR_SAIDA.items():
        linhas = getattr(res, nome)
        ruins = 0
        for l in linhas:
            v = l.get(col)
            if v is None:
                continue
            if l["id_saida"] not in soma:
                erros.append(f"[{nome}] {l['id_saida']} sem rastro")
                ruins += 1
            elif soma[l["id_saida"]] != v:
                erros.append(f"[{nome}] {l['id_saida']}: valor {v} != soma do rastro {soma[l['id_saida']]}")
                ruins += 1
        ok.append(f"rastro × {nome}: {len(linhas)} linhas, {ruins} divergentes")

    # 2) ids únicos
    for nome in VALOR_POR_SAIDA:
        ids = [l["id_saida"] for l in getattr(res, nome)]
        if len(ids) != len(set(ids)):
            erros.append(f"[{nome}] id_saida repetido")

    # 3) CNPJ com 14 dígitos
    for nome, col in (("comissoes", "cnpj"), ("divergencias", "cnpj"), ("notas", "tomador_cnpj")):
        for l in getattr(res, nome):
            if not re.fullmatch(r"\d{14}", str(l.get(col) or "")):
                erros.append(f"[{nome}] {l['id_saida']}: CNPJ inválido '{l.get(col)}'")

    # 4) a regra de truncamento reproduz o valor_taxa da Orbe em todas as linhas
    o = fontes.orbe
    recalc = [valor_taxa(b, t) for b, t in zip(o["valor_bruto"], o["taxa_aplicada_pct"])]
    dif = sum(1 for a, b in zip(recalc, o["valor_taxa"]) if a != b)
    (erros if dif else ok).append(f"truncamento × valor_taxa Orbe: {dif} linhas diferentes")

    # 5) conciliação do checkout: Σ valor_taxa Orbe = Σ comissão + Σ divergência + Σ taxa fora da comissão
    if det_checkout is not None and res.comissoes:
        tot_orbe = sum(o.loc[~o["duplicado"], "valor_taxa"], ZERO)
        tot_com = sum((c["comissao_brl"] for c in res.comissoes if c["linha_negocio"] == "CHECKOUT"), ZERO)
        tot_div = sum((d["diferenca_brl"] for d in res.divergencias if d["linha_negocio"] == "CHECKOUT"), ZERO)
        d = det_checkout[~det_checkout["situacao"].eq("DUPLICADO")]
        fora = sum(d.loc[d["comissao"].isna(), "valor_taxa"], ZERO)
        # base "contratada": a divergência é a parte do valor_taxa que NÃO entra na comissão
        div_fora = tot_div if base_checkout == "contratada" else ZERO
        fecha = tot_orbe == tot_com + div_fora + fora
        msg = (f"conciliação checkout (base {base_checkout}): Σ valor_taxa Orbe {tot_orbe} = comissão {tot_com} "
               f"+ divergência {div_fora} + taxa fora da comissão {fora} -> {'FECHA' if fecha else 'NÃO FECHA'}")
        (ok if fecha else erros).append(msg)

    # 6) conta contábil existe e aceita lançamento
    if res.lancamentos:
        analiticas = set(fontes.plano.loc[fontes.plano["ACEITA_LANCTO"].str.upper() == "S", "COD_CONTA"])
        for l in res.lancamentos:
            if l["conta_codigo"] and l["conta_codigo"] not in analiticas:
                erros.append(f"[lancamentos] {l['id_saida']}: conta {l['conta_codigo']} não é analítica")
        n_ext = len(fontes.aurora) + len(fontes.meridiano)
        (ok if len(res.lancamentos) == n_ext else erros).append(
            f"lançamentos classificados {len(res.lancamentos)} de {n_ext} linhas de extrato")

    res.log.extend(["OK  " + m for m in ok])
    res.log.extend(["ERRO " + m for m in erros])
    return erros
