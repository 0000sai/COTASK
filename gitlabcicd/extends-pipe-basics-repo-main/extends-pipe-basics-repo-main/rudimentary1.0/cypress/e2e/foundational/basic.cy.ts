it('Rudimentary test', () => {
    cy.visit('/');

    cy.get("h2").should("contain.text", "This is demo site");

})
