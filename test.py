from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import json
import os

# 1. Настройки (повторяем структуру из app.py)
DATABASE_URL = "sqlite:///interviews.db"  # ← должен совпадать с app.config['SQLALCHEMY_DATABASE_URI']
Base = declarative_base()


# 2. Минимальная модель (только для чтения!)
class Interview(Base):
    __tablename__ = 'interviews'

    id = Column(Integer, primary_key=True)
    direction = Column(String(100), nullable=False)
    fio = Column(String(100), nullable=False)
    questionnaire = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    session_id = Column(String(128), nullable=True)


# 3. Создаём engine и сессию
engine = create_engine(DATABASE_URL, echo=False)  # echo=True → SQL-логи
Session = sessionmaker(bind=engine)
session = Session()


# 4. Самостоятельная функция (не зависит от Flask!)
def get_all_interviews():
    """
    Читает все записи из interviews.db и возвращает список словарей.
    Работает без Flask — только SQLAlchemy Core.
    """
    interviews = session.query(Interview).all()
    result = []

    for i in interviews:
        # Парсим анкету
        try:
            questionnaire = json.loads(i.questionnaire) if i.questionnaire else {}
        except (json.JSONDecodeError, TypeError):
            questionnaire = {"_error": "invalid JSON", "raw": i.questionnaire}

        # Обработка времени (naive → UTC)
        started_at = i.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        else:
            started_at = started_at.astimezone(timezone.utc)

        result.append({
            'id': i.id,
            'direction': i.direction,
            'fio': i.fio,
            'questionnaire': questionnaire,
            'started_at': started_at.isoformat().replace('+00:00', 'Z'),
            'session_id': i.session_id
        })

    return result


# 5. Запуск
if __name__ == '__main__':
    # Проверяем, существует ли БД
    if not os.path.exists("interviews.db"):
        print("❌ Файл interviews.db не найден в текущей папке!")
        print("Текущая директория:", os.getcwd())
        exit(1)

    data = get_all_interviews()
    print(f"✅ Найдено {len(data)} записей:")
    for item in data:
        print(json.dumps(item, ensure_ascii=False, indent=2))