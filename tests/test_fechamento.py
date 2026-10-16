"""Testes com números-âncora verificados à mão no data pack de set/2026.

Rodar: PYTHONPATH=src python -m pytest -q
"""
from __future__ import annotations

import shutil
import tomllib
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tarvo import checkout, conciliacao, lancamentos, lojistas, notas, pendencias, remessa
from tarvo.fechar import main
from tarvo.loaders import carregar_tudo
from tarvo.resultado import Resultado
from tarvo.util import cnpj, taxa_pct, valor_taxa
from tarvo.validar import validar

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "set2026"
CONFIG = RAIZ / "config"


@pytest.fixture(scope="module")
def rodada():
    prem = tomllib.loads((CONFIG / "premissas.toml").read_text(encoding="utf-8"))
    f = carregar_tudo(DADOS)
    cad = lojistas.montar(f.taxas, CONFIG / "de_para_ec.csv")
    res = Resultado()
    det = checkout.processar(f.orbe, cad, prem, res)
    det_rem = remessa.processar(f.ponte, f.ponte_meta, cad, prem, res)
    notas.processar(res, prem, f.ponte_meta, "09/2026")
    chaves = lancamentos.chaves_lojistas(f.taxas["lojista_planilha"], f.orbe["nome_estabelecimento"],
                                         f.ponte["cliente"], cad.nome.values())
    lancamentos.processar([f.aurora, f.meridiano], lancamentos.carregar_regras(CONFIG / "regras_contas.csv"),
                          chaves, res)
    conciliacao.processar(f.ponte, f.meridiano, res)
    pendencias.processar(res, cad, set(det["cnpj"].dropna()) | set(det_rem["cnpj"].dropna()))
    erros = validar(res, f, det, prem["checkout"]["base_comissao"])
    return f, res, det, det_rem, erros


def test_utilitarios():
    assert cnpj(3229837000103) == "03229837000103"
    assert cnpj("22.224.579/0001-09") == "22224579000109"
    assert taxa_pct("1,49%") == (Decimal("1.49"), None)
    assert taxa_pct(0.0149) == (Decimal("1.49"), None)
    assert taxa_pct("padrão") == (None, "PADRAO")
    assert valor_taxa(Decimal("608.88"), Decimal("2.69")) == Decimal("16.37")      # trunca, não arredonda
    assert valor_taxa(Decimal("-4049.29"), Decimal("3.19")) == Decimal("-129.17")  # em direção a zero


def test_leitores(rodada):
    f, *_ = rodada
    assert len(f.orbe) == 1943
    assert len(f.ponte) == 233 and f.ponte["duplicado"].sum() == 1
    assert len(f.aurora) == 84 and f.aurora["ref_origem"].iloc[0] == "L9" and f.aurora["ref_origem"].iloc[-1] == "L92"
    assert len(f.meridiano) == 100
    assert f.ponte_meta["participacao_pct_email"] == Decimal("50")
    assert f.ponte_meta["ponte_cnpj"] == "75374179000146"


def test_validacao_sem_erros(rodada):
    *_, erros = rodada
    assert erros == []


def test_divergencias_checkout(rodada):
    _, res, *_ = rodada
    chk = [d for d in res.divergencias if d["linha_negocio"] == "CHECKOUT"]
    assert len(chk) == 92
    assert sum(d["diferenca_brl"] for d in chk) == Decimal("1576.23")
    rota = [d for d in chk if d["cnpj"] == "95927868000148"]
    assert len(rota) == 87 and min(d["data"] for d in rota).isoformat() == "2026-09-12"
    bridge = [d for d in chk if d["cnpj"] == "22224579000109"]
    assert len(bridge) == 5 and all(d["data"].isoformat() >= "2026-09-15" for d in bridge)


def test_divergencias_remessa(rodada):
    _, res, *_ = rodada
    rem = [d for d in res.divergencias if d["linha_negocio"] == "REMESSA"]
    assert {d["cnpj"] for d in rem} == {"17217888000111"}  # só Mundo Aberto (1,5% x 1,2%)
    assert len(rem) == 23


