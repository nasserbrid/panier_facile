/**
 * PanierFacile - Service Worker
 * Gère le cache des ressources et le mode hors-ligne
 */

const CACHE_NAME = 'panierfacile-v1';
const STATIC_CACHE = 'panierfacile-static-v1';
const DYNAMIC_CACHE = 'panierfacile-dynamic-v1';

// Ressources à mettre en cache lors de l'installation
const STATIC_ASSETS = [
  '/',
  '/static/css/styles.css',
  '/static/js/base.js',
  '/static/js/chatbot.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  // Bootstrap & Font Awesome depuis CDN
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css'
];

// Installation du Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installation...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Mise en cache des ressources statiques');
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.error('[SW] Erreur lors de la mise en cache:', err);
      });
    })
  );
  self.skipWaiting(); // Force l'activation immédiate
});

// Activation du Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activation...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Suppression ancien cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim(); // Prend le contrôle immédiatement
});

// Stratégie de cache : Network First avec fallback sur Cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ne pas cacher les requêtes API ou admin
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/admin/') ||
    url.pathname.includes('/webhook')
  ) {
    return; // Laisser passer sans cache
  }

  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        // Cloner la réponse pour la mettre en cache
        const responseClone = networkResponse.clone();

        // Mettre en cache les réponses réussies
        if (networkResponse.status === 200) {
          caches.open(DYNAMIC_CACHE).then((cache) => {
            cache.put(request, responseClone);
          });
        }

        return networkResponse;
      })
      .catch(() => {
        // Si le réseau échoue, chercher dans le cache
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('[SW] Récupération depuis le cache:', request.url);
            return cachedResponse;
          }

          // Si pas dans le cache et page HTML, afficher page offline
          if (request.headers.get('accept').includes('text/html')) {
            return caches.match('/'); // Rediriger vers la home
          }
        });
      })
  );
});

// Gestion des messages du client
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
