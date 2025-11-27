from flask import Flask, render_template, redirect, request, jsonify
from flask_login import LoginManager, login_required, logout_user
from flask import request, session, jsonify
from ai_interviewer import setup_scibox, interview_step

import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
import json
from api import IndexAPI, InterviewAPI, ResultsAPI
from task_gen import TaskGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = "key"
load_dotenv()
SITE_KEY = os.environ.get('SITE_KEY')
SECRET_KEY_RECAPTCHA = os.environ.get('SECRET_KEY_RECAPTCHA')


from api.IndexAPI import blueprint as index_bp
from api.InterviewAPI import blueprint as interview_bp
from api.ResultsAPI import blueprint as results_bp

# Регистрация (глобально!)
app.register_blueprint(index_bp)
app.register_blueprint(interview_bp)
app.register_blueprint(results_bp)


login_manager = LoginManager()
login_manager.init_app(app)



import os

# === ИНИЦИАЛИЗАЦИЯ SciBox ПРИ СТАРТЕ ===
SCIBOX_API_KEY = os.getenv("SCIBOX_API_KEY", "sk-gqlpOmmxNrBvLyv766GXYg")  # ← ваш ключ
try:
    setup_scibox(SCIBOX_API_KEY)
    print("✅ SciBox инициализирован")
except Exception as e:
    print(f"❌ ОШИБКА инициализации SciBox: {e}")



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'interviews.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'


db = SQLAlchemy(app)


# Модель записи интервью
class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    direction = db.Column(db.String(100), nullable=False)
    fio = db.Column(db.String(100), nullable=False)
    questionnaire = db.Column(db.Text, nullable=True)  # JSON-строка или NULL
    started_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    session_id = db.Column(db.String(128), nullable=True)  # можно для отладки

    def __repr__(self):
        return f"<Interview {self.id}: {self.fio} — {self.direction}>"

# Создаём таблицы (вызов один раз при первом запуске)
with app.app_context():
    db.create_all()





login_manager.login_view = 'login'
class User:
    def __init__(self, id):
        self.id = id

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    return User(id=1)




# выход с аккаунта
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


# обработка ошибки 404
@app.errorhandler(404)
def not_found_error(_):
    return render_template('404.html')


from flask import request, jsonify

# ... остальной код ...

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        topic = data.get('topic', 'общая разработка').strip()  # ← важно: тема!

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        bot_reply, evaluation = interview_step(topic, user_message)
        bot_reply = bot_reply.replace('<think>\n\n</think>\n\n', '')
        print([bot_reply])
        # Опционально: если пришла оценка — можно её сохранить или выделить
        response_data = {
            'reply': bot_reply,
            'status': 'success'
        }
        if evaluation is not None:
            response_data['evaluation'] = evaluation

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500



from flask import request, jsonify

@app.route('/api/code-paste', methods=['POST'])
def handle_code_paste():
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

        data = request.get_json(silent=True)  # silent=True — не падает, если JSON невалидный
        if data is None:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

        pasted_code = data.get('code', '')
        timestamp = data.get('timestamp', 'unknown')
        print(f"[PASTE DETECTED] Вставлено:\n{pasted_code[:100]}... in {timestamp}")

        return jsonify({
            'status': 'received',
            'message': 'Вставка зафиксирована',
            'length': len(pasted_code)
        }), 200

    except Exception as e:
        error_msg = f"Внутренняя ошибка: {str(e)}"
        print("Ошибка в /api/code-paste:", error_msg)
        return jsonify({
            'status': 'server_error',
            'message': error_msg
        }), 500


def main():
    # Сохраняем TaskGenerator в конфигурации приложения для доступа из blueprint
    app.config['TASK_GENERATOR'] = task_generator


    app.run(port=5000, host='127.0.0.1', debug=True)


