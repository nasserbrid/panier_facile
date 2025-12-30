/**
 * Intermarché Matching Progress
 * Auto-refresh de la page pendant que la tâche Celery est en cours
 */

(function() {
    'use strict';

    // Auto-refresh toutes les 3 secondes si la tâche est en cours
    const taskStatus = document.getElementById('task-status');

    if (taskStatus) {
        const status = taskStatus.dataset.status;

        // Si la tâche est en cours (PENDING ou STARTED), rafraîchir la page
        if (status === 'PENDING' || status === 'STARTED') {
            console.log('Tâche en cours, rafraîchissement dans 3 secondes...');

            setTimeout(function() {
                window.location.reload();
            }, 3000);
        }
    }
})();
