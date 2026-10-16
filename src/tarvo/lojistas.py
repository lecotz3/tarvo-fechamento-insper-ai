"""Cadastro de lojistas: junta a planilha de taxas (CNPJ, EC) com o de-para confirmado em config/.

Nunca casa nomes por semelhança. O EC só é ligado a um CNPJ se estiver na planilha
ou no de-para (com status e evidência registrados).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from .util import cnpj


@dataclass
class Cadastro:
    taxas: pd.DataFrame                # linhas da planilha (uma por vigência)
    ec_para_cnpj: dict[str, str]
    ec_status: dict[str, tuple[str, str]]   # ec -> (status, evidência)
    nome: dict[str, str]               # cnpj -> nome canônico

    def contratos(self, cnpj_: str, dia: date) -> pd.DataFrame:
        """Linhas da planilha vigentes para o CNPJ na data. Mais de uma = vigência ambígua (pendência)."""
        return self.taxas[(self.taxas["cnpj"] == cnpj_)
                          & (self.taxas["vig_inicio"] <= dia) & (self.taxas["vig_fim"] >= dia)]


def montar(taxas: pd.DataFrame, de_para_path: Path) -> Cadastro:
    ec_para_cnpj, ec_status, nome = {}, {}, {}
    for _, r in taxas.iterrows():
        if r["cnpj"]:
            atual = nome.get(r["cnpj"], "")
            cand = str(r["lojista_planilha"]).replace("(NOVA)", "").strip()
            if len(cand) > len(atual):
                nome[r["cnpj"]] = cand
        if r["ec_orbe"]:
            ec_para_cnpj[r["ec_orbe"]] = r["cnpj"]
            ec_status[r["ec_orbe"]] = ("PLANILHA", r["ref_origem"])
    if de_para_path.exists():
        dp = pd.read_csv(de_para_path, sep=";", dtype=str, keep_default_na=False)
        for _, r in dp.iterrows():
            ec, c = r["ec_orbe"].strip(), cnpj(r["cnpj"])
            if ec in ec_para_cnpj and ec_para_cnpj[ec] != c:
                raise ValueError(f"de-para conflita com a planilha para EC {ec}")
            ec_para_cnpj[ec] = c
            ec_status[ec] = (r["status"].strip(), r["evidencia"].strip())
            nome.setdefault(c, r["nome_canonico"].strip())
    return Cadastro(taxas=taxas, ec_para_cnpj=ec_para_cnpj, ec_status=ec_status, nome=nome)
