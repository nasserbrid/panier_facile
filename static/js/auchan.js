/**
 * Auchan Drive - Gestion de l'interface utilisateur
 *
 * Fonctionnalités:
 * - Sélection de l'enseigne Auchan
 * - Navigation vers le matching de produits
 */

document.addEventListener('DOMContentLoaded', function() {
    // Gérer le bouton "Utiliser Auchan"
    const auchanBtn = document.querySelector('.btn-choose-auchan');

    if (auchanBtn) {
        auchanBtn.addEventListener('click', function() {
            const panierId = this.dataset.panierId;

            // Afficher un spinner pendant le chargement
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Chargement...';
            this.disabled = true;

            // Rediriger vers le matching Auchan
            window.location.href = `/panier/${panierId}/auchan/match/?store_id=scraping`;
        });
    }
});

/**
 * Fonction pour copier la liste de produits dans le presse-papier
 * Utilisée dans auchan_create_cart.html
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
            btn.classList.remove('btn-outline-info');
            btn.classList.add('btn-success');

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-info');
            }, 2000);
        } else {
            alert('Liste copiée dans le presse-papier !');
        }
    } catch (err) {
        console.error('Erreur lors de la copie:', err);
        alert('Impossible de copier automatiquement. Veuillez sélectionner et copier manuellement.');
    }
}
