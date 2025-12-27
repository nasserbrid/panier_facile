/**
 * Script pour la sélection de magasin et la géolocalisation
 * Page: select_store_for_drive.html
 */

document.addEventListener('DOMContentLoaded', function() {
    const getLocationBtn = document.getElementById('getLocationBtn');
    const geocodeBtn = document.getElementById('geocodeBtn');
    const addressInput = document.getElementById('addressInput');
    const locationMessage = document.getElementById('locationMessage');
    const saveToProfile = document.getElementById('saveToProfile');

    // Fonction pour afficher un message
    function showMessage(message, type = 'info') {
        locationMessage.className = `alert alert-${type}`;
        locationMessage.textContent = message;
        locationMessage.style.display = 'block';
        setTimeout(() => {
            locationMessage.style.display = 'none';
        }, 5000);
    }

    // Fonction pour sauvegarder la localisation
    function saveLocation(latitude, longitude, address) {
        // Récupérer le CSRF token depuis le template
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch(saveLocationUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                latitude: latitude,
                longitude: longitude,
                address: address,
                save_to_profile: saveToProfile.checked
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                // Recharger la page pour afficher les magasins
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showMessage('Erreur: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            showMessage('Erreur de connexion', 'danger');
            console.error('Error:', error);
        });
    }

    // Géolocalisation GPS
    getLocationBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            showMessage('La géolocalisation n\'est pas supportée par votre navigateur', 'danger');
            return;
        }

        showMessage('Détection de votre position en cours...', 'info');
        getLocationBtn.disabled = true;

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                // Reverse geocoding pour obtenir l'adresse
                fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
                    .then(response => response.json())
                    .then(data => {
                        const address = data.display_name || '';
                        addressInput.value = address;
                        saveLocation(lat, lon, address);
                    })
                    .catch(() => {
                        saveLocation(lat, lon, '');
                    })
                    .finally(() => {
                        getLocationBtn.disabled = false;
                    });
            },
            function(error) {
                let errorMsg = 'Impossible de récupérer votre position';
                if (error.code === error.PERMISSION_DENIED) {
                    errorMsg = 'Vous avez refusé l\'accès à votre position';
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    errorMsg = 'Position indisponible';
                } else if (error.code === error.TIMEOUT) {
                    errorMsg = 'Délai d\'attente dépassé';
                }
                showMessage(errorMsg, 'danger');
                getLocationBtn.disabled = false;
            }
        );
    });

    // Géocodage d'adresse
    geocodeBtn.addEventListener('click', function() {
        const address = addressInput.value.trim();
        if (!address) {
            showMessage('Veuillez entrer une adresse', 'warning');
            return;
        }

        showMessage('Recherche de l\'adresse en cours...', 'info');
        geocodeBtn.disabled = true;

        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    const lat = parseFloat(data[0].lat);
                    const lon = parseFloat(data[0].lon);
                    saveLocation(lat, lon, data[0].display_name);
                } else {
                    showMessage('Adresse introuvable', 'warning');
                }
            })
            .catch(error => {
                showMessage('Erreur lors de la recherche', 'danger');
                console.error('Error:', error);
            })
            .finally(() => {
                geocodeBtn.disabled = false;
            });
    });

    // Gestion du clic sur "Choisir" un magasin
    const chooseStoreBtns = document.querySelectorAll('.btn-choose-store');
    const driveModal = new bootstrap.Modal(document.getElementById('driveModal'));

    chooseStoreBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const storeName = this.getAttribute('data-store-name');
            const panierId = this.getAttribute('data-panier-id');

            // Afficher le nom du magasin dans la modal
            document.getElementById('driveStoreName').textContent = storeName;

            // Réinitialiser les états
            document.getElementById('driveLoading').style.display = 'block';
            document.getElementById('driveSuccess').style.display = 'none';
            document.getElementById('driveError').style.display = 'none';
            document.getElementById('driveModalFooter').style.display = 'none';

            // Afficher la modal
            driveModal.show();

            // Rediriger vers la page de matching
            // On utilise un iframe caché pour vérifier si le panier a des ingrédients
            window.location.href = `/panier/${panierId}/intermarche/match/?store_id=scraping`;
        });
    });
});
