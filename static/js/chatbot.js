document.addEventListener("DOMContentLoaded", function () {
    const chatBox = document.getElementById('chatBox');
    const questionInput = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    const loading = document.getElementById('loading');
    const chatbot = document.getElementById('chatbot');
    const openBtn = document.getElementById('openChatBtn');
    const closeBtn = document.getElementById('closeChatBtn');

    // ---------- Gestion de l'ouverture et de la fermeture ----------
    // Je fais apparaître le chat quand je clique sur le bouton
    openBtn.addEventListener('click', () => {
        chatbot.style.display = 'flex';
    });

    // Je cache le chat quand je clique sur la croix
    closeBtn.addEventListener('click', () => {
        chatbot.style.display = 'none';
    });

    // ---------- Gestion des messages ----------
    // Je crée un message et je l'ajoute à la chatBox
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;

        // Je mets le message avant le loader
        chatBox.insertBefore(messageDiv, loading);

        // Je scroll vers le bas automatiquement
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Je gère l'affichage du loader et le désactive des inputs
    function showLoading(show) {
        loading.classList.toggle('active', show);
        sendBtn.disabled = show;
        questionInput.disabled = show;
    }

    // Je montre un message d'erreur dans le chat
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `⚠️ ${message}`;
        chatBox.insertBefore(errorDiv, loading);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Je récupère la question et j'envoie la requête au serveur
    async function sendQuestion() {
        const question = questionInput.value.trim();
        if (!question) return;

        // Je montre la question de l'utilisateur dans le chat
        addMessage(question, 'user');
        questionInput.value = '';

        showLoading(true);

        try {
            const response = await fetch(chatbotUrl + "?question=" + encodeURIComponent(question));

            const data = await response.json();

            if (response.ok) {
                // Je montre la réponse du bot
                addMessage(data.answer, 'bot');
            } else {
                showError(data.error || 'Une erreur est survenue');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showError('Impossible de contacter le serveur. Veuillez réessayer.');
        } finally {
            showLoading(false);
        }
    }

    // Je remplis l'input avec une suggestion et je l'envoie
    window.askQuestion = function(question) {
        questionInput.value = question;
        sendQuestion();
    };

    // Je gère l'envoi via la touche Enter
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendQuestion();
        }
    }

    questionInput.addEventListener('keypress', handleKeyPress);

    // Je mets le focus sur l'input au chargement
    questionInput.focus();

    // Je gère le clic sur le bouton envoyer
    sendBtn.addEventListener('click', sendQuestion);
});
