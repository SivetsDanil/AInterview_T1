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
            // ИЗМЕНЕНИЕ: Замена alert() на безопасный console.warn()
            console.warn("Время собеседования вышло!"); 
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
    
    // 1. Сначала вызываем reCAPTCHA API, чтобы получить токен
    grecaptcha.ready(function() {
        // !!! ВАШ ПУБЛИЧНЫЙ КЛЮЧ RECAPTCHA ДОЛЖЕН БЫТЬ ЗДЕСЬ !!!
        // Убедитесь, что это "Ключ сайта" (Site Key), зарегистрированный для localhost.
        const SITE_KEY_JS ="6LeNDRksAAAAAFpfLym3unGOmDpGMqTZybb_6QA1"; 

        grecaptcha.execute(SITE_KEY_JS, {action: 'submit'}).then(function(token) {
            // 2. Получив токен, отправляем его вместе с сообщением на наш сервер
            sendVerificationRequest(message, token);
        }).catch(error => {
            // ДОБАВЛЕНО: Обработка ошибки, если grecaptcha.execute не сработала
            console.error("Ошибка при выполнении grecaptcha.execute:", error);
            addMessage('Ошибка: не удалось получить токен reCAPTCHA. Проверьте Консоль (F12).', 'ai');
        });
    });
}

/**
 * Отправляет токен и сообщение на бэкенд для верификации и получения ответа AI.
 * @param {string} message - Сообщение пользователя.
 * @param {string} token - Токен reCAPTCHA.
 */
function sendVerificationRequest(message, token) {
    const FORM_URL = '/verify'; // Маршрут в app.py
    const messageInput = document.querySelector('.chat-input');

    // Показываем сообщение пользователя сразу, пока ждем ответа
    addMessage(message, 'user');
    messageInput.value = ''; 
    
    const formData = new FormData();
    formData.append('message', message);
    formData.append('g-recaptcha-response', token); // Главное: токен reCAPTCHA

    fetch(FORM_URL, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        // УЛУЧШЕНИЕ: Обработка HTTP-статуса для лучшей отладки
        if (!response.ok) {
            // Если статус 4xx или 5xx, пытаемся получить JSON с ошибкой от Flask
            return response.json().then(errorData => {
                // Если Flask отправил JSON с сообщением об ошибке
                throw new Error(errorData.message || `HTTP Error! Status: ${response.status}.`);
            }).catch(() => {
                // Если Flask не отправил JSON (например, при серьезной 500 ошибке)
                throw new Error(`HTTP Error! Status: ${response.status}. Проверьте логи сервера.`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Верификация успешна, добавляем ответ AI
            const aiResponse = data.ai_response || 'Получен ответ от AI.';
            setTimeout(() => {
                addMessage(aiResponse, 'ai');
            }, 500);
            
        } else {
            // Верификация не пройдена
            setTimeout(() => {
                addMessage(`❌ Ошибка верификации reCAPTCHA: ${data.message}`, 'ai');
            }, 500);
            console.error('Ошибка верификации reCAPTCHA:', data);
        }
    })
    .catch(error => {
        // Ошибка сети или ошибка, вызванная throw new Error в предыдущем блоке
        setTimeout(() => {
            addMessage(`Произошла ошибка сети/сервера: ${error.message}`, 'ai');
        }, 500);
        console.error('Ошибка Fetch:', error);
    });
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
    const consoleContent = document.querySelector('.console-content');
    consoleContent.innerHTML = '> Тесты запущены...\n> ✓ Тест 1 пройден\n> ✓ Тест 2 пройден\n> ✗ Тест 3 не пройден';
}

function endInterview() {

    if (confirm('Завершить собеседование?')) {
        // Замените на реальный URL
        window.location.href = 'results'; 
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const editor = document.querySelector('.code-editor');
    if (!editor) return;

    editor.addEventListener('paste', async function (e) {
        e.preventDefault(); // ← блокируем вставку

        const pastedText = (e.clipboardData || window.clipboardData).getData('text');

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4d4d;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            font-family: sans-serif;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: fadeInOut 3s ease forwards;
        `;
        toast.innerHTML = 'Вставка кода запрещена.<br>Пишите самостоятельно.';
        document.body.appendChild(toast);

        // Добавляем CSS-анимацию (если её ещё нет)
        if (!document.querySelector('#toast-style')) {
            const style = document.createElement('style');
            style.id = 'toast-style';
            style.textContent = `
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translateY(-20px); }
                    10% { opacity: 1; transform: translateY(0); }
                    90% { opacity: 1; transform: translateY(0); }
                    100% { opacity: 0; transform: translateY(-20px); }
                }
            `;
            document.head.appendChild(style);
        }

        // Автоудаление тоста через 3 сек
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => toast.remove(), 300);
        }, 2700);

        try {
            await fetch('/api/code-paste', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: pastedText.trim().substring(0, 1000),
                    timestamp: Date.now(),
                    type: 'blocked_paste'
                })
            });
        } catch (err) {
            console.warn('Не удалось отправить лог вставки:', err);
        }
    });
});

