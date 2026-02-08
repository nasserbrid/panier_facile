/**
 * PanierFacile - Comparaison de prix
 *
 * Gestion du polling pour suivre la progression de la comparaison
 * et de la geolocalisation pour detecter la position de l'utilisateur.
 */

/**
 * Classe pour gerer la progression de la comparaison
 */
class ComparisonProgress {
    constructor(taskId, panierId, options = {}) {
        this.taskId = taskId;
        this.panierId = panierId;
        this.pollInterval = options.pollInterval || 2000;
        this.statusApiUrl = options.statusApiUrl || `/panier/api/comparison-status/${taskId}/`;
        this.resultsUrlBase = options.resultsUrlBase || `/panier/${panierId}/comparer/resultats/`;

        this.pollTimer = null;
        this.elements = {
            progressBar: document.getElementById('progressBar'),
            statusMessage: document.getElementById('statusMessage'),
            carrefourStatus: document.getElementById('carrefourStatus'),
            carrefourSpinner: document.getElementById('carrefourSpinner'),
            aldiStatus: document.getElementById('aldiStatus'),
            aldiSpinner: document.getElementById('aldiSpinner'),
            spinner: document.querySelector('.spinner-border')
        };
    }

    /**
     * Demarre le polling de status
     */
    start() {
        this.pollStatus();
        this.pollTimer = setInterval(() => this.pollStatus(), this.pollInterval);
    }

    /**
     * Arrete le polling
     */
    stop() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    /**
     * Fait une requete pour obtenir le status de la tache
     */
    async pollStatus() {
        try {
            const response = await fetch(this.statusApiUrl);
            const data = await response.json();

            console.log('Status:', data);

            switch (data.state) {
                case 'PROGRESS':
                    this.updateProgress(data);
                    break;
                case 'SUCCESS':
                    this.handleSuccess(data);
                    break;
                case 'FAILURE':
                    this.handleFailure(data);
                    break;
            }
        } catch (error) {
            console.error('Erreur polling:', error);
        }
    }

    /**
     * Met a jour l'affichage de la progression
     */
    updateProgress(data) {
        if (!data.progress) return;

        const { current, total, message, supermarket } = data.progress;
        const percent = Math.round((current / total) * 100);

        // Mise a jour de la barre de progression
        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = `${percent}%`;
            this.elements.progressBar.textContent = `${percent}%`;
            this.elements.progressBar.setAttribute('aria-valuenow', percent);
        }

        // Mise a jour du message
        if (this.elements.statusMessage) {
            this.elements.statusMessage.textContent = message || 'Recherche en cours...';
        }

        // Mise a jour du status par supermarche
        this.updateSupermarketStatus(supermarket);
    }

    /**
     * Met a jour les indicateurs par supermarche
     */
    updateSupermarketStatus(supermarket) {
        if (supermarket === 'carrefour') {
            if (this.elements.carrefourStatus) {
                this.elements.carrefourStatus.textContent = 'Carrefour: recherche...';
            }
            if (this.elements.carrefourSpinner) {
                this.elements.carrefourSpinner.classList.remove('text-secondary');
                this.elements.carrefourSpinner.classList.add('text-primary');
            }
        } else if (supermarket === 'aldi') {
            // Carrefour termine
            if (this.elements.carrefourStatus) {
                this.elements.carrefourStatus.innerHTML = '<i class="fas fa-check text-success me-1"></i>Carrefour termine';
            }
            if (this.elements.carrefourSpinner) {
                this.elements.carrefourSpinner.style.display = 'none';
            }
            // Aldi en cours
            if (this.elements.aldiStatus) {
                this.elements.aldiStatus.textContent = 'Aldi: recherche...';
            }
            if (this.elements.aldiSpinner) {
                this.elements.aldiSpinner.classList.remove('text-secondary');
                this.elements.aldiSpinner.classList.add('text-primary');
            }
        }
    }

    /**
     * Gere le succes de la tache
     */
    handleSuccess(data) {
        this.stop();

        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = '100%';
            this.elements.progressBar.textContent = '100%';
        }

        if (this.elements.statusMessage) {
            this.elements.statusMessage.textContent = 'Comparaison terminee! Redirection...';
        }

        // Redirection vers les resultats
        if (data.result && data.result.comparison_id) {
            window.location.href = `${this.resultsUrlBase}${data.result.comparison_id}/`;
        }
    }

    /**
     * Gere l'echec de la tache
     */
    handleFailure(data) {
        this.stop();

        if (this.elements.statusMessage) {
            this.elements.statusMessage.innerHTML =
                '<span class="text-danger">Erreur lors de la comparaison. Veuillez reessayer.</span>';
        }

        if (this.elements.spinner) {
            this.elements.spinner.style.display = 'none';
        }
    }
}

/**
 * Classe pour gerer la geolocalisation
 */
class GeolocationHelper {
    constructor(options = {}) {
        this.saveLocationUrl = options.saveLocationUrl || '/panier/save-location/';
        this.csrfToken = options.csrfToken || '';
    }

    /**
     * Detecte la position GPS de l'utilisateur
     */
    detectPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('La geolocalisation n\'est pas supportee par votre navigateur.'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                }),
                error => {
                    let message = 'Impossible de detecter votre position';
                    if (error.code === error.PERMISSION_DENIED) {
                        message = 'Vous avez refuse l\'acces a votre position';
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        message = 'Position indisponible';
                    } else if (error.code === error.TIMEOUT) {
                        message = 'Delai d\'attente depasse';
                    }
                    reject(new Error(message));
                }
            );
        });
    }

    /**
     * Sauvegarde la position sur le serveur
     */
    async savePosition(latitude, longitude, saveToProfile = false) {
        const response = await fetch(this.saveLocationUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                latitude,
                longitude,
                save_to_profile: saveToProfile
            })
        });

        if (!response.ok) {
            throw new Error('Erreur lors de la sauvegarde de la position');
        }

        return response.json();
    }

    /**
     * Detecte et sauvegarde la position
     */
    async detectAndSave(saveToProfile = false) {
        const position = await this.detectPosition();
        await this.savePosition(position.latitude, position.longitude, saveToProfile);
        return position;
    }
}

// Export pour utilisation dans les templates
window.ComparisonProgress = ComparisonProgress;
window.GeolocationHelper = GeolocationHelper;
