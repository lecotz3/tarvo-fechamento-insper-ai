"""Notas fiscais de serviço a emitir pela Tarvo.

CHECKOUT: uma NF por lojista (tomador = lojista), no valor da comissão de checkout.
REMESSA:  premissa H5 = uma NF contra a Ponte Câmbio pela participação total no spread
          (o e-mail da Ponte condiciona o repasse ao recebimento da 'nota fiscal de intermediação').
          Alternativa configurável: uma NF por lojista.
O rastro da NF reaponta para as mesmas linhas de origem da comissão.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .resultado import Resultado

ZERO = Decimal("0")


def processar(res: Resultado, prem: dict, meta_ponte: dict, competencia: str) -> None:
    rastro_por_id = defaultdict(list)
    for r in res.rastro:
        rastro_por_id[r["id_saida"]].append(r)

    def copiar_rastro(de: list[str], para: str) -> None:
        for i in de:
            for r in rastro_por_id[i]:
                res.rastrear(para, r["arquivo_origem"], r["ref_origem"], r["valor"])

    chk = [c for c in res.comissoes if c["linha_negocio"] == "CHECKOUT"]
    for c in chk:
        if c["comissao_brl"] <= 0:
            res.pendencia("NF_SEM_VALOR_POSITIVO", c["id_saida"], c["comissao_brl"],
                          f"{c['lojista']}: comissão de checkout do mês ≤ 0 (estornos maiores que as vendas). "
                          f"NF não emitida.", "Financeiro Tarvo / Contador",
                          [(r["arquivo_origem"], r["ref_origem"], r["valor"]) for r in rastro_por_id[c["id_saida"]]])
            continue
        id_saida = f"NF-CHK-{c['cnpj']}"
        res.notas.append({"id_saida": id_saida, "tomador_cnpj": c["cnpj"], "tomador": c["lojista"],
                          "linha_negocio": "CHECKOUT", "valor_brl": c["comissao_brl"],
                          "discriminacao": f"Intermediação de pagamentos (MDR e antecipação de recebíveis) - "
                                           f"competência {competencia} - {c['qtd_transacoes']} lançamentos Orbe",
                          "origem": c["id_saida"]})
        copiar_rastro([c["id_saida"]], id_saida)

    rem = [c for c in res.comissoes if c["linha_negocio"] == "REMESSA"]
    if not rem:
        return
    if prem["notas"]["remessa_tomador"].upper() == "PONTE":
        total = sum((c["comissao_brl"] for c in rem), ZERO)
        n_ops = sum(c["qtd_transacoes"] for c in rem)
        pct = rem[0].get("participacao_pct")
        ponte_cnpj = meta_ponte.get("ponte_cnpj")
        id_saida = f"NF-REM-{ponte_cnpj}"
        res.notas.append({"id_saida": id_saida, "tomador_cnpj": ponte_cnpj,
                          "tomador": prem["notas"]["ponte_razao_social"], "linha_negocio": "REMESSA",
                          "valor_brl": total,
                          "discriminacao": f"Comissão de intermediação de câmbio - participação de {pct:f}% no spread "
                                           f"realizado - competência {competencia} - {n_ops} operações "
                                           f"de {len(rem)} lojistas",
                          "origem": ",".join(c["id_saida"] for c in rem)})
        copiar_rastro([c["id_saida"] for c in rem], id_saida)
    else:
        for c in rem:
            id_saida = f"NF-REM-{c['cnpj']}"
            res.notas.append({"id_saida": id_saida, "tomador_cnpj": c["cnpj"], "tomador": c["lojista"],
                              "linha_negocio": "REMESSA", "valor_brl": c["comissao_brl"],
                              "discriminacao": f"Intermediação de câmbio - competência {competencia} - "
                                               f"{c['qtd_transacoes']} operações", "origem": c["id_saida"]})
            copiar_rastro([c["id_saida"]], id_saida)
