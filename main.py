from flask import Flask, render_template, redirect,request,jsonify
from flask_login import LoginManager, login_required, logout_user
from flask import request, session, jsonify
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
import json

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


        #ВОТ СООБЩЕНИЕ ЮЗЕРА
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        #ВОТ ТУТ ФОРМИРУЕТЕ ОТВЕТ
        bot_reply = f"Умный ответ на твое {user_message}"


        return jsonify({
            'reply': bot_reply,
            'status': 'success'
        })

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