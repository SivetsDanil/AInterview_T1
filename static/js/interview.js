const sendBtn = document.querySelector('.send-btn');
const runTestsBtn = document.querySelector('.run-tests-btn');
const messageInput = document.querySelector('.chat-input');

sendBtn.addEventListener('click', sendMessage);
runTestsBtn.addEventListener('click', runTests);
messageInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function sendMessage() {
    const input = document.querySelector('.chat-input');
    const message = input.value.trim();
    if (message) {
        addMessage(message, 'user');
        input.value = '';

        // Заглушка ответа AI
        setTimeout(() => {
            addMessage('Спасибо за ваш ответ! Продолжайте работу над задачей.', 'ai');
        }, 500);
    }
}

function addMessage(text, sender) {
    const messagesContainer = document.querySelector('.chat-messages');
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${sender}`;
    messageElement.textContent = text;
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function runTests() {
    const console = document.querySelector('.console-content');
    console.innerHTML = '> Тесты запущены...\n> ✓ Тест 1 пройден\n> ✓ Тест 2 пройден\n> ✗ Тест 3 не пройден';
}

function endInterview() {
    if (confirm('Завершить собеседование?')) {
        window.location.href = 'results';
    }
}
