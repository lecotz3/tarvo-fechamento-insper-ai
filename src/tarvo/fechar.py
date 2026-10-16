"""Fechamento mensal da Tarvo em um comando.

    python -m tarvo.fechar --dados data/set2026 --saida saida

Lê os arquivos como chegam, calcula, valida e grava os CSVs em saida/.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import pandas as pd

from . import checkout, lojistas
from .loaders import carregar_tudo
from .resultado import Resultado
from .util import write_csv
from .validar import validar

RAIZ = Path(__file__).resolve().parents[2]

SAIDAS = {
    "comissoes": ("comissoes_por_lojista.csv", ["id_saida", "cnpj", "lojista", "linha_negocio", "comissao_brl"]),
    "divergencias": ("divergencias_taxa.csv", ["id_saida", "cnpj", "linha_negocio", "ref_origem",
                                               "taxa_contratada_pct", "taxa_aplicada_pct", "diferenca_brl"]),
    "notas": ("notas_a_emitir.csv", ["id_saida", "tomador_cnpj", "tomador", "linha_negocio", "valor_brl",
                                     "discriminacao"]),
    "lancamentos": ("lancamentos_classificados.csv", ["id_saida", "banco", "ref_origem", "data", "descricao",
                                                      "valor", "conta_codigo", "metodo", "confianca"]),
    "pendencias": ("pendencias.csv", ["id_saida", "tipo", "ref_origem", "valor_brl", "motivo", "quem_decide"]),
    "rastro": ("rastro.csv", ["id_saida", "arquivo_origem", "ref_origem", "valor"]),
}


def gravar(res: Resultado, saida: Path) -> None:
    for attr, (arquivo, obrig) in SAIDAS.items():
        linhas = getattr(res, attr)
        df = pd.DataFrame(linhas) if linhas else pd.DataFrame(columns=obrig)
        extras = [c for c in df.columns if c not in obrig]
        write_csv(df[obrig + extras], saida / arquivo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dados", type=Path, default=RAIZ / "data" / "set2026")
    ap.add_argument("--saida", type=Path, default=RAIZ / "saida")
    ap.add_argument("--config", type=Path, default=RAIZ / "config")
    a = ap.parse_args(argv)

    prem = tomllib.loads((a.config / "premissas.toml").read_text(encoding="utf-8"))
    fontes = carregar_tudo(a.dados)
    cad = lojistas.montar(fontes.taxas, a.config / "de_para_ec.csv")
    res = Resultado()

    det = checkout.processar(fontes.orbe, cad, prem, res)

    erros = validar(res, fontes, det, prem["checkout"]["base_comissao"])
    gravar(res, a.saida)
    write_csv(det, a.saida / "detalhe" / "detalhe_checkout.csv")
    (a.saida / "log_validacao.txt").write_text("\n".join(res.log) + "\n", encoding="utf-8")

    print("\n".join(res.log))
    print(f"\nComissões: {len(res.comissoes)} | Divergências: {len(res.divergencias)} | "
          f"Notas: {len(res.notas)} | Lançamentos: {len(res.lancamentos)} | Pendências: {len(res.pendencias)} | "
          f"Rastro: {len(res.rastro)} linhas")
    if erros:
        print(f"\n{len(erros)} ERRO(S) DE VALIDAÇÃO — não use a saída antes de corrigir.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
