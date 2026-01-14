/**
 * Carrefour Drive - Gestion de l'interface utilisateur
 *
 * Fonctionnalités:
 * - Sélection de l'enseigne Carrefour
 * - Navigation vers le matching de produits
 */

document.addEventListener('DOMContentLoaded', function() {
    // Gérer le bouton "Utiliser Carrefour"
    const carrefourBtn = document.querySelector('.btn-choose-carrefour');

    if (carrefourBtn) {
        carrefourBtn.addEventListener('click', function() {
            const panierId = this.dataset.panierId;

            // Afficher un spinner pendant le chargement
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Chargement...';
            this.disabled = true;

            // Rediriger vers le matching Carrefour
            window.location.href = `/panier/${panierId}/carrefour/match/?store_id=scraping`;
        });
    }
});

/**
 * Fonction pour copier la liste de produits dans le presse-papier
 * Utilisée dans carrefour_create_cart.html
 */
function copyProductList() {
    const textarea = document.getElementById('productList');

    if (!textarea) {
        console.error('Element productList non trouvé');
        return;
    }

    // Sélectionner le texte
    textarea.select();
    textarea.setSelectionRange(0, 99999); // Pour mobile

    // Copier dans le presse-papier
    try {
        document.execCommand('copy');

        // Feedback visuel
        const btn = document.querySelector('.btn-copy-list');
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copié !';
            btn.classList.remove('btn-outline-primary');
            btn.classList.add('btn-success');

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-primary');
            }, 2000);
        } else {
            alert('Liste copiée dans le presse-papier !');
        }
    } catch (err) {
        console.error('Erreur lors de la copie:', err);
        alert('Impossible de copier automatiquement. Veuillez sélectionner et copier manuellement.');
    }
}
