"""Relatório de comissões da adquirente Orbe (CSV ';', vírgula decimal, datas dd/mm/aaaa)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..util import br_num

COLUNAS = [
    "id_transacao", "data_movimento", "cod_estabelecimento", "nome_estabelecimento",
    "tipo_lancamento", "modalidade", "qtd_parcelas", "bandeira", "valor_bruto",
    "taxa_aplicada_pct", "valor_taxa", "valor_liquido", "id_referencia", "data_venda_original",
]


def carregar(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"{path.name}: colunas ausentes {faltando}")
    for c in df.columns:
        df[c] = df[c].str.strip()
    for c in ["valor_bruto", "taxa_aplicada_pct", "valor_taxa", "valor_liquido"]:
        df[c] = df[c].map(br_num)
    df["data_movimento"] = pd.to_datetime(df["data_movimento"], format="%d/%m/%Y")
    df["data_venda_original"] = pd.to_datetime(df["data_venda_original"].replace("", None), format="%d/%m/%Y")
    df["qtd_parcelas"] = pd.to_numeric(df["qtd_parcelas"].replace("", None)).astype("Int64")
    df["arquivo_origem"] = path.name
    df["ref_origem"] = df["id_transacao"]
    df["linha_arquivo"] = df.index + 2  # cabeçalho na linha 1
    # Duplicata não derruba a execução: vira pendência no motor de checkout.
    df["duplicado"] = df["id_transacao"].duplicated(keep="first")
    return df
