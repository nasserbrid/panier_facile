document.addEventListener("DOMContentLoaded", function () {
  let popup = document.getElementById("popup-message");
  if (popup) {
    popup.style.display = "block";
    setTimeout(function () {
      popup.style.animation = "fadeOut 1s ease-in-out";
      setTimeout(() => (popup.style.display = "none"), 1000);
    }, 3000);
  }
});
