# Under Limite — Estado do projeto

## O que existe

- **Site publicado:** https://maxmox.github.io/Futebol/ (GitHub Pages, branch `main`)
- **Repo:** https://github.com/maxmox/Futebol.git
- **Fonte local:** pasta `Trade` — `index.html` (gerado, não editar à mão), `analisar_backtests.py` (gera o site)
- **Workflow:** colocar CSVs nas pastas `under limite ht/ft entrada min X ao Y/` → `python analisar_backtests.py` → `git add index.html && git commit && git push`

## Estrutura técnica

- `analisar_backtests.py` lê todos os CSVs das pastas, remove duplicatas, e embute os dados como JSON em `index.html` (arquivo único, sem dependências).
- Dados embutidos: `rows = [bucketIdx, minuto, odd, placarIdx, win]`, `buckets` (período ht/ft, faixa de minuto, n).
- Página tem 3 seções: **Consulta rápida** (calculadora com chips; interpola winrate × minuto por período+placar, n≥50 por placar senão usa taxa geral), **Mapa de valor** (grade entrada×placar, toque abre detalhe com "lucrativo a partir de odd ≈ X" + ROI por faixa de odd), **Cobertura e lacunas** (gerada automaticamente dos buckets: janelas sem dados, placares fracos, extrapolações).
- Constantes: STAKE=10, comissão 6,5%, alerta de odd suspeita +15% sobre a justa, placares = ['0-0','1-0','0-1','1-1'].

## Backtests atuais (25.132 entradas, gerado 2026-09-29)

HT: 15-16 (n=3.780), 25-26 (3.709), 35-36 (2.828), 42-43 (2.488, dois CSVs fundidos, focado em 0x0)
FT: 60-61 (3.182), 70-71 (3.351), 80-81 (3.060), 85-86 (2.734)

## Achados-chave (para referência futura)

- FT 60-61: só 0x0 lucrativo (+6,7%); 1x0/0x1/1x1 negativos.
- Edge cresce no fim do jogo; início de jogo/2º tempo ≈ breakeven.
- Odd muito alta não salva cenário ruim (FT 60-61 1x1 com odd ≥3,5: ROI −30%).

## Limitações conhecidas / próximos passos possíveis

- Interpolação linear entre buckets; janelas sem dados listadas na seção Cobertura.
- HT placares 1x0/0x1/1x1 têm amostra quase nula nos min 15-36 (filtros do backtest) — calculadora usa taxa geral nesses casos.
- Ideias futuras: backtests em minutos faltantes (ex.: FT 75, HT 30), filtros por liga, curva de comissão configurável.
