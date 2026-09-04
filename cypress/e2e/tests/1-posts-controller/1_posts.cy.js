/**
 * E2E tests for the JSONPlaceholder Posts controller.
 *
 * These are NOT traditional functional tests.
 * The main goal is to GENERATE HTTP TRAFFIC that will be captured
 * in the HAR file for later security analysis by OWASP ZAP.
 *
 * Every request made here will appear in the HAR and be scanned.
 */
import { urls } from "../../../support/pages/urls";
import { payloads } from "../../../support/pages/payloads";

describe("JSONPlaceholder - Posts", () => {
  it("GET - List all posts", () => {
    cy.apiFetch({
      url: urls.posts,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });

  it("GET - Get post by ID", () => {
    cy.apiFetch({
      url: urls.postById(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.property("id", 1);
    });
  });

  it("GET - List comments for post 1", () => {
    cy.apiFetch({
      url: urls.postComments(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });

  it("POST - Create new post", () => {
    cy.apiFetch({
      url: urls.posts,
      method: "POST",
      body: payloads.createPost,
    }).then((response) => {
      expect(response.status).to.eq(201);
      expect(response.data).to.have.property("id");
    });
  });

  it("PUT - Update existing post", () => {
    cy.apiFetch({
      url: urls.postById(1),
      method: "PUT",
      body: payloads.updatePost,
    }).then((response) => {
      expect(response.status).to.eq(200);
    });
  });

  it("DELETE - Delete post", () => {
    cy.apiFetch({
      url: urls.postById(1),
      method: "DELETE",
    }).then((response) => {
      expect(response.status).to.eq(200);
    });
  });
});
