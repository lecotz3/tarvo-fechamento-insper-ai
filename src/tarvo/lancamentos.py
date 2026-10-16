"""Classificação dos lançamentos dos dois extratos no plano de contas do ERP Fênix.

Ordem de decisão:
  1. REGRA: tabela config/regras_contas.csv (regex sobre o histórico, primeira que casar vence).
     '<LOJISTA>' no padrão exige que o nome no histórico comece com um lojista conhecido
     (as duas primeiras palavras do nome, sem acento, comparadas exatamente; nada de semelhança aproximada).
  2. IA: só para o que nenhuma regra cobre, se habilitada (ver ia.py). Confiança abaixo do limite -> pendência.
  3. HUMANO: sem regra e sem IA -> conta em branco + pendência.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from .resultado import Resultado


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", s.replace("-", " ")).strip()


STOP_SUFIXOS = {"LTDA", "LTD", "LT", "L", "ME", "SA", "S/A", "EIRELI"}


def chaves_lojistas(*listas_de_nomes) -> set[str]:
    """Primeiras duas palavras de cada nome conhecido de lojista (planilha, Orbe, Ponte, de-para)."""
    chaves = set()
    for nomes in listas_de_nomes:
        for n in nomes:
            p = [w for w in norm(n).split() if w not in STOP_SUFIXOS]
            if len(p) >= 2:
                chaves.add(" ".join(p[:2]))
    return chaves


def carregar_regras(path: Path) -> pd.DataFrame:
    r = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    r["ordem"] = r["ordem"].astype(int)
    r["confianca"] = r["confianca"].astype(float)
    return r.sort_values("ordem")


def _casa(regra, desc_n: str, chaves: set[str]) -> bool:
    pad = regra["padrao"]
    if "<LOJISTA>" in pad:
        prefixo = pad.split("<LOJISTA>")[0]
        m = re.search(prefixo, desc_n)
        if not m:
            return False
        resto = desc_n[m.end():].split()
        return len(resto) >= 2 and " ".join(resto[:2]) in chaves
    return re.search(pad, desc_n) is not None


def processar(extratos: list[pd.DataFrame], regras: pd.DataFrame, chaves: set[str], res: Resultado,
              classificador_ia=None, limite_ia: float = 0.8) -> pd.DataFrame:
    saida = []
    for ext in extratos:
        for _, l in ext.iterrows():
            desc_n = norm(l["descricao"])
            id_saida = f"LAN-{l['banco']}-{l['ref_origem']}"
            reg = {"id_saida": id_saida, "banco": l["banco"], "ref_origem": l["ref_origem"],
                   "data": l["data"].date(), "descricao": l["descricao"], "valor": l["valor"],
                   "conta_codigo": "", "metodo": "HUMANO", "confianca": 0.0, "regra": "", "justificativa": ""}
            regra = next((r for _, r in regras.iterrows()
                          if r["banco"] in ("*", l["banco"]) and _casa(r, desc_n, chaves)), None)
            if regra is not None:
                reg.update(conta_codigo=regra["conta_codigo"], metodo="REGRA", confianca=regra["confianca"],
                           regra=f"R{regra['ordem']}", justificativa=regra["nota"])
                if regra["pendencia"]:
                    res.pendencia(regra["pendencia"], l["ref_origem"], l["valor"],
                                  f"{l['banco']} {l['data']:%Y-%m-%d} '{l['descricao']}': {regra['nota']}. "
                                  f"Classificado provisoriamente em {regra['conta_codigo']}.",
                                  regra["quem_decide"] or "Financeiro Tarvo",
                                  [(l["arquivo_origem"], l["ref_origem"], l["valor"])], banco=l["banco"])
            elif classificador_ia is not None:
                sug = classificador_ia(l)
                if sug:
                    reg.update(conta_codigo=sug["conta_codigo"], metodo="IA", confianca=sug["confianca"],
                               justificativa=sug.get("justificativa", ""))
                if not sug or sug["confianca"] < limite_ia:
                    res.pendencia("LANCAMENTO_BAIXA_CONFIANCA", l["ref_origem"], l["valor"],
                                  f"{l['banco']} '{l['descricao']}': nenhuma regra cobre; sugestão da IA "
                                  f"{sug['conta_codigo'] if sug else '-'} (confiança {sug['confianca'] if sug else 0}). "
                                  f"Confirmar a conta.", "Financeiro Tarvo / Contador",
                                  [(l["arquivo_origem"], l["ref_origem"], l["valor"])], banco=l["banco"])
            else:
                res.pendencia("LANCAMENTO_NAO_CLASSIFICADO", l["ref_origem"], l["valor"],
                              f"{l['banco']} '{l['descricao']}': nenhuma regra de classificação cobre este histórico.",
                              "Financeiro Tarvo / Contador",
                              [(l["arquivo_origem"], l["ref_origem"], l["valor"])], banco=l["banco"])
            res.lancamentos.append(reg)
            res.rastrear(id_saida, l["arquivo_origem"], l["ref_origem"], l["valor"])
            saida.append(reg)
    return pd.DataFrame(saida)
