/**
 * E2E tests for the Albums and Photos controller.
 * Generates GET traffic for album/photo endpoints.
 */
import { urls } from "../../../support/pages/urls";

describe("JSONPlaceholder - Albums and Photos", () => {
  it("GET - List all albums", () => {
    cy.apiFetch({
      url: urls.albums,
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });

  it("GET - Get album by ID", () => {
    cy.apiFetch({
      url: urls.albumById(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.property("id", 1);
    });
  });

  it("GET - List photos in album", () => {
    cy.apiFetch({
      url: urls.albumPhotos(1),
      method: "GET",
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.data).to.have.length.greaterThan(0);
    });
  });
});
