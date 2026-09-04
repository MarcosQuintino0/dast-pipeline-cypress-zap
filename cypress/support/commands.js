/**
 * Custom command: checks if HAR recording is active.
 * Defaults to TRUE - only deactivates if explicitly set to false.
 */
Cypress.Commands.add("isHarActive", () => {
  const value = Cypress.env("harActive");
  return value === undefined ? true : value === true;
});

/**
 * Custom command: prepares options for fetch calls.
 * Uses the browser's native fetch() instead of cy.request() because
 * ONLY requests made through the browser are captured by the HAR generator.
 * cy.request() from Cypress bypasses the browser and does NOT appear in the HAR.
 */
Cypress.Commands.add("prepareFetchOptions", (method, body = null) => {
  const options = {
    method: method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
    options.body = JSON.stringify(body);
  }

  return cy.wrap(options);
});

/**
 * Custom command: safely parses a fetch response.
 * fetch() returns a Response object, not direct JSON.
 * We need to call .json() or .text() to extract the body.
 */
Cypress.Commands.add("parseResponse", (response) => {
  return cy.wrap(
    response
      .clone()
      .json()
      .catch(() => response.text())
  );
});

/**
 * Custom command: ensures the browser has an active context.
 * The HAR generator needs a loaded page to intercept requests.
 * Without this, fetch requests may fail or not be captured.
 */
Cypress.Commands.add("ensureBrowserContext", () => {
  const appUrl = Cypress.env("appUrl");
  if (appUrl) {
    cy.visit(appUrl, { failOnStatusCode: false });
  }
});

/**
 * Main command: makes HTTP requests using the browser's fetch API.
 *
 * WHY FETCH AND NOT CY.REQUEST?
 * - cy.request() makes the request directly from Cypress's Node.js process
 * - This means the request does NOT go through the browser
 * - The HAR generator ONLY captures requests that go through the browser
 * - Using fetch() ensures the request is made by the browser and captured in the HAR
 *
 * @param {Object} options - { url, method, body }
 */
Cypress.Commands.add("apiFetch", (options) => {
  const { url, method = "GET", body = null } = options;

  return cy.prepareFetchOptions(method, body).then((fetchOptions) => {
    return cy.window().then((win) => {
      return win.fetch(url, fetchOptions).then((response) => {
        return cy.parseResponse(response).then((data) => {
          return {
            status: response.status,
            ok: response.ok,
            data: data,
          };
        });
      });
    });
  });
});
