# analisar_backtests.py
# Le os CSVs de backtest das pastas "under limite ht/ft entrada min X ao Y"
# e gera a pagina index.html (site do GitHub Pages) com os dados embutidos.
#
# Uso:  python analisar_backtests.py
# Para atualizar o site com novos backtests, basta colocar os CSVs
# nas pastas e rodar este script de novo. Linhas duplicadas entre CSVs
# da mesma pasta sao removidas automaticamente.

import csv
import glob
import json
import os
import re

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(PASTA_BASE, "index.html")

PLACARES = ["0-0", "1-0", "0-1", "1-1"]


def norm_col(k):
    return re.sub(r"[^a-z0-9]+", "_", k.strip().lower()).strip("_")


# colunas padrao do CSV (normalizadas); qualquer outra vira stat extra embutida no JSON
COLUNAS_BASE = {norm_col(k) for k in [
    "Data", "Casa", "Fora", "Liga", "Mercado", "Seleção", "Tipo",
    "Minut.", "Odd", "Placar Entrada", "Placar Final", "Result.", "L/P",
]}


def coletar():
    buckets = []
    linhas = []
    stats_cols = []
    vistos = set()
    padrao = os.path.join(PASTA_BASE, "under limite *")
    for pasta in sorted(glob.glob(padrao)):
        nome = os.path.basename(pasta)
        m = re.search(r"under limite (ht|ft)\b(.*?)\bmin\s+(\d+)\s+ao\s+(\d+)(.*)$", nome, re.IGNORECASE)
        if not m:
            continue
        periodo = m.group(1).lower()
        meio = re.sub(r"\s*-\s*", " ", m.group(2)).strip()
        meio = re.sub(r"^\s*entrada\s*", "", meio, flags=re.IGNORECASE).strip()
        min_lo, min_hi = int(m.group(3)), int(m.group(4))
        sufixo = re.sub(r"\s*-\s*", " · ", m.group(5).strip(" -")).strip(" ·")
        tag = " · ".join(x for x in (meio, sufixo) if x)
        csvs = glob.glob(os.path.join(pasta, "*.csv"))
        if not csvs:
            print(f"AVISO: pasta sem CSV ignorada: {nome}")
            continue
        bidx = len(buckets)
        n_antes = len(linhas)
        for arq in csvs:
            with open(arq, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    chave = (r["Data"], r["Casa"], r["Fora"], r["Minut."], r["Odd"], r["Mercado"])
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    placar = r["Placar Entrada"].strip()
                    if placar not in PLACARES:
                        PLACARES.append(placar)
                    linha = [
                        bidx,
                        int(r["Minut."]),
                        float(r["Odd"]),
                        PLACARES.index(placar),
                        1 if r["Result."].strip().lower() == "win" else 0,
                    ]
                    extras = {}
                    for k, v in r.items():
                        if not k:
                            continue
                        nk = norm_col(k)
                        if nk in COLUNAS_BASE or not v or not v.strip():
                            continue
                        extras[nk] = v.strip()
                        if nk not in stats_cols:
                            stats_cols.append(nk)
                    if extras:
                        linha.append(extras)
                    linhas.append(linha)
        label = f"{min_lo}-{min_hi}" + (f" · {tag}" if tag else "")
        buckets.append({
            "periodo": periodo,
            "label": label,
            "min_lo": min_lo,
            "min_hi": min_hi,
            "centro": (min_lo + min_hi) / 2,
            "n": len(linhas) - n_antes,
        })
    return buckets, linhas, stats_cols


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Under Limite — Calculadora e Dashboard</title>
<style>
  :root {
    --bg: #0d1117; --card: #161c2b; --borda: #28324a;
    --txt: #e8edf5; --suave: #8b97ad;
    --verde: #2ecc71; --vermelho: #e74c3c; --amarelo: #f1c40f; --azul: #4da3ff;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body { background: var(--bg); color: var(--txt); font-family: 'Segoe UI', Arial, sans-serif;
         margin: 0; padding: 20px 14px 40px; display: flex; justify-content: center; }
  main { width: 100%; max-width: 780px; }
  h1 { font-size: 1.35rem; margin: 0 0 2px; }
  .sub { color: var(--suave); font-size: .82rem; margin-bottom: 18px; }
  .card { background: var(--card); border: 1px solid var(--borda); border-radius: 14px;
          padding: 16px 18px; margin-bottom: 14px; }
  .card h2 { font-size: .95rem; margin: 0 0 12px; color: var(--azul); letter-spacing: .3px; }
  .lbl { font-size: .75rem; color: var(--suave); text-transform: uppercase; letter-spacing: .5px; margin: 12px 0 6px; }
  .lbl:first-child { margin-top: 0; }

  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { padding: 9px 18px; border-radius: 22px; border: 1px solid var(--borda); background: #0d1220;
          color: var(--suave); cursor: pointer; font-size: .95rem; user-select: none; transition: all .12s; }
  .chip:hover { border-color: var(--azul); }
  .chip.on { background: var(--azul); color: #0d1220; border-color: var(--azul); font-weight: 700; }

  .step { display: flex; gap: 8px; align-items: stretch; max-width: 300px; }
  .step button { width: 46px; border-radius: 10px; border: 1px solid var(--borda); background: #0d1220;
                 color: var(--txt); font-size: 1.3rem; cursor: pointer; }
  .step button:hover { border-color: var(--azul); }
  .step input { flex: 1; text-align: center; background: #0d1220; border: 1px solid var(--borda);
                border-radius: 10px; color: var(--txt); font-size: 1.25rem; font-weight: 700; padding: 8px; }
  input:focus { outline: none; border-color: var(--azul); }
  select { width: 100%; background: #0d1220; border: 1px solid var(--borda); border-radius: 10px;
           color: var(--txt); font-size: .95rem; padding: 9px 10px; margin-bottom: 4px; }
  select:focus { outline: none; border-color: var(--azul); }
  textarea { width: 100%; background: #0d1220; border: 1px solid var(--borda); border-radius: 10px;
             color: var(--txt); font-size: .92rem; padding: 9px 10px; resize: vertical; font-family: inherit; }
  textarea:focus { outline: none; border-color: var(--azul); }
  .btn-jev { display: block; width: 100%; margin: 12px 0 4px; padding: 12px; border-radius: 10px; border: 1px solid var(--azul);
             background: rgba(77,163,255,.12); color: var(--azul); font-size: 1rem; font-weight: 700; cursor: pointer; }
  .btn-jev:hover { background: var(--azul); color: #0d1220; }
  .btn-jev:disabled { opacity: .5; cursor: wait; }
  details summary { cursor: pointer; color: var(--suave); font-size: .82rem; margin-top: 10px; }
  details input { width: 100%; background: #0d1220; border: 1px solid var(--borda); border-radius: 10px;
                  color: var(--txt); font-size: .9rem; padding: 8px 10px; margin: 8px 0 6px; }
  details input:focus { outline: none; border-color: var(--azul); }
  .btn-mini { padding: 7px 14px; border-radius: 8px; border: 1px solid var(--borda); background: #0d1220;
              color: var(--txt); font-size: .85rem; cursor: pointer; }
  .btn-mini:hover { border-color: var(--azul); }
  .jev-probs { font-size: .82rem; color: var(--suave); line-height: 1.7; margin-top: 8px; }
  .jev-probs b { color: var(--txt); }
  .linha2 { display: flex; gap: 20px; flex-wrap: wrap; }

  /* abas */
  .abas { display: flex; gap: 8px; margin-bottom: 14px; }
  .aba { flex: 1; text-align: center; padding: 11px; border-radius: 12px; border: 1px solid var(--borda);
         background: #0d1220; color: var(--suave); cursor: pointer; font-size: .95rem; font-weight: 700; }
  .aba.on { background: var(--azul); color: #0d1220; border-color: var(--azul); }

  /* form ao vivo */
  .grade-entradas { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px,1fr)); gap: 8px; }
  .gi { background: #0d1220; border: 1px solid var(--borda); border-radius: 10px; padding: 6px 8px; }
  .gi .k { font-size: .62rem; color: var(--suave); text-transform: uppercase; letter-spacing: .4px; }
  .gi input { width: 100%; background: transparent; border: none; color: var(--txt);
              font-size: 1.05rem; font-weight: 700; padding: 2px 0 0; }
  .gi input:focus { outline: none; }
  .gi:focus-within { border-color: var(--azul); }

  .veredito { text-align: center; padding: 16px 14px; border-radius: 12px; font-size: 1.15rem;
              font-weight: 800; margin: 14px 0; line-height: 1.35; }
  .v-verde  { background: rgba(46,204,113,.14); color: var(--verde); border: 1px solid var(--verde); }
  .v-vermelho { background: rgba(231,76,60,.14); color: var(--vermelho); border: 1px solid var(--vermelho); }
  .v-amarelo { background: rgba(241,196,15,.10); color: var(--amarelo); border: 1px solid var(--amarelo); }
  .metricas { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap: 8px; }
  .metrica { background: #0d1220; border: 1px solid var(--borda); border-radius: 10px; padding: 10px 12px; }
  .metrica .k { font-size: .68rem; color: var(--suave); text-transform: uppercase; letter-spacing: .5px; }
  .metrica .v { font-size: 1.25rem; font-weight: 800; margin-top: 2px; }
  .fonte { font-size: .8rem; color: var(--suave); line-height: 1.5; margin-top: 10px; }
  .fonte b { color: var(--amarelo); }

  /* mapa de valor */
  .mapa { width: 100%; border-collapse: separate; border-spacing: 5px; }
  .mapa th { font-size: .72rem; color: var(--suave); text-transform: uppercase; padding: 2px 4px; text-align: center; }
  .mapa th.e { text-align: left; }
  .celula { border-radius: 10px; padding: 8px 6px; text-align: center; cursor: pointer;
            border: 1px solid transparent; min-width: 74px; transition: transform .08s; }
  .celula:hover { transform: scale(1.04); }
  .celula.sel { border-color: var(--azul); box-shadow: 0 0 0 1px var(--azul); }
  .celula .j { font-size: 1.05rem; font-weight: 800; }
  .celula .r { font-size: .72rem; font-weight: 700; }
  .celula .n { font-size: .65rem; opacity: .75; }
  .c-pos { background: rgba(46,204,113,.13); } .c-pos .j { color: var(--verde); } .c-pos .r { color: var(--verde); }
  .c-neg { background: rgba(231,76,60,.10); } .c-neg .j { color: var(--vermelho); } .c-neg .r { color: var(--vermelho); }
  .c-fraco { background: rgba(241,196,15,.08); } .c-fraco .j { color: var(--amarelo); } .c-fraco .r { color: var(--amarelo); }
  .c-vazio { background: #0d1220; color: var(--suave); cursor: default; font-size: .72rem; }
  .c-vazio:hover { transform: none; }
  .linha-label { font-size: .8rem; color: var(--txt); font-weight: 700; white-space: nowrap; padding-right: 6px; }
  .linha-label span { display: block; font-size: .65rem; color: var(--suave); font-weight: 400; }

  table.dados { width: 100%; border-collapse: collapse; font-size: .85rem; }
  table.dados th, table.dados td { padding: 6px 8px; text-align: right; border-bottom: 1px solid var(--borda); }
  table.dados th:first-child, table.dados td:first-child { text-align: left; }
  table.dados th { color: var(--suave); font-weight: 600; font-size: .72rem; text-transform: uppercase; }
  .pos { color: var(--verde); } .neg { color: var(--vermelho); }
  .scroll { max-height: 280px; overflow-y: auto; }

  /* cobertura */
  .faixa { display: flex; height: 22px; border-radius: 6px; overflow: hidden; margin: 4px 0 2px; }
  .faixa div { height: 100%; }
  .fz-medido { background: var(--azul); }
  .fz-interp { background: #24405e; }
  .fz-vazio { background: #1a2030; }
  .faixa-lbl { display: flex; justify-content: space-between; font-size: .68rem; color: var(--suave); margin-bottom: 14px; }
  .legenda span { display: inline-flex; align-items: center; margin-right: 14px; font-size: .75rem; color: var(--suave); }
  .legenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; }
  ul.lacunas { margin: 10px 0 0; padding-left: 18px; font-size: .85rem; color: var(--suave); line-height: 1.7; }
  ul.lacunas b { color: var(--txt); }
  .nota { font-size: .8rem; color: var(--suave); line-height: 1.55; }
  .nota b { color: var(--txt); }
</style>
</head>
<body>
<main>
  <h1>Under Limite — Calculadora de Entrada</h1>
  <div class="sub" id="resumoDados"></div>

  <div class="abas">
    <div class="aba on" id="tabDash" onclick="trocaAba('dash')">Dashboard</div>
    <div class="aba" id="tabLive" onclick="trocaAba('live')">Ao vivo (Jev)</div>
    <div class="aba" id="tabCfg" onclick="trocaAba('cfg')">Conexão Jev</div>
  </div>

  <div id="abaDash">

  <!-- ============ CALCULADORA ============ -->
  <div class="card">
    <h2>Consulta rápida</h2>

    <div class="lbl">Período</div>
    <div class="chips" id="cPeriodos"></div>

    <div class="lbl">Placar no momento da entrada</div>
    <div class="chips" id="cPlacares"></div>

    <div class="lbl">Minuto do jogo</div>
    <div class="chips" id="cMinChips" style="margin-bottom:8px"></div>
    <div class="linha2">
      <div>
        <div class="step">
          <button onclick="passo('cMin',-1)">−</button>
          <input id="cMin" type="number" min="0" max="95" value="70">
          <button onclick="passo('cMin',1)">+</button>
        </div>
      </div>
      <div>
        <div class="lbl" style="margin:0 0 6px">Odd oferecida</div>
        <div class="step">
          <button onclick="passo('cOdd',-0.05)">−</button>
          <input id="cOdd" type="number" min="1.01" step="0.01" value="1.80">
          <button onclick="passo('cOdd',0.05)">+</button>
        </div>
      </div>
    </div>

    <div class="lbl">Margem de segurança (ROI alvo)</div>
    <div class="chips" id="cMargens"></div>

    <div id="cVeredito" class="veredito v-verde">—</div>
    <div class="metricas">
      <div class="metrica"><div class="k">Green estimado</div><div class="v" id="cWinrate">—</div></div>
      <div class="metrica"><div class="k">Odd justa</div><div class="v" id="cJusta">—</div></div>
      <div class="metrica"><div class="k">Odd mínima c/ margem</div><div class="v" id="cMinima">—</div></div>
      <div class="metrica"><div class="k">ROI esperado</div><div class="v" id="cRoi">—</div></div>
    </div>
    <div id="cFonte" class="fonte"></div>
  </div>

  <!-- ============ MAPA DE VALOR ============ -->
  <div class="card">
    <h2>Mapa de valor — toque num cenário para ver o detalhe</h2>
    <div style="overflow-x:auto"><table class="mapa" id="mapa"></table></div>
    <div class="legenda" style="margin-top:8px">
      <span><i style="background:rgba(46,204,113,.5)"></i>ROI histórico positivo</span>
      <span><i style="background:rgba(231,76,60,.5)"></i>ROI negativo</span>
      <span><i style="background:rgba(241,196,15,.5)"></i>amostra pequena (&lt;100)</span>
      <span><i style="background:#1a2030"></i>sem dados</span>
    </div>
    <div id="detalhe" style="margin-top:14px; display:none">
      <div class="lbl" id="detTitulo"></div>
      <div class="metricas" id="detMetricas" style="margin-bottom:10px"></div>
      <div id="detValor" class="veredito" style="margin:0 0 10px"></div>
      <div class="scroll"><table class="dados" id="detTabela"></table></div>
      <div class="nota" style="margin-top:8px">ROI por faixa de odd dentro deste cenário (stake 10, comissão 6,5%). Verde = faixa lucrativa no histórico.</div>
    </div>
  </div>

  <!-- ============ ANÁLISE POR ESTATÍSTICA ============ -->
  <div class="card" id="cardStats" style="display:none">
    <h2>Análise por estatística pré-live — onde o contexto muda o edge</h2>
    <div class="lbl">Cenário (período · minuto · placar)</div>
    <select id="sCenario"></select>
    <div class="lbl">Estatística pré-live (coluna extra do CSV)</div>
    <select id="sStat"></select>
    <div id="sResultado" style="margin-top:12px"></div>
    <p class="nota" style="margin:10px 0 0">
      Divide as entradas do cenário em <b>3 faixas (tercís)</b> da estatística escolhida e mostra o ROI histórico em cada uma.
      Cenários com menos de 150 entradas com a stat preenchida não são exibidos.
      <b>Cada segmentação é um teste a mais:</b> antes de concluir que uma faixa tem valor, lembre que múltiplos testes inflam falsos positivos —
      exija amostra grande e confirmação em forward-test.
    </p>
  </div>

  <!-- ============ DECISOR JEV ============ -->
  <div class="card">
    <h2>Decisor de entrada (Jev)</h2>
    <p class="nota" style="margin:0 0 10px">
      Usa o <b>mesmo período, placar, minuto, odd e margem</b> da Consulta rápida acima. O cálculo de valor
      (odd justa, mínima, ROI) é feito pelos dados de backtest; o <b>Jev</b> (modelo de decisão da TypeSafe AI)
      classifica o contexto ao vivo e atua como guardrail. Sem contexto informado, ele julga só pelo cenário.
    </p>
    <div class="lbl">Contexto ao vivo (opcional)</div>
    <textarea id="jevContexto" rows="2" placeholder="Ex.: visitante pressiona, 3 escanteios nos últimos 10 min, chance clara aos 78'..."></textarea>
    <p class="nota" style="margin:6px 0 0">Se o relay estiver fora do ar, o decisor cai para o cálculo de backtest puro. A conexão é configurada na aba <b>Conexão Jev</b> acima.</p>
    <button class="btn-jev" id="jevConsultar">Consultar decisão</button>
    <div id="jevVeredito"></div>
    <div id="jevDetalhe"></div>
    <p class="nota" style="margin:10px 0 0">
      O Jev classifica contexto com probabilidade calibrada — não prevê o jogo. A decisão de valor vem dos dados de backtest
      e nenhum modelo garante lucro: valide em forward-test antes de aumentar stake.
    </p>
  </div>

  <!-- ============ COBERTURA ============ -->
  <div class="card">
    <h2>Cobertura dos dados — onde existem dados e onde não</h2>
    <div class="lbl">1º tempo (HT)</div>
    <div class="faixa" id="faixaHT"></div>
    <div class="faixa-lbl"><span>0'</span><span>15'</span><span>30'</span><span>45'+</span></div>
    <div class="lbl">2º tempo (FT)</div>
    <div class="faixa" id="faixaFT"></div>
    <div class="faixa-lbl"><span>45'</span><span>60'</span><span>75'</span><span>90'+</span></div>
    <div class="legenda">
      <span><i style="background:var(--azul)"></i>medido no backtest</span>
      <span><i style="background:#24405e"></i>interpolado entre medições</span>
      <span><i style="background:#1a2030"></i>sem dados (extrapolação)</span>
    </div>
    <ul class="lacunas" id="lacunas"></ul>
  </div>

  <!-- ============ NOTAS ============ -->
  <div class="card">
    <h2>Como interpretar</h2>
    <p class="nota" style="margin:0">
      <b>Odd justa</b> = 1 / taxa de green histórica — abaixo dela a entrada perde no longo prazo.
      <b>Odd mínima</b> = odd justa + margem de segurança. ROI e lucro usam stake 10 e comissão de 6,5% sobre o lucro (padrão exchange).<br>
      <b>Critérios:</b> os filtros da estratégia (sem cartão vermelho, PI1 ≤ 50, CG ≤ 5) já vêm aplicados nos backtests do Fut Odds —
      só considere jogos que passam nos mesmos critérios.<br>
      <b>Odd suspeita:</b> odd muito acima da justa nem sempre é valor — pode ser pênalti, falta perigosa ou pressão que os indicadores
      não capturaram. O alerta dispara quando a odd passa de +15% da justa.<br>
      <b>Atualização:</b> novos CSVs nas pastas + rodar <b>analisar_backtests.py</b> regeneram este site.
    </p>
  </div>
  </div><!-- /abaDash -->

  <!-- ============ ABA AO VIVO ============ -->
  <div id="abaLive" style="display:none">

  <div class="card">
    <h2>Estado do jogo ao vivo</h2>
    <p class="nota" style="margin:0 0 10px">Preencha com os dados da tela ao vivo (Fut Odds). Campos de pressão e probabilidades são opcionais, mas melhoram a avaliação do Jev.</p>

    <div class="lbl">Preenchimento rápido — Ctrl+C no Fut Odds, Ctrl+V aqui (acumulativo)</div>
    <textarea id="lvPaste" rows="3" placeholder="No Fut Odds: Ctrl+A na tela do jogo, Ctrl+C, Ctrl+V aqui — os campos se preenchem sozinhos. Repita com as abas Press., Prob. (Match e Gols), Stats e Odds: cada colagem completa o que falta e nunca apaga o que já entrou."></textarea>
    <div style="display:flex;gap:8px;margin-top:6px">
      <button class="btn-mini" id="lvColarBtn">Preencher campos</button>
    </div>
    <div id="lvPasteMsg" class="jev-probs" style="margin-top:6px"></div>

    <div class="lbl">Jogo</div>
    <div class="grade-entradas">
      <div class="gi"><div class="k">Gols casa</div><input id="lvGolsC" type="number" min="0" value="0"></div>
      <div class="gi"><div class="k">Gols fora</div><input id="lvGolsF" type="number" min="0" value="0"></div>
      <div class="gi"><div class="k">Minuto</div><input id="lvMin" type="number" min="0" max="95" value="70"></div>
    </div>

    <div class="lbl">Odds do under</div>
    <div class="grade-entradas">
      <div class="gi"><div class="k">Odd live</div><input id="lvOddLive" type="number" step="0.01" min="1.01" value="1.80"></div>
      <div class="gi"><div class="k">Odd pré-live</div><input id="lvOddPre" type="number" step="0.01" min="1.01" value="2.00"></div>
      <div class="gi"><div class="k">Linha (gols)</div><input id="lvLinha" type="number" step="0.5" min="0.5" max="8.5" value="2.5"></div>
    </div>

    <div class="lbl">Probabilidades projetadas % (opcional)</div>
    <div class="grade-entradas">
      <div class="gi"><div class="k">Vitória casa</div><input id="lvWinC" type="number" min="0" max="100" placeholder="—"></div>
      <div class="gi"><div class="k">Empate</div><input id="lvEmp" type="number" min="0" max="100" placeholder="—"></div>
      <div class="gi"><div class="k">Vitória fora</div><input id="lvWinF" type="number" min="0" max="100" placeholder="—"></div>
      <div class="gi"><div class="k">Over 2.5 pré</div><input id="lvOver25" type="number" min="0" max="100" placeholder="—"></div>
    </div>

    <div class="lbl">Indicadores de pressão (opcional)</div>
    <div class="grade-entradas">
      <div class="gi"><div class="k">APPM (soma)</div><input id="lvAPPM" type="number" step="0.01" placeholder="—"></div>
      <div class="gi"><div class="k">APPM10 (soma)</div><input id="lvAPPM10" type="number" step="0.01" placeholder="—"></div>
      <div class="gi"><div class="k">CG (soma)</div><input id="lvCG" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">CG10 (soma)</div><input id="lvCG10" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">PI1 (soma)</div><input id="lvPI1" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">PI2 (soma)</div><input id="lvPI2" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">PI3 (soma)</div><input id="lvPI3" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">xG ao vivo (soma)</div><input id="lvXG" type="number" step="0.1" placeholder="—"></div>
    </div>

    <div class="lbl">Volume de jogo (opcional)</div>
    <div class="grade-entradas">
      <div class="gi"><div class="k">Posse casa %</div><input id="lvPosse" type="number" min="0" max="100" placeholder="—"></div>
      <div class="gi"><div class="k">Atq. perig. casa</div><input id="lvAPC" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">Atq. perig. fora</div><input id="lvAPF" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">Finaliz. casa</div><input id="lvFinC" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">Finaliz. fora</div><input id="lvFinF" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">Escant. casa</div><input id="lvEscC" type="number" placeholder="—"></div>
      <div class="gi"><div class="k">Escant. fora</div><input id="lvEscF" type="number" placeholder="—"></div>
    </div>

    <div class="lbl">Contexto livre (opcional)</div>
    <textarea id="lvCtx" rows="2" placeholder="Ex.: expulso aos 60', chuva forte, pênalti defendido, goleiro sentindo..."></textarea>

    <div class="lbl">Margem de segurança</div>
    <div class="chips" id="lvMargens"></div>

    <button class="btn-jev" id="lvPrecificar">Precificar under</button>
  </div>

  <div class="card" id="lvResultado" style="display:none">
    <h2>Precificação</h2>
    <div id="lvVeredito"></div>
    <div class="metricas" id="lvMetricas" style="margin-top:10px"></div>
    <div class="lbl" style="margin-top:14px">Queda esperada da odd justa nos próximos minutos</div>
    <table class="dados" id="lvDecaimento"></table>
    <div id="lvBacktest" class="fonte" style="margin-top:10px"></div>
    <div id="lvJev" class="jev-probs"></div>
    <p class="nota" style="margin:10px 0 0">
      Precificação heurística: Poisson (λ da odd pré-live) × decaimento t^0,84 × ajuste de contexto do Jev.
      <b>Ainda não validada em forward-test</b> — não substitui os backtests até ser auditada.
      O Jev não gera números; ele classifica o contexto que o código usa para ajustar o modelo.
    </p>
  </div>

  </div><!-- /abaLive -->

  <!-- ============ ABA CONEXÃO JEV ============ -->
  <div id="abaCfg" style="display:none">
  <div class="card">
    <h2>Conexão do Jev</h2>
    <p class="nota" style="margin:0 0 10px">
      O site já vem ligado ao <b>relay Cloudflare do projeto</b> — um Worker gratuito que guarda a chave TypeSafe
      (fora do repositório) e repassa as chamadas, contornando o bloqueio de CORS da API oficial.
      <b>Não é preciso colar chave nenhuma</b>: clique em <b>Testar conexão</b> e use. Custo ~US$ 0,00002 por decisão.
    </p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn-mini" id="cfgTestar">Testar conexão</button>
    </div>
    <div id="cfgStatus" class="jev-probs" style="margin-top:10px"></div>
    <div class="lbl" style="margin-top:12px">URL do relay Cloudflare (já preenchida — só mude se fizer redeploy do Worker)</div>
    <input id="cfgRelay" type="text" placeholder="https://jev-relay.SEU-USUARIO.workers.dev"
           style="width:100%;background:#0d1220;border:1px solid var(--borda);border-radius:10px;color:var(--txt);font-size:.9rem;padding:9px 10px">
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="btn-mini" id="cfgSalvarRelay">Salvar relay</button>
      <button class="btn-mini" id="cfgRemover">Restaurar padrão</button>
    </div>
    <p class="nota" style="margin:8px 0 0">
      A URL do relay fica salva só no <b>seu navegador</b> (localStorage) quando alterada.
      Código do Worker em <code>relay_cloudflare.js</code> no repositório, com instruções de deploy no topo do arquivo.
    </p>
  </div>
  </div><!-- /abaCfg -->
</main>

<script>
const DADOS = /*__DATA__*/;
const PLACARES = DADOS.placares;
const BUCKETS = DADOS.buckets;
const ROWS = DADOS.rows;            // [bucketIdx, minuto, odd, placarIdx, win]
const STAKE = 10, COMISSAO = 0.065, ALERTA = 0.15;

const $ = id => document.getElementById(id);
const fmtOdd = v => v.toFixed(2);
const fmtPct = v => (v * 100).toFixed(1) + '%';
const fmtN = v => v.toLocaleString('pt-BR');
const fmtJ = s => s.green > 0 ? fmtOdd(s.justa) : '—';
const placarFmt = p => p.replace('-', 'x');
const lucroDe = r => r[4] ? (r[2] - 1) * STAKE * (1 - COMISSAO) : -STAKE;

function resumo(rows) {
  const n = rows.length;
  if (!n) return null;
  const wins = rows.reduce((a, r) => a + r[4], 0);
  const lucro = rows.reduce((a, r) => a + lucroDe(r), 0);
  const green = wins / n;
  return { n, green, justa: 1 / green, lucro, roi: lucro / (n * STAKE) };
}
const rowsDoBucket = i => ROWS.filter(r => r[0] === i);
const rowsCenario = (i, p) => ROWS.filter(r => r[0] === i && PLACARES[r[3]] === p);

// ================= estado da calculadora =================
const calc = { periodo: 'ft', placar: '0-0', margem: 0.05 };

function chipsDo(id, itens, get, set) {
  const el = $(id);
  el.innerHTML = '';
  for (const it of itens) {
    const c = document.createElement('div');
    c.className = 'chip' + (get(it) ? ' on' : '');
    c.textContent = it.label;
    c.onclick = () => { set(it); renderCalc(); };
    el.appendChild(c);
  }
}

function passo(id, d) {
  const el = $(id);
  const casas = id === 'cOdd' ? 2 : 0;
  el.value = Math.max(id === 'cOdd' ? 1.01 : 0, (parseFloat(el.value) || 0) + d).toFixed(casas);
  renderCalc();
}

function pontosCalc(periodo, placar) {
  const pts = [], ptsGeral = [];
  BUCKETS.forEach((b, i) => {
    if (b.periodo !== periodo) return;
    const sG = resumo(rowsDoBucket(i));
    if (sG) ptsGeral.push({ x: b.centro, p: sG.green, n: sG.n, label: b.label });
    const sP = resumo(rowsCenario(i, placar));
    if (sP && sP.n >= 50) pts.push({ x: b.centro, p: sP.green, n: sP.n, label: b.label });
  });
  return { pts: pts.length ? pts : ptsGeral, usouGeral: !pts.length };
}

function interpola(pts, min) {
  const s = [...pts].sort((a, b) => a.x - b.x);
  if (min <= s[0].x) return { p: s[0].p, extra: min < s[0].x };
  if (min >= s[s.length - 1].x) return { p: s[s.length - 1].p, extra: min > s[s.length - 1].x };
  for (let i = 0; i < s.length - 1; i++)
    if (min >= s[i].x && min <= s[i + 1].x) {
      const t = (min - s[i].x) / (s[i + 1].x - s[i].x);
      return { p: s[i].p + t * (s[i + 1].p - s[i].p), extra: false };
    }
}

function renderChipsCalc() {
  chipsDo('cPeriodos',
    [{ label: '1º tempo (HT)', v: 'ht' }, { label: '2º tempo (FT)', v: 'ft' }],
    it => calc.periodo === it.v, it => { calc.periodo = it.v; renderChipsCalc(); });

  chipsDo('cPlacares', PLACARES.map(p => ({ label: placarFmt(p), v: p })),
    it => calc.placar === it.v, it => { calc.placar = it.v; });

  const mins = BUCKETS.filter(b => b.periodo === calc.periodo)
    .map(b => ({ label: Math.round(b.centro) + "'", v: Math.round(b.centro) }));
  chipsDo('cMinChips', mins, () => false, it => { $('cMin').value = it.v; });

  chipsDo('cMargens', [{ label: '0%', v: 0 }, { label: '5%', v: .05 }, { label: '10%', v: .10 }],
    it => calc.margem === it.v, it => { calc.margem = it.v; });
}

function renderCalc() {
  renderChipsCalc();
  const min = parseFloat($('cMin').value);
  const odd = parseFloat($('cOdd').value);
  const v = $('cVeredito');
  if (isNaN(min) || isNaN(odd) || odd < 1.01) { v.className = 'veredito'; v.textContent = 'Preencha minuto e odd'; return; }

  const { pts, usouGeral } = pontosCalc(calc.periodo, calc.placar);
  const { p, extra } = interpola(pts, min);
  const justa = 1 / p;
  const minima = justa * (1 + calc.margem);
  const roiEsp = odd * p - 1;

  $('cWinrate').textContent = fmtPct(p);
  $('cJusta').textContent = fmtOdd(justa);
  $('cMinima').textContent = fmtOdd(minima);
  $('cRoi').textContent = (roiEsp >= 0 ? '+' : '') + fmtPct(roiEsp);
  $('cRoi').style.color = roiEsp >= 0 ? 'var(--verde)' : 'var(--vermelho)';

  if (odd >= justa * (1 + ALERTA)) {
    v.className = 'veredito v-amarelo';
    v.textContent = '⚠ ODD SUSPEITA — muito acima da justa. Possível pênalti, falta perigosa ou pressão não capturada. Verifique o jogo ao vivo antes de entrar.';
  } else if (odd >= minima) {
    v.className = 'veredito v-verde';
    v.textContent = '✔ TEM VALOR — odd acima da mínima com margem';
  } else if (odd >= justa) {
    v.className = 'veredito v-amarelo';
    v.textContent = '◑ NO LIMITE — acima do breakeven, mas sem a margem de segurança';
  } else {
    v.className = 'veredito v-vermelho';
    v.textContent = '✖ SEM VALOR — odd abaixo da justa para este cenário';
  }

  let fonte = `Âncoras: ${pts.map(q => `min ${q.label} (${fmtN(q.n)} entradas)`).join(' · ')}.`;
  if (usouGeral) fonte += ' <b>Este placar não tem amostra própria suficiente — usando a taxa geral do período.</b>';
  if (extra) fonte += ' <b>Minuto fora da faixa medida — extrapolação, use com cautela.</b>';
  $('cFonte').innerHTML = fonte;
}

// ================= mapa de valor =================
let selecionado = null;

function renderMapa() {
  let html = '<tr><th class="e">Entrada</th>' + PLACARES.map(p => `<th>${placarFmt(p)}</th>`).join('') + '</tr>';
  BUCKETS.forEach((b, i) => {
    html += `<tr><td class="linha-label">${b.periodo.toUpperCase()} ${b.label}'<span>${fmtN(b.n)} entradas</span></td>`;
    for (const p of PLACARES) {
      const s = resumo(rowsCenario(i, p));
      if (!s) { html += '<td><div class="celula c-vazio">sem dados</div></td>'; continue; }
      const cls = s.n < 100 ? 'c-fraco' : (s.roi >= 0 ? 'c-pos' : 'c-neg');
      const sel = selecionado && selecionado.i === i && selecionado.p === p ? ' sel' : '';
      html += `<td><div class="celula ${cls}${sel}" onclick="detalhar(${i},'${p}')">` +
              `<div class="j">${fmtJ(s)}</div>` +
              `<div class="r">${(s.roi >= 0 ? '+' : '') + fmtPct(s.roi)}</div>` +
              `<div class="n">n=${fmtN(s.n)} · ${fmtPct(s.green)}</div></div></td>`;
    }
    html += '</tr>';
  });
  $('mapa').innerHTML = html;
}

function detalhar(i, p) {
  selecionado = { i, p };
  renderMapa();
  const b = BUCKETS[i];
  const rows = rowsCenario(i, p);
  const s = resumo(rows);
  $('detalhe').style.display = '';
  $('detTitulo').textContent = `${b.periodo.toUpperCase()} · entrada min ${b.label} · placar ${placarFmt(p)}`;
  $('detMetricas').innerHTML =
    `<div class="metrica"><div class="k">Entradas</div><div class="v">${fmtN(s.n)}</div></div>` +
    `<div class="metrica"><div class="k">Green</div><div class="v">${fmtPct(s.green)}</div></div>` +
    `<div class="metrica"><div class="k">Odd justa</div><div class="v">${fmtJ(s)}</div></div>` +
    `<div class="metrica"><div class="k">ROI histórico</div><div class="v" style="color:${s.roi >= 0 ? 'var(--verde)' : 'var(--vermelho)'}">${(s.roi >= 0 ? '+' : '') + fmtPct(s.roi)}</div></div>`;

  // faixas de odd dentro do cenario
  const maxOdd = Math.max(...rows.map(r => r[2]));
  let faixas = [];
  for (let lo = 1.0; lo < maxOdd; lo += 0.2) {
    const hi = lo + 0.2;
    const sel = rows.filter(r => r[2] >= lo && (r[2] < hi || hi >= maxOdd));
    if (sel.length >= 10) faixas.push({ lo, hi, s: resumo(sel) });
  }
  const primeiraBoa = faixas.find(f => f.s.n >= 30 && f.s.roi > 0);
  const dv = $('detValor');
  if (primeiraBoa) {
    dv.className = 'veredito v-verde';
    dv.textContent = `Nos dados, este cenário fica lucrativo a partir de odd ≈ ${primeiraBoa.lo.toFixed(2)} (faixa ${primeiraBoa.lo.toFixed(2)}–${primeiraBoa.hi.toFixed(2)}: ROI ${fmtPct(primeiraBoa.s.roi)} em ${fmtN(primeiraBoa.s.n)} entradas)`;
  } else {
    dv.className = 'veredito v-vermelho';
    dv.textContent = 'Nenhuma faixa de odd com amostra razoável foi lucrativa neste cenário — evite ou exija odd bem acima da justa.';
  }
  let html = '<tr><th>Faixa de odd</th><th>n</th><th>Green</th><th>Odd justa</th><th>ROI</th><th>Lucro</th></tr>';
  for (const f of faixas) {
    const cls = f.s.roi >= 0 ? 'pos' : 'neg';
    html += `<tr><td>${f.lo.toFixed(2)}–${f.hi.toFixed(2)}</td><td>${fmtN(f.s.n)}${f.s.n < 100 ? ' *' : ''}</td>` +
            `<td>${fmtPct(f.s.green)}</td><td>${fmtJ(f.s)}</td>` +
            `<td class="${cls}">${(f.s.roi >= 0 ? '+' : '') + fmtPct(f.s.roi)}</td>` +
            `<td class="${cls}">${(f.s.lucro >= 0 ? '+' : '') + f.s.lucro.toFixed(0)}</td></tr>`;
  }
  $('detTabela').innerHTML = html;
  $('detalhe').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ================= cobertura e lacunas =================
function renderCobertura() {
  function faixa(elId, de, ate, periodo) {
    const el = $(elId);
    el.innerHTML = '';
    const bs = BUCKETS.filter(b => b.periodo === periodo).sort((a, b) => a.min_lo - b.min_lo);
    let cursor = de;
    const total = ate - de;
    const add = (classe, largura) => {
      if (largura <= 0) return;
      const d = document.createElement('div');
      d.className = classe;
      d.style.width = (largura / total * 100) + '%';
      el.appendChild(d);
    };
    for (const b of bs) {
      const lo = Math.max(b.min_lo, de), hi = Math.min(b.min_hi + 1, ate);
      if (hi <= de || lo >= ate) continue;
      if (cursor < lo) add(bs.indexOf(b) > 0 && cursor >= bs[0].min_lo ? 'fz-interp' : 'fz-vazio', lo - cursor);
      add('fz-medido', hi - lo);
      cursor = hi;
    }
    if (cursor < ate) add(cursor > bs[bs.length - 1].min_lo ? 'fz-vazio' : 'fz-vazio', ate - cursor);
  }
  faixa('faixaHT', 0, 46, 'ht');
  faixa('faixaFT', 45, 91, 'ft');

  // lacunas geradas a partir dos dados
  const notas = [];
  for (const periodo of ['ht', 'ft']) {
    const bs = BUCKETS.filter(b => b.periodo === periodo).sort((a, b) => a.min_lo - b.min_lo);
    if (!bs.length) continue;
    const nome = periodo.toUpperCase();
    notas.push(`<b>${nome}:</b> dados reais nos minutos ${bs.map(b => b.label).join(', ')} — entre eles os valores são <b>interpolados</b>.`);
    for (let i = 0; i < bs.length - 1; i++)
      if (bs[i + 1].min_lo - bs[i].min_hi > 1)
        notas.push(`<b>${nome} min ${bs[i].min_hi + 1}–${bs[i + 1].min_lo - 1}:</b> nenhum backtest cobre essa janela — a calculadora interpola entre as medições mais próximas.`);
    notas.push(`<b>${nome} após min ${bs[bs.length - 1].min_hi}:</b> sem dados — qualquer leitura aí é extrapolação.`);
    for (const p of PLACARES) {
      const n = ROWS.filter(r => BUCKETS[r[0]].periodo === periodo && PLACARES[r[3]] === p).length;
      if (n === 0) notas.push(`<b>${nome} placar ${placarFmt(p)}:</b> nenhuma entrada nos backtests — a calculadora usa a taxa geral do período nesse caso.`);
      else if (n < 100) notas.push(`<b>${nome} placar ${placarFmt(p)}:</b> só ${n} entradas — amostra fraca, leia com cautela.`);
    }
  }
  notas.push('<b>HT min 42–43:</b> backtest focado em 0x0 (estratégia otimizada) — outros placares quase não aparecem nessa janela.');
  $('lacunas').innerHTML = notas.map(n => `<li>${n}</li>`).join('');
}

// ================= decisor Jev =================
// O site chama SEMPRE o relay Cloudflare (Worker) — a chave TypeSafe fica
// guardada no Worker, fora do repositório, e a chamada não sofre CORS.
const JEV_RELAY_PADRAO = 'https://still-cake-5afc.cavalcante-maxi.workers.dev';
const JEV_QUESTOES = {
  risco: {
    type: 'choice',
    instructions: 'Qual o perfil de risco desta entrada under no mercado de gols, dado o cenário de backtest e o contexto ao vivo?',
    criteria: {
      baixo: 'contexto consistente com jogo truncado, sem sinais de pressão ofensiva',
      moderado: 'alguma pressão, incerteza ou contexto vazio demais para cravar',
      alto: 'pressão ofensiva clara, chance clara, pênalti, falta perigosa ou cartão vermelho'
    }
  },
  pressao: {
    type: 'noul',
    instructions: 'O contexto ao vivo descreve pressão ofensiva relevante contra esta entrada under?'
  },
  truncado: {
    type: 'noul',
    instructions: 'O contexto ao vivo indica jogo truncado de baixa intensidade, consistente com a entrada under?'
  }
};
function normRelay(u) {
  u = (u || '').trim().replace(/\s+/g, '');
  if (!u) return '';
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  return u.replace(/\/+$/, '');
}
const jevRelay = () => normRelay(localStorage.getItem('jev_relay_url')) || JEV_RELAY_PADRAO;

function cfgStatus() {
  const el = $('cfgStatus'), relay = jevRelay();
  $('cfgRelay').value = relay;
  el.innerHTML = normRelay(localStorage.getItem('jev_relay_url'))
    ? `<b>Relay personalizado salvo:</b> ${relay}`
    : '<b>Relay padrão do projeto ativo</b> — clique em <b>Testar conexão</b> para confirmar que está no ar.';
}

function initCfg() {
  cfgStatus();
  $('cfgRemover').onclick = () => { localStorage.removeItem('jev_relay_url'); localStorage.removeItem('openrouter_key'); cfgStatus(); };
  $('cfgSalvarRelay').onclick = () => {
    const u = normRelay($('cfgRelay').value);
    if (!u) { cfgStatus(); return; }
    localStorage.setItem('jev_relay_url', u);
    cfgStatus();
  };
  $('cfgTestar').onclick = async () => {
    $('cfgStatus').innerHTML = 'Testando…';
    const r = await jevChamar({ teste: 'conexao' }, { ping: { type: 'noul', instructions: 'Este texto é um teste de conexão?' } }, false);
    $('cfgStatus').innerHTML = r.erro
      ? `<b>Falhou:</b> ${r.erro}`
      : `<b>Conectado.</b> Resposta do Jev recebida via relay (P(teste)=${((r.ans.ping && r.ans.ping.noul != null) ? r.ans.ping.noul.toFixed(2) : 'ok')}).`;
  };
  $('jevConsultar').onclick = jevDecidir;
}

// números vêm do backtest (Jev é fraco em matemática — cálculo fica no código)
function jevCenario() {
  const min = parseFloat($('cMin').value), odd = parseFloat($('cOdd').value);
  if (isNaN(min) || isNaN(odd) || odd < 1.01) return null;
  const { pts } = pontosCalc(calc.periodo, calc.placar);
  const { p, extra } = interpola(pts, min);
  const justa = 1 / p;
  const minima = justa * (1 + calc.margem);
  // bucket medido mais próximo deste minuto (para n e ROI histórico reais, não interpolados)
  let melhor = null;
  BUCKETS.forEach((b, i) => {
    if (b.periodo !== calc.periodo) return;
    const s = resumo(rowsCenario(i, calc.placar));
    if (s && (!melhor || Math.abs(b.centro - min) < Math.abs(melhor.centro - min)))
      melhor = { centro: b.centro, label: b.label, n: s.n, green: s.green, roi: s.roi };
  });
  return {
    min, odd, p, justa, minima, extra,
    roiEsp: odd * p - 1,
    alerta: odd >= justa * (1 + ALERTA),
    hist: melhor
  };
}

function jevVereditoDet(c) {
  if (c.alerta) return { cls: 'v-amarelo', txt: '⚠ ODD SUSPEITA — muito acima da justa. Verifique o jogo ao vivo antes de entrar.' };
  if (c.odd >= c.minima) return { cls: 'v-verde', txt: '✔ TEM VALOR — odd acima da mínima com margem (dados de backtest)' };
  if (c.odd >= c.justa) return { cls: 'v-amarelo', txt: '◑ NO LIMITE — acima do breakeven, sem a margem de segurança' };
  return { cls: 'v-vermelho', txt: '✖ SEM VALOR — odd abaixo da justa para este cenário' };
}

function jevMostra(c, detHtml, vered) {
  const v = vered || jevVereditoDet(c);
  $('jevVeredito').className = 'veredito ' + v.cls;
  $('jevVeredito').textContent = v.txt;
  let html = `<div class="metricas" style="margin-top:10px">
    <div class="metrica"><div class="k">Green estimado</div><div class="v">${fmtPct(c.p)}</div></div>
    <div class="metrica"><div class="k">Odd justa</div><div class="v">${fmtOdd(c.justa)}</div></div>
    <div class="metrica"><div class="k">Odd mínima</div><div class="v">${fmtOdd(c.minima)}</div></div>
    <div class="metrica"><div class="k">ROI esperado</div><div class="v" style="color:${c.roiEsp >= 0 ? 'var(--verde)' : 'var(--vermelho)'}">${(c.roiEsp >= 0 ? '+' : '') + fmtPct(c.roiEsp)}</div></div>
  </div>`;
  if (c.hist) html += `<div class="fonte">Âncora medida mais próxima: ${c.hist.label} · n=${fmtN(c.hist.n)} · green ${fmtPct(c.hist.green)} · ROI hist. ${(c.hist.roi >= 0 ? '+' : '') + fmtPct(c.hist.roi)}${c.extra ? ' · <b>minuto fora da faixa medida (extrapolação)</b>' : ''}</div>`;
  if (detHtml) html += detHtml;
  $('jevDetalhe').innerHTML = html;
}

function jevMsgErro(status, data) {
  // TypeSafe devolve {"detail":{"error_type","message"}}; outras APIs usam {"error":{"message"}}
  const msg = (data && (
    (data.detail && (data.detail.message || data.detail.error_type)) ||
    (data.error && (data.error.message || data.error.code)) ||
    data.erro)) || '';
  if (status === 401) return 'Chave inválida no Worker (401) — confira o secret TYPESAFE_API_KEY do relay.';
  if (status === 402) return 'Créditos esgotados na TypeSafe (402).';
  if (status === 429) return 'Limite de requisições (429) — tente em instantes.';
  if (status === 529) return 'API saturada (529) — tente em instantes.';
  return 'Erro ' + status + (msg ? ': ' + msg : '');
}

async function jevChamar(state, questions, tentativa) {
  const url = jevRelay();
  const ctrl = new AbortController();
  const to = setTimeout(() => ctrl.abort(), 20000);
  try {
    const resp = await fetch(url, {
      method: 'POST', signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'jev-latest', state, questions })
    });
    if ((resp.status === 429 || resp.status === 529) && !tentativa) {
      await new Promise(r => setTimeout(r, 2000));
      return jevChamar(state, questions, true);
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) return { erro: jevMsgErro(resp.status, data) };
    const ans = data.answers || (data.output && data.output.answers) || (data.decision && data.decision.answers) || null;
    if (!ans) return { erro: 'Resposta fora do formato esperado (o relay respondeu, mas sem o campo "answers").' };
    return { ans };
  } catch (e) {
    return { erro: e.name === 'AbortError'
      ? 'Tempo esgotado (20s) — o relay ou a API não respondeu.'
      : 'Falha de rede ao chamar o relay (' + (e.message || e.name) + '). Confira a URL na aba Conexão Jev.' };
  } finally { clearTimeout(to); }
}

async function jevDecidir() {
  const c = jevCenario();
  if (!c) { $('jevVeredito').className = 'veredito v-amarelo'; $('jevVeredito').textContent = 'Preencha minuto e odd na Consulta rápida acima.'; return; }
  const ctx = $('jevContexto').value.trim();

  // decisão puramente matemática: não gasta chamada quando a odd está muito abaixo da justa
  if (c.odd < c.justa * 0.9) {
    jevMostra(c, `<div class="fonte">Jev não consultado: a odd está tão abaixo da justa que o veredito é matemático — contexto nenhum o tornaria lucrativo.</div>`);
    return;
  }
  if (!jevRelay()) {
    jevMostra(c, `<div class="fonte">⚠ Sem relay configurado, o Jev não avalia o contexto — o veredito acima é só o cálculo de backtest.</div>`);
    return;
  }

  $('jevConsultar').disabled = true;
  $('jevVeredito').className = 'veredito';
  $('jevVeredito').textContent = 'Consultando Jev…';
  const state = {
    cenario: `${calc.periodo.toUpperCase()} min ${Math.round(c.min)} placar ${placarFmt(calc.placar)}`,
    odd_oferecida: c.odd,
    odd_justa_backtest: +c.justa.toFixed(2),
    taxa_green_historica: +c.p.toFixed(3),
    entradas_na_ancora: c.hist ? c.hist.n : 0,
    roi_historico_ancora: c.hist ? +c.hist.roi.toFixed(3) : null,
    odd_suspeita: c.alerta,
    contexto_ao_vivo: ctx || 'sem contexto informado — julgar apenas pelo cenário'
  };
  const { ans, erro } = await jevChamar(state, JEV_QUESTOES, false);
  $('jevConsultar').disabled = false;

  if (erro || !ans.risco || !ans.pressao) {
    jevMostra(c, `<div class="veredito v-amarelo" style="margin:10px 0 0">Jev indisponível: ${erro || 'resposta sem os campos esperados'}<br>Veredito abaixo é só o cálculo determinístico de backtest.</div>`);
    return;
  }

  const pressao = ans.pressao.noul, truncado = ans.truncado ? ans.truncado.noul : null;
  const risco = ans.risco.choice;
  let cls, txt, regra;
  if (pressao > 0.60) {
    cls = 'v-vermelho'; txt = '✖ EVITAR — o contexto indica pressão contra a entrada';
    regra = `guardrail: P(pressão) = ${pressao.toFixed(2)} > 0,60`;
  } else if (risco === 'alto') {
    cls = 'v-amarelo'; txt = '◑ AGUARDE / VERIFIQUE — Jev classificou risco alto';
    regra = `risco = alto (confiança ${(ans.risco.confidence || 0).toFixed(2)})`;
  } else if (risco === 'moderado') {
    cls = 'v-amarelo';
    txt = c.odd >= c.minima ? '◑ NO LIMITE — valor existe, mas exija contexto limpo' : jevVereditoDet(c).txt.replace(/^◑\s*/, '');
    regra = `risco = moderado (confiança ${(ans.risco.confidence || 0).toFixed(2)})`;
  } else {
    const v = jevVereditoDet(c);
    cls = v.cls; txt = v.txt + ' — contexto validado pelo Jev';
    regra = `risco = baixo (confiança ${(ans.risco.confidence || 0).toFixed(2)})`;
  }

  const probs = ans.risco.probabilities || {};
  const probTxt = Object.entries(probs).map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(' · ');
  const detHtml = `<div class="jev-probs">
    <b>Jev:</b> ${regra}<br>
    <b>P(pressão):</b> ${(pressao * 100).toFixed(0)}%${truncado !== null ? ` · <b>P(jogo truncado):</b> ${(truncado * 100).toFixed(0)}%` : ''}<br>
    <b>Distribuição de risco:</b> ${probTxt}
  </div>`;
  jevMostra(c, detHtml, { cls, txt });
}

// ================= abas =================
function trocaAba(qual) {
  $('abaDash').style.display = qual === 'dash' ? '' : 'none';
  $('abaLive').style.display = qual === 'live' ? '' : 'none';
  $('abaCfg').style.display = qual === 'cfg' ? '' : 'none';
  $('tabDash').className = 'aba' + (qual === 'dash' ? ' on' : '');
  $('tabLive').className = 'aba' + (qual === 'live' ? ' on' : '');
  $('tabCfg').className = 'aba' + (qual === 'cfg' ? ' on' : '');
}

// ================= precificação ao vivo (Poisson + Jev) =================
// motor determinístico: λ vem da odd pré-live (ou do % over 2.5 projetado) e decai com t^0,84
function poisPMF(k, l) { return Math.exp(-l) * Math.pow(l, k) / fat(k); }
function poisCDF(k, l) { let s = 0; for (let i = 0; i <= k; i++) s += poisPMF(i, l); return Math.min(s, 1); }
function fat(n) { let r = 1; for (let i = 2; i <= n; i++) r *= i; return r; }

function lambdaDaProb(pUnder, linha) {
  const kMax = Math.floor(linha);
  let lo = 0.05, hi = 8;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    if (poisCDF(kMax, mid) > pUnder) lo = mid; else hi = mid; // λ maior → under menos provável
  }
  return (lo + hi) / 2;
}
const lambdaRestante = (lamTotal, min) => lamTotal * Math.pow(Math.max(0.5, 95 - min) / 95, 0.84);

function precoUnder(lamTotal, min, linha, golsAtuais, mult) {
  const permitidos = Math.floor(linha) - golsAtuais; // gols que ainda cabem
  if (permitidos < 0) return { p: 0, odd: Infinity };
  const lam = lambdaRestante(lamTotal, min) * (mult || 1);
  const p = poisCDF(permitidos, lam);
  return { p, odd: p > 0 ? 1 / p : Infinity };
}

const LV_QUESTOES = {
  ameaca: {
    type: 'choice',
    instructions: 'Qual o nível de ameaça de gol nos próximos minutos, dados placar, minuto, indicadores de pressão e probabilidades?',
    criteria: {
      baixa: 'jogo controlado, pouca criação, sem pressão ofensiva relevante',
      moderada: 'alguma criação e pressão, mas sem domínio claro nem chances claras frequentes',
      alta: 'pressão ofensiva forte, chances claras, pênalti, falta perigosa, expulsão ou time desesperado'
    }
  },
  ritmo: {
    type: 'choice',
    instructions: 'Qual o ritmo ofensivo atual da partida?',
    criteria: { lento: 'jogo parado ou cadenciado', normal: 'ritmo médio de liga', acelerado: 'trocas de ataque intensas' }
  },
  truncado: {
    type: 'noul',
    instructions: 'O jogo está truncado, com baixa criação de chances pelos dois lados?'
  },
  pressao_desbalanceada: {
    type: 'noul',
    instructions: 'Um time pressiona muito mais que o outro neste momento?'
  }
};

// ---- Preenchimento rápido: lê o Ctrl+C do Fut Odds ----
// Acumulativo: cada colagem traz só a aba que estava aberta e preenche o que
// reconhece, sem nunca limpar campo já preenchido. Cole Press., Prob., Stats e
// Odds em sequência e o formulário vai se completando.

const lvPN = s => { const v = parseFloat(String(s).replace(',', '.')); return isNaN(v) ? null : v; };

// pares "<casa> RÓTULO <fora>" das abas Press. e Stats
const LV_PARES = [
  [/([\d.,]+)\s+\bAPPM\b\s+([\d.,]+)/i, 'APPM', 'lvAPPM', 'soma'],
  [/([\d.,]+)\s+\bAPPM10\b\s+([\d.,]+)/i, 'APPM10', 'lvAPPM10', 'soma'],
  [/([\d.,]+)\s+\bCG\b\s+([\d.,]+)/i, 'CG', 'lvCG', 'soma'],
  [/([\d.,]+)\s+\bCG10\b\s+([\d.,]+)/i, 'CG10', 'lvCG10', 'soma'],
  [/([\d.,]+)\s+\bPI1\b\s+([\d.,]+)/i, 'PI1', 'lvPI1', 'soma'],
  [/([\d.,]+)\s+\bPI2\b\s+([\d.,]+)/i, 'PI2', 'lvPI2', 'soma'],
  [/([\d.,]+)\s+\bPI3\b\s+([\d.,]+)/i, 'PI3', 'lvPI3', 'soma'],
  [/([\d.,]+)\s+\bH2H\b\s+([\d.,]+)/i, 'H2H', null, 'soma'],
  [/([\d.,]+)\s*%\s+Posse de Bola\s+([\d.,]+)\s*%/i, 'Posse', 'lvPosse', 'casa'],
  [/([\d.,]+)\s+xG\s*\(Expected Goals\)\s+([\d.,]+)/i, 'xG', 'lvXG', 'soma'],
  [/([\d.,]+)\s+Ataques Perigosos\s+([\d.,]+)/i, 'Atq. perig.', 'lvAPC|lvAPF', 'ambos'],
  [/([\d.,]+)\s+Finaliza[çc][õo]es\s+([\d.,]+)/i, 'Finaliz.', 'lvFinC|lvFinF', 'ambos'],
  [/([\d.,]+)\s+Escanteios\s+([\d.,]+)/i, 'Escanteios', 'lvEscC|lvEscF', 'ambos'],
];

const LV_ROTULOS = {
  lvMin: 'minuto', lvGolsC: 'gols casa', lvGolsF: 'gols fora', lvOddLive: 'odd live',
  lvOddPre: 'odd pré', lvLinha: 'linha', lvWinC: 'vit. casa', lvEmp: 'empate', lvWinF: 'vit. fora',
  lvOver25: 'over 2.5 proj.', lvAPPM: 'APPM som.', lvAPPM10: 'APPM10 som.', lvCG: 'CG som.', lvCG10: 'CG10 som.',
  lvPI1: 'PI1 som.', lvPI2: 'PI2 som.', lvPI3: 'PI3 som.', lvXG: 'xG som.', lvPosse: 'posse casa',
  lvAPC: 'atq.perig. casa', lvAPF: 'atq.perig. fora', lvFinC: 'finaliz. casa',
  lvFinF: 'finaliz. fora', lvEscC: 'escant. casa', lvEscF: 'escant. fora',
};

function lvParse(txt) {
  const t = String(txt || '').replace(/ /g, ' ').replace(/[–—]/g, '-');
  const campos = {}, info = [];
  let overLive = null;
  const por = (re, fn) => { const m = t.match(re); if (m) fn(m); };

  // cabeçalho (vem junto em qualquer aba)
  por(/(\d{1,3})\s*'/, m => { const v = lvPN(m[1]); if (v !== null && v <= 95) campos.lvMin = v; });

  const placar = [...t.matchAll(/\(\s*\d+\s*[ºo°]\s*\)\s*(\d+)\b/g)];
  if (placar.length >= 2) { campos.lvGolsC = lvPN(placar[0][1]); campos.lvGolsF = lvPN(placar[1][1]); }

  const times = [...t.matchAll(/([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 .'-]{1,40}?)\s*\(\s*\d+\s*[ºo°]\s*\)/g)].map(m => {
    let n = m[1].replace(/\s*\blogo\b\s*/gi, '|').split('|').pop().trim();
    const meio = Math.floor(n.length / 2);          // "FAR RabatFAR Rabat" -> "FAR Rabat"
    if (n.length % 2 === 0 && n.slice(0, meio) === n.slice(meio)) n = n.slice(0, meio).trim();
    return n;
  });

  // 8 números do cabeçalho: linha 1 = pré-live, linha 2 = ao vivo
  por(/Casa\s+([\d.,]+)\s+Empate\s+([\d.,]+)\s+Fora\s+([\d.,]+)\s+Over\s*2[.,]5\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)/i,
    m => {
      overLive = lvPN(m[8]);              // over 2.5 ao vivo: referência de mercado
      info.push('1x2 pré ' + m[1] + '/' + m[2] + '/' + m[3] + ' · ao vivo ' + m[5] + '/' + m[6] + '/' + m[7]
                 + ' · over 2.5 ' + m[4] + ' → ' + m[8]);
    });

  // abas Press. e Stats
  for (const [re, rot, alvo, modo] of LV_PARES) {
    por(re, m => {
      const c = lvPN(m[1]), f = lvPN(m[2]);
      if (c === null || f === null) return;
      info.push(rot + ' ' + c + '×' + f + (modo === 'soma' ? ' = ' + +(c + f).toFixed(2) : ''));
      if (!alvo) return;
      if (modo === 'ambos') { const [a, b] = alvo.split('|'); campos[a] = c; campos[b] = f; }
      else if (modo === 'casa') campos[alvo] = c;
      else campos[alvo] = +(c + f).toFixed(2);          // soma: patamar do Fut Odds e combinado
    });
  }

  // aba Prob. (Futodds)
  por(/Casa\s*\(FT\)\s*([\d.,]+)\s*%/i, m => campos.lvWinC = lvPN(m[1]));
  por(/Empate\s*\(FT\)\s*([\d.,]+)\s*%/i, m => campos.lvEmp = lvPN(m[1]));
  por(/Fora\s*\(FT\)\s*([\d.,]+)\s*%/i, m => campos.lvWinF = lvPN(m[1]));
  por(/Over\s*2[.,]5\s*FT\s*([\d.,]+)\s*%/i, m => campos.lvOver25 = lvPN(m[1]));

  // aba Odds -> Over/Under do tempo regulamentar (ignora o 1º tempo).
  // A exchange dá 4 preços por linha: over back, over lay, under back, under lay.
  // Interessa o under BACK (é o que se aposta); o lay fica só no diagnóstico.
  const reg = t.split(/Total de Gols\s*-\s*Primeiro Tempo/i)[0];
  const partes = reg.split(/Total de Gols\s*-\s*Tempo Regulamentar/i);
  const linhas = {};
  if (partes.length > 1) {
    for (const m of partes[1].matchAll(/(\d+[.,]5)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)/g)) {
      const u = lvPN(m[4]);
      if (u !== null && u >= 1.01)
        linhas[lvPN(m[1])] = { over: lvPN(m[2]), under: u, underLay: lvPN(m[5]) };
    }
  }
  if (Object.keys(linhas).length)
    info.push('under back/lay por linha: '
      + Object.entries(linhas).map(([k, v]) => k + ' ' + v.under + '/' + v.underLay).join(' · '));

  // frase de momento do Fut Odds -> vira contexto para o Jev
  let frase = null;
  const antes = t.split(/under limite|Casa\s+[\d.,]+\s+Empate/i)[0];
  const corte = [...antes.matchAll(/Jogou (?:em casa|fora)|\d{2}\/\d{2}/g)].pop();
  if (corte) {
    const cand = antes.slice(corte.index + corte[0].length).replace(/\s+/g, ' ').trim();
    if (cand.length > 8) frase = cand;
  }

  return { campos, info, times, frase, linhas, overLive };
}

// contexto acumulado entre colagens (cada aba traz só um pedaço)
let lvAuto = { times: null, frase: null, press: {} };
// a odd live default (1.80) nunca deve virar veredito: so conta se veio de colagem
let lvOddDeColagem = false, lvRefOver = null;
const LV_CTX_ORDEM = ['PI1', 'PI2', 'PI3', 'CG', 'Atq. perig.', 'Finaliz.'];
// patamares combinados do Fut Odds a partir dos quais o indicador favorece over
const LV_PATAMAR = { PI1: 70, PI2: 12, PI3: 8 };

function lvColar() {
  const txt = $('lvPaste').value;
  const r = lvParse(txt);
  const postos = [];

  for (const [id, v] of Object.entries(r.campos)) {
    if (v === null || !$(id)) continue;
    $(id).value = String(v);
    postos.push((LV_ROTULOS[id] || id) + ' ' + v);
  }

  // odd live do under: linha da tabela Over/Under que bate com a linha escolhida
  const linha = parseFloat($('lvLinha').value);
  if (r.linhas[linha]) {
    $('lvOddLive').value = String(r.linhas[linha].under);
    lvOddDeColagem = true;
    postos.push('odd live ' + r.linhas[linha].under + ' (under ' + linha + ', back)');
  } else if (Object.keys(r.linhas).length) {
    postos.push('⚠ tabela de odds lida, mas sem a linha ' + linha);
  }
  if (r.overLive) lvRefOver = r.overLive;

  // contexto do Jev: acumula por rótulo; trocar de jogo zera o acumulado
  const times = r.times.length >= 2 ? r.times[0] + ' × ' + r.times[1] : null;
  if (times && lvAuto.times && times !== lvAuto.times) {
    lvAuto = { times: null, frase: null, press: {} };
    lvOddDeColagem = false; lvRefOver = null;        // jogo novo: odd anterior nao vale mais
  }
  if (times) lvAuto.times = times;
  if (r.frase) lvAuto.frase = r.frase;
  for (const i of r.info) {
    const rot = LV_CTX_ORDEM.find(o => i.startsWith(o + ' '));
    if (!rot) continue;
    const lim = LV_PATAMAR[rot], soma = parseFloat((i.split(' = ')[1] || ''));
    lvAuto.press[rot] = lim && !isNaN(soma)
      ? i + (soma >= lim ? ' — ACIMA do patamar de over (' + lim + ')'
                         : ' (patamar de over ' + lim + ')')
      : i;
  }
  const press = LV_CTX_ORDEM.filter(o => lvAuto.press[o]).map(o => lvAuto.press[o]).join(' · ');
  const auto = [lvAuto.times, lvAuto.frase, press].filter(Boolean);
  if (auto.length) {
    const manual = $('lvCtx').value.split('\n').filter(l => !l.startsWith('[auto]')).join('\n').trim();
    $('lvCtx').value = '[auto] ' + auto.join(' — ') + (manual ? '\n' + manual : '');
  }

  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const alerta = (postos.length && !lvOddDeColagem)
    ? '<br><b style="color:var(--amarelo)">⚠ Odd live não veio nesta colagem</b> — está em '
      + esc($('lvOddLive').value) + ', que é valor antigo. No Fut Odds abra <b>Odds → Over/Under</b> '
      + '(a sub-aba Principais não traz a linha de gols) e cole de novo, ou digite a odd à mão.'
    : '';
  $('lvPasteMsg').innerHTML = postos.length
    ? '<b>Preenchido:</b> ' + esc(postos.join(' · '))
      + (r.info.length ? '<br><span class="nota">Lido: ' + esc(r.info.join(' · ')) + '</span>' : '') + alerta
    : '<b>Nada reconhecido nesse texto.</b> Copie a tela do jogo no Fut Odds (abas Press., Prob., Stats ou Odds) e cole aqui.';
  return postos.length > 0;
}

const lvNum = id => { const v = parseFloat($(id).value); return isNaN(v) ? null : v; };
let lvMargem = 0.05;

function initLive() {
  chipsDo('lvMargens', [{ label: '0%', v: 0 }, { label: '5%', v: .05 }, { label: '10%', v: .10 }],
    it => lvMargem === it.v, it => { lvMargem = it.v; });
  $('lvPrecificar').onclick = lvPrecificar;
  $('lvColarBtn').onclick = lvColar;
  // colar ja preenche: o botao vira so um reforco
  $('lvPaste').addEventListener('paste', () => setTimeout(lvColar, 0));
}

async function lvPrecificar() {
  const golsC = lvNum('lvGolsC'), golsF = lvNum('lvGolsF'), min = lvNum('lvMin');
  const oddLive = lvNum('lvOddLive'), oddPre = lvNum('lvOddPre'), linha = lvNum('lvLinha');
  if (golsC === null || golsF === null || min === null || !oddLive || !oddPre || !linha) {
    $('lvResultado').style.display = '';
    $('lvVeredito').className = 'veredito v-amarelo';
    $('lvVeredito').textContent = 'Preencha gols, minuto, odds e linha.';
    return;
  }
  const gols = golsC + golsF;
  if (Math.floor(linha) - gols < 0) {
    $('lvResultado').style.display = '';
    $('lvVeredito').className = 'veredito v-vermelho';
    $('lvVeredito').textContent = 'Under já perdido — o placar passou da linha.';
    $('lvMetricas').innerHTML = ''; $('lvDecaimento').innerHTML = ''; $('lvBacktest').innerHTML = ''; $('lvJev').innerHTML = '';
    return;
  }

  // λ base: prioriza o % over 2.5 projetado se informado (sem margem da casa)
  const over25 = lvNum('lvOver25');
  let lamTotal, fonteLam;
  if (over25 !== null) {
    lamTotal = lambdaDaProb(1 - over25 / 100, 2.5);
    fonteLam = `% over 2.5 projetado (${over25}%)`;
  } else {
    lamTotal = lambdaDaProb(1 / oddPre, linha);
    fonteLam = `odd under ${linha} pré-live (${oddPre}) — inclui margem da casa`;
  }

  const base = precoUnder(lamTotal, min, linha, gols, 1);

  // coleta do estado p/ o Jev
  const estado = {
    placar: `${golsC}x${golsF}`, minuto: min, linha_under: linha,
    odd_live: oddLive, odd_pre: oddPre,
    odd_base_modelo: +base.odd.toFixed(3),
    lambda_total_estimado: +lamTotal.toFixed(2),
    probs_pct: { vitoria_casa: lvNum('lvWinC'), empate: lvNum('lvEmp'), vitoria_fora: lvNum('lvWinF'), over_25_pre: over25 },
    pressao: { appm: lvNum('lvAPPM'), appm10: lvNum('lvAPPM10'), cg: lvNum('lvCG'), cg10: lvNum('lvCG10'),
               pi1: lvNum('lvPI1'), pi2: lvNum('lvPI2'), pi3: lvNum('lvPI3'), xg: lvNum('lvXG') },
    volume: { posse_casa: lvNum('lvPosse'), ataques_perigosos_casa: lvNum('lvAPC'), ataques_perigosos_fora: lvNum('lvAPF'),
              finalizacoes_casa: lvNum('lvFinC'), finalizacoes_fora: lvNum('lvFinF'), escanteios_casa: lvNum('lvEscC'), escanteios_fora: lvNum('lvEscF') },
    contexto: $('lvCtx').value.trim() || null
  };

  // consulta Jev (via relay)
  let mult = 1, jevHtml = '', ans = null;
  if (jevRelay()) {
    $('lvPrecificar').disabled = true;
    $('lvPrecificar').textContent = 'Consultando Jev…';
    const r = await jevChamar(estado, LV_QUESTOES, false);
    $('lvPrecificar').disabled = false;
    $('lvPrecificar').textContent = 'Precificar under';
    if (r.erro || !r.ans.ameaca) {
      jevHtml = `<b>Jev indisponível:</b> ${r.erro || 'resposta sem os campos esperados'} — mostrando só o modelo base.`;
    } else {
      ans = r.ans;
      const pa = ans.ameaca.probabilities || {};
      const pr = ans.ritmo ? (ans.ritmo.probabilities || {}) : {};
      const multAmeaca = 0.80 * (pa.baixa || 0) + 1.00 * (pa.moderada || 0) + 1.40 * (pa.alta || 0);
      const multRitmo = 0.90 * (pr.lento || 0) + 1.00 * (pr.normal || 0) + 1.15 * (pr.acelerado || 0);
      const multTrunc = 1 - 0.15 * (ans.truncado ? ans.truncado.noul : 0);
      mult = Math.min(1.70, Math.max(0.55, multAmeaca * multRitmo * multTrunc));
      const txtAmeaca = Object.entries(pa).map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(' · ');
      const txtRitmo = Object.entries(pr).map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(' · ');
      jevHtml = `<b>Jev — ameaça de gol:</b> ${ans.ameaca.choice} (${txtAmeaca})<br>` +
                (txtRitmo ? `<b>Ritmo:</b> ${ans.ritmo.choice} (${txtRitmo})<br>` : '') +
                `<b>P(truncado):</b> ${((ans.truncado ? ans.truncado.noul : 0) * 100).toFixed(0)}% · ` +
                `<b>P(pressão desbalanceada):</b> ${((ans.pressao_desbalanceada ? ans.pressao_desbalanceada.noul : 0) * 100).toFixed(0)}%<br>` +
                `<b>Ajuste aplicado ao λ:</b> ameaça ×${multAmeaca.toFixed(2)} · ritmo ×${multRitmo.toFixed(2)} · truncado ×${multTrunc.toFixed(2)} → <b>×${mult.toFixed(2)}</b>`;
    }
  } else {
    jevHtml = '<b>Sem relay configurado:</b> precificação sem ajuste de contexto (só tempo + odd pré). Configure na aba <b>Conexão Jev</b>.';
  }

  const final = precoUnder(lamTotal, min, linha, gols, mult);
  const ev = oddLive * final.p - 1;
  const oddMin = final.odd * (1 + lvMargem);

  // a odd live e a unica entrada que o modelo nao sabe conferir sozinho: se ela nao
  // veio de colagem, ou destoa do mercado, nenhum EV+ pode sair como verde confiante
  const avisos = [];
  if (!lvOddDeColagem)
    avisos.push('a odd live ' + fmtOdd(oddLive) + ' não foi preenchida por colagem — confira em Odds → Over/Under');
  if (lvRefOver && linha === 2.5 && lvRefOver > 1.01) {
    const underMercado = 1 / (1 - 1 / lvRefOver);       // implicada pelo over 2.5 ao vivo
    if (oddLive > underMercado * 1.25)
      avisos.push('o over 2.5 ao vivo estava ' + fmtOdd(lvRefOver) + ', o que implica under ≈ '
        + fmtOdd(underMercado) + ' — a odd live informada não existe nesse mercado');
  }

  const vd = $('lvVeredito');
  if (ev >= 0 && avisos.length) {
    vd.className = 'veredito v-amarelo';
    vd.innerHTML = '⚠ EV+ NÃO CONFIÁVEL — ' + avisos.join('; ')
      + '<br><span class="nota">O EV abaixo só vale depois de corrigir isso.</span>';
  }
  else if (ev >= 0 && oddLive >= oddMin) { vd.className = 'veredito v-verde'; vd.textContent = '✔ EV+ — odd live acima da justa precificada com margem'; }
  else if (ev >= 0) { vd.className = 'veredito v-amarelo'; vd.textContent = '◑ EV+ NO LIMITE — acima da justa, mas sem a margem'; }
  else { vd.className = 'veredito v-vermelho'; vd.textContent = '✖ EV− — odd live abaixo da justa precificada'; }

  $('lvMetricas').innerHTML =
    `<div class="metrica"><div class="k">Odd base (só tempo)</div><div class="v">${fmtOdd(base.odd)}</div></div>` +
    `<div class="metrica"><div class="k">Ajuste Jev (λ)</div><div class="v">×${mult.toFixed(2)}</div></div>` +
    `<div class="metrica"><div class="k">Odd justa final</div><div class="v">${fmtOdd(final.odd)}</div></div>` +
    `<div class="metrica"><div class="k">EV da odd ${fmtOdd(oddLive)}</div><div class="v" style="color:${ev >= 0 ? 'var(--verde)' : 'var(--vermelho)'}">${(ev >= 0 ? '+' : '') + fmtPct(ev)}</div></div>`;

  // curva de decaimento (próximos 5 min)
  let linhas = '<tr><th>Minuto</th><th>Odd justa</th><th>Queda vs agora</th></tr>';
  for (let d = 0; d <= 5; d++) {
    const f = precoUnder(lamTotal, Math.min(94, min + d), linha, gols, mult);
    const queda = d === 0 ? '—' : fmtPct(1 - f.odd / final.odd);
    linhas += `<tr><td>${min + d}'</td><td>${fmtOdd(f.odd)}</td><td>${d === 0 ? '—' : '−' + queda}</td></tr>`;
  }
  const f5 = precoUnder(lamTotal, Math.min(94, min + 5), linha, gols, mult);
  const quedaPorMin = (1 - f5.odd / final.odd) / 5 * 100;
  linhas += `<tr style="border-top:2px solid var(--borda)"><td colspan="3"><b>Queda média esperada: ${quedaPorMin.toFixed(1)}% da odd por minuto</b> (modelo, sem Jev refeito a cada minuto)</td></tr>`;
  $('lvDecaimento').innerHTML = linhas;

  // comparador com backtest, se o placar/minuto existir nos dados
  const placar = `${golsC}-${golsF}`;
  let bt = '';
  if (PLACARES.includes(placar)) {
    const periodo = min < 45 ? 'ht' : 'ft';
    const { pts, usouGeral } = pontosCalc(periodo, placar);
    if (pts.length) {
      const it = interpola(pts, min);
      const justaBT = 1 / it.p;
      const div = final.odd / justaBT;
      bt = `<b>Comparador backtest:</b> ${periodo.toUpperCase()} ${placarFmt(placar)} · justa ${fmtOdd(justaBT)}${usouGeral ? ' (taxa geral — placar sem amostra)' : ''}` +
           ` · modelo+Jev ${fmtOdd(final.odd)} → ${div > 1.05 ? 'modelo mais pessimista' : div < 0.95 ? 'modelo mais otimista' : 'alinhados'} (${div >= 1 ? '+' : ''}${((div - 1) * 100).toFixed(0)}%)${it.extra ? ' · <b>minuto fora da faixa medida</b>' : ''}`;
    }
  }
  $('lvBacktest').innerHTML = bt || `Sem célula de backtest para ${placarFmt(placar)} — sem comparador.`;

  $('lvJev').innerHTML = jevHtml;
  $('lvResultado').style.display = '';
}

// ================= análise por estatística =================
const extrasDe = r => r[5] || {};
let CENARIOS_STATS = [];

function initStats() {
  const cols = DADOS.stats_cols || [];
  if (!cols.length) return; // sem stats nos CSVs — seção fica oculta
  $('cardStats').style.display = '';

  CENARIOS_STATS = [];
  BUCKETS.forEach((b, i) => {
    for (const p of PLACARES) {
      const rows = rowsCenario(i, p);
      if (rows.length >= 150)
        CENARIOS_STATS.push({ i, p, rows, label: `${b.periodo.toUpperCase()} ${b.label}' · ${placarFmt(p)} (n=${fmtN(rows.length)})` });
    }
  });
  $('sCenario').innerHTML = CENARIOS_STATS.map((c, j) => `<option value="${j}">${c.label}</option>`).join('');
  $('sStat').innerHTML = cols.map(c => `<option value="${c}">${c}</option>`).join('');
  $('sCenario').onchange = renderStats;
  $('sStat').onchange = renderStats;
  renderStats();
}

function renderStats() {
  const cen = CENARIOS_STATS[+($('sCenario').value || 0)];
  const col = $('sStat').value;
  if (!cen || !col) return;

  const comStat = cen.rows.filter(r => !isNaN(parseFloat(extrasDe(r)[col])));
  const vals = comStat.map(r => parseFloat(extrasDe(r)[col])).sort((a, b) => a - b);
  const el = $('sResultado');

  if (vals.length < 150) {
    el.innerHTML = `<div class="veredito v-amarelo">Só ${fmtN(vals.length)} entradas têm "${col}" preenchido neste cenário — abaixo do mínimo de 150 para segmentar.</div>`;
    return;
  }
  const q1 = vals[Math.floor(vals.length / 3)], q2 = vals[Math.floor(vals.length * 2 / 3)];
  const grupos = [
    { nome: `${q1.toFixed(1)} ou menos`, sel: comStat.filter(r => parseFloat(extrasDe(r)[col]) <= q1) },
    { nome: `${q1.toFixed(1)} – ${q2.toFixed(1)}`, sel: comStat.filter(r => { const v = parseFloat(extrasDe(r)[col]); return v > q1 && v <= q2; }) },
    { nome: `mais de ${q2.toFixed(1)}`, sel: comStat.filter(r => parseFloat(extrasDe(r)[col]) > q2) },
  ];
  const geral = resumo(comStat);

  let html = '<tr><th>Faixa da stat</th><th>n</th><th>Green</th><th>Odd justa</th><th>ROI</th><th>Lucro</th></tr>';
  for (const g of grupos) {
    const s = resumo(g.sel);
    const cls = s.roi >= 0 ? 'pos' : 'neg';
    html += `<tr><td>${g.nome}</td><td>${fmtN(s.n)}</td><td>${fmtPct(s.green)}</td><td>${fmtOdd(s.justa)}</td>` +
            `<td class="${cls}">${(s.roi >= 0 ? '+' : '') + fmtPct(s.roi)}</td>` +
            `<td class="${cls}">${(s.lucro >= 0 ? '+' : '') + s.lucro.toFixed(0)}</td></tr>`;
  }
  html += `<tr style="border-top:2px solid var(--borda)"><td><b>Todas com stat</b></td><td>${fmtN(geral.n)}</td>` +
          `<td>${fmtPct(geral.green)}</td><td>${fmtOdd(geral.justa)}</td>` +
          `<td class="${geral.roi >= 0 ? 'pos' : 'neg'}">${(geral.roi >= 0 ? '+' : '') + fmtPct(geral.roi)}</td>` +
          `<td class="${geral.roi >= 0 ? 'pos' : 'neg'}">${(geral.lucro >= 0 ? '+' : '') + geral.lucro.toFixed(0)}</td></tr>`;
  el.innerHTML = `<div class="scroll"><table class="dados">${html}</table></div>`;
}

// ================= init =================
(function init() {
  const total = ROWS.length;
  const ht = BUCKETS.filter(b => b.periodo === 'ht').length, ft = BUCKETS.filter(b => b.periodo === 'ft').length;
  $('resumoDados').textContent = `${fmtN(total)} entradas analisadas · ${ht} backtests HT + ${ft} FT · dados de ${DADOS.gerado_em}`;
  $('cMin').addEventListener('input', renderCalc);
  $('cOdd').addEventListener('input', renderCalc);
  renderCalc();
  renderMapa();
  renderCobertura();
  initStats();
  initCfg();
  initLive();
})();
</script>
</body>
</html>
"""


def main():
    buckets, linhas, stats_cols = coletar()
    if not linhas:
        raise SystemExit("Nenhum CSV encontrado nas pastas 'under limite *'.")

    dados = {
        "gerado_em": __import__("datetime").date.today().isoformat(),
        "placares": PLACARES,
        "buckets": buckets,
        "rows": linhas,
        "stats_cols": stats_cols,
    }
    html = HTML_TEMPLATE.replace(
        "/*__DATA__*/", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Gerado: {ARQUIVO_SAIDA} ({len(linhas)} entradas)")
    for i, b in enumerate(buckets):
        wins = sum(r[4] for r in linhas if r[0] == i)
        print(f"  {b['periodo'].upper()} min {b['label']}: n={b['n']} green={wins/b['n']*100:.1f}%")


if __name__ == "__main__":
    main()
