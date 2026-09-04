#!/usr/bin/env node
/**
 * Gera as evidencias visuais do README a partir de execucoes reais.
 *
 * Nada aqui e montado. O texto vem dos arquivos que o proprio pipeline
 * produziu — saida do Cypress, do processamento e do scan — e as imagens sao
 * renderizacoes desse texto, com o arquivo de origem citado no rodape de cada
 * uma para que qualquer numero possa ser conferido.
 *
 * Requer o Chrome instalado, que ja e pre-requisito do projeto: o Cypress
 * roda com --browser chrome. O playwright-core dirige o navegador existente em
 * vez de baixar outro.
 *
 * Uso:
 *   node scripts/generate-evidence.mjs --terminal <arquivo.txt> --saida <nome>
 *   node scripts/generate-evidence.mjs --relatorio <relatorio.html>
 */
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const DESTINO = join(RAIZ, "docs", "assets");

/** Remove os codigos de cor ANSI, que virariam lixo visivel na imagem. */
function limparAnsi(texto) {
  // eslint-disable-next-line no-control-regex
  return texto.replace(/\[[0-9;]*m/g, "");
}

function escapar(texto) {
  return texto
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Colore apenas marcadores e cabecalhos. Nenhum valor e alterado. */
function colorir(texto) {
  return escapar(texto)
    .replace(/^(.*\b(ERROR|FAILED|✖)\b.*)$/gm, '<span class="erro">$1</span>')
    .replace(
      /^(.*\b(PASS|passed|✓|✔|OK|SUCCESS)\b.*)$/gm,
      '<span class="ok">$1</span>',
    )
    .replace(
      /^(\s*(?:---\s*)?(?:PHASE|FASE)[^\n]*)$/gm,
      '<span class="fase">$1</span>',
    )
    .replace(/^(.*\[High\].*)$/gm, '<span class="alto">$1</span>')
    .replace(
      /^(.*\[(?:Medium|Low|Informational)\].*)$/gm,
      '<span class="medio">$1</span>',
    );
}

function montarPagina(conteudo, titulo, rodape, largura) {
  return `<!doctype html><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #0d1117; font-family: 'Cascadia Code','Consolas','DejaVu Sans Mono',monospace; }
  .janela { width: ${largura}px; background: #0d1117; border: 1px solid #30363d; border-radius: 10px; overflow: hidden; }
  .barra { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #161b22; border-bottom: 1px solid #30363d; }
  .bolinha { width: 11px; height: 11px; border-radius: 50%; }
  .titulo { margin-left: 10px; color: #8b949e; font-size: 12.5px; }
  pre { margin: 0; padding: 16px 20px 20px; color: #c9d1d9; font-size: 12.6px; line-height: 1.5; white-space: pre; }
  .ok { color: #3fb950; }
  .erro { color: #f85149; }
  .fase { color: #58a6ff; font-weight: 700; }
  .alto { color: #f85149; font-weight: 700; }
  .medio { color: #d29922; }
  .rodape { padding: 9px 20px 12px; color: #6e7681; font-size: 11.4px; border-top: 1px solid #21262d; }
</style>
<div class="janela">
  <div class="barra">
    <span class="bolinha" style="background:#ff5f57"></span>
    <span class="bolinha" style="background:#febc2e"></span>
    <span class="bolinha" style="background:#28c840"></span>
    <span class="titulo">${escapar(titulo)}</span>
  </div>
  <pre>${colorir(conteudo)}</pre>
  <div class="rodape">${escapar(rodape)}</div>
</div>`;
}

function argumento(nome) {
  const i = process.argv.indexOf(nome);
  return i === -1 ? undefined : process.argv[i + 1];
}

async function capturar(html, arquivoDeSaida) {
  const navegador = await chromium.launch({ channel: "chrome" });
  const pagina = await navegador.newPage({ deviceScaleFactor: 2 });
  await pagina.setContent(html);
  mkdirSync(DESTINO, { recursive: true });
  const caminho = join(DESTINO, arquivoDeSaida);
  await pagina.locator(".janela").screenshot({ path: caminho });
  await navegador.close();
  return caminho;
}

async function main() {
  const relatorio = argumento("--relatorio");

  if (relatorio) {
    if (!existsSync(relatorio)) {
      process.stderr.write(
        `[evidencias] Relatorio nao encontrado: ${relatorio}\n`,
      );
      process.exit(1);
    }

    const navegador = await chromium.launch({ channel: "chrome" });
    const pagina = await navegador.newPage({
      viewport: { width: 1280, height: 900 },
    });
    await pagina.goto(`file://${relatorio.replace(/\\/g, "/")}`);
    await pagina.waitForTimeout(1500);
    mkdirSync(DESTINO, { recursive: true });
    const caminho = join(DESTINO, "relatorio-zap.png");
    await pagina.screenshot({ path: caminho });
    await navegador.close();
    process.stdout.write(`[evidencias] ${caminho}\n`);
    return;
  }

  const origem = argumento("--terminal");
  const saida = argumento("--saida");

  if (!origem || !saida) {
    process.stderr.write(
      "Uso: node scripts/generate-evidence.mjs --terminal <arquivo.txt> --saida <nome.png>\n",
    );
    process.exit(1);
  }

  const bruto = limparAnsi(readFileSync(origem, "utf8"));
  const linhas = bruto
    .split(/\r?\n/)
    .filter((linha) => linha.trim().length > 0);
  const largura = Math.min(
    1180,
    Math.max(760, 9 * Math.max(...linhas.map((l) => l.length)) + 60),
  );

  const html = montarPagina(
    linhas.join("\n"),
    argumento("--titulo") ?? basename(origem),
    `Saida real do pipeline. Origem: ${basename(origem)}`,
    largura,
  );

  const caminho = await capturar(html, saida);
  const kb = Math.round(statSync(caminho).size / 1024);
  process.stdout.write(`[evidencias] ${caminho} (${kb} kB)\n`);
}

main().catch((erro) => {
  process.stderr.write(`[evidencias] ${erro.message}\n`);
  process.exit(1);
});
