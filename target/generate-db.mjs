#!/usr/bin/env node
/**
 * Gera o conjunto de dados do alvo local, com a mesma forma do JSONPlaceholder.
 *
 * Por que gerar em vez de baixar: o alvo precisa subir sem internet e sempre
 * com o mesmo conteudo. Um scan de seguranca comparado entre duas execucoes so
 * faz sentido se o alvo for identico nas duas.
 *
 * A geracao e deterministica — sem Math.random e sem data corrente — entao
 * rodar este script duas vezes produz exatamente o mesmo db.json.
 *
 * Uso: node target/generate-db.mjs
 */
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = dirname(fileURLToPath(import.meta.url));

/** Quantidades. Menores que as do JSONPlaceholder publico, o que esta documentado no README. */
const TOTAIS = { users: 10, posts: 100, comments: 500, albums: 100, photos: 500, todos: 200 };

/**
 * Gerador pseudoaleatorio com semente fixa (LCG).
 *
 * Existe para o texto variar entre registros sem que o resultado varie entre
 * execucoes. Math.random quebraria a reprodutibilidade do alvo.
 */
function criarSorteio(semente) {
  let estado = semente;
  return (limite) => {
    estado = (estado * 1103515245 + 12345) % 2147483648;
    return estado % limite;
  };
}

const sorteio = criarSorteio(20260904);

const PALAVRAS = [
  'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipisicing', 'elit',
  'quia', 'voluptas', 'nostrum', 'rerum', 'est', 'autem', 'sunt', 'reiciendis',
  'occaecati', 'fugiat', 'quas', 'totam', 'molestias', 'architecto', 'beatae',
];

function frase(minimo, maximo) {
  const total = minimo + sorteio(maximo - minimo + 1);
  const partes = Array.from({ length: total }, () => PALAVRAS[sorteio(PALAVRAS.length)]);
  return partes.join(' ');
}

function paragrafo(linhas) {
  return Array.from({ length: linhas }, () => frase(6, 12)).join('\n');
}

const users = Array.from({ length: TOTAIS.users }, (_, i) => {
  const id = i + 1;
  return {
    id,
    name: `Usuario ${id}`,
    username: `usuario${id}`,
    email: `usuario${id}@example.test`,
    address: {
      street: `Rua ${frase(1, 2)}`,
      suite: `Sala ${id * 7}`,
      city: `Cidade ${id}`,
      zipcode: `${10000 + id * 137}-${id * 3}`,
      geo: { lat: `${(-23.5 - id * 0.11).toFixed(4)}`, lng: `${(-46.6 - id * 0.09).toFixed(4)}` },
    },
    phone: `1-770-736-${String(8031 + id).padStart(4, '0')}`,
    website: `usuario${id}.example.test`,
    company: {
      name: `Empresa ${id}`,
      catchPhrase: frase(3, 5),
      bs: frase(2, 4),
    },
  };
});

const posts = Array.from({ length: TOTAIS.posts }, (_, i) => ({
  userId: (i % TOTAIS.users) + 1,
  id: i + 1,
  title: frase(4, 8),
  body: paragrafo(2),
}));

const comments = Array.from({ length: TOTAIS.comments }, (_, i) => ({
  postId: (i % TOTAIS.posts) + 1,
  id: i + 1,
  name: frase(3, 6),
  email: `comentarista${i + 1}@example.test`,
  body: paragrafo(2),
}));

const albums = Array.from({ length: TOTAIS.albums }, (_, i) => ({
  userId: (i % TOTAIS.users) + 1,
  id: i + 1,
  title: frase(3, 6),
}));

const photos = Array.from({ length: TOTAIS.photos }, (_, i) => {
  const id = i + 1;
  return {
    albumId: (i % TOTAIS.albums) + 1,
    id,
    title: frase(3, 7),
    url: `http://localhost:3000/static/photo-${id}.png`,
    thumbnailUrl: `http://localhost:3000/static/thumb-${id}.png`,
  };
});

const todos = Array.from({ length: TOTAIS.todos }, (_, i) => ({
  userId: (i % TOTAIS.users) + 1,
  id: i + 1,
  title: frase(3, 7),
  completed: i % 3 === 0,
}));

const db = { posts, comments, albums, photos, todos, users };

const destino = join(AQUI, 'db.json');
writeFileSync(destino, `${JSON.stringify(db, null, 2)}\n`, 'utf8');

const resumo = Object.entries(db)
  .map(([colecao, itens]) => `${colecao}=${itens.length}`)
  .join(' ');

process.stdout.write(`[alvo] db.json gerado: ${resumo}\n`);
