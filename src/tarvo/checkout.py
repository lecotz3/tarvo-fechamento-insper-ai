"""Linha de negócio CHECKOUT: comissão por lojista e divergência taxa contratada × aplicada.

Para cada linha da Orbe:
  1. EC -> CNPJ (planilha ou de-para em config/; nunca por semelhança de nome);
  2. taxa contratada = planilha vigente na data (venda original, para estornos) + modalidade + faixa de parcelas;
  3. comissão da linha = valor_bruto × taxa base (contratada ou aplicada), truncada nos centavos como a Orbe;
  4. divergência = valor_taxa cobrado pela Orbe − comissão pela taxa contratada.
Assim, por construção, Σ valor_taxa (Orbe) = Σ comissão + Σ divergência (com base "contratada").
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .lojistas import Cadastro
from .resultado import Resultado
from .util import valor_taxa

ZERO = Decimal("0")


def coluna_taxa(r) -> str | None:
    tipo = r["tipo_lancamento"].upper()
    if tipo.startswith("ANTECIPACAO") or tipo.startswith("REVERSAO ANTECIPACAO"):
        return "antecipacao"
    mod = (r["modalidade"] or "").upper()
    if mod == "DEBITO":
        return "debito"
    if mod == "CREDITO A VISTA":
        return "credito_vista"
    if mod == "PIX":
        return "pix"
    if mod == "CREDITO PARCELADO":
        p = r["qtd_parcelas"]
        if pd.isna(p):
            return None
        if 2 <= p <= 6:
            return "credito_2_6"
        if 7 <= p <= 12:
            return "credito_7_12"
    return None


def processar(orbe: pd.DataFrame, cad: Cadastro, prem: dict, res: Resultado) -> pd.DataFrame:
    pc = prem["checkout"]
    det = []          # detalhe por transação (vai para saida/detalhe_checkout.csv)
    sem_ec = defaultdict(list)
    sem_contrato = defaultdict(list)

    for _, r in orbe.iterrows():
        ec = r["cod_estabelecimento"]
        tipo = r["tipo_lancamento"].upper()
        d = {"id_transacao": r["id_transacao"], "arquivo_origem": r["arquivo_origem"], "ec": ec,
             "nome_orbe": r["nome_estabelecimento"], "tipo_lancamento": tipo, "modalidade": r["modalidade"],
             "qtd_parcelas": r["qtd_parcelas"], "data_movimento": r["data_movimento"].date(),
             "valor_bruto": r["valor_bruto"], "taxa_aplicada_pct": r["taxa_aplicada_pct"],
             "valor_taxa": r["valor_taxa"], "cnpj": None, "taxa_contratada_pct": None,
             "ref_contrato": None, "comissao": None, "divergencia": None, "situacao": "OK"}

        if r["duplicado"]:
            d["situacao"] = "DUPLICADO"
            res.pendencia("TRANSACAO_DUPLICADA", r["id_transacao"], r["valor_taxa"],
                          "id_transacao repetido no relatório da Orbe; considerado uma vez só.",
                          "Financeiro Tarvo (contestar com a Orbe)",
                          [(r["arquivo_origem"], r["id_transacao"], r["valor_taxa"])])
            det.append(d)
            continue
        if not pc["incluir_antecipacao"] and "ANTECIPACAO" in tipo:
            d["situacao"] = "FORA_ESCOPO"
            det.append(d)
            continue

        c = cad.ec_para_cnpj.get(ec)
        if not c:
            d["situacao"] = "SEM_CADASTRO"
            sem_ec[ec].append(d)
            det.append(d)
            continue
        d["cnpj"] = c

        usa_original = tipo in ("ESTORNO", "REVERSAO ANTECIPACAO") and pc["data_taxa_estorno"] == "venda_original"
        dia = r["data_venda_original"] if usa_original and pd.notna(r["data_venda_original"]) else r["data_movimento"]
        cands = cad.contratos(c, dia.date())
        col = coluna_taxa(r)
        contratada = None
        if len(cands) == 1 and col:
            linha = cands.iloc[0]
            contratada = linha[col]
            d["ref_contrato"] = linha["ref_origem"]
            if linha["inativo"]:
                d["situacao"] = "LOJISTA_INATIVO"
        elif len(cands) > 1:
            d["situacao"] = "VIGENCIA_AMBIGUA"

        aplicada_val = r["valor_taxa"]
        if contratada is not None:
            d["taxa_contratada_pct"] = contratada
            pela_contratada = valor_taxa(r["valor_bruto"], contratada)
            d["divergencia"] = aplicada_val - pela_contratada
            d["comissao"] = pela_contratada if pc["base_comissao"] == "contratada" else aplicada_val
        else:
            if d["situacao"] == "OK":
                d["situacao"] = "SEM_CONTRATO"
            sem_contrato[c].append(d)
            d["comissao"] = aplicada_val if pc["sem_contrato"] == "aplicada_com_pendencia" else None
        det.append(d)

    df = pd.DataFrame(det)

    # --- comissão por lojista (com rastro até cada transação) ---
    ok = df[df["comissao"].notna()]
    for c, g in ok.groupby("cnpj", sort=True):
        id_saida = f"COM-CHK-{c}"
        total = sum(g["comissao"], ZERO)
        status_ec = {cad.ec_status.get(e, ("?", ""))[0] for e in g["ec"]}
        res.comissoes.append({"id_saida": id_saida, "cnpj": c, "lojista": cad.nome.get(c, g["nome_orbe"].iloc[0]),
                              "linha_negocio": "CHECKOUT", "comissao_brl": total,
                              "qtd_transacoes": len(g), "ec_orbe": ",".join(sorted(set(g["ec"]))),
                              "status_cadastro": ",".join(sorted(status_ec)),
                              "situacao": ",".join(sorted(set(g["situacao"])))})
        for _, t in g.iterrows():
            res.rastrear(id_saida, t["arquivo_origem"], t["id_transacao"], t["comissao"])

    # --- divergências transação a transação ---
    div = df[df["divergencia"].notna() & (df["divergencia"] != 0)]
    for _, t in div.iterrows():
        id_saida = f"DIV-CHK-{t['id_transacao']}"
        res.divergencias.append({"id_saida": id_saida, "cnpj": t["cnpj"], "linha_negocio": "CHECKOUT",
                                 "ref_origem": t["id_transacao"], "taxa_contratada_pct": t["taxa_contratada_pct"],
                                 "taxa_aplicada_pct": t["taxa_aplicada_pct"], "diferenca_brl": t["divergencia"],
                                 "lojista": cad.nome.get(t["cnpj"], t["nome_orbe"]), "data": t["data_movimento"],
                                 "tipo_lancamento": t["tipo_lancamento"], "modalidade": t["modalidade"],
                                 "qtd_parcelas": t["qtd_parcelas"], "valor_bruto": t["valor_bruto"],
                                 "ref_contrato": t["ref_contrato"]})
        res.rastrear(id_saida, t["arquivo_origem"], t["id_transacao"], t["divergencia"])

    # --- pendências de cadastro / contrato ---
    for ec, linhas in sem_ec.items():
        v = sum((x["valor_taxa"] for x in linhas), ZERO)
        res.pendencia("LOJISTA_SEM_CADASTRO", f"EC {ec}", v,
                      f"EC {ec} ('{linhas[0]['nome_orbe']}') tem {len(linhas)} lançamentos na Orbe e não está na planilha "
                      f"nem no de-para. Comissão não calculada.", "Financeiro Tarvo (cadastro)",
                      [(x["arquivo_origem"], x["id_transacao"], x["valor_taxa"]) for x in linhas])
    for c, linhas in sem_contrato.items():
        v = sum((x["valor_taxa"] for x in linhas), ZERO)
        trat = ("comissão calculada pela taxa aplicada pela Orbe" if pc["sem_contrato"] == "aplicada_com_pendencia"
                else "fora da comissão")
        res.pendencia("SEM_TAXA_CONTRATADA", f"CNPJ {c}", v,
                      f"{cad.nome.get(c, c)}: {len(linhas)} lançamentos sem taxa contratada vigente na planilha "
                      f"({trat}). Divergência não calculada para não gerar alarme falso.",
                      "Financeiro Tarvo + Comercial (definir contrato)",
                      [(x["arquivo_origem"], x["id_transacao"], x["valor_taxa"]) for x in linhas])
    for ec, (status, evid) in cad.ec_status.items():
        if status == "PENDENTE_CONFIRMACAO" and ec in set(df["ec"]):
            g = df[(df["ec"] == ec) & df["comissao"].notna()]
            v = sum(g["comissao"], ZERO)
            res.pendencia("CADASTRO_EC_NAO_CONFIRMADO", f"EC {ec}", v,
                          f"EC {ec} ligado ao CNPJ {cad.ec_para_cnpj[ec]} ({cad.nome.get(cad.ec_para_cnpj[ec])}) por evidência, "
                          f"sem confirmação do financeiro: {evid}", "Financeiro Tarvo (confirmar cadastro)",
                          [(t["arquivo_origem"], t["id_transacao"], t["comissao"]) for _, t in g.iterrows()])
    return df
