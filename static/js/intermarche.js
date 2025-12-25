/**
 * PanierFacile - Intermarché Integration JavaScript
 * Handles store selection map and cart redirect countdown
 */

// ========== Store Selection Map (intermarche_select_store.html) ==========

function initStoreSelectionMap(userLat, userLon, stores) {
    // Initialize map centered on user location
    const map = L.map('map').setView([userLat, userLon], 12);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // User location marker (blue)
    const userIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    L.marker([userLat, userLon], {icon: userIcon})
        .addTo(map)
        .bindPopup('<b>Votre position</b>')
        .openPopup();

    // Store markers (green)
    const storeIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    stores.forEach(store => {
        const marker = L.marker([store.latitude, store.longitude], {icon: storeIcon})
            .addTo(map)
            .bindPopup(`
                <b>${store.name}</b><br>
                ${store.distance_km} km<br>
                <button class="btn btn-sm btn-primary mt-2" onclick="selectStore('${store.id}', '${store.name}')">
                    Sélectionner
                </button>
            `);

        marker.on('click', function() {
            this.openPopup();
        });
    });
}

function selectStore(storeId, storeName) {
    if (confirm(`Confirmer la sélection de ${storeName} ?`)) {
        document.getElementById('selectedStoreId').value = storeId;
        document.getElementById('storeSelectionForm').submit();
    }
}

// ========== Cart Redirect Countdown (intermarche_redirect.html) ==========

function initRedirectCountdown(redirectUrl, initialSeconds = 5) {
    let timeLeft = initialSeconds;
    const countdownElement = document.getElementById('countdown');

    if (!countdownElement) {
        console.error('Countdown element not found');
        return;
    }

    const timer = setInterval(function() {
        timeLeft--;
        countdownElement.textContent = timeLeft;

        if (timeLeft <= 0) {
            clearInterval(timer);
            window.location.href = redirectUrl;
        }
    }, 1000);

    // Cancel redirect if user navigates away
    window.addEventListener('beforeunload', function() {
        clearInterval(timer);
    });
}
