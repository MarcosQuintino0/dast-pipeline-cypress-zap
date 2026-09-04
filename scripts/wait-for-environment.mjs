#!/usr/bin/env node
/**
 * Aguarda o ambiente do pipeline ficar realmente pronto.
 *
 * O criterio e o estado observavel de cada servico — a API devolvendo dados e
 * a API do ZAP devolvendo sua versao — e nunca uma espera fixa. Um "sleep 30"
 * passa quando a maquina esta rapida e falha quando esta lenta, que e o pior
 * dos dois mundos.
 *
 * Serve tambem como diagnostico: com --once reporta o estado atual e encerra,
 * respondendo de imediato a pergunta "por que o scan nao roda?".
 *
 * Uso:
 *   node scripts/wait-for-environment.mjs
 *   node scripts/wait-for-environment.mjs --once
 */
import process from 'node:process';

const API_PORT = process.env.API_PORT ?? '3000';
const ZAP_HOST = process.env.ZAP_HOST ?? '127.0.0.1';
const ZAP_PORT = process.env.ZAP_PORT ?? '8080';
const ZAP_API_KEY = process.env.ZAP_API_KEY ?? 'dast-pipeline-local';

const TIMEOUT_MS = Number(process.env.WAIT_TIMEOUT_MS ?? 180_000);
const INTERVALO_MS = 2_000;
const APENAS_UMA_VEZ = process.argv.includes('--once');

const SERVICOS = [
  {
    nome: 'api',
    url: `http://localhost:${API_PORT}/posts?_limit=1`,
    interpretar: (corpo) => {
      const dados = JSON.parse(corpo);
      return {
        pronto: Array.isArray(dados) && dados.length > 0,
        detalhe: `alvo respondendo em :${API_PORT}`,
      };
    },
  },
  {
    nome: 'zap',
    url: `http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/version/?apikey=${ZAP_API_KEY}`,
    interpretar: (corpo) => {
      const { version } = JSON.parse(corpo);
      return { pronto: Boolean(version), detalhe: `OWASP ZAP ${version}` };
    },
  },
];

async function sondar(servico) {
  try {
    const resposta = await fetch(servico.url, { signal: AbortSignal.timeout(5_000) });
    if (!resposta.ok) return { pronto: false, detalhe: `HTTP ${resposta.status}` };
    return servico.interpretar(await resposta.text());
  } catch (erro) {
    if (erro.name === 'TimeoutError') return { pronto: false, detalhe: 'timeout' };
    if (erro instanceof SyntaxError) return { pronto: false, detalhe: 'resposta nao e JSON' };
    return { pronto: false, detalhe: 'sem resposta' };
  }
}

function relatar(resultados) {
  for (const { servico, pronto, detalhe } of resultados) {
    process.stdout.write(`  ${pronto ? 'OK   ' : 'FALHA'} ${servico.nome.padEnd(5)} ${detalhe}\n`);
  }
}

async function main() {
  const limite = Date.now() + TIMEOUT_MS;

  for (;;) {
    const resultados = await Promise.all(
      SERVICOS.map(async (servico) => ({ servico, ...(await sondar(servico)) })),
    );

    const pendentes = resultados.filter((resultado) => !resultado.pronto);

    if (pendentes.length === 0) {
      process.stdout.write('[ambiente] Pronto.\n');
      relatar(resultados);
      return;
    }

    if (APENAS_UMA_VEZ || Date.now() > limite) {
      process.stdout.write(
        APENAS_UMA_VEZ
          ? '[ambiente] Estado atual:\n'
          : `[ambiente] Tempo limite de ${TIMEOUT_MS}ms excedido.\n`,
      );
      relatar(resultados);
      process.stdout.write('\n  Suba o ambiente com: npm run env:up\n');
      process.exitCode = 1;
      return;
    }

    const nomes = pendentes.map((resultado) => resultado.servico.nome).join(', ');
    process.stdout.write(`[ambiente] Aguardando: ${nomes}\n`);
    await new Promise((resolve) => setTimeout(resolve, INTERVALO_MS));
  }
}

main();
