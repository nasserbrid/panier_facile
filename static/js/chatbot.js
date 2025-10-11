

document.addEventListener("DOMContentLoaded", function () {
    const chatBox = document.getElementById('chatBox');
    const questionInput = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    const loading = document.getElementById('loading');

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;

        // Insérer avant le loading
        chatBox.insertBefore(messageDiv, loading);

        // Scroll vers le bas
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showLoading(show) {
        loading.classList.toggle('active', show);
        sendBtn.disabled = show;
        questionInput.disabled = show;
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `⚠️ ${message}`;
        chatBox.insertBefore(errorDiv, loading);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendQuestion() {
        const question = questionInput.value.trim();
        if (!question) return;

        // Ajouter le message de l'utilisateur
        addMessage(question, 'user');
        questionInput.value = '';

        showLoading(true);

        try {
            const response = await fetch(`/chatbot/?question=${encodeURIComponent(question)}`);
            const data = await response.json();

            if (response.ok) {
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

    window.askQuestion = function(question) {
        questionInput.value = question;
        sendQuestion();
    };

    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            sendQuestion();
        }
    }

    questionInput.addEventListener('keypress', handleKeyPress);

    // Focus automatique sur l'input
    questionInput.focus();

    // Bouton envoyer
    sendBtn.addEventListener('click', sendQuestion);
});
