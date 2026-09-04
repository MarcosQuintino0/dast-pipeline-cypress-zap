const { defineConfig } = require("cypress");
const {
  install,
  ensureBrowserFlags,
} = require("@neuralegion/cypress-har-generator");

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      install(on, config);

      on("before:browser:launch", (browser = {}, launchOptions) => {
        ensureBrowserFlags(browser, launchOptions);

        if (browser.family === "chromium" && browser.name !== "electron") {
          launchOptions.args.push("--disable-features=BlockThirdPartyCookies");
          launchOptions.args.push("--disable-site-isolation-trials");
          launchOptions.args.push(
            "--js-flags=--max-old-space-size=3500 --max-semi-space-size=1024"
          );
        }
        return launchOptions;
      });

      return config;
    },
    specPattern: "cypress/e2e/tests/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
    defaultCommandTimeout: 50000,
    pageLoadTimeout: 100000,
    video: false,
    screenshotOnRunFailure: true,
    chromeWebSecurity: false,
  },
});
