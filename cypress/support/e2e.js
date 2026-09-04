/**
 * Global E2E test setup file.
 *
 * IMPORTANT FLOW:
 * 1. before() runs BEFORE all tests in the spec
 * 2. Loads a page in the browser (required for the HAR generator)
 * 3. Starts HAR recording
 * 4. after() runs AFTER all tests
 * 5. Saves the HAR file named after the spec
 *
 * JSONPlaceholder doesn't require authentication, so there's
 * no need to obtain a token. This simplifies the setup.
 */
import "./commands";
import "@neuralegion/cypress-har-generator/commands";

before(() => {
  cy.isHarActive().then((harActive) => {
    if (harActive) {
      // Load a page to have an active browser context
      cy.ensureBrowserContext();

      // Start HAR recording
      // cy.recordHar() is registered by install() in cypress.config.js
      cy.recordHar({
        content: Cypress.spec.name.replace(".cy.js", ""),
      });
    }
  });
});

after(() => {
  cy.isHarActive().then((harActive) => {
    if (harActive) {
      // Save the HAR to the configured folder
      // cy.saveHar() is registered by install() in cypress.config.js
      cy.saveHar({
        fileName: `raw_traffic_${Cypress.spec.name.replace(".cy.js", "")}`,
        outDir: "security_tests/traffic",
      });
    }
  });
});
