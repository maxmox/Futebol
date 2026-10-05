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
  .linha2 { display: flex; gap: 20px; flex-wrap: wrap; }

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
