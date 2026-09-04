/**
 * Centralizes all tested endpoint URLs.
 * Using a centralized file makes maintenance easier and
 * allows swapping the API easily in the future.
 *
 * JSONPlaceholder provides the following resources:
 * /posts (100 posts), /comments (500 comments), /albums (100 albums),
 * /photos (5000 photos), /todos (200 todos), /users (10 users)
 */

const baseUrl =
  Cypress.env("apiUrl") || "https://jsonplaceholder.typicode.com";

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