@app.route('/verify', methods=['POST'])
def verify_recaptcha():
    """Обрабатывает AJAX-запрос с токеном reCAPTCHA и проверяет его."""
    
    recaptcha_response = request.form.get('g-recaptcha-response')
    user_message = request.form.get('message') 
    
    if not recaptcha_response:
        return jsonify({'success': False, 'message': 'Токен reCAPTCHA отсутствует'}), 400

    payload = {
        'secret': SECRET_KEY_RECAPTCHA,
        'response': recaptcha_response
    }
    
    VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
    try:
        response = requests.post(VERIFY_URL, data=payload)
        result = response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': f'Ошибка при связи с Google: {e}'}), 500

    if result.get('success'):
        score = result.get('score', 1.0) 
        
        # Рекомендованный порог для reCAPTCHA v3
        if score >= 0.5:
            # TODO: Здесь вызывайте ваш LLM API (llm.t1v.scibox.tech)
            # Временно используем заглушку
            LLM_RESPONSE = f"Спасибо за ваш вопрос! reCAPTCHA успешно пройдена. Счет - {score}"
            
            return jsonify({
                'success': True, 
                'score': score,
                'ai_response': LLM_RESPONSE
            }), 200
        else:
            return jsonify({'success': False, 'message': f'Слишком низкий скор ({score})', 'score': score}), 403
    else:
        return jsonify({'success': False, 'message': 'Неудачная верификация', 'errors': result.get('error-codes')}), 403


