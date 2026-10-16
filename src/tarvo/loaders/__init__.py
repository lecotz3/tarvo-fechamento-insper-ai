"""Leitores de cada fonte. Todos devolvem linhas com arquivo_origem e ref_origem para o rastro."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..util import find_file
from . import bancos, orbe, ponte, taxas


@dataclass
class Fontes:
    orbe: pd.DataFrame
    taxas: pd.DataFrame
    ponte: pd.DataFrame
    ponte_meta: dict
    plano: pd.DataFrame
    aurora: pd.DataFrame
    meridiano: pd.DataFrame
    arquivos: dict = field(default_factory=dict)


def carregar_tudo(pasta: Path) -> Fontes:
    arq = {
        "orbe": find_file(pasta, "*orbe*.csv"),
        "taxas": find_file(pasta, "*taxa*.xlsx"),
        "ponte": find_file(pasta, "*ponte*.eml", "*.eml"),
        "plano": find_file(pasta, "*plano*conta*.csv"),
        "aurora": find_file(pasta, "*aurora*.csv"),
        "meridiano": find_file(pasta, "*meridiano*.ofx", "*.ofx"),
    }
    p_df, p_meta = ponte.carregar(arq["ponte"])
    return Fontes(
        orbe=orbe.carregar(arq["orbe"]),
        taxas=taxas.carregar(arq["taxas"]),
        ponte=p_df,
        ponte_meta=p_meta,
        plano=bancos.carregar_plano(arq["plano"]),
        aurora=bancos.carregar_aurora(arq["aurora"]),
        meridiano=bancos.carregar_meridiano(arq["meridiano"]),
        arquivos={k: v.name for k, v in arq.items()},
    )
