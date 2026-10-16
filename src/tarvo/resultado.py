"""Acumula as saídas, o rastro e as pendências de todos os motores."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Resultado:
    comissoes: list[dict] = field(default_factory=list)
    divergencias: list[dict] = field(default_factory=list)
    notas: list[dict] = field(default_factory=list)
    lancamentos: list[dict] = field(default_factory=list)
    pendencias: list[dict] = field(default_factory=list)
    rastro: list[dict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def rastrear(self, id_saida: str, arquivo_origem: str, ref_origem: str, valor: Decimal, **extra) -> None:
        self.rastro.append({"id_saida": id_saida, "arquivo_origem": arquivo_origem,
                            "ref_origem": ref_origem, "valor": valor, **extra})

    def pendencia(self, tipo: str, ref_origem: str, valor_brl: Decimal | None, motivo: str, quem_decide: str,
                  origens: list[tuple[str, str, Decimal]] | None = None, **extra) -> str:
        """Registra uma pendência. `origens` = linhas (arquivo, ref, valor) que compõem valor_brl."""
        id_saida = f"PEN-{len(self.pendencias) + 1:03d}"
        self.pendencias.append({"id_saida": id_saida, "tipo": tipo, "ref_origem": ref_origem,
                                "valor_brl": valor_brl, "motivo": motivo, "quem_decide": quem_decide, **extra})
        if valor_brl is not None:
            for arq, ref, v in (origens or []):
                self.rastrear(id_saida, arq, ref, v)
        return id_saida