@app.route('/api/run-tests', methods=['POST'])
def run_tests_endpoint(task_generator=None):
    """Endpoint для реального выполнения тестов"""
    import subprocess
    import tempfile
    import os
    import json

    def normalize_snippet(value):
        """Приводит любые данные к тексту для записи в файлы и stdin."""
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return '' if value is None else str(value)

    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        task_id = data.get('task_id')
        user_code = normalize_snippet(data.get('user_code', ''))
        language = data.get('language', 'python').lower()  # Нормализуем язык к нижнему регистру

        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400

        if not user_code:
            return jsonify({'error': 'user_code is required'}), 400

        if task_generator is None:
            return jsonify({'error': 'TaskGenerator not initialized'}), 500

        # Получаем задачу из кэша
        task = task_generator.task_cache.get(task_id)
        if not task:
            return jsonify({'error': f'Task {task_id} not found'}), 404

        test_cases = task.get('test_cases', [])
        if not test_cases:
            return jsonify({'error': 'No test cases found'}), 400

        # Выполняем тесты
        passed_tests = 0
        total_tests = len(test_cases)
        test_results = []

        for i, test_case in enumerate(test_cases):
            test_input = normalize_snippet(test_case.get('input', ''))
            expected_output = normalize_snippet(test_case.get('output', '')).strip()

            try:
                # Выполняем код с тестовым вводом
                if language == 'python':
                    # Создаем временный файл с кодом пользователя
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                        f.write(user_code)
                        temp_file = f.name

                    try:
                        # Запускаем код с входными данными через stdin
                        process = subprocess.run(
                            ['python', temp_file],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            encoding='utf-8'
                        )

                        # Получаем вывод
                        if process.returncode == 0:
                            actual_output = process.stdout.strip()
                        else:
                            # Если была ошибка выполнения, берем stderr
                            actual_output = process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Runtime error'
                            })
                            continue

                        # Сравниваем результаты (игнорируем пробелы в конце)
                        actual_clean = actual_output.strip()
                        expected_clean = expected_output.strip()

                        if actual_clean == expected_clean:
                            passed_tests += 1
                            test_results.append({
                                'test': i + 1,
                                'status': 'passed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                        else:
                            test_results.append({
                                'test': i + 1,
                                'status': 'failed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                    finally:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                elif language == 'go':
                    # Go требует, чтобы файл был в директории с go.mod или использовался go run
                    import tempfile as tf
                    temp_dir = tf.mkdtemp()
                    try:
                        go_file = os.path.join(temp_dir, 'main.go')
                        with open(go_file, 'w', encoding='utf-8') as f:
                            # Убеждаемся, что код имеет package main
                            if 'package main' not in user_code:
                                f.write('package main\n\n')
                            f.write(user_code)

                        # Запускаем код Go с входными данными через stdin
                        process = subprocess.run(
                            ['go', 'run', go_file],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=10,
                            encoding='utf-8',
                            cwd=temp_dir
                        )

                        if process.returncode == 0:
                            actual_output = process.stdout.strip()
                        else:
                            actual_output = process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Compilation or runtime error'
                            })
                            continue

                        actual_clean = actual_output.strip()
                        expected_clean = expected_output.strip()

                        if actual_clean == expected_clean:
                            passed_tests += 1
                            test_results.append({
                                'test': i + 1,
                                'status': 'passed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                        else:
                            test_results.append({
                                'test': i + 1,
                                'status': 'failed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                    finally:
                        import shutil
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)

                elif language == 'java':
                    # Создаем временный файл с кодом Java
                    # Java требует, чтобы имя класса совпадало с именем файла
                    class_name = 'Solution'
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False, encoding='utf-8') as f:
                        # Убеждаемся, что класс называется Solution
                        java_code = user_code
                        if 'class Solution' not in java_code and 'public class' in java_code:
                            # Заменяем имя класса на Solution
                            import re
                            java_code = re.sub(r'public class \w+', 'public class Solution', java_code)
                            java_code = re.sub(r'class \w+', 'class Solution', java_code)
                        f.write(java_code)
                        temp_file = f.name
                        temp_dir = os.path.dirname(temp_file)

                    try:
                        # Компилируем Java код
                        compile_process = subprocess.run(
                            ['javac', temp_file],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            encoding='utf-8',
                            cwd=temp_dir
                        )

                        if compile_process.returncode != 0:
                            actual_output = compile_process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Compilation error'
                            })
                            continue

                        # Запускаем скомпилированный класс
                        run_process = subprocess.run(
                            ['java', '-cp', temp_dir, 'Solution'],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            encoding='utf-8'
                        )

                        if run_process.returncode == 0:
                            actual_output = run_process.stdout.strip()
                        else:
                            actual_output = run_process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Runtime error'
                            })
                            continue

                        actual_clean = actual_output.strip()
                        expected_clean = expected_output.strip()

                        if actual_clean == expected_clean:
                            passed_tests += 1
                            test_results.append({
                                'test': i + 1,
                                'status': 'passed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                        else:
                            test_results.append({
                                'test': i + 1,
                                'status': 'failed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                    finally:
                        # Удаляем скомпилированные файлы
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                        class_file = os.path.join(temp_dir, 'Solution.class')
                        if os.path.exists(class_file):
                            os.unlink(class_file)

                elif language == 'cpp' or language == 'c++':
                    # Создаем временный файл с кодом C++
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False, encoding='utf-8') as f:
                        f.write(user_code)
                        temp_file = f.name
                        temp_dir = os.path.dirname(temp_file)
                        exe_file = os.path.join(temp_dir, 'solution.exe' if os.name == 'nt' else 'solution')

                    try:
                        # Компилируем C++ код
                        compile_process = subprocess.run(
                            ['g++', '-o', exe_file, temp_file],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            encoding='utf-8'
                        )

                        if compile_process.returncode != 0:
                            actual_output = compile_process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Compilation error'
                            })
                            continue

                        # Запускаем скомпилированную программу
                        run_process = subprocess.run(
                            [exe_file],
                            input=test_input,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            encoding='utf-8'
                        )

                        if run_process.returncode == 0:
                            actual_output = run_process.stdout.strip()
                        else:
                            actual_output = run_process.stderr.strip()
                            test_results.append({
                                'test': i + 1,
                                'status': 'error',
                                'input': test_input,
                                'expected': expected_output,
                                'actual': actual_output,
                                'error': 'Runtime error'
                            })
                            continue

                        actual_clean = actual_output.strip()
                        expected_clean = expected_output.strip()

                        if actual_clean == expected_clean:
                            passed_tests += 1
                            test_results.append({
                                'test': i + 1,
                                'status': 'passed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                        else:
                            test_results.append({
                                'test': i + 1,
                                'status': 'failed',
                                'input': test_input,
                                'expected': expected_clean,
                                'actual': actual_clean
                            })
                    finally:
                        # Удаляем временные файлы
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                        if os.path.exists(exe_file):
                            os.unlink(exe_file)

                else:
                    # Для других языков возвращаем ошибку
                    return jsonify({
                        'error': f'Language {language} is not supported for test execution yet'
                    }), 400

            except subprocess.TimeoutExpired:
                test_results.append({
                    'test': i + 1,
                    'status': 'timeout',
                    'input': test_input,
                    'error': 'Execution timeout'
                })
            except Exception as e:
                test_results.append({
                    'test': i + 1,
                    'status': 'error',
                    'input': test_input,
                    'error': str(e)
                })

        all_passed = passed_tests == total_tests

        return jsonify({
            'status': 'success',
            'passed': passed_tests,
            'total': total_tests,
            'all_passed': all_passed,
            'test_results': test_results
        }), 200

    except Exception as e:
        error_msg = f"Ошибка при выполнении тестов: {str(e)}"
        print(f"❌ Ошибка в /api/run-tests: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500


@app.route('/main', methods=['POST'])
def review_code_endpoint():
    """Endpoint для обработки запроса на ревью кода"""

@app.route('/api/start', methods=['POST'])
def start_interview():
    data = request.get_json()
    direction = data.get('direction')

    if not direction:
        return jsonify({'error': 'Направление не указано'}), 400

    # Сохраняем в сессии
    session['direction'] = direction
    session['started_at'] = datetime.now().isoformat()
    return jsonify({'success': True})


@app.route('/api/save-fio', methods=['POST'])
def save_fio():
    data = request.get_json()
    fio = data.get('fio')

    if not fio or len(fio) > 100:
        return jsonify({'success': False, 'error': 'Некорректное ФИО'}), 400

    direction = session.get('direction')
    started_at_str = session.get('started_at')

    if not direction:
        return jsonify({'success': False, 'error': 'Направление не найдено в сессии'}), 400

    # Парсим started_at (если нужно — но можно и не брать из сессии, а писать прямо в БД)
    try:
        started_at = datetime.fromisoformat(started_at_str)
    except (TypeError, ValueError):
        started_at = datetime.now(timezone.utc)

    # Создаём запись в БД
    interview = Interview(
        direction=direction,
        fio=fio,
        questionnaire=json.dumps({}),  # 🔹 ЗАГЛУШКА: пустая анкета как JSON
        started_at=started_at,
        session_id=session.sid if hasattr(session, 'sid') else None
    )

    try:
        db.session.add(interview)
        db.session.commit()
        session['interview_id'] = interview.id  # сохраняем ID в сессию на будущее
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        task_id = data.get('task_id')
        user_code = data.get('user_code', '')
        language = data.get('language', 'python')

        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400

        if not user_code:
            return jsonify({'error': 'user_code is required'}), 400

        if task_generator is None:
            error_msg = (
                'TaskGenerator not initialized. Please set OPENAI_API_KEY and OPENAI_BASE_URL '
                'in your .env file or environment variables.'
            )
            print(f"ERROR: {error_msg}")
            return jsonify({
                'error': error_msg,
                'details': 'Check that OPENAI_API_KEY and OPENAI_BASE_URL are set in .env file'
            }), 500

        # Вызываем метод review_code класса TaskGenerator
        result = task_generator.review_code(
            task_id=task_id,
            user_code=user_code,
            language=language
        )

        # Выводим результат в консоль PyCharm
        print("=" * 80)
        print("РЕЗУЛЬТАТ РЕВЬЮ КОДА:")
        print("=" * 80)
        print(f"Task ID: {task_id}")
        print(f"Language: {language}")
        print(f"User Code:\n{user_code}")
        print("\nReview Result:")
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 80)

        return jsonify({
            'status': 'success',
            'result': result
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Ошибка сохранения в БД', 'details': str(e)}), 500

    session['fio'] = fio
    return jsonify({'success': True})


def init_db():
    with app.app_context():
        if 'interviews' not in db.metadata.tables:
            print("⚠️  Таблица 'interviews' не найдена в метаданных — возможно, модель не импортирована")
        db.create_all()
init_db()

def main():
    app.run(port=5000, host='127.0.0.1', debug=True)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        db_path = os.path.abspath(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))

    app.run(port=5000, host='127.0.0.1', debug=True)