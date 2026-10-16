"""E-mail mensal da Ponte Câmbio (.eml) com o relatório de operações em anexo (.xlsx).

O anexo é extraído em memória: a solução consome o arquivo exatamente como chega na caixa de entrada.
"""
from __future__ import annotations

import email
import io
import re
from email import policy
from pathlib import Path

import openpyxl
import pandas as pd

from ..util import cnpj, dec

COLUNAS = {
    "Nº Operação": "num_operacao",
    "Data Contratação": "data_contratacao",
    "Data Liquidação": "data_liquidacao",
    "CNPJ Cliente": "cnpj_cliente",
    "Cliente": "cliente",
    "Moeda": "moeda",
    "Valor ME": "valor_me",
    "Taxa Cliente": "taxa_cliente",
    "PTAX Ref.": "ptax",
    "Valor R$": "valor_brl",
    "Spread R$": "spread_brl",
    "Spread %": "spread_frac",
    "Spread Estimado R$ (D-1)": "spread_estimado_brl",
    "IOF R$": "iof_brl",
    "Status Compliance": "status_compliance",
    "Observação": "observacao",
}


def _ler_email(path: Path):
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    corpo = ""
    anexo = None
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        fn = part.get_filename()
        if fn and fn.lower().endswith(".xlsx"):
            anexo = (fn, part.get_payload(decode=True))
        elif part.get_content_type() == "text/plain":
            corpo += part.get_content()
    if anexo is None:
        raise ValueError(f"{path.name}: nenhum anexo .xlsx encontrado")
    return msg, corpo, anexo


def carregar(path: Path) -> tuple[pd.DataFrame, dict]:
    msg, corpo, (anexo_nome, anexo_bytes) = _ler_email(path)
    wb = openpyxl.load_workbook(io.BytesIO(anexo_bytes), data_only=True)
    ws = wb.worksheets[0]

    header_idx, header_row = None, None
    linhas, rodape = [], {}
    for row in ws.iter_rows():
        vals = [c.value for c in row]
        if header_idx is None:
            if any(str(v).strip() == "Nº Operação" for v in vals if v is not None):
                header_idx = {str(v).strip(): i for i, v in enumerate(vals) if v is not None}
                header_row = row[0].row
            continue
        primeiro = vals[0]
        if primeiro is None:
            continue
        s = str(primeiro).strip()
        if re.match(r"^[A-Z]{2}-\d{4}-\d+$", s):
            reg = {canon: vals[header_idx[orig]] if orig in header_idx else None for orig, canon in COLUNAS.items()}
            reg["linha_anexo"] = row[0].row
            linhas.append(reg)
        elif s.endswith(":"):  # rodapé: 'Total de operações:', 'Spread total R$:'
            rodape[s.rstrip(":").strip()] = vals[1]

    df = pd.DataFrame(linhas)
    df["num_operacao"] = df["num_operacao"].astype(str).str.strip()
    df["cnpj"] = df["cnpj_cliente"].map(cnpj)
    for c in ["valor_me", "taxa_cliente", "ptax", "valor_brl", "spread_brl", "spread_frac", "spread_estimado_brl", "iof_brl"]:
        df[c] = df[c].map(dec)
    df["spread_pct"] = df["spread_frac"].map(lambda x: None if x is None else x * 100)
    df["data_contratacao"] = pd.to_datetime(df["data_contratacao"])
    df["data_liquidacao"] = pd.to_datetime(df["data_liquidacao"])
    df["observacao"] = df["observacao"].fillna("")
    df["arquivo_origem"] = f"{path.name}>{anexo_nome}"
    df["ref_origem"] = df["num_operacao"]
    df["duplicado"] = df["num_operacao"].duplicated(keep="first")

    m = re.search(r"participa\w*\s+de\s+(\d+(?:[.,]\d+)?)\s*%", corpo, flags=re.I)
    m_cnpj = re.search(r"Ponte C\w+mbio S\.A\.\s*-\s*CNPJ\s*([\d./-]+)", corpo)
    meta = {
        "assunto": str(msg["subject"]),
        "data_email": str(msg["date"]),
        "anexo": anexo_nome,
        "linha_cabecalho": header_row,
        "rodape": rodape,
        "participacao_pct_email": dec(m.group(1).replace(",", ".")) if m else None,
        "ponte_cnpj": cnpj(m_cnpj.group(1)) if m_cnpj else None,
        "corpo": corpo,
    }
    return df, meta
