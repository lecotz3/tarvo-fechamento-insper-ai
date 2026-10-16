"""Funções utilitárias: números no formato brasileiro, CNPJ, arredondamento e escrita das saídas."""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

CENTAVO = Decimal("0.01")


def br_num(s) -> Decimal | None:
    """'1.234,56' -> Decimal('1234.56'). Vazio -> None."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if not s:
        return None
    return Decimal(s.replace(".", "").replace(",", "."))


def dec(x) -> Decimal | None:
    """Converte float/int/str (formato com ponto) em Decimal sem herdar ruído binário."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    return Decimal(str(x))


def money(x: Decimal) -> Decimal:
    """Arredonda para centavos, meio para cima (uso geral)."""
    return x.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def valor_taxa(bruto: Decimal, taxa_pct: Decimal) -> Decimal:
    """Taxa em R$ do jeito que a Orbe calcula: bruto × taxa, TRUNCADO nos centavos (em direção a zero).

    Verificado: reproduz o valor_taxa das 1.943 linhas de set/2026. Arredondar (meio para cima)
    erraria 1.001 linhas por R$ 0,01 e geraria divergências falsas.
    """
    return (bruto * taxa_pct / 100).quantize(CENTAVO, rounding=ROUND_DOWN)


def cnpj(x) -> str | None:
    """Normaliza CNPJ para 14 dígitos: tira máscara e repõe zeros à esquerda perdidos no Excel."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, float):
        x = int(x)
    d = re.sub(r"\D", "", str(x))
    return d.zfill(14) if d else None


def taxa_pct(x) -> tuple[Decimal | None, str | None]:
    """Lê uma taxa da planilha e devolve (percentual, marcador).

    Aceita 0.0149 (fração), '1,49%' (texto), 'padrão' e vazio.
    Retorna o percentual (1.49) ou None. O marcador é 'PADRAO', 'VAZIO' ou None.
    """
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None, "VAZIO"
    if isinstance(x, (int, float)):
        return (Decimal(str(x)) * 100).quantize(Decimal("0.0001")).normalize(), None
    s = str(x).strip().lower()
    if not s:
        return None, "VAZIO"
    if s.startswith("padr"):
        return None, "PADRAO"
    if s.endswith("%"):
        return Decimal(s.rstrip("%").strip().replace(",", ".")).normalize(), None
    v = Decimal(s.replace(",", "."))
    return ((v * 100) if v < 1 else v).normalize(), None


def fmt_brl(x: Decimal | None) -> str:
    return "" if x is None else f"{money(x):.2f}"


def fmt_pct(x: Decimal | None) -> str:
    return "" if x is None else f"{x.quantize(Decimal('0.0001')).normalize():f}"


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """CSV no formato da correção automática: ';' separador, '.' decimal, UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(lambda v: f"{v:f}" if isinstance(v, Decimal) else v)
    out.to_csv(path, sep=";", index=False, encoding="utf-8", lineterminator="\n")


def find_file(pasta: Path, *padroes: str) -> Path:
    """Acha um arquivo da competência pelo padrão de nome (o nome muda a cada mês)."""
    for p in padroes:
        achados = sorted(pasta.glob(p))
        if achados:
            return achados[0]
    raise FileNotFoundError(f"Nenhum arquivo em {pasta} casa com {padroes}")
