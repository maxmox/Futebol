# Under Limite — Estado do projeto

## O que existe

- **Site publicado:** https://maxmox.github.io/Futebol/ (GitHub Pages, branch `main`)
- **Repo:** https://github.com/maxmox/Futebol.git
- **Fonte local:** pasta `Trade` — `index.html` (gerado, não editar à mão), `analisar_backtests.py` (gera o site)
- **Workflow:** colocar CSVs nas pastas `under limite ht/ft entrada min X ao Y/` → `python analisar_backtests.py` → `git add index.html && git commit && git push`

## Estrutura técnica

- `analisar_backtests.py` lê todos os CSVs das pastas, remove duplicatas, e embute os dados como JSON em `index.html` (arquivo único, sem dependências).
- Dados embutidos: `rows = [bucketIdx, minuto, odd, placarIdx, win, extras?]`, `buckets` (período ht/ft, faixa de minuto, n), `stats_cols` (colunas extras encontradas nos CSVs).
- **Colunas extras:** qualquer coluna além do padrão vira stat embutida (ex.: `CS Casa %`, `Win Fora %`, `OU 2.5 Pré`) — nomes normalizados para minúsculas/underscore. A seção **Análise por estatística** do site segmenta o ROI por tercil da stat (mín. 150 entradas com a stat preenchida).
- Página tem 4 seções: **Consulta rápida** (calculadora com chips; interpola winrate × minuto por período+placar, n≥50 por placar senão usa taxa geral), **Mapa de valor** (grade entrada×placar, toque abre detalhe com "lucrativo a partir de odd ≈ X" + ROI por faixa de odd), **Análise por estatística** (só aparece quando há stats nos CSVs), **Cobertura e lacunas** (gerada automaticamente dos buckets: janelas sem dados, placares fracos, extrapolações).
- Constantes: STAKE=10, comissão 6,5%, alerta de odd suspeita +15% sobre a justa.
- **Convenção de pastas:** `Under Limite <ht|ft> - <descrição> - min X ao Y [- sufixo livre]`. O sufixo (ex.: "stats pre-live", "post gol") entra no label do bucket no mapa.

## Backtests atuais (27.243 entradas, gerado 2026-10-05)

HT: 15-16 (n=3.780), 25-26 (3.709), 35-36 (2.828), 42-43 (2.488, dois CSVs fundidos, focado em 0x0)
FT: 60-61 (3.182), 70-71 (3.351), 80-81 (3.060), 85-86 (2.734)
FT 2 gols de diferença (2x0/0x2): 70-71 (n=730), 80-81 (766)
FT goleadas (3x0/0x3 → Under 3.5; 3x1/1x3 → Under 4.5): 80-81 (615)
Pastas com placares no nome ("Under Limite ft - Placares ... - min X ao Y") são reconhecidas pelo script; o mercado muda conforme o placar, mas a aposta é sempre "não sai mais gol".

## Achados-chave (para referência futura)

- FT 60-61: só 0x0 lucrativo (+6,7%); 1x0/0x1/1x1 negativos.
- Edge cresce no fim do jogo; início de jogo/2º tempo ≈ breakeven.
- Odd muito alta não salva cenário ruim (FT 60-61 1x1 com odd ≥3,5: ROI −30%).
- 2 gols de diferença: todos os cenários positivos — FT 70-71: 2x0 +1,0%, 0x2 +8,7%; FT 80-81: 2x0 +6,2%, 0x2 +8,7%. Visitante vencendo por 2 rende mais que mandante.
- Goleadas FT 80-81: todas positivas (+3,1% a +6,4%) — under limite em jogo decidido é lucrativo em geral.

## Limitações conhecidas / próximos passos possíveis

- Interpolação linear entre buckets; janelas sem dados listadas na seção Cobertura.
- HT placares 1x0/0x1/1x1 têm amostra quase nula nos min 15-36 (filtros do backtest) — calculadora usa taxa geral nesses casos.
- **Roadmap de exploração (plano aprovado 2026-10-05):**
  - Fase 1 — backtests de lacuna/confirmação: FT 85-86 (2x0/0x2 e goleadas), FT 0x0 min 75-76 e 90-91, HT 0x0 min 30-31 e 40-41. Exportar já com colunas de stats pré-live.
  - Fase 2 — backtests de surpresa: flag de gol recente (`gol_ha`, `fav_marcou`) para testar o exagero de reação do mercado a gols.
  - Fase 3 — cruzar células validadas com `ou25_pre`, `cs_casa/cs_fora`, `win_casa/win_fora` (seção Análise por estatística), máx. 3 stats por célula para conter múltiplos testes.
- Ideias futuras: filtros por liga, curva de comissão configurável.
