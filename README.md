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

## Decisor de entrada (Jev)

- Seção do site que combina o cálculo determinístico de backtest (odd justa, mínima, ROI — mesmo motor da calculadora) com o modelo de decisão **Jev** (TypeSafe AI), que classifica o contexto ao vivo como guardrail.
- **Arquitetura:** os números são calculados em JS puro (o Jev é fraco em matemática); o Jev responde 3 perguntas numa chamada só (choice `risco` baixo/moderado/alto + noul `pressao` + noul `truncado`) e o código combina: `P(pressão) > 0,60` → EVITAR; risco alto → aguardar; risco baixo → veredito de backtest mantido.
- **Via de acesso:** a API oficial da TypeSafe **bloqueia navegador (CORS)** — o site chama o modelo exclusivamente pelo **relay Cloudflare Worker** (`relay_cloudflare.js`), que guarda a chave TypeSafe como secret no Worker (fora do repositório) e devolve a resposta com CORS liberado. A URL do relay vai embutida no site como padrão (`JEV_RELAY_PADRAO` no `analisar_backtests.py`) — funciona sem configurar nada. OpenRouter foi removida (2026-10): não há mais chamada direta nem chave no navegador.
- **Configuração:** aba "Conexão Jev" do site — botão de teste de conexão; campo de URL do relay só para o caso de redeploy do Worker (fica no localStorage do navegador, nunca no repositório).
- **`jev_teste.py`:** testa prompts/perguntas novos localmente com a chave TypeSafe (`export TYPESAFE_API_KEY=... && python jev_teste.py "<cenario>" "<contexto>"`) — a chave TypeSafe só funciona fora do navegador.
- Disclaimer na própria UI: o Jev classifica contexto, não prevê o jogo; nenhum modelo garante lucro.

## Aba "Ao vivo" (precificação do under)

- Aba ao lado do Dashboard: o usuário insere o estado do jogo (placar, minuto, odds live/pré + linha, probabilidades projetadas, indicadores de pressão APPM/CG/PI/xG, volume de jogo, contexto livre) e recebe **odd justa do under no momento**, **curva de queda da odd nos próximos 5 min** (%/min) e **veredito EV+ / limite / EV−**.
- **Motor:** Poisson com λ extraído da odd under pré-live (ou do % over 2.5 projetado, se informado) × decaimento `t^0,84`; o **Jev** classifica o contexto (ameaça baixa/moderada/alta, ritmo lento/normal/acelerado, noul truncado, noul pressão desbalanceada) e as probabilidades viram multiplicador sobre o λ (×0,55 a ×1,70). O Jev não faz conta — quem precifica é o código; o Jev ajusta o contexto que os backtests não medem.
- Mostra também o **comparador com backtest** (justa da célula do mapa vs justa do modelo+Jev, com % de divergência) quando existe célula para o placar/minuto.
- **Preenchimento rápido (colagem do Fut Odds):** o textarea no topo da aba lê o Ctrl+C da tela do jogo e preenche os campos sozinho (dispara no próprio `paste`; o botão "Preencher campos" é só reforço). É **acumulativo** — cada colagem escreve só o que reconhece e nunca limpa campo já preenchido, então basta colar as abas Press., Prob. (Match e Gols), Stats e Odds em sequência. Parser: `lvParse`/`lvColar` no `analisar_backtests.py`.
  - Mapeamento: minuto e placar do cabeçalho; `APPM/APPM10/CG/CG10/PI1/PI2/PI3` da aba Press.; posse, xG, atq. perigosos, finalizações e escanteios da Stats; `Casa/Empate/Fora (FT)` e `Over 2.5 FT` da Prob.; odd under da tabela Over/Under (linha que bate com o campo "Linha").
  - **Tabela Over/Under = odds de exchange.** Cada linha traz 4 preços: `over back, over lay, under back, under lay` (a 1ª de cada par é o back; o lay é sempre o maior). O campo "Odd live" recebe o **under back** da linha escolhida, que é o preço que se aposta; o lay aparece só no diagnóstico da colagem. A 1ª coluna é a linha de gols, sempre de 0,5 em 0,5.
  - **Indicadores de pressão são somados** (casa + fora), porque os patamares do Fut Odds são combinados — e é assim que o filtro `CG<=5 e PI1<50` deve ser lido. Os rótulos no formulário marcam "(soma)". O par original (`PI1 20×10 = 30`) vai no contexto do Jev, para ele enxergar o desbalanço que a soma esconde. `xG` também é soma.
  - **Patamares de over do Fut Odds** (`LV_PATAMAR`): PI1 70, PI2 12, PI3 8 combinados. Quando a soma passa do patamar, o contexto do Jev recebe "ACIMA do patamar de over (N)" — vira sinal qualitativo em vez de número solto.
  - Referência dos indicadores: PI1 = finalizações + posse nos últimos 10 min; PI2 = ataques perigosos e ausência de cantos nos últimos 10 min; PI3 = igual ao PI2 nos últimos 5 min; H2H = duelo estatística a estatística, 1 ponto para o vencedor de cada; xG é o da Bet365.
  - O contexto do Jev ganha um bloco `[auto]` com times, a frase de momento do Fut Odds e o balanço de pressão; o que você digitar à mão abaixo dele é preservado. Trocar de jogo zera o acumulado.
  - **Guarda da odd live** (2026-10-08): a odd live é a única entrada que o modelo não confere sozinho, e a sub-aba *Principais* do Fut Odds **não** traz a linha de gols — só *Odds → Over/Under* traz. Quando nenhuma colagem preencheu a odd live do jogo atual, ela continua no default (1.80) e o EV sai fantasiado. Agora: `lvOddDeColagem` marca a procedência (zera ao trocar de jogo), a mensagem da colagem avisa em amarelo, e **nenhum EV+ sai verde** enquanto a odd não for confirmada. Segunda checagem: o over 2.5 ao vivo do cabeçalho (`lvRefOver`) implica um under de mercado; se a odd informada passar 25% disso, o veredito também trava.
  - Não vem na colagem: **odd under pré-live** (o cabeçalho só traz o over) — mas com `Over 2.5 FT %` preenchido o motor usa o λ projetado, que é melhor.
- **Não validada em forward-test** — marcada como heurística na própria UI; calibração do multiplicador vem depois, com uso registrado.

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
