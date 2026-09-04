/**
 * E2E tests for the Todos controller.
 * Generates GET and POST traffic for todo endpoints.
 */
import { urls } from "../../../support/pages/urls";
import { payloads } from "../../../support/pages/payloads";

describe("JSONPlaceholder - Todos", () => {
  it("GET - List all todos", () => {
    cy.apiFetch({
      url: urls.todos,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });

  it("GET - Get todo by ID", () => {
    cy.apiFetch({
      url: urls.todoById(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.property("id", 1);
    });
  });

  it("POST - Create new todo", () => {
    cy.apiFetch({
      url: urls.todos,
      method: "POST",
      body: payloads.createTodo,
    }).then((response) => {
      expect(response.status).to.eq(201);
    });
  });
});
