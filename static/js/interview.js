// Элементы будут получены после загрузки DOM
let sendBtn, runTestsBtn, messageInput, languageSelect, codeEditor, timerDisplay;

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
    // Получаем элементы после загрузки DOM
    sendBtn = document.querySelector('.send-btn');
    runTestsBtn = document.querySelector('.run-tests-btn');
    messageInput = document.querySelector('.chat-input');
    languageSelect = document.querySelector('.language-select');
    codeEditor = document.querySelector('.code-editor');
    timerDisplay = document.querySelector('.timer');
    
    // Инициализируем редактор
    if (codeEditor && languageSelect) {
        const selectedLang = languageSelect.value || 'python';
        if (languageTemplates[selectedLang]) {
            codeEditor.value = languageTemplates[selectedLang];
        }
    }
    
    // Обработчик смены языка
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            const selectedLang = e.target.value;
            if (codeEditor && languageTemplates[selectedLang]) {
                const currentCode = codeEditor.value.trim();
                
                // Проверяем, является ли текущий код шаблоном
                let isTemplate = false;
                for (const [lang, template] of Object.entries(languageTemplates)) {
                    const templateTrimmed = template.trim();
                    if (currentCode === templateTrimmed) {
                        isTemplate = true;
                        break;
                    }
                }
                
                // Если код пустой или это шаблон, заменяем на новый шаблон
                if (currentCode === '' || isTemplate) {
                    codeEditor.value = languageTemplates[selectedLang];
                }
                // Иначе оставляем код пользователя
            }
        });
    }
    
    // Обработчик кнопки отправки сообщения
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // Обработчик кнопки запуска тестов
    if (runTestsBtn) {
        runTestsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (window.runTests) {
                window.runTests();
            }
        });
    }
    
    // Обработчик Enter в поле сообщения
    if (messageInput) {
        messageInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    // Запускаем таймер
    if (timerDisplay) {
        startTimer(45 * 60);
    }
});


/**
 * Запускает обратный отсчет таймера
 * @param {number} durationInSeconds - Продолжительность в секундах
 */


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

// Делаем функцию глобальной для доступа из onclick
window.runTests = async function runTests() {
    console.log('runTests вызвана');
    const consoleContent = document.querySelector('.console-content') || document.getElementById('consoleOutput');
    const codeEditor = document.querySelector('.code-editor');
    const languageSelect = document.querySelector('.language-select');
    
    if (!consoleContent) {
        console.error('Не найден элемент .console-content или #consoleOutput');
        return;
    }
    
    // Получаем код из редактора
    const userCode = codeEditor ? codeEditor.value.trim() : '';
    const language = languageSelect ? languageSelect.value : 'python';
    
    // Получаем task_id (можно из data-атрибута кнопки или из глобальной переменной)
    const taskId = document.querySelector('.run-tests-btn')?.dataset.taskId || 
                   window.currentTaskId || 
                   'default_task_id';
    
    console.log('Task ID:', taskId, 'Language:', language, 'Code length:', userCode.length);
    
    if (!userCode) {
        consoleContent.innerHTML = '> ❌ Ошибка: Код не может быть пустым';
        return;
    }
    
    // Показываем, что запрос отправляется
    consoleContent.innerHTML = '> Тесты запущены...\n> Выполнение кода...';
    
    try {
        console.log('Отправка запроса на /api/run-tests');
        // Сначала выполняем реальные тесты
        const testResponse = await fetch('/api/run-tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_id: taskId,
                user_code: userCode,
                language: language
            })
        });
        
        console.log('Ответ получен, статус:', testResponse.status);
        const testData = await testResponse.json();
        console.log('Данные ответа:', testData);
        
        if (testResponse.ok && testData.status === 'success') {
            const passed = testData.passed;
            const total = testData.total;
            const allPassed = testData.all_passed;
            const testResults = testData.test_results || [];
            
            let output = `> Результаты тестов: ${passed}/${total} пройдено\n\n`;
            
            // Показываем результаты каждого теста
            testResults.forEach(test => {
                if (test.status === 'passed') {
                    output += `> ✓ Тест ${test.test}: ПРОЙДЕН\n`;
                } else if (test.status === 'failed') {
                    output += `> ✗ Тест ${test.test}: НЕ ПРОЙДЕН\n`;
                    output += `>   Ввод: ${test.input}\n`;
                    output += `>   Ожидалось: ${test.expected}\n`;
                    output += `>   Получено: ${test.actual}\n\n`;
                } else if (test.status === 'error') {
                    output += `> ✗ Тест ${test.test}: ОШИБКА\n`;
                    output += `>   ${test.error}\n\n`;
                } else if (test.status === 'timeout') {
                    output += `> ✗ Тест ${test.test}: ТАЙМАУТ\n\n`;
                }
            });
            
            if (allPassed) {
                output += '\n> 🎉 Все тесты пройдены! Задача решена.\n';
                consoleContent.innerHTML = output;
                
                // Генерируем новую задачу и очищаем редактор
                await loadNewTask();
            } else {
                output += `\n> ❌ Не все тесты пройдены. Продолжайте работу.\n`;
                consoleContent.innerHTML = output;
            }
        } else {
            let errorMsg = testData.message || testData.error || 'Ошибка выполнения тестов';
            consoleContent.innerHTML = `> ❌ Ошибка: ${errorMsg}`;
        }
    } catch (error) {
        consoleContent.innerHTML = `> ❌ Ошибка сети: ${error.message}`;
        console.error('Ошибка при отправке запроса:', error);
    }
};

