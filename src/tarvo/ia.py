"""Classificação por IA do resíduo do extrato (o que nenhuma regra de config/regras_contas.csv cobre).

Desligada por padrão: ative com `--ia`. Requer o pacote `anthropic` e credencial
(ANTHROPIC_API_KEY ou perfil `ant auth login`).

Garantias:
- a saída é JSON validado por schema (structured outputs) e `conta_codigo` só pode ser uma conta
  ANALÍTICA do plano (enum), então a IA não inventa conta;
- a IA nunca calcula valor: só sugere a conta de um lançamento que já existe;
- confiança abaixo do limite vira pendência para uma pessoa (ver lancamentos.py).
"""
from __future__ import annotations

import json

import pandas as pd

MODELO = "claude-opus-5-5"

SISTEMA = (
    "Você classifica lançamentos de extrato bancário de uma subadquirente brasileira (Tarvo Pagamentos) "
    "no plano de contas do ERP. Contexto: a Tarvo recebe da adquirente Orbe (TED) e repassa aos lojistas (PIX); "
    "na conta Meridiano recebe recursos de lojistas para remessas internacionais e liquida na Ponte Câmbio. "
    "Escolha a conta analítica mais adequada. Se o histórico não permitir identificar a natureza, use "
    "1.1.09.002 (créditos não identificados) para entradas e dê confiança baixa. Confiança entre 0 e 1: "
    "acima de 0.8 só quando o histórico deixa a natureza inequívoca."
)


def criar_classificador(plano: pd.DataFrame):
    """Devolve uma função lançamento -> {conta_codigo, confianca, justificativa} ou None se indisponível."""
    try:
        import anthropic
    except ImportError:
        return None, "pacote 'anthropic' não instalado (pip install anthropic)"

    analiticas = plano[plano["ACEITA_LANCTO"].str.upper() == "S"]
    contas = analiticas["COD_CONTA"].tolist()
    lista = "\n".join(f"{r.COD_CONTA} - {r.DESCRICAO} (natureza {r.NATUREZA})" for r in analiticas.itertuples())
    schema = {
        "type": "object",
        "properties": {
            "conta_codigo": {"type": "string", "enum": contas},
            "confianca": {"type": "number"},
            "justificativa": {"type": "string"},
        },
        "required": ["conta_codigo", "confianca", "justificativa"],
        "additionalProperties": False,
    }
    client = anthropic.Anthropic()

    def classificar(l) -> dict | None:
        try:
            resp = client.beta.messages.create(
                model=MODELO,
                max_tokens=2048,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
                system=SISTEMA + "\n\nPlano de contas (somente contas analíticas):\n" + lista,
                messages=[{"role": "user", "content":
                           f"Banco: {l['banco']}\nData: {l['data']:%Y-%m-%d}\nHistórico: {l['descricao']}\n"
                           f"Valor (R$, negativo = saída): {l['valor']}"}],
            )
        except anthropic.APIStatusError as e:
            print(f"[ia] erro da API ({e.status_code}) em {l['ref_origem']}: lançamento vai para pendência")
            return None
        except anthropic.APIConnectionError:
            print(f"[ia] sem conexão em {l['ref_origem']}: lançamento vai para pendência")
            return None
        if resp.stop_reason == "refusal":
            return None
        texto = next((b.text for b in resp.content if b.type == "text"), None)
        if not texto:
            return None
        d = json.loads(texto)
        d["confianca"] = max(0.0, min(1.0, float(d["confianca"])))
        return d

    return classificar, f"IA habilitada ({MODELO}) para lançamentos sem regra"
