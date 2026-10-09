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

## Aba "Ao vivo" (precificação do under limite)

- **O mercado é sempre "não sai mais nenhum gol"** — o mesmo dos backtests. A linha é sempre `placar + 0,5` e o horizonte é o fim do período: **HT** até o intervalo (fim 47', com acréscimo) ou **FT** até o fim do jogo (fim 95'). O período sai do minuto (`<45` = HT) e pode ser fixado à mão nos chips. Não existe mais campo de linha livre: precificar `under 2.5` era outro mercado e foi o que produzia divergências de −39% contra o backtest.
- **Estimador primário: os backtests.** As 27.243 entradas medem exatamente esse mercado, inclusive efeitos de placar que o Poisson não enxerga (em 1x0/0x1 sai *mais* gol que o modelo prevê — time atrás se expõe; em 1x1 sai *menos*). A célula `(período, placar, minuto)` vem de `pontosCalc` + `interpola`, igual à calculadora.
- **Condicionamento pelo jogo.** O backtest é incondicional quanto à qualidade ofensiva da partida, então o λ da célula é multiplicado por `(λ_restante(λ_do_jogo) / λ_restante(λ_médio))^k`. O λ do jogo sai do **over 2.5 projetado** do Futodds (sem margem) ou da odd over 2.5 pré-live. O expoente `k = LV_PRIOR / (LV_PRIOR + F(t))` amortece o ajuste conforme o jogo anda: sem ele, com 0 gols a razão entre posteriores é sempre `λ_jogo/λ_amostra`, ou seja o placar observado não descontaria nada do que o mercado previu antes da bola rolar. Aos 63' o peso do pré-jogo é 0,75. **Esta correção é escolha de modelagem, não medida** — os CSVs atuais não exportam `ou25_pre` (`stats_cols` está vazio), então não há como validá-la com os dados que existem; é a Fase 3 do roadmap.
- **Mercado da exchange como juiz.** Quando a colagem traz o par over/under da linha, a P implícita sem overround aparece como métrica e é contra **ela** que a divergência é medida — não contra o backtest cru. Caso que motivou: Tauro × Chorrillo 0x0 aos 63', backtest cru 43,0%, mercado 26,0%, modelo 22,2%. O aviso antigo acusava "104% de divergência" contra o backtest quando o modelo é que estava perto de quem sabe.
- **Fallback Poisson calibrado**, usado só onde não há célula: perfil de intensidade `r(t) = A + B·t` **ajustado contra os próprios 27k backtests** (fatia de gols do 1º tempo = 45,8%, contra 45% de livro) e correção bayesiana Gamma-Poisson pelo placar observado (`LV_PRIOR = 2` jogos). Aderência medida: erro médio ponderado **2,6%**, 24 de 26 células dentro de ±10%; nos 8 buckets de 0x0, ±2%.
- **Odd live** sai da tabela certa da exchange: *Primeiro Tempo* se HT, *Tempo Regulamentar* se FT, linha `placar + 0,5`, coluna **under back**.

### Algoritmo do Jev

- O Jev **não faz conta**. Ele classifica o contexto que o backtest não mede, em 5 perguntas: `ameaca` (baixa/moderada/alta), `ritmo` (lento/normal/acelerado), `perfil` (truncado/equilibrado/aberto), `urgencia` (noul) e `evento_critico` (noul).
- **Combinação em log(λ), somando — não multiplicando.** Cada resposta vira `z ∈ [-1,+1]` pela diferença das pontas da distribuição (o meio não desloca nada), ponderada por `LV_PESOS` (ameaça 0,26 · evento 0,22 · ritmo 0,15 · perfil 0,14 · urgência 0,12). Propriedade que motiva o desenho: **quando o Jev fica indeciso a distribuição se achata, os z tendem a zero e o ajuste some sozinho** — com respostas 33/33/33 o multiplicador dá ×1,04. Produto de fatores, como era antes, compunha extremos em vez de encolher.
- `evento_critico` é unilateral (só empurra λ para cima): a ausência de pênalti/expulsão é o caso normal, não uma evidência a favor do under.
- Teto `LV_TETO = 0,62` em log → multiplicador entre **×0,54 e ×1,86**. O Jev corrige contexto; não reescreve a estimativa empírica.
- **Vetos**, que valem mesmo com EV positivo: `ameaca.alta ≥ 55%` ou `evento_critico ≥ 60%` → veredito "NÃO ENTRAR".
- O estado enviado inclui os pares **casa×fora** (que a soma dos campos esconde), os patamares de over do Fut Odds, e `outros_dados` — pares `<n> RÓTULO <n>` sem campo próprio no formulário (Ataques, No Alvo, Cartões Amarelos). **A varredura fica presa ao bloco de Stats/Pressão**: solta no texto inteiro ela lia o cabeçalho de odds e os rótulos de aba como estatística (`Empate 2.36×3.40`, `Geral 365×5`, `Min 10×15`) e mandava isso ao Jev como se fosse dado de jogo.
- **Troca de período refaz a odd** (`lvEscolheOdd`): a mesma linha tem preço diferente em HT e FT, então mudar o chip depois de colar reescolhe o valor na tabela certa. Se a colagem não trouxe a tabela daquele período, a odd é marcada como não confirmada e o EV+ trava.

## Aba "Scanner" (varredura da Tabela Live)

- Cola a **Tabela Live** inteira do Fut Odds (Ctrl+A na tela) e precifica o under limite de **todos os jogos de uma vez**, nos dois períodos. Não há odd oferecida nessa tela: a saída é a **odd justa** e a **mínima com margem** — o preço que vale caçar na casa.
- **Parser:** a âncora é o token de minuto (`HT`, `28'`, `-'`). Antes dele, desde o separador de linha anterior, vêm times e placar; depois vêm os 43 valores (19 pares casa/fora + 5 odds pré-live `OCASA/OEMPA/OFORA/OV25/UN25`). Preservar os separadores importa: sem eles o cabeçalho da tabela entra no bloco de times do primeiro jogo e ele some. Jogos que não começaram (`-'`, `0'`) são listados como ignorados, não descartados em silêncio.
- **Placar:** é o último número do grupo de cada time — o campo varia de 2 a 3 caixas conforme a linha. Confira na tela; se o Fut Odds mudar essa coluna, é aqui que quebra.
- **λ do jogo** sai do par `OV25`/`UN25` sem overround; sem eles, cai para a média da amostra (2,52) e a linha é marcada.
- **Ordenação pela janela de backtest** (HT 15/25/35/42, FT 60/70/80/85): é só nelas que o edge está documentado, então a coluna "Janela" mostra `agora` ou `em N'` e a tabela ordena por isso. Clicar no jogo o leva para a aba **Ao vivo** com os campos preenchidos, onde o Jev entra na conta — a odd live fica deliberadamente por confirmar, porque a Tabela Live não a traz.
- **Fora da faixa medida, a base passa a ser o Poisson calibrado.** Antes a célula da ponta era aplicada a um minuto que ela não cobre: para um 1x0 no intervalo, usar a célula do minuto 60 ignora 15 minutos de jogo e derruba a justa de **5,80 para 3,32**. A mesma regra foi aplicada à aba Ao vivo.

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
