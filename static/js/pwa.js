/**
 * PanierFacile - PWA Registration
 * Enregistre le Service Worker pour activer les fonctionnalités PWA
 */

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('✅ Service Worker enregistré avec succès');
        console.log('Scope:', registration.scope);

        // Vérifier les mises à jour du Service Worker
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          console.log('🔄 Nouvelle version du Service Worker détectée');

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('✅ Nouvelle version prête. Rechargez pour mettre à jour.');
            }
          });
        });
      })
      .catch(error => {
        console.error('❌ Erreur lors de l\'enregistrement du Service Worker:', error);
      });
  });

  // Gérer les changements de contrôleur (nouvelle version activée)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    console.log('🔄 Service Worker mis à jour, rechargement de la page...');
    window.location.reload();
  });
}
