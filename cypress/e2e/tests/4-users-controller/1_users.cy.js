/**
 * E2E tests for the Users controller.
 * Generates GET traffic for user endpoints.
 */
import { urls } from "../../../support/pages/urls";

describe("JSONPlaceholder - Users", () => {
  it("GET - List all users", () => {
    cy.apiFetch({
      url: urls.users,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length(10);
    });
  });

  it("GET - Get user by ID", () => {
    cy.apiFetch({
      url: urls.userById(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.property("id", 1);
    });
  });

  it("GET - List posts by user", () => {
    cy.apiFetch({
      url: urls.userPosts(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });
});
