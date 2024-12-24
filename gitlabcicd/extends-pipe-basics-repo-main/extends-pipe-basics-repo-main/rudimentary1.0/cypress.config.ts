import { defineConfig } from 'cypress'

export default defineConfig({

  // These settings apply everywhere unless overridden
  defaultCommandTimeout: 5000,
  viewportWidth: 1920,
  viewportHeight: 1080,


  e2e: {

    baseUrl: "https://live.techpanda.org",

    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',

    setupNodeEvents(on, config) {
      // e2e testing node events setup code
    },
  },
})
