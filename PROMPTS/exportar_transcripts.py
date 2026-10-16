"""Copia os transcripts do Claude Code deste projeto para PROMPTS/transcripts/.

O enunciado permite remover chaves de API e dados pessoais e proíbe qualquer outra edição.
Este script só mascara e-mails e padrões de chave/token. Todo o resto vai byte a byte.

Uso (rodar no fim do dia, depois da última sessão):
    python PROMPTS/exportar_transcripts.py
    python PROMPTS/exportar_transcripts.py --origem "C:/Users/<voce>/.claude/projects/<pasta-do-projeto>"
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PADROES = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "[CHAVE-REMOVIDA]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[TOKEN-REMOVIDO]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL-REMOVIDO]"),
]


def main() -> None:
    padrao_origem = Path.home() / ".claude" / "projects" / "C--Users-Leonardo-HACKATOn"
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", type=Path, default=padrao_origem)
    ap.add_argument("--destino", type=Path, default=Path(__file__).resolve().parent / "transcripts")
    a = ap.parse_args()
    a.destino.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(a.origem.glob("*.jsonl"))
    if not arquivos:
        raise SystemExit(f"Nenhum transcript .jsonl em {a.origem}")
    for f in arquivos:
        # newline="" nos dois lados: nenhuma conversão de fim de linha (o arquivo sai idêntico, salvo a máscara)
        with open(f, encoding="utf-8", errors="surrogateescape", newline="") as fh:
            txt = fh.read()
        n = 0
        for rx, sub in PADROES:
            txt, k = rx.subn(sub, txt)
            n += k
        with open(a.destino / f.name, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
            fh.write(txt)
        print(f"{f.name}: {n} trecho(s) mascarado(s)")


if __name__ == "__main__":
    main()
