"""Extratos bancários: Aurora (CSV do internet banking) e Meridiano (OFX SGML)."""
from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ..util import br_num


def _ler_texto(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path.name}: encoding não reconhecido")


def carregar_aurora(path: Path) -> pd.DataFrame:
    """ref_origem = número da linha física no arquivo (L10, L11, ...), como pede o enunciado."""
    linhas = list(csv.reader(_ler_texto(path).splitlines(), delimiter=";"))
    cab = None
    regs = []
    for n, row in enumerate(linhas, start=1):
        if cab is None:
            if row and row[0].strip().lower() == "data" and any("valor" in c.lower() for c in row):
                cab = [c.strip() for c in row]
            continue
        if len(row) < 4 or not re.match(r"^\d{2}/\d{2}/\d{4}$", row[0].strip()):
            continue  # linhas em branco, SALDO FINAL, avisos de rodapé
        desc = row[1].strip()
        valor = br_num(row[3])
        if valor is None or desc.upper().startswith("SALDO"):
            continue  # SALDO ANTERIOR não é lançamento
        regs.append({
            "banco": "AURORA",
            "ref_origem": f"L{n}",
            "data": datetime.strptime(row[0].strip(), "%d/%m/%Y"),
            "descricao": desc,
            "documento": row[2].strip(),
            "valor": valor,
            "saldo": br_num(row[4]) if len(row) > 4 else None,
        })
    if cab is None:
        raise ValueError(f"{path.name}: cabeçalho 'Data;Lançamento;...' não encontrado")
    df = pd.DataFrame(regs)
    df["arquivo_origem"] = path.name
    return df


def carregar_meridiano(path: Path) -> pd.DataFrame:
    """OFX 1.02 (SGML, tags sem fechamento). ref_origem = FITID."""
    txt = _ler_texto(path)
    regs = []
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", txt, flags=re.S):
        campos = dict(re.findall(r"<([A-Z]+)>([^<\r\n]*)", bloco))
        regs.append({
            "banco": "MERIDIANO",
            "ref_origem": campos["FITID"].strip(),
            "data": datetime.strptime(campos["DTPOSTED"][:8], "%Y%m%d"),
            "descricao": campos.get("MEMO", "").strip(),
            "documento": campos.get("CHECKNUM", "").strip(),
            "valor": Decimal(campos["TRNAMT"].strip()),
            "tipo_ofx": campos.get("TRNTYPE", "").strip(),
        })
    df = pd.DataFrame(regs)
    df["arquivo_origem"] = path.name
    m = re.search(r"<LEDGERBAL>\s*<BALAMT>([-\d.]+)", txt)
    df.attrs["saldo_final"] = Decimal(m.group(1)) if m else None
    df["duplicado"] = df["ref_origem"].duplicated(keep="first")
    return df


def carregar_plano(path: Path) -> pd.DataFrame:
    df = pd.read_csv(io_text(path), sep=";", dtype=str, keep_default_na=False)
    df.columns = [c.strip().upper() for c in df.columns]
    return df


def io_text(path: Path):
    import io
    return io.StringIO(_ler_texto(path))
