/**
 * PanierFacile - Base JavaScript
 * Scripts globaux utilisés dans base.html
 */

// ========== STRIPE CHECKOUT ==========
document.addEventListener("DOMContentLoaded", function() {
  // Récupérer la clé publique Stripe depuis l'attribut data
  const stripeKeyElement = document.getElementById("stripe-key");
  if (!stripeKeyElement) return;

  const stripePublicKey = stripeKeyElement.dataset.key;
  const stripe = Stripe(stripePublicKey);
  const checkoutBtn = document.getElementById("checkout-navbar");

  if (checkoutBtn) {
    checkoutBtn.addEventListener("click", () => {
      // Récupérer le CSRF token
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                        || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;

      // Récupérer l'URL depuis l'attribut data
      const checkoutUrl = checkoutBtn.dataset.checkoutUrl;

      fetch(checkoutUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({})
      })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          alert("Erreur : " + data.error);
        } else {
          stripe.redirectToCheckout({ sessionId: data.id });
        }
      })
      .catch((err) => console.error("Erreur Stripe :", err));
    });
  }
});

// ========== CHATBOT URL ==========
// Note: L'URL du chatbot doit être définie via un attribut data sur un élément
// Exemple: <div id="chatbot-config" data-url="/chatbot/"></div>
// Le fichier chatbot.js utilisera cette URL
