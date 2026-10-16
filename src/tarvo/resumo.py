"""Resumo do fechamento em português, para a analista e o CFO. Todo número sai das saídas já validadas."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .resultado import Resultado

ZERO = Decimal("0")


def brl(v: Decimal) -> str:
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def gerar(res: Resultado, competencia: str, path: Path) -> None:
    com = defaultdict(lambda: ZERO)
    for c in res.comissoes:
        com[c["linha_negocio"]] += c["comissao_brl"]
    div = defaultdict(lambda: ZERO)
    ndiv = defaultdict(int)
    for d in res.divergencias:
        div[d["linha_negocio"]] += d["diferenca_brl"]
        ndiv[d["linha_negocio"]] += 1
    nf_total = sum((n["valor_brl"] for n in res.notas), ZERO)
    metodos = defaultdict(int)
    for l in res.lancamentos:
        metodos[l["metodo"]] += 1

    L = [f"# Fechamento Tarvo: competência {competencia}", "",
         "> Gerado automaticamente a partir dos arquivos do mês. Cada número abaixo tem rastro até a linha de origem "
         "em `rastro.csv`.", "",
         "## Receita do mês (comissões)", "",
         "| Linha de negócio | Comissão | Lojistas |", "|---|---:|---:|"]
    for linha in ("CHECKOUT", "REMESSA"):
        n = sum(1 for c in res.comissoes if c["linha_negocio"] == linha)
        L.append(f"| {linha.title()} | {brl(com[linha])} | {n} |")
    L += [f"| **Total** | **{brl(sum(com.values(), ZERO))}** | |", "",
          f"**Notas fiscais a emitir:** {len(res.notas)}, somando {brl(nf_total)}.", ""]
    rem = [n for n in res.notas if n["linha_negocio"] == "REMESSA"]
    if rem:
        L += [f"A NF de remessa ({brl(rem[0]['valor_brl'])}) vai para **{rem[0]['tomador']}**: o repasse da "
              f"participação só é pago depois que a Ponte recebe a nota.", ""]

    L += ["## Dinheiro em jogo", "",
          "| Item | Valor | O que fazer |", "|---|---:|---|"]
    for linha, parceiro in (("CHECKOUT", "Orbe"), ("REMESSA", "Ponte")):
        if ndiv[linha]:
            L.append(f"| Taxa cobrada acima do contrato ({linha.lower()}, {ndiv[linha]} transações) | {brl(div[linha])} "
                     f"| Devolver ao lojista e pedir à {parceiro} a correção do cadastro |")
    por_tipo = defaultdict(lambda: [0, ZERO])
    for p in res.pendencias:
        por_tipo[p["tipo"]][0] += 1
        por_tipo[p["tipo"]][1] += p["valor_brl"] or ZERO
    rotulos = {
        "OPERACAO_DUPLICADA": "Operação duplicada no relatório da Ponte (participação que seria contada em dobro)",
        "SPREAD_NEGATIVO": "Spreads negativos da Ponte (participação negativa, fora da comissão até decisão)",
        "SEM_TAXA_CONTRATADA": "Taxas cobradas de lojista sem contrato na planilha",
        "CREDITO_NAO_IDENTIFICADO": "Crédito sem pagador identificado (Aurora)",
        "DEVOLUCAO_PIX": "Devolução de PIX de lojista a esclarecer (Aurora)",
        "APORTE_SEM_REMESSA": "Aporte de lojista sem remessa correspondente (Meridiano)",
    }
    for tipo, rot in rotulos.items():
        if tipo in por_tipo:
            n, v = por_tipo[tipo]
            L.append(f"| {rot} ({n}) | {brl(v)} | Ver `pendencias.csv` |")

    L += ["", "## Pendências por responsável", ""]
    por_dono = defaultdict(list)
    for p in res.pendencias:
        por_dono[p["quem_decide"]].append(p)
    for dono, ps in sorted(por_dono.items(), key=lambda x: -len(x[1])):
        L.append(f"**{dono}** ({len(ps)})")
        for p in ps:
            v = f" | {brl(p['valor_brl'])}" if p["valor_brl"] is not None else ""
            L.append(f"- `{p['id_saida']}` {p['tipo']} | {p['ref_origem']}{v}")
        L.append("")

    L += ["## Lançamentos bancários", "",
          f"{len(res.lancamentos)} lançamentos classificados: {metodos['REGRA']} por regra, {metodos['IA']} por IA, "
          f"{metodos['HUMANO']} aguardando uma pessoa.", "",
          "## Checagens automáticas", ""] + [f"- {m}" for m in res.log if m.startswith(("OK", "ERRO"))]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
