const stripeNavbar = Stripe("{{ STRIPE_PUBLISHABLE_KEY }}");
const btnNavbar = document.getElementById("checkout-navbar");

if (btnNavbar) {
  btnNavbar.addEventListener("click", () => {
    fetch("{% url 'create_checkout_session' %}", {
      method: "POST",
      headers: {
        "X-CSRFToken": "{{ csrf_token }}",
        "Content-Type": "application/json",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.id) stripeNavbar.redirectToCheckout({ sessionId: data.id });
        else console.error("Erreur lors de la création de la session:", data.error);
      })
      .catch((err) => console.error(err));
  });
}
