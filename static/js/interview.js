const sendBtn = document.querySelector('.send-btn');
const runTestsBtn = document.querySelector('.run-tests-btn');
const messageInput = document.querySelector('.chat-input');
const languageSelect = document.querySelector('.language-select');
const codeEditor = document.querySelector('.code-editor');
const timerDisplay = document.querySelector('.timer');

const languageTemplates = {
    'python': `def solve():
    # Ваше решение здесь
    pass

# Пример вызова:
# print(solve())
`,
    'cpp': `class Solution {
public:
    // Ваше решение здесь
    void solve() {
        
    }
};
// int main() {
//     Solution s;
//     s.solve();
//     return 0;
// }
`,
    'java': `class Solution {
    // Ваше решение здесь
    public void solve() {
        
    }
}
// public class Main {
//     public static void main(String[] args) {
//         Solution s = new Solution();
//         s.solve();
//     }
// }
`,
    'go': `package main

import "fmt"

func solve() {
    // Ваше решение здесь
}
`,
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    codeEditor.value = languageTemplates[languageSelect.value];
    startTimer(45 * 60);
});


languageSelect.addEventListener('change', (e) => {
    const selectedLang = e.target.value;
    codeEditor.value = languageTemplates[selectedLang] || '// Выберите язык...';
});


sendBtn.addEventListener('click', sendMessage);
runTestsBtn.addEventListener('click', runTests);
messageInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});


/**
 * Запускает обратный отсчет таймера
 * @param {number} durationInSeconds - Продолжительность в секундах
 */
function startTimer(durationInSeconds) {
    let timer = durationInSeconds;
    let minutes, seconds;

    const interval = setInterval(() => {
        minutes = parseInt(timer / 60, 10);
        seconds = parseInt(timer % 60, 10);

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        timerDisplay.textContent = minutes + ":" + seconds;

        if (--timer < 0) {
            clearInterval(interval);
            timerDisplay.textContent = "00:00";
            alert("Время собеседования вышло!");
            // Вы можете добавить здесь вызов endInterview() или другой логики
        }
    }, 1000);
}


async function sendMessage() {
    const input = document.querySelector('.chat-input');
    const message = input.value.trim();

    if (!message) return;

    // Добавляем сообщение пользователя
    addMessage(message, 'user');
    input.value = '';

    // Показываем "печатает..." или заглушку, пока ждём ответ
    const loadingId = 'loading-' + Date.now();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        if (response.ok && data.reply) {
            addMessage(data.reply, 'ai');
        } else {
            document.getElementById(loadingId)?.remove();
            addMessage(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, 'ai');
        }
    } catch (error) {
        document.getElementById(loadingId)?.remove();
        addMessage(`Не удалось подключиться к серверу`, 'ai');
        console.error('Ошибка отправки:', error);
    }
}

function addMessage(text, sender) {
    const messagesContainer = document.querySelector('.chat-messages');
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${sender}`;
    messageElement.textContent = text;
    messagesContainer.appendChild(messageElement);
    // Прокрутка вниз
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function runTests() {
    const consoleContent = document.querySelector('.console-content');
    consoleContent.innerHTML = '> Тесты запущены...\n> ✓ Тест 1 пройден\n> ✓ Тест 2 пройден\n> ✗ Тест 3 не пройден';
}

function endInterview() {
    if (confirm('Завершить собеседование?')) {
        // Замените на реальный URL
        window.location.href = 'results'; 
    }
}