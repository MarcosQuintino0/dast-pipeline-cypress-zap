/**
 * Centralizes all request payloads (bodies) for POST/PUT.
 * Separating test data makes maintenance and reuse easier.
 *
 * The "userId" and "id" fields use numeric values that will be
 * replaced by {{AUTO_INT}} during HAR preprocessing.
 * This allows ZAP to vary the values during active scan,
 * avoiding duplicate key errors on the server.
 */

export const payloads = {
  createPost: {
    title: "DAST Security Test",
    body: "This post was created during automated DAST tests",
    userId: 1,
  },
  updatePost: {
    id: 1,
    title: "Post Updated by Scanner",
    body: "Content updated during DAST security testing",
    userId: 1,
  },
  createComment: {
    postId: 1,
    name: "DAST Test Comment",
    email: "dast@test.com",
    body: "Comment automatically generated for security testing",
  },
  createTodo: {
    userId: 1,
    title: "DAST test task",
    completed: false,
  },
};
