from flask import Flask, render_template, redirect,request,jsonify
from flask_login import LoginManager, login_required, logout_user
import requests
from dotenv import load_dotenv
import os
from api import IndexAPI, InterniewAPI, ResultsAPI

app = Flask(__name__)
app.config['SECRET_KEY'] = "key"
load_dotenv()
SITE_KEY = os.environ.get('SITE_KEY')
SECRET_KEY_RECAPTCHA = os.environ.get('SECRET_KEY_RECAPTCHA')

login_manager = LoginManager()
login_manager.init_app(app)



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


def main():
    app.register_blueprint(IndexAPI.blueprint)
    app.register_blueprint(InterniewAPI.blueprint)
    app.register_blueprint(ResultsAPI.blueprint)

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

if __name__ == '__main__':
    main()
