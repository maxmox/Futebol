# jev_teste.py
# Testa decisoes do Jev (TypeSafe AI) direto da API oficial, fora do navegador.
# A API da TypeSafe bloqueia chamadas de navegador (CORS) — por isso o site usa
# a OpenRouter; este script serve para testar prompts/perguntas novos localmente.
#
# Uso (Git Bash):
#   export TYPESAFE_API_KEY="sua_chave"
#   python jev_teste.py "FT 80-81 placar 0x0, odd 1.55" "jogo truncado, sem pressao"
#
# A chave NUNCA deve ser gravada neste arquivo nem commitada.

import json
import os
import sys
import urllib.request

URL = "https://api.typesafe.ai/v1/systemone"

QUESTOES = {
    "risco": {
        "type": "choice",
        "instructions": "Qual o perfil de risco desta entrada under no mercado de gols, dado o cenario de backtest e o contexto ao vivo?",
        "criteria": {
            "baixo": "contexto consistente com jogo truncado, sem sinais de pressao ofensiva",
            "moderado": "alguma pressao, incerteza ou contexto vazio demais para cravar",
            "alto": "pressao ofensiva clara, chance clara, penalti, falta perigosa ou cartao vermelho",
        },
    },
    "pressao": {
        "type": "noul",
        "instructions": "O contexto ao vivo descreve pressao ofensiva relevante contra esta entrada under?",
    },
    "truncado": {
        "type": "noul",
        "instructions": "O contexto ao vivo indica jogo truncado de baixa intensidade, consistente com a entrada under?",
    },
}


def main():
    chave = os.environ.get("TYPESAFE_API_KEY", "")
    if not chave:
        raise SystemExit("Defina TYPESAFE_API_KEY (export TYPESAFE_API_KEY=...)")

    cenario = sys.argv[1] if len(sys.argv) > 1 else "FT 80-81 placar 0x0, odd 1.55"
    contexto = sys.argv[2] if len(sys.argv) > 2 else "sem contexto informado"

    state = {"cenario": cenario, "contexto_ao_vivo": contexto}
    corpo = json.dumps({"model": "jev-latest", "state": state, "questions": QUESTOES}).encode()

    req = urllib.request.Request(
        URL,
        data=corpo,
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dados = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Erro {e.code}: {e.read().decode()[:500]}")

    for nome, ans in dados.get("answers", {}).items():
        print(f"\n[{nome}]")
        if ans.get("type") == "choice":
            print(f"  escolha: {ans.get('choice')} (confianca {ans.get('confidence', 0):.2f})")
            for op, p in (ans.get("probabilities") or {}).items():
                print(f"    {op}: {p * 100:.0f}%")
        else:
            print(f"  noul: {ans.get('noul', 0):.2f}")
    uso = dados.get("usage", {})
    print(f"\ntokens de entrada: {uso.get('input_tokens')} · modelo: {dados.get('model')}")


if __name__ == "__main__":
    main()
