/**
 * Centraliza as URLs de todos os endpoints exercitados.
 *
 * O alvo e a API local subida por docker compose, com a mesma forma do
 * JSONPlaceholder: /posts, /comments, /albums, /photos, /todos e /users,
 * incluindo as rotas aninhadas /posts/:id/comments e /users/:id/posts.
 *
 * O valor padrao aponta para localhost de proposito.
 *
 * A versao anterior caia em https://jsonplaceholder.typicode.com quando a
 * variavel nao estava definida. Num projeto que gera trafego para alimentar um
 * scan de seguranca isso e uma armadilha: bastaria esquecer o cypress.env.json
 * para o pipeline passar a mirar, em silencio, uma API publica de terceiros.
 * O padrao seguro e o alvo que voce controla.
 */

const baseUrl = Cypress.env("apiUrl") || "http://localhost:3000";

export const urls = {
  // Posts
  posts: `${baseUrl}/posts`,
  postById: (id) => `${baseUrl}/posts/${id}`,
  postComments: (id) => `${baseUrl}/posts/${id}/comments`,

  // Comments
  comments: `${baseUrl}/comments`,

  // Todos
  todos: `${baseUrl}/todos`,
  todoById: (id) => `${baseUrl}/todos/${id}`,

  // Users
  users: `${baseUrl}/users`,
  userById: (id) => `${baseUrl}/users/${id}`,
  userPosts: (id) => `${baseUrl}/users/${id}/posts`,

  // Albums and Photos
  albums: `${baseUrl}/albums`,
  albumById: (id) => `${baseUrl}/albums/${id}`,
  albumPhotos: (id) => `${baseUrl}/albums/${id}/photos`,
  photos: `${baseUrl}/photos`,
};