def test_remessa(rodada):
    _, res, _, det_rem, _ = rodada
    rem = [c for c in res.comissoes if c["linha_negocio"] == "REMESSA"]
    assert len(rem) == 14
    assert det_rem["situacao"].value_counts().to_dict() == {"OK": 228, "SPREAD_NEGATIVO": 4, "DUPLICADO": 1}
    total = sum(c["comissao_brl"] for c in rem)
    assert abs(total - Decimal("39542.88")) <= Decimal("0.07")  # 50% × spread positivo único, ± arredondamento por lojista


def test_notas(rodada):
    _, res, *_ = rodada
    ponte = [n for n in res.notas if n["linha_negocio"] == "REMESSA"]
    assert len(ponte) == 1 and ponte[0]["tomador_cnpj"] == "75374179000146"
    assert len([n for n in res.notas if n["linha_negocio"] == "CHECKOUT"]) == 22


def test_lancamentos(rodada):
    _, res, *_ = rodada
    assert len(res.lancamentos) == 184
    assert all(l["conta_codigo"] for l in res.lancamentos)
    por_ref = {l["ref_origem"]: l for l in res.lancamentos}
    assert por_ref["L9"]["conta_codigo"] == "1.1.03.001"
    assert por_ref["L50"]["conta_codigo"] == "1.1.09.002"
    assert por_ref["MRD2026090132"]["conta_codigo"] == "1.1.03.002"


def test_pendencias_chave(rodada):
    _, res, *_ = rodada
    tipos = [p["tipo"] for p in res.pendencias]
    for t in ("SEM_TAXA_CONTRATADA", "OPERACAO_DUPLICADA", "SPREAD_NEGATIVO", "CREDITO_NAO_IDENTIFICADO",
              "APORTE_SEM_REMESSA", "CONDICAO_COMERCIAL_NAO_REGISTRADA"):
        assert t in tipos, t
    assert tipos.count("SPREAD_NEGATIVO") == 4


def test_roda_em_outubro_sem_retrabalho(tmp_path):
    """Simula outubro: mesmos formatos, nomes de arquivo diferentes, pasta nova."""
    out = tmp_path / "out2026"
    out.mkdir()
    for p in DADOS.iterdir():
        shutil.copy(p, out / p.name.replace("set2026", "out2026").replace("092026", "102026"))
    saida = tmp_path / "saida"
    assert main(["--dados", str(out), "--saida", str(saida), "--config", str(CONFIG)]) == 0
    ref = pd.read_csv(RAIZ / "saida" / "comissoes_por_lojista.csv", sep=";", dtype=str)
    novo = pd.read_csv(saida / "comissoes_por_lojista.csv", sep=";", dtype=str)
    assert ref[["cnpj", "linha_negocio", "comissao_brl"]].equals(novo[["cnpj", "linha_negocio", "comissao_brl"]])


def test_ia_baixa_confianca_vira_pendencia():
    """Caminho da IA sem chamar a API: lançamento sem regra + sugestão com confiança baixa -> pendência."""
    from datetime import datetime
    ext = pd.DataFrame([{"banco": "AURORA", "ref_origem": "L999", "data": datetime(2026, 10, 5),
                         "descricao": "PIX RECEBIDO FULANO DE TAL", "valor": Decimal("100.00"),
                         "arquivo_origem": "extrato_teste.csv"}])
    regras = lancamentos.carregar_regras(CONFIG / "regras_contas.csv")
    res = Resultado()
    fake = lambda l: {"conta_codigo": "1.1.09.002", "confianca": 0.4, "justificativa": "pagador desconhecido"}
    lancamentos.processar([ext], regras, set(), res, classificador_ia=fake)
    assert res.lancamentos[0]["metodo"] == "IA" and res.lancamentos[0]["conta_codigo"] == "1.1.09.002"
    assert [p["tipo"] for p in res.pendencias] == ["LANCAMENTO_BAIXA_CONFIANCA"]
