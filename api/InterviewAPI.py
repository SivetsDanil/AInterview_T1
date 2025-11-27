import flask
from flask import (
    current_app,
    jsonify,
    render_template,
    request,
)

blueprint = flask.Blueprint(
    'InterviewAPI',
    __name__,
    template_folder='templates'
)

DEFAULT_POSITION = "Python Developer"
DEFAULT_DIFFICULTY = "middle"


def _generate_task(position: str = DEFAULT_POSITION, difficulty: str = DEFAULT_DIFFICULTY):
    """Запрашивает задачу у TaskGenerator и обрабатывает ошибки."""
    task_generator = current_app.config.get("TASK_GENERATOR")
    if task_generator is None:
        return None, (
            "Сервис генерации задач не настроен. Проверьте переменные окружения "
            "OPENAI_API_KEY и OPENAI_BASE_URL."
        )

    try:
        task = task_generator.generate_task(position=position, difficulty=difficulty)
        if task.get("error"):
            return None, task["error"]
        return task, None
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Не удалось сгенерировать задачу", exc_info=exc)
        return None, "Не удалось сгенерировать задачу. Попробуйте ещё раз через пару минут."


@blueprint.route('/interview', methods=['GET'])
def index():
    task, error = _generate_task()
    return render_template('interview.html', task=task, error=error)


@blueprint.route('/api/generate-task', methods=['POST'])
def generate_task_api():
    """AJAX-эндпоинт для генерации новой задачи с клиента."""
    payload = request.get_json(silent=True) or {}
    position = payload.get('position', DEFAULT_POSITION)
    difficulty = payload.get('difficulty', DEFAULT_DIFFICULTY)

    task, error = _generate_task(position=position, difficulty=difficulty)
    if error:
        return jsonify({'status': 'error', 'error': error}), 500

    return jsonify({'status': 'success', 'task': task}), 200
