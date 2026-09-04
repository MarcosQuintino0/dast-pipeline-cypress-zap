/**
 * E2E tests for the Comments controller.
 * Generates GET and POST traffic for comment endpoints.
 */
import { urls } from "../../../support/pages/urls";
import { payloads } from "../../../support/pages/payloads";

describe("JSONPlaceholder - Comments", () => {
  it("GET - List all comments", () => {
    cy.apiFetch({
      url: urls.comments,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });

  it("GET - List comments for post 1", () => {
    cy.apiFetch({
      url: urls.postComments(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
    });
  });

  it("GET - Filter comments by postId via query string", () => {
    cy.apiFetch({
      url: `${urls.comments}?postId=1`,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
    });
  });

  it("POST - Create new comment", () => {
    cy.apiFetch({
      url: urls.comments,
      method: "POST",
      body: payloads.createComment,
    }).then((response) => {
      expect(response.status).to.eq(201);
    });
  });
});
