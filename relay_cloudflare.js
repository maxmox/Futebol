// relay_cloudflare.js — Cloudflare Worker: destrava a API da TypeSafe no navegador
// =============================================================================
// A API da TypeSafe (api.typesafe.ai) rejeita chamadas de navegador (CORS).
// Este Worker recebe a requisição do site, repassa para a TypeSafe usando a SUA
// chave (que fica guardada no Worker, fora do repositório) e devolve com
// Access-Control-Allow-Origin: * — assim o site funciona com a chave TypeSafe.
//
// DEPLOY (grátis, ~5 min):
//   1. Crie conta em https://dash.cloudflare.com (plano gratuito, sem cartão)
//   2. Workers & Pages → Create Worker → Deploy (aceite o hello-world)
//   3. Edit code → apague tudo → cole este arquivo → Deploy
//   4. Settings → Variables and Secrets → Add secret:
//        Nome: TYPESAFE_API_KEY
//        Valor: sua chave (apikey_...)
//   5. Copie a URL do Worker (algo como https://jev-relay.SEU-USUARIO.workers.dev)
//   6. No site, aba Chave API: cole a URL no campo "URL do relay" e salve
//
// Custo do Worker: 100.000 requisições/dia gratuitas — praticamente infinito
// para este uso. A chamada ao Jev continua debitando seus créditos TypeSafe.
//
// SEGURANÇA: o Worker é público (qualquer um com a URL pode gastar sua chave).
// Para uso pessoal está ok; se a URL vazar, redeploy o Worker e troque a chave.

const UPSTREAM = "https://api.typesafe.ai/v1/systemone";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (request.method !== "POST")
      return new Response(JSON.stringify({ erro: "use POST" }), { status: 405, headers: CORS });

    const key = env.TYPESAFE_API_KEY;
    if (!key)
      return new Response(JSON.stringify({ erro: "TYPESAFE_API_KEY não configurada no Worker" }), { status: 500, headers: CORS });

    let corpo = request.body;
    try {
      const json = await request.json(); // valida e reempacota com o model da TypeSafe
      json.model = json.model && json.model.startsWith("typesafe/") ? "jev-latest" : (json.model || "jev-latest");
      corpo = JSON.stringify(json);
    } catch {
      return new Response(JSON.stringify({ erro: "JSON inválido" }), { status: 400, headers: CORS });
    }

    const resp = await fetch(UPSTREAM, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: corpo,
    });
    const texto = await resp.text();
    return new Response(texto, { status: resp.status, headers: { ...CORS, "Content-Type": "application/json" } });
  },
};