async function loadNewTask() {
    const codeEditor = document.querySelector('.code-editor');
    const languageSelect = document.querySelector('.language-select');
    const consoleContent = document.querySelector('.console-content');
    
    try {
        // Очищаем редактор и устанавливаем шаблон для текущего языка
        if (codeEditor && languageSelect) {
            const selectedLang = languageSelect.value;
            codeEditor.value = languageTemplates[selectedLang] || '';
        }
        
        // Генерируем новую задачу
        const response = await fetch('/api/generate-task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                position: 'Python Developer',
                difficulty: 'middle'
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            const newTask = data.task;
            
            // Обновляем task_id
            window.currentTaskId = newTask.id;
            const runTestsBtn = document.querySelector('.run-tests-btn');
            if (runTestsBtn) {
                runTestsBtn.dataset.taskId = newTask.id;
            }
            
            // Обновляем содержимое задачи на странице
            updateTaskDisplay(newTask);
            
            consoleContent.innerHTML += '\n> Новая задача загружена!';
        } else {
            consoleContent.innerHTML += `\n> ⚠️ Не удалось загрузить новую задачу: ${data.error || 'Неизвестная ошибка'}`;
        }
    } catch (error) {
        console.error('Ошибка при загрузке новой задачи:', error);
        consoleContent.innerHTML += `\n> ⚠️ Ошибка при загрузке новой задачи: ${error.message}`;
    }
}

function updateTaskDisplay(task) {
    // Обновляем вкладку "Задача"
    const taskTab = document.getElementById('task-tab');
    if (taskTab) {
        const problemContent = taskTab.querySelector('.problem-content');
        if (problemContent) {
            let html = `<h3>${task.title || task.id || 'Задача'}</h3>`;
            html += `<div class="task-description"><p style="white-space: pre-wrap;">${task.description || 'Описание задачи отсутствует'}</p></div>`;
            
            if (task.constraints) {
                html += `<div class="task-constraints" style="margin-top: 15px; padding: 10px; background: #F3F4F6; border-radius: 6px;">
                    <strong>Ограничения:</strong>
                    <p style="white-space: pre-wrap;">${task.constraints}</p>
                </div>`;
            }
            
            problemContent.innerHTML = html;
        }
    }
    
    // Обновляем примеры во вкладке "Примеры"
    const examplesTab = document.getElementById('examples-tab');
    if (examplesTab && task.test_cases && Array.isArray(task.test_cases)) {
        let examplesHTML = '<h4>Все примеры ввода/вывода:</h4>';
        task.test_cases.forEach((testCase, index) => {
            const input = testCase.input || '';
            const output = testCase.output || '';
            examplesHTML += `
                <div style="margin-bottom: 20px; padding: 15px; background: #1F2937; color: #F9FAFB; border-radius: 6px; font-family: monospace;">
                    <div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #374151;">
                        <strong style="color: #9CA3AF;">Пример ${index + 1}:</strong>
                    </div>
                    <div style="margin-bottom: 8px;">
                        <strong style="color: #60A5FA;">Ввод:</strong>
                        <pre style="margin: 5px 0; white-space: pre-wrap; background: #111827; padding: 8px; border-radius: 4px;">${escapeHtml(input)}</pre>
                    </div>
                    <div>
                        <strong style="color: #34D399;">Вывод:</strong>
                        <pre style="margin: 5px 0; white-space: pre-wrap; background: #111827; padding: 8px; border-radius: 4px;">${escapeHtml(output)}</pre>
                    </div>
                </div>
            `;
        });
        examplesTab.innerHTML = `<div class="problem-content">${examplesHTML}</div>`;
    }
    
    // Обновляем task_id в кнопке
    const runTestsBtn = document.querySelector('.run-tests-btn');
    if (runTestsBtn && task.id) {
        runTestsBtn.dataset.taskId = task.id;
        runTestsBtn.disabled = false;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function endInterview() {

    if (confirm('Завершить собеседование?')) {
        // Замените на реальный URL
        window.location.href = 'results'; 
    }
}

document.addEventListener('DOMContentLoaded', () => {

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




